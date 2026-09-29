#!/usr/bin/env python3
"""
全域变更管控系统 - 迭代阶段变更管理
依据：MR-080全域变更管控元法则
功能：变更分级/自动审批/人工审批/全域锁定/变更审计
"""
import os
import sys
import json
import time
import hashlib
import subprocess
from datetime import datetime
from collections import defaultdict

BASE_DIR = "/opt/ZONGYUAN-ROOT"
LOG_FILE = f"{BASE_DIR}/logs/change_manager.log"
CHAT_ID = "oc_1c68eb3664e751e397062ff0c60ffa3"

# ============================================================
# 变更分级规范（P0-P4）
# ============================================================
CHANGE_LEVELS = {
    "P0": {
        "name": "核心架构变更",
        "risk": "critical",
        "color": "red",
        "must_manual": True,
        "auto_threshold": 100,
        "examples": [
            "元法则新增/修改/删除",
            "记忆网关9120配置变更",
            "通信协议网关9122变更",
            "GEO晶格9151配置变更",
            "SSH配置/用户/密钥变更",
            "iptables/防火墙规则变更",
            "端口公网开放/关闭",
            "数据库结构变更",
            "域名/DNS/SSL证书变更",
            "系统级配置(sysctl/systemd)",
            "chattr白名单变更",
            "Merkle链配置变更"
        ]
    },
    "P1": {
        "name": "核心服务变更",
        "risk": "high",
        "color": "orange",
        "must_manual": True,
        "auto_threshold": 95,
        "examples": [
            "核心服务启停/重启（记忆网关/通信网关/GEO）",
            "核心服务配置参数修改",
            "crontab定时任务新增/删除/修改",
            "Nginx核心配置变更",
            "飞书应用配置变更",
            "希尔伯特镜像态/QEL配置变更",
            "本地LLM模型切换/参数调整",
            "向量数据库配置变更",
            "知识图谱服务配置变更"
        ]
    },
    "P2": {
        "name": "功能开发与部署",
        "risk": "medium_high",
        "color": "yellow",
        "must_manual": False,
        "auto_threshold": 90,
        "examples": [
            "新服务部署",
            "现有服务功能新增",
            "API接口新增/修改",
            "网页内容/样式更新",
            "脚本功能新增（非核心）",
            "真值库批量导入",
            "飞书Base表结构变更",
            "文档/白皮书更新"
        ]
    },
    "P3": {
        "name": "优化与维护",
        "risk": "medium",
        "color": "blue",
        "must_manual": False,
        "auto_threshold": 80,
        "examples": [
            "非核心服务参数调优",
            "日志级别调整",
            "监控阈值调整",
            "非核心服务重启",
            "缓存清理",
            "临时文件清理",
            "性能优化（不改变功能）"
        ]
    },
    "P4": {
        "name": "低风险操作",
        "risk": "low",
        "color": "green",
        "must_manual": False,
        "auto_threshold": 70,
        "examples": [
            "只读查询/统计",
            "日志查看",
            "状态检查",
            "文档生成",
            "报告生成",
            "数据导出（不修改）"
        ]
    }
}

# ============================================================
# 全域锁定清单（chattr +i）
# ============================================================
LOCKDOWN_FILES = {
    "meta_laws": [
        "/opt/ZONGYUAN-ROOT/meta_rule_set.json",
    ],
    "core_config": [
        "/opt/ZONGYUAN-ROOT/config/chattr_whitelist.json",
        "/opt/ZONGYUAN-ROOT/config/iptables_rules.rules",
        "/opt/ZONGYUAN-ROOT/config/crontab_priority.json",
    ],
    "core_scripts": [
        "/opt/ZONGYUAN-ROOT/scripts/port_ledger.py",
        "/opt/ZONGYUAN-ROOT/scripts/port_change_approval.py",
        "/opt/ZONGYUAN-ROOT/scripts/restore_iptables.sh",
        "/opt/ZONGYUAN-ROOT/scripts/chattr_safe.sh",
        "/opt/ZONGYUAN-ROOT/scripts/kernel_health_monitor.py",
        "/opt/ZONGYUAN-ROOT/scripts/realtime_alert.py",
        "/opt/ZONGYUAN-ROOT/scripts/merkle_chain_maintainer.py",
        "/opt/ZONGYUAN-ROOT/scripts/change_manager.py",
    ],
    "security": [
        "/opt/ZONGYUAN-ROOT/scripts/feishu_approval_callback.py",
        "/opt/ZONGYUAN-ROOT/scripts/approval_bridge.py",
        "/opt/ZONGYUAN-ROOT/scripts/intelligent_approval_engine.py",
        "/opt/ZONGYUAN-ROOT/scripts/intelligent_approval_daemon.py",
    ],
    "system": [
        "/etc/ssh/sshd_config",
        "/etc/hosts.allow",
        "/etc/hosts.deny",
    ]
}

