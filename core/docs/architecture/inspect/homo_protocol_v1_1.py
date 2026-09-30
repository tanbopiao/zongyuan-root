"""
同源协议 v1.1 实现
DID-BR-000002 ｜ ZONGYUAN-ROOT ｜ Ω₀⊂⊙∞⊂Ω

v1.1 新增特性：
- 握手重试机制
- 心跳保活
- 报文签名校验
- 异常报文熔断
- 版本字段兼容
- 完善错误码体系
"""
import json
import time
import hmac
import hashlib
import uuid
from typing import Dict, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum


class MessageType(Enum):
    """报文类型"""
    HANDSHAKE = "HANDSHAKE"
    REQUEST = "REQUEST"
    RESPONSE = "RESPONSE"
    HEARTBEAT = "HEARTBEAT"
    ACK = "ACK"
    LOCK = "LOCK"


class Priority(Enum):
    """优先级"""
    P0 = "P0"  # 紧急
    P1 = "P1"  # 高
    P2 = "P2"  # 中
    P3 = "P3"  # 低


class ErrorCode(Enum):
    """错误码体系"""
    E_AUTH_401 = "E_AUTH_401"          # 鉴权失败
    E_AUTH_403 = "E_AUTH_403"          # 无权限
    E_TIMEOUT_408 = "E_TIMEOUT_408"    # 请求超时
    E_RATE_429 = "E_RATE_429"          # 限流
    E_TASK_NOTFOUND = "E_TASK_NOTFOUND"  # 任务不存在
    E_TASK_FAILED = "E_TASK_FAILED"    # 任务执行失败
    E_SERVER_500 = "E_SERVER_500"      # 服务器错误
    E_BAD_MSG_400 = "E_BAD_MSG_400"    # 报文格式错误
    E_SIGNATURE_INVALID = "E_SIGNATURE_INVALID"  # 签名错误
    E_PROTOCOL_VERSION = "E_PROTOCOL_VERSION"    # 版本不兼容


@dataclass
class Message:
    """同源协议报文"""
    msg_type: str
    request_id: str
    timestamp: int
    from_did: str
    to_did: str
    protocol_version: str = "1.1"
    action: str = ""
    priority: str = "P2"
    params: dict = field(default_factory=dict)
    signature: str = ""
    status: str = ""
    data: dict = field(default_factory=dict)
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "msg_type": self.msg_type,
            "request_id": self.request_id,
            "timestamp": self.timestamp,
            "from_did": self.from_did,
            "to_did": self.to_did,
            "protocol_version": self.protocol_version,
            "action": self.action,
            "priority": self.priority,
            "params": self.params,
            "signature": self.signature,
            "status": self.status,
            "data": self.data,
            "error": self.error
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Message":
        return cls(
            msg_type=data.get("msg_type", ""),
            request_id=data.get("request_id", ""),
            timestamp=data.get("timestamp", 0),
            from_did=data.get("from_did", ""),
            to_did=data.get("to_did", ""),
            protocol_version=data.get("protocol_version", "1.0"),
            action=data.get("action", ""),
            priority=data.get("priority", "P2"),
            params=data.get("params", {}),
            signature=data.get("signature", ""),
            status=data.get("status", ""),
            data=data.get("data", {}),
            error=data.get("error", "")
        )


