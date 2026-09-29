#!/usr/bin/env python3
"""
端口变更审批系统 - 接入飞书审批流程
功能：端口变更申请 → 五方智能体仲裁 → 飞书交互卡片审批 → 审批通过自动执行
依据：MR-079端口安全固化与人工审核元法则 + MR-068智能审批方法论
"""
import os
import sys
import json
import time
import hashlib
import subprocess
from datetime import datetime

BASE_DIR = "/opt/ZONGYUAN-ROOT"
QUEUE_DIR = f"{BASE_DIR}/queue"
LOG_FILE = f"{BASE_DIR}/logs/port_approval.log"
CHAT_ID = "oc_1c68eb3664e751e397062ff0c60ffa3"

# 公网端口白名单（MR-079定义）
PUBLIC_WHITELIST = [22, 80, 443, 2222, 7100, 9120, 9122, 9125, 9151]

def log(msg, level="INFO"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{level}] {msg}"
    print(line)
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def send_feishu_text(text):
    """发送飞书文本消息"""
    try:
        sys.path.insert(0, f"{BASE_DIR}/scripts")
        from feishu_media_archive_bot import send_text
        send_text(CHAT_ID, text)
    except Exception as e:
        log(f"发飞书失败: {e}", "WARN")

def send_feishu_card(card_content):
    """发送飞书交互卡片"""
    try:
        import urllib.request
        data = json.dumps({
            "receive_id": CHAT_ID,
            "msg_type": "interactive",
            "content": json.dumps(card_content)
        }).encode()
        req = urllib.request.Request(
            "http://127.0.0.1:8001/feishu/im/v1/messages?receive_id_type=chat_id",
            data=data,
            headers={"Content-Type": "application/json"}
        )
        response = urllib.request.urlopen(req, timeout=10)
        return json.loads(response.read())
    except Exception as e:
        log(f"发飞书卡片失败: {e}", "WARN")
        return None

def intelligent_evaluate(operation):
    """调用智能审批引擎进行五方仲裁评分"""
    try:
        sys.path.insert(0, f"{BASE_DIR}/scripts")
        from intelligent_approval_engine import (
            security_score, stability_score, cost_score, 
            value_score, compliance_score, AGENT_WEIGHTS, APPROVAL_MATRIX
        )
        
        op = {
            "type": "security",
            "description": operation["description"],
            "params": operation
        }
        
        scores = {
            "security": security_score(op),
            "stability": stability_score(op),
            "cost": cost_score(op),
            "value": value_score(op),
            "compliance": compliance_score(op)
        }
        
        total = sum(scores[k] * AGENT_WEIGHTS[k] for k in AGENT_WEIGHTS)
        
        matrix = APPROVAL_MATRIX.get("security", {})
        must_manual = matrix.get("must_manual", True)
        auto_threshold = matrix.get("auto_threshold", 100)
        manual_threshold = matrix.get("manual_threshold", 90)
        
        return {
            "scores": scores,
            "total_score": round(total, 1),
            "must_manual": must_manual,
            "auto_threshold": auto_threshold,
            "manual_threshold": manual_threshold,
            "decision": "manual" if must_manual else ("auto" if total >= auto_threshold else "manual" if total >= manual_threshold else "reject")
        }
    except Exception as e:
        log(f"智能评估失败: {e}，默认人工审批")
        return {
            "scores": {},
            "total_score": 0,
            "must_manual": True,
            "decision": "manual"
        }

def build_approval_card(operation, evaluation):
    """构建飞书审批交互卡片"""
    op_id = operation["op_id"]
    port = operation["port"]
    action = operation["action"]
    action_text = {"open": "开放公网", "close": "关闭公网", "modify": "修改配置"}.get(action, action)
    
    scores = evaluation.get("scores", {})
    score_text = "\n".join([f"  {k}: {v}" for k, v in scores.items()])
    
    card = {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": f"🔒 端口变更审批 - {action_text} {port}"},
            "template": "red"
        },
        "elements": [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**申请编号**: `{op_id}`\n**变更类型**: {action_text}\n**目标端口**: {port}\n**申请原因**: {operation.get('reason', '未说明')}\n**风险评估**: {operation.get('risk_assessment', '未评估')}"
                }
            },
            {"tag": "hr"},
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**五方智能体仲裁评分**:\n{score_text}\n**综合评分**: {evaluation.get('total_score', 0)}/100\n**审批类型**: 必须人工审批（安全策略变更）"
                }
            },
            {"tag": "hr"},
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**执行计划**:\n{operation.get('execution_plan', '未提供')}\n\n**回滚方案**: 自动备份iptables规则，可一键回滚"
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
                        "value": {"action": "approve", "op_id": op_id}
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "❌ 拒绝"},
                        "type": "danger",
                        "value": {"action": "reject", "op_id": op_id}
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "⏸️ 暂缓"},
                        "type": "default",
                        "value": {"action": "pending", "op_id": op_id}
                    }
                ]
            },
            {
                "tag": "note",
                "elements": [
                    {"tag": "plain_text", "content": f"Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | MR-079端口安全元法则 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"}
                ]
            }
        ]
    }
    return card

