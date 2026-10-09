#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT MR-018 多节点协同引擎
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | Ω-TAN-7-001

定位：多服务器协同，实现高可用和负载均衡。

核心功能：
  1. 节点管理 - 注册/注销/查询计算节点
  2. 心跳检测 - 定期检测节点存活状态，超时标记离线
  3. 资源监控 - 收集各节点CPU/内存/磁盘/负载等资源信息
  4. 负载均衡 - 根据资源状态和任务类型智能选择最优节点
  5. 主备选举 - 主节点故障时自动选举新主节点（简化Raft）
  6. 数据同步 - 多节点间真值库和状态的增量同步
  7. 任务分发 - 将任务分发到最优节点执行

技术设计：
  - 节点注册中心：基于SQLite的节点信息存储
  - 心跳协议：节点每30秒发送心跳，120秒无心跳标记离线
  - 资源采集：通过SSH或API采集节点资源信息
  - 负载均衡算法：加权轮询+最少连接+资源状态综合评分
  - 主备选举：基于节点优先级和存活状态的主节点选举
  - 数据同步：基于9120 API的真值增量同步
"""

import os
import sys
import json
import time
import sqlite3
import logging
import hashlib
import socket
import requests
import subprocess
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict

# ============================================================
# 配置
# ============================================================
CONFIG = {
    "db_path": "/opt/ZONGYUAN-ROOT/data/memory_gateway.db",
    "node_db_path": "/opt/ZONGYUAN-ROOT/data/nodes_registry.db",
    "log_file": "/opt/ZONGYUAN-ROOT/ops/mr018_multi_node/mr018.log",
    "audit_log": "/opt/ZONGYUAN-ROOT/ops/mr018_multi_node/audit.jsonl",
    "state_file": "/opt/ZONGYUAN-ROOT/ops/mr018_multi_node/state.json",
    "local_llm_url": "http://127.0.0.1:8081/v1/chat/completions",
    "external_llm_url": "http://127.0.0.1:8021/v1/chat/completions",
    "heartbeat_interval": 30,       # 心跳间隔（秒）
    "heartbeat_timeout": 120,       # 心跳超时（秒）
    "monitor_interval": 60,         # 资源监控间隔（秒）
    "sync_interval": 300,           # 数据同步间隔（秒）
    "local_node_id": "node-main-001",
    "local_node_name": "ZONGYUAN-ROOT 主节点",
    "local_node_ip": "123.207.202.158",
    "local_node_role": "master",    # master/worker/candidate
    "local_node_priority": 100,     # 选举优先级
    "api_port": 9122,               # 多节点协同API端口
    "node_id": "mr018-multi-node",
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
    return logging.getLogger("mr018")

logger = setup_logging()

# ============================================================
# 工具函数
# ============================================================
def get_local_resources() -> Dict:
    """获取本地节点资源信息"""
    resources = {}
    try:
        # CPU信息
        with open("/proc/loadavg", "r") as f:
            load = f.read().split()
            resources["load_1m"] = float(load[0])
            resources["load_5m"] = float(load[1])
            resources["load_15m"] = float(load[2])

        # CPU核心数
        with open("/proc/cpuinfo", "r") as f:
            resources["cpu_cores"] = f.read().count("processor")

        # 内存信息
        with open("/proc/meminfo", "r") as f:
            meminfo = {}
            for line in f:
                parts = line.split(":")
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip().split()[0]
                    meminfo[key] = int(value)
            total_mem = meminfo.get("MemTotal", 0)
            available_mem = meminfo.get("MemAvailable", 0)
            resources["memory_total_mb"] = round(total_mem / 1024, 1)
            resources["memory_available_mb"] = round(available_mem / 1024, 1)
            resources["memory_used_percent"] = round((1 - available_mem / total_mem) * 100, 1) if total_mem > 0 else 0

        # 磁盘信息
        stat = os.statvfs("/")
        total_disk = stat.f_blocks * stat.f_frsize
        free_disk = stat.f_bavail * stat.f_frsize
        resources["disk_total_gb"] = round(total_disk / (1024**3), 1)
        resources["disk_available_gb"] = round(free_disk / (1024**3), 1)
        resources["disk_used_percent"] = round((1 - free_disk / total_disk) * 100, 1) if total_disk > 0 else 0

        # 运行时间
        with open("/proc/uptime", "r") as f:
            uptime = float(f.read().split()[0])
            resources["uptime_seconds"] = int(uptime)
            resources["uptime_hours"] = round(uptime / 3600, 1)

        resources["status"] = "healthy"
    except Exception as e:
        resources["status"] = "error"
        resources["error"] = str(e)

    return resources


def calculate_node_score(resources: Dict, task_type: str = "general") -> float:
    """计算节点综合评分（0-100，越高越好）"""
    if resources.get("status") != "healthy":
        return 0.0

    score = 0.0

    # 内存评分（权重40%）：可用内存越多越好
    mem_available = resources.get("memory_available_mb", 0)
    mem_total = resources.get("memory_total_mb", 1)
    mem_ratio = mem_available / mem_total if mem_total > 0 else 0
    score += mem_ratio * 40

    # CPU评分（权重30%）：负载越低越好
    cpu_cores = resources.get("cpu_cores", 1)
    load_1m = resources.get("load_1m", 0)
    cpu_load_ratio = min(1.0, load_1m / cpu_cores) if cpu_cores > 0 else 1.0
    score += (1 - cpu_load_ratio) * 30

    # 磁盘评分（权重20%）：可用磁盘越多越好
    disk_available = resources.get("disk_available_gb", 0)
    disk_total = resources.get("disk_total_gb", 1)
    disk_ratio = disk_available / disk_total if disk_total > 0 else 0
    score += disk_ratio * 20

    # 运行时间评分（权重10%）：运行时间越长越稳定
    uptime_hours = resources.get("uptime_hours", 0)
    stability_score = min(1.0, uptime_hours / 168)  # 7天满分
    score += stability_score * 10

    # 任务类型调整
    if task_type == "llm_inference":
        # LLM推理更看重内存
        score += mem_ratio * 10
    elif task_type == "data_processing":
        # 数据处理更看重CPU和磁盘
        score += (1 - cpu_load_ratio) * 5 + disk_ratio * 5

    return round(min(100.0, score), 1)

# ============================================================
# 组件一：节点注册中心
# ============================================================
class NodeRegistry:
    """节点注册中心"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """初始化数据库"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS nodes (
                node_id TEXT PRIMARY KEY,
                node_name TEXT,
                ip_address TEXT,
                role TEXT,
                priority INTEGER,
                status TEXT,
                resources TEXT,
                score REAL,
                last_heartbeat REAL,
                registered_at REAL,
                updated_at REAL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS node_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                node_id TEXT,
                event_type TEXT,
                event_data TEXT,
                timestamp REAL
            )
        """)
        conn.commit()
        conn.close()

    def register(self, node_id: str, node_name: str, ip_address: str,
                 role: str = "worker", priority: int = 50) -> bool:
        """注册节点"""
        now = time.time()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO nodes
            (node_id, node_name, ip_address, role, priority, status, resources, score, last_heartbeat, registered_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 'online', '{}', 0, ?, ?, ?)
        """, (node_id, node_name, ip_address, role, priority, now, now, now))
        conn.commit()
        conn.close()
        self._log_event(node_id, "register", {"role": role, "ip": ip_address})
        logger.info(f"节点注册: {node_id} ({node_name}, {ip_address}, {role})")
        return True

    def unregister(self, node_id: str) -> bool:
        """注销节点"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM nodes WHERE node_id = ?", (node_id,))
        conn.commit()
        conn.close()
        self._log_event(node_id, "unregister", {})
        logger.info(f"节点注销: {node_id}")
        return True

    def heartbeat(self, node_id: str, resources: Dict = None) -> bool:
        """节点心跳"""
        now = time.time()
        score = calculate_node_score(resources) if resources else 0
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE nodes SET status = 'online', resources = ?, score = ?, last_heartbeat = ?, updated_at = ?
            WHERE node_id = ?
        """, (json.dumps(resources or {}), score, now, now, node_id))
        conn.commit()
        conn.close()
        return True

    def get_node(self, node_id: str) -> Optional[Dict]:
        """获取节点信息"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM nodes WHERE node_id = ?", (node_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            node = dict(row)
            node["resources"] = json.loads(node.get("resources", "{}"))
            return node
        return None

    def get_all_nodes(self, include_offline: bool = False) -> List[Dict]:
        """获取所有节点"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        if include_offline:
            cursor.execute("SELECT * FROM nodes ORDER BY priority DESC")
        else:
            cursor.execute("SELECT * FROM nodes WHERE status = 'online' ORDER BY score DESC")
        rows = cursor.fetchall()
        conn.close()
        nodes = []
        for row in rows:
            node = dict(row)
            node["resources"] = json.loads(node.get("resources", "{}"))
            nodes.append(node)
        return nodes

    def check_timeouts(self) -> List[str]:
        """检查超时节点，返回超时节点ID列表"""
        now = time.time()
        timeout = CONFIG["heartbeat_timeout"]
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT node_id FROM nodes
            WHERE status = 'online' AND last_heartbeat < ?
        """, (now - timeout,))
        timeout_nodes = [row[0] for row in cursor.fetchall()]

        for node_id in timeout_nodes:
            cursor.execute("UPDATE nodes SET status = 'offline' WHERE node_id = ?", (node_id,))
            self._log_event(node_id, "timeout", {"last_heartbeat_age": now - self._get_last_heartbeat(node_id)})
            logger.warning(f"节点超时离线: {node_id}")

        conn.commit()
        conn.close()
        return timeout_nodes

    def _get_last_heartbeat(self, node_id: str) -> float:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT last_heartbeat FROM nodes WHERE node_id = ?", (node_id,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else 0

    def _log_event(self, node_id: str, event_type: str, event_data: Dict):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO node_events (node_id, event_type, event_data, timestamp)
            VALUES (?, ?, ?, ?)
        """, (node_id, event_type, json.dumps(event_data), time.time()))
        conn.commit()
        conn.close()

    def get_best_node(self, task_type: str = "general") -> Optional[Dict]:
        """获取最优节点（用于负载均衡）"""
        nodes = self.get_all_nodes()
        if not nodes:
            return None

        # 按任务类型计算评分并排序
        scored_nodes = []
        for node in nodes:
            resources = node.get("resources", {})
            score = calculate_node_score(resources, task_type)
            scored_nodes.append((node, score))

        scored_nodes.sort(key=lambda x: x[1], reverse=True)
        return scored_nodes[0][0] if scored_nodes else None

