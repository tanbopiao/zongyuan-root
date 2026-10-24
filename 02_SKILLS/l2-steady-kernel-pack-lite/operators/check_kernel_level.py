#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""内核等级自检算子 check_kernel_level。

检测当前智能体运行环境，判定内核等级 L0 / L1 / L2。

入参: kernel_capability 对象，布尔字段清单
返回值: 字符串，L0 / L1 / L2

来源: L2_STEADY_KERNEL_PACK V1.0-LITE
"""

# L2 六项硬性指标（全部为 True 才判定 L2）
_L2_CRITERIA = (
    "独立算子校验层",
    "死循环熔断机制",
    "快照断点持久存储",
    "原子回滚",
    "全域资产哈希账本",
    "短时原子执行调度",
)

# L1 最低门槛（两项必须同时具备）
_L1_MINIMUM = ("独立算子校验层", "死循环熔断机制")


def check_kernel_level(kernel_capability: dict) -> str:
    """根据能力清单判定内核等级。

    Args:
        kernel_capability: 当前环境能力布尔字段清单，如
            {"独立算子校验层": True, "死循环熔断机制": True, ...}

    Returns:
        "L2" / "L1" / "L0" 之一。
    """
    # L2 六项硬性指标全部为 True，才判定 L2
    criteria = [
        kernel_capability.get(key, False) for key in _L2_CRITERIA
    ]
    true_count = sum(criteria)

    if true_count == 6:
        return "L2"

    # 仅具备算子校验层 + 死循环熔断，判定 L1
    if all(kernel_capability.get(key, False) for key in _L1_MINIMUM):
        return "L1"

    return "L0"


def selftest() -> int:
    """三档断言自检，返回失败数。"""
    full_l2 = {k: True for k in _L2_CRITERIA}
    cases = [
        ("空能力→L0", {}, "L0"),
        ("仅提示词约束→L0", {"元规则": True}, "L0"),
        ("只缺快照(5/6)但门槛齐→L1", {**full_l2, "快照断点持久存储": False}, "L1"),
        ("L1最小门槛两项→L1", {"独立算子校验层": True, "死循环熔断机制": True}, "L1"),
        ("有熔断无校验层→L0", {"死循环熔断机制": True}, "L0"),
        ("仅持久存储无门槛→L0", {"快照断点持久存储": True, "原子回滚": True}, "L0"),
        ("六项全齐→L2", full_l2, "L2"),
        ("六项全真但缺字段拼写(部分未命中)→L0", {"独立算子校验层": True}, "L0"),
    ]
    failed = 0
    for name, caps, expect in cases:
        got = check_kernel_level(caps)
        ok = got == expect
        if not ok:
            failed += 1
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: expect={expect} got={got}")
    print(f"selftest: {len(cases) - failed}/{len(cases)} PASS")
    return failed


if __name__ == "__main__":
    raise SystemExit(selftest())