def submit_port_change(port, action, reason, risk_assessment="", execution_plan=""):
    """提交端口变更申请"""
    op_id = f"PORT-{hashlib.md5(f'{port}{action}{time.time()}'.encode()).hexdigest()[:8].upper()}"
    
    operation = {
        "op_id": op_id,
        "port": port,
        "action": action,
        "reason": reason,
        "risk_assessment": risk_assessment,
        "execution_plan": execution_plan or f"1. 备份当前iptables规则\n2. {'开放' if action == 'open' else '关闭'}端口{port}\n3. 验证服务可用性\n4. 更新端口台账\n5. 写入审计日志",
        "description": f"端口变更: {action}端口{port}, 原因: {reason}",
        "submitted_at": datetime.now().isoformat(),
        "status": "pending_approval"
    }
    
    # 智能评估
    log(f"提交端口变更申请: {op_id} | {action}端口{port}")
    evaluation = intelligent_evaluate(operation)
    operation["evaluation"] = evaluation
    
    log(f"智能评估完成: 综合评分{evaluation.get('total_score', 0)}/100, 决策: {evaluation.get('decision')}")
    
    # 安全策略变更必须人工审批
    if evaluation.get("must_manual", True):
        log("安全策略变更，必须人工审批，发送飞书审批卡片")
        
        card = build_approval_card(operation, evaluation)
        result = send_feishu_card(card)
        
        if result:
            log(f"飞书审批卡片已发送: {result}")
        else:
            log("飞书卡片发送失败，改用文本消息通知")
            send_feishu_text(f"🔒 端口变更审批申请\n编号: {op_id}\n操作: {action}端口{port}\n原因: {reason}\n\n请回复 批准/拒绝 进行审批")
        
        # 保存待审批申请
        pending_dir = f"{QUEUE_DIR}/pending_approval"
        os.makedirs(pending_dir, exist_ok=True)
        with open(f"{pending_dir}/{op_id}.json", "w") as f:
            json.dump(operation, f, ensure_ascii=False, indent=2)
        
        return {
            "status": "pending_approval",
            "op_id": op_id,
            "message": f"申请已提交，等待人工审批。审批编号: {op_id}",
            "evaluation": evaluation
        }
    else:
        # 自动通过（安全策略变更不会走到这里）
        return execute_port_change(operation)

def execute_port_change(operation):
    """执行端口变更"""
    op_id = operation["op_id"]
    port = operation["port"]
    action = operation["action"]
    
    log(f"执行端口变更: {op_id} | {action}端口{port}")
    
    # 1. 备份当前规则
    backup_file = f"{BASE_DIR}/backups/port_change_{op_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.rules"
    os.makedirs(os.path.dirname(backup_file), exist_ok=True)
    subprocess.run(["iptables-save"], stdout=open(backup_file, "w"))
    log(f"已备份iptables规则: {backup_file}")
    
    # 2. 执行变更
    if action == "open":
        # 从PORT_HARDENING链中删除该端口的DROP规则
        subprocess.run(f"iptables -D PORT_HARDENING -p tcp --dport {port} -j DROP", shell=True, capture_output=True)
        log(f"已开放端口: {port}")
    elif action == "close":
        # 添加DROP规则
        subprocess.run(f"iptables -I PORT_HARDENING 4 -p tcp --dport {port} -j DROP", shell=True, capture_output=True)
        log(f"已关闭端口: {port}")
    
    # 3. 保存规则
    subprocess.run(["iptables-save"], stdout=open(f"{BASE_DIR}/config/iptables_rules.rules", "w"))
    
    # 4. 更新端口台账
    subprocess.run(["python3", f"{BASE_DIR}/scripts/port_ledger.py", "scan"], capture_output=True)
    
    # 5. 记录审计日志
    operation["status"] = "executed"
    operation["executed_at"] = datetime.now().isoformat()
    operation["backup_file"] = backup_file
    
    audit_dir = f"{BASE_DIR}/queue/executed"
    os.makedirs(audit_dir, exist_ok=True)
    with open(f"{audit_dir}/{op_id}.json", "w") as f:
        json.dump(operation, f, ensure_ascii=False, indent=2)
    
    # 6. 通知
    send_feishu_text(f"✅ 端口变更已执行\n编号: {op_id}\n操作: {action}端口{port}\n备份: {backup_file}\n\nΩ₀⊂⊙∞⊂Ω | DID-BR-000002")
    
    return {
        "status": "executed",
        "op_id": op_id,
        "message": f"端口变更已执行: {action}端口{port}",
        "backup_file": backup_file
    }

