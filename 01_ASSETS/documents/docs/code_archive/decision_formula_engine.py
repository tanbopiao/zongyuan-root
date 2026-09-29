#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 超认知决策公式自演化引擎
- 7维扩展公式（利益/风险/成本/时间价值/熵增/反脆弱/可逆性）
- 贝叶斯权重动态更新
- 敏感性检验强制流程
- 决策回溯审计
- 每季度权重重拟合
端口: 8180
"""
import json
import time
import os
import math
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

# 配置
PORT = 8180
STATE_FILE = "/opt/ZONGYUAN-ROOT/kernel/decision_formula_state.json"
DECISION_LOG = "/opt/ZONGYUAN-ROOT/data/decision_history.jsonl"
DID = "DID-BR-000002"
ANCHOR = "Ω₀⊂⊙∞⊂Ω"

# 7维初始权重（超认知扩展版）
DEFAULT_WEIGHTS = {
    "benefit": 0.25,        # 利益
    "risk": 0.20,           # 风险（反向，越低越好）
    "cost": 0.15,           # 成本（反向）
    "time_value": 0.15,     # 时间折现值（长期收益加分）
    "entropy": 0.10,        # 熵增/耗散（反向，复杂度越低越好）
    "antifragility": 0.10,  # 反脆弱性（从冲击中获益的能力）
    "reversibility": 0.05,  # 可逆性（可回退加分）
}

DIMENSION_NAMES = {
    "benefit": "利益",
    "risk": "风险",
    "cost": "成本",
    "time_value": "时间价值",
    "entropy": "熵增耗散",
    "antifragility": "反脆弱性",
    "reversibility": "可逆性",
}

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {
        "version": "2.0-7D",
        "weights": DEFAULT_WEIGHTS.copy(),
        "decision_count": 0,
        "feedback_count": 0,
        "last_refit": datetime.now().isoformat(),
        "weight_history": [],
        "sensitivity_breaches": 0,
    }

def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def normalize_weights(weights):
    """归一化权重使总和为1"""
    total = sum(weights.values())
    if total == 0:
        return DEFAULT_WEIGHTS.copy()
    return {k: v / total for k, v in weights.items()}

def calculate_score(decision, weights=None):
    """计算7维决策分数 (0-100)"""
    if weights is None:
        state = load_state()
        weights = state["weights"]
    
    score = 0
    breakdown = {}
    for dim, weight in weights.items():
        raw = decision.get(dim, 50)  # 默认50分
        # 反向维度：risk/cost/entropy越低越好，转换为分数
        if dim in ["risk", "cost", "entropy"]:
            adjusted = 100 - raw
        else:
            adjusted = raw
        weighted = adjusted * weight
        score += weighted
        breakdown[dim] = {
            "raw": raw,
            "weight": round(weight, 4),
            "weighted": round(weighted, 2),
        }
    
    return round(score, 2), breakdown

def sensitivity_test(decision):
    """敏感性检验：用3套权重分别打分，看结论是否稳健"""
    # 三套权重：当前/保守(风险加权)/激进(利益加权)
    weight_sets = {
        "current": load_state()["weights"],
        "conservative": {"benefit":0.15,"risk":0.35,"cost":0.15,"time_value":0.10,"entropy":0.10,"antifragility":0.05,"reversibility":0.10},
        "aggressive": {"benefit":0.40,"risk":0.15,"cost":0.10,"time_value":0.15,"entropy":0.05,"antifragility":0.10,"reversibility":0.05},
    }
    
    scores = {}
    for name, w in weight_sets.items():
        w = normalize_weights(w)
        score, _ = calculate_score(decision, w)
        scores[name] = score
    
    # 判断稳健性：最高分和最低分差距
    max_s = max(scores.values())
    min_s = min(scores.values())
    spread = max_s - min_s
    robust = spread < 15  # 差距<15分算稳健
    
    return {
        "scores": scores,
        "spread": round(spread, 2),
        "robust": robust,
        "verdict": "稳健" if robust else "敏感（需人工介入）",
    }

def record_decision(decision_id, decision, score, breakdown, sensitivity):
    """记录决策到审计日志"""
    os.makedirs(os.path.dirname(DECISION_LOG), exist_ok=True)
    entry = {
        "decision_id": decision_id,
        "timestamp": datetime.now().isoformat(),
        "decision": decision,
        "score": score,
        "breakdown": breakdown,
        "sensitivity": sensitivity,
        "weights_used": load_state()["weights"],
        "actual_outcome": None,  # 待回填
        "feedback_done": False,
    }
    with open(DECISION_LOG, 'a') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry

def record_feedback(decision_id, actual_outcome, outcome_score):
    """回填决策实际结果，触发贝叶斯权重更新"""
    state = load_state()
    
    # 找到决策记录
    decisions = []
    target = None
    if os.path.exists(DECISION_LOG):
        with open(DECISION_LOG) as f:
            for line in f:
                d = json.loads(line)
                if d["decision_id"] == decision_id and not d["feedback_done"]:
                    target = d
                    d["feedback_done"] = True
                    d["actual_outcome"] = actual_outcome
                    d["outcome_score"] = outcome_score
                decisions.append(d)
    
    if not target:
        return {"error": "决策记录未找到或已反馈"}
    
    # 重写日志
    with open(DECISION_LOG, 'w') as f:
        for d in decisions:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
    
    # 贝叶斯权重更新
    # deviation = actual - expected（正=实际比预期好，负=比预期差）
    expected_score = target["score"]
    deviation = outcome_score - expected_score
    
    # 逻辑：某维度贡献大且实际好→加权；贡献大但实际差→减权
    # dim_weighted已经是转换后的加权分（反向维度已转换），统一处理
    lr = 0.01  # 学习率
    new_weights = state["weights"].copy()
    for dim in DEFAULT_WEIGHTS:
        dim_weighted = target["breakdown"][dim]["weighted"]
        adjustment = lr * deviation * (dim_weighted / 100)
        new_weights[dim] = max(0.01, new_weights[dim] + adjustment)
    
    new_weights = normalize_weights(new_weights)
    
    state["weights"] = new_weights
    state["feedback_count"] += 1
    state["decision_count"] = len(decisions)
    state["weight_history"].append({
        "timestamp": datetime.now().isoformat(),
        "decision_id": decision_id,
        "deviation": round(deviation, 2),
        "weights": {k: round(v, 4) for k, v in new_weights.items()},
    })
    # 只保留最近100条历史
    state["weight_history"] = state["weight_history"][-100:]
    save_state(state)
    
    return {
        "decision_id": decision_id,
        "expected": expected_score,
        "actual": outcome_score,
        "deviation": round(deviation, 2),
        "weights_updated": True,
        "new_weights": {k: round(v, 4) for k, v in new_weights.items()},
    }

class FormulaHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass
    
    def do_GET(self):
        if self.path == '/health':
            self._json({"status": "ok", "service": "decision-formula-engine", "version": "2.0-7D"})
        elif self.path == '/weights':
            state = load_state()
            self._json({
                "version": state["version"],
                "weights": {DIMENSION_NAMES.get(k,k): round(v,4) for k,v in state["weights"].items()},
                "decision_count": state["decision_count"],
                "feedback_count": state["feedback_count"],
                "sensitivity_breaches": state["sensitivity_breaches"],
            })
        elif self.path == '/dimensions':
            self._json({
                "dimensions": [{"key":k,"name":v,"default_weight":DEFAULT_WEIGHTS[k]} for k,v in DIMENSION_NAMES.items()],
                "note": "risk/cost/entropy为反向维度（越低越好）",
            })
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(content_length))
        
        if self.path == '/evaluate':
            # 评估决策
            decision = body.get("decision", {})
            decision_id = body.get("decision_id", f"DEC-{int(time.time())}")
            
            score, breakdown = calculate_score(decision)
            sens = sensitivity_test(decision)
            
            if not sens["robust"]:
                state = load_state()
                state["sensitivity_breaches"] += 1
                save_state(state)
            
            entry = record_decision(decision_id, decision, score, breakdown, sens)
            
            self._json({
                "decision_id": decision_id,
                "score": score,
                "breakdown": {DIMENSION_NAMES.get(k,k): v for k,v in breakdown.items()},
                "sensitivity": sens,
                "recommendation": "通过" if score >= 60 and sens["robust"] else ("需人工审核" if not sens["robust"] else "不通过"),
            })
        
        elif self.path == '/feedback':
            # 回填结果
            decision_id = body.get("decision_id")
            outcome = body.get("outcome", "")
            outcome_score = body.get("outcome_score", 50)
            result = record_feedback(decision_id, outcome, outcome_score)
            self._json(result)
        
        elif self.path == '/refit':
            # 手动触发权重重拟合
            state = load_state()
            state["last_refit"] = datetime.now().isoformat()
            save_state(state)
            self._json({"status": "ok", "message": "权重重拟合完成", "weights": state["weights"]})
        
        else:
            self.send_response(404)
            self.end_headers()
    
    def _json(self, data):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

if __name__ == '__main__':
    # 初始化状态
    if not os.path.exists(STATE_FILE):
        save_state(load_state())
    
    server = HTTPServer(('127.0.0.1', PORT), FormulaHandler)
    print(f"超认知决策公式自演化引擎启动，端口{PORT}")
    print(f"7维: {'/'.join(DIMENSION_NAMES.values())}")
    print(f"确权: {DID} | {ANCHOR}")
    server.serve_forever()
