"""Ω-Refer 信封封装 —— 方案 §三 ProductionPayload 规范 + 协议 §2.2 报文头

输出即标准信封: Ω_PROTO_VER / DID / DID_Sig / TruthRootHash / StateVersion /
               RefSet / ProductionPayload / ConflictPolicy / FuseMask
铁律: 不含合法 EID 的实体不进 RefSet; 哈希校验失败/权限不过 → 拒绝下发。
"""
from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone, timedelta

CST = timezone(timedelta(hours=8))
Ω_PROTO_VER = "1.0"


def sign_did(did: str, truth_root: str, state_version: int) -> str:
    """DID 签名占位实现(SHA256 摘要); 生产替换为真实 DID 密钥签名。"""
    return hashlib.sha256(
        f"{did}|{truth_root}|{state_version}".encode()).hexdigest()[:32]


def build_envelope(
    *,
    did: str,
    eid: str,
    entity_type: str,
    label: str,
    masked_record: dict,
    truth_root_hash: str,
    state_version: int,
    source_system: str,
    source_primary_key: str,
    is_real_time: bool,
    field_mask: list[str],
    fuse_mask: list[str],
    conflict_policy: str = "reject",
    snapshot_time: str | None = None,
) -> dict:
    """组装单实体 Ω-Refer 信封(Step4.1-4.3)。"""
    if snapshot_time is None:
        snapshot_time = datetime.now(CST).isoformat(timespec="seconds")
    return {
        "Ω_PROTO_VER": Ω_PROTO_VER,
        "DID": did,
        "DID_Sig": sign_did(did, truth_root_hash, state_version),
        "TruthRootHash": truth_root_hash,
        "StateVersion": state_version,
        "RefSet": [
            {"eid": eid, "entity_type": entity_type, "label": label}
        ],
        "ProductionPayload": {
            "source_system": source_system,
            "source_primary_key": source_primary_key,
            "snapshot_time": snapshot_time,
            "is_real_time": is_real_time,
            "field_mask": field_mask,
            "data": masked_record,
        },
        "ConflictPolicy": conflict_policy,
        "FuseMask": fuse_mask,
    }


def envelope_digest(envelope: dict) -> str:
    """信封内容摘要(审计索引/对账用, 写入 Merkle-DAG 审计日志的叶子)。"""
    body = json.dumps(envelope, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(body.encode()).hexdigest()
