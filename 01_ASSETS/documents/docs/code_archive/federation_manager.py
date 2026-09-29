#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
元极恒一｜多实例联邦框架
功能：多容器实例间状态同步，单容器重启不影响全局服务
组件：联邦配置 + 同步协议 + 状态同步 + 故障转移
溯源：Ω₀⊂⊙∞⊂Ω｜DID-BR-000002
"""

import sys
import json
import time
import hashlib
import socket
import sqlite3
from pathlib import Path
from datetime import datetime

# 统一数据库连接模块（自动设置PRAGMA: WAL/NORMAL/20MB缓存）
sys.path.insert(0, str(Path(__file__).parent.parent))
from comm.db_utils import get_connection

BASE_DIR = Path(__file__).parent.parent.resolve()
FEDERATION_CONFIG = BASE_DIR / "config" / "federation_config.json"
FEDERATION_STATE = BASE_DIR / "db" / "federation_state.db"

DID = "DID-BR-000002"
TRACE = "Ω₀⊂⊙∞⊂Ω"


class FederationConfig:
    """联邦配置管理"""

    DEFAULT_CONFIG = {
        "federation_id": "yuanjihengyi-federation-v1",
        "local_instance": {
            "instance_id": "local-001",
            "role": "master",  # master/slave/standalone
            "hostname": socket.gethostname(),
            "endpoint": "http://localhost:8090",
            "priority": 100,
            "status": "active",
        },
        "peer_instances": [],
        "sync_config": {
            "enabled": False,  # 单实例默认关闭，多实例时开启
            "interval_seconds": 30,
            "sync_items": ["merkle_ledger", "operator_results", "audit_log", "node_state"],
            "conflict_resolution": "priority_wins",  # priority_wins/timestamp_wins/manual
            "max_retry": 3,
            "timeout_seconds": 10,
        },
        "failover_config": {
            "enabled": False,
            "heartbeat_timeout": 60,
            "auto_promote": True,
        },
        "did": DID,
        "trace": TRACE,
    }

    def __init__(self):
        self.config = self._load_or_create()

    def _load_or_create(self):
        if FEDERATION_CONFIG.exists():
            try:
                with open(FEDERATION_CONFIG, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        # 创建默认配置
        FEDERATION_CONFIG.parent.mkdir(parents=True, exist_ok=True)
        with open(FEDERATION_CONFIG, "w", encoding="utf-8") as f:
            json.dump(self.DEFAULT_CONFIG, f, ensure_ascii=False, indent=2)
        return self.DEFAULT_CONFIG

    def get(self, key, default=None):
        return self.config.get(key, default)

    def get_local(self):
        return self.config.get("local_instance", {})

    def get_peers(self):
        return self.config.get("peer_instances", [])

    def is_sync_enabled(self):
        return self.config.get("sync_config", {}).get("enabled", False)

    def add_peer(self, instance_id, endpoint, role="slave", priority=50):
        peers = self.config.get("peer_instances", [])
        # 检查是否已存在
        for p in peers:
            if p.get("instance_id") == instance_id:
                p["endpoint"] = endpoint
                p["role"] = role
                p["priority"] = priority
                self._save()
                return False
        peers.append({
            "instance_id": instance_id,
            "endpoint": endpoint,
            "role": role,
            "priority": priority,
            "status": "unknown",
            "last_heartbeat": None,
        })
        self.config["peer_instances"] = peers
        self._save()
        return True

    def remove_peer(self, instance_id):
        peers = [p for p in self.get_peers() if p.get("instance_id") != instance_id]
        self.config["peer_instances"] = peers
        self._save()

    def enable_sync(self, enabled=True):
        self.config["sync_config"]["enabled"] = enabled
        self._save()

    def _save(self):
        with open(FEDERATION_CONFIG, "w", encoding="utf-8") as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)


class FederationState:
    """联邦状态存储（SQLite）"""

    def __init__(self):
        FEDERATION_STATE.parent.mkdir(parents=True, exist_ok=True)
        self.conn = get_connection(str(FEDERATION_STATE))
        self._init_tables()

    def _init_tables(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS sync_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sync_id TEXT UNIQUE,
                peer_id TEXT,
                sync_type TEXT,
                status TEXT,
                items_synced INTEGER,
                conflict_count INTEGER,
                duration_ms REAL,
                timestamp REAL,
                details TEXT
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS peer_heartbeat (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                peer_id TEXT UNIQUE,
                endpoint TEXT,
                status TEXT,
                last_heartbeat REAL,
                latency_ms REAL,
                instance_info TEXT
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS failover_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT UNIQUE,
                event_type TEXT,
                from_instance TEXT,
                to_instance TEXT,
                reason TEXT,
                timestamp REAL,
                result TEXT
            )
        """)
        self.conn.commit()

    def log_sync(self, sync_id, peer_id, sync_type, status, items_synced, conflict_count, duration_ms, details=""):
        try:
            self.conn.execute("""
                INSERT OR REPLACE INTO sync_log
                (sync_id, peer_id, sync_type, status, items_synced, conflict_count, duration_ms, timestamp, details)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (sync_id, peer_id, sync_type, status, items_synced, conflict_count, duration_ms, time.time(), details))
            self.conn.commit()
        except Exception as e:
            print(f"记录同步日志失败: {e}")

    def update_heartbeat(self, peer_id, endpoint, status, latency_ms=0, instance_info=""):
        try:
            self.conn.execute("""
                INSERT OR REPLACE INTO peer_heartbeat
                (peer_id, endpoint, status, last_heartbeat, latency_ms, instance_info)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (peer_id, endpoint, status, time.time(), latency_ms, instance_info))
            self.conn.commit()
        except Exception as e:
            print(f"更新心跳失败: {e}")

    def get_peer_status(self, peer_id):
        cursor = self.conn.execute("SELECT * FROM peer_heartbeat WHERE peer_id=?", (peer_id,))
        row = cursor.fetchone()
        if row:
            return {
                "peer_id": row[1],
                "endpoint": row[2],
                "status": row[3],
                "last_heartbeat": row[4],
                "latency_ms": row[5],
            }
        return None

    def get_sync_stats(self):
        cursor = self.conn.execute("""
            SELECT
                COUNT(*) as total_syncs,
                SUM(CASE WHEN status='success' THEN 1 ELSE 0 END) as success_count,
                SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) as failed_count,
                AVG(duration_ms) as avg_duration,
                SUM(items_synced) as total_items_synced
            FROM sync_log
        """)
        row = cursor.fetchone()
        return {
            "total_syncs": row[0] or 0,
            "success_count": row[1] or 0,
            "failed_count": row[2] or 0,
            "avg_duration_ms": round(row[3] or 0, 2),
            "total_items_synced": row[4] or 0,
        }

    def close(self):
        self.conn.close()


