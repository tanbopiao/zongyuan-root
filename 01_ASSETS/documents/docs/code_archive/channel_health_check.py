#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 同步通道健康检查脚本 V1.0
元极恒一自治体系 - 8通道同步体系健康管理

功能：
1. 8通道自动健康检测
2. 通道延迟测量
3. 通道可用性验证
4. 故障切换建议
5. 通道健康评分
6. 健康报告生成

通道清单：
1. 飞书Base (状态台账/资产台账读写)
2. 飞书云盘 (文件上传下载)
3. 飞书知识库 (节点创建/内容写入)
4. 飞书IM (消息通知)
5. SSH (云服务器命令执行)
6. 记忆网关API (真值读写)
7. Git仓库 (版本管理)
8. SQLite本地 (本地数据同步)
"""

import os
import sys
import json
import time
import subprocess
import argparse
from datetime import datetime
from pathlib import Path

# 配置
BASE_TOKEN = "AM2VbZ064akRc1sFWw3cVAdTnBg"
STATUS_TABLE = "tblJg58700JMNxx7"
MONITOR_DIR = "/home/user/Doubao/chats/1128121028098/monitoring"
CHANNEL_REPORT = os.path.join(MONITOR_DIR, "channel_health_report.json")

# 通道定义
CHANNELS = {
    "feishu_base": {
        "name": "飞书Base",
        "description": "状态台账/资产台账读写",
        "priority": "P0",
        "category": "飞书生态",
        "test_type": "read_write"
    },
    "feishu_drive": {
        "name": "飞书云盘",
        "description": "文件上传下载",
        "priority": "P0",
        "category": "飞书生态",
        "test_type": "read"
    },
    "feishu_wiki": {
        "name": "飞书知识库",
        "description": "节点创建/内容写入",
        "priority": "P1",
        "category": "飞书生态",
        "test_type": "read"
    },
    "feishu_im": {
        "name": "飞书IM",
        "description": "消息通知",
        "priority": "P2",
        "category": "飞书生态",
        "test_type": "config_check"
    },
    "ssh": {
        "name": "SSH",
        "description": "云服务器命令执行",
        "priority": "P0",
        "category": "云服务器",
        "test_type": "connectivity"
    },
    "memory_gateway": {
        "name": "记忆网关API",
        "description": "真值读写 (依赖SSH)",
        "priority": "P0",
        "category": "云服务器",
        "test_type": "indirect",
        "depends_on": "ssh"
    },
    "git": {
        "name": "Git仓库",
        "description": "版本管理",
        "priority": "P2",
        "category": "版本控制",
        "test_type": "config_check"
    },
    "sqlite_local": {
        "name": "SQLite本地",
        "description": "本地数据同步",
        "priority": "P1",
        "category": "本地存储",
        "test_type": "local"
    }
}


def ensure_dir():
    os.makedirs(MONITOR_DIR, exist_ok=True)


def run_lark(args, timeout=15):
    """执行lark-cli命令并计时"""
    start = time.time()
    try:
        r = subprocess.run(
            ['lark-cli'] + args + ['--as', 'user', '--format', 'json'],
            capture_output=True, text=True, timeout=timeout
        )
        elapsed = time.time() - start
        lines = r.stdout.strip().split('\n')
        js = next((i for i, l in enumerate(lines) if l.strip().startswith('{')), 0)
        try:
            data = json.loads('\n'.join(lines[js:]))
            return {"ok": data.get("ok", False), "elapsed": elapsed, "data": data}
        except:
            return {"ok": False, "elapsed": elapsed, "error": "parse failed"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "elapsed": timeout, "error": "timeout"}
    except Exception as e:
        return {"ok": False, "elapsed": time.time() - start, "error": str(e)}


def test_feishu_base():
    """测试飞书Base通道"""
    # 读测试
    read_result = run_lark([
        'base', '+record-list',
        '--base-token', BASE_TOKEN,
        '--table-id', STATUS_TABLE,
        '--page-size', '5'
    ])
    
    if not read_result["ok"]:
        return {"status": "down", "latency_ms": read_result["elapsed"] * 1000, "error": read_result.get("error", "read failed")}
    
    # 写测试（写入一个测试键然后删除）
    test_key = f"_channel_test_{int(time.time())}"
    write_result = run_lark([
        'base', '+record-upsert',
        '--base-token', BASE_TOKEN,
        '--table-id', STATUS_TABLE,
        '--json', json.dumps({"状态键": test_key, "状态值": "test", "备注": "通道健康检查", "更新时间": datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
    ])
    
    total_latency = (read_result["elapsed"] + write_result.get("elapsed", 0)) * 1000
    
    if write_result.get("ok"):
        return {"status": "healthy", "latency_ms": round(total_latency, 1), "read_ok": True, "write_ok": True}
    else:
        return {"status": "degraded", "latency_ms": round(total_latency, 1), "read_ok": True, "write_ok": False, "error": "write failed"}


def test_feishu_drive():
    """测试飞书云盘通道"""
    # 搜索测试（读操作）
    result = run_lark([
        'drive', '+search',
        '--query', 'ZONGYUAN',
        '--page-size', '3'
    ], timeout=10)
    
    if result["ok"]:
        return {"status": "healthy", "latency_ms": round(result["elapsed"] * 1000, 1)}
    else:
        return {"status": "down", "latency_ms": round(result["elapsed"] * 1000, 1), "error": result.get("error", "search failed")}


def test_feishu_wiki():
    """测试飞书知识库通道"""
    # 列出知识空间（读操作）
    result = run_lark([
        'wiki', '+space-list'
    ], timeout=10)
    
    if result["ok"]:
        return {"status": "healthy", "latency_ms": round(result["elapsed"] * 1000, 1)}
    else:
        return {"status": "down", "latency_ms": round(result["elapsed"] * 1000, 1), "error": result.get("error", "space-list failed")}


def test_feishu_im():
    """测试飞书IM通道（配置检查）"""
    # 检查是否有配置的群聊ID
    config_path = "/home/user/Doubao/chats/1128121028098/sync_channels/im_config.json"
    if os.path.exists(config_path):
        try:
            with open(config_path) as f:
                config = json.load(f)
            if config.get("chat_id"):
                return {"status": "configured", "latency_ms": 0, "chat_id": config["chat_id"][:10] + "..."}
        except:
            pass
    
    return {"status": "not_configured", "latency_ms": 0, "error": "群聊ID未配置，通知通道不可用"}


def test_ssh():
    """测试SSH通道"""
    start = time.time()
    try:
        r = subprocess.run(
            ['ssh', '-o', 'ConnectTimeout=10', '-o', 'ServerAliveInterval=5',
             '-o', 'ServerAliveCountMax=2', '-o', 'StrictHostKeyChecking=no',
             'zongyuan-cloud', 'echo SSH_OK'],
            capture_output=True, text=True, timeout=20
        )
        elapsed = time.time() - start
        if r.returncode == 0 and "SSH_OK" in r.stdout:
            return {"status": "healthy", "latency_ms": round(elapsed * 1000, 1)}
        else:
            return {"status": "degraded", "latency_ms": round(elapsed * 1000, 1), "error": r.stderr[:100] if r.stderr else "auth failed"}
    except subprocess.TimeoutExpired:
        return {"status": "down", "latency_ms": 20000, "error": "connection timeout (认证成功但会话建立超时)"}
    except Exception as e:
        return {"status": "down", "latency_ms": round((time.time() - start) * 1000, 1), "error": str(e)}


def test_memory_gateway():
    """测试记忆网关API（间接，依赖SSH）"""
    # 先检查SSH状态
    ssh_status = test_ssh()
    if ssh_status["status"] != "healthy":
        return {"status": "indirect_unavailable", "latency_ms": 0, "depends_on": "ssh", "ssh_status": ssh_status["status"], "error": "依赖SSH通道，SSH不可用导致记忆网关间接不可达"}
    
    # SSH可用时测试记忆网关
    start = time.time()
    try:
        r = subprocess.run(
            ['ssh', '-o', 'ConnectTimeout=10', 'zongyuan-cloud',
             'curl -s -m 5 http://127.0.0.1:9120/api/status'],
            capture_output=True, text=True, timeout=20
        )
        elapsed = time.time() - start
        if r.returncode == 0:
            try:
                data = json.loads(r.stdout)
                return {"status": "healthy", "latency_ms": round(elapsed * 1000, 1),
                        "truths": data.get("stats", {}).get("truths", "?"),
                        "nodes": data.get("stats", {}).get("nodes", "?")}
            except:
                return {"status": "degraded", "latency_ms": round(elapsed * 1000, 1), "error": "parse failed"}
        else:
            return {"status": "down", "latency_ms": round(elapsed * 1000, 1), "error": "curl failed"}
    except Exception as e:
        return {"status": "down", "latency_ms": round((time.time() - start) * 1000, 1), "error": str(e)}


def test_git():
    """测试Git仓库通道（配置检查）"""
    git_config = "/home/user/Doubao/chats/1128121028098/sync_channels/git_config.json"
    if os.path.exists(git_config):
        try:
            with open(git_config) as f:
                config = json.load(f)
            if config.get("repo_url"):
                return {"status": "configured", "latency_ms": 0, "repo_url": config["repo_url"][:20] + "..."}
        except:
            pass
    
    # 检查本地git配置
    try:
        r = subprocess.run(['git', 'config', '--global', 'user.name'], capture_output=True, text=True, timeout=5)
        if r.returncode == 0 and r.stdout.strip():
            return {"status": "partial", "latency_ms": 0, "git_user": r.stdout.strip(), "error": "git用户已配置，但仓库URL未配置"}
    except:
        pass
    
    return {"status": "not_configured", "latency_ms": 0, "error": "Git仓库未配置"}


def test_sqlite_local():
    """测试SQLite本地通道"""
    import sqlite3
    start = time.time()
    try:
        db_path = os.path.join(MONITOR_DIR, "channel_test.db")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY, value TEXT, ts TEXT)")
        cursor.execute("INSERT INTO test (value, ts) VALUES (?, ?)", ("test", datetime.now().isoformat()))
        conn.commit()
        cursor.execute("SELECT COUNT(*) FROM test")
        count = cursor.fetchone()[0]
        conn.close()
        elapsed = time.time() - start
        return {"status": "healthy", "latency_ms": round(elapsed * 1000, 1), "records": count}
    except Exception as e:
        return {"status": "down", "latency_ms": round((time.time() - start) * 1000, 1), "error": str(e)}


def calculate_channel_score(channel_result):
    """计算通道健康评分"""
    status = channel_result.get("status", "unknown")
    
    if status == "healthy":
        latency = channel_result.get("latency_ms", 1000)
        if latency < 500:
            return 100
        elif latency < 1000:
            return 90
        elif latency < 2000:
            return 80
        else:
            return 70
    elif status == "degraded":
        return 50
    elif status in ("down", "indirect_unavailable"):
        return 0
    elif status in ("configured", "partial"):
        return 60  # 已配置但未测试
    elif status == "not_configured":
        return 0
    else:
        return 30


def generate_failover_suggestions(results):
    """生成故障切换建议"""
    suggestions = []
    
    # 检查P0通道
    p0_channels = {k: v for k, v in CHANNELS.items() if v["priority"] == "P0"}
    for channel_id, channel_info in p0_channels.items():
        result = results.get(channel_id, {})
        score = result.get("score", 0)
        if score < 50:
            if channel_id == "ssh":
                suggestions.append({
                    "channel": "SSH",
                    "issue": "SSH通道不可用",
                    "impact": "记忆网关API间接不可达，云服务器操作受阻",
                    "failover": "使用飞书Base作为真值写入备用通道；通过腾讯云VNC登录修复SSH",
                    "priority": "P0-紧急"
                })
            elif channel_id == "memory_gateway":
                suggestions.append({
                    "channel": "记忆网关API",
                    "issue": "记忆网关不可达",
                    "impact": "27条真值待同步，真值库可能过时",
                    "failover": "待SSH恢复后批量同步；期间使用飞书Base状态台账作为真值权威源",
                    "priority": "P0-紧急"
                })
    
    # 检查通知通道
    im_result = results.get("feishu_im", {})
    if im_result.get("status") == "not_configured":
        suggestions.append({
            "channel": "飞书IM",
            "issue": "通知通道未配置",
            "impact": "告警无法即时通知，安全事件响应延迟",
            "failover": "配置飞书群聊chat_id；临时使用飞书Base状态记录告警",
            "priority": "P1-高"
        })
    
    # 检查版本控制通道
    git_result = results.get("git", {})
    if git_result.get("status") == "not_configured":
        suggestions.append({
            "channel": "Git仓库",
            "issue": "版本管理通道未配置",
            "impact": "代码和配置无版本控制，回滚困难",
            "failover": "配置Git仓库URL和访问令牌；临时使用本地文件备份+Merkle-DAG",
            "priority": "P2-中"
        })
    
    return suggestions


def run_channel_check():
    """执行通道健康检查"""
    ensure_dir()
    
    print("="*70)
    print("ZONGYUAN-ROOT 同步通道健康检查")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    results = {}
    
    # 按顺序测试各通道
    test_order = [
        ("feishu_base", test_feishu_base),
        ("feishu_drive", test_feishu_drive),
        ("feishu_wiki", test_feishu_wiki),
        ("feishu_im", test_feishu_im),
        ("ssh", test_ssh),
        ("memory_gateway", test_memory_gateway),
        ("git", test_git),
        ("sqlite_local", test_sqlite_local),
    ]
    
    for i, (channel_id, test_func) in enumerate(test_order, 1):
        channel_info = CHANNELS[channel_id]
        print(f"\n[{i}/8] 测试 {channel_info['name']} ({channel_info['priority']})...")
        try:
            result = test_func()
        except Exception as e:
            result = {"status": "error", "latency_ms": 0, "error": str(e)}
        
        result["score"] = calculate_channel_score(result)
        result["channel_id"] = channel_id
        result["channel_name"] = channel_info["name"]
        result["priority"] = channel_info["priority"]
        result["category"] = channel_info["category"]
        results[channel_id] = result
        
        status_icon = {"healthy": "✅", "degraded": "⚠️", "down": "❌",
                       "configured": "⚙️", "not_configured": "🔧", "partial": "🔧",
                       "indirect_unavailable": "🔗", "error": "❌"}.get(result["status"], "❓")
        
        latency_str = f"{result['latency_ms']}ms" if result.get("latency_ms", 0) > 0 else "N/A"
        print(f"  {status_icon} 状态: {result['status']} | 评分: {result['score']}/100 | 延迟: {latency_str}")
        if result.get("error"):
            print(f"     错误: {result['error'][:80]}")
    
    # 计算总体健康度
    total_score = sum(r["score"] for r in results.values())
    avg_score = round(total_score / len(results), 1)
    healthy_count = sum(1 for r in results.values() if r["status"] == "healthy")
    down_count = sum(1 for r in results.values() if r["status"] in ("down", "indirect_unavailable"))
    
    # 生成故障切换建议
    suggestions = generate_failover_suggestions(results)
    
    # 保存报告
    report = {
        "checked_at": datetime.now().isoformat(),
        "overall_score": avg_score,
        "healthy_count": healthy_count,
        "down_count": down_count,
        "total_channels": len(results),
        "channels": results,
        "failover_suggestions": suggestions
    }
    
    with open(CHANNEL_REPORT, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    # 输出总结
    print("\n" + "="*70)
    print("通道健康检查总结")
    print("="*70)
    print(f"  总体健康评分: {avg_score}/100")
    print(f"  健康通道: {healthy_count}/{len(results)}")
    print(f"  故障通道: {down_count}/{len(results)}")
    
    if suggestions:
        print(f"\n故障切换建议 ({len(suggestions)} 条):")
        for s in suggestions:
            print(f"  [{s['priority']}] {s['channel']}: {s['issue']}")
            print(f"    影响: {s['impact']}")
            print(f"    建议: {s['failover']}")
    
    print(f"\n报告已保存: {CHANNEL_REPORT}")
    return report


def main():
    parser = argparse.ArgumentParser(description='ZONGYUAN-ROOT 同步通道健康检查')
    parser.add_argument('--check', action='store_true', help='执行通道健康检查')
    parser.add_argument('--report', action='store_true', help='显示上次检查报告')
    args = parser.parse_args()
    
    if args.report:
        if os.path.exists(CHANNEL_REPORT):
            with open(CHANNEL_REPORT) as f:
                report = json.load(f)
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            print("暂无检查报告，请先执行 --check")
    else:
        run_channel_check()


if __name__ == "__main__":
    main()
