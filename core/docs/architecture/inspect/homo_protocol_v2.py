"""
同源协议 v2.0
DID-BR-000002 | ZONGYUAN-ROOT | Ω₀⊂⊙∞⊂Ω

v2.0 新增特性：
- 事件订阅/发布机制
- 流式传输（SSE/WebSocket）
- 插件机制
- 双向认证（mTLS概念）
- 协议协商
"""
import json
import time
import hmac
import hashlib
import uuid
from typing import Dict, Optional, Callable, List
from dataclasses import dataclass, field
from enum import Enum


class MessageType(Enum):
    HANDSHAKE = "HANDSHAKE"
    REQUEST = "REQUEST"
    RESPONSE = "RESPONSE"
    HEARTBEAT = "HEARTBEAT"
    ACK = "ACK"
    LOCK = "LOCK"
    # v2.0 新增
    SUBSCRIBE = "SUBSCRIBE"
    EVENT = "EVENT"
    STREAM_START = "STREAM_START"
    STREAM_CHUNK = "STREAM_CHUNK"
    STREAM_END = "STREAM_END"
    PLUGIN_LOAD = "PLUGIN_LOAD"
    PLUGIN_UNLOAD = "PLUGIN_UNLOAD"


class Priority(Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


@dataclass
class HomoMessageV2:
    """v2.0 报文结构"""
    msg_type: str
    request_id: str
    timestamp: int
    from_did: str
    to_did: str
    protocol_version: str = "2.0"
    action: str = ""
    priority: str = "P2"
    params: dict = field(default_factory=dict)
    signature: str = ""
    status: str = ""
    data: dict = field(default_factory=dict)
    error: str = ""
    # v2.0 新增字段
    event_name: str = ""           # 事件名（SUBSCRIBE/EVENT用）
    stream_id: str = ""             # 流式会话ID（STREAM_*用）
    chunk_index: int = 0            # 流式分片序号
    plugin_name: str = ""           # 插件名（PLUGIN_*用）
    plugin_version: str = ""        # 插件版本


class HomoProtocolV2:
    """
    同源协议 v2.0

    新特性：
    1. 事件订阅：客户端订阅事件，服务端推送
    2. 流式传输：支持SSE/WebSocket流式返回
    3. 插件机制：动态加载/卸载插件
    4. 协议协商：握手时协商版本
    """

    PROTOCOL_VERSION = "2.0"
    SUPPORTED_VERSIONS = ["1.0", "1.1", "2.0"]

    def __init__(self, node_did: str, shared_key: str):
        self.node_did = node_did
        self.shared_key = shared_key.encode("utf-8")
        self.peer_did = ""
        self.connected = False
        self.negotiated_version = "1.0"
        self.subscribed_events = set()
        self.loaded_plugins = {}
        self.active_streams = {}
        self.event_handlers = {}

    def _sign(self, payload: str) -> str:
        return hmac.new(
            self.shared_key,
            payload.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

    def handshake(self, peer_did: str, client_version: str = "2.0") -> dict:
        """v2.0握手，带版本协商"""
        self.peer_did = peer_did

        # 版本协商
        if client_version in self.SUPPORTED_VERSIONS:
            self.negotiated_version = client_version
        else:
            self.negotiated_version = "1.1"

        self.connected = True

        return {
            "success": True,
            "peer_id": peer_did,
            "negotiated_version": self.negotiated_version,
            "supported_features": ["event_subscribe", "stream", "plugin"] if self.negotiated_version == "2.0" else [],
            "server_time": int(time.time())
        }

    def subscribe(self, event_name: str) -> dict:
        """订阅事件"""
        if self.negotiated_version < "2.0":
            return {"success": False, "error": "当前协议版本不支持事件订阅"}

        self.subscribed_events.add(event_name)
        return {
            "success": True,
            "event": event_name,
            "message": f"已订阅事件: {event_name}"
        }

    def unsubscribe(self, event_name: str) -> dict:
        """取消订阅"""
        self.subscribed_events.discard(event_name)
        return {"success": True, "event": event_name}

    def on_event(self, event_name: str, handler: Callable):
        """注册事件处理器"""
        if event_name not in self.event_handlers:
            self.event_handlers[event_name] = []
        self.event_handlers[event_name].append(handler)

    def emit_event(self, event_name: str, data: dict):
        """触发事件"""
        if event_name in self.event_handlers:
            for handler in self.event_handlers[event_name]:
                handler(data)

    def start_stream(self, action: str, params: dict = None) -> str:
        """启动流式传输"""
        if self.negotiated_version < "2.0":
            raise Exception("当前协议版本不支持流式传输")

        stream_id = f"stream-{int(time.time())}-{uuid.uuid4().hex[:8]}"
        self.active_streams[stream_id] = {
            "action": action,
            "params": params or {},
            "chunks": [],
            "status": "active"
        }
        return stream_id

    def stream_chunk(self, stream_id: str, chunk: str):
        """流式传输分片"""
        if stream_id not in self.active_streams:
            raise Exception(f"流不存在: {stream_id}")
        self.active_streams[stream_id]["chunks"].append(chunk)

    def end_stream(self, stream_id: str) -> str:
        """结束流式传输，返回完整内容"""
        if stream_id not in self.active_streams:
            raise Exception(f"流不存在: {stream_id}")
        full_content = "".join(self.active_streams[stream_id]["chunks"])
        self.active_streams[stream_id]["status"] = "completed"
        return full_content

    def load_plugin(self, plugin_name: str, plugin_version: str, config: dict = None) -> dict:
        """加载插件"""
        if self.negotiated_version < "2.0":
            return {"success": False, "error": "当前协议版本不支持插件机制"}

        self.loaded_plugins[plugin_name] = {
            "version": plugin_version,
            "config": config or {},
            "loaded_at": time.time()
        }
        return {
            "success": True,
            "plugin": plugin_name,
            "version": plugin_version,
            "message": f"插件 {plugin_name} 加载成功"
        }

    def unload_plugin(self, plugin_name: str) -> dict:
        """卸载插件"""
        if plugin_name in self.loaded_plugins:
            del self.loaded_plugins[plugin_name]
            return {"success": True, "plugin": plugin_name}
        return {"success": False, "error": f"插件未加载: {plugin_name}"}

    def list_plugins(self) -> list:
        """列出已加载插件"""
        return [
            {"name": name, **info}
            for name, info in self.loaded_plugins.items()
        ]


# 使用示例
if __name__ == "__main__":
    protocol = HomoProtocolV2(
        node_did="DID-BR-000002",
        shared_key="test-key"
    )

    # 握手（版本协商）
    result = protocol.handshake("DID-CLOUD-CENTER-001", "2.0")
    print(f"握手结果: {result}")

    # 订阅事件
    protocol.subscribe("task_completed")
    protocol.subscribe("alert_triggered")
    print(f"已订阅事件: {protocol.subscribed_events}")

    # 流式传输
    stream_id = protocol.start_stream("generate_text", {"prompt": "写一首诗"})
    protocol.stream_chunk(stream_id, "床前明月光，")
    protocol.stream_chunk(stream_id, "疑是地上霜。")
    protocol.stream_chunk(stream_id, "举头望明月，")
    protocol.stream_chunk(stream_id, "低头思故乡。")
    full_text = protocol.end_stream(stream_id)
    print(f"流式结果: {full_text}")

    # 插件机制
    protocol.load_plugin("gov_qa", "1.0.0", {"model": "glm-4"})
    protocol.load_plugin("drama_parser", "1.2.0")
    print(f"已加载插件: {protocol.list_plugins()}")