class FederationProtocol:
    """联邦同步协议"""

    @staticmethod
    def create_sync_message(sync_type, payload, source_id, target_id):
        """创建同步消息"""
        return {
            "protocol_version": "1.0",
            "message_id": f"SYNC-{int(time.time())}-{hashlib.md5(str(time.time()).encode()).hexdigest()[:8]}",
            "message_type": "sync",
            "sync_type": sync_type,
            "source_instance": source_id,
            "target_instance": target_id,
            "timestamp": time.time(),
            "payload": payload,
            "checksum": hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest(),
            "did": DID,
            "trace": TRACE,
        }

    @staticmethod
    def create_heartbeat_message(instance_info):
        """创建心跳消息"""
        return {
            "protocol_version": "1.0",
            "message_id": f"HB-{int(time.time())}-{hashlib.md5(str(time.time()).encode()).hexdigest()[:8]}",
            "message_type": "heartbeat",
            "instance_info": instance_info,
            "timestamp": time.time(),
            "did": DID,
            "trace": TRACE,
        }

    @staticmethod
    def verify_checksum(message):
        """验证消息校验和"""
        payload = message.get("payload", {})
        expected_checksum = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        return message.get("checksum") == expected_checksum

    @staticmethod
    def resolve_conflict(local_item, remote_item, strategy="priority_wins", local_priority=100, remote_priority=50):
        """冲突解决"""
        if strategy == "priority_wins":
            return local_item if local_priority >= remote_priority else remote_item
        elif strategy == "timestamp_wins":
            local_ts = local_item.get("timestamp", 0)
            remote_ts = remote_item.get("timestamp", 0)
            return local_item if local_ts >= remote_ts else remote_item
        else:
            return local_item  # 默认本地优先


