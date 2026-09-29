"""
HRM-SDK 故障事件回流模块
业务异常 → evolution_task_queue.json 自治进化队列
"""
import json

import requests

from .config import KERNEL_BASE_ENDPOINT, REQUEST_TIMEOUT, DID_SUBJECT, TRACE_SYMBOL
from .signer import sign_request
from .local_queue import LocalQueue
from .exceptions import KernelUnreachableError

# 复用离线队列（与资产提交同队列，保证事件不丢）
_offline_queue = LocalQueue()


def report_evolution_event(
    event_source: str,
    event_level: str,
    event_type: str,
    event_desc: str,
    attach_snap_hash: str = "",
) -> dict:
    """上报业务故障事件至自治进化队列

    Args:
        event_source: 事件来源（hrm-suite）
        event_level: P0 / P1 / P2 / P3
        event_type: MATCH_ERROR / STORE_SUBMIT_FAIL / AGENT_EXCEPTION ...
        event_desc: 故障描述
        attach_snap_hash: 关联业务快照哈希（可选）
    """
    body = {
        "event_source": event_source,
        "event_level": event_level,
        "event_type": event_type,
        "event_desc": event_desc[:500],
        "attach_snap_hash": attach_snap_hash,
        "did": DID_SUBJECT,
        "trace_symbol": TRACE_SYMBOL,
    }
    headers = sign_request(body)
    try:
        resp = requests.post(
            f"{KERNEL_BASE_ENDPOINT}/evolution/event/report",
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )
        data = resp.json()
        return data.get("data", {"reported": True})
    except (requests.ConnectionError, requests.Timeout) as e:
        # 内核不可达 → 本地队列缓存，恢复后补报
        queued = _offline_queue.push({"type": "evolution_event", "body": body})
        if not queued:
            raise KernelUnreachableError(f"内核不可达且本地队列已满: {e}")
        return {"reported": False, "local_queued": True}
