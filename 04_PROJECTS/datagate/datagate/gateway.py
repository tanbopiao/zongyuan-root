"""DataGate 编排器 —— 唯一边界控制点(方案 §一: 禁止 Agent 直连业务库)

处理流水线(Step3 + Step4, 顺序不可颠倒):
  ingest:  主键非法阻断 → EID绑定 → Schema值域校验 → 快照提交(TruthRootHash+StateVersion+TTL)
  query:   EID存在性(Ω-Refer账本) → data_stale熔断 → 行级/字段权限裁剪(不下游传播)
           → 组装 Ω-Refer 信封(RefSet+ProductionPayload+DID签名)
  write:   一律拒绝 → WriteApprovalRequired(写回生产系统走独立审批工单流, 公理)
"""
from __future__ import annotations

import json
from pathlib import Path

from .eid import EidRegistry
from .schema import EntitySchema
from .permission import PermissionPolicy
from .snapshot import SnapshotStore, Snapshot
from .fuse import FuseCheck, FuseViolation
from .envelope import build_envelope, envelope_digest


class WriteApprovalRequired(PermissionError):
    """公理熔断: Agent 链路只读, 写回生产系统必须独立审批工单流(方案 §五.1)。"""

    def __init__(self, eid: str, payload: dict):
        super().__init__(
            f"写回被拒: eid={eid} —— 请生成变更申请单推送人工审批节点, "
            f"审批通过后单独调用业务写接口(Step5.4)")
        self.eid = eid
        self.payload = payload


class DataGate:
    def __init__(self, policy: PermissionPolicy | None = None,
                 default_ttl: float = 300.0,
                 audit_path: str | None = None):
        self.eids = EidRegistry()
        self.snapshots = SnapshotStore()
        self.policy = policy or PermissionPolicy()
        self.fuse = FuseCheck()
        self.schemas: dict[str, EntitySchema] = {}
        self.default_ttl = default_ttl            # 工单快照 TTL=300s(方案 §三)
        self.audit_path = Path(audit_path) if audit_path else None
        self._audit: list[dict] = []

    # ---------- Step3.3: Schema 载入 ----------
    def register_schema(self, schema: EntitySchema) -> None:
        self.schemas[schema.entity_type] = schema

    # ---------- ingest: 适配器数据入库(只读采集侧) ----------
    def ingest(self, record: dict, *, is_real_time: bool = True,
               ttl: float | None = None) -> Snapshot:
        """业务记录 → EID绑定 → 值域校验 → 快照提交。命中熔断抛 FuseViolation。"""
        entity_type = record.get("entity_type", "generic")
        business_key = record.get("business_key", "")
        site_code = record.get("site_code", "")
        self.fuse.check_primary_key(business_key)            # 主键非法阻断
        schema = self.schemas.get(entity_type)
        if schema is None:
            raise FuseViolation("param_invalid", f"未注册实体类型: {entity_type}")
        fields = self.fuse.check_schema(record.get("fields", {}), schema)  # 值域越界
        eid = self.eids.bind(entity_type, business_key, site_code)
        snap = self.snapshots.commit(
            eid, fields,
            source_system=record.get("source_system", "UNKNOWN"),
            source_primary_key=business_key,
            is_real_time=is_real_time and record.get("is_real_time", True),
            ttl_seconds=ttl if ttl is not None else self.default_ttl,
        )
        self._log("ingest", {"eid": eid, "sv": snap.state_version,
                             "root": snap.truth_root_hash[:16]})
        return snap

    def ingest_adapter(self, adapter, ttl: float | None = None) -> list[Snapshot]:
        """批量消费适配器(API/CDC/文件), 文件适配器自动短TTL+离线标签。"""
        out = []
        for rec in adapter.fetch():
            rec.setdefault("source_system", adapter.source_system)
            rec.setdefault("entity_type", adapter.entity_type)
            out.append(self.ingest(rec, is_real_time=adapter.is_real_time, ttl=ttl))
        return out

    # ---------- query: 出口唯一 —— 只回 Ω-Refer 信封 ----------
    def query(self, eid: str, did: str) -> dict:
        """按 EID 查询实体 → 熔断校验 → 权限裁剪 → 信封封装(Step4)。"""
        if not self.eids.resolve(eid):
            raise FuseViolation("param_invalid", f"EID 不在真值账本: {eid}")
        snap = self.snapshots.latest(eid)
        if snap is None:
            raise FuseViolation("param_invalid", f"EID 无快照: {eid}")
        self.fuse.check_stale(snap)                           # data_stale 熔断
        entity_type = self._entity_type_of(eid)
        site_code = self._site_of(eid) or ""
        masked = self.fuse.check_permission(did, site_code, snap.data, self.policy)
        fuse_mask = self.fuse.stale_label(snap)               # 离线→软stale标签(不阻断)
        env = build_envelope(
            did=did, eid=eid, entity_type=entity_type,
            label=f"{snap.source_primary_key}",
            masked_record=masked,
            truth_root_hash=snap.truth_root_hash,
            state_version=snap.state_version,
            source_system=snap.source_system,
            source_primary_key=snap.source_primary_key,
            is_real_time=snap.is_real_time,
            field_mask=list(masked.keys()),
            fuse_mask=fuse_mask,
        )
        self._log("query", {"eid": eid, "did": did, "digest": envelope_digest(env)[:16]})
        return env

    # ---------- write: 公理护栏 ----------
    def write(self, eid: str, payload: dict) -> None:
        """写回生产业务库 —— 一律拒绝, 走审批工单流(方案 §五.1 / Step5.4)。"""
        self._log("write_rejected", {"eid": eid, "payload": payload})
        raise WriteApprovalRequired(eid, payload)

    # ---------- 快照回退(Ω-Refer 协议 §2.3 第6步) ----------
    def rollback(self, eid: str, state_version: int) -> Snapshot | None:
        return self.snapshots.rollback(eid, state_version)

    # ---------- Step7 审计闭环: Merkle-DAG 审计日志 ----------
    def _log(self, action: str, fields: dict) -> None:
        entry = {"action": action, **fields}
        self._audit.append(entry)
        if self.audit_path:
            with open(self.audit_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # 内部索引辅助(EID→类型/厂区; 骨架用注册表反查, 生产可建倒排索引)
    def _entity_type_of(self, eid: str) -> str:
        for ck, e in self.eids.export().items():
            if e == eid:
                return ck.split("|", 1)[0]
        return "generic"

    def _site_of(self, eid: str) -> str | None:
        for ck, e in self.eids.export().items():
            if e == eid:
                parts = ck.split("|")
                return parts[1] if len(parts) == 3 else ""
        return None
