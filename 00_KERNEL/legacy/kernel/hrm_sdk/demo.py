"""
HRM-SDK 使用示例
展示业务侧标准调用流程
"""
import hashlib
import json
from hrm_sdk import (
    submit_asset, steady_judge, report_evolution_event,
    query_asset, KernelUnreachableError, ReceiptVerifyError, SteadyRejectError,
)
from hrm_sdk.asset_submit import sha256_of


def demo_resume_confirm():
    """示例：简历确权 + 稳态校验 + 授权分发"""
    # 1. 计算简历内容哈希（原文不入库，只存哈希）
    resume_struct = {"name": "***", "education": "硕士", "skills": ["Python", "AI"]}
    content_sha256 = sha256_of(resume_struct)
    print(f"[1] 简历内容哈希: {content_sha256[:20]}...")

    # 2. 提交简历确权资产
    try:
        receipt = submit_asset(
            meta_class_id="hrm-person-resume",
            content_sha256=content_sha256,
            asset_payload={"struct_version": "1.0", "field_count": len(resume_struct)},
            operate_type="CREATE",
        )
        print(f"[2] 简历确权成功: snap_hash={receipt['snap_hash'][:20]}... eFuse={receipt.get('eFuse_id')}")
    except KernelUnreachableError as e:
        print(f"[2] 内核不可达（已入本地队列）: {e}")
        return
    except ReceiptVerifyError as e:
        print(f"[2] 回执校验失败: {e}")
        return

    # 3. 简历授权分发前做稳态判定
    try:
        judge = steady_judge(
            biz_scene="hrm_resume_authorize",
            factor_interest=65,  # 利益
            factor_risk=80,      # 风险
            factor_cost=20,      # 成本
        )
        print(f"[3] 稳态判定通过: score={judge.get('score')}")
    except SteadyRejectError as e:
        print(f"[3] 稳态判定拒绝: {e}")
        return

    # 4. 授权分发（模拟业务动作）
    print("[4] 授权分发执行成功（单次有效，阅后即焚）")


def demo_fault_report():
    """示例：业务故障上报进化队列"""
    try:
        # 模拟匹配引擎异常
        result = report_evolution_event(
            event_source="hrm-suite",
            event_level="P1",
            event_type="MATCH_ERROR",
            event_desc="双塔匹配引擎超时：job_id=MT-20260907-001",
        )
        print(f"[上报] 故障事件已上报: {result}")
    except KernelUnreachableError as e:
        print(f"[上报] 内核不可达，事件已缓存: {e}")


if __name__ == "__main__":
    print("=" * 50)
    print("HRM-SDK V1.0 演示")
    print("确权: DID-BR-000002 | Ω₀⊂⊙∞⊂Ω")
    print("=" * 50)
    demo_resume_confirm()
    demo_fault_report()
    print("=" * 50)
