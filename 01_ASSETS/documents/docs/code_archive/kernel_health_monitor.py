#!/usr/bin/env python3
"""
内核健康监控脚本
定期检查系统健康状态，推送到飞书群
整合：系统资源/核心服务/记忆网关/GEO晶格/元法则/门户/安全/进程
"""
import os
import sys
import json
import sqlite3
import subprocess
import socket
import urllib.request
from datetime import datetime

DB_PATH = "/opt/ZONGYUAN-ROOT/data/memory_gateway.db"
FEISHU_GATEWAY = "http://127.0.0.1:8001/feishu/im/v1/messages?receive_id_type=chat_id"
FEISHU_CHAT_ID = "oc_1c68eb3664e751e397062ff0c60ffa3"

def run_cmd(cmd, timeout=10):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip()
    except:
        return ""

def check_port(port):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        return result == 0
    except:
        return False

def get_health_data():
    """收集健康数据"""
    data = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "hostname": run_cmd("hostname"),
        "uptime": run_cmd("uptime -p"),
        "system": {},
        "services": {},
        "memory_gateway": {},
        "geo": {},
        "meta_rules": {},
        "portal": {},
        "security": {},
        "issues": [],
        "score": 100,
    }
    
    # 系统资源
    cpu_load = run_cmd("cat /proc/loadavg | awk '{print $1}'")
    mem_used = run_cmd("free -h | grep Mem | awk '{print $3}'")
    mem_total = run_cmd("free -h | grep Mem | awk '{print $2}'")
    mem_pct = run_cmd("free | grep Mem | awk '{printf \"%.0f\", $3/$2*100}'")
    disk_used = run_cmd("df -h / | tail -1 | awk '{print $3}'")
    disk_total = run_cmd("df -h / | tail -1 | awk '{print $2}'")
    disk_pct = run_cmd("df / | tail -1 | awk '{print $5}' | tr -d '%'")
    
    data["system"] = {
        "cpu_load": cpu_load,
        "mem_used": mem_used,
        "mem_total": mem_total,
        "mem_pct": int(mem_pct) if mem_pct else 0,
        "disk_used": disk_used,
        "disk_total": disk_total,
        "disk_pct": int(disk_pct) if disk_pct else 0,
    }
    
    # 内存检查
    if data["system"]["mem_pct"] > 85:
        data["issues"].append(f"内存占用过高: {mem_pct}%")
        data["score"] -= 10
    elif data["system"]["mem_pct"] > 70:
        data["issues"].append(f"内存占用偏高: {mem_pct}%")
        data["score"] -= 5
    
    # 磁盘检查
    if data["system"]["disk_pct"] > 85:
        data["issues"].append(f"磁盘占用过高: {disk_pct}%")
        data["score"] -= 10
    elif data["system"]["disk_pct"] > 70:
        data["issues"].append(f"磁盘占用偏高: {disk_pct}%")
        data["score"] -= 5
    
    # 核心服务
    services = [
        (9120, "记忆网关"),
        (9151, "GEO晶格"),
        (8088, "门户8088"),
        (8014, "向量数据库"),
        (8070, "知识图谱"),
        (8081, "本地LLM"),
        (8021, "AI代理"),
        (8023, "Agent Hub"),
        (8094, "闭环调度"),
        (8001, "飞书网关"),
        (8060, "审批回调"),
    ]
    svc_ok = 0
    svc_fail = 0
    for port, name in services:
        status = check_port(port)
        data["services"][name] = {"port": port, "status": "online" if status else "offline"}
        if status:
            svc_ok += 1
        else:
            svc_fail += 1
            data["issues"].append(f"服务离线: {name}(:{port})")
            data["score"] -= 5
    
    data["services"]["_summary"] = {"online": svc_ok, "offline": svc_fail, "total": len(services)}
    
    # 记忆网关
    try:
        req = urllib.request.Request("http://127.0.0.1:9120/api/status")
        with urllib.request.urlopen(req, timeout=5) as resp:
            gw_data = json.loads(resp.read())
        truths = gw_data.get("stats", {}).get("truths", 0)
        nodes = gw_data.get("stats", {}).get("nodes", 0)
        data["memory_gateway"] = {"truths": truths, "nodes": nodes, "status": "online"}
    except Exception as e:
        data["memory_gateway"] = {"status": "error", "error": str(e)}
        data["issues"].append("记忆网关API无响应")
        data["score"] -= 5
    
    # GEO晶格
    try:
        req = urllib.request.Request("http://127.0.0.1:9151/api/status")
        with urllib.request.urlopen(req, timeout=5) as resp:
            geo_data = json.loads(resp.read())
        lock_level = geo_data.get("lock_level", "?")
        stability = geo_data.get("stability", {}).get("overall_stability", 0)
        data["geo"] = {"lock_level": lock_level, "stability": round(stability * 100, 1), "status": "online"}
        if stability < 0.9:
            data["issues"].append(f"GEO稳态偏低: {stability*100:.1f}%")
            data["score"] -= 5
    except Exception as e:
        data["geo"] = {"status": "error", "error": str(e)}
    
    # 元法则
    mr_file = "/opt/ZONGYUAN-ROOT/meta_rule_set.json"
    if os.path.exists(mr_file):
        try:
            with open(mr_file) as f:
                mr_data = json.load(f)
            mr_count = len(mr_data.get("meta_rules", []))
            mr_version = mr_data.get("version", "?")
            chattr = run_cmd(f"lsattr {mr_file} 2>/dev/null | grep -q 'i' && echo 'yes' || echo 'no'")
            data["meta_rules"] = {"count": mr_count, "version": mr_version, "chattr_i": chattr == "yes"}
            if chattr != "yes":
                data["issues"].append("元法则未设置chattr +i保护")
                data["score"] -= 3
        except Exception as e:
            data["meta_rules"] = {"status": "error", "error": str(e)}
    
    # 门户
    portal_http = run_cmd("curl -s -o /dev/null -w '%{http_code}' -H 'Host: www.huodouai.com' --resolve www.huodouai.com:443:127.0.0.1 -sk https://www.huodouai.com/aios/ 2>/dev/null")
    data["portal"] = {"http_code": portal_http, "status": "online" if portal_http == "200" else "error"}
    if portal_http != "200":
        data["issues"].append(f"门户HTTP异常: {portal_http}")
        data["score"] -= 5
    
    # 安全
    ssh_fail = run_cmd("grep -c 'Failed password' /var/log/secure 2>/dev/null || echo 0")
    failed_services = run_cmd("systemctl --failed --no-pager 2>/dev/null | grep -c 'loaded failed'")
    zombie = run_cmd("ps aux | awk '$8==\"Z\"' | wc -l")
    data["security"] = {
        "ssh_fail_count": int(ssh_fail) if ssh_fail else 0,
        "failed_services": int(failed_services) if failed_services else 0,
        "zombie_processes": int(zombie) if zombie else 0,
    }
    if int(failed_services) > 0:
        data["issues"].append(f"失败服务: {failed_services}个")
        data["score"] -= 5
    if int(zombie) > 5:
        data["issues"].append(f"僵尸进程过多: {zombie}个")
        data["score"] -= 3
    
    # Merkle链完整性检查
    merkle_file = "/opt/ZONGYUAN-ROOT/kernel/merkle_chain_state.json"
    if os.path.exists(merkle_file):
        try:
            with open(merkle_file) as f:
                merkle_data = json.load(f)
            chain = merkle_data.get("chain", [])
            current_root = merkle_data.get("current_root", "")
            last_update = merkle_data.get("last_update", "")
            chain_height = len(chain)
            
            # 检查链连续性
            chain_continuous = True
            if len(chain) > 1:
                for i in range(1, len(chain)):
                    if chain[i].get("prev_root") != chain[i-1].get("merkle_root"):
                        chain_continuous = False
                        break
            
            # 检查最后更新时间（超过24小时未更新视为异常）
            time_diff_hours = 999
            if last_update:
                try:
                    last_dt = datetime.fromisoformat(last_update.replace("Z", "+00:00"))
                    time_diff_hours = (datetime.now() - last_dt.replace(tzinfo=None)).total_seconds() / 3600
                except:
                    pass
            
            data["merkle_chain"] = {
                "height": chain_height,
                "current_root": current_root[:20] + "..." if len(current_root) > 20 else current_root,
                "last_update": last_update,
                "chain_continuous": chain_continuous,
                "hours_since_update": round(time_diff_hours, 1),
            }
            
            if not chain_continuous:
                data["issues"].append("Merkle链不连续！")
                data["score"] -= 10
            elif time_diff_hours > 24:
                data["issues"].append(f"Merkle链超过{round(time_diff_hours)}小时未更新")
                data["score"] -= 5
        except Exception as e:
            data["merkle_chain"] = {"status": "error", "error": str(e)}
            data["issues"].append("Merkle链状态文件读取失败")
            data["score"] -= 5
    else:
        data["merkle_chain"] = {"status": "not_found"}
        data["issues"].append("Merkle链状态文件不存在")
        data["score"] -= 5
    
    # 确保分数不低于0
    if data["score"] < 0:
        data["score"] = 0
    
    return data