# 绝对禁止chattr +i的文件（黑名单）
NEVER_LOCK = [
    "/opt/ZONGYUAN-ROOT/kernel/merkle_chain_state.json",
    "/opt/ZONGYUAN-ROOT/data/memory_gateway.db",
    "/opt/ZONGYUAN-ROOT/data/quantum_entanglement.db",
]

def log(msg, level="INFO"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{level}] {msg}"
    print(line)
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def send_feishu(text):
    try:
        sys.path.insert(0, f"{BASE_DIR}/scripts")
        from feishu_media_archive_bot import send_text
        send_text(CHAT_ID, text)
    except Exception as e:
        log(f"发飞书失败: {e}", "WARN")

def classify_change(description, file_path="", command=""):
    """自动分类变更级别"""
    desc = (description + " " + file_path + " " + command).lower()
    
    # P0关键词
    p0_keywords = ["元法则", "meta_rule", "9120", "记忆网关", "9122", "通信网关", "9151", "geo晶格",
                   "ssh", "sshd", "iptables", "防火墙", "端口", "port", "数据库结构", "域名", "dns", "ssl",
                   "sysctl", "systemd", "chattr", "merkle", "哈希链", "密钥", "authorized_keys"]
    for kw in p0_keywords:
        if kw in desc:
            return "P0"
    
    # P1关键词
    p1_keywords = ["crontab", "定时任务", "nginx", "飞书配置", "app_id", "app_secret",
                   "镜像态", "qel", "9125", "9160", "llama", "本地llm", "向量数据库", "8014",
                   "知识图谱", "8070", "核心服务", "重启"]
    for kw in p1_keywords:
        if kw in desc:
            return "P1"
    
    # P2关键词
    p2_keywords = ["部署", "deploy", "新服务", "新增功能", "api", "接口", "网页", "官网",
                   "脚本", "真值导入", "base表", "文档", "白皮书"]
    for kw in p2_keywords:
        if kw in desc:
            return "P2"
    
    # P3关键词
    p3_keywords = ["优化", "调优", "参数", "日志级别", "监控", "阈值", "缓存", "清理", "性能"]
    for kw in p3_keywords:
        if kw in desc:
            return "P3"
    
    # 默认P2
    return "P2"

def intelligent_evaluate(change_type, description):
    """五方智能体仲裁评分"""
    try:
        sys.path.insert(0, f"{BASE_DIR}/scripts")
        from intelligent_approval_engine import (
            security_score, stability_score, cost_score,
            value_score, compliance_score, AGENT_WEIGHTS
        )
        
        op = {"type": change_type, "description": description}
        scores = {
            "security": security_score(op),
            "stability": stability_score(op),
            "cost": cost_score(op),
            "value": value_score(op),
            "compliance": compliance_score(op)
        }
        total = sum(scores[k] * AGENT_WEIGHTS[k] for k in AGENT_WEIGHTS)
        return {"scores": scores, "total_score": round(total, 1)}
    except Exception as e:
        log(f"智能评估失败: {e}")
        return {"scores": {}, "total_score": 0}

