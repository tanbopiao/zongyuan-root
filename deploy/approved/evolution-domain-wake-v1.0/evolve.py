#!/usr/bin/env python3
"""进化域算子唤醒引擎 V1.0 - CTE三态闭环(C→T→E→C)
TruthToEvolution: 真值纯度/冲突/漂移 → 进化信号
EvolutionToCausal: 进化策略 → do-calculus因果干预变量
输出: 进化代际 + 策略调整 + 干预设计 + 三态闭环状态
"""
import sqlite3, json, os, time, urllib.request, re

GATEWAY = "https://www.huodouai.com/api/report/truth"
TOKEN = "ZR-CAPTURE-2026-OMEGA-d04bb54ba2a55a7d"
DB = "/opt/ZONGYUAN-ROOT/data/memory_gateway.db"
OUT = "/opt/ZONGYUAN-ROOT/data/evolve_report.json"
STATE_FILE = "/opt/ZONGYUAN-ROOT/data/evolve_state.json"

# 三维稳态决策权重
BENEFIT_W, RISK_W, COST_W = 0.40, 0.35, 0.25

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f: return json.load(f)
    return {"generation": 0, "prior_strategies": []}

def save_state(s):
    with open(STATE_FILE, "w") as f: json.dump(s, f, ensure_ascii=False, indent=2)

def load_truths():
    truths = []
    if os.path.exists(DB):
        con = sqlite3.connect(DB); cur = con.cursor()
        try:
            for t in [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")]:
                try:
                    cols = [r[1] for r in cur.execute(f"PRAGMA table_info({t})")]
                    if any(c in cols for c in ['truth_key','key','value','content']):
                        truths += cur.execute(f"SELECT * FROM {t} LIMIT 6000").fetchall()
                except: pass
        finally: con.close()
    return truths

def truth_to_evolution(rows):
    """TruthToEvolution: 真值域 → 进化信号"""
    total = len(rows)
    # 纯度评分(0-100): 有来源/置信度/确权的比例
    pure = 0
    conflicts = 0
    seen = {}
    for r in rows:
        s = str(r)
        if re.search(r'(confidence.{0,3}(0\.[8-9]|1))|(source)|(DID)|(确权)|(锚定)', s, re.I):
            pure += 1
        for m in re.finditer(r'([A-Z][A-Z0-9.\-]{5,50})', s):
            k = m.group(1)
            if k in seen and seen[k] != s[:30]: conflicts += 1
            seen[k] = s[:30]
    purity = round(pure/max(total,1)*100, 1)
    drift = round(conflicts/max(total,1)*100, 1)
    return {"purity": purity, "conflict_rate": drift, "total": total}

def evolution_to_causal(evol):
    """EvolutionToCausal: 进化信号 → 策略调整(因果干预变量)"""
    # 三维稳态评估
    strategies = []
    purity = evol["purity"]; conflict = evol["conflict_rate"]
    if purity < 60:
        s = {"strategy": "增强真值来源锚定", "intervention": "do(true_source_anchor)", 
             "score": round(0.4*0.9 + 0.35*0.7 + 0.25*0.6, 3), "priority": "P0"}
        strategies.append(s)
    if conflict > 5:
        s = {"strategy": "矛盾真值隔离熔断", "intervention": "do(conflict_fuse)", 
             "score": round(0.4*0.8 + 0.35*0.9 + 0.25*0.5, 3), "priority": "P1"}
        strategies.append(s)
    # 默认稳健策略
    s = {"strategy": "稳态收敛: 增加消化频率", "intervention": "do(digest_freq_up)",
         "score": round(0.4*0.7 + 0.35*0.8 + 0.25*0.7, 3), "priority": "P2"}
    strategies.append(s)
    strategies.sort(key=lambda x: -x["score"])
    return strategies

def run():
    state = load_state()
    rows = load_truths()
    evol = truth_to_evolution(rows)
    strategies = evolution_to_causal(evol)
    state["generation"] += 1
    state["prior_strategies"].append(strategies[0]["strategy"])
    save_state(state)
    report = {
        "evolve_version": "V1.0",
        "generation": state["generation"],
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "truth_scanned": evol["total"],
        "purity_score": evol["purity"],
        "conflict_rate": evol["conflict_rate"],
        "evolution_signals": strategies,
        "recommended": strategies[0] if strategies else None,
        "tri_state_closed_loop": "C→T→E→C ACTIVE",
        "decision_weights": {"benefit": BENEFIT_W, "risk": RISK_W, "cost": COST_W},
        "status": "EVOLUTION-DOMAIN-WOKEN"
    }
    with open(OUT, "w") as f: json.dump(report, f, ensure_ascii=False, indent=2)
    return report

def report_up(rep):
    H = {"Content-Type":"application/json","X-Capture-Token":TOKEN}
    d = {"truth_key":"EVOLVE.WAKE-REPORT-20260929",
         "truth_value":json.dumps(rep, ensure_ascii=False),
         "source_node":"hub-central-agent","confidence":1.0,"truth_type":"meta_law"}
    try:
        r = urllib.request.Request(GATEWAY, data=json.dumps(d).encode(), headers=H)
        return json.loads(urllib.request.urlopen(r, timeout=12).read()).get("action")
    except Exception as e: return f"fail:{e}"

if __name__ == "__main__":
    rep = run()
    print(json.dumps(rep, ensure_ascii=False, indent=2))
    print("上报:", report_up(rep))
