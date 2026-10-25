"""熔断规则 —— 方案 §三 / Step3.6: TTL过期熔断、空值阻断、值域越界阻断、主键非法阻断

FuseMask 项与全局元规则联动: loop(META-RULE-018) / param_invalid / permission_deny
                          / data_stale(本方案新增)
"""
from __future__ import annotations

from .schema import SchemaError
from .permission import PermissionDenied
from .snapshot import Snapshot

# 方案 §三 完整熔断掩码集合
FUSE_LOOP = "loop"
FUSE_PARAM_INVALID = "param_invalid"
FUSE_PERMISSION_DENY = "permission_deny"
FUSE_DATA_STALE = "data_stale"


class FuseViolation(Exception):
    """熔断异常: 携带命中的 FuseMask 项, 禁止继续流向 LLM/工具链。"""

    def __init__(self, mask_item: str, msg: str):
        super().__init__(msg)
        self.mask_item = mask_item


class FuseCheck:
    """四类静态熔断规则(方案 Step3.6)。"""

    @staticmethod
    def check_primary_key(business_key: str) -> None:
        """主键非法阻断: 空/非串/超长。"""
        if not isinstance(business_key, str) or not business_key.strip():
            raise FuseViolation(FUSE_PARAM_INVALID, f"主键非法: {business_key!r}")
        if len(business_key) > 128:
            raise FuseViolation(FUSE_PARAM_INVALID, f"主键超长: {len(business_key)}")

    @staticmethod
    def check_schema(record: dict, schema) -> dict:
        """值域越界/类型不匹配/空值阻断 → param_invalid。"""
        try:
            return schema.validate(record)
        except SchemaError as e:
            raise FuseViolation(FUSE_PARAM_INVALID, str(e)) from e

    @staticmethod
    def check_permission(did: str, site_code: str, record: dict, policy) -> dict:
        """权限越界(行级/字段级) → permission_deny, 网关层拦截不下游传播。"""
        try:
            return policy.mask_record(did, site_code, record)
        except PermissionDenied as e:
            raise FuseViolation(FUSE_PERMISSION_DENY, str(e)) from e

    @staticmethod
    def check_stale(snap: Snapshot) -> None:
        """快照 TTL 过期 → data_stale; 过期实体禁止用于工具决策(方案 §三)。"""
        if snap.is_stale():
            raise FuseViolation(
                FUSE_DATA_STALE,
                f"快照过期: eid={snap.eid} age={snap.age():.1f}s > ttl={snap.ttl_seconds}s "
                f"(StateVersion={snap.state_version})")

    @staticmethod
    def stale_label(snap: Snapshot) -> list[str]:
        """软标记(不阻断): 离线快照打 stale 标签, 高风险决策不允许仅依赖离线数据。"""
        return [FUSE_DATA_STALE] if not snap.is_real_time else []