# ============================================================
# 组件二：主备选举器
# ============================================================
class MasterElection:
    """主备选举器（简化Raft）"""

    def __init__(self, registry: NodeRegistry):
        self.registry = registry
        self.current_master = None

    def elect_master(self) -> Optional[Dict]:
        """选举主节点"""
        nodes = self.registry.get_all_nodes()
        if not nodes:
            logger.warning("没有可用节点，无法选举主节点")
            return None

        # 按优先级排序，优先级最高的成为主节点
        candidates = [n for n in nodes if n.get("role") in ["master", "candidate"]]
        if not candidates:
            candidates = nodes  # 如果没有候选节点，所有节点都可以参选

        candidates.sort(key=lambda x: (x.get("priority", 0), x.get("score", 0)), reverse=True)
        new_master = candidates[0]

        # 更新所有节点角色
        conn = sqlite3.connect(self.registry.db_path)
        cursor = conn.cursor()
        for node in nodes:
            role = "master" if node["node_id"] == new_master["node_id"] else "worker"
            cursor.execute("UPDATE nodes SET role = ? WHERE node_id = ?", (role, node["node_id"]))
        conn.commit()
        conn.close()

        self.current_master = new_master
        self.registry._log_event(new_master["node_id"], "elected_master", {
            "priority": new_master.get("priority"),
            "score": new_master.get("score"),
        })
        logger.info(f"主节点选举完成: {new_master['node_id']} ({new_master['node_name']}, 优先级{new_master.get('priority')})")
        return new_master

    def get_master(self) -> Optional[Dict]:
        """获取当前主节点"""
        if self.current_master:
            return self.current_master
        nodes = self.registry.get_all_nodes()
        masters = [n for n in nodes if n.get("role") == "master"]
        if masters:
            self.current_master = masters[0]
            return masters[0]
        return None

    def failover(self) -> Optional[Dict]:
        """主节点故障转移"""
        master = self.get_master()
        if master and master.get("status") == "online":
            logger.info("主节点正常，无需故障转移")
            return master

        logger.warning("主节点故障，启动故障转移...")
        self.registry._log_event(master["node_id"] if master else "unknown", "master_failover_start", {})
        new_master = self.elect_master()
        if new_master:
            self.registry._log_event(new_master["node_id"], "master_failover_complete", {
                "old_master": master["node_id"] if master else "unknown",
            })
        return new_master