class FederationManager:
    """联邦管理器（主入口）"""

    def __init__(self):
        self.config = FederationConfig()
        self.state = FederationState()

    def get_status(self):
        """获取联邦状态"""
        local = self.config.get_local()
        peers = self.config.get_peers()
        sync_stats = self.state.get_sync_stats()

        return {
            "federation_id": self.config.get("federation_id"),
            "sync_enabled": self.config.is_sync_enabled(),
            "local_instance": local,
            "peer_count": len(peers),
            "peers": peers,
            "sync_stats": sync_stats,
            "failover_enabled": self.config.get("failover_config", {}).get("enabled", False),
            "did": DID,
            "trace": TRACE,
        }

    def add_peer(self, instance_id, endpoint, role="slave", priority=50):
        """添加对等节点"""
        return self.config.add_peer(instance_id, endpoint, role, priority)

    def remove_peer(self, instance_id):
        """移除对等节点"""
        self.config.remove_peer(instance_id)

    def enable_sync(self, enabled=True):
        """启用/禁用同步"""
        self.config.enable_sync(enabled)

    def sync_with_peer(self, peer_id, sync_type="full"):
        """与对等节点同步（框架实现，实际同步需网络连通）"""
        peer = next((p for p in self.config.get_peers() if p.get("instance_id") == peer_id), None)
        if not peer:
            return {"status": "error", "error": f"对等节点 {peer_id} 不存在"}

        if not self.config.is_sync_enabled():
            return {"status": "error", "error": "联邦同步未启用"}

        sync_id = f"SYNC-{int(time.time())}-{hashlib.md5(peer_id.encode()).hexdigest()[:8]}"
        start_time = time.time()

        # 框架实现：记录同步尝试（实际网络同步需在多实例环境中实现）
        items_synced = 0
        conflicts = 0
        status = "framework_only"

        duration_ms = round((time.time() - start_time) * 1000, 2)
        self.state.log_sync(sync_id, peer_id, sync_type, status, items_synced, conflicts, duration_ms,
                            "框架实现，实际同步需多实例网络环境")

        return {
            "status": status,
            "sync_id": sync_id,
            "peer_id": peer_id,
            "sync_type": sync_type,
            "items_synced": items_synced,
            "conflicts": conflicts,
            "duration_ms": duration_ms,
            "message": "联邦框架已就绪，实际同步需在多实例网络环境中启用",
        }

    def close(self):
        self.state.close()


def main():
    print("=" * 60)
    print("元极恒一｜多实例联邦框架")
    print("=" * 60)

    manager = FederationManager()
    status = manager.get_status()

    print(f"\n联邦ID: {status['federation_id']}")
    print(f"同步状态: {'已启用' if status['sync_enabled'] else '未启用（单实例模式）'}")
    print(f"本地实例: {status['local_instance']['instance_id']} ({status['local_instance']['role']})")
    print(f"对等节点数: {status['peer_count']}")
    print(f"故障转移: {'已启用' if status['failover_enabled'] else '未启用'}")
    print(f"同步统计: {status['sync_stats']['total_syncs']}次同步")

    print(f"\n配置文件: {FEDERATION_CONFIG}")
    print(f"状态数据库: {FEDERATION_STATE}")

    print("\n" + "=" * 60)
    print("联邦框架已就绪！")
    print("多实例部署时：")
    print("  1. 修改 config/federation_config.json 配置实例ID和角色")
    print("  2. 添加对等节点 endpoint")
    print("  3. 启用同步: sync_config.enabled = true")
    print("  4. 配置故障转移: failover_config.enabled = true")
    print("=" * 60)

    manager.close()


if __name__ == "__main__":
    main()
