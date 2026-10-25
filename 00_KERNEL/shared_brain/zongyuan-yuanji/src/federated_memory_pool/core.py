"""Federated Memory Pool L2 — 单文件实现

ZONGYUAN-ROOT 元极恒一自治体系 · 联邦记忆池 · L2 网关真值库 (append_only)
Ω₀⊂⊙∞⊂Ω | DID-BR-000002

核心能力（对应联邦记忆内核 v2.0 设计）：

  五阶段治理:  propose → validate → vote → archive → confirm
  生命周期:    proposed → validated → reinforced → decayed → soft_forgotten
                                                       │
                                                       ▼
                                                   confirmed (跨节点共识上链)
  三算子:      Retain / Recall / Reflect  (isomorphic to propose+archive / validate+confirm / vote+archive)
  双层隔离:    MemoryBank 隔离 (节点内) ∪ 节点边界 (跨节点)
  生命周期治理: 价值打分 / 时序衰减 / 软遗忘 (降为只读索引，非物理删除)
  冲突消解:    同键异值 → 高价值侧优先共识；均低价值 → 两侧共存 + conflict_flag
  数据边界:    原始数据本地留存 · 共识摘要跨域同步
  哈希账本:    所有资产 Merkle-DAG 哈希，可溯源审计
  L0 豁免:    world_fact 类 (L0元宪法/公理) 不受衰减与软遗忘约束

纯标准库零依赖。文件存储，节点间通过 JSON 快照文件同步。
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# =============================================================================
# 常量与状态
# =============================================================================

ANCHOR = "Ω₀⊂⊙∞⊂Ω"
DEFAULT_DID = "DID-BR-000002"
KERNEL_VERSION = "L2-IMPL-20261020"

# 生命周期状态
STATE_PROPOSED = "proposed"
STATE_VALIDATED = "validated"
STATE_REINFORCED = "reinforced"
STATE_DECAYED = "decayed"
STATE_SOFT_FORGOTTEN = "soft_forgotten"
STATE_CONFIRMED = "confirmed"

LIFECYCLE_STATES = [
    STATE_PROPOSED, STATE_VALIDATED, STATE_REINFORCED,
    STATE_DECAYED, STATE_SOFT_FORGOTTEN, STATE_CONFIRMED,
]

# 九类真值
TRUTH_TYPES = {
    "meta_law", "rule", "config", "decision", "data",
    "creative", "risk", "protocol", "unknown",
}

# L0 豁免类型：world_fact 类不受衰减与软遗忘
L0_IMMUTABLE_TYPES = {"meta_law", "rule"}  # meta_law/rule 视为 L0 元宪法/公理类


# =============================================================================
# 值打分策略
# =============================================================================

# truth_type → 基础价值分
TYPE_BASE_VALUE = {
    "meta_law":   10.0,   # L0 元宪法
    "rule":        9.0,   # L1 规则
    "protocol":    8.0,
    "decision":    7.0,
    "risk":        7.0,
    "config":      6.0,
    "data":        4.0,
    "creative":    4.0,
    "unknown":     2.0,
}

# 价值分阈值
HIGH_VALUE_THRESHOLD = 7.0      # ≥ 高价值 → 跨节点可信收敛
LOW_VALUE_THRESHOLD = 4.0       # < 低价值 → 本地轻量化
DECAY_START_AFTER = 24 * 3600   # 24h 未命中开始衰减
DECAY_INTERVAL = 6 * 3600       # 每 6h 一次衰减步进
DECAY_FACTOR = 0.90             # 单次衰减倍率
SOFT_FORGET_THRESHOLD = 2.0     # 价值分低于此值 → 软遗忘
CONFIRM_VOTE_QUORUM = 2         # 跨节点确认需 ≥ 2 票


# =============================================================================
# 数据模型
# =============================================================================

@dataclass
class MemoryRecord:
    """单条记忆记录（原子）"""
    key: str
    value: Any
    truth_type: str = "unknown"
    did: str = DEFAULT_DID
    node: str = "local"
    state: str = STATE_PROPOSED
    value_score: float = 2.0
    version: int = 1
    created_at: float = 0.0
    updated_at: float = 0.0
    last_hit_at: float = 0.0
    hits: int = 0
    sha256: str = ""
    source_node: str = ""
    votes: List[Dict[str, Any]] = field(default_factory=list)
    conflict_flag: bool = False
    frozen_reason: str = ""

    def __post_init__(self):
        now = time.time()
        if self.created_at == 0.0:
            self.created_at = now
        if self.updated_at == 0.0:
            self.updated_at = now
        if self.last_hit_at == 0.0:
            self.last_hit_at = now
        if self.source_node == "":
            self.source_node = self.node
        if self.truth_type not in TRUTH_TYPES:
            self.truth_type = "unknown"
        # 计算初始价值分（若无显式指定则用类型基础分）
        if self.value_score == 0.0:
            self.value_score = TYPE_BASE_VALUE.get(self.truth_type, 2.0)
        if not self.sha256:
            self.sha256 = self.compute_sha()

    def compute_sha(self) -> str:
        """计算记录的内容哈希（Merkle 单元）"""
        # 排除 sha256 字段本身，避免自引用
        d = {k: v for k, v in asdict(self).items() if k != "sha256"}
        blob = json.dumps(d, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(blob).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "MemoryRecord":
        # 只取已知字段，容忍额外字段
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        clean = {k: v for k, v in d.items() if k in valid_keys}
        return cls(**clean)


# =============================================================================
# MemoryBank：节点内隔离的存储单元
# =============================================================================

class MemoryBank:
    """按项目/Agent/用户隔离的记忆存储单元。

    双层隔离的第一层：Bank 之间严格隔离，禁止跨 Bank 记忆泄露。
    """

    def __init__(self, name: str, did: str = DEFAULT_DID):
        self.name = name
        self.did = did
        self.records: Dict[str, MemoryRecord] = {}
        self.ledger: List[Dict[str, Any]] = []  # append-only Merkle 账本
        self.tombstones: Dict[str, Dict[str, Any]] = {}  # 软遗忘索引

    def retain(self, key: str, value: Any, truth_type: str = "unknown",
               did: str = DEFAULT_DID) -> MemoryRecord:
        """Retain 算子：写入即提案；结构化归一并计算 SHA256 后入本节点账本（归档）"""
        if key in self.records:
            # 版本升级：覆盖并 version+1
            rec = self.records[key]
            old_state = rec.state
            rec.value = value
            rec.truth_type = truth_type
            rec.version += 1
            rec.updated_at = time.time()
            rec.sha256 = rec.compute_sha()
            # 若已确认，不重置状态（L0 铁律：confirmed 不可被本地覆盖）
            if old_state != STATE_CONFIRMED:
                rec.state = STATE_VALIDATED
                rec.value_score = max(rec.value_score, TYPE_BASE_VALUE.get(truth_type, 2.0))
        else:
            rec = MemoryRecord(
                key=key, value=value, truth_type=truth_type,
                did=did, node=self.name, state=STATE_PROPOSED,
            )
            self.records[key] = rec
        self._ledger_append(rec)
        return rec

    def recall(self, key: str, source_node: str = "") -> Optional[MemoryRecord]:
        """Recall 算子：召回即校验；命中高价值记忆触发跨节点确权"""
        rec = self.records.get(key)
        if rec is None:
            return None
        # 更新命中统计
        rec.last_hit_at = time.time()
        rec.hits += 1
        rec.sha256 = rec.compute_sha()
        self._ledger_append(rec, event="recall")
        return rec

    def reflect(self, key: str, delta_score: float = 0.5,
                note: str = "") -> Optional[MemoryRecord]:
        """Reflect 算子：反思归纳即共识投票产物；新观察回写账本并纳入联邦摘要"""
        rec = self.records.get(key)
        if rec is None:
            return None
        rec.value_score = max(0.0, min(10.0, rec.value_score + delta_score))
        if rec.state == STATE_VALIDATED and rec.value_score >= HIGH_VALUE_THRESHOLD:
            rec.state = STATE_REINFORCED
        rec.updated_at = time.time()
        rec.sha256 = rec.compute_sha()
        self._ledger_append(rec, event=f"reflect:{note or 'adjust'}")
        return rec

    def _ledger_append(self, rec: MemoryRecord, event: str = "retain") -> None:
        """Merkle-DAG 账本追加"""
        entry = {
            "ts": time.time(),
            "event": event,
            "key": rec.key,
            "version": rec.version,
            "state": rec.state,
            "sha256": rec.sha256,
            "did": rec.did,
            "node": self.name,
        }
        self.ledger.append(entry)

    def is_l0_immutable(self, key: str) -> bool:
        rec = self.records.get(key)
        return rec is not None and rec.truth_type in L0_IMMUTABLE_TYPES

    def soft_forget(self, key: str) -> bool:
        """软遗忘：降级为只读索引，保留可审计痕迹（非物理删除）"""
        rec = self.records.get(key)
        if rec is None or self.is_l0_immutable(key):
            return False
        rec.state = STATE_SOFT_FORGOTTEN
        rec.frozen_reason = "soft_forget:lifecycle"
        rec.updated_at = time.time()
        self.tombstones[key] = {
            "forgotten_at": time.time(),
            "final_sha": rec.sha256,
            "final_value_score": rec.value_score,
        }
        self._ledger_append(rec, event="soft_forget")
        return True


# =============================================================================
# MemoryNode：单个联邦节点
# =============================================================================

class MemoryNode:
    """联邦节点：持有一个或多个 MemoryBank，负责本地生命周期管理"""

    def __init__(self, name: str, did: str = DEFAULT_DID,
                 local_dir: Optional[Path] = None):
        self.name = name
        self.did = did
        self.banks: Dict[str, MemoryBank] = {}
        self.default_bank = MemoryBank(name="default", did=did)
        self.banks["default"] = self.default_bank
        self.local_dir = Path(local_dir) if local_dir else None
        self._ensure_dir()

    def _ensure_dir(self):
        if self.local_dir:
            self.local_dir.mkdir(parents=True, exist_ok=True)

    def get_bank(self, bank_name: str) -> MemoryBank:
        return self.banks.get(bank_name, self.default_bank)

    # -- Retain / Recall / Reflect 三算子（银行级）-------------------------------

    def retain(self, key: str, value: Any, truth_type: str = "unknown",
               bank: str = "default", did: str = "") -> MemoryRecord:
        bank_obj = self.get_bank(bank)
        return bank_obj.retain(key, value, truth_type, did or self.did)

    def recall(self, key: str, bank: str = "default") -> Optional[MemoryRecord]:
        return self.get_bank(bank).recall(key)

    def reflect(self, key: str, delta_score: float = 0.5,
                note: str = "", bank: str = "default") -> Optional[MemoryRecord]:
        return self.get_bank(bank).reflect(key, delta_score, note)

    # -- 生命周期治理 -----------------------------------------------------------

    def apply_lifecycle(self, now: float = 0.0,
                        force_decay: bool = False) -> Dict[str, int]:
        """应用生命周期状态机：衰减 + 软遗忘。

        仅作用于 state ∈ {validated, reinforced, decayed}；
        world_fact 类 (L0) 完全豁免。
        返回各动作计数。
        """
        now = now or time.time()
        counts = {"decayed": 0, "soft_forgotten": 0}
        for bank in self.banks.values():
            for key, rec in list(bank.records.items()):
                if rec.state in (STATE_CONFIRMED, STATE_SOFT_FORGOTTEN):
                    continue
                if bank.is_l0_immutable(key) and not force_decay:
                    continue
                idle = now - rec.last_hit_at
                if idle >= DECAY_START_AFTER or force_decay:
                    # 计算衰减步进数
                    steps = max(1, int((idle - DECAY_START_AFTER) / DECAY_INTERVAL) + 1) if idle >= DECAY_START_AFTER else 1
                    rec.value_score = rec.value_score * (DECAY_FACTOR ** steps)
                    rec.updated_at = now
                    rec.sha256 = rec.compute_sha()
                    old_state = rec.state
                    if rec.value_score < SOFT_FORGET_THRESHOLD:
                        if bank.soft_forget(key):
                            counts["soft_forgotten"] += 1
                    elif rec.state in (STATE_VALIDATED, STATE_REINFORCED):
                        rec.state = STATE_DECAYED
                        counts["decayed"] += 1
                        bank._ledger_append(rec, event="decay")
        return counts

    # -- 冲突消解 ---------------------------------------------------------------

    def resolve_conflict(self, key: str,
                         incoming: MemoryRecord,
                         bank: str = "default") -> Tuple[str, MemoryRecord]:
        """同键异值冲突消解：高价值侧优先共识；均低价值 → 两侧共存 + conflict_flag

        返回 (winner_side, resulting_record)。winner_side ∈ {local, incoming, merged}
        """
        bank_obj = self.get_bank(bank)
        local_rec = bank_obj.records.get(key)
        if local_rec is None:
            # 本地无，直接接管
            bank_obj.retain(incoming.key, incoming.value, incoming.truth_type)
            return "incoming", bank_obj.records[key]

        if local_rec.sha256 == incoming.sha256:
            return "merged", local_rec  # 内容一致

        local_v = local_rec.value_score
        incoming_v = incoming.value_score

        # 内容差异 → 冲突
        conflict_flag = True
        if abs(local_v - incoming_v) >= 2.0:
            # 高价值侧胜出
            if incoming_v > local_v:
                bank_obj.retain(incoming.key, incoming.value, incoming.truth_type)
                bank_obj.records[key].conflict_flag = conflict_flag
                return "incoming", bank_obj.records[key]
            else:
                local_rec.conflict_flag = conflict_flag
                bank_obj._ledger_append(local_rec, event="conflict:keep_local")
                return "local", local_rec

        # 均低价值：两侧共存，标记 conflict_flag 待 Reflect 仲裁
        local_rec.conflict_flag = conflict_flag
        local_rec.updated_at = time.time()
        local_rec.sha256 = local_rec.compute_sha()
        bank_obj._ledger_append(local_rec, event="conflict_flag")
        return "merged", local_rec

    # -- 序列化 -----------------------------------------------------------------

    def snapshot(self) -> Dict[str, Any]:
        """导出节点快照（JSON 可序列化）"""
        return {
            "node": self.name,
            "did": self.did,
            "generated_at": time.time(),
            "anchor": ANCHOR,
            "banks": {
                name: {
                    "records": {k: r.to_dict() for k, r in bank.records.items()},
                    "ledger_len": len(bank.ledger),
                    "tombstones": bank.tombstones,
                }
                for name, bank in self.banks.items()
            },
        }

    def save(self) -> str:
        """持久化到本地文件，返回路径"""
        if not self.local_dir:
            raise RuntimeError("MemoryNode.local_dir not set")
        path = self.local_dir / f"node-{self.name}.json"
        path.write_text(json.dumps(self.snapshot(), ensure_ascii=False, indent=2))
        return str(path)

    @classmethod
    def load(cls, path: Path) -> "MemoryNode":
        """从快照文件加载节点"""
        d = json.loads(Path(path).read_text())
        node = cls(name=d["node"], did=d.get("did", DEFAULT_DID), local_dir=Path(path).parent)
        for bank_name, bank_data in d.get("banks", {}).items():
            bank = MemoryBank(name=bank_name, did=node.did)
            for key, rec_dict in bank_data.get("records", {}).items():
                bank.records[key] = MemoryRecord.from_dict(rec_dict)
            bank.tombstones = bank_data.get("tombstones", {})
            node.banks[bank_name] = bank
        return node


# =============================================================================
# 共识引擎：五阶段治理
# =============================================================================

class ConsensusEngine:
    """联邦记忆池五阶段共识引擎

    propose → validate → vote → archive → confirm

    - propose: 任意节点写入即产生 proposal，附带 SHA256 与元宪法合规标记
    - validate: 哈希凭证 + 元宪法合规校验（L0 层校验）
    - vote: 多节点投票，quorum = CONFIRM_VOTE_QUORUM (≥2 票)
    - archive: 达成共识后写入 Merkle-DAG 账本
    - confirm: 跨节点确权，state → confirmed（不可被覆盖）
    """

    def __init__(self, did: str = DEFAULT_DID):
        self.did = did
        self.proposals: Dict[str, List[Dict[str, Any]]] = {}  # key → [proposal...]
        self.audit_log: List[Dict[str, Any]] = []

    def _log(self, event: str, key: str, **kw):
        entry = {"ts": time.time(), "event": event, "key": key, "did": self.did, **kw}
        self.audit_log.append(entry)
        return entry

    def propose(self, record: MemoryRecord) -> Dict[str, Any]:
        """Stage 1: 写入即提案"""
        sha = record.sha256 or record.compute_sha()
        proposal = {
            "ts": time.time(),
            "from": record.node,
            "did": record.did,
            "key": record.key,
            "value": record.value,
            "truth_type": record.truth_type,
            "sha256": sha,
            "version": record.version,
            "value_score": record.value_score,
            "status": "proposed",
        }
        self.proposals.setdefault(record.key, []).append(proposal)
        entry = self._log("propose", record.key, sha=sha, version=record.version)
        proposal["log_ts"] = entry["ts"]
        return proposal

    def validate(self, key: str) -> Dict[str, Any]:
        """Stage 2: 哈希校验 + 元宪法合规通过"""
        proposals = self.proposals.get(key, [])
        if not proposals:
            return {"key": key, "status": "rejected", "reason": "no_proposal"}

        # 选最新提案
        latest = max(proposals, key=lambda p: p["ts"])
        # 元宪法合规：L0 豁免类型不允许从 proposed 直接跳 confirmed
        if latest["truth_type"] in L0_IMMUTABLE_TYPES:
            # L0 类型必须 validate + 明确 vote
            reason = "L0_type_requires_explicit_vote"
        else:
            reason = ""

        result = {
            "key": key,
            "status": "validated",
            "sha256": latest["sha256"],
            "value_score": latest["value_score"],
            "high_value": latest["value_score"] >= HIGH_VALUE_THRESHOLD,
            "reason": reason,
        }
        self._log("validate", key, sha=latest["sha256"])
        return result

    def vote(self, key: str, voter_node: str, voter_did: str,
             sha_expected: str, agree: bool = True) -> Dict[str, Any]:
        """Stage 3: 跨节点投票"""
        proposals = self.proposals.get(key, [])
        if not proposals:
            return {"key": key, "status": "rejected", "reason": "no_proposal"}

        # 找到匹配 sha 的提案
        target = next((p for p in proposals if p["sha256"] == sha_expected), None)
        if target is None:
            return {"key": key, "status": "rejected", "reason": "sha_mismatch"}

        target.setdefault("votes", [])
        target["votes"].append({
            "ts": time.time(),
            "voter": voter_node,
            "did": voter_did,
            "agree": agree,
        })
        agree_votes = sum(1 for v in target["votes"] if v["agree"])
        reached_quorum = agree_votes >= CONFIRM_VOTE_QUORUM
        self._log("vote", key, voter=voter_node, agree=agree,
                  agree_votes=agree_votes, quorum=reached_quorum)
        return {
            "key": key,
            "status": "quorum_reached" if reached_quorum else "pending",
            "agree_votes": agree_votes,
            "required": CONFIRM_VOTE_QUORUM,
        }

    def archive(self, key: str, node: MemoryNode, bank: str = "default") -> Dict[str, Any]:
        """Stage 4: 达成共识后写入 Merkle-DAG 账本"""
        proposals = self.proposals.get(key, [])
        if not proposals:
            return {"key": key, "status": "rejected", "reason": "no_proposal"}

        latest = max(proposals, key=lambda p: p["ts"])
        agree_votes = sum(1 for v in latest.get("votes", []) if v["agree"])
        if agree_votes < CONFIRM_VOTE_QUORUM:
            return {
                "key": key, "status": "rejected",
                "reason": "quorum_not_reached",
                "agree_votes": agree_votes,
            }

        bank_obj = node.get_bank(bank)
        rec = bank_obj.retain(
            key=latest["key"], value=latest["value"],
            truth_type=latest["truth_type"], did=latest["did"],
        )
        rec.votes = list(latest["votes"])
        rec.state = STATE_VALIDATED
        rec.sha256 = rec.compute_sha()
        self._log("archive", key, sha=rec.sha256, votes=agree_votes)
        return {"key": key, "status": "archived", "sha256": rec.sha256}

    def confirm(self, key: str, node: MemoryNode, bank: str = "default") -> Dict[str, Any]:
        """Stage 5: 跨节点确权 → confirmed（不可被覆盖）"""
        bank_obj = node.get_bank(bank)
        rec = bank_obj.records.get(key)
        if rec is None:
            return {"key": key, "status": "rejected", "reason": "not_in_ledger"}

        proposals = self.proposals.get(key, [])
        latest = max(proposals, key=lambda p: p["ts"]) if proposals else None
        agree_votes = sum(1 for v in latest.get("votes", []) if v["agree"]) if latest else 0
        if agree_votes < CONFIRM_VOTE_QUORUM:
            return {
                "key": key, "status": "rejected",
                "reason": "quorum_not_reached",
                "agree_votes": agree_votes,
            }

        rec.state = STATE_CONFIRMED
        rec.updated_at = time.time()
        rec.sha256 = rec.compute_sha()
        # 记录 votes
        rec.votes = list(latest.get("votes", [])) if latest else rec.votes
        bank_obj._ledger_append(rec, event="confirm")
        self._log("confirm", key, sha=rec.sha256, votes=agree_votes)
        return {
            "key": key, "status": "confirmed",
            "sha256": rec.sha256, "votes": agree_votes,
        }


# =============================================================================
# FederatedMemoryPool：多节点联邦协调器
# =============================================================================

class FederatedMemoryPool:
    """联邦记忆池协调器

    双层隔离（Bank 边界 ∪ 节点边界）+ 五阶段共识 + 生命周期治理
    """

    def __init__(self, did: str = DEFAULT_DID):
        self.did = did
        self.nodes: Dict[str, MemoryNode] = {}
        self.consensus = ConsensusEngine(did=did)

    def register_node(self, name: str, local_dir: Optional[Path] = None) -> MemoryNode:
        node = MemoryNode(name=name, did=self.did, local_dir=local_dir)
        self.nodes[name] = node
        return node

    def load_node(self, path: Path) -> MemoryNode:
        node = MemoryNode.load(path)
        self.nodes[node.name] = node
        return node

    # -- 高层 API：propose→validate→vote→archive→confirm 一键链路 -------------

    def submit_high_value(self, key: str, value: Any, truth_type: str,
                          proposer: str, voter,
                          bank: str = "default") -> Dict[str, Any]:
        """高价值记忆一键跨节点确认（五阶段全跑）

        proposer 作为提案者自动投一票，然后追加 voter 的投票。
        voter 可以是单个节点名字符串，也可以是多投票人列表，
        凑够 CONFIRM_VOTE_QUORUM 后自动归档 + 确认。
        """
        node = self.nodes[proposer]
        rec = node.retain(key, value, truth_type, bank=bank)
        proposal = self.consensus.propose(rec)
        validation = self.consensus.validate(key)

        # 提案者自证一票 + 显式 voter 票
        voters = [voter] if isinstance(voter, str) else list(voter)
        self.consensus.vote(
            key, voter_node=proposer, voter_did=self.did,
            sha_expected=rec.sha256, agree=True,
        )
        last_vote = None
        for v in voters:
            if v not in self.nodes:
                raise KeyError(f"node {v!r} not registered")
            if v == proposer:
                continue  # 提案者已自动投票，跳过重复
            last_vote = self.consensus.vote(
                key, voter_node=v, voter_did=self.did,
                sha_expected=rec.sha256, agree=True,
            )
        if last_vote is None:
            # 只有 proposer 一票，重算状态
            proposals = self.consensus.proposals.get(key, [])
            latest = max(proposals, key=lambda p: p["ts"])
            agree = sum(1 for x in latest.get("votes", []) if x["agree"])
            last_vote = {
                "key": key,
                "status": "quorum_reached" if agree >= CONFIRM_VOTE_QUORUM else "pending",
                "agree_votes": agree,
                "required": CONFIRM_VOTE_QUORUM,
            }

        result = {"propose": proposal, "validate": validation, "vote": last_vote}
        if last_vote["status"] == "quorum_reached":
            result["archive"] = self.consensus.archive(key, node, bank=bank)
            result["confirm"] = self.consensus.confirm(key, node, bank=bank)
        return result

    # -- 增量同步（跨节点） -----------------------------------------------------

    def sync(self, source: str, target: str) -> Dict[str, int]:
        """从 source 节点向 target 节点增量同步

        仅推送 value_score ≥ HIGH_VALUE_THRESHOLD 的记录（分级联邦共识）。
        冲突消解按节点内 resolve_conflict。
        """
        src = self.nodes[source]
        dst = self.nodes[target]
        stats = {"pushed": 0, "skipped": 0, "conflict": 0, "rejected": 0}
        for bank_name, bank in src.banks.items():
            for key, rec in bank.records.items():
                if rec.state != STATE_CONFIRMED and rec.value_score < HIGH_VALUE_THRESHOLD:
                    stats["skipped"] += 1
                    continue
                incoming = MemoryRecord(
                    key=rec.key, value=rec.value, truth_type=rec.truth_type,
                    did=rec.did, node=dst.name, state=rec.state,
                    value_score=rec.value_score, version=rec.version,
                    sha256=rec.sha256, source_node=rec.node,
                    votes=list(rec.votes),
                )
                dst_rec = dst.get_bank(bank_name).records.get(key)
                if dst_rec is not None and dst_rec.sha256 == rec.sha256:
                    stats["skipped"] += 1
                    continue
                _, result_rec = dst.resolve_conflict(key, incoming, bank=bank_name)
                if result_rec.conflict_flag:
                    stats["conflict"] += 1
                else:
                    stats["pushed"] += 1
        return stats

    # -- 数据边界校验 -----------------------------------------------------------

    def enforce_boundary(self, bank_a: str, bank_b: str, node_name: str) -> bool:
        """节点内 Bank 隔离：禁止跨 Bank 记忆泄露"""
        node = self.nodes.get(node_name)
        if node is None:
            return False
        a = node.get_bank(bank_a)
        b = node.get_bank(bank_b)
        # 隔离规则：A 与 B 不共享 record 引用
        for k_a, r_a in a.records.items():
            for k_b, r_b in b.records.items():
                if r_a is r_b:  # 同一对象引用即违规
                    return False
        return True

    # -- 全局生命周期 -----------------------------------------------------------

    def apply_lifecycle_all(self, now: float = 0.0,
                            force_decay: bool = False) -> Dict[str, Dict[str, int]]:
        """对所有节点应用生命周期治理"""
        return {
            name: node.apply_lifecycle(now=now, force_decay=force_decay)
            for name, node in self.nodes.items()
        }

    # -- 统计 -------------------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        total_records = 0
        by_state: Dict[str, int] = {}
        by_type: Dict[str, int] = {}
        confirmed = 0
        high_value = 0
        conflicts = 0
        soft_forgotten = 0
        ledger_entries = 0
        for node in self.nodes.values():
            for bank in node.banks.values():
                ledger_entries += len(bank.ledger)
                total_records += len(bank.records)
                soft_forgotten += len(bank.tombstones)
                for rec in bank.records.values():
                    by_state[rec.state] = by_state.get(rec.state, 0) + 1
                    by_type[rec.truth_type] = by_type.get(rec.truth_type, 0) + 1
                    if rec.state == STATE_CONFIRMED:
                        confirmed += 1
                    if rec.value_score >= HIGH_VALUE_THRESHOLD:
                        high_value += 1
                    if rec.conflict_flag:
                        conflicts += 1
        return {
            "nodes": len(self.nodes),
            "records": total_records,
            "by_state": by_state,
            "by_truth_type": by_type,
            "confirmed": confirmed,
            "high_value": high_value,
            "conflicts": conflicts,
            "soft_forgotten": soft_forgotten,
            "ledger_entries": ledger_entries,
            "audit_log_len": len(self.consensus.audit_log),
        }


# =============================================================================
# Merkle 根校验
# =============================================================================

def merkle_root_from_ledger(entries: List[Dict[str, Any]]) -> str:
    """从账本条目列表计算 Merkle 根哈希"""
    if not entries:
        return hashlib.sha256(b"").hexdigest()
    leaves = [hashlib.sha256(json.dumps(e, sort_keys=True, default=str).encode()).hexdigest()
              for e in entries]
    while len(leaves) > 1:
        if len(leaves) % 2 == 1:
            leaves.append(leaves[-1])
        next_level = []
        for i in range(0, len(leaves), 2):
            next_level.append(
                hashlib.sha256((leaves[i] + leaves[i+1]).encode()).hexdigest()
            )
        leaves = next_level
    return leaves[0]


def verify_ledger_integrity(bank: MemoryBank) -> Dict[str, Any]:
    """校验账本完整性：重算每条记录的 SHA256 与账本记录对比"""
    tampered = []
    for key, rec in bank.records.items():
        recomputed = rec.compute_sha()
        # 账本最后一条该 key 的 sha
        last_ledger_sha = None
        for entry in reversed(bank.ledger):
            if entry["key"] == key:
                last_ledger_sha = entry["sha256"]
                break
        if last_ledger_sha and last_ledger_sha != recomputed:
            tampered.append(key)
    merkle = merkle_root_from_ledger(bank.ledger)
    return {
        "tampered": tampered,
        "merkle_root": merkle,
        "ledger_len": len(bank.ledger),
    }
