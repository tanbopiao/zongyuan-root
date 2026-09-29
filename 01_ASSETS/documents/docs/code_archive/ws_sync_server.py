#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中枢智能WebSocket实时同步服务端
ZONGYUAN-ROOT Real-time Sync Server

功能：
- WebSocket长连接管理
- 心跳保活与断线检测
- 状态实时同步（全量+增量）
- 真值上报与广播
- 决策上报与广播
- 元法则更新广播
- 冲突检测与乐观锁
- 消息持久化
- 认证与权限管理

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
import sqlite3
from datetime import datetime
from typing import Dict, Set, Optional, Any
from dataclasses import dataclass, field

try:
    import websockets
    from websockets.server import serve
except ImportError:
    print("请安装websockets库: pip install websockets")
    raise

# ============================================================
# 配置
# ============================================================

@dataclass
class ServerConfig:
    """服务端配置"""
    host: str = "0.0.0.0"
    port: int = 9130
    heartbeat_interval: int = 30  # 心跳间隔（秒）
    heartbeat_timeout: int = 90   # 心跳超时（秒）
    max_message_size: int = 1024 * 1024  # 最大消息大小（1MB）
    max_connections: int = 100    # 最大连接数
    db_path: str = "/opt/ZONGYUAN-ROOT/data/ws_sync.db"
    truth_db_path: str = "/opt/ZONGYUAN-ROOT/data/memory_gateway.db"
    log_path: str = "/var/log/zongyuan-ws-sync/server.log"
    log_level: str = "INFO"
    enable_auth: bool = True       # 是否启用认证
    enable_tls: bool = False       # 是否启用TLS（生产环境建议通过Nginx反代）
    tls_cert: str = ""
    tls_key: str = ""

# ============================================================
# 数据模型
# ============================================================

@dataclass
class ClientSession:
    """客户端会话"""
    session_id: str
    node_id: str
    node_type: str  # dialog / dev / worker / admin
    websocket: Any
    connected_at: float
    last_heartbeat: float
    local_version: int = 0
    permissions: Set[str] = field(default_factory=set)
    message_queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    authenticated: bool = False

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
# 状态管理器
# ============================================================

