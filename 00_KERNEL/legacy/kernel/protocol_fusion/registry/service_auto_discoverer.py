#!/usr/bin/env python3
"""
服务自动发现模块 - 扫描指定端口范围，自动检测并注册HTTP服务
"""
import threading
import time
import logging
import requests
from typing import List, Dict, Any, Optional, Set

from ..unified_protocol import ServiceEndpoint, ProtocolType, AuthType

logger = logging.getLogger(__name__)


class ServiceAutoDiscoverer:
    """服务自动发现器 - 定时扫描端口，自动注册新服务"""

    def __init__(
        self,
        registry,
        port_range: tuple = (8000, 8100),
        scan_interval: int = 60,
        health_check_path: str = "/health",
        auto_register: bool = True,
    ):
        self.registry = registry
        self.port_range = port_range
        self.scan_interval = scan_interval
        self.health_check_path = health_check_path
        self.auto_register = auto_register
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._discovered_ports: Set[int] = set()
        self._lock = threading.Lock()
        self._scan_count = 0
        self._new_services_found = 0

    def scan_port(self, port: int, timeout: float = 2.0) -> Optional[Dict[str, Any]]:
        """扫描单个端口，检测是否有HTTP服务"""
        url = f"http://127.0.0.1:{port}"
        try:
            # 先尝试健康检查端点
            health_url = f"{url}{self.health_check_path}"
            response = requests.get(health_url, timeout=timeout)
            if response.status_code < 500:
                try:
                    data = response.json()
                    service_name = data.get("service_name", f"service-{port}")
                    service_version = data.get("version", "1.0.0")
                    description = data.get("description", "")
                    capabilities = data.get("capabilities", [])
                    return {
                        "port": port,
                        "url": url,
                        "service_name": service_name,
                        "service_version": service_version,
                        "description": description,
                        "capabilities": capabilities,
                        "health_check_url": health_url,
                        "health_status": "healthy",
                    }
                except (ValueError, KeyError):
                    # 健康检查返回非JSON，尝试根路径
                    pass

            # 尝试根路径
            response = requests.get(url, timeout=timeout)
            if response.status_code < 500:
                return {
                    "port": port,
                    "url": url,
                    "service_name": f"service-{port}",
                    "service_version": "1.0.0",
                    "description": f"Auto-discovered service on port {port}",
                    "capabilities": [],
                    "health_check_url": health_url,
                    "health_status": "unknown",
                }
        except requests.exceptions.RequestException:
            pass
        return None

    def scan_range(self) -> List[Dict[str, Any]]:
        """扫描整个端口范围"""
        results = []
        start_port, end_port = self.port_range
        logger.info(f"开始扫描端口范围: {start_port}-{end_port}")

        for port in range(start_port, end_port + 1):
            result = self.scan_port(port)
            if result:
                results.append(result)
                logger.info(f"发现服务: port={port}, name={result['service_name']}")

        logger.info(f"扫描完成，发现 {len(results)} 个服务")
        return results

    def register_discovered_services(self, services: List[Dict[str, Any]]) -> int:
        """注册发现的服务"""
        registered = 0
        for svc in services:
            # 检查是否已注册
            existing = self.registry.get_service(svc["service_name"])
            if existing:
                continue

            endpoint = ServiceEndpoint(
                service_name=svc["service_name"],
                service_version=svc["service_version"],
                endpoint_url=svc["url"],
                protocol_type=ProtocolType.REST_JSON,
                auth_type=AuthType.INTERNAL_TRUST,
                health_check_url=svc.get("health_check_url", ""),
                description=svc.get("description", ""),
                capabilities=svc.get("capabilities", []),
                status="active",
            )
            if self.registry.register_service(endpoint):
                registered += 1
                logger.info(f"自动注册服务: {svc['service_name']} -> {svc['url']}")

        return registered

    def _scan_loop(self):
        """扫描循环（后台线程）"""
        while self._running:
            try:
                self._scan_count += 1
                logger.info(f"第 {self._scan_count} 次自动服务发现扫描")

                services = self.scan_range()

                with self._lock:
                    self._discovered_ports.update(s["port"] for s in services)

                if self.auto_register:
                    new_count = self.register_discovered_services(services)
                    self._new_services_found += new_count
                    if new_count > 0:
                        logger.info(f"本次自动注册 {new_count} 个新服务")

            except Exception as e:
                logger.error(f"服务发现扫描异常: {str(e)}")

            # 等待下一次扫描
            for _ in range(self.scan_interval):
                if not self._running:
                    break
                time.sleep(1)

    def start(self):
        """启动自动发现（后台线程）"""
        if self._running:
            logger.warning("服务自动发现已在运行中")
            return

        self._running = True
        self._thread = threading.Thread(target=self._scan_loop, daemon=True)
        self._thread.start()
        logger.info(f"服务自动发现已启动，扫描间隔: {self.scan_interval}秒，端口范围: {self.port_range}")

    def stop(self):
        """停止自动发现"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("服务自动发现已停止")

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            return {
                "running": self._running,
                "scan_count": self._scan_count,
                "new_services_found": self._new_services_found,
                "discovered_ports": sorted(list(self._discovered_ports)),
                "port_range": list(self.port_range),
                "scan_interval": self.scan_interval,
                "auto_register": self.auto_register,
            }

    def scan_now(self) -> Dict[str, Any]:
        """立即执行一次扫描（不等待定时）"""
        services = self.scan_range()
        registered = 0
        if self.auto_register:
            registered = self.register_discovered_services(services)

        with self._lock:
            self._discovered_ports.update(s["port"] for s in services)
            self._scan_count += 1
            self._new_services_found += registered

        return {
            "services_found": len(services),
            "new_registered": registered,
            "services": services,
        }
