#!/usr/bin/env python3
"""
服务健康监控与熔断降级模块
- 定时健康检查所有注册服务
- 异常服务自动熔断
- 请求降级到备用服务
- 服务恢复自动半开探测
"""
import threading
import time
import logging
import requests
from typing import Dict, Any, Optional, List
from enum import Enum

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """熔断器状态"""
    CLOSED = "closed"           # 正常状态，请求正常通过
    OPEN = "open"               # 熔断状态，请求直接拒绝/降级
    HALF_OPEN = "half_open"     # 半开状态，允许少量请求探测


class ServiceCircuitBreaker:
    """单个服务的熔断器"""

    def __init__(
        self,
        service_name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 30,
        half_open_max_requests: int = 3,
    ):
        self.service_name = service_name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_requests = half_open_max_requests

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0.0
        self.last_success_time = 0.0
        self.half_open_requests = 0
        self.total_requests = 0
        self.total_failures = 0
        self._lock = threading.Lock()

    def allow_request(self) -> bool:
        """是否允许请求通过"""
        with self._lock:
            if self.state == CircuitState.CLOSED:
                return True

            if self.state == CircuitState.OPEN:
                # 检查是否超过恢复超时，进入半开状态
                if time.time() - self.last_failure_time >= self.recovery_timeout:
                    self.state = CircuitState.HALF_OPEN
                    self.half_open_requests = 0
                    logger.info(f"服务 {self.service_name} 进入半开状态，开始探测恢复")
                    return True
                return False

            if self.state == CircuitState.HALF_OPEN:
                # 半开状态允许有限请求探测
                if self.half_open_requests < self.half_open_max_requests:
                    self.half_open_requests += 1
                    return True
                return False

            return False

    def record_success(self):
        """记录成功"""
        with self._lock:
            self.total_requests += 1
            self.success_count += 1
            self.last_success_time = time.time()

            if self.state == CircuitState.HALF_OPEN:
                # 半开状态连续成功，恢复正常
                if self.success_count >= self.half_open_max_requests:
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    self.success_count = 0
                    logger.info(f"服务 {self.service_name} 恢复正常，熔断器关闭")

            elif self.state == CircuitState.CLOSED:
                # 正常状态，重置失败计数
                if self.failure_count > 0:
                    self.failure_count = max(0, self.failure_count - 1)

    def record_failure(self):
        """记录失败"""
        with self._lock:
            self.total_requests += 1
            self.total_failures += 1
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.state == CircuitState.HALF_OPEN:
                # 半开状态失败，重新熔断
                self.state = CircuitState.OPEN
                self.half_open_requests = 0
                self.success_count = 0
                logger.warning(f"服务 {self.service_name} 半开探测失败，重新熔断")

            elif self.state == CircuitState.CLOSED:
                # 正常状态失败达到阈值，熔断
                if self.failure_count >= self.failure_threshold:
                    self.state = CircuitState.OPEN
                    logger.warning(f"服务 {self.service_name} 失败次数达到阈值({self.failure_threshold})，熔断器打开")

    def get_state(self) -> Dict[str, Any]:
        """获取熔断器状态"""
        with self._lock:
            return {
                "service_name": self.service_name,
                "state": self.state.value,
                "failure_count": self.failure_count,
                "success_count": self.success_count,
                "total_requests": self.total_requests,
                "total_failures": self.total_failures,
                "failure_rate": round(self.total_failures / max(self.total_requests, 1), 4),
                "last_failure_time": self.last_failure_time,
                "last_success_time": self.last_success_time,
            }


