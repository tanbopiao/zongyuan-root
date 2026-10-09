#!/usr/bin/env python3
"""智能推演引擎 V1.0 - 大脑从台账升级为参谋
奇点预测(四级预警) + 因果链溯源 + 三维稳态方案评估
"""
import sqlite3, json, os, time, urllib.request, re
from collections import Counter

GATEWAY = "https://www.huodouai.com/api/report/truth"
TOKEN = "ZR-CAPTURE-2026-OMEGA-d04bb54ba2a55a7d"
DB = "/opt/ZONGYUAN-ROOT/data/memory_gateway.db"
OUT = "/opt/ZONGYUAN-ROOT/data/oracle_report.json"
BENEFIT_W, RISK_W, COST_W = 0.40, 0.35, 0.25

def load_truths():
    rows = []
    if os.path.exists(DB):
        con = sqlite3.connect(DB); cur = con.cursor()
        try:
            for t in [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")]:
                try:
                    cols = [r[1] for r in cur.execute(f"PRAGMA table_info({t})")]
                    if any(c in cols for c in ['truth_key','key','value','content']):
                        rows += cur.execute(f"SELECT * FROM {t} LIMIT 6000").fetchall()
                except: pass
        finally: con.close()
    return rows

def causality_trace(rows):
    """因果链溯源：从真值中提取因果/风险关系"""
    causes = Counter(); risks = Counter()
    for r in rows:
        s = str(r)
        for m in re.finditer(r'(由于|因为|导致|引发|触发|风险|故障|失败|断点)\s*([^，。]{2,30})', s):
            causes[m.group(2).strip()] += 1
        if re.search(r'(risk|风险|故障|fail|断点|告警)', s, re.I):
            for m in re.finditer(r'([A-Z][A-Z0-9.\-]{5,50})', s): risks[m.group(1)] += 1
    return causes.most_common(8), risks.most_common(10)

def singularity_forecast(risks):
    """奇点概率预测：风险实体 → 爆发概率 + 四级预警"""
    forecast = []
    for ent, count in risks[:8]:
        # 概率模型：出现频次归一化 + 风险权重
        prob = min(0.95, count/20 + 0.15)
        level = "蓝" if prob < 0.3 else "黄" if prob < 0.5 else "橙" if prob < 0.7 else "红"
        forecast.append({"entity": ent, "appear": count, "burst_prob": round(prob, 2), "warning": level})
    return forecast

def plan_eval(forecast):
    """三维稳态方案评估：生成≥3套方案"""
    red = [f for f in forecast if f["warning"]=="红"]
    orange = [f for f in forecast if f["warning"] in "橙红"]
    plans = []
    if red:
        p = {"plan": "P0熔断隔离", "actions": [f"隔离{e['entity']}" for e in red],
             "score": round(BENEFIT_W*0.9+RISK_W*0.9+COST_W*0.5,3), "recommend": True}
        plans.append(p)
    if orange:
        p = {"plan": "P1加固巡检", "actions": [f"监控{e['entity']}" for e in orange[:3]],
             "score": round(BENEFIT_W*0.7+RISK_W*0.85+COST_W*0.7,3), "recommend": True}
        plans.append(p)
    p = {"plan": "P2稳态收敛", "actions": ["增加消化频率","统一协议对齐","历史资产归档"],
         "score": round(BENEFIT_W*0.6+RISK_W*0.8+COST_W*0.9,3), "recommend": True}
    plans.append(p)
    plans.sort(key=lambda x:-x["score"])
    return plans

def run():
    rows = load_truths()
    causes, risks = causality_trace(rows)
    forecast = singularity_forecast(risks)
    plans = plan_eval(forecast)
    report = {
        "oracle_version": "V1.0",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "truth_scanned": len(rows),
        "causal_trace": causes,
        "singularity_forecast": forecast,
        "top_red_warning": [f for f in forecast if f["warning"]=="红"][:3],
        "plans": plans,
        "recommended_plan": plans[0] if plans else None,
        "decision_weights": {"benefit":0.40,"risk":0.35,"cost":0.25},
        "oracle_status": "ACTIVE-ORACLE"
    }
    with open(OUT, "w") as f: json.dump(report, f, ensure_ascii=False, indent=2)
    return report

def report_up(rep):
    H = {"Content-Type":"application/json","X-Capture-Token":TOKEN}
    d = {"truth_key":"ORACLE.REPORT-20260929",
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
