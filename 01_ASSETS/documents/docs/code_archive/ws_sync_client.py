#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中枢智能WebSocket实时同步客户端
ZONGYUAN-ROOT Real-time Sync Client

功能：
- 自动连接WebSocket服务端
- 心跳保活
- 自动重连（指数退避）
- 状态同步（全量+增量）
- 真值上报
- 决策上报
- 操作请求
- 消息队列（断线缓存，重连补发）
- 事件回调机制

版本：V1.0
日期：2026-09-16
确权：DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
"""

import asyncio
import json
import time
import uuid
import hashlib
import logging
from typing import Dict, Optional, Any, Callable, Awaitable
from dataclasses import dataclass, field
from enum import Enum

try:
    import websockets
except ImportError:
    print("请安装websockets库: pip install websockets")
    raise

# ============================================================
# 配置
# ============================================================

@dataclass
class ClientConfig:
    """客户端配置"""
    server_url: str = "ws://127.0.0.1:9130"
    node_id: str = ""
    node_type: str = "dialog"  # dialog / dev / worker / admin
    permissions: list = field(default_factory=lambda: ["read", "write"])
    heartbeat_interval: int = 30  # 心跳间隔（秒）
    reconnect_base_delay: float = 1.0  # 重连基础延迟（秒）
    reconnect_max_delay: float = 60.0  # 重连最大延迟（秒）
    max_reconnect_attempts: int = 0  # 最大重连次数（0=无限）
    message_queue_max_size: int = 1000  # 消息队列最大大小
    enable_auto_sync: bool = True  # 启用自动状态同步
    sync_interval: int = 300  # 定期全量同步间隔（秒）
    log_level: str = "INFO"

# ============================================================
# 客户端状态
# ============================================================

class ClientState(Enum):
    """客户端状态"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATED = "authenticated"
    RECONNECTING = "reconnecting"
    ERROR = "error"

# ============================================================
# 消息模型
# ============================================================

@dataclass
class SyncMessage:
    """同步消息"""
    type: str
    id: str
    timestamp: float
    sender: str
    version: int
    payload: Dict[str, Any]
    signature: str = ""

    def to_json(self) -> str:
        return json.dumps({
            "type": self.type,
            "id": self.id,
            "timestamp": self.timestamp,
            "sender": self.sender,
            "version": self.version,
            "payload": self.payload,
            "signature": self.signature
        }, ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str: str) -> "SyncMessage":
        data = json.loads(json_str)
        return cls(
            type=data.get("type", "UNKNOWN"),
            id=data.get("id", str(uuid.uuid4())),
            timestamp=data.get("timestamp", time.time()),
            sender=data.get("sender", "unknown"),
            version=data.get("version", 0),
            payload=data.get("payload", {}),
            signature=data.get("signature", "")
        )

# ============================================================
# 事件回调类型
# ============================================================

EventHandler = Callable[[SyncMessage, "WSSyncClient"], Awaitable[None]]

# ============================================================
# 主客户端类
# ============================================================

