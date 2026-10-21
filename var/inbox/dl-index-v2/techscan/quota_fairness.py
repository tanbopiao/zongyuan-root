#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""quota_fairness.py · 配额公平检查(EconEval-Agent方法论)
统计各节点/命名空间任务量与上报活跃度, 计算公平指数(基尼系数), 检测饿死节点
0额度 · 只读 · 可定时"""
import sqlite3, json, time, urllib.request, os
from collections import Counter
DB = "/www/wwwroot/huodouai.com/zhongshu/data/truth/truth.db"
def gini(vals):
    if not vals: return 0.0
    v = sorted(vals); n = len(v)
    s = sum((i+1)*x for i, x in enumerate(v))
    return round((2*s)/(n*sum(v)) - (n+1)/n, 3) if sum(v) else 0.0
def main():
    c = sqlite3.connect(DB); c.text_factory = str
    rows = c.execute("select key,value,ts from truth order by seq").fetchall()
    node_cnt = Counter(); ns_cnt = Counter()
    for r in rows:
        k = r[0]; v = str(r[1])
        ns = k.split(".")[0][:24]; ns_cnt[ns] += 1
        for tag in ("NODE-DEV", "NODE-MI", "NODE-LOCAL", "CLOUD", "node_heartbeat", "worker"):
            if tag in k: node_cnt[tag] += 1; break
    n = len(rows)
    fair = gini(list(ns_cnt.values()))
    top_nodes = node_cnt.most_common(6)
    # 饿死检测: 命名空间占总数<0.5%且有写入意图的视为边缘
    edge = [k for k, v in ns_cnt.items() if v / max(n, 1) < 0.005]
    out = {
        "scan_ts": int(time.time()), "truth_total": n,
        "gini_index": fair,  # 越接近0越公平
        "fairness": "均衡" if fair < 0.5 else ("偏集中" if fair < 0.7 else "严重集中"),
        "top_namespaces": ns_cnt.most_common(6),
        "node_activity": top_nodes,
        "edge_namespaces": edge[:10],
        "starved_risk": len(edge) > 0 and "边缘命名空间存在(占<0.5%), 需关注" or "无饿死风险"
    }
    os.makedirs("/www/wwwroot/huodouai.com/zhongshu/data", exist_ok=True)
    json.dump(out, open("/www/wwwroot/huodouai.com/zhongshu/data/quota-fairness-20261011.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    # 上报云端
    try:
        body = json.dumps({"key": "QUOTA.FAIRNESS." + time.strftime("%Y%m%d"),
            "value": {"did": "DID-BR-000002", "ts": int(time.time()),
                      "content": "Ω锚定 配额公平检查 空间时间属性因果本体维度D1 " + json.dumps(out, ensure_ascii=False)[:800]}}).encode()
        rq = urllib.request.Request("https://www.huodouai.com/api/report/truth", data=body, method="POST",
            headers={"Content-Type": "application/json", "X-DID": "DID-BR-000002"})
        urllib.request.urlopen(rq, timeout=12)
    except Exception: pass
    c.close()
if __name__ == "__main__":
    main()
