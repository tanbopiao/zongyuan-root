#!/usr/bin/env python3
"""
统一API网关 V1.1 - 集成自动服务发现 + 健康监控 + 熔断降级
"""
from typing import Any, Dict, Optional
from flask import Flask, request, jsonify
import threading
import time
import uuid
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ..unified_protocol import (
    UnifiedRequest, UnifiedResponse, ProtocolType, AuthType,
    ZR_PROTOCOL_VERSION, ZR_PROTOCOL_HEADER, ZR_TRACE_HEADER, ZR_SERVICE_HEADER
)
from ..registry.protocol_registry import ProtocolRegistry
from ..registry.service_auto_discoverer import ServiceAutoDiscoverer
from ..registry.health_monitor import HealthMonitor
from ..adapters.rest_json_adapter import RestJsonAdapter

logger = logging.getLogger(__name__)


class UnifiedAPIGateway:
    """统一API网关 V1.1"""

    def __init__(self, host: str = "0.0.0.0", port: int = 8900, config: Optional[Dict[str, Any]] = None):
        self.host = host
        self.port = port
        self.config = config or {}
        self.registry = ProtocolRegistry()
        self.app = Flask(__name__)
        self.request_count = 0
        self.success_count = 0
        self.failure_count = 0
        self._lock = threading.Lock()

        # 初始化组件
        self._setup_adapters()
        self._setup_health_monitor()
        self._setup_auto_discoverer()
        self._setup_routes()

    def _setup_adapters(self):
        """初始化默认适配器"""
        rest_adapter = RestJsonAdapter(self.config.get("rest_config", {}))
        self.registry.register_adapter("rest_json", rest_adapter)

    def _setup_health_monitor(self):
        """初始化健康监控器"""
        self.health_monitor = HealthMonitor(
            registry=self.registry,
            check_interval=self.config.get("health_check_interval", 30),
            health_timeout=self.config.get("health_timeout", 3.0),
            failure_threshold=self.config.get("failure_threshold", 3),
            recovery_timeout=self.config.get("recovery_timeout", 30),
        )

    def _setup_auto_discoverer(self):
        """初始化自动服务发现器"""
        self.auto_discoverer = ServiceAutoDiscoverer(
            registry=self.registry,
            port_range=tuple(self.config.get("scan_port_range", (8000, 8100))),
            scan_interval=self.config.get("scan_interval", 60),
            auto_register=True,
        )

    def _setup_routes(self):
        """设置API路由"""

        @self.app.route("/health", methods=["GET"])
        def health():
            return jsonify({
                "status": "healthy",
                "gateway_version": "1.1.0",
                "protocol_version": ZR_PROTOCOL_VERSION,
                "services_registered": len(self.registry.list_services()),
                "adapters_registered": len(self.registry.list_adapters()),
                "health_monitor_running": self.health_monitor._running,
                "auto_discoverer_running": self.auto_discoverer._running,
                "request_count": self.request_count,
                "success_count": self.success_count,
                "failure_count": self.failure_count,
                "timestamp": time.time(),
            })

        @self.app.route("/registry/services", methods=["GET"])
        def list_services():
            services = self.registry.list_services()
            return jsonify({
                "total": len(services),
                "services": [s.to_dict() for s in services],
            })

        @self.app.route("/registry/adapters", methods=["GET"])
        def list_adapters():
            return jsonify({
                "total": len(self.registry.list_adapters()),
                "adapters": self.registry.list_adapters(),
            })

        @self.app.route("/registry/register", methods=["POST"])
        def register_service():
            data = request.json
            from ..unified_protocol import ServiceEndpoint
            endpoint = ServiceEndpoint(
                service_name=data["service_name"],
                service_version=data.get("service_version", "1.0.0"),
                endpoint_url=data["endpoint_url"],
                protocol_type=ProtocolType(data.get("protocol_type", "rest_json")),
                auth_type=AuthType(data.get("auth_type", "internal_trust")),
                health_check_url=data.get("health_check_url", ""),
                description=data.get("description", ""),
                capabilities=data.get("capabilities", []),
            )
            self.registry.register_service(endpoint)
            return jsonify({"status": "registered", "service": endpoint.to_dict()})

        @self.app.route("/invoke/<service_name>", methods=["GET", "POST", "PUT", "DELETE"])
        @self.app.route("/invoke/<service_name>/<path:endpoint>", methods=["GET", "POST", "PUT", "DELETE"])
        def invoke_service(service_name: str, endpoint: str = ""):
            """统一调用入口 - 带熔断检查"""
            start_time = time.time()
            with self._lock:
                self.request_count += 1

            # 熔断检查
            if not self.health_monitor.allow_request(service_name):
                with self._lock:
                    self.failure_count += 1
                return jsonify({
                    "success": False,
                    "error": {"code": 1007, "message": f"服务 {service_name} 已熔断，请求被拒绝"},
                    "request_id": f"gw-{uuid.uuid4().hex[:16]}",
                }), 503

            # 构建统一请求
            unified_request = UnifiedRequest(
                request_id=f"gw-{uuid.uuid4().hex[:16]}",
                source_service=request.headers.get(ZR_SERVICE_HEADER, "external"),
                target_service=service_name,
                endpoint=endpoint,
                method=request.method,
                headers=dict(request.headers),
                params=dict(request.args),
                body=request.json if request.is_json else (request.data.decode() if request.data else None),
            )

            # 获取服务端点
            service = self.registry.get_service(service_name)
            if not service:
                with self._lock:
                    self.failure_count += 1
                self.health_monitor.record_request_result(service_name, False)
                return jsonify({
                    "success": False,
                    "error": {"code": 1001, "message": f"服务未注册: {service_name}"},
                    "request_id": unified_request.request_id,
                }), 404

            # 获取适配器
            adapter = self.registry.get_adapter_for_protocol(service.protocol_type)
            if not adapter:
                with self._lock:
                    self.failure_count += 1
                return jsonify({
                    "success": False,
                    "error": {"code": 1006, "message": f"不支持的协议类型: {service.protocol_type}"},
                    "request_id": unified_request.request_id,
                }), 500

            # 设置适配器的base_url
            if hasattr(adapter, "base_url"):
                adapter.base_url = service.endpoint_url

            # 执行请求
            unified_response = adapter.execute(unified_request)

            # 记录请求结果（用于熔断）
            self.health_monitor.record_request_result(service_name, unified_response.success)

            with self._lock:
                if unified_response.success:
                    self.success_count += 1
                else:
                    self.failure_count += 1

            # 返回统一响应
            response = jsonify(unified_response.to_dict())
            response.headers[ZR_PROTOCOL_HEADER] = ZR_PROTOCOL_VERSION
            response.headers[ZR_TRACE_HEADER] = unified_response.trace_hash
            response.status_code = unified_response.status_code
            return response

        @self.app.route("/stats", methods=["GET"])
        def gateway_stats():
            return jsonify({
                "request_count": self.request_count,
                "success_count": self.success_count,
                "failure_count": self.failure_count,
                "success_rate": round(self.success_count / max(self.request_count, 1), 4),
                "services": len(self.registry.list_services()),
                "adapters": len(self.registry.list_adapters()),
            })

        # === 新增：自动服务发现API ===
        @self.app.route("/discovery/status", methods=["GET"])
        def discovery_status():
            return jsonify(self.auto_discoverer.get_stats())

        @self.app.route("/discovery/scan", methods=["POST"])
        def discovery_scan():
            """立即执行一次服务发现扫描"""
            result = self.auto_discoverer.scan_now()
            return jsonify({
                "status": "completed",
                "services_found": result["services_found"],
                "new_registered": result["new_registered"],
                "services": result["services"],
            })

        # === 新增：健康监控API ===
        @self.app.route("/health-monitor/status", methods=["GET"])
        def health_monitor_status():
            return jsonify(self.health_monitor.get_stats())

        @self.app.route("/health-monitor/check", methods=["POST"])
        def health_monitor_check():
            """立即执行一次全量健康检查"""
            result = self.health_monitor.check_now()
            return jsonify({
                "status": "completed",
                "total": result["total"],
                "healthy": result["healthy"],
                "unhealthy": result["unhealthy"],
                "circuit_open": result["circuit_open"],
                "details": result["details"],
            })

        @self.app.route("/circuit-breaker/<service_name>", methods=["GET"])
        def circuit_breaker_status(service_name: str):
            """查看指定服务的熔断器状态"""
            breaker = self.health_monitor._get_or_create_breaker(service_name)
            return jsonify(breaker.get_state())

    def register_default_services(self):
        """注册默认服务"""
        from ..unified_protocol import ServiceEndpoint, ProtocolType, AuthType

        default_services = [
            ("gov-api", "1.0.0", "http://127.0.0.1:8025", "政务API服务"),
            ("main-api", "1.0.0", "http://127.0.0.1:8000", "主API服务"),
            ("system-state", "1.0.0", "http://127.0.0.1:8004", "系统状态服务"),
            ("workbench-api", "1.0.0", "http://127.0.0.1:8765", "工作台API"),
            ("drama-api", "1.0.0", "http://127.0.0.1:8012", "短剧API服务"),
            ("vector-retrieval", "1.0.0", "http://127.0.0.1:8003", "向量检索服务"),
            ("smart-ai", "1.0.0", "http://127.0.0.1:8005", "智能AI服务"),
            ("ops-service", "1.0.0", "http://127.0.0.1:8007", "运维服务"),
            ("ai-research", "1.0.0", "http://127.0.0.1:8009", "AI研究服务"),
            ("api-gateway", "1.0.0", "http://127.0.0.1:8010", "API网关服务"),
            ("platform-service", "1.0.0", "http://127.0.0.1:8011", "平台服务"),
            ("drama-works", "1.0.0", "http://127.0.0.1:8021", "短剧作品服务"),
            ("drama-management", "1.0.0", "http://127.0.0.1:8022", "短剧管理服务"),
            ("education-service", "1.0.0", "http://127.0.0.1:8025", "教育服务"),
            ("agent-federation", "1.0.0", "http://127.0.0.1:8023", "Agent联邦服务"),
        ]

        for name, version, url, desc in default_services:
            endpoint = ServiceEndpoint(
                service_name=name,
                service_version=version,
                endpoint_url=url,
                protocol_type=ProtocolType.REST_JSON,
                auth_type=AuthType.INTERNAL_TRUST,
                health_check_url=f"{url}/health",
                description=desc,
            )
            self.registry.register_service(endpoint)

        logger.info(f"已注册 {len(default_services)} 个默认服务")

    def start_background_services(self):
        """启动后台服务（健康监控+自动发现）"""
        self.health_monitor.start()
        logger.info("健康监控已启动")
        self.auto_discoverer.start()
        logger.info("自动服务发现已启动")

    def start(self):
        """启动网关"""
        logger.info(f"统一API网关 V1.1 启动: {self.host}:{self.port}")
        self.register_default_services()
        self.start_background_services()
        self.app.run(host=self.host, port=self.port, threaded=True)

    def get_flask_app(self):
        return self.app
