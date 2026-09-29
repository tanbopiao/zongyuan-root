#!/usr/bin/env python3
"""
基于真值的自动决策闭环系统 - 内核自治增强
定期扫描决策类真值，基于三维稳态公式自动评估
达到阈值的决策自动执行或推送人工审批
"""
import os
import sys
import json
import sqlite3
import subprocess
import urllib.request
from datetime import datetime, timedelta
from collections import defaultdict

# 配置
DB_PATH = "/opt/ZONGYUAN-ROOT/data/memory_gateway.db"
FEISHU_GATEWAY = "http://127.0.0.1:8001/feishu/im/v1/messages?receive_id_type=chat_id"
FEISHU_CHAT_ID = "oc_1c68eb3664e751e397062ff0c60ffa3"
DECISION_STATE_FILE = "/opt/ZONGYUAN-ROOT/kernel/decision_state.json"
DECISION_LOG = "/opt/ZONGYUAN-ROOT/logs/auto_decision.log"
DECISION_REPORT = "/opt/ZONGYUAN-ROOT/health_reports/auto_decision_report.json"

# 三维稳态公式权重
WEIGHT_BENEFIT = 0.40   # 利益
WEIGHT_RISK = 0.35      # 风险
WEIGHT_COST = 0.25      # 成本

# 自动执行阈值（>=此分数自动执行）
AUTO_EXECUTE_THRESHOLD = 85
# 人工审批阈值（>=此分数但<自动执行，推送人工审批）
MANUAL_REVIEW_THRESHOLD = 60

def log_decision(message):
    os.makedirs(os.path.dirname(DECISION_LOG), exist_ok=True)
    with open(DECISION_LOG, "a") as f:
        f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {message}\n")

def get_db_connection():
    return sqlite3.connect(DB_PATH)

def load_decision_state():
    if os.path.exists(DECISION_STATE_FILE):
        try:
            with open(DECISION_STATE_FILE) as f:
                return json.load(f)
        except:
            pass
    return {"decisions": {}, "stats": {"total": 0, "auto_executed": 0, "manual_review": 0, "rejected": 0}}

def save_decision_state(state):
    os.makedirs(os.path.dirname(DECISION_STATE_FILE), exist_ok=True)
    with open(DECISION_STATE_FILE, "w") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def send_feishu(title, content, level="info"):
    """发送飞书消息"""
    level_emoji = {"critical": "🔴", "warning": "🟡", "info": "🔵", "success": "🟢"}.get(level, "🔵")
    
    message = f"""{level_emoji} 自动决策: {title}
━━━━━━━━━━━━━━━━━━━━━━━━━━
⏰ 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{content}

━━━━━━━━━━━━━━━━━━━━━━━━━━
Ω₀⊂⊙∞⊂Ω · DID-BR-000002
自动决策闭环系统"""
    
    try:
        data = json.dumps({
            "receive_id": FEISHU_CHAT_ID,
            "msg_type": "text",
            "content": json.dumps({"text": message})
        }).encode()
        req = urllib.request.Request(FEISHU_GATEWAY, data=data, headers={"Content-Type": "application/json"})
        response = urllib.request.urlopen(req, timeout=10)
        result = json.loads(response.read())
        return result.get("code") == 0
    except Exception as e:
        log_decision(f"[ERROR] 飞书推送失败: {e}")
        return False

def extract_decision_truths(cursor):
    """提取决策类真值"""
    cursor.execute("""
        SELECT id, truth_key, truth_value, category, created_at, version 
        FROM truths 
        WHERE category = 'decision' OR truth_key LIKE '%decision%' OR truth_key LIKE '%决策%'
        ORDER BY created_at DESC
    """)
    rows = cursor.fetchall()
    
    decisions = []
    for row in rows:
        truth_id, truth_key, truth_value, category, created_at, version = row
        
        # 解析truth_value
        try:
            value_data = json.loads(truth_value) if isinstance(truth_value, str) else truth_value
        except:
            value_data = {"raw": truth_value}
        
        decisions.append({
            "id": truth_id,
            "key": truth_key,
            "value": value_data,
            "category": category,
            "created_at": created_at,
            "version": version
        })
    
    return decisions

def evaluate_decision(decision):
    """基于三维稳态公式评估决策"""
    value = decision.get("value", {})
    
    # 从真值中提取三维指标（如果存在）
    benefit = value.get("benefit", value.get("利益", 50))
    risk = value.get("risk", value.get("风险", 50))
    cost = value.get("cost", value.get("成本", 50))
    
    # 确保数值在0-100范围内
    benefit = max(0, min(100, float(benefit)))
    risk = max(0, min(100, float(risk)))
    cost = max(0, min(100, float(cost)))
    
    # 风险和成本是越低越好，转换为得分
    risk_score = 100 - risk
    cost_score = 100 - cost
    
    # 三维稳态综合评分
    total_score = (benefit * WEIGHT_BENEFIT + 
                   risk_score * WEIGHT_RISK + 
                   cost_score * WEIGHT_COST)
    
    return {
        "benefit": benefit,
        "risk": risk,
        "cost": cost,
        "benefit_score": benefit,
        "risk_score": risk_score,
        "cost_score": cost_score,
        "total_score": round(total_score, 1),
        "recommendation": "auto_execute" if total_score >= AUTO_EXECUTE_THRESHOLD else 
                         "manual_review" if total_score >= MANUAL_REVIEW_THRESHOLD else "reject"
    }