def submit_change(change_type, description, execution_cmd="", file_path=""):
    """提交变更申请"""
    change_id = f"CHG-{hashlib.md5(f'{change_type}{description}{time.time()}'.encode()).hexdigest()[:8].upper()}"
    
    # 自动分级
    auto_level = classify_change(description, file_path, execution_cmd)
    level_config = CHANGE_LEVELS[auto_level]
    
    change = {
        "change_id": change_id,
        "change_type": change_type,
        "level": auto_level,
        "level_name": level_config["name"],
        "risk": level_config["risk"],
        "description": description,
        "execution_cmd": execution_cmd,
        "file_path": file_path,
        "submitted_at": datetime.now().isoformat(),
        "status": "pending"
    }
    
    log(f"提交变更: {change_id} | {auto_level} | {description}")
    
    # 智能评估
    evaluation = intelligent_evaluate(change_type, description)
    change["evaluation"] = evaluation
    
    # 审批决策
    must_manual = level_config["must_manual"]
    auto_threshold = level_config["auto_threshold"]
    total_score = evaluation.get("total_score", 0)
    
    if must_manual:
        decision = "manual"
        decision_reason = f"{auto_level}级变更必须人工审批"
    elif total_score >= auto_threshold:
        decision = "auto_approve"
        decision_reason = f"评分{total_score}>={auto_threshold}，自动通过"
    else:
        decision = "manual"
        decision_reason = f"评分{total_score}<{auto_threshold}，需人工审批"
    
    change["decision"] = decision
    change["decision_reason"] = decision_reason
    
    if decision == "auto_approve":
        # 自动执行
        log(f"自动通过: {change_id} | {decision_reason}")
        return execute_change(change)
    else:
        # 人工审批 - 发送飞书卡片
        log(f"人工审批: {change_id} | {decision_reason}")
        send_approval_card(change)
        
        # 保存待审批
        pending_dir = f"{BASE_DIR}/queue/pending_changes"
        os.makedirs(pending_dir, exist_ok=True)
        with open(f"{pending_dir}/{change_id}.json", "w") as f:
            json.dump(change, f, ensure_ascii=False, indent=2)
        
        return {
            "status": "pending_approval",
            "change_id": change_id,
            "level": auto_level,
            "message": f"{auto_level}级变更已提交，等待人工审批。编号: {change_id}",
            "evaluation": evaluation
        }

def send_approval_card(change):
    """发送飞书审批卡片"""
    try:
        import urllib.request
        level = change["level"]
        colors = {"P0": "red", "P1": "orange", "P2": "yellow", "P3": "blue", "P4": "green"}
        color = colors.get(level, "grey")
        
        scores = change.get("evaluation", {}).get("scores", {})
        score_text = "\n".join([f"  {k}: {v}" for k, v in scores.items()])
        
        card = {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": f"🔄 变更审批 [{level}] {change['level_name']}"},
                "template": color
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**变更编号**: `{change['change_id']}`\n**变更级别**: {level} - {change['level_name']}\n**风险等级**: {change['risk']}\n**变更描述**: {change['description']}"
                    }
                },
                {"tag": "hr"},
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**五方智能体评分**:\n{score_text}\n**综合评分**: {change.get('evaluation', {}).get('total_score', 0)}/100"
                    }
                },
                {"tag": "hr"},
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": "✅ 批准执行"},
                            "type": "primary",
                            "value": {"action": "approve_change", "change_id": change["change_id"]}
                        },
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": "❌ 拒绝"},
                            "type": "danger",
                            "value": {"action": "reject_change", "change_id": change["change_id"]}
                        }
                    ]
                },
                {
                    "tag": "note",
                    "elements": [
                        {"tag": "plain_text", "content": f"Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | MR-080变更管控 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"}
                    ]
                }
            ]
        }
        
        data = json.dumps({
            "receive_id": CHAT_ID,
            "msg_type": "interactive",
            "content": json.dumps(card)
        }).encode()
        req = urllib.request.Request(
            "http://127.0.0.1:8001/feishu/im/v1/messages?receive_id_type=chat_id",
            data=data,
            headers={"Content-Type": "application/json"}
        )
        urllib.request.urlopen(req, timeout=10)
        log(f"飞书审批卡片已发送: {change['change_id']}")
    except Exception as e:
        log(f"发飞书卡片失败: {e}", "WARN")
        send_feishu(f"🔄 变更审批申请\n编号: {change['change_id']}\n级别: {change['level']}\n描述: {change['description']}\n\n请回复 批准/拒绝")