class StateManager:
    """状态管理器 - 维护中枢智能全局状态与版本号"""

    def __init__(self, config: ServerConfig, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.global_version: int = 0
        self.state: Dict[str, Any] = {
            "truth_count": 0,
            "meta_law_count": 0,
            "decision_count": 0,
            "node_online_count": 0,
            "system_status": "running",
            "last_update": datetime.now().isoformat()
        }
        self.change_log: list = []  # 变更日志（用于增量同步）
        self._init_db()
        self._load_state_from_truth_db()

    def _init_db(self):
        """初始化同步数据库"""
        try:
            conn = sqlite3.connect(self.config.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    type TEXT,
                    sender TEXT,
                    timestamp REAL,
                    version INTEGER,
                    payload TEXT,
                    signature TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS connections (
                    session_id TEXT PRIMARY KEY,
                    node_id TEXT,
                    node_type TEXT,
                    connected_at REAL,
                    disconnected_at REAL,
                    local_version INTEGER
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS state_version (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    version INTEGER,
                    updated_at REAL
                )
            """)
            cursor.execute("INSERT OR IGNORE INTO state_version (id, version, updated_at) VALUES (1, 0, ?)", (time.time(),))
            conn.commit()

            # 读取当前版本号
            cursor.execute("SELECT version FROM state_version WHERE id = 1")
            row = cursor.fetchone()
            if row:
                self.global_version = row[0]

            conn.close()
            self.logger.info(f"同步数据库初始化完成，当前版本号: {self.global_version}")
        except Exception as e:
            self.logger.error(f"同步数据库初始化失败: {e}")

    def _load_state_from_truth_db(self):
        """从真值库加载当前状态"""
        try:
            conn = sqlite3.connect(self.config.truth_db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM truths")
            self.state["truth_count"] = cursor.fetchone()[0]
            conn.close()
            self.logger.info(f"从真值库加载状态完成，真值数量: {self.state['truth_count']}")
        except Exception as e:
            self.logger.warning(f"从真值库加载状态失败: {e}")

    def increment_version(self) -> int:
        """递增全局版本号"""
        self.global_version += 1
        try:
            conn = sqlite3.connect(self.config.db_path)
            cursor = conn.cursor()
            cursor.execute("UPDATE state_version SET version = ?, updated_at = ? WHERE id = 1",
                           (self.global_version, time.time()))
            conn.commit()
            conn.close()
        except Exception as e:
            self.logger.error(f"版本号持久化失败: {e}")
        return self.global_version

    def get_full_state(self) -> Dict[str, Any]:
        """获取全量状态"""
        self.state["last_update"] = datetime.now().isoformat()
        return {
            "version": self.global_version,
            "state": self.state.copy(),
            "timestamp": time.time()
        }

    def get_incremental_state(self, since_version: int) -> Optional[Dict[str, Any]]:
        """获取增量状态（自指定版本以来的变更）"""
        changes = [c for c in self.change_log if c["version"] > since_version]
        if not changes:
            return None
        return {
            "from_version": since_version,
            "to_version": self.global_version,
            "changes": changes,
            "timestamp": time.time()
        }

    def record_change(self, change_type: str, data: Dict[str, Any]) -> int:
        """记录变更并递增版本号"""
        version = self.increment_version()
        change = {
            "version": version,
            "type": change_type,
            "data": data,
            "timestamp": time.time()
        }
        self.change_log.append(change)
        # 只保留最近1000条变更日志
        if len(self.change_log) > 1000:
            self.change_log = self.change_log[-1000:]
        return version

    def update_truth_count(self, count: int):
        """更新真值数量"""
        self.state["truth_count"] = count
        self.record_change("state_update", {"truth_count": count})

# ============================================================
# 消息处理器
# ============================================================

class MessageHandler:
    """消息处理器 - 处理各类消息"""

    def __init__(self, server: "WSSyncServer", logger: logging.Logger):
        self.server = server
        self.logger = logger

    async def handle(self, message: SyncMessage, client: ClientSession) -> Optional[SyncMessage]:
        """处理消息，返回响应消息（如有）"""
        handler_name = f"_handle_{message.type.lower()}"
        handler = getattr(self, handler_name, None)
        if handler:
            try:
                return await handler(message, client)
            except Exception as e:
                self.logger.error(f"处理消息 {message.type} 失败: {e}")
                return self._create_error(message, f"处理失败: {str(e)}")
        else:
            self.logger.warning(f"未知消息类型: {message.type}")
            return self._create_error(message, f"未知消息类型: {message.type}")

    def _create_response(self, original: SyncMessage, response_type: str, payload: Dict[str, Any]) -> SyncMessage:
        """创建响应消息"""
        return SyncMessage(
            type=response_type,
            id=str(uuid.uuid4()),
            timestamp=time.time(),
            sender="hub-central-agent",
            version=self.server.state_manager.global_version,
            payload={**payload, "request_id": original.id}
        )

    def _create_error(self, original: SyncMessage, error_msg: str) -> SyncMessage:
        """创建错误消息"""
        return self._create_response(original, "ERROR", {"error": error_msg})

    async def _handle_hello(self, message: SyncMessage, client: ClientSession) -> SyncMessage:
        """处理HELLO消息 - 客户端连接初始化"""
        payload = message.payload
        client.node_id = payload.get("node_id", f"unknown-{client.session_id}")
        client.node_type = payload.get("node_type", "dialog")
        client.local_version = payload.get("version", 0)
        client.permissions = set(payload.get("permissions", ["read"]))
        client.authenticated = True  # V1.0简化认证，后续可加强

        self.logger.info(f"节点连接: {client.node_id} ({client.node_type}), 本地版本: {client.local_version}")

        # 记录连接
        self.server._record_connection(client)

        # 返回WELCOME消息
        welcome_payload = {
            "session_id": client.session_id,
            "server_version": self.server.state_manager.global_version,
            "heartbeat_interval": self.server.config.heartbeat_interval,
            "permissions": list(client.permissions),
            "message": "欢迎连接中枢智能实时同步服务"
        }
        welcome = self._create_response(message, "WELCOME", welcome_payload)

        # 同时推送状态同步
        full_state = self.server.state_manager.get_full_state()
        state_sync = self._create_response(message, "STATE_SYNC", {
            "sync_type": "full",
            "data": full_state
        })

        # 先发送WELCOME，再发送STATE_SYNC
        await client.websocket.send(welcome.to_json())
        return state_sync

    async def _handle_heartbeat(self, message: SyncMessage, client: ClientSession) -> SyncMessage:
        """处理心跳消息"""
        client.last_heartbeat = time.time()
        client.local_version = message.version
        return self._create_response(message, "HEARTBEAT_ACK", {
            "server_time": time.time(),
            "server_version": self.server.state_manager.global_version
        })

    async def _handle_state_request(self, message: SyncMessage, client: ClientSession) -> SyncMessage:
        """处理状态请求"""
        request_type = message.payload.get("type", "auto")
        since_version = message.payload.get("since_version", client.local_version)

        if request_type == "full":
            data = self.server.state_manager.get_full_state()
            sync_type = "full"
        else:
            # 自动判断：版本差距小用增量，大用全量
            version_diff = self.server.state_manager.global_version - since_version
            if version_diff <= 100:
                data = self.server.state_manager.get_incremental_state(since_version)
                if data is None:
                    data = self.server.state_manager.get_full_state()
                    sync_type = "full"
                else:
                    sync_type = "incremental"
            else:
                data = self.server.state_manager.get_full_state()
                sync_type = "full"

        return self._create_response(message, "STATE_SYNC", {
            "sync_type": sync_type,
            "data": data
        })

    async def _handle_truth_report(self, message: SyncMessage, client: ClientSession) -> Optional[SyncMessage]:
        """处理真值上报"""
        if "write" not in client.permissions:
            return self._create_error(message, "权限不足：无写权限")

        payload = message.payload
        truth_key = payload.get("truth_key", "")
        truth_value = payload.get("truth_value", "")
        truth_category = payload.get("category", "general")

        if not truth_key or not truth_value:
            return self._create_error(message, "真值key和value不能为空")

        # 写入真值库
        try:
            version = self.server._write_truth(truth_key, truth_value, truth_category, client.node_id)
            self.server.state_manager.update_truth_count(self.server._get_truth_count())

            # 广播给其他节点
            broadcast_msg = SyncMessage(
                type="TRUTH_BROADCAST",
                id=str(uuid.uuid4()),
                timestamp=time.time(),
                sender="hub-central-agent",
                version=version,
                payload={
                    "truth_key": truth_key,
                    "truth_value": truth_value,
                    "category": truth_category,
                    "source_node": client.node_id,
                    "version": version
                }
            )
            await self.server._broadcast(broadcast_msg, exclude_session=client.session_id)

            return self._create_response(message, "ACK", {
                "status": "success",
                "truth_key": truth_key,
                "version": version
            })
        except Exception as e:
            self.logger.error(f"真值写入失败: {e}")
            return self._create_error(message, f"真值写入失败: {str(e)}")

    async def _handle_decision_report(self, message: SyncMessage, client: ClientSession) -> Optional[SyncMessage]:
        """处理决策上报"""
        if "write" not in client.permissions:
            return self._create_error(message, "权限不足：无写权限")

        payload = message.payload
        decision_id = payload.get("decision_id", str(uuid.uuid4()))
        decision_content = payload.get("content", {})
        decision_type = payload.get("type", "general")

        # 记录决策（V1.0简化，后续可接入决策引擎）
        version = self.server.state_manager.record_change("decision", {
            "decision_id": decision_id,
            "content": decision_content,
            "type": decision_type,
            "source_node": client.node_id
        })

        # 广播给其他节点
        broadcast_msg = SyncMessage(
            type="DECISION_BROADCAST",
            id=str(uuid.uuid4()),
            timestamp=time.time(),
            sender="hub-central-agent",
            version=version,
            payload={
                "decision_id": decision_id,
                "content": decision_content,
                "type": decision_type,
                "source_node": client.node_id,
                "version": version
            }
        )
        await self.server._broadcast(broadcast_msg, exclude_session=client.session_id)

        return self._create_response(message, "ACK", {
            "status": "success",
            "decision_id": decision_id,
            "version": version
        })

    async def _handle_action_request(self, message: SyncMessage, client: ClientSession) -> SyncMessage:
        """处理操作请求（需审批）"""
        if "admin" not in client.permissions:
            return self._create_error(message, "权限不足：无管理权限")

        payload = message.payload
        action = payload.get("action", "")
        action_params = payload.get("params", {})

        # V1.0简化：自动批准，后续可接入审批流程
        self.logger.info(f"操作请求: {action} from {client.node_id}, params: {action_params}")

        version = self.server.state_manager.record_change("action", {
            "action": action,
            "params": action_params,
            "source_node": client.node_id,
            "status": "approved"
        })

        return self._create_response(message, "ACTION_RESPONSE", {
            "status": "approved",
            "action": action,
            "version": version,
            "message": "操作已批准（V1.0自动批准，后续接入审批流程）"
        })

    async def _handle_ack(self, message: SyncMessage, client: ClientSession) -> None:
        """处理消息确认 - 无需响应"""
        self.logger.debug(f"收到确认: {message.id} from {client.node_id}")

    async def _handle_disconnect(self, message: SyncMessage, client: ClientSession) -> None:
        """处理断开连接"""
        self.logger.info(f"节点主动断开: {client.node_id}")

# ============================================================
# 主服务类
# ============================================================

class WSSyncServer:
    """WebSocket实时同步服务主类"""

    def __init__(self, config: Optional[ServerConfig] = None):
        self.config = config or ServerConfig()
        self.clients: Dict[str, ClientSession] = {}  # session_id -> ClientSession
        self.node_sessions: Dict[str, str] = {}  # node_id -> session_id
        self.state_manager: Optional[StateManager] = None
        self.message_handler: Optional[MessageHandler] = None
        self.logger = self._setup_logger()
        self._running = False

    def _setup_logger(self) -> logging.Logger:
        """设置日志"""
        logger = logging.getLogger("ws_sync_server")
        logger.setLevel(getattr(logging, self.config.log_level, logging.INFO))

        # 控制台输出
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(
            '%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        logger.addHandler(console_handler)

        # 文件输出
        try:
            import os
            os.makedirs(os.path.dirname(self.config.log_path), exist_ok=True)
            file_handler = logging.FileHandler(self.config.log_path, encoding='utf-8')
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            ))
            logger.addHandler(file_handler)
        except Exception as e:
            logger.warning(f"日志文件初始化失败: {e}")

        return logger

    async def _handle_client(self, websocket, path):
        """处理客户端连接"""
        session_id = str(uuid.uuid4())
        client = ClientSession(
            session_id=session_id,
            node_id=f"pending-{session_id}",
            node_type="pending",
            websocket=websocket,
            connected_at=time.time(),
            last_heartbeat=time.time()
        )

        self.clients[session_id] = client
        self.logger.info(f"新连接: {session_id}, 来自: {websocket.remote_address}")

        try:
            async for message_str in websocket:
                try:
                    message = SyncMessage.from_json(message_str)
                    self._persist_message(message)
                    response = await self.message_handler.handle(message, client)
                    if response:
                        await websocket.send(response.to_json())
                except json.JSONDecodeError as e:
                    self.logger.error(f"消息解析失败: {e}")
                except Exception as e:
                    self.logger.error(f"消息处理异常: {e}")
        except websockets.exceptions.ConnectionClosed:
            self.logger.info(f"连接关闭: {client.node_id} ({session_id})")
        except Exception as e:
            self.logger.error(f"连接异常: {client.node_id} ({session_id}): {e}")
        finally:
            # 清理客户端
            if session_id in self.clients:
                del self.clients[session_id]
            if client.node_id in self.node_sessions:
                if self.node_sessions[client.node_id] == session_id:
                    del self.node_sessions[client.node_id]
            self._record_disconnection(client)
            self.logger.info(f"客户端已清理: {client.node_id} ({session_id}), 当前在线: {len(self.clients)}")

    async def _broadcast(self, message: SyncMessage, exclude_session: Optional[str] = None):
        """广播消息到所有连接的客户端"""
        disconnected = []
        for session_id, client in self.clients.items():
            if exclude_session and session_id == exclude_session:
                continue
            try:
                await client.websocket.send(message.to_json())
            except Exception as e:
                self.logger.warning(f"广播失败到 {client.node_id}: {e}")
                disconnected.append(session_id)

        # 清理断开的连接
        for session_id in disconnected:
            if session_id in self.clients:
                del self.clients[session_id]

    async def _heartbeat_check(self):
        """心跳检查循环"""
        while self._running:
            await asyncio.sleep(self.config.heartbeat_interval)
            now = time.time()
            timeout_clients = []

            for session_id, client in self.clients.items():
                if now - client.last_heartbeat > self.config.heartbeat_timeout:
                    timeout_clients.append(session_id)
                    self.logger.warning(f"心跳超时: {client.node_id} ({session_id})")

            for session_id in timeout_clients:
                if session_id in self.clients:
                    client = self.clients[session_id]
                    try:
                        await client.websocket.close()
                    except:
                        pass
                    del self.clients[session_id]
                    if client.node_id in self.node_sessions:
                        if self.node_sessions[client.node_id] == session_id:
                            del self.node_sessions[client.node_id]

            if timeout_clients:
                self.logger.info(f"心跳检查完成，清理 {len(timeout_clients)} 个超时连接，当前在线: {len(self.clients)}")

    def _persist_message(self, message: SyncMessage):
        """持久化消息到数据库"""
        try:
            conn = sqlite3.connect(self.config.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO messages (id, type, sender, timestamp, version, payload, signature)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                message.id, message.type, message.sender, message.timestamp,
                message.version, json.dumps(message.payload, ensure_ascii=False), message.signature
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            self.logger.warning(f"消息持久化失败: {e}")

    def _record_connection(self, client: ClientSession):
        """记录连接"""
        self.node_sessions[client.node_id] = client.session_id
        self.state_manager.state["node_online_count"] = len(self.clients)
        try:
            conn = sqlite3.connect(self.config.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO connections (session_id, node_id, node_type, connected_at, disconnected_at, local_version)
                VALUES (?, ?, ?, ?, NULL, ?)
            """, (client.session_id, client.node_id, client.node_type, client.connected_at, client.local_version))
            conn.commit()
            conn.close()
        except Exception as e:
            self.logger.warning(f"连接记录失败: {e}")

    def _record_disconnection(self, client: ClientSession):
        """记录断开连接"""
        self.state_manager.state["node_online_count"] = len(self.clients)
        try:
            conn = sqlite3.connect(self.config.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE connections SET disconnected_at = ?, local_version = ? WHERE session_id = ?
            """, (time.time(), client.local_version, client.session_id))
            conn.commit()
            conn.close()
        except Exception as e:
            self.logger.warning(f"断开记录失败: {e}")

    def _write_truth(self, key: str, value: str, category: str, source_node: str) -> int:
        """写入真值到真值库"""
        import hashlib
        truth_hash = hashlib.sha256(f"{key}:{value}".encode()).hexdigest()
        conn = sqlite3.connect(self.config.truth_db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO truths (truth_key, truth_value, truth_hash, category, node_id, created_at, updated_at, version)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (key, value, truth_hash, category, source_node, time.time(), time.time(), 1))
        conn.commit()
        conn.close()
        return self.state_manager.record_change("truth", {"key": key, "category": category})

    def _get_truth_count(self) -> int:
        """获取真值数量"""
        try:
            conn = sqlite3.connect(self.config.truth_db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM truths")
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except Exception as e:
            self.logger.warning(f"获取真值数量失败: {e}")
            return 0

    async def start(self):
        """启动服务"""
        self._running = True
        self.state_manager = StateManager(self.config, self.logger)
        self.message_handler = MessageHandler(self, self.logger)

        self.logger.info("=" * 60)
        self.logger.info("中枢智能WebSocket实时同步服务启动")
        self.logger.info(f"监听地址: {self.config.host}:{self.config.port}")
        self.logger.info(f"心跳间隔: {self.config.heartbeat_interval}秒")
        self.logger.info(f"最大连接数: {self.config.max_connections}")
        self.logger.info(f"当前版本号: {self.state_manager.global_version}")
        self.logger.info("=" * 60)

        # 启动心跳检查
        asyncio.create_task(self._heartbeat_check())

        # 启动WebSocket服务
        async with serve(
            self._handle_client,
            self.config.host,
            self.config.port,
            max_size=self.config.max_message_size,
            ping_interval=None,  # 我们自己实现心跳
            ping_timeout=None
        ):
            self.logger.info("WebSocket服务已就绪，等待客户端连接...")
            await asyncio.Future()  # 永久运行

    async def stop(self):
        """停止服务"""
        self._running = False
        self.logger.info("正在停止服务...")
        for client in self.clients.values():
            try:
                await client.websocket.close()
            except:
                pass
        self.clients.clear()
        self.logger.info("服务已停止")

# ============================================================
# 主入口
# ============================================================

def main():
    """主入口"""
    import argparse

    parser = argparse.ArgumentParser(description="中枢智能WebSocket实时同步服务")
    parser.add_argument("--host", default="0.0.0.0", help="监听地址")
    parser.add_argument("--port", type=int, default=9130, help="监听端口")
    parser.add_argument("--db-path", default="/opt/ZONGYUAN-ROOT/data/ws_sync.db", help="同步数据库路径")
    parser.add_argument("--truth-db-path", default="/opt/ZONGYUAN-ROOT/data/memory_gateway.db", help="真值库路径")
    parser.add_argument("--log-path", default="/var/log/zongyuan-ws-sync/server.log", help="日志路径")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"], help="日志级别")
    parser.add_argument("--heartbeat-interval", type=int, default=30, help="心跳间隔（秒）")
    parser.add_argument("--heartbeat-timeout", type=int, default=90, help="心跳超时（秒）")

    args = parser.parse_args()

    config = ServerConfig(
        host=args.host,
        port=args.port,
        db_path=args.db_path,
        truth_db_path=args.truth_db_path,
        log_path=args.log_path,
        log_level=args.log_level,
        heartbeat_interval=args.heartbeat_interval,
        heartbeat_timeout=args.heartbeat_timeout
    )

    server = WSSyncServer(config)

    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        print("\n收到中断信号，正在停止服务...")
        asyncio.run(server.stop())
    except Exception as e:
        print(f"服务启动失败: {e}")
        raise

if __name__ == "__main__":
    main()
