#!/usr/bin/env python3
"""高价值资讯分类器 + 内核自进化触发器"""
import json, sqlite3, datetime

NEWS_DB = "/opt/ZONGYUAN-ROOT/news_collector/news.db"
KERNEL = "/opt/ZONGYUAN-ROOT/kernel.json"

MATRIX = {
    "model_evolution": {"kw": ["gpt","claude","qwen","llama","mistral","gemini","model","benchmark","mmlu","reasoning","astra","open source","fine-tune","lora","quantization","tokens/s","cerebras"], "w": 0.95, "action": "评估新模型接入内核API网关"},
    "agent_architecture": {"kw": ["agent","autonomous","tool use","tool calling","react","planning","multi-agent","orchestration","workflow","cursor","codex","self-healing","self-improving","meta-cognition","fleet"], "w": 0.90, "action": "分析Agent架构，优化自治内核七大进程"},
    "infra_performance": {"kw": ["kubernetes","docker","serverless","edge","inference","latency","throughput","gpu","tpu","vector","rag","embedding","cache","redis","infrastructure"], "w": 0.80, "action": "评估性能优化，提升内核响应速度"},
    "security_safety": {"kw": ["cve","vulnerability","exploit","security","patch","breach","prompt injection","jailbreak","alignment","safety","red team"], "w": 0.85, "action": "触发安全加固，更新L0防护规则"},
    "ai_boundary": {"kw": ["defeat","limitation","failure","hallucination","boundary","consciousness","understanding","symbol grounding","world model","grandmaster"], "w": 0.75, "action": "校准内核真值边界，更新兜底层"},
}

def classify(title):
    t = title.lower()
    r = []
    for dim, cfg in MATRIX.items():
        hits = sum(1 for k in cfg["kw"] if k in t)
        if hits: r.append({"dim": dim, "score": min(hits*cfg["w"],1.0), "action": cfg["action"]})
    return sorted(r, key=lambda x: x["score"], reverse=True)

def main():
    conn = sqlite3.connect(NEWS_DB)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS evolution_analysis (id INTEGER PRIMARY KEY, news_id INTEGER, dimension TEXT, score REAL, action TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    c.execute("SELECT id,title,source,url FROM news WHERE id NOT IN (SELECT news_id FROM evolution_analysis)")
    items = c.fetchall()
    hv = 0
    for nid, title, src, url in items:
        for cl in classify(title):
            c.execute("INSERT INTO evolution_analysis (news_id,dimension,score,action) VALUES (?,?,?,?)", (nid,cl["dim"],cl["score"],cl["action"]))
            if cl["score"] >= 0.8: hv += 1
    conn.commit()
    c.execute("SELECT dimension,COUNT(*),ROUND(AVG(score),2) FROM evolution_analysis GROUP BY dimension ORDER BY COUNT(*) DESC")
    stats = c.fetchall()
    c.execute("SELECT n.title,e.dimension,e.score,e.action FROM evolution_analysis e JOIN news n ON e.news_id=n.id WHERE e.score>=0.8 ORDER BY e.score DESC LIMIT 5")
    top = c.fetchall()
    conn.close()
    
    report = {"time": datetime.datetime.now().isoformat(), "analyzed": len(items), "high_value": hv, "triggered": hv>=3, "stats": stats, "top": top}
    try:
        with open(KERNEL) as f: k = json.load(f)
        k["evolution_engine"] = {"last": report["time"], "high_value": hv, "triggered": report["triggered"], "dimensions": {s[0]:{"count":s[1],"avg":s[2]} for s in stats}}
        with open(KERNEL,"w") as f: json.dump(k,f,ensure_ascii=False,indent=2)
    except: pass
    
    print(f"分析: {len(items)}条 | 高价值: {hv}条 | 进化触发: {'是' if hv>=3 else '否'}")
    print("维度分布:")
    for s in stats: print(f"  {s[0]}: {s[1]}条 均分{s[2]}")
    print("TOP高价值:")
    for t in top: print(f"  [{t[1]}] {t[2]} | {t[0][:60]}")

if __name__ == "__main__":
    main()
