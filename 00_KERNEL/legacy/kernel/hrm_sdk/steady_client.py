"""
HRM-SDK 稳态决策算子客户端
UNI-STEADY-CORE-V1.0 三维稳态决策
利益 40% / 风险 35% / 成本 25%
"""
import json

import requests

from .config import KERNEL_BASE_ENDPOINT, REQUEST_TIMEOUT, DID_SUBJECT
from .signer import sign_request
from .exceptions import KernelUnreachableError, SteadyRejectError


def steady_judge(
    biz_scene: str,
    factor_interest: int,
    factor_risk: int,
    factor_cost: int,
    auto_reject: bool = True,
) -> dict:
    """调用全局稳态决策算子

    Args:
        biz_scene: 业务场景标识（hrm_resume_authorize / hrm_cert_confirm 等）
        factor_interest: 利益因子 0-100（权重40%）
        factor_risk: 风险因子 0-100（权重35%）
        factor_cost: 成本因子 0-100（权重25%）
        auto_reject: True 时稳态不通过直接抛 SteadyRejectError

    Returns:
        {"steady_pass": bool, "score": float, "judge_reason": str}

    Raises:
        SteadyRejectError: auto_reject=True 且稳态不通过
    """
    body = {
        "biz_scene": biz_scene,
        "factor_interest": int(factor_interest),
        "factor_risk": int(factor_risk),
        "factor_cost": int(factor_cost),
        "did": DID_SUBJECT,
    }
    headers = sign_request(body)
    try:
        resp = requests.post(
            f"{KERNEL_BASE_ENDPOINT}/steady/judge",
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(data.get("message", "稳态算子错误"))
        result = data.get("data", {})
        if auto_reject and not result.get("steady_pass", False):
            raise SteadyRejectError(result.get("judge_reason", "稳态判定未通过"))
        return result
    except (requests.ConnectionError, requests.Timeout) as e:
        raise KernelUnreachableError(f"内核不可达，稳态判定失败: {e}")
