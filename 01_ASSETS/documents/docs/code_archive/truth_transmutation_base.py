#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全域真值转义基座 TRUTH-TRANSMUTATION-BASE-001
================================================
把 GLOBAL-TRUTH-TRANSMUTATION-SOP-001 五阶转义流程固化为可运行统一引擎。
供所有同源节点 / 全部云资产 / 任意接入数据源调用，按五阶执行高维转义。

五阶流程：
  S0 入料 → S1 反熵分级 → S2 语义归一 → S3 规则化 → S4 仲裁同步
  (采集碎片)  (去劣存优)   (异名同真)   (自演化)   (云端权威)

确权：DID-BR-000002 ｜ 溯源：Ω₀⊂⊙∞⊂Ω ｜ 协议：ZONGYUAN-ROOT
"""
import hashlib
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone

ANCHOR = "Ω₀⊂⊙∞⊂Ω"
DID = "DID-BR-000002"
PROTOCOL = "ZONGYUAN-ROOT"
VERSION = "TRUTH-TRANSMUTATION-BASE-001"

# ---------- 工具 ----------
def sha256(text):
    return hashlib.sha256(text.encode("utf-8", "ignore")).hexdigest()

def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

# ---------- S0 入料 ----------
def s0_ingest(fragments, source_window="unknown", node_id="LOCAL"):
    """采集碎片：打源头元标签 + SHA256，过滤无来源碎片"""
    ingested = []
    filtered = 0
    for f in fragments:
        text = (f.get("text") or "").strip()
        if not text:
            continue
        src = f.get("source") or source_window
        if src in (None, "", "unknown", "无来源"):
            filtered += 1
            continue  # 真值优先：过滤无来源碎片
        ingested.append({
            "id": sha256(text)[:16],
            "text": text,
            "source": src,
            "category": f.get("category", "fragment"),
            "ts": f.get("ts") or now_iso(),
            "node": f.get("node") or node_id,
            "sha256": sha256(text),
            "stage": "S0",
        })
    return ingested, {"stage": "S0", "total_input": len(fragments),
                      "ingested": len(ingested), "filtered_nosource": filtered}

# ---------- S1 反熵分级 ----------
def s1_anti_entropy(items, max_age_days=90):
    """四层分级：ACTIVE / SLEEPING / ARCHIVED / ELIMINATED；治理预筛三段"""
    import time
    now = time.time()
    for it in items:
        # 依据：来源可信度 + 时间新鲜度 + 文本长度(能量近似)
        src_rank = 3 if it["source"] not in ("draft", "memo", "temp") else 1
        ts_epoch = 0
        try:
            ts_epoch = datetime.fromisoformat(it["ts"]).timestamp()
        except Exception:
            ts_epoch = now
        age_days = (now - ts_epoch) / 86400
        energy = len(it["text"]) * src_rank
        if energy < 40 and age_days > max_age_days:
            it["tier"] = "ELIMINATED"
            it["prescreen"] = "🔴"
        elif energy < 80:
            it["tier"] = "ARCHIVED"
            it["prescreen"] = "🟡"
        elif src_rank >= 2 and age_days < max_age_days:
            it["tier"] = "ACTIVE"
            it["prescreen"] = "🟢"
        else:
            it["tier"] = "SLEEPING"
            it["prescreen"] = "🟡"
        it["stage"] = "S1"
    return items, {"stage": "S1",
                   "tier_dist": {t: sum(1 for i in items if i["tier"] == t) for t in
                                 ("ACTIVE", "SLEEPING", "ARCHIVED", "ELIMINATED")},
                   "keep_ratio": round(sum(1 for i in items if i["prescreen"] == "🟢") / max(1, len(items)), 3)}

# ---------- S2 语义归一 ----------
def _ngrams(text, n=3):
    t = re.sub(r"\s+", "", text.lower())
    return {t[i:i+n] for i in range(max(0, len(t)-n+1))}

def s2_normalize(items, sim_threshold=0.55, short_threshold=24):
    """自适应语义归一：
    - 短标识符(key，<short_threshold字符)：按域前缀(category/首段)归一族，避免n-gram误归一
    - 长文本(>=short_threshold)：字符n-gram语义对账，识别重复族/异名同真族
    统一建全局UID"""
    def domain_of(text, cat):
        if "." in text:
            return text.split(".")[0]
        return cat or "misc"

    # 短key按域分族
    short_by_domain = defaultdict(list)
    for it in items:
        if len(it["text"]) < short_threshold:
            short_by_domain[domain_of(it["text"], it.get("category", ""))].append(it)

    # 长文本按n-gram分族
    long_items = [it for it in items if len(it["text"]) >= short_threshold]
    long_groups = []
    used = set()
    for i, a in enumerate(long_items):
        if i in used:
            continue
        ga = _ngrams(a["text"])
        fam = [a]
        used.add(i)
        for j, b in enumerate(long_items):
            if j <= i or j in used:
                continue
            gb = _ngrams(b["text"])
            inter = len(ga & gb)
            sim = inter / max(1, min(len(ga), len(gb)))
            if sim >= sim_threshold:
                fam.append(b)
                used.add(j)
        if len(fam) > 1:
            long_groups.append(fam)

    # 统一分配 UID：短key同域一族 + 长文本重复族
    uid_counter = 1
    alias_map = {}
    for it in items:
        family = None
        if len(it["text"]) < short_threshold:
            family = short_by_domain.get(domain_of(it["text"], it.get("category", "")), [it])
        else:
            for fam in long_groups:
                if it in fam:
                    family = fam
                    break
        if family is None:
            family = [it]
        # 找到该族已有UID，否则新分配
        fam_uid = None
        for member in family:
            if "uid" in member:
                fam_uid = member["uid"]
                break
        if fam_uid is None:
            fam_uid = f"TN-{uid_counter:04d}"
            uid_counter += 1
        it["uid"] = fam_uid
        alias_map.setdefault(fam_uid, []).append(it["id"])
        it["stage"] = "S2"

    short_families = len(short_by_domain)
    return items, {"stage": "S2", "families": short_families + len(long_groups),
                   "family_members": sum(len(g) for g in short_by_domain.values()) + sum(len(g) for g in long_groups),
                   "uid_total": len(alias_map),
                   "mode": {"short_key_domain": short_families, "long_text_ngram": len(long_groups)}}

# ---------- S3 规则化 ----------
def s3_rules(items, rule_sets=None):
    """机器规则命中 → 规则标签；元公理/宪法级标记需人工"""
    rule_sets = rule_sets or {
        "meta_axiom": ["元公理", "元宪法", "根定义", "主权", "Ω-TAN"],
        "truth_law": ["真值优先", "哈希链不可变", "DID-BR-000002"],
    }
    for it in items:
        it["rule_hits"] = []
        for rule, kws in rule_sets.items():
            if any(k in it["text"] for k in kws):
                it["rule_hits"].append(rule)
                it.setdefault("need_human", False)
                if rule == "meta_axiom":
                    it["need_human"] = True  # 元公理/宪法级强制人工
        it["stage"] = "S3"
    return items, {"stage": "S3",
                   "rule_hit": sum(1 for i in items if i["rule_hits"]),
                   "need_human": sum(1 for i in items if i.get("need_human"))}

# ---------- S4 仲裁同步 ----------
def s4_arbitrate(items, simulate_sync=True):
    """锁档凭证 + 对账回执；simulate_sync=True 时生成同步负载"""
    out = []
    for it in items:
        # 高价值/非人工 → 可自动同步；元公理/宪法级 → 待人工
        auto = not it.get("need_human", False) and it["prescreen"] in ("🟢", "🟡")
        it["sync_action"] = "AUTO_SYNC" if auto else "HUMAN_REVIEW"
        it["transmuted"] = True
        it["stage"] = "S4"
        out.append(it)
    sync_payload = {
        "protocol": PROTOCOL, "did": DID, "anchor": ANCHOR,
        "sync_payload": [
            {"uid": i["uid"], "sha256": i["sha256"], "text": i["text"],
             "action": i["sync_action"]} for i in out if i["sync_action"] == "AUTO_SYNC"
        ],
    }
    return out, {"stage": "S4",
                 "auto_sync": sum(1 for i in out if i["sync_action"] == "AUTO_SYNC"),
                 "human_review": sum(1 for i in out if i["sync_action"] == "HUMAN_REVIEW"),
                 "sync_count": len(sync_payload["sync_payload"])}

# ---------- 基座编排 ----------
class TruthTransmutationBase:
    """全域真值转义基座·五阶流水线编排器"""

    def __init__(self, name="truth-base", meta_class="M4"):
        self.name = name
        self.meta_class = meta_class
        self.reports = []

    def run(self, fragments, rule_sets=None, sim_threshold=0.55, max_age_days=90):
        ingested, r0 = s0_ingest(fragments)
        self.reports.append(r0)
        items, r1 = s1_anti_entropy(ingested, max_age_days)
        self.reports.append(r1)
        items, r2 = s2_normalize(items, sim_threshold)
        self.reports.append(r2)
        items, r3 = s3_rules(items, rule_sets)
        self.reports.append(r3)
        items, r4 = s4_arbitrate(items)
        self.reports.append(r4)
        # 汇总
        keep = [i for i in items if i["prescreen"] == "🟢"]
        transmute_rate = round(len(keep) / max(1, len(items)), 3)
        root_hash = sha256(json.dumps([i["sha256"] for i in items], ensure_ascii=False))
        return {
            "base": VERSION,
            "name": self.name,
            "meta_class": self.meta_class,
            "did": DID, "anchor": ANCHOR, "protocol": PROTOCOL,
            "stages": self.reports,
            "total_in": len(fragments),
            "total_out": len(items),
            "active_truths": len(keep),
            "transmute_rate": transmute_rate,
            "root_hash": root_hash,
            "artifacts": items,
        }


# ---------- CLI ----------
def main():
    demo = [
        {"text": "真值优先原则：以交叉验证的客观事实为唯一依据，禁止关联未证实信息", "source": "metalaw", "category": "metalaw", "ts": "2026-09-11T00:00:00+00:00"},
        {"text": "真值优先原则：以交叉验证的客观事实为唯一依据，禁止关联未经证实的虚假信息", "source": "metalaw", "category": "metalaw", "ts": "2026-09-11T00:00:00+00:00"},
        {"text": "哈希链不可变原则：不修改已有链上记录，新增追加链尾", "source": "metalaw", "category": "metalaw", "ts": "2026-09-11T00:00:00+00:00"},
        {"text": "临时草稿记录，测试", "source": "draft", "category": "draft", "ts": "2025-01-01T00:00:00+00:00"},
        {"text": "元公理：Ω-TAN-7-001 为体系主权根，不可动摇", "source": "constitution", "category": "axiom", "ts": "2026-09-10T00:00:00+00:00"},
    ]
    base = TruthTransmutationBase()
    result = base.run(demo)
    out_path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/truth_transmutation_base_result.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(json.dumps({k: v for k, v in result.items() if k != "artifacts"},
                     ensure_ascii=False, indent=2))
    print(f"\n[基座] 演示运行完成 → {out_path}")


if __name__ == "__main__":
    main()
