#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
云端本地载体自动桥接机制 - 核心引擎
解决云电脑销毁/IP变更后的自动恢复与持续连接问题

核心组件：
  1. GatewayClient    - 9120网关客户端（多地址自动切换）
  2. NodeRegistrar    - 节点注册与心跳保活
  3. TruthSyncManager - 真值同步管理器（增量上传/下载）
  4. RuleSyncManager  - 元法则/规则同步管理器
  5. EnvRecovery      - 环境销毁后自动恢复
  6. ReconnectManager - 断线重连管理器（指数退避）

确权: DID-BR-000002 | 溯源: Ω₀⊂⊙∞⊂Ω
"""

import os
import sys
import json
import time
import uuid
import hashlib
import logging
import logging.handlers
import threading
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import (
    BRIDGE_NAME, BRIDGE_VERSION, BRIDGE_DID, BRIDGE_TRACE_MARK,
    CLOUD_GATEWAY, LOCAL_NODE, HEARTBEAT, TRUTH_SYNC, RULE_SYNC,
    ENVIRONMENT_RECOVERY, SECURITY, LOCAL_STORAGE, SCHEDULER, LOG_CONFIG
)


# ============================================================================
# 日志配置
# ============================================================================

def setup_logging(log_dir: str = None) -> logging.Logger:
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, LOG_CONFIG["log_file"])
    else:
        log_file = LOG_CONFIG["log_file"]

    logger = logging.getLogger("CloudLocalBridge")
    logger.setLevel(getattr(logging, LOG_CONFIG["log_level"]))

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(LOG_CONFIG["log_format"]))
    logger.addHandler(console_handler)

    try:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=LOG_CONFIG["max_log_size_mb"] * 1024 * 1024,
            backupCount=LOG_CONFIG["backup_count"],
            encoding="utf-8"
        )
        file_handler.setFormatter(logging.Formatter(LOG_CONFIG["log_format"]))
        logger.addHandler(file_handler)
    except Exception:
        pass

    return logger


# ============================================================================
# 本地存储管理器
# ============================================================================

class LocalStorage:
    """本地存储管理器（JSON文件持久化）"""

    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)

    def _path(self, filename: str) -> str:
        return os.path.join(self.data_dir, filename)

    def load_json(self, filename: str, default: Any = None) -> Any:
        filepath = self._path(filename)
        try:
            if os.path.exists(filepath):
                with open(filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logging.getLogger("CloudLocalBridge").warning(f"加载 {filename} 失败: {e}")
        return default if default is not None else {}

    def save_json(self, filename: str, data: Any):
        filepath = self._path(filename)
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.getLogger("CloudLocalBridge").warning(f"保存 {filename} 失败: {e}")

    def exists(self, filename: str) -> bool:
        return os.path.exists(self._path(filename))

    def remove(self, filename: str):
        filepath = self._path(filename)
        if os.path.exists(filepath):
            os.remove(filepath)


# ============================================================================
# 9120网关客户端（多地址自动切换）
# ============================================================================

class GatewayClient:
    """9120网关客户端，支持公网/直连/备用多地址自动切换"""

    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.addresses = [
            CLOUD_GATEWAY["public_url"],
            CLOUD_GATEWAY["direct_url"],
            CLOUD_GATEWAY["backup_url"],
        ]
        self.current_index = 0
        self.timeout = CLOUD_GATEWAY["timeout"]
        self._online = False
        self._lock = threading.Lock()

    @property
    def base_url(self) -> str:
        return self.addresses[self.current_index]

    def is_online(self, force_check: bool = False) -> bool:
        if not force_check and self._online:
            return True
        return self._check_online()

    def _check_online(self) -> bool:
        for i in range(len(self.addresses)):
            url = self.addresses[(self.current_index + i) % len(self.addresses)]
            try:
                import urllib.request
                req = urllib.request.Request(f"{url}/api/truths", method="GET")
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    if resp.status == 200:
                        with self._lock:
                            self.current_index = (self.current_index + i) % len(self.addresses)
                            self._online = True
                        self.logger.info(f"网关在线: {url}")
                        return True
            except Exception as e:
                self.logger.debug(f"网关地址 {url} 不可用: {e}")
                continue
        self._online = False
        self.logger.warning("所有网关地址均不可用")
        return False

    def _request(self, method: str, endpoint: str, data: Dict = None) -> Optional[Any]:
        """发送请求，自动切换地址"""
        last_error = None
        for i in range(len(self.addresses)):
            url = self.addresses[(self.current_index + i) % len(self.addresses)]
            try:
                import urllib.request
                full_url = f"{url}{endpoint}"
                if method == "GET":
                    req = urllib.request.Request(full_url, method="GET")
                else:
                    req = urllib.request.Request(
                        full_url,
                        data=json.dumps(data).encode("utf-8") if data else None,
                        headers={"Content-Type": "application/json"},
                        method=method
                    )
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    result = json.loads(resp.read().decode("utf-8"))
                    with self._lock:
                        self.current_index = (self.current_index + i) % len(self.addresses)
                        self._online = True
                    return result
            except Exception as e:
                last_error = e
                self.logger.debug(f"请求 {url}{endpoint} 失败: {e}")
                continue
        self._online = False
        self.logger.warning(f"请求 {endpoint} 失败（所有地址）: {last_error}")
        return None

    def list_truths(self) -> List[str]:
        result = self._request("GET", "/api/truths")
        if result:
            return result if isinstance(result, list) else result.get("truths", [])
        return []

    def get_truth(self, key: str) -> Optional[Dict]:
        from urllib.parse import quote
        encoded_key = quote(key, safe='')
        result = self._request("GET", f"/api/truth/{encoded_key}")
        return result

    def upsert_truth(self, key: str, value: Any, node_id: str = "", category: str = "bridge") -> bool:
        result = self._request("POST", "/api/truth/upsert", {
            "key": key,
            "value": value if isinstance(value, str) else json.dumps(value, ensure_ascii=False),
            "node_id": node_id,
            "category": category
        })
        if result:
            return result.get("status") == "ok" or result.get("success") is True
        return False

    def register_node(self, node_info: Dict) -> bool:
        """注册节点到云端"""
        result = self._request("POST", "/api/node/register", {
            **node_info,
            "DID": BRIDGE_DID,
            "ROOT_OMEGA": "Ω-TAN-7-001",
        })
        return result is not None

    def send_heartbeat(self, node_id: str, status: Dict) -> bool:
        """发送心跳"""
        result = self._request("POST", "/api/node/heartbeat", {
            "node_id": node_id,
            "status": status,
            "timestamp": time.time(),
            "DID": BRIDGE_DID,
        })
        return result is not None


# ============================================================================
# 节点注册与心跳管理器
# ============================================================================

class NodeManager:
    """节点注册与心跳保活管理器"""

    def __init__(self, gateway: GatewayClient, storage: LocalStorage, logger: logging.Logger):
        self.gateway = gateway
        self.storage = storage
        self.logger = logger
        self.node_id = self._load_or_create_node_id()
        self.registered = False
        self.heartbeat_thread = None
        self.running = False
        self.consecutive_failures = 0

    def _load_or_create_node_id(self) -> str:
        """加载或创建节点ID"""
        state = self.storage.load_json(LOCAL_STORAGE["node_state_file"], {})
        node_id = state.get("node_id", "")
        if not node_id:
            node_id = f"bridge-{uuid.uuid4().hex[:12]}"
            state["node_id"] = node_id
            state["created_at"] = time.time()
            self.storage.save_json(LOCAL_STORAGE["node_state_file"], state)
            self.logger.info(f"创建新节点ID: {node_id}")
        else:
            self.logger.info(f"加载已有节点ID: {node_id}")
        return node_id

    def register(self) -> bool:
        """注册节点到云端"""
        if not self.gateway.is_online():
            self.logger.warning("网关不在线，跳过注册")
            return False

        node_info = {
            "node_id": self.node_id,
            "node_type": LOCAL_NODE["node_type"],
            "node_name": LOCAL_NODE["node_name"],
            "node_description": LOCAL_NODE["node_description"],
            "capabilities": LOCAL_NODE["capabilities"],
            "resource_limits": LOCAL_NODE["resource_limits"],
            "bridge_version": BRIDGE_VERSION,
            "registered_at": time.time(),
            "platform": sys.platform,
            "python_version": sys.version,
        }

        success = self.gateway.register_node(node_info)
        if success:
            self.registered = True
            self.logger.info(f"节点注册成功: {self.node_id}")
            # 保存节点信息到本地
            state = self.storage.load_json(LOCAL_STORAGE["node_state_file"], {})
            state.update(node_info)
            state["registered"] = True
            self.storage.save_json(LOCAL_STORAGE["node_state_file"], state)
        else:
            self.logger.warning(f"节点注册失败: {self.node_id}")
        return success

    def start_heartbeat(self):
        """启动心跳线程"""
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            return
        self.running = True
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self.heartbeat_thread.start()
        self.logger.info("心跳线程已启动")

    def stop_heartbeat(self):
        """停止心跳线程"""
        self.running = False
        if self.heartbeat_thread:
            self.heartbeat_thread.join(timeout=5)
        self.logger.info("心跳线程已停止")

    def _heartbeat_loop(self):
        """心跳循环"""
        while self.running:
            try:
                if not self.registered:
                    self.register()
                    time.sleep(HEARTBEAT["interval_seconds"])
                    continue

                status = self._get_node_status()
                success = self.gateway.send_heartbeat(self.node_id, status)

                if success:
                    self.consecutive_failures = 0
                    self.logger.debug(f"心跳成功 (节点: {self.node_id})")
                else:
                    self.consecutive_failures += 1
                    self.logger.warning(f"心跳失败 ({self.consecutive_failures}/{HEARTBEAT['max_failures_before_offline']})")

                    if self.consecutive_failures >= HEARTBEAT["max_failures_before_offline"]:
                        self.logger.error("连续心跳失败，节点判定离线，尝试重新注册...")
                        self.registered = False
                        self.consecutive_failures = 0

            except Exception as e:
                self.logger.error(f"心跳异常: {e}", exc_info=True)

            time.sleep(HEARTBEAT["interval_seconds"])

    def _get_node_status(self) -> Dict:
        """获取节点当前状态"""
        try:
            import psutil
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=1)
            return {
                "online": True,
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_mb": memory.available // (1024 * 1024),
                "uptime_seconds": time.time() - psutil.boot_time(),
                "active_threads": threading.active_count(),
            }
        except ImportError:
            return {
                "online": True,
                "cpu_percent": 0,
                "memory_percent": 0,
                "active_threads": threading.active_count(),
            }


# ============================================================================
# 真值同步管理器
# ============================================================================

class TruthSyncManager:
    """真值同步管理器（增量上传/下载）"""

    def __init__(self, gateway: GatewayClient, storage: LocalStorage,
                 node_id: str, logger: logging.Logger):
        self.gateway = gateway
        self.storage = storage
        self.node_id = node_id
        self.logger = logger
        self.upload_thread = None
        self.download_thread = None
        self.running = False
        self.local_truth_queue = deque()  # 待上传的本地真值队列

    def queue_truth(self, key: str, value: Any, category: str = "bridge"):
        """将本地真值加入上传队列"""
        self.local_truth_queue.append({
            "key": key,
            "value": value,
            "category": category,
            "queued_at": time.time(),
        })
        self.logger.debug(f"真值已加入上传队列: {key} (队列长度: {len(self.local_truth_queue)})")

    def start_sync(self):
        """启动同步线程"""
        self.running = True
        self.upload_thread = threading.Thread(target=self._upload_loop, daemon=True)
        self.download_thread = threading.Thread(target=self._download_loop, daemon=True)
        self.upload_thread.start()
        self.download_thread.start()
        self.logger.info("真值同步线程已启动")

    def stop_sync(self):
        """停止同步线程"""
        self.running = False
        for t in [self.upload_thread, self.download_thread]:
            if t:
                t.join(timeout=5)
        self.logger.info("真值同步线程已停止")

    def _upload_loop(self):
        """上传循环（本地→云端）"""
        while self.running:
            try:
                if not self.gateway.is_online():
                    time.sleep(10)
                    continue

                uploaded = 0
                while self.local_truth_queue and uploaded < TRUTH_SYNC["max_batch_size"]:
                    item = self.local_truth_queue.popleft()
                    success = self.gateway.upsert_truth(
                        key=item["key"],
                        value=item["value"],
                        node_id=self.node_id,
                        category=item["category"]
                    )
                    if success:
                        uploaded += 1
                    else:
                        # 失败则放回队列头部
                        self.local_truth_queue.appendleft(item)
                        break

                if uploaded > 0:
                    self.logger.info(f"真值上传完成: {uploaded} 条 (队列剩余: {len(self.local_truth_queue)})")

            except Exception as e:
                self.logger.error(f"上传循环异常: {e}", exc_info=True)

            time.sleep(TRUTH_SYNC["upload_interval_seconds"])

    def _download_loop(self):
        """下载循环（云端→本地）"""
        while self.running:
            try:
                if not self.gateway.is_online():
                    time.sleep(10)
                    continue

                # 获取云端真值列表
                cloud_truths = self.gateway.list_truths()
                if not cloud_truths:
                    time.sleep(TRUTH_SYNC["download_interval_seconds"])
                    continue

                # 加载本地缓存
                local_cache = self.storage.load_json(LOCAL_STORAGE["truth_cache_file"], {})
                local_keys = set(local_cache.keys())

                # 找出新增的真值
                new_keys = [k for k in cloud_truths if k not in local_keys]

                # 过滤黑名单
                if TRUTH_SYNC["category_blacklist"]:
                    new_keys = [k for k in new_keys
                                if not any(k.startswith(p) for p in TRUTH_SYNC["category_blacklist"])]

                if new_keys:
                    self.logger.info(f"发现 {len(new_keys)} 条新增云端真值，开始拉取...")
                    downloaded = 0
                    for key in new_keys[:TRUTH_SYNC["max_batch_size"]]:
                        truth = self.gateway.get_truth(key)
                        if truth:
                            local_cache[key] = {
                                "value": truth.get("truth", {}).get("value", "") or truth.get("value", ""),
                                "downloaded_at": time.time(),
                                "source": "cloud",
                            }
                            downloaded += 1

                    # 限制缓存大小
                    if len(local_cache) > LOCAL_STORAGE["max_cache_size"]:
                        # 删除最旧的
                        sorted_keys = sorted(local_cache.keys(),
                                            key=lambda k: local_cache[k].get("downloaded_at", 0))
                        for old_key in sorted_keys[:len(local_cache) - LOCAL_STORAGE["max_cache_size"]]:
                            del local_cache[old_key]

                    self.storage.save_json(LOCAL_STORAGE["truth_cache_file"], local_cache)
                    self.logger.info(f"真值下载完成: {downloaded} 条 (本地缓存: {len(local_cache)} 条)")

            except Exception as e:
                self.logger.error(f"下载循环异常: {e}", exc_info=True)

            time.sleep(TRUTH_SYNC["download_interval_seconds"])

    def get_cached_truth(self, key: str) -> Optional[Any]:
        """获取本地缓存的真值"""
        local_cache = self.storage.load_json(LOCAL_STORAGE["truth_cache_file"], {})
        return local_cache.get(key, {}).get("value")


# ============================================================================
# 元法则/规则同步管理器
# ============================================================================

class RuleSyncManager:
    """元法则/规则同步管理器"""

    def __init__(self, gateway: GatewayClient, storage: LocalStorage, logger: logging.Logger):
        self.gateway = gateway
        self.storage = storage
        self.logger = logger
        self.rules_thread = None
        self.running = False
        self.applied_rules = set()

    def start(self):
        """启动规则同步线程"""
        self.running = True
        self.rules_thread = threading.Thread(target=self._rule_sync_loop, daemon=True)
        self.rules_thread.start()
        self.logger.info("规则同步线程已启动")

    def stop(self):
        """停止规则同步线程"""
        self.running = False
        if self.rules_thread:
            self.rules_thread.join(timeout=5)
        self.logger.info("规则同步线程已停止")

    def _rule_sync_loop(self):
        """规则同步循环"""
        while self.running:
            try:
                if not self.gateway.is_online():
                    time.sleep(30)
                    continue

                # 获取云端真值列表
                cloud_truths = self.gateway.list_truths()

                # 筛选规则类真值
                rule_keys = [k for k in cloud_truths
                            if any(k.startswith(p) for p in RULE_SYNC["rule_prefixes"])]

                new_rules = [k for k in rule_keys if k not in self.applied_rules]

                if new_rules:
                    self.logger.info(f"发现 {len(new_rules)} 条新规则，开始拉取...")
                    for key in new_rules[:20]:  # 每次最多处理20条
                        rule = self.gateway.get_truth(key)
                        if rule and RULE_SYNC["auto_apply"]:
                            self._apply_rule(key, rule)
                            self.applied_rules.add(key)

                    self.logger.info(f"规则同步完成: {len(new_rules)} 条新规则已应用")

            except Exception as e:
                self.logger.error(f"规则同步异常: {e}", exc_info=True)

            time.sleep(RULE_SYNC["pull_interval_seconds"])

    def _apply_rule(self, key: str, rule: Dict):
        """应用规则到本地环境"""
        try:
            value = rule.get("truth", {}).get("value", "") or rule.get("value", "")
            if isinstance(value, str):
                try:
                    value = json.loads(value)
                except Exception:
                    pass

            # 保存到本地规则库
            rules_file = "applied_rules.json"
            rules = self.storage.load_json(rules_file, {})
            rules[key] = {
                "value": value,
                "applied_at": time.time(),
            }
            self.storage.save_json(rules_file, rules)

            self.logger.debug(f"规则已应用: {key}")

        except Exception as e:
            self.logger.warning(f"应用规则失败 {key}: {e}")

    def get_applied_rules(self) -> Dict:
        """获取已应用的规则"""
        return self.storage.load_json("applied_rules.json", {})


# ============================================================================
# 环境恢复管理器
# ============================================================================

class EnvRecoveryManager:
    """环境销毁后自动恢复管理器"""

    def __init__(self, gateway: GatewayClient, storage: LocalStorage, logger: logging.Logger):
        self.gateway = gateway
        self.storage = storage
        self.logger = logger

    def check_and_recover(self) -> bool:
        """检查并执行环境恢复"""
        marker_file = ENVIRONMENT_RECOVERY["recovery_marker_file"]

        # 检查是否已经初始化过
        if self.storage.exists(marker_file):
            self.logger.info("环境已初始化，跳过恢复")
            return True

        self.logger.info("检测到新环境，开始从云端恢复...")

        if not self.gateway.is_online(force_check=True):
            self.logger.error("云端不可用，无法恢复")
            return False

        try:
            # 1. 恢复节点ID
            self._recover_node_id()

            # 2. 恢复自定义配置
            self._recover_configs()

            # 3. 恢复书签/常用链接
            self._recover_bookmarks()

            # 4. 恢复代码片段
            self._recover_snippets()

            # 5. 标记恢复完成
            self.storage.save_json(marker_file, {
                "recovered_at": time.time(),
                "recovered_from": "cloud",
                "bridge_version": BRIDGE_VERSION,
            })

            self.logger.info("环境恢复完成 ✓")
            return True

        except Exception as e:
            self.logger.error(f"环境恢复失败: {e}", exc_info=True)
            return False

    def _recover_node_id(self):
        """从云端恢复节点ID"""
        # 尝试从云端获取最近活跃的节点
        try:
            # 这里简化处理：如果本地没有node_id，创建新的并注册
            state = self.storage.load_json(LOCAL_STORAGE["node_state_file"], {})
            if not state.get("node_id"):
                # 尝试从云端节点列表中查找（如果有这个API）
                # 否则创建新节点
                self.logger.info("创建新节点ID（云端无历史节点记录）")
        except Exception as e:
            self.logger.warning(f"恢复节点ID失败: {e}")

    def _recover_configs(self):
        """恢复自定义配置"""
        try:
            config_truth = self.gateway.get_truth("BRIDGE.CONFIG.CUSTOM")
            if config_truth:
                value = config_truth.get("truth", {}).get("value", "")
                if value:
                    self.storage.save_json("custom_configs.json", json.loads(value) if isinstance(value, str) else value)
                    self.logger.info("自定义配置已恢复")
        except Exception as e:
            self.logger.warning(f"恢复自定义配置失败: {e}")

    def _recover_bookmarks(self):
        """恢复书签/常用链接"""
        try:
            bookmarks_truth = self.gateway.get_truth("BRIDGE.BOOKMARKS")
            if bookmarks_truth:
                value = bookmarks_truth.get("truth", {}).get("value", "")
                if value:
                    self.storage.save_json("bookmarks.json", json.loads(value) if isinstance(value, str) else value)
                    self.logger.info("书签已恢复")
        except Exception as e:
            self.logger.warning(f"恢复书签失败: {e}")

    def _recover_snippets(self):
        """恢复代码片段"""
        try:
            snippets_truth = self.gateway.get_truth("BRIDGE.SNIPPETS")
            if snippets_truth:
                value = snippets_truth.get("truth", {}).get("value", "")
                if value:
                    self.storage.save_json("snippets.json", json.loads(value) if isinstance(value, str) else value)
                    self.logger.info("代码片段已恢复")
        except Exception as e:
            self.logger.warning(f"恢复代码片段失败: {e}")

    def backup_to_cloud(self):
        """将本地配置备份到云端"""
        try:
            # 备份自定义配置
            custom_configs = self.storage.load_json("custom_configs.json", {})
            if custom_configs:
                self.gateway.upsert_truth("BRIDGE.CONFIG.CUSTOM", custom_configs, category="bridge_config")

            # 备份书签
            bookmarks = self.storage.load_json("bookmarks.json", {})
            if bookmarks:
                self.gateway.upsert_truth("BRIDGE.BOOKMARKS", bookmarks, category="bridge_config")

            # 备份代码片段
            snippets = self.storage.load_json("snippets.json", {})
            if snippets:
                self.gateway.upsert_truth("BRIDGE.SNIPPETS", snippets, category="bridge_config")

            self.logger.info("本地配置已备份到云端")
        except Exception as e:
            self.logger.warning(f"备份到云端失败: {e}")


# ============================================================================
# 断线重连管理器
# ============================================================================

class ReconnectManager:
    """断线重连管理器（指数退避）"""

    def __init__(self, gateway: GatewayClient, logger: logging.Logger):
        self.gateway = gateway
        self.logger = logger
        self.backoff_config = HEARTBEAT["reconnect_backoff"]
        self.current_delay = self.backoff_config["initial_delay"]
        self.reconnect_thread = None
        self.running = False
        self.on_reconnect_callback = None

    def start(self, on_reconnect=None):
        """启动重连监控"""
        self.running = True
        self.on_reconnect_callback = on_reconnect
        self.reconnect_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.reconnect_thread.start()
        self.logger.info("断线重连监控已启动")

    def stop(self):
        """停止重连监控"""
        self.running = False
        if self.reconnect_thread:
            self.reconnect_thread.join(timeout=5)
        self.logger.info("断线重连监控已停止")

    def _monitor_loop(self):
        """监控循环"""
        while self.running:
            try:
                if not self.gateway.is_online(force_check=True):
                    self.logger.warning(f"网关离线，{self.current_delay}秒后尝试重连...")
                    time.sleep(self.current_delay)

                    # 指数退避
                    self.current_delay = min(
                        self.current_delay * self.backoff_config["multiplier"],
                        self.backoff_config["max_delay"]
                    )

                    if self.gateway.is_online(force_check=True):
                        self.logger.info("网关重连成功 ✓")
                        self.current_delay = self.backoff_config["initial_delay"]
                        if self.on_reconnect_callback:
                            self.on_reconnect_callback()
                else:
                    # 在线时重置退避
                    self.current_delay = self.backoff_config["initial_delay"]

            except Exception as e:
                self.logger.error(f"重连监控异常: {e}", exc_info=True)

            time.sleep(10)


# ============================================================================
# 桥接主引擎
# ============================================================================

class CloudLocalBridge:
    """云端本地载体自动桥接主引擎"""

    def __init__(self, data_dir: str = None):
        self.name = BRIDGE_NAME
        self.version = BRIDGE_VERSION

        # 初始化存储
        if data_dir is None:
            data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    LOCAL_STORAGE["data_dir"])
        self.storage = LocalStorage(data_dir)

        # 初始化日志
        self.logger = setup_logging(data_dir)

        # 初始化组件
        self.gateway = GatewayClient(self.logger)
        self.node_manager = NodeManager(self.gateway, self.storage, self.logger)
        self.truth_sync = TruthSyncManager(self.gateway, self.storage,
                                            self.node_manager.node_id, self.logger)
        self.rule_sync = RuleSyncManager(self.gateway, self.storage, self.logger)
        self.env_recovery = EnvRecoveryManager(self.gateway, self.storage, self.logger)
        self.reconnect = ReconnectManager(self.gateway, self.logger)

        self._started = False

    def initialize(self) -> bool:
        """初始化桥接"""
        self.logger.info("=" * 60)
        self.logger.info(f"{self.name} v{self.version} 初始化")
        self.logger.info(f"云端本地载体自动桥接机制")
        self.logger.info(f"确权: {BRIDGE_DID} | 溯源: {BRIDGE_TRACE_MARK}")
        self.logger.info("=" * 60)

        # 1. 环境恢复检查
        self.logger.info("\n[1/4] 环境恢复检查...")
        recovered = self.env_recovery.check_and_recover()
        if not recovered:
            self.logger.warning("环境恢复未完成（云端不可用），将以新节点模式运行")

        # 2. 网关连接检查
        self.logger.info("\n[2/4] 云端网关连接检查...")
        if self.gateway.is_online(force_check=True):
            self.logger.info("云端网关: 在线 ✓")
        else:
            self.logger.warning("云端网关: 不在线（将在后台自动重连）")

        # 3. 节点注册
        self.logger.info("\n[3/4] 节点注册...")
        if self.gateway.is_online():
            self.node_manager.register()
        else:
            self.logger.info("网关不在线，跳过注册（将在重连后自动注册）")

        # 4. 启动后台服务
        self.logger.info("\n[4/4] 启动后台服务...")
        self.node_manager.start_heartbeat()
        self.truth_sync.start_sync()
        self.rule_sync.start()
        self.reconnect.start(on_reconnect=self._on_reconnect)

        self._started = True
        self.logger.info("\n" + "=" * 60)
        self.logger.info("桥接初始化完成 ✓")
        self.logger.info(f"  节点ID: {self.node_manager.node_id}")
        self.logger.info(f"  心跳: 每{HEARTBEAT['interval_seconds']}秒")
        self.logger.info(f"  真值上传: 每{TRUTH_SYNC['upload_interval_seconds']}秒")
        self.logger.info(f"  真值下载: 每{TRUTH_SYNC['download_interval_seconds']}秒")
        self.logger.info(f"  规则同步: 每{RULE_SYNC['pull_interval_seconds']}秒")
        self.logger.info("=" * 60)

        return True

    def _on_reconnect(self):
        """重连成功回调"""
        self.logger.info("重连成功，执行恢复操作...")
        # 重新注册节点
        self.node_manager.register()
        # 备份本地配置
        self.env_recovery.backup_to_cloud()

    def shutdown(self):
        """优雅关闭"""
        self.logger.info("正在关闭桥接...")
        # 备份配置
        if self.gateway.is_online():
            self.env_recovery.backup_to_cloud()
        # 停止所有线程
        self.reconnect.stop()
        self.rule_sync.stop()
        self.truth_sync.stop_sync()
        self.node_manager.stop_heartbeat()
        self._started = False
        self.logger.info("桥接已关闭")

    def get_status(self) -> Dict:
        """获取桥接状态"""
        return {
            "bridge": {
                "name": self.name,
                "version": self.version,
                "did": BRIDGE_DID,
                "trace_mark": BRIDGE_TRACE_MARK,
                "started": self._started,
            },
            "node": {
                "node_id": self.node_manager.node_id,
                "node_type": LOCAL_NODE["node_type"],
                "node_name": LOCAL_NODE["node_name"],
                "registered": self.node_manager.registered,
                "consecutive_heartbeat_failures": self.node_manager.consecutive_failures,
            },
            "gateway": {
                "online": self.gateway.is_online(),
                "current_url": self.gateway.base_url,
            },
            "sync": {
                "upload_queue_size": len(self.truth_sync.local_truth_queue),
                "applied_rules_count": len(self.rule_sync.applied_rules),
            },
            "storage": {
                "data_dir": self.storage.data_dir,
            },
        }

    def queue_truth(self, key: str, value: Any, category: str = "bridge"):
        """快捷方法：将真值加入上传队列"""
        self.truth_sync.queue_truth(key, value, category)

    def run_forever(self):
        """前台运行（阻塞）"""
        if not self._started:
            self.initialize()
        self.logger.info("桥接正在运行，按 Ctrl+C 停止...")
        try:
            while True:
                time.sleep(60)
                # 每分钟输出一次状态摘要
                status = self.get_status()
                self.logger.info(
                    f"状态: 网关{'在线' if status['gateway']['online'] else '离线'} | "
                    f"节点{'已注册' if status['node']['registered'] else '未注册'} | "
                    f"上传队列: {status['sync']['upload_queue_size']} | "
                    f"已应用规则: {status['sync']['applied_rules_count']}"
                )
        except KeyboardInterrupt:
            self.logger.info("收到中断信号")
        finally:
            self.shutdown()
