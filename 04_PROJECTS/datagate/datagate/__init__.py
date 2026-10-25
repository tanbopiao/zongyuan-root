"""
DataGate 生产数据网关 · 核心代码骨架
=====================================
锁定依据: PROD-DATA-GATEWAY-PLAN-20261023-LOCKED (SEED-Ω-REFER-DATA-GATE-001)
         PROD-DATA-GATEWAY-STEP8-20261023-LOCKED (Step3 适配器开发配置)

核心公理(骨架内强制):
  1. 原始生产库不暴露给 Agent —— 只有 DataGate 一个边界控制点, 禁止直连业务库
  2. Agent 链路只读 —— write() 一律拒绝, 写回业务系统走独立审批工单流
  3. 一切输出必须是带 EID + TruthRootHash + StateVersion 的 Ω-Refer 信封

模块分层(正交隔离):
  eid        实体建模与 EID 自动分配      (Step3.2 业务主键↔全局EID固定绑定)
  schema     Schema 强约束 + 值域校验     (Step3.3)
  permission 行级/字段掩码(联动OBS权责)   (Step3.4)
  snapshot   快照引擎 Merkle锚定+StateVersion+TTL (Step3.5)
  fuse       熔断规则(TTL过期/空值/值域/主键)      (Step3.6)
  envelope   Ω-Refer 信封封装(RefSet/ProductionPayload/FuseMask)
  adapters   三接入适配器: API / CDC / 文件       (方案 路径1-3)
  gateway    DataGate 编排器 —— 唯一边界控制点
"""

from .eid import EidRegistry
from .schema import EntitySchema, FieldDef, SchemaError
from .permission import PermissionPolicy, PermissionDenied
from .snapshot import SnapshotStore, Snapshot
from .fuse import FuseCheck, FuseViolation
from .envelope import build_envelope
from .adapters import BaseAdapter, ApiAdapter, CdcAdapter, FileAdapter
from .gateway import DataGate, WriteApprovalRequired

__version__ = "0.1.0-skeleton"
__all__ = [
    "EidRegistry", "EntitySchema", "FieldDef", "SchemaError",
    "PermissionPolicy", "PermissionDenied",
    "SnapshotStore", "Snapshot",
    "FuseCheck", "FuseViolation",
    "build_envelope",
    "BaseAdapter", "ApiAdapter", "CdcAdapter", "FileAdapter",
    "DataGate", "WriteApprovalRequired",
]