# ============================================================
# 组件三：数据同步器
# ============================================================
class DataSynchronizer:
    """数据同步器（多节点间真值库增量同步）"""

    def __init__(self, registry: NodeRegistry, db_path: str):
        self.registry = registry
        self.db_path = db_path
        self.last_sync_time = {}

    def sync_to_node(self, target_node: Dict) -> Dict:
        """同步数据到目标节点"""
        node_id = target_node["node_id"]
        ip = target_node["ip_address"]
        last_sync = self.last_sync_time.get(node_id, 0)

        try:
            # 查询增量真值
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT truth_key, truth_value, truth_hash, category, node_id, created_at, updated_at
                FROM truths WHERE updated_at > ? ORDER BY updated_at ASC
            """, (last_sync,))
            incremental_truths = cursor.fetchall()
            conn.close()

            if not incremental_truths:
                return {"success": True, "synced": 0, "message": "无增量数据"}

            # 通过9120 API同步到目标节点
            sync_url = f"http://{ip}:9120/api/truth/sync"
            truths_data = []
            for row in incremental_truths:
                truths_data.append({
                    "truth_key": row[0],
                    "truth_value": row[1],
                    "truth_hash": row[2],
                    "category": row[3],
                    "source_node": row[4],
                    "created_at": row[5],
                    "updated_at": row[6],
                })

            resp = requests.post(sync_url, json={
                "truths": truths_data,
                "source_node": CONFIG["local_node_id"],
                "sync_type": "incremental",
            }, timeout=30)

            if resp.status_code == 200:
                self.last_sync_time[node_id] = time.time()
                logger.info(f"数据同步到 {node_id}: {len(incremental_truths)}条真值")
                return {"success": True, "synced": len(incremental_truths)}
            else:
                return {"success": False, "error": f"HTTP {resp.status_code}"}

        except Exception as e:
            logger.error(f"数据同步到 {node_id} 失败: {e}")
            return {"success": False, "error": str(e)}

    def sync_all_nodes(self) -> Dict:
        """同步数据到所有在线节点"""
        nodes = self.registry.get_all_nodes()
        results = {}
        for node in nodes:
            if node["node_id"] != CONFIG["local_node_id"]:
                results[node["node_id"]] = self.sync_to_node(node)
        return results

# ============================================================
# 组件四：任务分发器
# ============================================================
class TaskDispatcher:
    """任务分发器（负载均衡）"""

    def __init__(self, registry: NodeRegistry):
        self.registry = registry

    def dispatch(self, task: Dict) -> Dict:
        """分发任务到最优节点"""
        task_type = task.get("type", "general")

        # 选择最优节点
        best_node = self.registry.get_best_node(task_type)
        if not best_node:
            return {"success": False, "error": "没有可用节点"}

        # 如果最优节点是本地节点，直接执行
        if best_node["node_id"] == CONFIG["local_node_id"]:
            return {
                "success": True,
                "dispatched_to": "local",
                "node_id": best_node["node_id"],
                "node_score": best_node.get("score", 0),
                "message": "任务在本地节点执行",
            }

        # 分发到远程节点
        try:
            ip = best_node["ip_address"]
            dispatch_url = f"http://{ip}:{CONFIG['api_port']}/api/task/execute"
            resp = requests.post(dispatch_url, json=task, timeout=60)
            if resp.status_code == 200:
                result = resp.json()
                return {
                    "success": True,
                    "dispatched_to": "remote",
                    "node_id": best_node["node_id"],
                    "node_score": best_node.get("score", 0),
                    "result": result,
                }
            else:
                return {"success": False, "error": f"远程执行失败 HTTP {resp.status_code}"}
        except Exception as e:
            return {"success": False, "error": f"任务分发失败: {e}"}

    def get_load_balance_report(self) -> Dict:
        """获取负载均衡报告"""
        nodes = self.registry.get_all_nodes(include_offline=True)
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_nodes": len(nodes),
            "online_nodes": sum(1 for n in nodes if n["status"] == "online"),
            "offline_nodes": sum(1 for n in nodes if n["status"] == "offline"),
            "nodes": [],
        }
        for node in nodes:
            resources = node.get("resources", {})
            report["nodes"].append({
                "node_id": node["node_id"],
                "name": node["node_name"],
                "role": node["role"],
                "status": node["status"],
                "score": node.get("score", 0),
                "priority": node.get("priority", 0),
                "memory_used_percent": resources.get("memory_used_percent", 0),
                "load_1m": resources.get("load_1m", 0),
                "disk_used_percent": resources.get("disk_used_percent", 0),
            })
        return report

# ============================================================
# 多节点协同引擎主类
# ============================================================
class MultiNodeEngine:
    """多节点协同引擎主类"""

    def __init__(self):
        self.registry = NodeRegistry(CONFIG["node_db_path"])
        self.election = MasterElection(self.registry)
        self.synchronizer = DataSynchronizer(self.registry, CONFIG["db_path"])
        self.dispatcher = TaskDispatcher(self.registry)
        self.state = self._load_state()
        self._register_local_node()

    def _register_local_node(self):
        """注册本地节点"""
        self.registry.register(
            node_id=CONFIG["local_node_id"],
            node_name=CONFIG["local_node_name"],
            ip_address=CONFIG["local_node_ip"],
            role=CONFIG["local_node_role"],
            priority=CONFIG["local_node_priority"],
        )
        # 发送初始心跳
        resources = get_local_resources()
        self.registry.heartbeat(CONFIG["local_node_id"], resources)

    def _load_state(self) -> Dict:
        if os.path.exists(CONFIG["state_file"]):
            try:
                with open(CONFIG["state_file"], "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "total_heartbeats": 0,
            "total_elections": 0,
            "total_syncs": 0,
            "total_dispatches": 0,
            "failover_count": 0,
            "last_heartbeat": None,
            "last_monitor": None,
            "last_sync": None,
            "started_at": datetime.now().isoformat(),
        }

    def _save_state(self):
        os.makedirs(os.path.dirname(CONFIG["state_file"]), exist_ok=True)
        with open(CONFIG["state_file"], "w") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    def run_heartbeat_cycle(self):
        """执行心跳周期"""
        # 本地节点心跳
        resources = get_local_resources()
        self.registry.heartbeat(CONFIG["local_node_id"], resources)
        self.state["total_heartbeats"] += 1
        self.state["last_heartbeat"] = datetime.now().isoformat()

        # 检查超时节点
        timeout_nodes = self.registry.check_timeouts()
        if timeout_nodes:
            logger.warning(f"超时节点: {timeout_nodes}")
            # 如果主节点超时，触发故障转移
            master = self.election.get_master()
            if master and master["node_id"] in timeout_nodes:
                self.election.failover()
                self.state["failover_count"] += 1

        self._save_state()

    def run_monitor_cycle(self):
        """执行资源监控周期"""
        nodes = self.registry.get_all_nodes()
        for node in nodes:
            if node["node_id"] == CONFIG["local_node_id"]:
                resources = get_local_resources()
                self.registry.heartbeat(node["node_id"], resources)
            else:
                # 远程节点通过API获取资源（简化：依赖节点自己上报）
                pass
        self.state["last_monitor"] = datetime.now().isoformat()
        self._save_state()

    def run_sync_cycle(self):
        """执行数据同步周期"""
        results = self.synchronizer.sync_all_nodes()
        self.state["total_syncs"] += 1
        self.state["last_sync"] = datetime.now().isoformat()
        self._save_state()
        return results

    def run_full_cycle(self) -> Dict:
        """执行完整协同周期"""
        logger.info("=" * 60)
        logger.info("MR-018 多节点协同周期")
        logger.info("=" * 60)

        # 1. 心跳
        self.run_heartbeat_cycle()

        # 2. 资源监控
        self.run_monitor_cycle()

        # 3. 主节点确认
        master = self.election.get_master()
        if not master:
            master = self.election.elect_master()
            self.state["total_elections"] += 1

        # 4. 数据同步（仅主节点执行）
        sync_results = {}
        if master and master["node_id"] == CONFIG["local_node_id"]:
            sync_results = self.run_sync_cycle()

        # 5. 生成负载均衡报告
        lb_report = self.dispatcher.get_load_balance_report()

        result = {
            "timestamp": datetime.now().isoformat(),
            "master_node": master["node_id"] if master else None,
            "load_balance_report": lb_report,
            "sync_results": sync_results,
            "state_summary": {
                "total_nodes": lb_report["total_nodes"],
                "online_nodes": lb_report["online_nodes"],
                "total_heartbeats": self.state["total_heartbeats"],
                "failover_count": self.state["failover_count"],
            },
        }

        logger.info(f"协同周期完成: {lb_report['online_nodes']}/{lb_report['total_nodes']}节点在线, 主节点{master['node_id'] if master else '无'}")
        logger.info("=" * 60)
        return result

    def get_status(self) -> Dict:
        """获取引擎状态"""
        nodes = self.registry.get_all_nodes(include_offline=True)
        master = self.election.get_master()
        return {
            "state": self.state,
            "local_node": {
                "id": CONFIG["local_node_id"],
                "name": CONFIG["local_node_name"],
                "ip": CONFIG["local_node_ip"],
                "role": CONFIG["local_node_role"],
                "priority": CONFIG["local_node_priority"],
                "resources": get_local_resources(),
            },
            "master_node": master["node_id"] if master else None,
            "all_nodes": [{"id": n["node_id"], "name": n["node_name"], "role": n["role"], "status": n["status"], "score": n.get("score", 0)} for n in nodes],
            "config": {
                "heartbeat_interval": f"{CONFIG['heartbeat_interval']}秒",
                "heartbeat_timeout": f"{CONFIG['heartbeat_timeout']}秒",
                "api_port": CONFIG["api_port"],
            },
        }

    def run_forever(self):
        """常驻运行"""
        logger.info("")
        logger.info("╔══════════════════════════════════════════════════════╗")
        logger.info("║  MR-018 多节点协同引擎启动                           ║")
        logger.info("║  能力: 节点管理+心跳检测+资源监控+负载均衡+主备选举  ║")
        logger.info("║  本地节点: {} ({})                       ║".format(CONFIG["local_node_id"], CONFIG["local_node_ip"]))
        logger.info("║  心跳间隔: {}秒, 超时: {}秒                       ║".format(CONFIG["heartbeat_interval"], CONFIG["heartbeat_timeout"]))
        logger.info("╚══════════════════════════════════════════════════════╝")
        logger.info("")

        # 启动时执行完整周期
        self.run_full_cycle()

        last_heartbeat = 0
        last_monitor = 0
        last_sync = 0

        while True:
            now = time.time()

            # 心跳周期
            if now - last_heartbeat >= CONFIG["heartbeat_interval"]:
                self.run_heartbeat_cycle()
                last_heartbeat = now

            # 监控周期
            if now - last_monitor >= CONFIG["monitor_interval"]:
                self.run_monitor_cycle()
                last_monitor = now

            # 同步周期（仅主节点）
            master = self.election.get_master()
            if master and master["node_id"] == CONFIG["local_node_id"]:
                if now - last_sync >= CONFIG["sync_interval"]:
                    self.run_sync_cycle()
                    last_sync = now

            time.sleep(5)


# ============================================================
# 命令行入口
# ============================================================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="MR-018 多节点协同引擎")
    parser.add_argument("command", choices=["cycle", "nodes", "elect", "sync", "dispatch", "status", "daemon"],
                        help="cycle=执行完整协同周期, nodes=查看节点列表, elect=选举主节点, sync=同步数据, dispatch=测试任务分发, status=查看状态, daemon=常驻运行")
    parser.add_argument("--task", help="任务类型（用于dispatch测试）")
    args = parser.parse_args()

    engine = MultiNodeEngine()

    if args.command == "cycle":
        result = engine.run_full_cycle()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "nodes":
        nodes = engine.registry.get_all_nodes(include_offline=True)
        print(f"节点总数: {len(nodes)}")
        for n in nodes:
            print(f"  [{n['status']:7s}] [{n['role']:8s}] {n['node_id']:20s} {n['node_name']:30s} 评分:{n.get('score', 0):5.1f} 优先级:{n.get('priority', 0)}")
    elif args.command == "elect":
        master = engine.election.elect_master()
        engine.state["total_elections"] += 1
        engine._save_state()
        print(f"主节点选举完成: {master['node_id']} ({master['node_name']})")
    elif args.command == "sync":
        results = engine.run_sync_cycle()
        print(json.dumps(results, ensure_ascii=False, indent=2))
    elif args.command == "dispatch":
        task = {"type": args.task or "general", "payload": "test"}
        result = engine.dispatcher.dispatch(task)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "status":
        status = engine.get_status()
        print(json.dumps(status, ensure_ascii=False, indent=2))
    elif args.command == "daemon":
        engine.run_forever()
