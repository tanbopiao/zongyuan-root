"""可观测性: 全链路日志 / 推理轨迹 / 阈值超限日志 / 熔断事件日志 / 面板数据接口.

- EventLogger: logs/events.jsonl (每事件一行, 分级/类型/详情/时间戳)
- TrajectoryLogger: logs/trajectory.jsonl (推理轨迹留存)
- MetricsRegistry: 面板数据接口 snapshot() -> dict / serve(port) HTTP JSON
"""
from __future__ import annotations

import json
import os
import threading
import time


class EventLogger:
    """全链路事件日志 (含阈值超限与熔断事件)。"""

    def __init__(self, log_dir: str):
        self.dir = log_dir
        os.makedirs(self.dir, exist_ok=True)
        self.path = os.path.join(self.dir, "events.jsonl")
        self._lock = threading.RLock()

    def write(self, level: str, etype: str, detail: dict | None = None) -> None:
        rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
               "level": level, "type": etype, "detail": detail or {}}
        line = json.dumps(rec, ensure_ascii=False)
        with self._lock:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
            # 同步按级别分片, 便于运维 grep
            with open(os.path.join(self.dir, f"{level}.jsonl"), "a", encoding="utf-8") as f:
                f.write(line + "\n")

    def tail(self, n: int = 50) -> list[dict]:
        try:
            with open(self.path, encoding="utf-8") as f:
                lines = f.readlines()
            return [json.loads(x) for x in lines[-n:]]
        except FileNotFoundError:
            return []


class TrajectoryLogger:
    """推理语义轨迹链留存 (每步向量摘要/相似度/事件)。"""

    def __init__(self, log_dir: str):
        os.makedirs(log_dir, exist_ok=True)
        self.path = os.path.join(log_dir, "trajectory.jsonl")
        self._lock = threading.RLock()

    def write(self, record: dict) -> None:
        with self._lock:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def read_all(self) -> list[dict]:
        try:
            with open(self.path, encoding="utf-8") as f:
                return [json.loads(x) for x in f if x.strip()]
        except FileNotFoundError:
            return []


class MetricsRegistry:
    """可视化面板数据接口 (核心指标: 相似度/推理步数/资源消耗/熔断次数)。"""

    def __init__(self):
        self._lock = threading.RLock()
        self._gauges: dict[str, float] = {}
        self._counters: dict[str, int] = {}

    def gauge(self, name: str, value: float) -> None:
        with self._lock:
            self._gauges[name] = value

    def incr(self, name: str, n: int = 1) -> None:
        with self._lock:
            self._counters[name] = self._counters.get(name, 0) + n

    def snapshot(self) -> dict:
        with self._lock:
            return {"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                    "gauges": dict(self._gauges),
                    "counters": dict(self._counters)}

    def serve(self, host: str = "127.0.0.1", port: int = 8120) -> "threading.Thread":
        """可选: 起一个只读 JSON 接口 (GET /metrics) 供面板拉取。"""
        import http.server
        import socketserver

        registry = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                if self.path.rstrip("/") in ("", "/metrics"):
                    body = json.dumps(registry.snapshot(), ensure_ascii=False).encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                else:
                    self.send_response(404)
                    self.end_headers()

            def log_message(self, *args):     # 静默, 避免污染日志
                pass

        class Srv(socketserver.TCPServer):
            allow_reuse_address = True

        t = threading.Thread(target=lambda: Srv((host, port), Handler).serve_forever(),
                             daemon=True)
        t.start()
        return t
