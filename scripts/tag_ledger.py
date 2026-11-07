#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
资产标注器 V1.0 · TAG LEDGER
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | 2026-11-07

用途：给联邦账本中缺失 type/value_score/grade 的裸索引补标注。
依据：FTG-001 文件类型门 + AVT-001 四类判据（复用 dual_layer_router）。

原则：
  1. 只补空白，不覆盖已有标注（人工结论优先）
  2. 低置信（无关键词命中、落默认 fact）标 confidence=medium 并进复核清单
  3. dry-run 先行，apply 前自动备份

用法：
  python3 scripts/tag_ledger.py --dry-run
  python3 scripts/tag_ledger.py --apply
"""
import json, os, sys, shutil, datetime, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from dual_layer_router import route

LEDGER = os.path.join(ROOT, "truth/federal-index/index_ledger.json")
BACKUP = os.path.join(ROOT, "truth/federal-index/_backup")
REVIEW = os.path.join(ROOT, "truth/quality/TAG-REVIEW-20261107.json")

STAMP = "FTG-001+AVT-001@rule-engine-v1"


def key_of(e):
    k = e.get("cloud_key")
    if k:
        return k, "cloud_key"
    p = (e.get("path") or "").split("/")[-1]
    if not p:
        return None, None
    return p.rsplit(".", 1)[0], "filename"


def plan():
    d = json.load(open(LEDGER, encoding="utf-8"))
    todo, keep, review, conflicts = [], [], [], []
    dist = collections.Counter()
    for e in d["entries"]:
        k, src = key_of(e)
        if not k:
            review.append({"mem_id": e.get("mem_id"), "reason": "无可用键"})
            continue
        r = route({"key": k, "path": e.get("path", "")})["result"]
        t, s, g = r["type"], r["value_score"], r["grade"]
        # FTG-002 目录命名空间门：关键词未命中时，由所在目录定性
        path_l = (e.get("path") or "").lower()
        if "默认" in r["basis"] and path_l:
            NS = [("meta-rules/", "rule", 88, "FTG-002 元规则目录"),
                  ("core/kernel/", "rule", 88, "FTG-002 内核目录"),
                  ("scripts/", "experience", 85, "FTG-002 脚本目录=可执行经验"),
                  ("core/docs/", "fact", 65, "FTG-002 文档目录=事实记录"),
                  ("truth/", "fact", 65, "FTG-002 真值账本目录"),
                  ("locks/", "fact", 65, "FTG-002 锁档目录"),
                  ("runtime/", "fact", 65, "FTG-002 运行时快照"),
                  ("core/ledger/", "fact", 70, "FTG-002 代际账本")]
            for ns, nt, nv, nb in NS:
                if ns in path_l:
                    t, s, g = nt, nv, ("L1" if nv >= 80 else "L2")
                    r = dict(r, basis=nb)
                    break
        already = e.get("type") and e.get("value_score")
        if already:
            keep.append(e["mem_id"])
            if e["type"] != t:
                conflicts.append({"mem_id": e["mem_id"], "key": k,
                                  "existing": e["type"], "engine": t, "action": "保留人工结论"})
            continue
        if "FTG-001" in r["basis"] or "FTG-002" in r["basis"] or s >= 80:
            conf = "high"
        elif "默认" in r["basis"]:
            conf = "low"
        else:
            conf = "medium"
        todo.append({"mem_id": e["mem_id"], "key": k, "key_source": src,
                     "path": e.get("path", ""), "type": t, "value_score": s,
                     "grade": g, "basis": r["basis"], "confidence": conf})
        dist[t] += 1
        if conf != "high":
            review.append({"mem_id": e["mem_id"], "key": k, "type": t,
                           "value_score": s, "confidence": conf, "basis": r["basis"]})
    return d, todo, keep, review, conflicts, dist


def main():
    apply = "--apply" in sys.argv
    d, todo, keep, review, conflicts, dist = plan()
    print(f"总计 {len(d['entries'])} 条")
    print(f"  待补标注 : {len(todo)}")
    print(f"  已有标注 : {len(keep)}（不覆盖）")
    print(f"  需人工复核: {len(review)}")
    print(f"  与人工结论冲突: {len(conflicts)}")
    print(f"  判定分布 : {dict(dist)}")

    if not apply:
        print("\n[dry-run] 未写盘。样例前 5 条：")
        for t in todo[:5]:
            print(f"  {t['mem_id']:<6}{t['key'][:40]:<42}{t['type']:<11}{t['value_score']:<4}{t['confidence']}")
        return

    os.makedirs(BACKUP, exist_ok=True)
    bk = os.path.join(BACKUP, "index_ledger.before-tag-20261107.json")
    if not os.path.exists(bk):
        shutil.copy2(LEDGER, bk)
        print("已备份 →", os.path.relpath(bk, ROOT))

    now = datetime.datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S+0800")
    by_id = {t["mem_id"]: t for t in todo}
    for e in d["entries"]:
        if e.get("mem_id") in by_id:
            t = by_id[e["mem_id"]]
            e.update({"type": t["type"], "value_score": t["value_score"],
                      "grade": t["grade"], "tag_basis": t["basis"],
                      "tag_confidence": t["confidence"], "tag_source": STAMP,
                      "tagged_at": now, "local_key": t["key"] if t["key_source"] == "filename" else None})
    d["tagging"] = {"round": 1, "at": now, "tagged": len(todo), "kept": len(keep),
                    "review": len(review), "conflicts": len(conflicts),
                    "source": STAMP, "distribution": dict(dist)}
    d["updated"] = now
    json.dump(d, open(LEDGER, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("已写入账本")

    os.makedirs(os.path.dirname(REVIEW), exist_ok=True)
    json.dump({"review_id": "TAG-REVIEW-20261107", "at": now, "did": "DID-BR-000002",
               "total": len(review), "items": review, "conflicts": conflicts},
              open(REVIEW, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("复核清单 →", os.path.relpath(REVIEW, ROOT), f"({len(review)} 条)")


if __name__ == "__main__":
    main()
