"""
HRM-SDK 签名模块
HMAC-SHA256 签名 + 回执校验
"""
import hashlib
import hmac
import json
import time

from .config import SCHEDULER_SECRET, SDK_VERSION, DID_SUBJECT, TRACE_SYMBOL
from .exceptions import ReceiptVerifyError


def _secret() -> str:
    if not SCHEDULER_SECRET:
        raise RuntimeError(
            "ZONGYUAN_ROOT_SCHEDULER_SECRET 未配置，禁止以无签名方式调用内核 API"
        )
    return SCHEDULER_SECRET


def sign_request(payload: dict) -> dict:
    """生成请求头：签名 + 时间戳 + 确权标识

    签名格式: HMAC-SHA256(secret, timestamp:body)
    """
    body = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    ts = str(int(time.time()))
    sig = hmac.new(
        _secret().encode("utf-8"),
        f"{ts}:{body}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return {
        "X-Request-Sign": sig,
        "X-Timestamp": ts,
        "X-DID-Subject": DID_SUBJECT,
        "X-Trace-Symbol": TRACE_SYMBOL,
        "X-SDK-Version": SDK_VERSION,
        "Content-Type": "application/json; charset=utf-8",
    }


def verify_receipt(receipt: dict, expected_snap_hash: str = "") -> bool:
    """校验内核返回锁档回执

    回执必须包含 snap_hash / parent_hash / status=BLOWN_PERMANENT
    若指定 expected_snap_hash，则回执哈希必须匹配
    """
    if not receipt:
        raise ReceiptVerifyError("回执为空")
    snap_hash = receipt.get("snap_hash") or receipt.get("new_root_hash") or ""
    if not snap_hash:
        raise ReceiptVerifyError("回执缺少快照哈希")
    if receipt.get("status") not in ("BLOWN_PERMANENT", "LOCKED", "SUCCESS"):
        raise ReceiptVerifyError(f"回执状态异常: {receipt.get('status')}")
    if expected_snap_hash and snap_hash != expected_snap_hash:
        raise ReceiptVerifyError(
            f"回执哈希不匹配: 期望 {expected_snap_hash[:16]}... 实际 {snap_hash[:16]}..."
        )
    return True