def format_feishu_message(data):
    """格式化为飞书消息"""
    score = data["score"]
    if score >= 90:
        status_emoji = "🟢"
        status_text = "健康"
    elif score >= 70:
        status_emoji = "🟡"
        status_text = "注意"
    else:
        status_emoji = "🔴"
        status_text = "异常"
    
    sys_info = data["system"]
    svc_summary = data["services"].get("_summary", {})
    
    msg = f"""{'='*40}
🔍 内核健康监控报告
{'='*40}

⏰ 时间: {data['timestamp']}
🖥️ 主机: {data['hostname']}
⏱️ 运行: {data['uptime']}

{status_emoji} 综合评分: {score}/100 ({status_text})

📊 系统资源:
  CPU负载: {sys_info.get('cpu_load', '?')}
  内存: {sys_info.get('mem_used', '?')}/{sys_info.get('mem_total', '?')} ({sys_info.get('mem_pct', '?')}%)
  磁盘: {sys_info.get('disk_used', '?')}/{sys_info.get('disk_total', '?')} ({sys_info.get('disk_pct', '?')}%)

⚙️ 核心服务:
  在线: {svc_summary.get('online', '?')}/{svc_summary.get('total', '?')}
  离线: {svc_summary.get('offline', '?')}

🧠 记忆网关:
  真值: {data['memory_gateway'].get('truths', '?')}条
  节点: {data['memory_gateway'].get('nodes', '?')}个

🔮 GEO晶格:
  锁档: Lv{data['geo'].get('lock_level', '?')}
  稳态: {data['geo'].get('stability', '?')}%

📜 元法则:
  数量: {data['meta_rules'].get('count', '?')}条
  版本: {data['meta_rules'].get('version', '?')}
  保护: {'✅ chattr+i' if data['meta_rules'].get('chattr_i') else '❌ 未保护'}

🌐 门户:
  HTTP: {data['portal'].get('http_code', '?')}

🔗 Merkle链:
  高度: {data['merkle_chain'].get('height', '?')}
  根哈希: {data['merkle_chain'].get('current_root', '?')}
  连续: {'✅' if data['merkle_chain'].get('chain_continuous') else '❌'}
  最后更新: {data['merkle_chain'].get('last_update', '?')[:19]} ({data['merkle_chain'].get('hours_since_update', '?')}小时前)

🔒 安全:
  SSH失败: {data['security'].get('ssh_fail_count', '?')}次
  失败服务: {data['security'].get('failed_services', '?')}个
  僵尸进程: {data['security'].get('zombie_processes', '?')}个
"""
    
    if data["issues"]:
        msg += f"""
⚠️ 发现问题 ({len(data['issues'])}项):
"""
        for i, issue in enumerate(data["issues"], 1):
            msg += f"  {i}. {issue}\n"
    
    msg += f"""
{'='*40}
Ω₀⊂⊙∞⊂Ω · DID-BR-000002
元极恒一超认知永恒自治体系
{'='*40}
"""
    return msg

