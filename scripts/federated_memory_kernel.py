#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
L2 联邦记忆内核 · 多节点治理层实现（承接 SEED-FEDERATED-MEM-KERNEL-V2.0）
五阶段治理：propose → validate → vote → archive → confirm
叠加：分层价值打分 / 时序衰减 / 软遗忘 / 分级联邦共识 / 数据边界 / 双层隔离

诚实口径（不夸大）：
  · 本地两节点仿真——同进程内两个 MemoryBank 充当两个节点，非真实分布式网络；
  · 共识为确定性多数票规则，非拜占庭容错、无网络分区/延迟/恶意节点建模；
  · 跨节点同步仅传「摘要」，原始 facts 不出节点（数据边界由构造强制）。
"""
import json, sys, hashlib, datetime
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent))
from memory_loop_sim import MemoryBank, sha256_text, NOW, ROOT

FED = Path("/workspace/evolution/federation")
AXIOM = "Ω₀⊂⊙∞⊂Ω"
DID = "DID-BR-000002"

# ---------- 分层价值打分 / 时序衰减 / 软遗忘 阈值 ----------
VALUE_BASE = {"world_fact": 1.00, "mental_model": 0.80, "observation": 0.60, "experience": 0.40}
HIGH_VALUE_TH = 0.60      # ≥ 该值 → 跨节点收敛（分级联邦共识）
SOFT_FORGET_TH = 0.25     # < 该值 → 软遗忘（非删除）
ADMISSION_TH = 0.25       # 准入投票门限：低于此值 → 未获准入 → 降级软遗忘（非删除）
DECAY_RATE = 0.08         # 每次衰减率（指数）


def value_score(mtype, corroboration=0, hits=0):
    return round(min(1.0, VALUE_BASE.get(mtype, 0.4) + 0.15 * corroboration + 0.10 * hits), 4)


def decay(score, age_days, rate=DECAY_RATE):
    return round(score * (1.0 - rate) ** age_days, 4)


class FedNode:
    """联邦节点：持有一个 L1 MemoryBank（独立目录 → 物理隔离）"""

    def __init__(self, node_id, bank_id, base_context=""):
        self.node_id = node_id
        self.bank = MemoryBank(bank_id, base_context, "literal")
        self.life = {}                       # mem_id -> {state, value, memory_type}
        self.exempt = {"world_fact"}          # world_fact 豁免衰减与软遗忘

    def retain(self, raw_id, text):
        return self.bank.retain(raw_id, text)


class Federation:
    """联邦治理层（本地两节点仿真）"""

    def __init__(self, d=FED):
        self.d = Path(d)
        self.d.mkdir(parents=True, exist_ok=True)
        self.nodes = {}
        self.proposals = []
        self.confirmed = {}                   # key -> canonical record
        self.sync = []                        # 跨节点摘要（不含 facts）
        self.conflicts = []

    def register(self, node):
        self.nodes[node.node_id] = node

    # ---------- 阶段 1：提案 ----------
    def propose(self, node, rec, key, corroboration=0, age_days=0):
        return {"prop_id": f"PROP-{sha256_text(key + rec['mem_id'])[:10].upper()}",
                "key": key, "mem_id": rec["mem_id"], "node": node.node_id,
                "memory_type": rec["memory_type"], "value_digest": rec["record_sha256"],
                "facts_digest": sha256_text(" ".join(rec["facts"])),
                "corroboration": corroboration, "age_days": age_days, "ts": NOW}

    # ---------- 阶段 2：校验（哈希 + L0） ----------
    def validate(self, prop, rec):
        ok_hash = bool(prop["value_digest"]) and prop["value_digest"] == rec["record_sha256"]
        l0_ok = (rec["memory_type"] != "world_fact") or bool(rec.get("immutable"))
        prop["validated"] = bool(ok_hash and l0_ok)
        prop["validate_detail"] = {"hash_ok": ok_hash, "l0_ok": l0_ok}
        return prop

    # ---------- 阶段 3：投票（分层价值 + 衰减） ----------
    def vote(self, prop, rec):
        base = value_score(rec["memory_type"], prop["corroboration"])
        exempt = rec["memory_type"] in self.nodes[prop["node"]].exempt
        final = base if exempt else decay(base, prop["age_days"])
        votes = {nid: ("yes" if final >= ADMISSION_TH else "no") for nid in self.nodes}
        yes = sum(1 for v in votes.values() if v == "yes")
        prop.update({"base_value": base, "value": final, "decay_exempt": exempt,
                     "votes": votes, "vote_yes": yes,
                     "quorum": yes * 2 > len(self.nodes)})
        return prop

    # ---------- 阶段 4+5：归档 + 确权（分级共识 / 软遗忘 / 冲突） ----------
    def archive_confirm(self, prop, rec):
        node = self.nodes[prop["node"]]

        # 阶段4：准入判定 → 生命周期分派（软遗忘先于价值分级，避免被回滚拦截）
        if not prop["validated"]:
            st = "rejected"
        elif not prop["quorum"]:
            st = "soft_forgotten"          # 未获准入 → 降级保留（可审计，非删除）
        elif prop["value"] >= HIGH_VALUE_TH:
            st = "confirmed"               # 高价值 → 跨节点收敛
        else:
            st = "confirmed_local"         # 普通 → 本地轻量，不出节点
        prop["state"] = st

        # 阶段5a：冲突仲裁（同键异值）——先仲裁，后同步，避免同步已被取代的摘要
        retraction = None
        if st in ("confirmed", "confirmed_local"):
            prior = self.confirmed.get(prop["key"])
            if prior and prior["value_digest"] != prop["value_digest"]:
                new_wins = prop["value"] > prior["value"]          # 平局 → 既有 canonical 保有
                winner, loser = (prop, prior) if new_wins else (prior, prop)
                self.conflicts.append({
                    "key": prop["key"], "winner_mem": winner["mem_id"], "winner_value": winner["value"],
                    "loser_mem": loser["mem_id"], "loser_value": loser["value"],
                    "resolution": "higher_value_wins" if new_wins else "canonical_holds_on_tie_or_lower"})
                winner["conflict_flag"] = True
                self.confirmed[prop["key"]] = winner
                loser["state"] = "conflict_superseded"
                self.nodes[loser["node"]].life[loser.get("mem_id")] = {
                    "state": "conflict_superseded", "value": loser["value"],
                    "memory_type": loser.get("memory_type"), "key": prop["key"]}
                if new_wins and prior.get("summary_id"):
                    # 追加式撤回（不可变账本语义：不删除，追加 retraction 记录）
                    retraction = {"type": "retraction", "superseded_summary": prior["summary_id"],
                                  "superseded_mem": prior["mem_id"], "by_mem": prop["mem_id"],
                                  "ts": NOW, "reason": "higher_value_canonical_supersede"}
                    self.sync.append(retraction)
                    prop["retraction"] = retraction["superseded_summary"]
            else:
                self.confirmed[prop["key"]] = prop

        # 阶段5b：跨节点摘要同步（仅 canonical 且 confirmed）
        if prop["state"] == "confirmed":
            summary = {"summary_id": f"SUM-{sha256_text(prop['key'] + prop['value_digest'])[:10].upper()}",
                       "key": prop["key"], "mem_id": rec["mem_id"], "origin_node": node.node_id,
                       "memory_type": rec["memory_type"], "value": prop["value"],
                       "value_digest": prop["value_digest"], "state": "confirmed",
                       "authorize_sign": AXIOM, "ts": NOW}
            assert "facts" not in summary, "数据边界违规：摘要携带原始 facts"
            self.sync.append(summary)
            prop["summary_id"] = summary["summary_id"]

        node.life[rec["mem_id"]] = {"state": prop["state"], "value": prop["value"],
                                    "memory_type": rec["memory_type"], "key": prop["key"]}
        return prop

    # ---------- 跨节点读取（双层隔离强制） ----------
    def read_across(self, reader: FedNode, mem_id):
        retracted = {r["superseded_mem"] for r in self.sync if r.get("type") == "retraction"}
        allowed = (any(s.get("mem_id") == mem_id for s in self.sync if s.get("type") != "retraction")
                   and mem_id not in retracted)
        return {"reader": reader.node_id, "mem_id": mem_id,
                "allowed": allowed, "reason": "confirmed 态方可跨节点读取" if allowed else "非 confirmed 态：跨节点边界拒绝"}

    def govern(self, node, rec, key, corroboration=0, age_days=0):
        trace = []
        p = self.propose(node, rec, key, corroboration, age_days); trace.append("propose")
        self.validate(p, rec); trace.append("validate")
        self.vote(p, rec); trace.append("vote")
        self.archive_confirm(p, rec); trace.append("archive"); trace.append("confirm")
        p["trace"] = trace
        self.proposals.append({k: v for k, v in p.items() if k != "votes"})
        return p

    def persist(self):
        (self.d / "proposals.jsonl").write_text(
            "\n".join(json.dumps(p, ensure_ascii=False) for p in self.proposals) + "\n", encoding="utf-8")
        (self.d / "sync.jsonl").write_text(
            "\n".join(json.dumps(s, ensure_ascii=False) for s in self.sync) + "\n", encoding="utf-8")
        (self.d / "confirmed.json").write_text(
            json.dumps({k: {"mem_id": v["mem_id"], "value": v["value"], "value_digest": v["value_digest"]}
                        for k, v in self.confirmed.items()}, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    fed = Federation()
    A = FedNode("NODE-A", "BANK-FED-NODE-A", "联邦仿真·节点A")
    B = FedNode("NODE-B", "BANK-FED-NODE-B", "联邦仿真·节点B")
    fed.register(A); fed.register(B)

    checks = []

    def ck(name, cond, detail):
        checks.append({"check": name, "pass": bool(cond), "detail": detail})

    # --- 场景 1：高价值全链路（跨节点收敛） ---
    r_wf = A.retain("WF-L0-001", "L0元宪法公理：记忆资产不得违背顶层公理体系，变更需人工审批。")
    p1 = fed.govern(A, r_wf, "K-WF-001", corroboration=2, age_days=30)
    ck("S1 高价值跨节点收敛", p1["state"] == "confirmed" and p1.get("summary_id"),
       f"state={p1['state']} value={p1['value']} summary={p1.get('summary_id')}")

    # --- 场景 2：普通任务记忆本地轻量（不出节点） ---
    r_exp = A.retain("EXP-001", "节点A执行了一次记忆归档任务，产生执行日志与原始任务记录。")
    p2 = fed.govern(A, r_exp, "K-EXP-001", corroboration=0, age_days=0)
    ck("S2 普通记忆仅本地（分级共识）", p2["state"] == "confirmed_local" and not p2.get("summary_id"),
       f"state={p2['state']} value={p2['value']} 同步={'否' if not p2.get('summary_id') else '是'}")

    # --- 场景 3：world_fact 豁免衰减 ---
    ck("S3 world_fact 豁免时序衰减", p1["decay_exempt"] is True and p1["value"] == p1["base_value"],
       f"base={p1['base_value']} final={p1['value']} exempt={p1['decay_exempt']}（age=30d 未衰减）")

    # --- 场景 4：软遗忘（非删除，可审计） ---
    r_dec = A.retain("EXP-OLD-001", "久远执行记录：一次性临时任务，长期未被任何检索命中。")
    p4 = fed.govern(A, r_dec, "K-EXP-OLD", corroboration=0, age_days=40)
    ck("S4 软遗忘而非删除", p4["state"] == "soft_forgotten" and p4["value"] < SOFT_FORGET_TH,
       f"state={p4['state']} value={p4['value']}（<{SOFT_FORGET_TH}）本地记录仍存在="
       f"{(A.bank.dir/'retain.jsonl').exists()}")

    # --- 场景 5：冲突仲裁（同键异值，低价值者被既有 canonical 压制） ---
    r_a_obs = A.retain("OBS-A-001", "综上归纳：本域记忆具备完整生命周期，结论性观察已绑定证据哈希。")
    pa = fed.govern(A, r_a_obs, "K-OBS-CONFLICT", corroboration=3, age_days=0)   # value=1.00
    r_b_obs = B.retain("OBS-B-001", "综上归纳：本域记忆无生命周期，结论性观察未绑定证据。")
    pb = fed.govern(B, r_b_obs, "K-OBS-CONFLICT", corroboration=0, age_days=0)   # value=0.60
    ck("S5 冲突仲裁·低价值被压制", fed.confirmed["K-OBS-CONFLICT"]["mem_id"] == r_a_obs["mem_id"]
       and pb["state"] == "conflict_superseded" and pa["state"] == "confirmed",
       f"winner_value={fed.confirmed['K-OBS-CONFLICT']['value']} loser_value={pb['value']} loser_state={pb['state']}")

    # --- 场景 5b：更高价值 newcomer 取代 canonical（追加式撤回，非删除） ---
    r_a_mm = A.retain("MM-A-001", "心智模型：本域形成四类记忆分层的领域理解。")
    pm1 = fed.govern(A, r_a_mm, "K-MM-CONFLICT", corroboration=0, age_days=0)    # 0.80 → confirmed
    r_b_mm = B.retain("MM-B-001", "心智模型：本域形成四层记忆架构并已并入联邦账本的领域理解。")
    pm2 = fed.govern(B, r_b_mm, "K-MM-CONFLICT", corroboration=2, age_days=0)    # 1.00 > 0.80 → 取代
    retracted = [s for s in fed.sync if s.get("type") == "retraction"]
    ck("S5b 更优者取代·追加式撤回", pm2["state"] == "confirmed" and pm1["state"] == "conflict_superseded"
       and len(retracted) == 1 and retracted[0]["superseded_mem"] == r_a_mm["mem_id"],
       f"new_confirmed={pm2['state']} old_state={pm1['state']} 撤回记录={len(retracted)}")

    # --- 场景 5c：已撤回记忆禁止跨节点读取 ---
    rd_retr = fed.read_across(B, r_a_mm["mem_id"])
    ck("S5c 撤回后跨节点读取被拒", rd_retr["allowed"] is False, f"allowed={rd_retr['allowed']} ({rd_retr['reason']})")

    # --- 场景 6：双层隔离（非 confirmed 禁止跨节点读取） ---
    rd_ok = fed.read_across(B, r_wf["mem_id"])      # 已 confirmed，允许
    rd_no = fed.read_across(B, r_exp["mem_id"])     # 仅本地，拒绝
    ck("S6 双层隔离·跨节点边界", rd_ok["allowed"] is True and rd_no["allowed"] is False,
       f"confirmed读={rd_ok['allowed']} 未confirmed读={rd_no['allowed']}")

    # --- 场景 7：数据边界（摘要不含原始 facts） ---
    sums = [s for s in fed.sync if s.get("type") != "retraction"]
    ck("S7 数据边界·摘要不含原文", len(sums) >= 1 and all("facts" not in s for s in sums),
       f"摘要数={len(sums)} 撤回数={len(fed.sync)-len(sums)} 均无 facts 字段={all('facts' not in s for s in sums)}")

    # --- 场景 8：校验拦截（篡改哈希必被拒） ---
    r_t = A.retain("TAMPER-001", "篡改样本：记录哈希将被人为改写以测试校验拦截。")
    p8 = fed.propose(A, r_t, "K-TAMPER")
    p8["value_digest"] = "deadbeef" * 8            # 篡改
    fed.validate(p8, r_t); fed.vote(p8, r_t); fed.archive_confirm(p8, r_t)
    ck("S8 校验拦截·篡改哈希被拒", p8["state"] == "rejected" and p8["validate_detail"]["hash_ok"] is False,
       f"state={p8['state']} hash_ok={p8['validate_detail']['hash_ok']}")

    failed = [c for c in checks if not c["pass"]]
    report = {"sim_id": "FED-MEM-L2-20261019", "seed": "SEED-FEDERATED-MEM-KERNEL-V2.0",
              "ts": NOW, "mode": "local_two_node_simulation", "network": "none (in-process)",
              "nodes": list(fed.nodes), "checks": checks,
              "passed": f"{len(checks)-len(failed)}/{len(checks)}",
              "verdict": "PASS" if not failed else "FAIL",
              "value_model": {"VALUE_BASE": VALUE_BASE, "HIGH_VALUE_TH": HIGH_VALUE_TH,
                              "SOFT_FORGET_TH": SOFT_FORGET_TH, "DECAY_RATE": DECAY_RATE},
              "sync_summaries": len(fed.sync), "conflicts": fed.conflicts,
              "confirmed_keys": list(fed.confirmed),
              "honest": {"distributed": False, "byzantine_fault_tolerance": False,
                         "consensus_rule": "deterministic majority vote"},
              "provenance": "measured"}
    fed.persist()

    # --- Merkle-DAG 区块 ---
    chain = sorted((ROOT / "ledger/chain").glob("BLK-*.json"))
    prev = json.loads(chain[-1].read_text(encoding="utf-8"))
    entry = {"type": "federated_l2_implementation", "ref": "FED-MEM-L2-20261019.json",
             "seed": "SEED-FEDERATED-MEM-KERNEL-V2.0", "passed": report["passed"],
             "verdict": report["verdict"], "checks": [c["check"] for c in checks],
             "sync_summaries": len(fed.sync), "conflicts": len(fed.conflicts),
             "provenance": "measured", "timestamp": NOW, "axiom_sign": AXIOM}
    payload = {"prev_block_hash": prev["block_hash"], "entry": entry}
    bh = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    blk = {"block_id": f"BLK-{int(datetime.datetime.now().timestamp())}-{bh[:8]}", "block_hash": bh,
           "merkle_root": bh, "prev_block_hash": payload["prev_block_hash"], "entry": entry,
           "sorted_at": NOW, "溯源标识": AXIOM, "确权编码": DID, "体系基线": "ZONGYUAN-ROOT V1.0"}
    (ROOT / "ledger/chain" / f"{blk['block_id']}.json").write_text(
        json.dumps(blk, ensure_ascii=False, indent=2), encoding="utf-8")
    report["merkle_block"] = blk["block_id"]; report["block_hash"] = bh

    (ROOT / "reports/FED-MEM-L2-20261019.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    for c in checks:
        print(f"  [{'PASS' if c['pass'] else 'FAIL'}] {c['check']}  —  {c['detail']}")
    print(f"\n总计 {report['passed']}  verdict={report['verdict']}  区块 {blk['block_id']}")


if __name__ == "__main__":
    main()