class WSSyncClient:
    """WebSocket实时同步客户端"""

    def __init__(self, config: Optional[ClientConfig] = None):
        self.config = config or ClientConfig()
        if not self.config.node_id:
            self.config.node_id = f"node-{uuid.uuid4().hex[:8]}"

        self.state: ClientState = ClientState.DISCONNECTED
        self.websocket: Optional[Any] = None
        self.session_id: str = ""
        self.local_version: int = 0
        self.server_version: int = 0
        self.reconnect_attempts: int = 0
        self.last_heartbeat: float = 0
        self.last_sync: float = 0

        # 消息队列（断线时缓存，重连后补发）
        self.message_queue: asyncio.Queue = asyncio.Queue(maxsize=self.config.message_queue_max_size)

        # 事件处理器
        self.event_handlers: Dict[str, list] = {}

        # 内部任务
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._reconnect_task: Optional[asyncio.Task] = None
        self._sync_task: Optional[asyncio.Task] = None
        self._running: bool = False

        self.logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        """设置日志"""
        logger = logging.getLogger(f"ws_sync_client_{self.config.node_id}")
        logger.setLevel(getattr(logging, self.config.log_level, logging.INFO))
        if not logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter(
                '%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            ))
            logger.addHandler(handler)
        return logger

    # ============================================================
    # 事件注册
    # ============================================================

    def on(self, event_type: str, handler: EventHandler):
        """注册事件处理器"""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
        self.logger.debug(f"注册事件处理器: {event_type}")

    def off(self, event_type: str, handler: Optional[EventHandler] = None):
        """注销事件处理器"""
        if event_type in self.event_handlers:
            if handler:
                self.event_handlers[event_type].remove(handler)
            else:
                del self.event_handlers[event_type]

    async def _emit_event(self, event_type: str, message: SyncMessage):
        """触发事件"""
        if event_type in self.event_handlers:
            for handler in self.event_handlers[event_type]:
                try:
                    await handler(message, self)
                except Exception as e:
                    self.logger.error(f"事件处理器执行失败 ({event_type}): {e}")

        # 通用事件
        if "*" in self.event_handlers:
            for handler in self.event_handlers["*"]:
                try:
                    await handler(message, self)
                except Exception as e:
                    self.logger.error(f"通用事件处理器执行失败: {e}")

    # ============================================================
    # 连接管理
    # ============================================================

    async def connect(self) -> bool:
        """连接到服务端"""
        if self.state in (ClientState.CONNECTING, ClientState.CONNECTED, ClientState.AUTHENTICATED):
            self.logger.warning(f"已处于连接状态: {self.state.value}")
            return True

        self.state = ClientState.CONNECTING
        self.logger.info(f"正在连接到 {self.config.server_url} ...")

        try:
            self.websocket = await websockets.connect(
                self.config.server_url,
                max_size=1024 * 1024,
                ping_interval=None,
                ping_timeout=None
            )
            self.state = ClientState.CONNECTED
            self.reconnect_attempts = 0
            self.logger.info("连接成功，正在发送HELLO...")

            # 发送HELLO消息
            await self._send_hello()

            # 启动后台任务
            self._running = True
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            if self.config.enable_auto_sync:
                self._sync_task = asyncio.create_task(self._periodic_sync_loop())

            # 启动消息接收循环
            asyncio.create_task(self._receive_loop())

            return True
        except Exception as e:
            self.logger.error(f"连接失败: {e}")
            self.state = ClientState.ERROR
            await self._schedule_reconnect()
            return False

    async def disconnect(self):
        """断开连接"""
        self.logger.info("正在断开连接...")
        self._running = False

        # 发送DISCONNECT消息
        if self.websocket and self.state in (ClientState.CONNECTED, ClientState.AUTHENTICATED):
            try:
                msg = self._create_message("DISCONNECT", {"reason": "client_disconnect"})
                await self.websocket.send(msg.to_json())
            except:
                pass

        # 取消后台任务
        for task in [self._heartbeat_task, self._reconnect_task, self._sync_task]:
            if task and not task.done():
                task.cancel()

        # 关闭连接
        if self.websocket:
            try:
                await self.websocket.close()
            except:
                pass
            self.websocket = None

        self.state = ClientState.DISCONNECTED
        self.logger.info("已断开连接")

    async def _schedule_reconnect(self):
        """调度重连"""
        if self._reconnect_task and not self._reconnect_task.done():
            return

        if self.config.max_reconnect_attempts > 0 and self.reconnect_attempts >= self.config.max_reconnect_attempts:
            self.logger.error(f"已达到最大重连次数 ({self.config.max_reconnect_attempts})，停止重连")
            self.state = ClientState.ERROR
            return

        self.reconnect_attempts += 1
        delay = min(
            self.config.reconnect_base_delay * (2 ** (self.reconnect_attempts - 1)),
            self.config.reconnect_max_delay
        )
        self.logger.info(f"将在 {delay:.1f} 秒后进行第 {self.reconnect_attempts} 次重连...")

        self.state = ClientState.RECONNECTING
        await asyncio.sleep(delay)
        await self.connect()

    # ============================================================
    # 消息收发
    # ============================================================

    def _create_message(self, msg_type: str, payload: Dict[str, Any]) -> SyncMessage:
        """创建消息"""
        msg = SyncMessage(
            type=msg_type,
            id=str(uuid.uuid4()),
            timestamp=time.time(),
            sender=self.config.node_id,
            version=self.local_version,
            payload=payload
        )
        # 计算签名（简化版，后续可加强）
        msg.signature = hashlib.sha256(
            f"{msg.id}:{msg.type}:{msg.timestamp}:{msg.sender}".encode()
        ).hexdigest()
        return msg

    async def _send(self, message: SyncMessage) -> bool:
        """发送消息"""
        if not self.websocket or self.state not in (ClientState.CONNECTED, ClientState.AUTHENTICATED):
            # 断线时缓存到队列
            try:
                if not self.message_queue.full():
                    self.message_queue.put_nowait(message)
                    self.logger.debug(f"消息已缓存到队列（断线）: {message.type}")
                else:
                    self.logger.warning(f"消息队列已满，丢弃消息: {message.type}")
            except Exception as e:
                self.logger.error(f"消息缓存失败: {e}")
            return False

        try:
            await self.websocket.send(message.to_json())
            return True
        except Exception as e:
            self.logger.error(f"消息发送失败: {e}")
            # 缓存到队列
            try:
                if not self.message_queue.full():
                    self.message_queue.put_nowait(message)
            except:
                pass
            return False

    async def _receive_loop(self):
        """消息接收循环"""
        while self._running and self.websocket:
            try:
                message_str = await self.websocket.recv()
                message = SyncMessage.from_json(message_str)
                await self._handle_message(message)
            except websockets.exceptions.ConnectionClosed:
                self.logger.warning("连接已关闭")
                break
            except Exception as e:
                self.logger.error(f"消息接收异常: {e}")
                if not self._running:
                    break

        # 连接断开，触发重连
        if self._running:
            self.state = ClientState.DISCONNECTED
            await self._schedule_reconnect()

    async def _handle_message(self, message: SyncMessage):
        """处理收到的消息"""
        self.logger.debug(f"收到消息: {message.type} from {message.sender} (v{message.version})")

        # 更新服务端版本号
        if message.version > self.server_version:
            self.server_version = message.version

        # 根据消息类型处理
        handler_name = f"_handle_{message.type.lower()}"
        handler = getattr(self, handler_name, None)
        if handler:
            try:
                await handler(message)
            except Exception as e:
                self.logger.error(f"处理消息 {message.type} 失败: {e}")

        # 触发事件
        await self._emit_event(message.type, message)

    async def _handle_welcome(self, message: SyncMessage):
        """处理WELCOME消息"""
        payload = message.payload
        self.session_id = payload.get("session_id", "")
        self.server_version = payload.get("server_version", 0)
        self.state = ClientState.AUTHENTICATED
        self.logger.info(f"认证成功，会话ID: {self.session_id}, 服务端版本: {self.server_version}")

        # 补发缓存的消息
        await self._flush_message_queue()

        # 请求状态同步
        if self.config.enable_auto_sync:
            await self.request_state_sync()

    async def _handle_heartbeat_ack(self, message: SyncMessage):
        """处理心跳确认"""
        self.last_heartbeat = time.time()
        self.server_version = message.payload.get("server_version", self.server_version)

    async def _handle_state_sync(self, message: SyncMessage):
        """处理状态同步"""
        payload = message.payload
        sync_type = payload.get("sync_type", "full")
        data = payload.get("data", {})

        if sync_type == "full":
            self.local_version = data.get("version", self.local_version)
            self.logger.info(f"全量状态同步完成，版本: {self.local_version}")
        else:
            from_version = data.get("from_version", 0)
            to_version = data.get("to_version", 0)
            changes = data.get("changes", [])
            self.local_version = to_version
            self.logger.info(f"增量状态同步完成，{from_version} -> {to_version}, {len(changes)} 条变更")

        self.last_sync = time.time()

    async def _handle_truth_broadcast(self, message: SyncMessage):
        """处理真值广播"""
        payload = message.payload
        self.local_version = payload.get("version", self.local_version)
        self.logger.debug(f"收到真值广播: {payload.get('truth_key', 'unknown')}")

    async def _handle_decision_broadcast(self, message: SyncMessage):
        """处理决策广播"""
        payload = message.payload
        self.local_version = payload.get("version", self.local_version)
        self.logger.debug(f"收到决策广播: {payload.get('decision_id', 'unknown')}")

    async def _handle_meta_law_update(self, message: SyncMessage):
        """处理元法则更新"""
        payload = message.payload
        self.local_version = payload.get("version", self.local_version)
        self.logger.info(f"收到元法则更新: {payload.get('law_id', 'unknown')}")

    async def _handle_action_response(self, message: SyncMessage):
        """处理操作响应"""
        payload = message.payload
        status = payload.get("status", "unknown")
        self.logger.info(f"操作响应: {status}")

    async def _handle_error(self, message: SyncMessage):
        """处理错误消息"""
        payload = message.payload
        self.logger.error(f"服务端错误: {payload.get('error', 'unknown')}")

    async def _flush_message_queue(self):
        """补发缓存的消息"""
        if self.message_queue.empty():
            return

        self.logger.info(f"正在补发缓存的消息 ({self.message_queue.qsize()} 条)...")
        while not self.message_queue.empty():
            try:
                message = self.message_queue.get_nowait()
                await self._send(message)
            except Exception as e:
                self.logger.error(f"补发消息失败: {e}")
                break
        self.logger.info("消息补发完成")

    # ============================================================
    # 心跳与同步
    # ============================================================

    async def _heartbeat_loop(self):
        """心跳循环"""
        while self._running:
            await asyncio.sleep(self.config.heartbeat_interval)
            if self.state in (ClientState.CONNECTED, ClientState.AUTHENTICATED):
                try:
                    msg = self._create_message("HEARTBEAT", {
                        "local_version": self.local_version,
                        "timestamp": time.time()
                    })
                    await self._send(msg)
                    self.last_heartbeat = time.time()
                except Exception as e:
                    self.logger.error(f"心跳发送失败: {e}")

    async def _periodic_sync_loop(self):
        """定期同步循环"""
        while self._running:
            await asyncio.sleep(self.config.sync_interval)
            if self.state == ClientState.AUTHENTICATED:
                try:
                    await self.request_state_sync(sync_type="auto")
                except Exception as e:
                    self.logger.error(f"定期同步失败: {e}")

    # ============================================================
    # 公开API
    # ============================================================

    async def _send_hello(self):
        """发送HELLO消息"""
        msg = self._create_message("HELLO", {
            "node_id": self.config.node_id,
            "node_type": self.config.node_type,
            "version": self.local_version,
            "permissions": self.config.permissions,
            "client_version": "1.0.0"
        })
        await self._send(msg)

    async def request_state_sync(self, sync_type: str = "auto", since_version: Optional[int] = None):
        """请求状态同步"""
        payload = {"type": sync_type}
        if since_version is not None:
            payload["since_version"] = since_version
        msg = self._create_message("STATE_REQUEST", payload)
        await self._send(msg)
        self.logger.debug(f"已请求状态同步: {sync_type}")

    async def report_truth(self, truth_key: str, truth_value: str, category: str = "general") -> bool:
        """上报真值"""
        msg = self._create_message("TRUTH_REPORT", {
            "truth_key": truth_key,
            "truth_value": truth_value,
            "category": category
        })
        return await self._send(msg)

    async def report_decision(self, decision_content: Dict[str, Any], decision_type: str = "general") -> bool:
        """上报决策"""
        msg = self._create_message("DECISION_REPORT", {
            "decision_id": str(uuid.uuid4()),
            "content": decision_content,
            "type": decision_type
        })
        return await self._send(msg)

    async def request_action(self, action: str, params: Optional[Dict[str, Any]] = None) -> bool:
        """请求操作（需审批）"""
        msg = self._create_message("ACTION_REQUEST", {
            "action": action,
            "params": params or {}
        })
        return await self._send(msg)

    async def send_ack(self, original_message: SyncMessage):
        """发送消息确认"""
        msg = self._create_message("ACK", {
            "ack_id": original_message.id,
            "received_at": time.time()
        })
        await self._send(msg)

    def get_state(self) -> Dict[str, Any]:
        """获取客户端状态"""
        return {
            "node_id": self.config.node_id,
            "node_type": self.config.node_type,
            "state": self.state.value,
            "session_id": self.session_id,
            "local_version": self.local_version,
            "server_version": self.server_version,
            "reconnect_attempts": self.reconnect_attempts,
            "message_queue_size": self.message_queue.qsize(),
            "last_heartbeat": self.last_heartbeat,
            "last_sync": self.last_sync,
            "connected": self.state in (ClientState.CONNECTED, ClientState.AUTHENTICATED)
        }

# ============================================================
# 使用示例
# ============================================================

async def example_usage():
    """使用示例"""

    # 1. 创建客户端
    config = ClientConfig(
        server_url="ws://127.0.0.1:9130",
        node_id="example-node-001",
        node_type="dialog",
        permissions=["read", "write"]
    )
    client = WSSyncClient(config)

    # 2. 注册事件处理器
    async def on_truth_broadcast(message: SyncMessage, client: WSSyncClient):
        print(f"收到真值广播: {message.payload.get('truth_key')}")

    async def on_state_sync(message: SyncMessage, client: WSSyncClient):
        print(f"状态同步完成，本地版本: {client.local_version}")

    client.on("TRUTH_BROADCAST", on_truth_broadcast)
    client.on("STATE_SYNC", on_state_sync)

    # 3. 连接
    await client.connect()

    # 4. 等待连接建立
    await asyncio.sleep(2)

    # 5. 上报真值
    await client.report_truth(
        truth_key="EXAMPLE.TRUTH.001",
        truth_value="这是一个测试真值",
        category="test"
    )

    # 6. 上报决策
    await client.report_decision(
        decision_content={"decision": "测试决策", "result": "approved"},
        decision_type="test"
    )

    # 7. 运行一段时间
    print("客户端运行中，按Ctrl+C停止...")
    try:
        while True:
            await asyncio.sleep(10)
            state = client.get_state()
            print(f"状态: {state['state']}, 本地版本: {state['local_version']}, 队列: {state['message_queue_size']}")
    except KeyboardInterrupt:
        pass

    # 8. 断开连接
    await client.disconnect()

# ============================================================
# 主入口
# ============================================================

def main():
    """主入口"""
    import argparse

    parser = argparse.ArgumentParser(description="中枢智能WebSocket实时同步客户端")
    parser.add_argument("--server", default="ws://127.0.0.1:9130", help="服务端地址")
    parser.add_argument("--node-id", default="", help="节点ID")
    parser.add_argument("--node-type", default="dialog", choices=["dialog", "dev", "worker", "admin"], help="节点类型")
    parser.add_argument("--example", action="store_true", help="运行示例")

    args = parser.parse_args()

    if args.example:
        asyncio.run(example_usage())
        return

    config = ClientConfig(
        server_url=args.server,
        node_id=args.node_id,
        node_type=args.node_type
    )
    client = WSSyncClient(config)

    async def run():
        await client.connect()
        try:
            while True:
                await asyncio.sleep(10)
        except KeyboardInterrupt:
            pass
        finally:
            await client.disconnect()

    asyncio.run(run())

if __name__ == "__main__":
    main()
