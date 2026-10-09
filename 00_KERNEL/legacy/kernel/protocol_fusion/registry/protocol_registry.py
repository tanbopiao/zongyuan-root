#!/usr/bin/env python3
"""
协议注册表 - 自动发现、注册和管理所有同源协议
"""
from typing import Any, Dict, List, Optional
from dataclasses import asdict
import threading
import time
import json
import logging
import uuid

from ..unified_protocol import (
    ServiceEndpoint, ProtocolType, AuthType, DataFormat
)

logger = logging.getLogger(__name__)


class ProtocolRegistry:
    """协议注册表 - 单例模式"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._services: Dict[str, ServiceEndpoint] = {}
        self._adapters: Dict[str, Any] = {}
        self._lock = threading.RLock()
        self._registry_version = "1.0.0"
        self._last_update = time.time()

    def register_service(self, endpoint: ServiceEndpoint) -> bool:
        """注册服务端点"""
        with self._lock:
            key = f"{endpoint.service_name}:{endpoint.service_version}"
            self._services[key] = endpoint
            self._last_update = time.time()
            logger.info(f"服务注册成功: {key} -> {endpoint.endpoint_url}")
            return True

    def unregister_service(self, service_name: str, service_version: str = "*") -> bool:
        """注销服务端点"""
        with self._lock:
            if service_version == "*":
                keys_to_remove = [k for k in self._services if k.startswith(f"{service_name}:")]
                for key in keys_to_remove:
                    del self._services[key]
            else:
                key = f"{service_name}:{service_version}"
                if key in self._services:
                    del self._services[key]
                else:
                    return False
            self._last_update = time.time()
            return True

    def get_service(self, service_name: str, service_version: str = "*") -> Optional[ServiceEndpoint]:
        """获取服务端点"""
        with self._lock:
            if service_version == "*":
                # 返回最新版本
                matching = [v for k, v in self._services.items() if k.startswith(f"{service_name}:")]
                if matching:
                    return matching[-1]
                return None
            key = f"{service_name}:{service_version}"
            return self._services.get(key)

    def list_services(self, protocol_type: Optional[ProtocolType] = None,
                      status: str = "active") -> List[ServiceEndpoint]:
        """列出所有服务"""
        with self._lock:
            services = list(self._services.values())
            if protocol_type:
                services = [s for s in services if s.protocol_type == protocol_type]
            if status:
                services = [s for s in services if s.status == status]
            return services

    def register_adapter(self, adapter_name: str, adapter_instance: Any) -> bool:
        """注册协议适配器"""
        with self._lock:
            self._adapters[adapter_name] = adapter_instance
            logger.info(f"适配器注册成功: {adapter_name}")
            return True

    def get_adapter(self, adapter_name: str) -> Optional[Any]:
        """获取协议适配器"""
        with self._lock:
            return self._adapters.get(adapter_name)

    def get_adapter_for_protocol(self, protocol_type: ProtocolType) -> Optional[Any]:
        """根据协议类型获取适配器"""
        with self._lock:
            for adapter in self._adapters.values():
                if hasattr(adapter, 'protocol_type') and adapter.protocol_type == protocol_type:
                    return adapter
            return None

    def list_adapters(self) -> List[Dict[str, Any]]:
        """列出所有适配器"""
        with self._lock:
            return [adapter.get_stats() for adapter in self._adapters.values()]

    def auto_discover_services(self, scan_urls: List[str]) -> int:
        """自动发现服务（扫描指定URL列表）"""
        discovered = 0
        for url in scan_urls:
            try:
                import requests
                response = requests.get(f"{url}/health", timeout=3)
                if response.status_code == 200:
                    data = response.json()
                    service_name = data.get("service_name", url.split("//")[-1].split(":")[0])
                    service_version = data.get("version", "1.0.0")
                    endpoint = ServiceEndpoint(
                        service_name=service_name,
                        service_version=service_version,
                        endpoint_url=url,
                        protocol_type=ProtocolType.REST_JSON,
                        auth_type=AuthType.INTERNAL_TRUST,
                        health_check_url=f"{url}/health",
                        description=data.get("description", ""),
                        capabilities=data.get("capabilities", []),
                    )
                    if self.register_service(endpoint):
                        discovered += 1
            except Exception as e:
                logger.debug(f"服务发现失败 {url}: {str(e)}")
        return discovered

    def health_check_all(self) -> Dict[str, Any]:
        """对所有注册服务执行健康检查"""
        results = {"total": 0, "healthy": 0, "unhealthy": 0, "details": []}
        with self._lock:
            services = list(self._services.values())

        for service in services:
            results["total"] += 1
            try:
                import requests
                if service.health_check_url:
                    response = requests.get(service.health_check_url, timeout=3)
                    is_healthy = response.status_code < 500
                else:
                    response = requests.get(service.endpoint_url, timeout=3)
                    is_healthy = response.status_code < 500

                service.status = "active" if is_healthy else "unhealthy"
                service.last_health_check = time.time()

                if is_healthy:
                    results["healthy"] += 1
                else:
                    results["unhealthy"] += 1

                results["details"].append({
                    "service": f"{service.service_name}:{service.service_version}",
                    "status": service.status,
                    "response_time_ms": response.elapsed.total_seconds() * 1000 if 'response' in locals() else 0,
                })
            except Exception as e:
                service.status = "unhealthy"
                results["unhealthy"] += 1
                results["details"].append({
                    "service": f"{service.service_name}:{service.service_version}",
                    "status": "unhealthy",
                    "error": str(e),
                })

        return results

    def export_registry(self) -> Dict[str, Any]:
        """导出注册表状态"""
        with self._lock:
            return {
                "registry_version": self._registry_version,
                "last_update": self._last_update,
                "services_count": len(self._services),
                "adapters_count": len(self._adapters),
                "services": [s.to_dict() for s in self._services.values()],
                "adapters": self.list_adapters(),
            }

    def save_to_file(self, filepath: str):
        """保存注册表到文件"""
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.export_registry(), f, ensure_ascii=False, indent=2)

    def load_from_file(self, filepath: str):
        """从文件加载注册表"""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            for svc_data in data.get("services", []):
                endpoint = ServiceEndpoint(
                    service_name=svc_data["service_name"],
                    service_version=svc_data["service_version"],
                    endpoint_url=svc_data["endpoint_url"],
                    protocol_type=ProtocolType(svc_data["protocol_type"]),
                    auth_type=AuthType(svc_data["auth_type"]),
                    data_format=DataFormat(svc_data.get("data_format", "json")),
                    health_check_url=svc_data.get("health_check_url", ""),
                    description=svc_data.get("description", ""),
                    capabilities=svc_data.get("capabilities", []),
                    status=svc_data.get("status", "active"),
                )
                self.register_service(endpoint)
            logger.info(f"注册表加载成功: {filepath}")
        except Exception as e:
            logger.error(f"注册表加载失败: {str(e)}")