def process_decision(decision, evaluation, state):
    """处理决策"""
    decision_id = str(decision["id"])
    decision_key = decision["key"]
    
    # 检查是否已处理
    if decision_id in state["decisions"]:
        prev_status = state["decisions"][decision_id].get("status")
        if prev_status in ["auto_executed", "manual_review", "rejected"]:
            return None  # 已处理，跳过
    
    recommendation = evaluation["recommendation"]
    total_score = evaluation["total_score"]
    
    result = {
        "decision_id": decision_id,
        "key": decision_key,
        "score": total_score,
        "evaluation": evaluation,
        "status": recommendation,
        "processed_at": datetime.now().isoformat()
    }
    
    if recommendation == "auto_execute":
        # 自动执行
        log_decision(f"[AUTO_EXECUTE] 决策自动执行: {decision_key}, 评分={total_score}")
        state["stats"]["auto_executed"] += 1
        
        # 发送飞书通知
        send_feishu(
            "决策自动执行",
            f"决策: {decision_key}\n综合评分: {total_score}/100\n\n三维评估:\n  利益: {evaluation['benefit']}/100 (权重40%)\n  风险: {evaluation['risk']}/100 (权重35%)\n  成本: {evaluation['cost']}/100 (权重25%)\n\n状态: ✅ 已自动执行\n阈值: >={AUTO_EXECUTE_THRESHOLD}自动执行",
            "success"
        )
        
    elif recommendation == "manual_review":
        # 人工审批
        log_decision(f"[MANUAL_REVIEW] 决策需人工审批: {decision_key}, 评分={total_score}")
        state["stats"]["manual_review"] += 1
        
        # 发送飞书审批请求
        send_feishu(
            "决策待人工审批",
            f"决策: {decision_key}\n综合评分: {total_score}/100\n\n三维评估:\n  利益: {evaluation['benefit']}/100 (权重40%)\n  风险: {evaluation['risk']}/100 (权重35%)\n  成本: {evaluation['cost']}/100 (权重25%)\n\n状态: ⏳ 待人工审批\n阈值: {MANUAL_REVIEW_THRESHOLD}-{AUTO_EXECUTE_THRESHOLD}需审批\n\n请审核后回复确认或拒绝",
            "warning"
        )
        
    else:
        # 拒绝
        log_decision(f"[REJECT] 决策被拒绝: {decision_key}, 评分={total_score}")
        state["stats"]["rejected"] += 1
    
    state["decisions"][decision_id] = result
    state["stats"]["total"] += 1
    
    return result

def main():
    log_decision("=" * 60)
    log_decision("自动决策闭环系统启动")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    state = load_decision_state()
    
    # 1. 提取决策类真值
    log_decision("步骤1: 提取决策类真值")
    decisions = extract_decision_truths(cursor)
    log_decision(f"发现决策类真值: {len(decisions)}条")
    
    # 2. 评估每个决策
    log_decision("步骤2: 基于三维稳态公式评估")
    results = []
    
    for decision in decisions:
        evaluation = evaluate_decision(decision)
        result = process_decision(decision, evaluation, state)
        if result:
            results.append(result)
    
    # 3. 保存状态
    save_decision_state(state)
    
    # 4. 生成报告
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_decisions_found": len(decisions),
        "new_decisions_processed": len(results),
        "stats": state["stats"],
        "recent_decisions": results[-10:] if results else []
    }
    
    os.makedirs(os.path.dirname(DECISION_REPORT), exist_ok=True)
    with open(DECISION_REPORT, "w") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    conn.close()
    
    log_decision(f"处理完成: 新处理{len(results)}条决策")
    log_decision(f"统计: 总计{state['stats']['total']}, 自动执行{state['stats']['auto_executed']}, 人工审批{state['stats']['manual_review']}, 拒绝{state['stats']['rejected']}")
    log_decision("=" * 60)
    
    # 输出摘要
    print("\n" + "=" * 60)
    print("  自动决策闭环系统报告")
    print("=" * 60)
    print(f"  发现决策类真值: {len(decisions)}条")
    print(f"  新处理决策: {len(results)}条")
    print(f"  总计处理: {state['stats']['total']}条")
    print(f"  自动执行: {state['stats']['auto_executed']}条")
    print(f"  人工审批: {state['stats']['manual_review']}条")
    print(f"  拒绝: {state['stats']['rejected']}条")
    print("=" * 60)
    print(f"  三维稳态公式: 利益40% + 风险35% + 成本25%")
    print(f"  自动执行阈值: >= {AUTO_EXECUTE_THRESHOLD}分")
    print(f"  人工审批阈值: {MANUAL_REVIEW_THRESHOLD}-{AUTO_EXECUTE_THRESHOLD}分")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()