def approve_operation(op_id):
    """批准并执行端口变更"""
    pending_file = f"{QUEUE_DIR}/pending_approval/{op_id}.json"
    if not os.path.exists(pending_file):
        return {"status": "error", "message": f"未找到审批申请: {op_id}"}
    
    with open(pending_file) as f:
        operation = json.load(f)
    
    # 移动到已批准
    os.remove(pending_file)
    result = execute_port_change(operation)
    return result

def reject_operation(op_id, reason=""):
    """拒绝端口变更"""
    pending_file = f"{QUEUE_DIR}/pending_approval/{op_id}.json"
    if not os.path.exists(pending_file):
        return {"status": "error", "message": f"未找到审批申请: {op_id}"}
    
    with open(pending_file) as f:
        operation = json.load(f)
    
    operation["status"] = "rejected"
    operation["rejected_at"] = datetime.now().isoformat()
    operation["reject_reason"] = reason
    
    rejected_dir = f"{QUEUE_DIR}/rejected"
    os.makedirs(rejected_dir, exist_ok=True)
    with open(f"{rejected_dir}/{op_id}.json", "w") as f:
        json.dump(operation, f, ensure_ascii=False, indent=2)
    
    os.remove(pending_file)
    
    send_feishu_text(f"❌ 端口变更已拒绝\n编号: {op_id}\n端口: {operation['port']}\n原因: {reason or '未说明'}\n\nΩ₀⊂⊙∞⊂Ω | DID-BR-000002")
    
    return {"status": "rejected", "op_id": op_id}

def list_pending():
    """列出待审批申请"""
    pending_dir = f"{QUEUE_DIR}/pending_approval"
    if not os.path.exists(pending_dir):
        return []
    
    pending = []
    for f in os.listdir(pending_dir):
        if f.endswith(".json"):
            with open(f"{pending_dir}/{f}") as fp:
                pending.append(json.load(fp))
    return pending

def main():
    import argparse
    parser = argparse.ArgumentParser(description="端口变更审批系统")
    parser.add_argument("command", choices=["submit", "approve", "reject", "list", "status"], help="命令")
    parser.add_argument("--port", type=int, help="端口号")
    parser.add_argument("--action", choices=["open", "close", "modify"], help="操作类型")
    parser.add_argument("--reason", help="变更原因")
    parser.add_argument("--op-id", help="审批编号")
    parser.add_argument("--risk", help="风险评估")
    
    args = parser.parse_args()
    
    if args.command == "submit":
        if not all([args.port, args.action, args.reason]):
            print("错误: submit需要 --port --action --reason 参数")
            print("示例: python3 port_change_approval.py submit --port 8080 --action open --reason '新服务部署'")
            return
        
        result = submit_port_change(args.port, args.action, args.reason, args.risk or "")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    elif args.command == "approve":
        if not args.op_id:
            print("错误: approve需要 --op-id 参数")
            return
        result = approve_operation(args.op_id)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    elif args.command == "reject":
        if not args.op_id:
            print("错误: reject需要 --op-id 参数")
            return
        result = reject_operation(args.op_id, args.reason or "")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    elif args.command == "list":
        pending = list_pending()
        print(f"待审批申请: {len(pending)}个")
        for op in pending:
            print(f"  {op['op_id']} | {op['action']}端口{op['port']} | {op['reason']}")
    
    elif args.command == "status":
        pending = list_pending()
        print(f"端口变更审批系统状态:")
        print(f"  待审批: {len(pending)}个")
        print(f"  公网白名单: {PUBLIC_WHITELIST}")
        print(f"  日志: {LOG_FILE}")

if __name__ == "__main__":
    main()