def execute_change(change):
    """执行变更"""
    change_id = change["change_id"]
    log(f"执行变更: {change_id}")
    
    # 备份
    if change.get("file_path") and os.path.exists(change["file_path"]):
        backup_dir = f"{BASE_DIR}/backups/change_{change_id}"
        os.makedirs(backup_dir, exist_ok=True)
        subprocess.run(["cp", change["file_path"], f"{backup_dir}/"])
    
    # 执行命令
    if change.get("execution_cmd"):
        result = subprocess.run(change["execution_cmd"], shell=True, capture_output=True, text=True, timeout=300)
        change["execution_result"] = {
            "returncode": result.returncode,
            "stdout": result.stdout[-500:],
            "stderr": result.stderr[-500:]
        }
    
    change["status"] = "executed"
    change["executed_at"] = datetime.now().isoformat()
    
    # 归档
    executed_dir = f"{BASE_DIR}/queue/executed_changes"
    os.makedirs(executed_dir, exist_ok=True)
    with open(f"{executed_dir}/{change_id}.json", "w") as f:
        json.dump(change, f, ensure_ascii=False, indent=2)
    
    send_feishu(f"✅ 变更已执行\n编号: {change_id}\n级别: {change['level']}\n描述: {change['description']}\n\nΩ₀⊂⊙∞⊂Ω | DID-BR-000002")
    
    return {"status": "executed", "change_id": change_id, "message": "变更已执行"}

def approve_change(change_id):
    """批准变更"""
    pending_file = f"{BASE_DIR}/queue/pending_changes/{change_id}.json"
    if not os.path.exists(pending_file):
        return {"status": "error", "message": f"未找到变更: {change_id}"}
    
    with open(pending_file) as f:
        change = json.load(f)
    
    os.remove(pending_file)
    return execute_change(change)

def reject_change(change_id, reason=""):
    """拒绝变更"""
    pending_file = f"{BASE_DIR}/queue/pending_changes/{change_id}.json"
    if not os.path.exists(pending_file):
        return {"status": "error", "message": f"未找到变更: {change_id}"}
    
    with open(pending_file) as f:
        change = json.load(f)
    
    change["status"] = "rejected"
    change["rejected_at"] = datetime.now().isoformat()
    change["reject_reason"] = reason
    
    rejected_dir = f"{BASE_DIR}/queue/rejected_changes"
    os.makedirs(rejected_dir, exist_ok=True)
    with open(f"{rejected_dir}/{change_id}.json", "w") as f:
        json.dump(change, f, ensure_ascii=False, indent=2)
    
    os.remove(pending_file)
    send_feishu(f"❌ 变更已拒绝\n编号: {change_id}\n描述: {change['description']}\n原因: {reason or '未说明'}")
    
    return {"status": "rejected", "change_id": change_id}

def lockdown_all():
    """执行全域锁定"""
    log("开始全域锁定...")
    results = {"locked": [], "failed": [], "skipped": []}
    
    all_files = []
    for category, files in LOCKDOWN_FILES.items():
        all_files.extend(files)
    
    for filepath in all_files:
        if filepath in NEVER_LOCK:
            results["skipped"].append(filepath)
            continue
        
        if os.path.exists(filepath):
            try:
                subprocess.run(["chattr", "+i", filepath], capture_output=True, timeout=5)
                # 验证
                result = subprocess.run(["lsattr", filepath], capture_output=True, text=True)
                if "i" in result.stdout:
                    results["locked"].append(filepath)
                    log(f"  已锁定: {filepath}")
                else:
                    results["failed"].append(filepath)
            except Exception as e:
                results["failed"].append(filepath)
                log(f"  锁定失败: {filepath} - {e}", "WARN")
        else:
            results["skipped"].append(filepath)
    
    # 更新chattr白名单
    whitelist_path = f"{BASE_DIR}/config/chattr_whitelist.json"
    if os.path.exists(whitelist_path):
        subprocess.run(["chattr", "-i", whitelist_path], capture_output=True)
        with open(whitelist_path) as f:
            whitelist = json.load(f)
        
        current = set(whitelist.get("allowed_files", []))
        for f in results["locked"]:
            current.add(f)
        whitelist["allowed_files"] = list(current)
        whitelist["never_lock"] = NEVER_LOCK
        
        with open(whitelist_path, "w") as f:
            json.dump(whitelist, f, ensure_ascii=False, indent=2)
        subprocess.run(["chattr", "+i", whitelist_path], capture_output=True)
    
    log(f"全域锁定完成: 锁定{len(results['locked'])}个, 失败{len(results['failed'])}个, 跳过{len(results['skipped'])}个")
    return results

