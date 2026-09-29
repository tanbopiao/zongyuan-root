#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全域真值转义算子 - TruthTransmutationOperator
将碎片输入按五阶转义(S0入料→S1反熵分级→S2语义归一→S3规则化→S4仲裁同步)转义为高阶真值。
属于：真值抽取算子组(truth_extraction)
确权：DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω ｜ ZONGYUAN-ROOT
"""
import hashlib
import json
import re
import time
from collections import defaultdict
from datetime import datetime, timezone
from core.base_operator import BaseOperator, OperatorResult, OperatorPriority
from registry.operator_registry import register_operator

ANCHOR = "Ω₀⊂⊙∞⊂Ω"
DID = "DID-BR-000002"


# ---------- 五阶转义核心（自包含） ----------
def _sha256(text):
    return hashlib.sha256(text.encode("utf-8", "ignore")).hexdigest()


def _s0_ingest(fragments, source_window="unknown", node_id="LOCAL"):
    ingested, filtered = [], 0
    for f in fragments or []:
        text = (f.get("text") or "").strip()
        if not text:
            continue
        src = f.get("source") or source_window
        if src in (None, "", "unknown", "无来源"):
            filtered += 1
            continue
        ingested.append({"id": _sha256(text)[:16], "text": text, "source": src,
                         "category": f.get("category", "fragment"),
                         "ts": f.get("ts") or datetime.now(timezone.utc).isoformat(timespec="seconds"),
                         "node": f.get("node") or node_id, "sha256": _sha256(text), "stage": "S0"})
    return ingested, {"stage": "S0", "ingested": len(ingested), "filtered_nosource": filtered}


def _s1_anti_entropy(items, max_age_days=90):
    now = time.time()
    for it in items:
        src_rank = 3 if it["source"] not in ("draft", "memo", "temp") else 1
        ts_epoch = now
        try:
            ts_epoch = datetime.fromisoformat(it["ts"]).timestamp()
        except Exception:
            pass
        age_days = (now - ts_epoch) / 86400
        energy = len(it["text"]) * src_rank
        if energy < 40 and age_days > max_age_days:
            it["tier"], it["prescreen"] = "ELIMINATED", "🔴"
        elif energy < 80:
            it["tier"], it["prescreen"] = "ARCHIVED", "🟡"
        elif src_rank >= 2 and age_days < max_age_days:
            it["tier"], it["prescreen"] = "ACTIVE", "🟢"
        else:
            it["tier"], it["prescreen"] = "SLEEPING", "🟡"
        it["stage"] = "S1"
    return items, {"stage": "S1",
                   "tier": {t: sum(1 for i in items if i["tier"] == t) for t in
                            ("ACTIVE", "SLEEPING", "ARCHIVED", "ELIMINATED")}}


def _ngrams(text, n=3):
    t = re.sub(r"\s+", "", text.lower())
    return {t[i:i + n] for i in range(max(0, len(t) - n + 1))}


def _s2_normalize(items, sim_threshold=0.55, short_threshold=24):
    def domain_of(text, cat):
        return text.split(".")[0] if "." in text else (cat or "misc")

    short_by_domain = defaultdict(list)
    for it in items:
        if len(it["text"]) < short_threshold:
            short_by_domain[domain_of(it["text"], it.get("category", ""))].append(it)
    long_items = [it for it in items if len(it["text"]) >= short_threshold]
    long_groups, used = [], set()
    for i, a in enumerate(long_items):
        if i in used:
            continue
        ga, fam = _ngrams(a["text"]), [a]
        used.add(i)
        for j, b in enumerate(long_items):
            if j <= i or j in used:
                continue
            gb = _ngrams(b["text"])
            sim = len(ga & gb) / max(1, min(len(ga), len(gb)))
            if sim >= sim_threshold:
                fam.append(b)
                used.add(j)
        if len(fam) > 1:
            long_groups.append(fam)
    uid_counter, alias = 1, {}
    for it in items:
        family = None
        if len(it["text"]) < short_threshold:
            family = short_by_domain.get(domain_of(it["text"], it.get("category", "")), [it])
        else:
            family = next((g for g in long_groups if it in g), [it])
        fam_uid = next((m["uid"] for m in family if "uid" in m), None)
        if fam_uid is None:
            fam_uid = f"TN-{uid_counter:04d}"
            uid_counter += 1
        it["uid"] = fam_uid
        alias.setdefault(fam_uid, []).append(it["id"])
        it["stage"] = "S2"
    return items, {"stage": "S2", "domain_groups": len(short_by_domain),
                   "long_ngram_groups": len(long_groups), "uid_total": len(alias)}


def _s3_rules(items):
    rule_sets = {"meta_axiom": ["元公理", "元宪法", "根定义", "主权", "Ω-TAN"],
                 "truth_law": ["真值优先", "哈希链不可变", "DID-BR-000002"]}
    for it in items:
        it["rule_hits"] = [rule for rule, kws in rule_sets.items() if any(k in it["text"] for k in kws)]
        if "meta_axiom" in it["rule_hits"]:
            it["need_human"] = True
        it["stage"] = "S3"
    return items, {"stage": "S3", "rule_hit": sum(1 for i in items if i["rule_hits"]),
                   "need_human": sum(1 for i in items if i.get("need_human"))}


def _s4_arbitrate(items):
    for it in items:
        auto = not it.get("need_human", False) and it["prescreen"] in ("🟢", "🟡")
        it["sync_action"] = "AUTO_SYNC" if auto else "HUMAN_REVIEW"
        it["stage"] = "S4"
    return items, {"stage": "S4",
                   "auto_sync": sum(1 for i in items if i["sync_action"] == "AUTO_SYNC"),
                   "human_review": sum(1 for i in items if i["sync_action"] == "HUMAN_REVIEW")}


@register_operator
class TruthTransmutationOperator(BaseOperator):
    """全域真值转义算子：五阶流水线转义碎片为高阶真值"""
    OPERATOR_ID = "truth-transmutation-v1"
    OPERATOR_NAME = "全域真值转义算子"
    OPERATOR_VERSION = "1.0.0"
    OPERATOR_GROUP = "truth_extraction"
    OPERATOR_DESCRIPTION = "按五阶转义(S0入料→S1反熵→S2归一→S3规则→S4仲裁)将碎片转义为高阶真值资产"
    PRIORITY = OperatorPriority.MEDIUM

    def execute(self, input_data):
        fragments = input_data.get("fragments") or input_data.get("items") or []
        source_window = input_data.get("source_window", "unknown")
        node_id = input_data.get("node_id", "DOUBAO-CLOUD-001")
        sim_threshold = input_data.get("sim_threshold", 0.55)
        if not fragments:
            return OperatorResult(success=False, error="未提供待转义碎片(fragments)")
        # 五阶编排
        items, r0 = _s0_ingest(fragments, source_window, node_id)
        items, r1 = _s1_anti_entropy(items)
        items, r2 = _s2_normalize(items, sim_threshold)
        items, r3 = _s3_rules(items)
        items, r4 = _s4_arbitrate(items)
        keep = [i for i in items if i["prescreen"] == "🟢"]
        data = {
            "operator": "truth-transmutation-v1", "did": DID, "anchor": ANCHOR,
            "stages": [r0, r1, r2, r3, r4],
            "total_in": len(fragments), "total_out": len(items),
            "active_truths": len(keep),
            "transmute_rate": round(len(keep) / max(1, len(items)), 3),
            "root_hash": _sha256(json.dumps([i["sha256"] for i in items], ensure_ascii=False)),
            "artifacts": items,
        }
        return OperatorResult(success=True, data=data, operator_id=self.OPERATOR_ID,
                              operator_name=self.OPERATOR_NAME)


if __name__ == "__main__":
    # 本地仿真自检
    import sys
    sys.path.insert(0, ".")
    from registry.operator_registry import OperatorRegistry
    reg = OperatorRegistry()
    registered = [o for o in reg.list_operators() if o.get("id") == "truth-transmutation-v1" or
                  "转义" in str(o.get("name", ""))]
    print("已注册算子:", registered if registered else reg.list_operators())
    # 直接实例化测试
    op = TruthTransmutationOperator()
    test = [{"text": "真值优先原则：以交叉验证的客观事实为唯一依据", "source": "metalaw", "ts": "2026-09-11T00:00:00+00:00"},
            {"text": "临时草稿", "source": "draft", "ts": "2025-01-01T00:00:00+00:00"}]
    res = op.execute({"fragments": test})
    print("执行success:", res.success)
    print("转义率:", res.data.get("transmute_rate") if res.data else "N/A")
