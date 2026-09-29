#!/usr/bin/env python3
"""
多智能体辩论决策引擎
三角色议会制：乐观派(利益最大化) / 保守派(风险最小化) / 中立派(成本最优)
七维公式仲裁，输出最优决策
确权: DID-BR-000002 | 溯源: Ω₀⊂⊙∞⊂Ω
零成本模式：默认使用本地LLM(8081)，增强模式可切换AI代理(8021)
"""
import json
import os
import sys
import urllib.request
from datetime import datetime

BASE = "/opt/ZONGYUAN-ROOT"
LOG_FILE = os.path.join(BASE, "logs/multi_agent_debate.log")
HISTORY_FILE = os.path.join(BASE, "data/debate_history.json")

# 端点
LOCAL_LLM = "http://127.0.0.1:8081/v1/chat/completions"
AI_PROXY = "http://127.0.0.1:8021/v1/chat/completions"
DECISION_ENGINE = "http://127.0.0.1:8180/evaluate"

# 三角色定义
AGENTS = {
    "optimist": {
        "name": "乐观派",
        "role": "利益最大化倡导者",
        "system_prompt": "你是乐观派分析师。你专注于机会、增长潜力和收益最大化。你倾向于看到事物的积极面，强调上行空间和战略价值。请用简洁的要点列出支持该决策的核心理由（不超过200字）。",
        "bias": {"benefit": 0.35, "risk": 0.10, "cost": 0.10, "time_value": 0.20, "entropy": 0.10, "antifragility": 0.10, "reversibility": 0.05}
    },
    "pessimist": {
        "name": "保守派",
        "role": "风险最小化守护者",
        "system_prompt": "你是保守派分析师。你专注于风险、隐患和下行保护。你倾向于看到事物的潜在危险，强调安全边际和风险控制。请用简洁的要点列出反对该决策的核心理由（不超过200字）。",
        "bias": {"benefit": 0.10, "risk": 0.35, "cost": 0.15, "time_value": 0.10, "entropy": 0.15, "antifragility": 0.10, "reversibility": 0.05}
    },
    "centrist": {
        "name": "中立派",
        "role": "成本最优平衡者",
        "system_prompt": "你是中立派分析师。你专注于成本效益、资源效率和务实平衡。你在机会和风险之间寻找最优平衡点，强调投入产出比和可执行性。请用简洁的要点给出你的平衡建议（不超过200字）。",
        "bias": {"benefit": 0.20, "risk": 0.20, "cost": 0.25, "time_value": 0.15, "entropy": 0.08, "antifragility": 0.07, "reversibility": 0.05}
    }
}

def log(msg):
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, 'a') as f:
        f.write("[%s] %s\n" % (ts, msg))

def call_llm(system_prompt, user_message, use_local=True):
    """调用LLM生成论证"""
    url = LOCAL_LLM if use_local else AI_PROXY
    model = "qwen2.5-0.5b" if use_local else "doubao"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        "max_tokens": 300,
        "temperature": 0.7
    }
    try:
        req = urllib.request.Request(
            url, data=json.dumps(payload).encode(),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            result = json.loads(r.read())
            return result["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return "论证生成失败: %s" % str(e)

def evaluate_with_bias(decision, bias):
    """用角色偏差权重评估决策（本地加权计算）"""
    total_w = sum(bias.values())
    normalized = {k: v / total_w for k, v in bias.items()}
    score = sum(decision.get(k, 50) * normalized.get(k, 0) for k in normalized)
    score = round(score, 2)
    recommendation = "通过" if score >= 60 else "不通过"
    return {"score": score, "recommendation": recommendation}

def run_debate(question, decision_scores, use_local=True):
    """
    执行一次完整辩论
    question: 决策问题描述
    decision_scores: dict, 七维评分 {benefit, risk, cost, time_value, entropy, antifragility, reversibility}
    """
    log("=" * 50)
    log("辩论开始: %s" % question)
    
    results = {}
    for agent_id, agent in AGENTS.items():
        log("【%s】生成论证..." % agent["name"])
        argument = call_llm(agent["system_prompt"], "决策问题: %s\n七维评分: %s" % (question, json.dumps(decision_scores, ensure_ascii=False)), use_local)
        evaluation = evaluate_with_bias(decision_scores, agent["bias"])
        results[agent_id] = {
            "name": agent["name"],
            "role": agent["role"],
            "argument": argument,
            "biased_score": evaluation.get("score", 0),
            "recommendation": evaluation.get("recommendation", "")
        }
        log("  评分: %.2f, 结论: %s" % (results[agent_id]["biased_score"], results[agent_id]["recommendation"]))
    
    # 仲裁：用标准七维权重重新评估
    log("【仲裁】七维公式标准评估...")
    final_eval = evaluate_with_bias(decision_scores, {
        "benefit": 0.25, "risk": 0.20, "cost": 0.15, "time_value": 0.15,
        "entropy": 0.10, "antifragility": 0.10, "reversibility": 0.05
    })
    
    # 综合三角色意见
    avg_score = sum(r["biased_score"] for r in results.values()) / 3
    verdict = {
        "question": question,
        "timestamp": datetime.now().isoformat(),
        "agents": results,
        "arbitration": {
            "standard_score": final_eval.get("score", 0),
            "average_agent_score": round(avg_score, 2),
            "final_recommendation": final_eval.get("recommendation", ""),
            "consensus": "一致通过" if all(r["biased_score"] >= 60 for r in results.values()) else 
                        "多数通过" if sum(1 for r in results.values() if r["biased_score"] >= 60) >= 2 else
                        "存在分歧，需人工终审"
        }
    }
    
    log("仲裁结果: 标准分%.2f, 代理均分%.2f, %s" % (
        verdict["arbitration"]["standard_score"],
        verdict["arbitration"]["average_agent_score"],
        verdict["arbitration"]["consensus"]
    ))
    
    # 保存历史
    history = []
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE) as f:
            history = json.load(f)
    history.append(verdict)
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
    
    log("辩论完成，已归档")
    log("=" * 50)
    return verdict

if __name__ == '__main__':
    if len(sys.argv) >= 2:
        question = sys.argv[1]
        # 默认评分
        scores = {"benefit": 70, "risk": 30, "cost": 40, "time_value": 70, "entropy": 40, "antifragility": 60, "reversibility": 70}
        if len(sys.argv) >= 3:
            try:
                scores = json.loads(sys.argv[2])
            except:
                pass
        result = run_debate(question, scores, use_local=True)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("用法: python3 multi_agent_debate.py \"决策问题\" '{\"benefit\":70,\"risk\":30,...}'")