def show_lockdown_status():
    """显示锁定状态"""
    print("\n" + "=" * 70)
    print("  全域锁定状态")
    print("=" * 70)
    
    all_files = []
    for category, files in LOCKDOWN_FILES.items():
        all_files.extend(files)
    
    locked = 0
    unlocked = 0
    missing = 0
    
    for filepath in all_files:
        if os.path.exists(filepath):
            result = subprocess.run(["lsattr", filepath], capture_output=True, text=True)
            if "i" in result.stdout:
                locked += 1
                print(f"  🔒 {filepath}")
            else:
                unlocked += 1
                print(f"  🔓 {filepath}")
        else:
            missing += 1
    
    print(f"\n  统计: 已锁定{locked}个, 未锁定{unlocked}个, 不存在{missing}个")
    print("=" * 70)

def main():
    import argparse
    parser = argparse.ArgumentParser(description="全域变更管控系统")
    parser.add_argument("command", choices=["submit", "approve", "reject", "list", "lockdown", "status", "levels"])
    parser.add_argument("--type", help="变更类型")
    parser.add_argument("--desc", help="变更描述")
    parser.add_argument("--cmd", help="执行命令")
    parser.add_argument("--file", help="目标文件")
    parser.add_argument("--change-id", help="变更编号")
    parser.add_argument("--reason", help="拒绝原因")
    
    args = parser.parse_args()
    
    if args.command == "submit":
        if not args.desc:
            print("错误: 需要 --desc 参数")
            return
        result = submit_change(args.type or "general", args.desc, args.cmd or "", args.file or "")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    elif args.command == "approve":
        if not args.change_id:
            print("错误: 需要 --change-id 参数")
            return
        result = approve_change(args.change_id)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    elif args.command == "reject":
        if not args.change_id:
            print("错误: 需要 --change-id 参数")
            return
        result = reject_change(args.change_id, args.reason or "")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    elif args.command == "list":
        pending_dir = f"{BASE_DIR}/queue/pending_changes"
        if os.path.exists(pending_dir):
            pending = os.listdir(pending_dir)
            print(f"待审批变更: {len(pending)}个")
            for f in pending:
                if f.endswith(".json"):
                    with open(f"{pending_dir}/{f}") as fp:
                        c = json.load(fp)
                        print(f"  {c['change_id']} | {c['level']} | {c['description'][:50]}")
    
    elif args.command == "lockdown":
        results = lockdown_all()
        print(f"\n锁定结果: 成功{len(results['locked'])}个, 失败{len(results['failed'])}个, 跳过{len(results['skipped'])}个")
    
    elif args.command == "status":
        show_lockdown_status()
    
    elif args.command == "levels":
        print("\n变更分级规范:")
        for level, config in CHANGE_LEVELS.items():
            print(f"\n  {level} - {config['name']} (风险:{config['risk']})")
            print(f"    必须人工审批: {'是' if config['must_manual'] else '否'}")
            print(f"    自动通过阈值: {config['auto_threshold']}分")
            print(f"    典型场景:")
            for ex in config["examples"][:5]:
                print(f"      - {ex}")

if __name__ == "__main__":
    main()
