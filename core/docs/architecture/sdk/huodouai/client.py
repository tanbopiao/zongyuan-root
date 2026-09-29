"""
同源协议客户端
"""
import hmac
import hashlib
import time
import json
import uuid
from typing import Dict, Optional
from urllib import request, error

from .exceptions import HomoError, AuthError, TimeoutError, TaskFailedError


class HandshakeResponse:
    """握手响应"""
    def __init__(self, data: dict):
        self.success = data.get("success", False)
        self.peer_id = data.get("peer_id", "")
        self.protocol_version = data.get("protocol_version", "1.0")
        self.server_time = data.get("server_time", 0)

    def __repr__(self):
        return f"<HandshakeResponse success={self.success} peer_id={self.peer_id}>"


class TaskResponse:
    """任务响应"""
    def __init__(self, data: dict):
        self.task_id = data.get("task_id", "")
        self.status = data.get("status", "PENDING")
        self.request_id = data.get("request_id", "")

    def __repr__(self):
        return f"<TaskResponse task_id={self.task_id} status={self.status}>"


class TaskStatus:
    """任务状态"""
    def __init__(self, data: dict):
        self.status = data.get("status", "PENDING")
        self.progress = data.get("progress", 0)
        self.result = data.get("result", {})
        self.error = data.get("error", "")

    def __repr__(self):
        return f"<TaskStatus status={self.status} progress={self.progress}%>"


class HomoClient:
    """
    同源协议客户端

    用法:
        client = HomoClient(
            node_did="DID-YOUR-NODE-001",
            shared_key="your-shared-key"
        )
        response = client.handshake()
    """

    def __init__(
        self,
        node_did: str,
        shared_key: str,
        base_url: str = "https://www.huodouai.com",
        timeout: int = 30,
        retry: int = 3
    ):
        self.node_did = node_did
        self.shared_key = shared_key.encode("utf-8")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.retry = retry

    def _sign(self, payload: str) -> str:
        """计算HMAC-SHA256签名"""
        return hmac.new(
            self.shared_key,
            payload.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

    def _post(self, path: str, data: dict) -> dict:
        """发送POST请求"""
        url = f"{self.base_url}{path}"
        payload = json.dumps(data, ensure_ascii=False)
        signature = self._sign(payload)

        headers = {
            "Content-Type": "application/json",
            "X-Node-DID": self.node_did,
            "X-Signature": signature,
            "X-Request-ID": str(uuid.uuid4())
        }

        req = request.Request(url, data=payload.encode("utf-8"), headers=headers, method="POST")

        last_error = None
        for attempt in range(self.retry):
            try:
                with request.urlopen(req, timeout=self.timeout) as resp:
                    body = resp.read().decode("utf-8")
                    return json.loads(body)
            except error.HTTPError as e:
                if e.code == 401:
                    raise AuthError("鉴权失败，请检查DID和密钥", code="E_AUTH_401")
                last_error = e
            except error.URLError as e:
                last_error = e
            time.sleep(1)

        raise TimeoutError(f"请求超时，已重试{self.retry}次: {last_error}")

    def handshake(self) -> HandshakeResponse:
        """发起握手"""
        data = {
            "msg_type": "HANDSHAKE",
            "timestamp": int(time.time()),
            "from_did": self.node_did,
            "to_did": "DID-CLOUD-CENTER-001",
            "protocol_version": "1.0"
        }
        result = self._post("/anchor/api/v1/handshake", data)
        return HandshakeResponse(result)

    def send_task(self, action: str, params: dict = None,
                  priority: str = "P2", timeout_sec: int = 300) -> TaskResponse:
        """下发任务"""
        data = {
            "msg_type": "REQUEST",
            "request_id": f"req-{int(time.time())}-{uuid.uuid4().hex[:8]}",
            "timestamp": int(time.time()),
            "from_did": self.node_did,
            "to_did": "DID-CLOUD-CENTER-001",
            "action": action,
            "priority": priority,
            "timeout_sec": timeout_sec,
            "params": params or {}
        }
        result = self._post("/anchor/api/v1/request", data)
        return TaskResponse(result)

    def get_task_status(self, task_id: str) -> TaskStatus:
        """查询任务状态"""
        url = f"{self.base_url}/anchor/api/v1/task/{task_id}"
        req = request.Request(url, headers={"X-Node-DID": self.node_did})
        with request.urlopen(req, timeout=self.timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return TaskStatus(data)
