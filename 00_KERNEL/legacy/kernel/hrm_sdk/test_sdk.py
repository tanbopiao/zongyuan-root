"""
HRM-SDK 单元测试（离线可跑，不依赖真实内核）
运行: python3 -m pytest hrm_sdk/test_sdk.py -v
"""
import os
import sys
import hashlib
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 测试用临时配置（不依赖真实环境变量）
os.environ["ZONGYUAN_ROOT_SCHEDULER_SECRET"] = "test-secret-for-unit"
os.environ["ZKROOT_API_ENDPOINT"] = "http://127.0.0.1:9"  # 不可达端口，测离线队列
os.environ["HRM_SDK_QUEUE_PATH"] = os.path.join(tempfile.mkdtemp(), "test_queue.dat")

from hrm_sdk.signer import sign_request, verify_receipt
from hrm_sdk.local_queue import LocalQueue
from hrm_sdk.asset_submit import sha256_of, submit_asset, consume_local_queue
from hrm_sdk.exceptions import (
    KernelUnreachableError, ReceiptVerifyError, LocalPendingError,
)
from hrm_sdk import steady_judge
from hrm_sdk.steady_client import SteadyRejectError
import requests


def test_sign_and_verify():
    """签名生成 + 回执校验"""
    payload = {"a": 1, "b": "中文"}
    headers = sign_request(payload)
    assert "X-Request-Sign" in headers
    assert len(headers["X-Request-Sign"]) == 64
    assert headers["X-DID-Subject"] == "DID-BR-000002"
    # 有效回执
    assert verify_receipt({"snap_hash": "ab" * 32, "status": "BLOWN_PERMANENT"})
    # 无效回执
    try:
        verify_receipt({"status": "FAIL"})
        assert False, "应当抛异常"
    except ReceiptVerifyError:
        pass


def test_sha256():
    """内容哈希计算"""
    h = sha256_of({"k": "v"})
    assert len(h) == 64
    assert sha256_of("str") == hashlib.sha256(b"str").hexdigest()


def test_local_queue_stack():
    """本地离线队列（手动栈迭代）"""
    q = LocalQueue(store_path=os.environ["HRM_SDK_QUEUE_PATH"], max_size=3)
    q.clear()
    assert q.push({"m": 1})
    assert q.push({"m": 2})
    assert q.push({"m": 3})
    assert not q.push({"m": 4})  # 超限
    assert q.size() == 3
    assert q.pop()["m"] == 3  # LIFO
    assert q.pop()["m"] == 2
    assert q.pop()["m"] == 1
    assert q.pop() is None
    q.clear()


def test_submit_offline_queue():
    """内核不可达 → 入本地离线队列"""
    q = LocalQueue(store_path=os.environ["HRM_SDK_QUEUE_PATH"], max_size=3)
    q.clear()
    try:
        submit_asset(
            meta_class_id="hrm-person-resume",
            content_sha256=sha256_of({"x": 1}),
            asset_payload={"v": "1"},
            retry=0,  # 不重试
        )
        assert False, "应当抛 KernelUnreachableError"
    except KernelUnreachableError:
        pass
    assert q.size() >= 1


def test_consume_queue():
    """离线队列消费（手动迭代）"""
    q = LocalQueue(store_path=os.environ["HRM_SDK_QUEUE_PATH"], max_size=3)
    q.clear()
    q.push({"type": "asset_submit", "body": {"n": 1}})
    q.push({"type": "asset_submit", "body": {"n": 2}})

    seen = []
    def handler(item):
        seen.append(item["body"]["n"])

    n = consume_local_queue(handler=handler)
    assert n == 2
    assert seen == [2, 1]  # LIFO
    assert q.size() == 0


if __name__ == "__main__":
    test_sign_and_verify()
    test_sha256()
    test_local_queue_stack()
    test_submit_offline_queue()
    test_consume_queue()
    print("ALL HRM-SDK UNIT TESTS PASSED ✅")