class HealthMonitor:
    """服务健康监控器 - 定时健康检查所有注册服务"""

    def __init__(
        self,
        registry,
        check_interval: int = 30,
        health_timeout: float = 3.0,
        failure_threshold: int = 3,
        recovery_timeout: int = 30,
    ):
        self.registry = registry
        self.check_interval = check_interval
        self.health_timeout = health_timeout
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout

        self._circuit_breakers: Dict[str, ServiceCircuitBreaker] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._check_count = 0
        self._lock = threading.Lock()

    def _get_or_create_breaker(self, service_name: str) -> ServiceCircuitBreaker:
        """获取或创建熔断器"""
        with self._lock:
            if service_name not in self._circuit_breakers:
                self._circuit_breakers[service_name] = ServiceCircuitBreaker(
                    service_name=service_name,
                    failure_threshold=self.failure_threshold,
                    recovery_timeout=self.recovery_timeout,
                )
            return self._circuit_breakers[service_name]

    def check_service_health(self, service_name: str) -> bool:
        """检查单个服务健康状态"""
        service = self.registry.get_service(service_name)
        if not service:
            return False

        breaker = self._get_or_create_breaker(service_name)

        # 如果熔断状态，不主动检查（等待恢复超时）
        if breaker.state == CircuitState.OPEN:
            if time.time() - breaker.last_failure_time >= self.recovery_timeout:
                # 超过恢复时间，尝试探测
                pass
            else:
                return False

        health_url = service.health_check_url or f"{service.endpoint_url}/health"

        try:
            response = requests.get(health_url, timeout=self.health_timeout)
            is_healthy = response.status_code < 500

            if is_healthy:
                breaker.record_success()
                service.status = "active"
            else:
                breaker.record_failure()
                service.status = "unhealthy"

            service.last_health_check = time.time()
            return is_healthy

        except requests.exceptions.RequestException:
            breaker.record_failure()
            service.status = "unhealthy"
            service.last_health_check = time.time()
            return False

    def check_all_services(self) -> Dict[str, Any]:
        """检查所有服务健康状态"""
        services = self.registry.list_services()
        results = {
            "total": len(services),
            "healthy": 0,
            "unhealthy": 0,
            "circuit_open": 0,
            "details": [],
        }

        for service in services:
            is_healthy = self.check_service_health(service.service_name)
            breaker = self._get_or_create_breaker(service.service_name)

            if is_healthy:
                results["healthy"] += 1
            else:
                results["unhealthy"] += 1

            if breaker.state == CircuitState.OPEN:
                results["circuit_open"] += 1

            results["details"].append({
                "service_name": service.service_name,
                "healthy": is_healthy,
                "circuit_state": breaker.state.value,
                "failure_count": breaker.failure_count,
            })

        return results

    def allow_request(self, service_name: str) -> bool:
        """检查是否允许请求通过（熔断检查）"""
        breaker = self._get_or_create_breaker(service_name)
        return breaker.allow_request()

    def record_request_result(self, service_name: str, success: bool):
        """记录请求结果（用于熔断器统计）"""
        breaker = self._get_or_create_breaker(service_name)
        if success:
            breaker.record_success()
        else:
            breaker.record_failure()

    def _monitor_loop(self):
        """监控循环（后台线程）"""
        while self._running:
            try:
                self._check_count += 1
                logger.info(f"第 {self._check_count} 次健康检查开始")
                results = self.check_all_services()
                logger.info(
                    f"健康检查完成: 总计{results['total']}, "
                    f"正常{results['healthy']}, 异常{results['unhealthy']}, "
                    f"熔断{results['circuit_open']}"
                )
            except Exception as e:
                logger.error(f"健康检查异常: {str(e)}")

            # 等待下一次检查
            for _ in range(self.check_interval):
                if not self._running:
                    break
                time.sleep(1)

    def start(self):
        """启动健康监控（后台线程）"""
        if self._running:
            logger.warning("健康监控已在运行中")
            return

        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info(f"健康监控已启动，检查间隔: {self.check_interval}秒")

    def stop(self):
        """停止健康监控"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("健康监控已停止")

    def get_stats(self) -> Dict[str, Any]:
        """获取监控统计信息"""
        with self._lock:
            breakers_stats = {
                name: breaker.get_state()
                for name, breaker in self._circuit_breakers.items()
            }
            return {
                "running": self._running,
                "check_count": self._check_count,
                "check_interval": self.check_interval,
                "monitored_services": len(self._circuit_breakers),
                "circuit_breakers": breakers_stats,
            }

    def check_now(self) -> Dict[str, Any]:
        """立即执行一次健康检查"""
        return self.check_all_services()
