#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地嵌入真语义召回后端（接入 SEED-HINDSIGHT-MEM-V1.0 记忆子系统）
模型：minishlab/potion-multilingual-128M（静态蒸馏嵌入 · dim=256 · 无需 torch · CPU 推理）
经 hf-mirror 下载，纯本地推理，零 LLM 额度、零运行时外呼。

诚实口径：静态嵌入（词表级蒸馏）≠ 上下文动态嵌入（如 BERT/LLM）。
本后端为「真预训练语义向量」，可捕获同义/近义，但对深层上下文与长程指代弱于动态模型。

评测口径：以 expected 记忆的排名（rank@1/@3）衡量召回质量，而非绝对余弦阈值
（静态嵌入余弦值域压缩在 0.1~0.5，绝对阈值易误伤，故本版改用 top-k 排序评测）。
"""
import os, sys, json, hashlib, datetime, time
import numpy as np
from pathlib import Path

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
os.environ.setdefault("HF_HOME", "/workspace/atomgit-mirror/zongyuan-root-sync/01_ASSETS/models/embedding")

sys.path.insert(0, str(Path(__file__).parent))
from memory_loop_sim import MemoryBank, est_tokens, sha256_text, ROOT

MODEL_NAME = "minishlab/potion-multilingual-128M"


class SemanticIndex:
    """本地嵌入索引（余弦相似度语义召回）"""

    def __init__(self, model_name: str = MODEL_NAME):
        from model2vec import StaticModel
        t = time.time()
        self.model = StaticModel.from_pretrained(model_name)
        self.model_name = model_name
        self.load_sec = round(time.time() - t, 2)

    def _norm(self, texts):
        v = np.asarray(self.model.encode(list(texts)), dtype="float32")
        if v.ndim == 1:
            v = v[None, :]
        return v / (np.linalg.norm(v, axis=1, keepdims=True) + 1e-9)

    def score_all(self, bank: "MemoryBank", query: str):
        """返回每个记忆的余弦分（透明可查）"""
        bodies = [" ".join(r["facts"]) + " " + " ".join(r["entities"]) for r in bank.records]
        E = self._norm(bodies)
        q = self._norm([query])[0]
        return list(zip([r["mem_id"] for r in bank.records], (E @ q).tolist()))

    def semantic_recall(self, bank: "MemoryBank", query: str, top_k: int = 5,
                        budget: int = 600, threshold: float = 0.0):
        """语义召回：嵌入余弦排序 → token 预算裁剪；输出带凭证"""
        if not bank.records:
            return {"query": query, "returned": 0, "items": [], "token_used": 0,
                    "trimmed_by_budget": 0, "budget": budget, "model": self.model_name,
                    "items_ids": [], "voucher": sha256_text(query)}
        scored = sorted(self.score_all(bank, query), key=lambda x: -x[1])
        by_id = {r["mem_id"]: r for r in bank.records}
        selected, used, trimmed = [], 0, 0
        for mem_id, score in scored:
            if score < threshold:
                continue
            r = by_id[mem_id]
            cost = est_tokens(" ".join(r["facts"]))
            if used + cost > budget:
                trimmed += 1
                continue
            used += cost
            selected.append({"mem_id": mem_id, "score": round(score, 4),
                             "memory_type": r["memory_type"],
                             "evidence_sha256": r["evidence_sha256"],
                             "record_sha256": r["record_sha256"], "facts": r["facts"][:2]})
            if len(selected) >= top_k:
                break
        return {"query": query, "bank_id": bank.bank_id, "returned": len(selected),
                "trimmed_by_budget": trimmed, "token_used": used, "budget": budget,
                "model": self.model_name, "threshold": threshold, "items": selected,
                "items_ids": [s["mem_id"] for s in selected],
                "voucher": sha256_text("semantic" + query + json.dumps([s["mem_id"] for s in selected]))}


def rank_of(expected, id_list):
    return (id_list.index(expected) + 1) if expected in id_list else None


def controlled_probe(idx):
    """受控对照探针：含『词元陷阱』干扰项，检验语义 vs 词元谁抓得住真目标。
    （合成构造，明确标注 synthetic_controlled，非仓库真实数据）"""
    b = MemoryBank("BANK-CONTROLLED-PROBE", "受控对照库", "literal")
    items = [
        ("C1-correct", "跨库记忆隔离规则：不同项目与用户必须使用独立 MemoryBank，禁止跨库读取，防止记忆泄露。"),
        ("D1-lexical-trap", "项目记忆库命名规范：MemoryBank 目录统一放在 memory_banks 下，按项目名建子目录，便于归档管理。"),
        ("D2-lexical-trap", "用户记忆索引文件格式说明：记录包含 memory 字段，项目编号与用户编号并列存储。"),
    ]
    existing = {r["raw_ref"] for r in b.records}
    for rid, txt in items:
        if rid not in existing:
            b.retain(rid, txt)
    q = "不同项目之间的记忆能不能互相读取"
    lex = b.recall(q, top_k=5)
    sem = idx.semantic_recall(b, q, top_k=5, threshold=0.0)
    c1 = next(r["mem_id"] for r in b.records if r["raw_ref"] == "C1-correct")
    by = {r["mem_id"]: r["raw_ref"] for r in b.records}
    rank_lex = rank_of(c1, [i["mem_id"] for i in lex["items"]])
    rank_sem = rank_of(c1, sem["items_ids"])
    top_sem = sorted(idx.score_all(b, q), key=lambda x: -x[1])[:3]
    return {
        "type": "synthetic_controlled", "query": q, "target": c1, "records": by,
        "lexical_rank_target": rank_lex,
        "semantic_rank_target": rank_sem,
        "lexical_order": [(by[i["mem_id"]], i["score"]) for i in lex["items"][:3]],
        "semantic_order": [(by[m], round(s, 4)) for m, s in top_sem],
        "verdict": "semantic_wins" if (rank_sem or 99) < (rank_lex or 99) else
                   ("tie" if rank_sem == rank_lex else "lexical_wins"),
    }


def main():
    bank = MemoryBank("BANK-ZONGYUAN-MAIN", "元极恒一自治体系·记忆子系统", "literal")
    idx = SemanticIndex()

    records = [{"mem_id": r["mem_id"], "raw_ref": r["raw_ref"], "type": r["memory_type"]}
               for r in bank.records]
    # expected 目标：SEED 种子真值记录
    expected = next((r["mem_id"] for r in bank.records if r["raw_ref"].startswith("SEED-HINDSIGHT")), None)

    QUERIES = [
        ("LEX_overlap", "记忆 种子 账本 元宪法 哈希"),
        ("PARAPHRASE", "外部记忆能力怎么装进主程序里"),
        ("CONCEPT", "怎样保证不同项目之间的记忆不会互相串门"),
    ]

    report = {"sim_id": "MEM-LOOP-SEMANTIC-20261019",
              "ts": datetime.datetime.now().astimezone().isoformat(),
              "model": idx.model_name, "model_load_sec": idx.load_sec, "dim": 256,
              "bank_records": len(bank.records), "records": records,
              "expected_mem_id": expected, "provenance": "measured", "results": [],
              "metrics": {}}

    for tag, q in QUERIES:
        lex = bank.recall(q, top_k=5)
        sem = idx.semantic_recall(bank, q, top_k=5, threshold=0.0)
        scores = idx.score_all(bank, q)
        report["results"].append({
            "tag": tag, "query": q,
            "lexical": {"ids": [i["mem_id"] for i in lex["items"]],
                        "rank_expected": rank_of(expected, [i["mem_id"] for i in lex["items"]])},
            "semantic": {"ids": sem["items_ids"],
                         "rank_expected": rank_of(expected, sem["items_ids"]),
                         "top_scores": [[m, round(s, 4)] for m, s in sorted(scores, key=lambda x: -x[1])[:3]]},
        })

    def acc(key):
        r1 = sum(1 for x in report["results"] if x[key]["rank_expected"] == 1)
        r3 = sum(1 for x in report["results"]
                 if x[key]["rank_expected"] is not None and x[key]["rank_expected"] <= 3)
        return {"hit@1": f"{r1}/{len(QUERIES)}", "hit@3": f"{r3}/{len(QUERIES)}"}
    report["metrics"] = {"lexical": acc("lexical"), "semantic": acc("semantic")}
    report["controlled_probe"] = controlled_probe(idx)

    # Merkle-DAG 区块
    chain = sorted((ROOT / "ledger/chain").glob("BLK-*.json"))
    prev = json.loads(chain[-1].read_text(encoding="utf-8"))
    entry = {"type": "semantic_recall_upgrade", "ref": "MEM-LOOP-SEMANTIC-20261019.json",
             "model": idx.model_name, "dim": 256, "load_sec": idx.load_sec,
             "metrics": report["metrics"], "results": report["results"], "provenance": "measured",
             "timestamp": report["ts"], "axiom_sign": "Ω₀⊂⊙∞⊂Ω"}
    payload = {"prev_block_hash": prev["block_hash"], "entry": entry}
    bh = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    blk = {"block_id": f"BLK-{int(datetime.datetime.now().timestamp())}-{bh[:8]}", "block_hash": bh,
           "merkle_root": bh, "prev_block_hash": payload["prev_block_hash"], "entry": entry,
           "sorted_at": report["ts"], "溯源标识": "Ω₀⊂⊙∞⊂Ω", "确权编码": "DID-BR-000002",
           "体系基线": "ZONGYUAN-ROOT V1.0"}
    (ROOT / "ledger/chain" / f"{blk['block_id']}.json").write_text(
        json.dumps(blk, ensure_ascii=False, indent=2), encoding="utf-8")
    report["merkle_block"] = blk["block_id"]
    report["block_hash"] = bh

    (ROOT / "reports/MEM-LOOP-SEMANTIC-20261019.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("记忆库记录:")
    for r in records:
        mark = " ←expected" if r["mem_id"] == expected else ""
        print(f"  {r['mem_id']}  [{r['type']}]  {r['raw_ref']}{mark}")
    print()
    for r in report["results"]:
        print(f"[{r['tag']:<12}] «{r['query']}»")
        print(f"   词元: rank={r['lexical']['rank_expected']}  ids={r['lexical']['ids']}")
        print(f"   语义: rank={r['semantic']['rank_expected']}  ids={r['semantic']['ids']}")
        print(f"         top余弦={r['semantic']['top_scores']}")
    print("\n命中率:", json.dumps(report["metrics"], ensure_ascii=False))
    cp = report["controlled_probe"]
    print(f"受控探针 «{cp['query']}»")
    print(f"   目标 C1 排名 → 词元={cp['lexical_rank_target']}  语义={cp['semantic_rank_target']}  ⇒ {cp['verdict']}")
    print(f"   词元序: {cp['lexical_order']}")
    print(f"   语义序: {cp['semantic_order']}")
    print(f"区块 {blk['block_id']} | 模型载入 {idx.load_sec}s")


if __name__ == "__main__":
    main()
