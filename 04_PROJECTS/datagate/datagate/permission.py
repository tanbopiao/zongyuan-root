"""行级/字段权限裁剪(联动 OBS 七域权责拓扑) —— 方案 §二.4 / Step3.4

基于调用方 DID 身份过滤厂区/产线/敏感成本字段;
权限越界在网关层拦截, 不向下游传播(→FuseMask=[permission_deny])。
示例: 车间操作员 DID 只能看本产线工单, 看不到成本/报价。
"""
from __future__ import annotations


class PermissionDenied(PermissionError):
    """权限越界 —— 网关层拦截, 由 gateway 转译为 FuseMask=[permission_deny]。"""

    def __init__(self, msg: str, did: str = ""):
        super().__init__(msg)
        self.did = did


class PermissionPolicy:
    """DID → 可见字段/可见厂区 映射(敏感字段独立权限域, 默认不纳入普通 Agent RefSet)。

    policy 示例(Step1 字段分级):
      {"did:zongyuan:cost_manager": {"sites": None, "fields": None},          # None=全可见
       "did:zongyuan:factory_op01": {"sites": ["SITE-A"], "fields": ["*"]},
       "did:zongyuan:agent_query":  {"sites": None,
                                     "fields": ["order_no","line_code","qty_plan",
                                                "qty_finish","status"]}}        # 成本默认屏蔽
    """

    def __init__(self, policy: dict[str, dict] | None = None) -> None:
        self.policy = policy or {}

    def mask_record(self, did: str, site_code: str, record: dict) -> dict:
        """按 DID 裁剪单条记录字段; 厂区越权直接抛 PermissionDenied。"""
        p = self.policy.get(did)
        if p is None:                       # 未登记 DID: 默认最小可见(无字段)
            raise PermissionDenied(f"DID 未授权: {did}", did)
        sites = p.get("sites")
        if sites is not None and site_code not in sites:
            raise PermissionDenied(
                f"厂区越权: DID={did} 不可访问 {site_code}", did)
        fields = p.get("fields")
        if fields is None:                  # None = 全字段可见(管理域)
            return dict(record)
        if "*" in fields:
            return dict(record)
        return {k: v for k, v in record.items() if k in fields}

    def is_sensitive_field(self, fname: str) -> bool:
        """敏感字段标记(成本/报价/核心工艺配方 → 独立EID分组, 方案 §五.2)。"""
        return fname in {"cost", "price", "quotation", "recipe"}
