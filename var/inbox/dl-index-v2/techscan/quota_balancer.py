#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""quota_balancer.py · 配额均衡调度闭环(针对基尼0.843告警)
分析命名空间活跃度, 识别低活跃高价值命名空间, 输出路由调度建议
0额度 · 只读 · 可持续对比治理"""
import sqlite3, json, time, urllib.request, os, re
from collections import defaultdict
DB = "/www/wwwroot/huodouai.com/zhongshu/data/truth/truth.db"

# 高价值但应提升频率的命名空间(治理/实验/审计类, 现状低频)
PRIORITY_NS = ["KERNEL", "ARCH", "L1", "SIM", "SCAN", "TRUTH-LORA", "EVO", "QUOTA", "TEST", "META"]

def main():
    c = sqlite3.connect(DB); c.text_factory = str
    rows = c.execute("select key,value,ts from truth order by seq").fetchall()
    n = len(rows)
    agg = defaultdict(lambda: {"count": 0, "last_ts": 0})
    for r in rows:
        k = r[0]
        m = re.match(r"^([A-Za-z0-9_-]+)", k)
        ns = m.group(1) if m else "other"
        agg[ns]["count"] += 1
        t = r[2]
        tv = 0
        if isinstance(t, (int, float)): tv = t/1000 if t > 1e12 else t
        elif isinstance(t, str):
            try: tv = datetime.fromisoformat(t.replace("Z", "+00:00")).timestamp()
            except Exception: pass
        if tv > agg[ns]["last_ts"]: agg[ns]["last_ts"] = tv
    top = sorted(agg.items(), key=lambda x: -x[1]["count"])
    top_share = sum(v["count"] for _, v in top[:3]) / n
    # 低活跃高价值命名空间: 占比<5% 且属于优先清单
    low_active = []
    for ns in PRIORITY_NS:
        v = agg.get(ns)
        if not v: continue
        share = v["count"] / n
        if share < 0.05:
            low_active.append({"ns": ns, "count": v["count"], "share": round(share, 4),
                               "last_ts": v["last_ts"]})
    # 路由建议: 现有周期任务向低活跃命名空间分流
    routes = []
    for la in low_active[:6]:
        routes.append(f"{la['ns']} <- 建议路由: 巡检/评分/实验类上报改挂{la['ns']}命名空间(当前{la['count']}条, 占{la['share']*100:.2f}%)")
    out = {
        "scan_ts": int(time.time()), "truth_total": n,
        "top3_share": round(top_share, 3),
        "top_namespaces": [(k, v["count"]) for k, v in top[:8]],
        "low_active_priority": low_active[:8],
        "routing_suggestions": routes,
        "target": "目标: 三轮公平检查后基尼由0.843降至<0.6, top3占比<60%",
        "baseline_gini": 0.843
    }
    os.makedirs("/www/wwwroot/huodouai.com/zhongshu/data", exist_ok=True)
    json.dump(out, open("/www/wwwroot/huodouai.com/zhongshu/data/quota-balancer-20261011.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    try:
        body = json.dumps({"key": "QUOTA.BALANCER." + time.strftime("%Y%m%d"),
            "value": {"did": "DID-BR-000002", "ts": int(time.time()),
                      "content": "Ω锚定 配额均衡调度建议 空间时间属性因果本体维度D1 " + json.dumps(out, ensure_ascii=False)[:800]}}).encode()
        rq = urllib.request.Request("https://www.huodouai.com/api/report/truth", data=body, method="POST",
            headers={"Content-Type": "application/json", "X-DID": "DID-BR-000002"})
        urllib.request.urlopen(rq, timeout=12)
    except Exception: pass
    c.close()

from datetime import datetime
if __name__ == "__main__":
    main()
