"""EID 实体建模与自动分配 —— 方案 §二.1

铁律: 同一业务主键(业务键+厂区编码)全局映射固定 EID, 跨轮次/跨 Agent 引用稳定;
      同一主键固定 EID, 不随机生成 (Step3.2)。
"""
from __future__ import annotations

import hashlib

# 各业务域 EID 前缀(方案 §二.1 固定编码规则)
DOMAIN_PREFIX = {
    "work_order": "E-M",   # 工单  E-M00xxx
    "line":       "E-L",   # 产线  E-L00xxx
    "batch":      "E-B",   # 批次  E-B00xxx
    "equipment":  "E-D",   # 设备  E-D00xxx
    "qc_order":   "E-Q",   # 质检单 E-Q00xxx
    "generic":    "E-0",   # 其它实体(工具返回/子任务等, Ω-Refer §2.1)
}


class EidRegistry:
    """业务主键 ↔ 全局 EID 固定绑定表(持久化介质预留: 本地文件/Merkle叶子)。"""

    def __init__(self) -> None:
        # canonical_key -> eid  (确定性, 进程重启后重算结果一致)
        self._bind: dict[str, str] = {}

    @staticmethod
    def _canonical(entity_type: str, business_key: str, site_code: str = "") -> str:
        # 同一业务主键(业务键+厂区编码)全局唯一
        return f"{entity_type}|{site_code}|{business_key}"

    def bind(self, entity_type: str, business_key: str, site_code: str = "") -> str:
        """绑定/复用固定 EID: 已绑定返回原 EID, 否则确定性生成。"""
        if entity_type not in DOMAIN_PREFIX:
            entity_type = "generic"
        ck = self._canonical(entity_type, business_key, site_code)
        if ck in self._bind:
            return self._bind[ck]              # 命中绑定: 引用稳定, 不漂移
        # 确定性编号: 业务主键哈希后段 → 同一主键永远得到同一 EID
        seq = int(hashlib.sha256(ck.encode()).hexdigest()[-8:], 16) % 100000
        eid = f"{DOMAIN_PREFIX[entity_type]}{seq:05d}"
        self._bind[ck] = eid
        return eid

    def resolve(self, eid: str) -> bool:
        """Ω-Refer 仲裁前置器: 校验 EID 是否存在于当前真值账本。"""
        return eid in self._bind.values()

    def export(self) -> dict[str, str]:
        return dict(self._bind)