def send_to_feishu(message):
    """发送到飞书群"""
    try:
        payload = {
            "receive_id": FEISHU_CHAT_ID,
            "msg_type": "text",
            "content": json.dumps({"text": message}, ensure_ascii=False)
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            FEISHU_GATEWAY,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            return result.get("code", -1) == 0
    except Exception as e:
        print(f"  飞书推送失败: {e}")
        return False

def main():
    print("=" * 60)
    print("  内核健康监控 - 执行中")
    print("=" * 60)
    print()
    
    # 收集健康数据
    print("  [1/3] 收集健康数据...")
    data = get_health_data()
    print(f"  ✅ 数据收集完成，综合评分: {data['score']}/100")
    print()
    
    # 保存到本地
    print("  [2/3] 保存健康报告...")
    report_dir = "/opt/ZONGYUAN-ROOT/health_reports"
    os.makedirs(report_dir, exist_ok=True)
    report_file = f"{report_dir}/health_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  ✅ 报告已保存: {report_file}")
    print()
    
    # 推送到飞书
    print("  [3/3] 推送到飞书...")
    message = format_feishu_message(data)
    success = send_to_feishu(message)
    if success:
        print("  ✅ 飞书推送成功")
    else:
        print("  ❌ 飞书推送失败")
    print()
    
    # 输出摘要
    print("=" * 60)
    print("  健康监控摘要")
    print("=" * 60)
    print(f"  综合评分: {data['score']}/100")
    print(f"  内存: {data['system']['mem_pct']}%")
    print(f"  磁盘: {data['system']['disk_pct']}%")
    print(f"  服务: {data['services']['_summary']['online']}/{data['services']['_summary']['total']}在线")
    print(f"  真值: {data['memory_gateway'].get('truths', '?')}条")
    print(f"  问题: {len(data['issues'])}项")
    if data["issues"]:
        for issue in data["issues"]:
            print(f"    - {issue}")
    print()
    print("  Ω₀⊂⊙∞⊂Ω · DID-BR-000002")
    print("  内核健康监控完成")
    print()

if __name__ == "__main__":
    main()
