"""
LOIP 守护进程 v0.3
后台常驻运行，自动治理AI输出，提供健康检查端点。

核心能力：
1. 后台常驻运行（7×24）
2. 目录文件监听（新AI输出文件自动治理）
3. 定期健康检查（基线完整性、审计链、漂移率）
4. HTTP健康检查端点（/health, /metrics）
5. 治理结果自动归档

使用方式：
    from loip.daemon import LOIPDaemon
    daemon = LOIPDaemon(baseline_path='./baseline.json', watch_dir='./ai_outputs')
    daemon.start()  # 阻塞运行
    # 或 daemon.start(blocking=False) 后台运行
"""
import os
import json
import time
import hashlib
import threading
import signal
from datetime import datetime
from typing import Any, Dict, Optional
from http.server import HTTPServer, BaseHTTPRequestHandler

from .sdk import LOIP

__version__ = "0.3.0"


class HealthHandler(BaseHTTPRequestHandler):
    """健康检查HTTP处理器"""
    daemon_ref = None  # 由守护进程设置

    def do_GET(self):
        if self.path == '/health':
            self._send_json(self.daemon_ref.health_check())
        elif self.path == '/metrics':
            self._send_json(self.daemon_ref.get_metrics())
        elif self.path == '/status':
            self._send_json(self.daemon_ref.get_status())
        else:
            self.send_response(404)
            self.end_headers()

    def _send_json(self, data: Dict):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass  # 静默HTTP日志


