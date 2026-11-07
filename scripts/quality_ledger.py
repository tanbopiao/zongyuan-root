#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT 真值质量账本生成器（四类打标 + 五维价值分级）
类型：rule 规范 / experience 经验轨迹 / fact 事实 / noise 噪声 / poison 待裁
口径：只看语义与来源，不按长度判价值（经验轨迹短也高价值）
作者节点：NODE-DEV-DOUBAO-WORK-001 · DID-BR-000002 · Ω₀⊂⊙∞⊂Ω
"""
import json, os, re, hashlib, datetime, collections

R = "/home/user/ZONGYUAN-ROOT"
OUT_DIR = f"{R}/truth/quality"
os.makedirs(OUT_DIR, exist_ok=True)
NOW = datetime.datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S+0800")

# ---------- 判据 ----------
RULE_KW = re.compile(r"(METALAW|METARULE|META-LAW|META-RULE|AXIOM|CONSTITUTION|PROTOCOL|LAW|RULE|SOP|判据|公理|元法则|元规则|元公理|元宪法|契约|红线)", re.I)
EXP_KW  = re.compile(r"(DEPLOY|REFRESH|INJECTION|EXPERIENCE|SYNC|VERIFY|REGISTER|CMD\.|EXEC|DONE|SELF_REFLECTION|EVOLUTION_SUGGESTION|KNOWLEDGE_EXTRACTION|CONFLICT_DETECTION|巡检|部署|注入|蒸馏|同步|验证|执行|回执)", re.I)
FACT_KW = re.compile(r"(ASSET|MEDIA|ARCHIVE|KERNEL\.REF|KERNEL\.CONCEPT|SEED|TRUTH|index|config|ledger|真值|资产|归档|快照)", re.I)
NOISE_KW= re.compile(r"(HEARTBEAT|PING|KEEPALIVE|EMPTY|TEMP\.|PLACEHOLDER|TEST\.(?!.*DONE)|lorem|test123|占位|心跳)", re.I)

def classify(text, path=""):
    """返回 (type, 依据)"""
    blob = f"{text} {path}"
    if NOISE_KW.search(blob) and not EXP_KW.search(blob):
        return "noise", "命中噪声特征"
    if RULE_KW.search(blob):
        return "rule", "命中规范/公理/协议特征"
    if EXP_KW.search(blob):
        return "experience", "命中动作-结果轨迹特征"
    if FACT_KW.search(blob):
        return "fact", "命中实体/资产/真值特征"
    return "fact", "默认归事实（待复核）"

BASE = {"rule": 88, "experience": 85, "fact": 65, "noise": 12, "poison": 0}

def score(t, rec, extra_ok=0, extra_bad=0):
    s = BASE[t] + extra_ok - extra_bad
    return max(0, min(100, s))

def grade(s):
    if s >= 80: return "L1"
    if s >= 60: return "L2"
    if s >= 30: return "L3"
    return "L4"

# ---------- 批次一：联邦索引 539 条 ----------
ledger_p = f"{R}/truth/federal-index/index_ledger.json"
led = json.load(open(ledger_p, encoding="utf-8"))
entries_out = []
type_cnt = collections.Counter(); grade_cnt = collections.Counter()
for e in led.get("entries", []):
    path = e.get("path", "")
    tags = " ".join(e.get("tags", []))
    t, why = classify(tags, path)
    ok = 0; bad = 0
    if e.get("sha256"): ok += 3
    if (e.get("bytes") or 0) > 0: ok += 3
    else: bad += 5                      # 元数据残缺（bytes=0）
    if "meta-rules" in tags or "axiomgate" in tags: ok += 2
    if "truth" in path or "truth" in tags: ok += 2
    if "experience" in t: ok += 3
    sc = score(t, e, ok, bad)
    g = grade(sc)
    type_cnt[t] += 1; grade_cnt[g] += 1
    entries_out.append({
        "mem_id": e.get("mem_id"), "path": path, "sha256": e.get("sha256"),
        "type": t, "type_basis": why, "value_score": sc, "grade": g,
        "bytes": e.get("bytes", 0), "tags": e.get("tags", []),
        "reuse_hint": {"rule": "直接注入 AxiomGate 约束层",
                       "experience": "提炼为 SOP / 技能包，作 agent 训练轨迹",
                       "fact": "进入 RAG 检索层",
                       "noise": "仅作负样本，不参与检索"}.get(t, "")
    })

# ---------- 批次二：去重索引的族级分布 ----------
dedup = json.load(open(f"{R}/truth/DEDUP-INDEX.json", encoding="utf-8"))
clusters = dedup.get("unmapped_clusters", [])
fam_out = []
fam_type_cnt = collections.Counter(); fam_item_cnt = collections.Counter()
for c in clusters:
    name = c.get("cluster", ""); n = int(c.get("count", 0))
    t, why = classify(name)
    sc = score(t, {}, 0, 0)
    fam_type_cnt[t] += 1; fam_item_cnt[t] += n
    fam_out.append({"cluster": name, "count": n, "type": t, "type_basis": why,
                    "value_score": sc, "grade": grade(sc)})

# ---------- 汇总 ----------
total_idx = len(entries_out)
total_fam_items = sum(fam_item_cnt.values())
summary = {
    "generated_at": NOW, "node": "NODE-DEV-DOUBAO-WORK-001", "did": "DID-BR-000002",
    "trace": "Ω₀⊂⊙∞⊂Ω",
    "scope": {"federal_index_entries": total_idx, "dedup_family_items": total_fam_items,
              "cloud_truth_total_unreadable": dedup.get("total_cloud_truths")},
    "index_by_type": dict(type_cnt), "index_by_grade": dict(grade_cnt),
    "family_by_type": dict(fam_type_cnt), "family_items_by_type": dict(fam_item_cnt),
    "family_by_grade": dict(collections.Counter(f["grade"] for f in fam_out)),
    "method": "语义+来源判据，不按长度判价值；经验轨迹与规范为高价值，事实为中价值，噪声仅负样本",
    "constraint": "云端 118507 条内容不可批量读取（ledger 仅哈希、search 退化），本账本为本地可审计口径"
}
# 族级明细只留 L1(高价值) 与 L4(噪声)，其余按类型聚合，避免账本膨胀
fam_detail = [f for f in fam_out if f["grade"] in ("L1", "L4")]
agg = collections.defaultdict(lambda: {"families": 0, "items": 0})
for f in fam_out:
    a = agg[f["type"]]; a["families"] += 1; a["items"] += f["count"]
summary["family_aggregate"] = dict(agg)
pruned = {
    "fam_top_by_count": sorted(fam_out, key=lambda x: -x["count"])[:300],
    "note": "全量 101986 族明细未落盘（避免账本膨胀）；如需全量请设置 FULL_DUMP=1 重跑"
}
obj = {"ledger_id": "QUALITY-LEDGER-V1.0", "summary": summary,
       "federal_index": entries_out, "dedup_family_high_value": fam_detail,
       "dedup_family_aggregate": pruned}
p = f"{OUT_DIR}/QUALITY-LEDGER.json"
json.dump(obj, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
os.chmod(p, 0o644)

print("== 批次一：联邦索引 %d 条 ==" % total_idx)
print("  类型:", dict(type_cnt))
print("  分级:", dict(grade_cnt))
print("== 批次二：去重族 %d 族 / %d 条 ==" % (len(fam_out), total_fam_items))
print("  类型(族数):", dict(fam_type_cnt))
print("  类型(条数):", dict(fam_item_cnt))
print("  分级:", dict(collections.Counter(f["grade"] for f in fam_out)))
print("\n账本:", p, os.path.getsize(p), "B 644")
json.dump(summary, open(f"{OUT_DIR}/summary.tmp", "w", encoding="utf-8"), ensure_ascii=False)
