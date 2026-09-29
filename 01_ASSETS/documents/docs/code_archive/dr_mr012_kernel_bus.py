#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT MR-012 元极内核总线
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | Ω-TAN-7-001

定位：体系的中枢神经系统，所有组件的统一通信和状态枢纽。

核心功能：
  1. 组件注册中心 - 所有MR组件启动时注册，上报能力和状态
  2. 统一状态总线 - 全局内核状态的单一数据源
  3. 事件通信通道 - 组件间事件发布/订阅，协同响应
  4. 指令分发器   - 统一接收外部指令，分发到对应组件
  5. 心跳与健康检查 - 所有组件心跳上报，异常自动告警

技术设计：
  - 基于SQLite + HTTP API的轻量级总线
  - 状态存储：/opt/ZONGYUAN-ROOT/kernel/bus_state.db
  - API端口：9121（与9120记忆网关分离）
"""

import os
import sys
import json
import time
import sqlite3
import logging
import hashlib
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, List, Optional, Any, Tuple

# ============================================================
# 配置
# ============================================================
CONFIG = {
    "host": "127.0.0.1",
    "port": 9121,
    "db_path": "/opt/ZONGYUAN-ROOT/kernel/bus_state.db",
    "log_file": "/opt/ZONGYUAN-ROOT/kernel/bus.log",
    "audit_log": "/opt/ZONGYUAN-ROOT/kernel/bus_audit.jsonl",
    "heartbeat_timeout": 120,      # 心跳超时（秒）
    "event_retention": 86400,       # 事件保留时间（秒）
    "node_id": "mr012-kernel-bus",
    "did": "DID-BR-000002",
    "trace_mark": "Ω₀⊂⊙∞⊂Ω",
}

# ============================================================
# 日志
# ============================================================
def setup_logging():
    os.makedirs(os.path.dirname(CONFIG["log_file"]), exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(CONFIG["log_file"]),
            logging.StreamHandler(sys.stdout),
        ],
    )
    return logging.getLogger("mr012")

logger = setup_logging()

# ============================================================
# 数据库
# ============================================================
class BusDatabase:
    """内核总线数据库"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self):
        conn = self._get_conn()
        cursor = conn.cursor()

        # 组件注册表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS components (
                component_id TEXT PRIMARY KEY,
                component_type TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                capabilities TEXT,           -- JSON数组
                status TEXT DEFAULT 'inactive', -- active/inactive/error/maintenance
                version TEXT,
                config TEXT,                  -- JSON对象
                registered_at REAL NOT NULL,
                last_heartbeat REAL,
                heartbeat_count INTEGER DEFAULT 0,
                metadata TEXT                 -- JSON对象
            )
        """)

        # 心跳记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS heartbeats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                component_id TEXT NOT NULL,
                timestamp REAL NOT NULL,
                status TEXT,
                metrics TEXT,                 -- JSON对象（CPU/内存/自定义指标）
                FOREIGN KEY (component_id) REFERENCES components(component_id)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_heartbeats_component ON heartbeats(component_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_heartbeats_timestamp ON heartbeats(timestamp)")

        # 全局内核状态表（键值对）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS kernel_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                value_type TEXT DEFAULT 'string', -- string/json/number/bool
                updated_by TEXT,
                updated_at REAL NOT NULL,
                version INTEGER DEFAULT 1
            )
        """)

        # 事件表（发布/订阅）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                source TEXT NOT NULL,
                target TEXT,                   -- 目标组件，NULL表示广播
                payload TEXT,                  -- JSON对象
                priority INTEGER DEFAULT 0,    -- 0=普通, 1=重要, 2=紧急
                timestamp REAL NOT NULL,
                consumed INTEGER DEFAULT 0,    -- 是否已被消费
                consumed_by TEXT,
                consumed_at REAL
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_consumed ON events(consumed)")

        # 指令表（分发/执行）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS commands (
                command_id TEXT PRIMARY KEY,
                command_type TEXT NOT NULL,
                target_component TEXT NOT NULL,
                payload TEXT,                  -- JSON对象
                status TEXT DEFAULT 'pending', -- pending/dispatched/executing/completed/failed
                result TEXT,                   -- JSON对象
                dispatched_at REAL,
                completed_at REAL,
                created_at REAL NOT NULL,
                created_by TEXT
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_commands_status ON commands(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_commands_target ON commands(target_component)")

        # 审计日志表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                action TEXT NOT NULL,
                actor TEXT,
                detail TEXT,                   -- JSON对象
                result TEXT                    -- success/failure
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp)")

        conn.commit()
        conn.close()
        logger.info("数据库初始化完成")

    # --- 组件管理 ---
    def register_component(self, component_id: str, component_type: str, name: str,
                           description: str = "", capabilities: List = None,
                           version: str = "", config: Dict = None, metadata: Dict = None) -> bool:
        """注册组件"""
        conn = self._get_conn()
        cursor = conn.cursor()
        now = time.time()
        try:
            cursor.execute("""
                INSERT INTO components (component_id, component_type, name, description, capabilities, status, version, config, registered_at, last_heartbeat, metadata)
                VALUES (?, ?, ?, ?, ?, 'active', ?, ?, ?, ?, ?)
                ON CONFLICT(component_id) DO UPDATE SET
                    component_type=excluded.component_type,
                    name=excluded.name,
                    description=excluded.description,
                    capabilities=excluded.capabilities,
                    status='active',
                    version=excluded.version,
                    config=excluded.config,
                    last_heartbeat=excluded.last_heartbeat,
                    metadata=excluded.metadata
            """, (
                component_id, component_type, name, description,
                json.dumps(capabilities or []),
                version, json.dumps(config or {}),
                now, now, json.dumps(metadata or {})
            ))
            conn.commit()
            self._audit("component_register", component_id, {"component_type": component_type, "name": name}, "success")
            return True
        except Exception as e:
            logger.error(f"组件注册失败: {e}")
            self._audit("component_register", component_id, {"error": str(e)}, "failure")
            return False
        finally:
            conn.close()

    def heartbeat(self, component_id: str, status: str = "active", metrics: Dict = None) -> bool:
        """组件心跳"""
        conn = self._get_conn()
        cursor = conn.cursor()
        now = time.time()
        try:
            cursor.execute("""
                UPDATE components SET last_heartbeat=?, heartbeat_count=heartbeat_count+1, status=?
                WHERE component_id=?
            """, (now, status, component_id))
            if cursor.rowcount == 0:
                return False
            cursor.execute("""
                INSERT INTO heartbeats (component_id, timestamp, status, metrics) VALUES (?, ?, ?, ?)
            """, (component_id, now, status, json.dumps(metrics or {})))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"心跳失败: {e}")
            return False
        finally:
            conn.close()

    def get_component(self, component_id: str) -> Optional[Dict]:
        """获取组件详情"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM components WHERE component_id=?", (component_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            d = dict(row)
            d["capabilities"] = json.loads(d.get("capabilities") or "[]")
            d["config"] = json.loads(d.get("config") or "{}")
            d["metadata"] = json.loads(d.get("metadata") or "{}")
            return d
        return None

    def list_components(self, status_filter: str = None) -> List[Dict]:
        """列出所有组件"""
        conn = self._get_conn()
        cursor = conn.cursor()
        if status_filter:
            cursor.execute("SELECT * FROM components WHERE status=? ORDER BY registered_at", (status_filter,))
        else:
            cursor.execute("SELECT * FROM components ORDER BY registered_at")
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        now = time.time()
        for row in rows:
            row["capabilities"] = json.loads(row.get("capabilities") or "[]")
            row["config"] = json.loads(row.get("config") or "{}")
            row["metadata"] = json.loads(row.get("metadata") or "{}")
            # 计算在线状态
            last_hb = row.get("last_heartbeat") or 0
            row["online"] = (now - last_hb) < CONFIG["heartbeat_timeout"]
            row["seconds_since_heartbeat"] = int(now - last_hb)
        return rows

    def update_component_status(self, component_id: str, status: str) -> bool:
        """更新组件状态"""
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE components SET status=? WHERE component_id=?", (status, component_id))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    # --- 内核状态 ---
    def get_state(self, key: str = None) -> Any:
        """获取内核状态"""
        conn = self._get_conn()
        cursor = conn.cursor()
        if key:
            cursor.execute("SELECT * FROM kernel_state WHERE key=?", (key,))
            row = cursor.fetchone()
            conn.close()
            if row:
                d = dict(row)
                if d["value_type"] == "json":
                    d["value"] = json.loads(d["value"])
                elif d["value_type"] == "number":
                    d["value"] = float(d["value"])
                elif d["value_type"] == "bool":
                    d["value"] = d["value"] == "true"
                return d
            return None
        else:
            cursor.execute("SELECT * FROM kernel_state ORDER BY updated_at DESC")
            rows = [dict(row) for row in cursor.fetchall()]
            conn.close()
            result = {}
            for row in rows:
                if row["value_type"] == "json":
                    result[row["key"]] = json.loads(row["value"])
                elif row["value_type"] == "number":
                    result[row["key"]] = float(row["value"])
                elif row["value_type"] == "bool":
                    result[row["key"]] = row["value"] == "true"
                else:
                    result[row["key"]] = row["value"]
            return result

    def set_state(self, key: str, value: Any, updated_by: str = "system") -> bool:
        """设置内核状态"""
        conn = self._get_conn()
        cursor = conn.cursor()
        now = time.time()
        # 推断类型
        if isinstance(value, (dict, list)):
            value_str = json.dumps(value, ensure_ascii=False)
            value_type = "json"
        elif isinstance(value, bool):
            value_str = "true" if value else "false"
            value_type = "bool"
        elif isinstance(value, (int, float)):
            value_str = str(value)
            value_type = "number"
        else:
            value_str = str(value)
            value_type = "string"
        try:
            cursor.execute("""
                INSERT INTO kernel_state (key, value, value_type, updated_by, updated_at, version)
                VALUES (?, ?, ?, ?, ?, 1)
                ON CONFLICT(key) DO UPDATE SET
                    value=excluded.value,
                    value_type=excluded.value_type,
                    updated_by=excluded.updated_by,
                    updated_at=excluded.updated_at,
                    version=kernel_state.version+1
            """, (key, value_str, value_type, updated_by, now))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"设置状态失败: {e}")
            return False
        finally:
            conn.close()

    # --- 事件 ---
    def publish_event(self, event_type: str, source: str, payload: Dict = None,
                      target: str = None, priority: int = 0) -> int:
        """发布事件"""
        conn = self._get_conn()
        cursor = conn.cursor()
        now = time.time()
        try:
            cursor.execute("""
                INSERT INTO events (event_type, source, target, payload, priority, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (event_type, source, target, json.dumps(payload or {}), priority, now))
            event_id = cursor.lastrowid
            conn.commit()
            logger.info(f"事件发布: [{event_type}] from={source} target={target or 'broadcast'} id={event_id}")
            return event_id
        except Exception as e:
            logger.error(f"事件发布失败: {e}")
            return -1
        finally:
            conn.close()

    def subscribe_events(self, component_id: str, event_types: List[str] = None,
                         since_id: int = 0, limit: int = 50) -> List[Dict]:
        """订阅/获取事件（长轮询模式：调用方定期拉取）"""
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            query = "SELECT * FROM events WHERE consumed=0 AND id > ?"
            params = [since_id]
            if event_types:
                placeholders = ",".join(["?"] * len(event_types))
                query += f" AND event_type IN ({placeholders})"
                params.extend(event_types)
            query += " ORDER BY priority DESC, timestamp ASC LIMIT ?"
            params.append(limit)
            cursor.execute(query, params)
            rows = [dict(row) for row in cursor.fetchall()]
            # 标记为已消费
            for row in rows:
                cursor.execute("UPDATE events SET consumed=1, consumed_by=?, consumed_at=? WHERE id=?",
                               (component_id, time.time(), row["id"]))
            conn.commit()
            for row in rows:
                row["payload"] = json.loads(row.get("payload") or "{}")
            return rows
        except Exception as e:
            logger.error(f"事件订阅失败: {e}")
            return []
        finally:
            conn.close()

    # --- 指令 ---
    def dispatch_command(self, command_type: str, target_component: str,
                         payload: Dict = None, created_by: str = "system") -> str:
        """分发指令"""
        conn = self._get_conn()
        cursor = conn.cursor()
        now = time.time()
        command_id = f"CMD-{int(now)}-{hashlib.md5(f'{command_type}{target_component}{now}'.encode()).hexdigest()[:8]}"
        try:
            cursor.execute("""
                INSERT INTO commands (command_id, command_type, target_component, payload, status, created_at, created_by)
                VALUES (?, ?, ?, ?, 'pending', ?, ?)
            """, (command_id, command_type, target_component, json.dumps(payload or {}), now, created_by))
            conn.commit()
            logger.info(f"指令分发: [{command_type}] target={target_component} id={command_id}")
            return command_id
        except Exception as e:
            logger.error(f"指令分发失败: {e}")
            return ""
        finally:
            conn.close()

    def get_pending_commands(self, component_id: str) -> List[Dict]:
        """获取组件的待执行指令"""
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT * FROM commands WHERE target_component=? AND status IN ('pending', 'dispatched')
                ORDER BY created_at ASC
            """, (component_id,))
            rows = [dict(row) for row in cursor.fetchall()]
            # 标记为已分发
            for row in rows:
                if row["status"] == "pending":
                    cursor.execute("UPDATE commands SET status='dispatched', dispatched_at=? WHERE command_id=?",
                                   (time.time(), row["command_id"]))
            conn.commit()
            for row in rows:
                row["payload"] = json.loads(row.get("payload") or "{}")
                row["result"] = json.loads(row.get("result") or "{}") if row.get("result") else {}
            return rows
        except Exception as e:
            logger.error(f"获取指令失败: {e}")
            return []
        finally:
            conn.close()

    def update_command_status(self, command_id: str, status: str, result: Dict = None) -> bool:
        """更新指令状态"""
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            if status in ("completed", "failed"):
                cursor.execute("""
                    UPDATE commands SET status=?, result=?, completed_at=? WHERE command_id=?
                """, (status, json.dumps(result or {}), time.time(), command_id))
            else:
                cursor.execute("UPDATE commands SET status=? WHERE command_id=?", (status, command_id))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"更新指令状态失败: {e}")
            return False
        finally:
            conn.close()

    def get_command(self, command_id: str) -> Optional[Dict]:
        """获取指令详情"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM commands WHERE command_id=?", (command_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            d = dict(row)
            d["payload"] = json.loads(d.get("payload") or "{}")
            d["result"] = json.loads(d.get("result") or "{}") if d.get("result") else {}
            return d
        return None

    # --- 仪表盘 ---
    def get_dashboard(self) -> Dict:
        """获取内核仪表盘数据"""
        conn = self._get_conn()
        cursor = conn.cursor()
        now = time.time()

        # 组件统计
        cursor.execute("SELECT COUNT(*) FROM components")
        total_components = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM components WHERE status='active'")
        active_components = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM components WHERE last_heartbeat > ?", (now - CONFIG["heartbeat_timeout"],))
        online_components = cursor.fetchone()[0]

        # 事件统计
        cursor.execute("SELECT COUNT(*) FROM events WHERE timestamp > ?", (now - 3600,))
        events_1h = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM events WHERE consumed=0")
        pending_events = cursor.fetchone()[0]

        # 指令统计
        cursor.execute("SELECT COUNT(*) FROM commands WHERE status IN ('pending', 'dispatched', 'executing')")
        pending_commands = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM commands WHERE status='completed'")
        completed_commands = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM commands WHERE status='failed'")
        failed_commands = cursor.fetchone()[0]

        # 状态键数量
        cursor.execute("SELECT COUNT(*) FROM kernel_state")
        state_keys = cursor.fetchone()[0]

        conn.close()

        return {
            "timestamp": datetime.now().isoformat(),
            "kernel": {
                "name": "ZONGYUAN-ROOT 元极内核总线",
                "version": "MR-012 v1.0",
                "did": CONFIG["did"],
                "trace_mark": CONFIG["trace_mark"],
                "uptime": "N/A",
            },
            "components": {
                "total": total_components,
                "active": active_components,
                "online": online_components,
                "offline": total_components - online_components,
            },
            "events": {
                "last_1h": events_1h,
                "pending": pending_events,
            },
            "commands": {
                "pending": pending_commands,
                "completed": completed_commands,
                "failed": failed_commands,
            },
            "state": {
                "keys": state_keys,
            },
        }

    # --- 审计 ---
    def _audit(self, action: str, actor: str, detail: Dict, result: str):
        """写入审计日志"""
        try:
            append_jsonl(CONFIG["audit_log"], {
                "timestamp": time.time(),
                "action": action,
                "actor": actor,
                "detail": detail,
                "result": result,
            })
        except Exception:
            pass

    def cleanup_old_data(self):
        """清理过期数据"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cutoff = time.time() - CONFIG["event_retention"]
        cursor.execute("DELETE FROM events WHERE timestamp < ? AND consumed=1", (cutoff,))
        cursor.execute("DELETE FROM heartbeats WHERE timestamp < ?", (time.time() - 86400 * 7,))
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        if deleted > 0:
            logger.info(f"清理过期数据: {deleted}条")


def append_jsonl(filepath: str, data: Any):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "a") as f:
        f.write(json.dumps(data, ensure_ascii=False) + "\n")


# ============================================================
# HTTP API 处理器
# ============================================================
class BusAPIHandler(BaseHTTPRequestHandler):
    """内核总线HTTP API"""

    db: BusDatabase = None  # 类变量，由外部设置

    def log_message(self, format, *args):
        pass  # 静默HTTP日志

    def _send_json(self, data: Any, status: int = 200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> Dict:
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return {}
        body = self.rfile.read(content_length)
        try:
            return json.loads(body)
        except Exception:
            return {}

    # --- 路由 ---
    def do_GET(self):
        path = self.path.split("?")[0]
        try:
            if path == "/api/health":
                self._handle_health()
            elif path == "/api/dashboard":
                self._handle_dashboard()
            elif path == "/api/component/list":
                self._handle_component_list()
            elif path.startswith("/api/component/"):
                component_id = path.split("/")[-1]
                self._handle_component_detail(component_id)
            elif path == "/api/kernel/state":
                self._handle_get_state()
            elif path == "/api/event/subscribe":
                self._handle_subscribe_events()
            elif path == "/api/command/status":
                self._handle_command_status()
            elif path.startswith("/api/command/"):
                command_id = path.split("/")[-1]
                self._handle_command_detail(command_id)
            else:
                self._send_json({"error": "not found", "path": path}, 404)
        except Exception as e:
            logger.error(f"GET {path} 错误: {e}")
            self._send_json({"error": str(e)}, 500)

    def do_POST(self):
        path = self.path.split("?")[0]
        try:
            if path == "/api/component/register":
                self._handle_register()
            elif path == "/api/component/heartbeat":
                self._handle_heartbeat()
            elif path == "/api/kernel/state":
                self._handle_set_state()
            elif path == "/api/event/publish":
                self._handle_publish_event()
            elif path == "/api/command/dispatch":
                self._handle_dispatch_command()
            elif path == "/api/command/complete":
                self._handle_complete_command()
            else:
                self._send_json({"error": "not found", "path": path}, 404)
        except Exception as e:
            logger.error(f"POST {path} 错误: {e}")
            self._send_json({"error": str(e)}, 500)

    # --- 健康检查 ---
    def _handle_health(self):
        self._send_json({
            "status": "ok",
            "service": "mr012-kernel-bus",
            "version": "1.0",
            "did": CONFIG["did"],
            "timestamp": datetime.now().isoformat(),
        })

    # --- 仪表盘 ---
    def _handle_dashboard(self):
        dashboard = self.db.get_dashboard()
        self._send_json(dashboard)

    # --- 组件注册 ---
    def _handle_register(self):
        body = self._read_body()
        required = ["component_id", "component_type", "name"]
        for field in required:
            if field not in body:
                self._send_json({"error": f"缺少必填字段: {field}"}, 400)
                return
        success = self.db.register_component(
            component_id=body["component_id"],
            component_type=body["component_type"],
            name=body["name"],
            description=body.get("description", ""),
            capabilities=body.get("capabilities", []),
            version=body.get("version", ""),
            config=body.get("config", {}),
            metadata=body.get("metadata", {}),
        )
        if success:
            self._send_json({"status": "ok", "message": "组件注册成功", "component_id": body["component_id"]})
        else:
            self._send_json({"error": "组件注册失败"}, 500)

    # --- 心跳 ---
    def _handle_heartbeat(self):
        body = self._read_body()
        if "component_id" not in body:
            self._send_json({"error": "缺少component_id"}, 400)
            return
        success = self.db.heartbeat(
            component_id=body["component_id"],
            status=body.get("status", "active"),
            metrics=body.get("metrics", {}),
        )
        if success:
            self._send_json({"status": "ok", "message": "心跳已接收"})
        else:
            self._send_json({"error": "组件未注册"}, 404)

    # --- 组件列表 ---
    def _handle_component_list(self):
        status_filter = None
        if "?" in self.path:
            query = self.path.split("?")[1]
            for param in query.split("&"):
                if param.startswith("status="):
                    status_filter = param.split("=")[1]
        components = self.db.list_components(status_filter)
        self._send_json({"components": components, "count": len(components)})

    # --- 组件详情 ---
    def _handle_component_detail(self, component_id: str):
        component = self.db.get_component(component_id)
        if component:
            self._send_json(component)
        else:
            self._send_json({"error": "组件不存在"}, 404)

    # --- 获取内核状态 ---
    def _handle_get_state(self):
        key = None
        if "?" in self.path:
            query = self.path.split("?")[1]
            for param in query.split("&"):
                if param.startswith("key="):
                    key = param.split("=", 1)[1]
        state = self.db.get_state(key)
        self._send_json({"state": state})

    # --- 设置内核状态 ---
    def _handle_set_state(self):
        body = self._read_body()
        if "key" not in body or "value" not in body:
            self._send_json({"error": "缺少key或value"}, 400)
            return
        success = self.db.set_state(
            key=body["key"],
            value=body["value"],
            updated_by=body.get("updated_by", "api"),
        )
        if success:
            self._send_json({"status": "ok", "message": "状态已更新"})
        else:
            self._send_json({"error": "状态更新失败"}, 500)

    # --- 发布事件 ---
    def _handle_publish_event(self):
        body = self._read_body()
        required = ["event_type", "source"]
        for field in required:
            if field not in body:
                self._send_json({"error": f"缺少必填字段: {field}"}, 400)
                return
        event_id = self.db.publish_event(
            event_type=body["event_type"],
            source=body["source"],
            payload=body.get("payload", {}),
            target=body.get("target"),
            priority=body.get("priority", 0),
        )
        if event_id > 0:
            self._send_json({"status": "ok", "event_id": event_id, "message": "事件已发布"})
        else:
            self._send_json({"error": "事件发布失败"}, 500)

    # --- 订阅事件 ---
    def _handle_subscribe_events(self):
        body = self._read_body()
        if "component_id" not in body:
            self._send_json({"error": "缺少component_id"}, 400)
            return
        events = self.db.subscribe_events(
            component_id=body["component_id"],
            event_types=body.get("event_types"),
            since_id=body.get("since_id", 0),
            limit=body.get("limit", 50),
        )
        self._send_json({"events": events, "count": len(events)})

    # --- 分发指令 ---
    def _handle_dispatch_command(self):
        body = self._read_body()
        required = ["command_type", "target_component"]
        for field in required:
            if field not in body:
                self._send_json({"error": f"缺少必填字段: {field}"}, 400)
                return
        command_id = self.db.dispatch_command(
            command_type=body["command_type"],
            target_component=body["target_component"],
            payload=body.get("payload", {}),
            created_by=body.get("created_by", "api"),
        )
        if command_id:
            self._send_json({"status": "ok", "command_id": command_id, "message": "指令已分发"})
        else:
            self._send_json({"error": "指令分发失败"}, 500)

    # --- 完成指令 ---
    def _handle_complete_command(self):
        body = self._read_body()
        if "command_id" not in body or "status" not in body:
            self._send_json({"error": "缺少command_id或status"}, 400)
            return
        success = self.db.update_command_status(
            command_id=body["command_id"],
            status=body["status"],
            result=body.get("result", {}),
        )
        if success:
            self._send_json({"status": "ok", "message": "指令状态已更新"})
        else:
            self._send_json({"error": "指令不存在"}, 404)

    # --- 指令状态列表 ---
    def _handle_command_status(self):
        # 简化：返回最近的指令
        conn = self.db._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM commands ORDER BY created_at DESC LIMIT 20")
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        for row in rows:
            row["payload"] = json.loads(row.get("payload") or "{}")
            row["result"] = json.loads(row.get("result") or "{}") if row.get("result") else {}
        self._send_json({"commands": rows, "count": len(rows)})

    # --- 指令详情 ---
    def _handle_command_detail(self, command_id: str):
        command = self.db.get_command(command_id)
        if command:
            self._send_json(command)
        else:
            self._send_json({"error": "指令不存在"}, 404)


# ============================================================
# 总线服务
# ============================================================
class KernelBus:
    """元极内核总线服务"""

    def __init__(self):
        self.db = BusDatabase(CONFIG["db_path"])
        self.server = None
        self._running = False

    def start(self):
        """启动总线服务"""
        BusAPIHandler.db = self.db
        self.server = HTTPServer((CONFIG["host"], CONFIG["port"]), BusAPIHandler)
        self._running = True

        # 注册总线自身
        self.db.register_component(
            component_id=CONFIG["node_id"],
            component_type="kernel_bus",
            name="元极内核总线",
            description="ZONGYUAN-ROOT体系中枢神经系统，统一组件通信和状态管理",
            capabilities=["component_registry", "state_bus", "event_bus", "command_dispatcher", "health_monitor"],
            version="1.0",
            config={"port": CONFIG["port"], "db_path": CONFIG["db_path"]},
        )

        # 设置内核初始状态
        self.db.set_state("kernel.bus.status", "running", CONFIG["node_id"])
        self.db.set_state("kernel.bus.started_at", datetime.now().isoformat(), CONFIG["node_id"])
        self.db.set_state("kernel.did", CONFIG["did"], CONFIG["node_id"])
        self.db.set_state("kernel.trace_mark", CONFIG["trace_mark"], CONFIG["node_id"])

        logger.info("")
        logger.info("╔══════════════════════════════════════════════════════╗")
        logger.info("║  MR-012 元极内核总线启动                              ║")
        logger.info(f"║  监听: {CONFIG['host']}:{CONFIG['port']}                                    ║")
        logger.info(f"║  数据库: {CONFIG['db_path']}          ║")
        logger.info("║  能力: 组件注册/状态总线/事件通信/指令分发/健康检查  ║")
        logger.info("╚══════════════════════════════════════════════════════╝")
        logger.info("")

        # 启动定期清理线程
        cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        cleanup_thread.start()

        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        """停止总线服务"""
        self._running = False
        if self.server:
            self.server.shutdown()
        logger.info("内核总线已停止")

    def _cleanup_loop(self):
        """定期清理过期数据"""
        while self._running:
            time.sleep(3600)  # 每小时清理一次
            try:
                self.db.cleanup_old_data()
            except Exception as e:
                logger.error(f"清理失败: {e}")


# ============================================================
# 命令行入口
# ============================================================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="MR-012 元极内核总线")
    parser.add_argument("--serve", action="store_true", help="启动总线服务（默认）")
    parser.add_argument("--status", action="store_true", help="查看总线状态（需要服务运行中）")
    parser.add_argument("--init-db", action="store_true", help="仅初始化数据库")

    args = parser.parse_args()

    if args.init_db:
        db = BusDatabase(CONFIG["db_path"])
        print("数据库初始化完成")
    elif args.status:
        try:
            import requests
            resp = requests.get(f"http://{CONFIG['host']}:{CONFIG['port']}/api/dashboard", timeout=5)
            print(json.dumps(resp.json(), ensure_ascii=False, indent=2))
        except Exception as e:
            print(f"无法连接总线: {e}")
    else:
        bus = KernelBus()
        bus.start()
