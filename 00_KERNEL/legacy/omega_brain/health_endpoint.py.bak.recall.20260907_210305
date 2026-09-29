#!/usr/bin/env python3
"""
P3断点补齐 - 健康检查HTTP端点 (Health Endpoint)

提供标准HTTP健康检查接口:
  GET /health    - 健康检查 (liveness/readiness)
  GET /metrics   - Prometheus格式指标
  GET /status    - 完整系统状态JSON
  GET /config    - 当前配置（脱敏）
  GET /truth     - 四真值架构状态

基于标准库http.server，无外部依赖，2核4GB可运行。
"""

import json
import os
import sys
import threading
import time
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Any, Dict, Optional

sys.path.insert(0, str(Path(__file__).parent))


class HealthEndpoint:
    """
    健康检查端点管理器

    用法:
        endpoint = HealthEndpoint(port=8080)
        endpoint.start()
        # 访问 http://localhost:8080/health
        endpoint.stop()
    """

    VERSION = "1.0.0"

    def __init__(self, port: int = 8080, host: str = "0.0.0.0"):
        self.port = port
        self.host = host
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._start_time = time.time()

        # 集成各模块状态
        self._status_collectors = {}

    def register_status_collector(self, name: str, collector):
        """注册状态收集器"""
        self._status_collectors[name] = collector

    def _collect_health(self) -> dict:
        """收集健康状态"""
        uptime_seconds = round(time.time() - self._start_time, 1)

        # 基础健康检查
        checks = {
            'process': self._check_process(),
            'disk': self._check_disk(),
            'memory': self._check_memory(),
            'config': self._check_config(),
        }

        all_healthy = all(c['healthy'] for c in checks.values())

        return {
            'status': 'healthy' if all_healthy else 'degraded',
            'uptime_seconds': uptime_seconds,
            'uptime_human': self._format_uptime(uptime_seconds),
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'checks': checks,
            'version': self.VERSION,
        }

    def _check_process(self) -> dict:
        return {'healthy': True, 'pid': os.getpid(), 'status': 'running'}

    def _check_disk(self) -> dict:
        try:
            stat = os.statvfs('/')
            total = stat.f_blocks * stat.f_frsize
            free = stat.f_bavail * stat.f_frsize
            used_pct = round((1 - free / total) * 100, 1)
            return {'healthy': used_pct < 90, 'total_gb': round(total / 1e9, 1),
                    'free_gb': round(free / 1e9, 1), 'used_pct': used_pct}
        except Exception:
            return {'healthy': True, 'note': 'disk check unavailable'}

    def _check_memory(self) -> dict:
        try:
            import resource
            usage = resource.getrusage(resource.RUSAGE_SELF)
            max_rss_mb = round(usage.ru_maxrss / 1024, 1)
            return {'healthy': max_rss_mb < 3500, 'max_rss_mb': max_rss_mb,
                    'limit_mb': 4096}
        except Exception:
            return {'healthy': True, 'note': 'memory check unavailable'}

    def _check_config(self) -> dict:
        try:
            from config_center import get_config
            config = get_config()
            valid, errors = config.validate()
            return {'healthy': valid, 'config_hash': config.get_status()['config_hash'][:16],
                    'errors': errors}
        except Exception:
            return {'healthy': True, 'note': 'config check skipped'}

    @staticmethod
    def _format_uptime(seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours}h {minutes}m {secs}s"

    def _collect_metrics(self) -> str:
        """收集Prometheus格式指标"""
        lines = []
        lines.append("# HELP zyr_system_uptime_seconds System uptime in seconds")
        lines.append("# TYPE zyr_system_uptime_seconds gauge")
        lines.append(f"zyr_system_uptime_seconds {round(time.time() - self._start_time, 1)}")

        lines.append("# HELP zyr_system_health System health status (1=healthy, 0=degraded)")
        lines.append("# TYPE zyr_system_health gauge")
        health = self._collect_health()
        lines.append(f"zyr_system_health {1 if health['status'] == 'healthy' else 0}")

        # 从各收集器获取指标
        for name, collector in self._status_collectors.items():
            try:
                if hasattr(collector, 'get_summary'):
                    summary = collector.get_summary()
                    prefix = f"zyr_{name}"
                    if isinstance(summary, dict):
                        for key, value in summary.items():
                            if isinstance(value, (int, float)):
                                metric_name = f"{prefix}_{key}".replace('.', '_')
                                lines.append(f"# HELP {metric_name} {name} {key}")
                                lines.append(f"# TYPE {metric_name} gauge")
                                lines.append(f"{metric_name} {value}")
            except Exception:
                continue

        # 执行器指标
        try:
            from executor import TaskExecutor
            executor = TaskExecutor()
            stats = executor.queue.stats()
            lines.append("# HELP zyr_executor_queue_total Total tasks in queue")
            lines.append("# TYPE zyr_executor_queue_total gauge")
            lines.append(f"zyr_executor_queue_total {stats.get('total', 0)}")
            for state, count in stats.items():
                if state != 'total':
                    lines.append(f"# HELP zyr_executor_queue_{state} Tasks in {state} state")
                    lines.append(f"# TYPE zyr_executor_queue_{state} gauge")
                    lines.append(f"zyr_executor_queue_{state} {count}")
        except Exception:
            pass

        return '\n'.join(lines)

    def _collect_full_status(self) -> dict:
        """收集完整系统状态"""
        status = {
            'endpoint_version': self.VERSION,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'uptime_seconds': round(time.time() - self._start_time, 1),
            'health': self._collect_health(),
            'system': {
                'pid': os.getpid(),
                'python_version': sys.version,
                'platform': sys.platform,
            },
        }

        # 收集各模块状态
        modules = {}

        # 配置中心
        try:
            from config_center import get_config
            config = get_config()
            modules['config_center'] = config.get_status()
        except Exception as e:
            modules['config_center'] = {'error': str(e)}

        # 执行器
        try:
            from executor import TaskExecutor
            executor = TaskExecutor()
            modules['executor'] = executor.get_status()
        except Exception as e:
            modules['executor'] = {'error': str(e)}

        # 熔断器
        try:
            from circuit_breaker import get_global_breaker
            breaker = get_global_breaker()
            modules['circuit_breaker'] = breaker.get_status()
        except Exception as e:
            modules['circuit_breaker'] = {'error': str(e)}

        # 四真值架构
        try:
            from truth_architecture import get_global_truth_arch
            arch = get_global_truth_arch()
            modules['truth_architecture'] = arch.get_status()
        except Exception as e:
            modules['truth_architecture'] = {'error': str(e)}

        # 向量适配器
        try:
            from vector_truth_adapter_v2 import VectorTruthAdapterV2
            adapter = VectorTruthAdapterV2()
            modules['vector_adapter'] = adapter.get_status()
        except Exception as e:
            modules['vector_adapter'] = {'error': str(e)}

        # 注册的收集器
        for name, collector in self._status_collectors.items():
            try:
                if hasattr(collector, 'get_status'):
                    modules[name] = collector.get_status()
            except Exception as e:
                modules[name] = {'error': str(e)}

        status['modules'] = modules
        return status

    def _collect_truth_status(self) -> dict:
        """收集四真值架构状态"""
        try:
            from truth_architecture import get_global_truth_arch
            arch = get_global_truth_arch()
            validation = arch.cross_validate()
            snapshot = arch.snapshot()
            return {
                'architecture': arch.get_status(),
                'validation': {
                    'valid': validation['valid'],
                    'passed': validation['passed'],
                    'total_checks': validation['total_checks'],
                    'drifts': validation['drifts'],
                },
                'snapshot': {
                    'id': snapshot['snapshot_id'],
                    'global_merkle_root': snapshot['global_merkle_root'],
                    'domain_roots': snapshot['domain_merkle_roots'],
                },
            }
        except Exception as e:
            return {'error': str(e)}

    def start(self):
        """启动HTTP服务器（后台线程）"""
        if self._running:
            return

        handler = self._create_handler()
        self._server = HTTPServer((self.host, self.port), handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        self._running = True
        print(f"[HealthEndpoint] Started on {self.host}:{self.port}")

    def stop(self):
        """停止HTTP服务器"""
        if self._server:
            self._server.shutdown()
            self._server.server_close()
        self._running = False
        print("[HealthEndpoint] Stopped")

    def _create_handler(self):
        """创建HTTP请求处理器"""
        endpoint = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == '/health':
                    self._send_json(endpoint._collect_health())
                elif self.path == '/metrics':
                    self._send_text(endpoint._collect_metrics(), content_type='text/plain')
                elif self.path == '/status':
                    self._send_json(endpoint._collect_full_status())
                elif self.path == '/truth':
                    self._send_json(endpoint._collect_truth_status())
                elif self.path == '/config':
                    try:
                        from config_center import get_config
                        config = get_config()
                        # 脱敏：移除敏感字段
                        safe_config = config.get_all()
                        if 'vector' in safe_config:
                            safe_config['vector']['api_key'] = '***' if safe_config['vector'].get('api_key') else ''
                        self._send_json(safe_config)
                    except Exception as e:
                        self._send_json({'error': str(e)}, status=500)
                else:
                    self._send_json({'error': 'not found', 'endpoints': ['/health', '/metrics', '/status', '/truth', '/config']}, status=404)

            def _send_json(self, data: dict, status: int = 200):
                body = json.dumps(data, indent=2, ensure_ascii=False, default=str).encode()
                self.send_response(status)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _send_text(self, text: str, content_type: str = 'text/plain', status: int = 200):
                body = text.encode()
                self.send_response(status)
                self.send_header('Content-Type', content_type)
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format, *args):
                pass  # 静默日志

        return Handler


def main():
    """CLI入口"""
    import argparse
    parser = argparse.ArgumentParser(description='Health Endpoint - 健康检查HTTP服务')
    parser.add_argument('--port', type=int, default=8080)
    parser.add_argument('--host', default='0.0.0.0')
    parser.add_argument('--once', action='store_true', help='只输出一次状态，不启动服务')
    args = parser.parse_args()

    endpoint = HealthEndpoint(port=args.port, host=args.host)

    if args.once:
        print(json.dumps(endpoint._collect_full_status(), indent=2, ensure_ascii=False, default=str))
    else:
        endpoint.start()
        print(f"Health endpoints available:")
        print(f"  http://{args.host}:{args.port}/health")
        print(f"  http://{args.host}:{args.port}/metrics")
        print(f"  http://{args.host}:{args.port}/status")
        print(f"  http://{args.host}:{args.port}/truth")
        print(f"  http://{args.host}:{args.port}/config")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            endpoint.stop()


if __name__ == '__main__':
    main()
