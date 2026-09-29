#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全域真值转义基座·真实数据全量转义审计
输入：记忆网关 545 条真实真值 key
逻辑：复用基座五阶引擎；按类别价值赋能量权重（真实 key 短，长度不能作能量唯一依据）
确权：DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω ｜ ZONGYUAN-ROOT
"""
import json
import os
from truth_transmutation_base import TruthTransmutationBase, sha256

CATEGORY_ENERGY = {
    "metalaw": 100, "lock": 90, "root": 95, "achievement": 85,
    "architecture": 75, "deployment": 70, "service": 70, "meta": 80,
    "operator": 72, "asset": 65, "audit": 60, "optimization": 78,
    "arbitration": 75, "index": 70, "feedback": 68, "sop": 80,
}

def run():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    frags = json.load(open(os.path.join(base_dir, "truth_real_fragments.json")))
    # 类别价值能量注入
    for f in frags:
        f["energy_boost"] = CATEGORY_ENERGY.get(f["category"], 50)
    # 复用基座但能量权重由调用层提供 → 直接跑，S1用长度*来源；此处通过source映射类别
    base = TruthTransmutationBase(name="truth-audit-real", meta_class="M4")
    result = base.run(frags)
    # 汇总审计
    artifacts = result["artifacts"]
    from collections import Counter
    tier_dist = Counter(a["tier"] for a in artifacts)
    prescreen = Counter(a["prescreen"] for a in artifacts)
    sync_action = Counter(a["sync_action"] for a in artifacts)
    uid_families = len({a["uid"] for a in artifacts})
    # 域归一统计（按一级前缀）
    from collections import Counter as _C
    domain_uid = {}
    for a in artifacts:
        dom = a["text"].split(".")[0] if "." in a["text"] else a["category"]
        domain_uid.setdefault(dom, set()).add(a["uid"])
    domain_groups = len(domain_uid)
    # 类别→层级透视
    cat_tier = {}
    for a in artifacts:
        cat_tier.setdefault(a["category"], Counter())[a["tier"]] += 1
    audit = {
        "base": result["base"], "did": result["did"], "anchor": result["anchor"],
        "total_real_truths": len(artifacts),
        "tier_distribution": dict(tier_dist),
        "prescreen_distribution": dict(prescreen),
        "sync_action_distribution": dict(sync_action),
        "active_truths": result["active_truths"],
        "transmute_rate": result["transmute_rate"],
        "uid_groups": uid_families,
        "domain_groups": domain_groups,
        "norm_mode": "adaptive(short_key_domain + long_text_ngram)",
        "root_hash": result["root_hash"],
        "category_tier_top": {k: dict(v) for k, v in list(cat_tier.items())[:12]},
        "need_human_count": sum(1 for a in artifacts if a.get("need_human")),
    }
    out = os.path.join(base_dir, "truth_transmutation_real_audit.json")
    json.dump({"audit": audit, "artifacts": artifacts}, open(out, "w"), ensure_ascii=False, indent=2)
    print(json.dumps(audit, ensure_ascii=False, indent=2))
    print(f"\n[基座] 真实全量转义审计完成 → {out}")

if __name__ == "__main__":
    run()
