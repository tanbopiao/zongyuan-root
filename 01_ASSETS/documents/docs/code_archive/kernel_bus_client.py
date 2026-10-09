#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT MR-012 内核总线客户端SDK
供所有MR组件接入内核总线使用。

功能：
  - 自动注册到总线
  - 自动心跳上报
  - 读写内核全局状态
  - 发布/订阅事件
  - 接收/执行指令
  - 查询组件状态

使用示例：
  from kernel_bus_client import BusClient

  client = BusClient(
      component_id="my-component",
      component_type="service",
      name="我的组件",
      capabilities=["do_something", "do_other"],
  )
  client.register()
  client.start_heartbeat()

  # 读写状态
  client.set_state("my.key", "value")
  value = client.get_state("my.key")

  # 发布事件
  client.publish_event("something_happened", {"data": "..."})

  # 订阅事件
  events = client.subscribe_events()

  # 接收指令
  commands = client.get_pending_commands()
"""

import os
import sys
import json
import time
import logging
import threading
import requests
from typing import Dict, List, Optional, Any, Callable

# ============================================================
# 配置
# ============================================================
BUS_URL = os.environ.get("KERNEL_BUS_URL", "http://127.0.0.1:9121")
HEARTBEAT_INTERVAL = 30  # 秒

logger = logging.getLogger("kernel_bus_client")


class BusClient:
    """内核总线客户端"""

    def __init__(self, component_id: str, component_type: str, name: str,
                 description: str = "", capabilities: List[str] = None,
                 version: str = "1.0", config: Dict = None,
                 bus_url: str = None, heartbeat_interval: int = HEARTBEAT_INTERVAL):
        self.component_id = component_id
        self.component_type = component_type
        self.name = name
        self.description = description
        self.capabilities = capabilities or []
        self.version = version
        self.config = config or {}
        self.bus_url = bus_url or BUS_URL
        self.heartbeat_interval = heartbeat_interval
        self._registered = False
        self._heartbeat_thread = None
        self._heartbeat_running = False
        self._event_handlers: Dict[str, List[Callable]] = {}
        self._command_handlers: Dict[str, Callable] = {}

    # --- 注册 ---
    def register(self) -> bool:
        """注册组件到总线"""
        try:
            resp = requests.post(
                f"{self.bus_url}/api/component/register",
                json={
                    "component_id": self.component_id,
                    "component_type": self.component_type,
                    "name": self.name,
                    "description": self.description,
                    "capabilities": self.capabilities,
                    "version": self.version,
                    "config": self.config,
                },
                timeout=5,
            )
            if resp.status_code == 200:
                self._registered = True
                logger.info(f"组件注册成功: {self.component_id}")
                return True
            else:
                logger.error(f"组件注册失败: {resp.status_code} {resp.text}")
                return False
        except Exception as e:
            logger.error(f"组件注册异常: {e}")
            return False

    def unregister(self):
        """注销组件（更新状态为inactive）"""
        self._heartbeat_running = False
        try:
            requests.post(
                f"{self.bus_url}/api/component/heartbeat",
                json={"component_id": self.component_id, "status": "inactive"},
                timeout=5,
            )
        except Exception:
            pass
        self._registered = False

    # --- 心跳 ---
    def heartbeat(self, metrics: Dict = None) -> bool:
        """发送一次心跳"""
        try:
            resp = requests.post(
                f"{self.bus_url}/api/component/heartbeat",
                json={
                    "component_id": self.component_id,
                    "status": "active",
                    "metrics": metrics or {},
                },
                timeout=5,
            )
            return resp.status_code == 200
        except Exception as e:
            logger.debug(f"心跳异常: {e}")
            return False

    def start_heartbeat(self):
        """启动后台心跳线程"""
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            return
        self._heartbeat_running = True
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._heartbeat_thread.start()
        logger.info(f"心跳线程已启动: 间隔{self.heartbeat_interval}秒")

    def stop_heartbeat(self):
        """停止心跳线程"""
        self._heartbeat_running = False

    def _heartbeat_loop(self):
        """心跳循环"""
        while self._heartbeat_running:
            try:
                # 收集基础指标
                metrics = self._collect_metrics()
                self.heartbeat(metrics)
            except Exception as e:
                logger.debug(f"心跳循环异常: {e}")
            time.sleep(self.heartbeat_interval)

    def _collect_metrics(self) -> Dict:
        """收集基础指标（子类可重写）"""
        metrics = {}
        try:
            import psutil
            metrics["cpu_percent"] = psutil.cpu_percent(interval=0.1)
            metrics["memory_mb"] = psutil.Process().memory_info().rss / 1024 / 1024
        except ImportError:
            pass
        return metrics

    # --- 内核状态 ---
    def get_state(self, key: str = None) -> Any:
        """获取内核状态"""
        try:
            url = f"{self.bus_url}/api/kernel/state"
            if key:
                url += f"?key={key}"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                return resp.json().get("state")
        except Exception as e:
            logger.debug(f"获取状态异常: {e}")
        return None

    def set_state(self, key: str, value: Any) -> bool:
        """设置内核状态"""
        try:
            resp = requests.post(
                f"{self.bus_url}/api/kernel/state",
                json={"key": key, "value": value, "updated_by": self.component_id},
                timeout=5,
            )
            return resp.status_code == 200
        except Exception as e:
            logger.debug(f"设置状态异常: {e}")
            return False

    # --- 事件 ---
    def publish_event(self, event_type: str, payload: Dict = None,
                      target: str = None, priority: int = 0) -> int:
        """发布事件"""
        try:
            resp = requests.post(
                f"{self.bus_url}/api/event/publish",
                json={
                    "event_type": event_type,
                    "source": self.component_id,
                    "payload": payload or {},
                    "target": target,
                    "priority": priority,
                },
                timeout=5,
            )
            if resp.status_code == 200:
                return resp.json().get("event_id", -1)
        except Exception as e:
            logger.debug(f"发布事件异常: {e}")
        return -1

    def subscribe_events(self, event_types: List[str] = None,
                         since_id: int = 0, limit: int = 50) -> List[Dict]:
        """订阅/拉取事件"""
        try:
            resp = requests.post(
                f"{self.bus_url}/api/event/subscribe",
                json={
                    "component_id": self.component_id,
                    "event_types": event_types,
                    "since_id": since_id,
                    "limit": limit,
                },
                timeout=5,
            )
            if resp.status_code == 200:
                return resp.json().get("events", [])
        except Exception as e:
            logger.debug(f"订阅事件异常: {e}")
        return []

    def register_event_handler(self, event_type: str, handler: Callable):
        """注册事件处理器"""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)

    def process_events(self, event_types: List[str] = None) -> int:
        """处理待处理事件（调用注册的处理器）"""
        events = self.subscribe_events(event_types)
        processed = 0
        for event in events:
            event_type = event.get("event_type")
            handlers = self._event_handlers.get(event_type, [])
            for handler in handlers:
                try:
                    handler(event)
                    processed += 1
                except Exception as e:
                    logger.error(f"事件处理器异常: {e}")
        return processed

    # --- 指令 ---
    def get_pending_commands(self) -> List[Dict]:
        """获取待执行指令"""
        try:
            resp = requests.post(
                f"{self.bus_url}/api/command/pending",
                json={"component_id": self.component_id},
                timeout=5,
            )
            # 注意：总线API是通过subscribe的方式，这里用另一个端点
            # 实际上待执行指令通过 /api/command/pending 获取
            if resp.status_code == 200:
                return resp.json().get("commands", [])
        except Exception:
            pass
        return []

    def complete_command(self, command_id: str, status: str = "completed",
                         result: Dict = None) -> bool:
        """完成指令"""
        try:
            resp = requests.post(
                f"{self.bus_url}/api/command/complete",
                json={
                    "command_id": command_id,
                    "status": status,
                    "result": result or {},
                },
                timeout=5,
            )
            return resp.status_code == 200
        except Exception as e:
            logger.debug(f"完成指令异常: {e}")
            return False

    def register_command_handler(self, command_type: str, handler: Callable):
        """注册指令处理器"""
        self._command_handlers[command_type] = handler

    def process_commands(self) -> int:
        """处理待执行指令"""
        commands = self.get_pending_commands()
        processed = 0
        for cmd in commands:
            cmd_type = cmd.get("command_type")
            handler = self._command_handlers.get(cmd_type)
            if handler:
                try:
                    result = handler(cmd)
                    self.complete_command(cmd["command_id"], "completed", result)
                    processed += 1
                except Exception as e:
                    logger.error(f"指令处理器异常: {e}")
                    self.complete_command(cmd["command_id"], "failed", {"error": str(e)})
            else:
                self.complete_command(cmd["command_id"], "failed", {"error": f"无处理器: {cmd_type}"})
        return processed

    # --- 查询 ---
    def get_component_info(self, component_id: str = None) -> Optional[Dict]:
        """获取组件信息"""
        cid = component_id or self.component_id
        try:
            resp = requests.get(f"{self.bus_url}/api/component/{cid}", timeout=5)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return None

    def list_components(self, status: str = None) -> List[Dict]:
        """列出所有组件"""
        try:
            url = f"{self.bus_url}/api/component/list"
            if status:
                url += f"?status={status}"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                return resp.json().get("components", [])
        except Exception:
            pass
        return []

    def get_dashboard(self) -> Optional[Dict]:
        """获取内核仪表盘"""
        try:
            resp = requests.get(f"{self.bus_url}/api/dashboard", timeout=5)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return None

    def is_bus_available(self) -> bool:
        """检查总线是否可用"""
        try:
            resp = requests.get(f"{self.bus_url}/api/health", timeout=3)
            return resp.status_code == 200
        except Exception:
            return False


# ============================================================
# 便捷函数：快速接入总线
# ============================================================
def connect_to_bus(component_id: str, component_type: str, name: str,
                   capabilities: List[str] = None, auto_heartbeat: bool = True) -> Optional[BusClient]:
    """
    快速接入内核总线。

    返回BusClient实例，如果总线不可用则返回None。
    """
    client = BusClient(
        component_id=component_id,
        component_type=component_type,
        name=name,
        capabilities=capabilities,
    )
    if not client.is_bus_available():
        logger.warning("内核总线不可用，跳过注册")
        return None
    if client.register():
        if auto_heartbeat:
            client.start_heartbeat()
        return client
    return None


# ============================================================
# 自测
# ============================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("=== 内核总线客户端SDK自测 ===")

    client = BusClient(
        component_id="test-client",
        component_type="test",
        name="测试客户端",
        capabilities=["test"],
    )

    # 检查总线
    if client.is_bus_available():
        print("✅ 总线可用")
    else:
        print("❌ 总线不可用（请先启动MR-012总线服务）")
        sys.exit(1)

    # 注册
    if client.register():
        print("✅ 组件注册成功")
    else:
        print("❌ 组件注册失败")
        sys.exit(1)

    # 心跳
    if client.heartbeat({"test": "ok"}):
        print("✅ 心跳发送成功")
    else:
        print("❌ 心跳发送失败")

    # 状态读写
    client.set_state("test.key", "test_value")
    value = client.get_state("test.key")
    print(f"✅ 状态读写: {value}")

    # 发布事件
    event_id = client.publish_event("test.event", {"data": "hello"})
    print(f"✅ 事件发布: id={event_id}")

    # 仪表盘
    dashboard = client.get_dashboard()
    if dashboard:
        print(f"✅ 仪表盘: 组件={dashboard['components']['total']}, 在线={dashboard['components']['online']}")

    print("\n=== 自测完成 ===")