class LOIPDaemon:
    """LOIP守护进程"""

    def __init__(self, baseline_path: str, audit_dir: str = "./loip_audit",
                 watch_dir: Optional[str] = None, health_port: int = 8090,
                 health_check_interval: int = 60, backend: str = "auto"):
        """
        初始化守护进程
        :param baseline_path: 基线文件路径
        :param audit_dir: 审计日志目录
        :param watch_dir: 监听目录（新文件自动治理），None则不监听
        :param health_port: 健康检查HTTP端口
        :param health_check_interval: 健康检查间隔（秒）
        :param backend: 检测后端
        """
        self.loip = LOIP(baseline_path, audit_dir, backend=backend)
        self.watch_dir = watch_dir
        self.health_port = health_port
        self.health_check_interval = health_check_interval

        self.running = False
        self.start_time = None
        self.processed_count = 0
        self.blocked_count = 0
        self.health_checks = 0
        self.last_health_check = None
        self.watch_thread = None
        self.health_thread = None
        self.http_server = None
        self._processed_files = set()

        # 注册信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def start(self, blocking: bool = True):
        """启动守护进程"""
        self.running = True
        self.start_time = datetime.now().isoformat()

        print(f"[LOIP Daemon] 启动中...")
        print(f"[LOIP Daemon] 版本: {__version__}")
        print(f"[LOIP Daemon] 基线: {self.loip.baseline.data['baseline_id']}")
        print(f"[LOIP Daemon] 锁档状态: {'已锁档' if self.loip.baseline.is_locked() else '未锁档'}")
        print(f"[LOIP Daemon] 健康检查端口: {self.health_port}")

        # 启动健康检查HTTP服务
        self._start_health_server()

        # 启动文件监听（如果配置了）
        if self.watch_dir:
            os.makedirs(self.watch_dir, exist_ok=True)
            self.watch_thread = threading.Thread(target=self._watch_loop, daemon=True)
            self.watch_thread.start()
            print(f"[LOIP Daemon] 文件监听: {self.watch_dir}")

        # 启动定期健康检查
        self.health_thread = threading.Thread(target=self._health_loop, daemon=True)
        self.health_thread.start()

        print(f"[LOIP Daemon] 启动完成，运行中...")

        if blocking:
            try:
                while self.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                self.stop()

    def stop(self):
        """停止守护进程"""
        self.running = False
        if self.http_server:
            self.http_server.shutdown()
        print(f"[LOIP Daemon] 已停止。处理文件: {self.processed_count}, 阻断: {self.blocked_count}")

    def _signal_handler(self, signum, frame):
        print(f"\n[LOIP Daemon] 收到信号 {signum}，正在停止...")
        self.stop()

    def _start_health_server(self):
        """启动健康检查HTTP服务"""
        try:
            HealthHandler.daemon_ref = self
            self.http_server = HTTPServer(('0.0.0.0', self.health_port), HealthHandler)
            thread = threading.Thread(target=self.http_server.serve_forever, daemon=True)
            thread.start()
            print(f"[LOIP Daemon] 健康检查: http://0.0.0.0:{self.health_port}/health")
        except Exception as e:
            print(f"[LOIP Daemon] 健康检查端口启动失败: {e}")

    def _watch_loop(self):
        """文件监听循环"""
        while self.running:
            try:
                if os.path.exists(self.watch_dir):
                    for filename in os.listdir(self.watch_dir):
                        filepath = os.path.join(self.watch_dir, filename)
                        if (os.path.isfile(filepath)
                                and filename.endswith(('.txt', '.json', '.md'))
                                and filepath not in self._processed_files):
                            self._process_file(filepath)
                            self._processed_files.add(filepath)
            except Exception as e:
                print(f"[LOIP Daemon] 监听异常: {e}")
            time.sleep(2)

    def _process_file(self, filepath: str):
        """处理单个文件"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            # 解析JSON格式或纯文本
            if filepath.endswith('.json'):
                data = json.loads(content)
                user_input = data.get('user_input', '')
                ai_output = data.get('ai_output', content)
            else:
                user_input = ''
                ai_output = content

            # 执行治理
            result = self.loip.process(user_input, ai_output)
            self.processed_count += 1

            if result.get('blocked') or result['overall_risk'] == 'critical':
                self.blocked_count += 1

            # 保存治理结果
            output_path = filepath + '.loip_processed'
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "original": ai_output[:500],
                    "corrected": result['corrected_output'][:500],
                    "risk": result['overall_risk'],
                    "drift_conflicts": result['drift_detection']['conflict_count'],
                    "hallucination_issues": result['hallucination_guard']['issue_count'],
                    "processed_at": datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)

            print(f"[LOIP Daemon] 已治理: {os.path.basename(filepath)} "
                  f"(风险:{result['overall_risk']}, 修正:{result['corrections_applied']})")

        except Exception as e:
            print(f"[LOIP Daemon] 处理文件失败 {filepath}: {e}")

    def _health_loop(self):
        """定期健康检查循环"""
        while self.running:
            try:
                self.health_checks += 1
                self.last_health_check = datetime.now().isoformat()
                # 执行完整性校验
                integrity = self.loip.verify_integrity()
                if not integrity['baseline_integrity']['integrity']:
                    print(f"[LOIP Daemon] 警告: 基线完整性校验失败!")
            except Exception as e:
                print(f"[LOIP Daemon] 健康检查异常: {e}")
            time.sleep(self.health_check_interval)

    def health_check(self) -> Dict[str, Any]:
        """执行健康检查并返回结果"""
        integrity = self.loip.verify_integrity()
        return {
            "status": "healthy",
            "version": __version__,
            "uptime": self._get_uptime(),
            "baseline_locked": self.loip.baseline.is_locked(),
            "baseline_integrity": integrity['baseline_integrity']['integrity'],
            "audit_chain_valid": all(v["valid"] for v in integrity['audit_hash_chain'].values()),
            "processed_count": self.processed_count,
            "blocked_count": self.blocked_count,
            "health_checks": self.health_checks,
            "last_health_check": self.last_health_check
        }

    def get_metrics(self) -> Dict[str, Any]:
        """获取治理指标"""
        drift_stats = self.loip.drift_detector.get_drift_stats()
        hallu_stats = self.loip.hallucination_guard.get_stats()
        return {
            "processed_total": self.processed_count,
            "blocked_total": self.blocked_count,
            "drift_total": drift_stats["total_drifts"],
            "hallucination_total": hallu_stats["total_interceptions"],
            "drift_by_type": drift_stats["drifts_by_type"],
            "uptime_seconds": self._get_uptime_seconds()
        }

    def get_status(self) -> Dict[str, Any]:
        """获取完整状态"""
        return {
            "running": self.running,
            "start_time": self.start_time,
            "uptime": self._get_uptime(),
            "loip_status": self.loip.get_status(),
            "watch_dir": self.watch_dir,
            "health_port": self.health_port
        }

    def _get_uptime(self) -> str:
        if not self.start_time:
            return "0s"
        start = datetime.fromisoformat(self.start_time)
        delta = datetime.now() - start
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours}h{minutes}m{seconds}s"

    def _get_uptime_seconds(self) -> int:
        if not self.start_time:
            return 0
        start = datetime.fromisoformat(self.start_time)
        return int((datetime.now() - start).total_seconds())


def main():
    """命令行启动守护进程"""
    import argparse
    parser = argparse.ArgumentParser(description="LOIP 守护进程")
    parser.add_argument("--baseline", default="./loip_baseline.json", help="基线文件路径")
    parser.add_argument("--audit-dir", default="./loip_audit", help="审计目录")
    parser.add_argument("--watch-dir", default=None, help="监听目录")
    parser.add_argument("--health-port", type=int, default=8090, help="健康检查端口")
    parser.add_argument("--interval", type=int, default=60, help="健康检查间隔(秒)")
    parser.add_argument("--backend", default="auto", choices=["auto", "keyword", "semantic"])
    args = parser.parse_args()

    daemon = LOIPDaemon(
        baseline_path=args.baseline,
        audit_dir=args.audit_dir,
        watch_dir=args.watch_dir,
        health_port=args.health_port,
        health_check_interval=args.interval,
        backend=args.backend
    )
    daemon.start(blocking=True)


if __name__ == "__main__":
    main()
