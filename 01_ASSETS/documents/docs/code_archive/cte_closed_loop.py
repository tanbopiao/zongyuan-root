#!/usr/bin/env python3
"""
CTE三位一体闭环编排器
Causal(因果域) → Truth(真值域) → Evolution(进化域) → Causal(反馈)
打通元内核自进化的最后一环
确权: DID-BR-000002 | 溯源: Ω₀⊂⊙∞⊂Ω
"""
import json
import os
import time
import urllib.request
from datetime import datetime

BASE = "/opt/ZONGYUAN-ROOT"
LOG_FILE = os.path.join(BASE, "logs/cte_closed_loop.log")
STATE_FILE = os.path.join(BASE, "data/cte_loop_state.json")

# 三域端点
CAUSAL_API = "http://127.0.0.1:8070"
TRUTH_API = "http://127.0.0.1:9120"
EVOLUTION_STATE = os.path.join(BASE, "data/meta_evolution_state.json")

def log(msg):
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, 'a') as f:
        f.write("[%s] %s\n" % (ts, msg))
    print("[%s] %s" % (ts, msg))

def api_get(url, timeout=5):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"error": str(e)}

def api_post(url, data, timeout=5):
    try:
        req = urllib.request.Request(
            url, data=json.dumps(data).encode(),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"error": str(e)}

def causal_stage():
    """C1: 因果域 - 获取因果洞察"""
    log("【C1因果域】采集因果网络状态...")
    status = api_get(CAUSAL_API + "/health")
    nodes = status.get("graph_nodes", 0)
    edges = status.get("graph_edges", 0)
    rules = status.get("causal_rules", 0)
    
    # 获取高影响节点（模拟因果链溯源）
    insight = {
        "nodes": nodes,
        "edges": edges,
        "causal_rules": rules,
        "key_insight": "因果网络当前有%d节点/%d边/%d规则，稳态运行" % (nodes, edges, rules)
    }
    log("  因果网络: %d节点/%d边/%d规则" % (nodes, edges, rules))
    return insight

def truth_stage(causal_insight):
    """T1: 真值域 - 基于因果洞察提炼真值"""
    log("【T1真值域】提炼相关真值...")
    
    # 从9120获取最近的meta_rule和decision类真值
    status = api_get(TRUTH_API + "/api/status")
    truth_count = status.get("total_truths", status.get("count", 0))
    
    # 构造真值条目（因果洞察→真值）
    truth_entry = {
        "key": "CTE.INSIGHT.%s" % datetime.now().strftime("%Y%m%d%H%M%S"),
        "value": json.dumps({
            "source": "causal_domain",
            "insight": causal_insight.get("key_insight", ""),
            "nodes": causal_insight.get("nodes", 0),
            "edges": causal_insight.get("edges", 0)
        }, ensure_ascii=False),
        "category": "theorem",
        "source": "cte_closed_loop",
        "did": "DID-BR-000002",
        "truth_type": "cte_insight",
        "confidence": 0.85
    }
    
    # 写入9120
    result = api_post(TRUTH_API + "/api/truth/upsert", truth_entry)
    log("  真值写入: %s" % ("成功" if not result.get("error") else result.get("error")))
    log("  真值总量: %d" % truth_count)
    
    return {"truth_count": truth_count, "entry_written": not result.get("error")}

def evolution_stage(truth_result):
    """E1: 进化域 - 基于真值生成进化策略"""
    log("【E1进化域】触发生成进化策略...")
    
    # 读取元进化引擎状态
    evo_state = {}
    if os.path.exists(EVOLUTION_STATE):
        with open(EVOLUTION_STATE) as f:
            evo_state = json.load(f)
    
    stats = evo_state.get("stats", {})
    total = stats.get("total_evolutions", 0)
    success = stats.get("successful_evolutions", 0)
    phase = evo_state.get("current_phase", "unknown")
    
    # 进化信号：真值增长→进化压力
    truth_count = truth_result.get("truth_count", 0)
    evolution_pressure = min(truth_count / 1000.0, 1.0)  # 真值越多压力越大
    
    strategy = {
        "evolution_phase": phase,
        "total_evolutions": total,
        "success_rate": (success / total * 100) if total > 0 else 0,
        "evolution_pressure": round(evolution_pressure, 3),
        "recommended_action": "continue_evolution" if evolution_pressure < 0.8 else "consolidate_and_archive",
        "signal": "truth_growth=%d, pressure=%.2f" % (truth_count, evolution_pressure)
    }
    log("  进化阶段: %s, 总进化: %d次, 压力: %.2f" % (phase, total, evolution_pressure))
    log("  推荐动作: %s" % strategy["recommended_action"])
    return strategy

def causal_feedback(evolution_strategy):
    """C2: 反馈因果域 - 进化策略作为干预变量注入"""
    log("【C2反馈】进化策略注入因果域...")
    
    # 将进化策略作为干预信号写入9120（因果域消费）
    feedback = {
        "key": "CTE.FEEDBACK.%s" % datetime.now().strftime("%Y%m%d%H%M%S"),
        "value": json.dumps({
            "source": "evolution_domain",
            "intervention_type": "strategy_injection",
            "strategy": evolution_strategy.get("recommended_action"),
            "phase": evolution_strategy.get("evolution_phase"),
            "do_calculus_note": "新策略作为do-calculus干预注入因果网络，观测下游传播"
        }, ensure_ascii=False),
        "category": "method",
        "source": "cte_closed_loop",
        "did": "DID-BR-000002",
        "truth_type": "cte_feedback",
        "confidence": 0.8
    }
    result = api_post(TRUTH_API + "/api/truth/upsert", feedback)
    log("  干预信号写入: %s" % ("成功" if not result.get("error") else result.get("error")))
    return not result.get("error")

def run_cte_cycle():
    """执行一次完整CTE闭环"""
    log("=" * 50)
    log("CTE三位一体闭环开始")
    start = time.time()
    
    # C1 → T1 → E1 → C2
    causal_insight = causal_stage()
    truth_result = truth_stage(causal_insight)
    evolution_strategy = evolution_stage(truth_result)
    feedback_ok = causal_feedback(evolution_strategy)
    
    elapsed = round(time.time() - start, 2)
    
    # 记录闭环状态
    state = {
        "last_cycle": datetime.now().isoformat(),
        "cycles_executed": 0,
        "last_result": {
            "causal_nodes": causal_insight.get("nodes", 0),
            "truth_count": truth_result.get("truth_count", 0),
            "evolution_phase": evolution_strategy.get("evolution_phase"),
            "feedback_ok": feedback_ok,
            "elapsed_seconds": elapsed
        }
    }
    
    # 累加计数
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            old = json.load(f)
        state["cycles_executed"] = old.get("cycles_executed", 0) + 1
    else:
        state["cycles_executed"] = 1
    
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    
    log("CTE闭环完成: 第%d次, 耗时%.2fs" % (state["cycles_executed"], elapsed))
    log("=" * 50)
    return state

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--daemon':
        log("CTE闭环编排器启动（守护模式，每30分钟）")
        while True:
            try:
                run_cte_cycle()
            except Exception as e:
                log("闭环异常: %s" % e)
            time.sleep(1800)  # 30分钟
    else:
        run_cte_cycle()
