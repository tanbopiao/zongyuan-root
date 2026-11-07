#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""公理断言检查器 V1.0 · 把自然语言公理转成可判定谓词
DID-BR-000002 | 2026-11-07
只检查能形式化的部分；不能形式化的公理显式标记 UNFORMALIZABLE。
"""
import json, os, hashlib, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
L = os.path.join(ROOT, "truth/federal-index/index_ledger.json")
d = json.load(open(L, encoding="utf-8"))
E = d["entries"]

def sha(p):
    fp = os.path.join(ROOT, p)
    if not os.path.exists(fp): return None
    return hashlib.sha256(open(fp, "rb").read()).hexdigest()

res = {}

# M1 真值不变：已锁档内容不可篡改 → 断言 ledger.sha == disk.sha
bad1, chk = [], 0
for e in E:
    if not e.get("sha256") or not e.get("path"): continue
    chk += 1
    h = sha(e["path"])
    if h and h != e["sha256"]: bad1.append(e["mem_id"])
res["M1"] = {"axiom": "已锁档内容不可篡改", "predicate": "ledger_sha == disk_sha",
             "checked": chk, "violated": len(bad1), "samples": bad1[:5]}

# M3 可追溯：每条必须有 sha256 + timestamp
bad3 = [e["mem_id"] for e in E if not e.get("sha256") or not e.get("timestamp")]
res["M3"] = {"axiom": "所有变更写入不可篡改账本", "predicate": "has(sha256) AND has(timestamp)",
             "checked": len(E), "violated": len(bad3), "samples": bad3[:5]}

# M4 / AXIOM-AVT-001：每条必须有 type（四类之一）
LEGAL = {"rule", "experience", "fact", "noise", "poison"}
bad4 = [e["mem_id"] for e in E if e.get("type") not in LEGAL]
res["M4"] = {"axiom": "规则即本体/轨迹即经验/事实即记忆/噪声即边界样本",
             "predicate": "type ∈ {rule,experience,fact,noise,poison}",
             "checked": len(E), "violated": len(bad4), "samples": bad4[:5]}

# AVT-002 索引四元：type/value_score/reuse_hint/bytes
bad2 = [e["mem_id"] for e in E
        if not all(k in e and e[k] not in (None, 0, "") for k in ("type", "value_score", "bytes"))
        or not e.get("reuse_hint")]
res["AVT-002"] = {"axiom": "索引是价值地图非目录", "predicate": "has(type,value_score,bytes,reuse_hint)",
                  "checked": len(E), "violated": len(bad2), "samples": bad2[:5]}

# M2 单调收敛：版本演进中 value_score 不得下降（按 path 分组取时间序）
by = collections.defaultdict(list)
for e in E:
    if e.get("path") and e.get("value_score") and e.get("timestamp"):
        by[e["path"]].append((e["timestamp"], e["value_score"], e["mem_id"]))
bad = []
for p, v in by.items():
    v.sort()
    for i in range(1, len(v)):
        if v[i][1] < v[i-1][1]: bad.append((p, v[i-1][1], v[i][1]))
res["M2"] = {"axiom": "系统状态向真值收敛禁止回退", "predicate": "value_score 时间序非降",
             "checked": len(by), "violated": len(bad), "samples": bad[:3],
             "note": "'收敛'未在原文定义，此处取 value_score 非降为操作化定义——这是翻译时引入的假设"}

print(f"{'公理':<9}{'可判定':<9}{'检查':<7}{'违规':<7}谓词")
print("-" * 82)
for k, v in res.items():
    print(f"{k:<9}{'YES':<9}{v['checked']:<7}{v['violated']:<7}{v['predicate'][:52]}")
print("-" * 82)
print("不可形式化：视觉公理/工程公理（政策约束，非逻辑命题）")
json.dump(res, open(os.path.join(ROOT, "truth/probe/AXIOM-CHECK-20261107.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
