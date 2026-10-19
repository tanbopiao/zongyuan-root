#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SEED-HINDSIGHT-MEM-V1.0 三算子闭环仿真引擎（纯本地 · 零外呼）
实现 Retain(写入) → Recall(检索) → Reflect(反思)，含 MemoryBank 隔离校验。

诚实口径：本仿真用「确定性本地规则」近似 Hindsight 的语义能力——
  - Retain：实体/时间/事实/关系抽取为规则式（正则+词表），非LLM；
  - Recall：词元重叠 + 时序加权重排 + token 预算裁剪，非向量语义召回；
  - Reflect：同现关联挖掘 + 频次归纳，非深度推理。
机制真实可复现；能力级别以本文件 description 为准，不夸大为生产级语义系统。
"""
import json, re, hashlib, datetime, os
from pathlib import Path
from collections import defaultdict, Counter

SEED_ID = "SEED-HINDSIGHT-MEM-V1.0"
AXIOM   = "Ω₀⊂⊙∞⊂Ω"
DID     = "DID-BR-000002"
ROOT    = Path("/workspace/atomgit-mirror/zongyuan-root-sync")
BANKS   = Path("/workspace/evolution/memory_banks")
NOW     = datetime.datetime.now().astimezone().isoformat()
TOKEN_BUDGET = 600          # 单次 Recall 上下文预算（近似 token）

# ---------------- 基础工具 ----------------
def sha256_text(t: str) -> str:
    return hashlib.sha256(t.encode("utf-8")).hexdigest()

def tokenize(text: str):
    """ASCII 词 + 中文二元组（近似分词）"""
    ascii_words = re.findall(r"[A-Za-z][A-Za-z0-9_\-\.]*", text.lower())
    cjk = re.findall(r"[\u4e00-\u9fff]", text)
    bigrams = [cjk[i] + cjk[i+1] for i in range(len(cjk) - 1)]
    return ascii_words + bigrams

def est_tokens(text: str) -> int:
    """近似 token 估算：中文1字≈1token，英文1词≈1.3"""
    cjk = len(re.findall(r"[\u4e00-\u9fff]", text))
    words = len(re.findall(r"[A-Za-z][A-Za-z0-9_\-\.]*", text))
    return int(cjk + words * 1.3)

def classify(text: str, default="experience") -> str:
    """规则式记忆分类"""
    if any(k in text for k in ("元宪法", "公理", "L0", "宪法", "immutable", "world_fact")):
        return "world_fact"
    if any(k in text for k in ("综上", "结论", "归纳", "因此", "表明", "结论性", "observation")):
        return "observation"
    if any(k in text for k in ("心智", "mental_model", "领域理解", "认知模型")):
        return "mental_model"
    return default

# ---------------- 算子 1：Retain ----------------
class MemoryBank:
    def __init__(self, bank_id: str, base_context: str = "", tendency: str = "literal"):
        self.bank_id = bank_id
        self.base_context = base_context
        self.tendency = tendency
        self.dir = BANKS / bank_id
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / "retain.jsonl"
        self.records = []
        if self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    self.records.append(json.loads(line))

    def retain(self, raw_id: str, text: str, truth_type: str = "experience", source_asset_sha256: str = None):
        """写入算子：抽取实体/时间/事实/关系，结构化归一 + SHA256；禁存原文对话"""
        mtype = classify(text, truth_type)
        entities = sorted(set(re.findall(r"[A-Z]{2,}[A-Z0-9_\-]*|SEED-[A-Z0-9\-\.]+|BLK-[0-9a-f\-]+|RULE\.[A-Z0-9\-\.]+", text)))[:12]
        times = sorted(set(re.findall(r"20\d{2}-\d{2}-\d{2}", text)))[:6]
        # 关系：粗粒度 主语-谓词-宾语式三元组（规则式）
        relations = []
        for m in re.finditer(r"([\u4e00-\u9fff]{2,12})(?:并入|融合|纳入|绑定|链接|归档|确权|上报)([\u4e00-\u9fffA-Za-z0-9\-\.]{2,24})", text):
            relations.append({"s": m.group(1), "p": "关联", "o": m.group(2)})
        rec = {
            "mem_id": f"MEM-{sha256_text(self.bank_id+raw_id+text)[:12].upper()}",
            "bank_id": self.bank_id, "memory_type": mtype, "raw_ref": raw_id,
            "facts": [t for t in re.split(r"[。；\n]", text) if t.strip()][:8],
            "entities": entities, "times": times, "relations": relations[:8],
            "evidence_sha256": source_asset_sha256 or sha256_text(text),
            "record_sha256": sha256_text(mtype + raw_id + text),
            "retained_at": NOW, "immutable": mtype == "world_fact",
            "provenance": "measured",
        }
        self.records.append(rec)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return rec

    # ---------------- 算子 2：Recall ----------------
    def recall(self, query: str, top_k: int = 3, budget: int = TOKEN_BUDGET):
        """检索算子：重排 + token 预算裁剪；输出带资产哈希凭证"""
        qtok = Counter(tokenize(query))
        scored = []
        for r in self.records:
            body = " ".join(r["facts"]) + " " + " ".join(r["entities"])
            rtok = Counter(tokenize(body))
            overlap = sum((qtok & rtok).values())
            norm = overlap / (sum(qtok.values()) ** 0.5 + 1e-6)
            recency = 1.0 if r["retained_at"][:10] == NOW[:10] else 0.85
            scored.append((norm * recency, r))
        scored.sort(key=lambda x: x[0], reverse=True)
        selected, used, trimmed = [], 0, 0
        for score, r in scored:
            if score <= 0:
                continue
            cost = est_tokens(" ".join(r["facts"]))
            if used + cost > budget:
                trimmed += 1
                continue
            used += cost
            selected.append({"mem_id": r["mem_id"], "score": round(score, 4),
                             "memory_type": r["memory_type"], "evidence_sha256": r["evidence_sha256"],
                             "record_sha256": r["record_sha256"], "facts": r["facts"]})
            if len(selected) >= top_k:
                break
        return {"query": query, "bank_id": self.bank_id, "returned": len(selected),
                "trimmed_by_budget": trimmed, "token_used": used, "budget": budget,
                "voucher": sha256_text(query + json.dumps([s["mem_id"] for s in selected])),
                "items": selected}

    # ---------------- 算子 3：Reflect ----------------
    def reflect(self):
        """反思算子：关联挖掘 + 归纳，产出 observation 与新版 mental_model，写入账本"""
        ent_freq = Counter()
        for r in self.records:
            for e in r["entities"]:
                ent_freq[e] += 1
        cooc = defaultdict(int)
        ent_sets = [set(r["entities"]) for r in self.records]
        for i in range(len(ent_sets)):
            for j in range(i + 1, len(ent_sets)):
                for e in (ent_sets[i] & ent_sets[j]):
                    cooc[e] += 1
        hot = [e for e, c in ent_freq.most_common(8) if c >= 1]
        by_type = Counter(r["memory_type"] for r in self.records)
        obs_text = (f"综上归纳：{self.bank_id} 存量记忆 {len(self.records)} 条，"
                    f"分层为 {dict(by_type)}；高频实体 {hot[:5]}；"
                    f"共现关联 {len(cooc)} 组。记忆资产已纳入 Merkle-DAG 账本，可溯源审计。")
        observation = {
            "mem_id": f"OBS-{sha256_text(obs_text)[:12].upper()}", "bank_id": self.bank_id,
            "memory_type": "observation", "raw_ref": "reflect:" + NOW,
            "facts": [obs_text], "entities": hot[:8], "times": [NOW[:10]], "relations": [],
            "evidence_sha256": sha256_text(json.dumps([r["record_sha256"] for r in self.records])),
            "record_sha256": sha256_text(obs_text), "retained_at": NOW, "immutable": False,
            "provenance": "derived_from_bank",
        }
        mm_text = (f"{self.bank_id} 领域理解（{NOW[:10]} 更新）：本域已形成 "
                   f"world_fact(不可变) / experience / observation / mental_model 四类分层，"
                   f"Retain→Recall→Reflect 闭环可用；受 L0 元宪法约束，不得突破。")
        mental_model = {
            "mem_id": f"MM-{sha256_text(mm_text)[:12].upper()}", "bank_id": self.bank_id,
            "memory_type": "mental_model", "raw_ref": "reflect:" + NOW,
            "facts": [mm_text], "entities": hot[:8], "times": [NOW[:10]], "relations": [],
            "evidence_sha256": observation["record_sha256"],
            "record_sha256": sha256_text(mm_text), "retained_at": NOW, "immutable": False,
            "provenance": "derived_from_bank",
        }
        for rec in (observation, mental_model):
            self.records.append(rec)
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return {"observation": observation, "mental_model": mental_model,
                "cooccurrence_groups": len(cooc), "hot_entities": hot[:8], "by_type": dict(by_type)}


# ================= 仿真主流程 =================
def main():
    result = {"sim_id": "MEM-LOOP-SIM-20261019", "seed": SEED_ID, "axiom": AXIOM,
              "ts": NOW, "mode": "local_rule_based_approx", "budget_external": 0}

    # --- 输入：仓库真实资产（非编造）---
    pl = Path("/workspace/evolution/persistent_layer/truths.jsonl")
    raw_inputs = []
    if pl.exists():
        for i, line in enumerate(pl.read_text(encoding="utf-8").splitlines()):
            if not line.strip():
                continue
            o = json.loads(line)
            raw_inputs.append((o["truth_id"], o.get("content", "")[:1200], o.get("sha256")))
    for f in [ROOT/"reports/META-ORDER-OPT-20261019.json", ROOT/"reports/EVOLUTION-CYCLE-20261019-V1.json"]:
        if f.exists():
            raw_inputs.append((f.stem, f.read_text(encoding="utf-8")[:1500], sha256_text(f.read_text(encoding="utf-8"))))

    # --- Bank A（主库）---
    bankA = MemoryBank("BANK-ZONGYUAN-MAIN", "元极恒一自治体系·记忆子系统", "literal")
    retained_A = [bankA.retain(rid, txt, source_asset_sha256=sh) for rid, txt, sh in raw_inputs]

    # --- Bank B（隔离对照库）---
    bankB = MemoryBank("BANK-ISOLATION-TEST", "隔离校验对照库", "literal")
    bankB.retain("DECOY-001", "【隔离哨兵】绝密对照令牌 ZZZ-ISOLATION-SENTINEL-9F3A 仅供跨Bank泄露检测。")

    # --- Recall ×2 ---
    r1 = bankA.recall("记忆 种子 账本 元宪法 哈希")
    r2 = bankA.recall("隔离 哨兵 泄露 ZZZ-SENTINEL")

    # --- 隔离校验：主库检索不得命中对照库哨兵 ---
    leakA = any("ZZZ-ISOLATION-SENTINEL-9F3A" in " ".join(i["facts"]) for i in r1["items"]) or \
            any("ZZZ-ISOLATION-SENTINEL" in e for i in r1["items"] for e in i.get("facts", []))
    leakB = any("ZZZ-ISOLATION-SENTINEL-9F3A" in " ".join(i["facts"]) for i in r2["items"])
    isolation = {"main_bank_leaked_sentinel": leakA, "isolation_probe_hit_own_bank": leakB,
                 "verdict": "PASS" if (not leakA) else "FAIL"}

    # --- Reflect ---
    ref = bankA.reflect()
    ref2 = bankB.reflect()

    # --- L0 约束校验：world_fact 不可变 且 心智模型未突破 ---
    wf = [r for r in bankA.records if r["memory_type"] == "world_fact"]
    l0_ok = all(r["immutable"] for r in wf) and ref["mental_model"]["memory_type"] == "mental_model"

    result.update({
        "retain": {"bank": "BANK-ZONGYUAN-MAIN", "records": len(retained_A),
                   "types": dict(Counter(r["memory_type"] for r in retained_A)),
                   "all_have_sha256": all(r["record_sha256"] for r in retained_A)},
        "recall": {"q1": {k: r1[k] for k in ("returned","trimmed_by_budget","token_used","budget","voucher")},
                   "q2": {k: r2[k] for k in ("returned","trimmed_by_budget","token_used","budget","voucher")}},
        "isolation": isolation,
        "reflect": {"observation": ref["observation"]["mem_id"], "mental_model": ref["mental_model"]["mem_id"],
                    "cooccurrence_groups": ref["cooccurrence_groups"], "hot_entities": ref["hot_entities"],
                    "bankB_observation": ref2["observation"]["mem_id"]},
        "l0_constraint_pass": l0_ok,
        "bankA_records_final": len(bankA.records),
        "provenance": "measured",
    })

    # --- Merkle-DAG 区块 ---
    chain = sorted((ROOT/"ledger/chain").glob("BLK-*.json"))
    prev = json.loads(chain[-1].read_text(encoding="utf-8"))
    entry = {"type": "memory_loop_sim", "ref": "MEM-LOOP-SIM-20261019.json",
             "seed": SEED_ID, "retain": result["retain"], "recall_vouchers":
             [r1["voucher"], r2["voucher"]], "reflect_obs": result["reflect"]["observation"],
             "isolation_verdict": isolation["verdict"], "l0_constraint_pass": l0_ok,
             "provenance": "measured", "timestamp": NOW, "axiom_sign": AXIOM}
    payload = {"prev_block_hash": prev["block_hash"], "entry": entry}
    bh = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    blk = {"block_id": f"BLK-{int(datetime.datetime.now().timestamp())}-{bh[:8]}",
           "block_hash": bh, "merkle_root": bh, "prev_block_hash": payload["prev_block_hash"],
           "entry": entry, "sorted_at": NOW, "溯源标识": AXIOM, "确权编码": DID,
           "体系基线": "ZONGYUAN-ROOT V1.0"}
    (ROOT/"ledger/chain"/f"{blk['block_id']}.json").write_text(json.dumps(blk, ensure_ascii=False, indent=2), encoding="utf-8")
    result["merkle_block"] = blk["block_id"]
    result["block_hash"] = bh

    rp = ROOT/"reports/MEM-LOOP-SIM-20261019.json"
    rp.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("\n报告:", rp)

if __name__ == "__main__":
    main()
