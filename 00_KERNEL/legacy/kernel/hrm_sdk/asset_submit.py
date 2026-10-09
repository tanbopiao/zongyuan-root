"""
HRM-SDK 资产快照提交模块
业务资产 → 内核 Merkle-DAG 链式锁档
"""
import hashlib
import json
import time

import requests

from .config import (
    KERNEL_BASE_ENDPOINT,
    REQUEST_TIMEOUT,
    RETRY_MAX,
    DID_SUBJECT,
    TRACE_SYMBOL,
)
from .signer import sign_request, verify_receipt
from .local_queue import LocalQueue
from .exceptions import KernelUnreachableError, ReceiptVerifyError, LocalPendingError

# 全局离线队列（进程内单例）
_offline_queue = LocalQueue()


def sha256_of(payload) -> str:
    """计算内容 SHA256（业务资产内容哈希）"""
    if isinstance(payload, str):
        raw = payload.encode("utf-8")
    else:
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def submit_asset(
    meta_class_id: str,
    content_sha256: str,
    asset_payload: dict,
    operate_type: str = "CREATE",
    retry: int = RETRY_MAX,
) -> dict:
    """提交资产快照至内核锁档（HRM 业务唯一入口）

    Args:
        meta_class_id: 元类ID，如 hrm-person-resume / hrm-company-cert
        content_sha256: 资产内容 SHA256
        asset_payload: 业务资产内容（仅存证字段，敏感原文禁止入库）
        operate_type: CREATE / UPDATE / DELETE_FLAGGED
        retry: 重试次数

    Returns:
        完整锁档回执（snap_hash / parent_hash / eFuse_id / new_root_hash）

    Raises:
        KernelUnreachableError: 内核不可达（已入本地队列）
        ReceiptVerifyError: 回执校验失败
    """
    body = {
        "meta_class_id": meta_class_id,
        "content_sha256": content_sha256,
        "asset_payload": asset_payload,
        "operate_type": operate_type,
        "did": DID_SUBJECT,
        "trace_symbol": TRACE_SYMBOL,
    }
    headers = sign_request(body)

    last_err = None
    for attempt in range(retry + 1):
        try:
            resp = requests.post(
                f"{KERNEL_BASE_ENDPOINT}/asset/snapshot/submit",
                data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )
            data = resp.json()
            if data.get("code") != 0:
                raise RuntimeError(data.get("message", "内核返回错误"))
            receipt = data.get("data", {})
            # 回执合法性校验
            verify_receipt(receipt)
            return receipt
        except (requests.ConnectionError, requests.Timeout) as e:
            last_err = e
            time.sleep(1 * (attempt + 1))  # 指数退避
        except Exception as e:
            raise e

    # 全部重试失败 → 入本地离线队列
    queued = _offline_queue.push({"type": "asset_submit", "body": body})
    if not queued:
        raise LocalPendingError("本地离线队列已满，请求被丢弃")
    raise KernelUnreachableError(f"内核不可达，请求已入本地队列 (last_err={last_err})")


def query_asset(snap_hash: str) -> dict:
    """查询资产存证凭证"""
    try:
        resp = requests.get(
            f"{KERNEL_BASE_ENDPOINT}/asset/snapshot/query",
            params={"snap_hash": snap_hash},
            headers={"X-DID-Subject": DID_SUBJECT},
            timeout=REQUEST_TIMEOUT,
        )
        data = resp.json()
        return data.get("data", {})
    except requests.ConnectionError as e:
        raise KernelUnreachableError(f"内核不可达: {e}")


def consume_local_queue(handler=None):
    """消费离线队列：手动栈迭代，不使用递归

    handler: 自定义重提交回调（默认重新调用 submit_asset）
    """
    n = 0
    while True:
        item = _offline_queue.pop()
        if item is None:
            break
        try:
            if handler:
                handler(item)
            else:
                submit_asset(
                    meta_class_id=item["body"]["meta_class_id"],
                    content_sha256=item["body"]["content_sha256"],
                    asset_payload=item["body"]["asset_payload"],
                    operate_type=item["body"]["operate_type"],
                )
            n += 1
        except Exception:
            # 重提交失败重新入栈，下次再试
            _offline_queue.push(item)
            break
    return n