class HomoProtocolV11:
    """
    同源协议 v1.1

    特性：
    - HMAC-SHA256签名验证
    - 握手重试机制
    - 心跳保活
    - 异常报文熔断
    - 版本兼容
    """

    PROTOCOL_VERSION = "1.1"
    MAX_RETRY = 3
    RETRY_INTERVAL = 2
    HEARTBEAT_INTERVAL = 30
    CIRCUIT_BREAKER_THRESHOLD = 5  # 熔断阈值

    def __init__(self, node_did: str, shared_key: str):
        self.node_did = node_did
        self.shared_key = shared_key.encode("utf-8")
        self.peer_did = ""
        self.connected = False
        self.last_heartbeat = 0
        self.error_count = 0
        self.circuit_open = False
        self.circuit_reset_time = 0
        self.retry_count = 0

    def _sign(self, payload: str) -> str:
        """计算HMAC-SHA256签名"""
        return hmac.new(
            self.shared_key,
            payload.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

    def _verify_signature(self, msg: Message) -> bool:
        """验证报文签名"""
        payload_dict = msg.to_dict().copy()
        payload_dict.pop("signature", None)
        payload = json.dumps(payload_dict, sort_keys=True)
        expected = self._sign(payload)
        return hmac.compare_digest(expected, msg.signature)

    def _create_message(self, msg_type: MessageType, to_did: str,
                       action: str = "", params: dict = None,
                       priority: Priority = Priority.P2) -> Message:
        """创建报文"""
        msg = Message(
            msg_type=msg_type.value,
            request_id=f"req-{int(time.time())}-{uuid.uuid4().hex[:8]}",
            timestamp=int(time.time()),
            from_did=self.node_did,
            to_did=to_did,
            protocol_version=self.PROTOCOL_VERSION,
            action=action,
            priority=priority.value,
            params=params or {}
        )
        payload_dict = msg.to_dict().copy()
        payload_dict.pop("signature", None)
        payload = json.dumps(payload_dict, sort_keys=True)
        msg.signature = self._sign(payload)
        return msg

    def handshake(self, peer_did: str) -> dict:
        """握手（带重试）"""
        self.peer_did = peer_did
        self.retry_count = 0

        while self.retry_count < self.MAX_RETRY:
            try:
                if self.circuit_open:
                    if time.time() < self.circuit_reset_time:
                        return {
                            "success": False,
                            "error": "熔断器开启，请稍后重试",
                            "error_code": ErrorCode.E_SERVER_500.value
                        }
                    else:
                        self.circuit_open = False
                        self.error_count = 0

                msg = self._create_message(
                    MessageType.HANDSHAKE,
                    peer_did,
                    action="HANDSHAKE"
                )

                # 模拟发送（实际由传输层实现）
                result = self._send(msg)

                if result.get("success"):
                    self.connected = True
                    self.last_heartbeat = time.time()
                    self.error_count = 0
                    return {
                        "success": True,
                        "peer_id": peer_did,
                        "protocol_version": self.PROTOCOL_VERSION,
                        "server_time": int(time.time())
                    }
                else:
                    self.error_count += 1
                    if self.error_count >= self.CIRCUIT_BREAKER_THRESHOLD:
                        self.circuit_open = True
                        self.circuit_reset_time = time.time() + 60  # 60秒后重试

                    self.retry_count += 1
                    if self.retry_count < self.MAX_RETRY:
                        time.sleep(self.RETRY_INTERVAL)

            except Exception as e:
                self.error_count += 1
                self.retry_count += 1
                if self.retry_count < self.MAX_RETRY:
                    time.sleep(self.RETRY_INTERVAL)

        return {
            "success": False,
            "error": f"握手失败，已重试{self.MAX_RETRY}次",
            "error_code": ErrorCode.E_TIMEOUT_408.value
        }

    def heartbeat(self) -> bool:
        """心跳保活"""
        if not self.connected:
            return False

        if time.time() - self.last_heartbeat < self.HEARTBEAT_INTERVAL:
            return True

        msg = self._create_message(
            MessageType.HEARTBEAT,
            self.peer_did,
            action="PING"
        )

        try:
            result = self._send(msg)
            if result.get("success"):
                self.last_heartbeat = time.time()
                return True
        except Exception:
            pass

        return False

    def send_request(self, action: str, params: dict = None,
                     priority: Priority = Priority.P2) -> dict:
        """发送请求"""
        if not self.connected:
            return {
                "success": False,
                "error": "未握手，请先调用handshake()",
                "error_code": ErrorCode.E_AUTH_401.value
            }

        # 检查熔断
        if self.circuit_open:
            return {
                "success": False,
                "error": "熔断器开启",
                "error_code": ErrorCode.E_SERVER_500.value
            }

        msg = self._create_message(
            MessageType.REQUEST,
            self.peer_did,
            action=action,
            params=params,
            priority=priority
        )

        try:
            result = self._send(msg)
            return result
        except Exception as e:
            self.error_count += 1
            return {
                "success": False,
                "error": str(e),
                "error_code": ErrorCode.E_SERVER_500.value
            }

    def _send(self, msg: Message) -> dict:
        """发送报文（占位，实际由传输层实现）"""
        # 实际实现中这里会调用HTTP请求
        return {"success": True, "request_id": msg.request_id, "status": "PENDING"}

    def handle_message(self, raw_data: dict) -> dict:
        """处理接收到的报文"""
        try:
            msg = Message.from_dict(raw_data)

            # 版本兼容
            if msg.protocol_version not in ["1.0", "1.1"]:
                return {
                    "success": False,
                    "error": f"不支持的协议版本: {msg.protocol_version}",
                    "error_code": ErrorCode.E_PROTOCOL_VERSION.value
                }

            # 签名验证
            if not self._verify_signature(msg):
                self.error_count += 1
                return {
                    "success": False,
                    "error": "签名验证失败",
                    "error_code": ErrorCode.E_SIGNATURE_INVALID.value
                }

            # 处理不同类型报文
            if msg.msg_type == MessageType.HANDSHAKE.value:
                return {
                    "success": True,
                    "action": "HANDSHAKE_ACK",
                    "protocol_version": self.PROTOCOL_VERSION
                }
            elif msg.msg_type == MessageType.HEARTBEAT.value:
                return {"success": True, "action": "PONG"}
            elif msg.msg_type == MessageType.REQUEST.value:
                return {
                    "success": True,
                    "action": "REQUEST_RECEIVED",
                    "request_id": msg.request_id
                }
            else:
                return {
                    "success": False,
                    "error": f"未知报文类型: {msg.msg_type}",
                    "error_code": ErrorCode.E_BAD_MSG_400.value
                }

        except Exception as e:
            return {
                "success": False,
                "error": f"报文解析失败: {str(e)}",
                "error_code": ErrorCode.E_BAD_MSG_400.value
            }


# 使用示例
if __name__ == "__main__":
    protocol = HomoProtocolV11(
        node_did="DID-BR-000002",
        shared_key="test-key"
    )

    # 握手
    result = protocol.handshake("DID-CLOUD-CENTER-001")
    print(f"握手结果: {result}")

    # 发送请求
    result = protocol.send_request("DEPLOY_WEB_PAGE", {"file": "index.html"})
    print(f"请求结果: {result}")

    # 心跳
    hb = protocol.heartbeat()
    print(f"心跳: {'成功' if hb else '失败'}")
