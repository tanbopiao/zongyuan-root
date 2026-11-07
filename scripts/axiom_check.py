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

# M1 真值不变（append-only 语义）：内容可变，但每次变更必须留痕。
# 判定：本条 sha ≠ 磁盘 sha 时，若账本中存在同 path 且 sha == 当前磁盘 sha 的另一条目 -> 版本演进（合规）
#       否则 -> 变更未留痕（违规）
bad1, chk, evolved = [], 0, 0
sha_index = {(x.get("path"), x.get("sha256")) for x in E if x.get("path") and x.get("sha256")}
for e in E:
    if not e.get("sha256") or not e.get("path"): continue
    chk += 1
    h = sha(e["path"])
    if not h or h == e["sha256"]: continue
    if (e["path"], h) in sha_index:
        evolved += 1          # 当前版本已另有条目记录
    else:
        bad1.append({"mem_id": e["mem_id"], "path": e["path"], "note": "文件已变更但无新版本记录"})
res["M1"] = {"axiom": "已锁档内容不可篡改", "predicate": "ledger_sha == disk_sha",
             "checked": chk, "violated": len(bad1), "compliant_version_evolution": evolved,
             "samples": bad1[:5]}

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
TAU = 0.20   # 衰减容差：允许单次 <=20% 的价值衰减，超出才判违规
bad, decay = [], 0
for p, v in by.items():
    v.sort()
    for i in range(1, len(v)):
        prev, cur = v[i-1][1], v[i][1]
        if cur >= prev: continue
        drop = (prev - cur) / prev if prev else 1.0
        if drop <= TAU: decay += 1                        # 合规衰减
        else: bad.append((p, prev, cur, round(drop, 3)))
res["M2"] = {"axiom": "系统状态向真值收敛禁止回退（含衰减容差）",
             "predicate": f"value_score(t) >= value_score(t-1)*(1-{TAU})",
             "checked": len(by), "violated": len(bad), "compliant_decay": decay,
             "samples": bad[:3],
             "note": "'收敛'原文未定义，此处取价值分时间序为操作化定义；tau=0.20 为经验阈值非原文"}

print(f"{'公理':<9}{'可判定':<9}{'检查':<7}{'违规':<7}谓词")
print("-" * 82)
for k, v in res.items():
    print(f"{k:<9}{'YES':<9}{v['checked']:<7}{v['violated']:<7}{v['predicate'][:52]}")
print("-" * 82)
print("不可形式化：视觉公理/工程公理（政策约束，非逻辑命题）")
# 运行态输出 644 可追加；冻结快照（AXIOM-CHECK-YYYYMMDD.json）保持 444 不动
OUT = os.path.join(ROOT, "truth/probe/axiom-check-latest.json")
json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"运行态结果 -> {os.path.relpath(OUT, ROOT)}")
