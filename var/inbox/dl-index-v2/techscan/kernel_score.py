#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""kernel_score.py · 自治内核量化评分(CogMetric-Bench方法论)
工作记忆=检索命中质量 | 流体智力=新真值采纳率 | 认知灵活性=命名空间多样性
输出可对外展示的内核评分JSON(0-100三轴+总评)
用法: python3 kernel_score.py (云端跑, 读truth.db)
"""
import sqlite3, json, time, os, re, urllib.request

DB = "/www/wwwroot/huodouai.com/zhongshu/data/truth/truth.db"
def main():
    c = sqlite3.connect(DB); c.text_factory = str
    rows = c.execute("select seq,key,value,ts from truth order by seq").fetchall()
    total = len(rows)
    keys = set(r[1] for r in rows)
    unique = len(keys)
    dup = total - unique
    # 命名空间多样性(认知灵活性)
    ns = set()
    for r in rows:
        m = re.match(r"^([A-Za-z0-9_]+)", r[1])
        if m: ns.add(m.group(1))
    ns_div = len(ns)
    # 基线完整性(工作记忆底座)
    base_hits = sum(1 for k in keys if any(b in k for b in ("SEED_TRUTH", "TRUTH-META", "KERNEL")))
    # 检索健康(工作记忆): 直连memory-search查一次
    mem_score = 0
    try:
        req = urllib.request.Request("http://127.0.0.1:9001/api/memory-search?q=%E7%AE%97%E5%8A%9B&k=5")
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read().decode())
            confs = [x.get("confidence", 0) for x in d.get("results", [])]
            mem_score = round(sum(confs) / len(confs), 3) if confs else 0
            mem_source = "semantic" if mem_score else "empty"
    except Exception:
        mem_score = 0
    if mem_score == 0:
        mem_source = "local"
        # 降级: 纯本地工作记忆计分(0外部依赖, 不调ARK/gateway) — 最近500条真值核心词命中率
        try:
            _w = ["算力", "调度", "真值", "节点", "记忆", "对齐", "锚定", "本体"]
            _sample = rows[-500:]
            _hits = sum(1 for r in _sample if any(w in str(r[2]) for w in _w))
            mem_score = round(min(1.0, _hits / max(len(_sample), 1) * 1.1), 3) if _sample else 0.5
        except Exception:
            mem_score = 0.5
    # 新真值采纳率(流体智力): 近24h新增 vs 拦截(对齐门)
    c24 = 0
    try:
        from datetime import datetime, timezone, timedelta
        st = time.time() - 86400
        for r in rows:
            t = r[3]
            if isinstance(t, (int, float)):
                tv = t / 1000.0 if t > 1e12 else t
                if tv > st: c24 += 1
            elif isinstance(t, str):
                try:
                    tv = datetime.fromisoformat(t.replace("Z", "+00:00")).timestamp()
                    if tv > st: c24 += 1
                except Exception: pass
    except Exception: pass

    wm = round(min(1.0, mem_score / 0.6) * 100, 1)          # 工作记忆=检索置信
    fl = round(min(100, c24 * 2 + 40), 1)                    # 流体智力=新真值活力(有增量即及格)
    cf = round(min(100, 40 + ns_div * 0.5), 1)               # 认知灵活性=命名空间多样性
    health = round(min(100, 60 + (1 - dup / max(total, 1)) * 40), 1)  # 数据健康=重复率惩罚
    overall = round((wm * 0.3 + fl * 0.25 + cf * 0.2 + health * 0.25), 1)
    out = {
        "scan_ts": int(time.time()),
        "kernel": "ZONGYUAN-ROOT 自治内核",
        "scores": {
            "working_memory": wm,      # 检索置信(记忆检索)
            "fluid_intelligence": fl,  # 新真值采纳活力
            "cognitive_flexibility": cf, # 命名空间多样性
            "data_health": health,     # 重复率治理
            "overall": overall
        },
        "metrics": {"truth_total": total, "unique_keys": unique, "duplicate_rows": dup,
                    "namespaces": ns_div, "baseline_keys": base_hits, "mem_confidence": mem_score, "new_24h": c24,
                    "mem_source": mem_source},
        "grade": "S" if overall >= 85 else ("A" if overall >= 70 else ("B" if overall >= 55 else "C"))
    }
    os.makedirs("/www/wwwroot/huodouai.com/zhongshu/data", exist_ok=True)
    json.dump(out, open("/www/wwwroot/huodouai.com/zhongshu/data/kernel-score-20261011.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    # 自动上报云端(轻量, 失败静默)
    try:
        import urllib.request
        body = json.dumps({"key": "KERNEL.SCORE." + time.strftime("%Y%m%d"),
            "value": {"did": "DID-BR-000002", "ts": int(time.time()),
                      "content": "Ω锚定 内核量化评分 空间时间属性因果本体维度D1 " + json.dumps(out, ensure_ascii=False)[:900]}}).encode()
        rq = urllib.request.Request("https://www.huodouai.com/api/report/truth", data=body, method="POST",
            headers={"Content-Type": "application/json", "X-DID": "DID-BR-000002"})
        urllib.request.urlopen(rq, timeout=12)
    except Exception:
        pass
    c.close()

if __name__ == "__main__":
    main()
