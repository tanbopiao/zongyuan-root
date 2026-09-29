#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ω-OP-SCHED 稳态智能 · 独立监控/检测服务
=========================================
ZONGYUAN-ROOT 元极恒一自治体系 · P4 稳态智能
DID: DID-BR-000002 | 本源根: Ω-TAN-7-001 | 溯源: Ω₀⊂⊙∞⊂Ω

零侵入生产调度服务(op_sched_api_server.py, 8072)，独立监听新端口(8073)，
提供稳态智能能力：自适应负载感知选worker、算子热升级、漂移检测、稳态健康总览。

端点：
  GET  /steady/status    稳态智能健康总览(漂移汇总/算子基线/最近告警)
  GET  /steady/drift     漂移检测详情
  GET  /steady/operators 已注册算子基线
  POST /steady/reload    算子热升级 {operator, new_version, source}
  GET  /health           健康检查

最优稳态：独立服务，不改生产核心；失败不影响既有调度；同源双锚点校验。
"""

import sys
import os
import json
import time
import threading
import argparse
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from adaptive_scheduler_enhance import (
        AdaptiveWorkerPicker,
        OperatorHotReload,
        DriftDetector,
    )
    _ENHANCE_AVAILABLE = True
except Exception as _e:
    _ENHANCE_AVAILABLE = False
    _ENHANCE_ERR = str(_e)

# 同源锚点
DID_ANCHOR = "DID-BR-000002"
ROOT_OMEGA_ANCHOR = "Ω-TAN-7-001"
TRACE_MARK = "Ω₀⊂⊙∞⊂Ω"

# 全局状态
PICKER = AdaptiveWorkerPicker()
DRIFT = DriftDetector()
HOTRELOAD = OperatorHotReload()
LAST_SCAN = None
ALERTS = []  # 漂移告警环形缓冲(最多50)


def _seed_baselines():
    defaults = {
        "P4真值对账": (0.97, 80, 0.3),
        "P7外部锚定": (0.98, 100, 0.3),
        "P1真值蒸馏": (0.95, 150, 0.5),
        "CausalToTruth": (0.96, 120, 0.4),
        "TruthToEvolution": (0.96, 110, 0.35),
        "Merkle校验": (0.99, 60, 0.2),
    }
    for op, (sr, lat, load) in defaults.items():
        DRIFT.set_baseline(op, success_rate=sr, avg_latency=lat, load=load)


def _drift_loop():
    """定时漂移巡检(60s)，超阈值写入告警缓冲"""
    global LAST_SCAN, ALERTS
    while True:
        try:
            summary = DRIFT.summary()
            LAST_SCAN = {**summary, "ts": datetime.now().isoformat()}
            # 收集红色/橙色告警
            for rep in DRIFT.detect_all():
                if rep.get("drift"):
                    ALERTS.append(rep)
            # 环形缓冲上限
            if len(ALERTS) > 50:
                ALERTS = ALERTS[-50:]
        except Exception:
            pass
        time.sleep(60)


class SteadyHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # 静默请求日志

    def _json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/health":
            self._json(200, {
                "status": "healthy", "service": "steady-intelligence",
                "enhance_available": _ENHANCE_AVAILABLE,
                "did": DID_ANCHOR, "root_omega": ROOT_OMEGA_ANCHOR, "trace": TRACE_MARK,
                "time": datetime.now().isoformat(),
            })
        elif path == "/steady/status":
            self._json(200, {
                "status": "ok",
                "enhance_available": _ENHANCE_AVAILABLE,
                "drift_summary": LAST_SCAN or DRIFT.summary(),
                "operator_count": len(DRIFT.baseline),
                "active_versions": HOTRELOAD.active_versions,
                "recent_alerts": len(ALERTS),
                "did": DID_ANCHOR, "trace": TRACE_MARK,
            })
        elif path == "/steady/drift":
            self._json(200, {
                "status": "ok",
                "drift_reports": DRIFT.detect_all(),
                "summary": DRIFT.summary(),
                "alerts": ALERTS[-10:],
                "trace": TRACE_MARK,
            })
        elif path == "/steady/operators":
            self._json(200, {
                "status": "ok",
                "operators": [
                    {"operator": op, "baseline": b}
                    for op, b in DRIFT.baseline.items()
                ],
                "trace": TRACE_MARK,
            })
        elif path == "/steady/alerts":
            self._json(200, {"status": "ok", "alerts": ALERTS[-10:], "count": len(ALERTS)})
        else:
            self._json(404, {"status": "not_found", "path": path})

    def do_POST(self):
        path = self.path.split("?")[0]
        if path == "/steady/reload":
            length = int(self.headers.get("Content-Length", 0))
            try:
                data = json.loads(self.rfile.read(length)) if length else {}
                op = data.get("operator")
                ver = data.get("new_version")
                src = data.get("source", "")
                if not op or not ver:
                    self._json(400, {"status": "error", "reason": "缺operator或new_version"})
                    return
                # 同源校验
                if data.get("did") != DID_ANCHOR or data.get("root_omega") != ROOT_OMEGA_ANCHOR:
                    self._json(403, {"status": "denied", "reason": "同源校验失败"})
                    return
                record = HOTRELOAD.reload(op, ver, src)
                self._json(200, {"status": "ok", "reload": record, "trace": TRACE_MARK})
            except Exception as e:
                self._json(500, {"status": "error", "reason": str(e)})
        else:
            self._json(404, {"status": "not_found", "path": path})


def main():
    parser = argparse.ArgumentParser(description="Ω-OP-SCHED 稳态智能服务")
    parser.add_argument("--port", type=int, default=8073, help="监听端口(默认8073)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="监听地址(默认127.0.0.1)")
    args = parser.parse_args()

    if not _ENHANCE_AVAILABLE:
        print(f"[稳态智能] 增强模块不可用: {_ENHANCE_ERR}")
        sys.exit(1)

    _seed_baselines()
    threading.Thread(target=_drift_loop, daemon=True).start()

    server = HTTPServer((args.host, args.port), SteadyHandler)
    print("=" * 56)
    print("  Ω-OP-SCHED 稳态智能服务")
    print(f"  DID: {DID_ANCHOR} | 本源根: {ROOT_OMEGA_ANCHOR}")
    print(f"  监听: {args.host}:{args.port}")
    print(f"  健康: http://localhost:{args.port}/health")
    print(f"  状态: http://localhost:{args.port}/steady/status")
    print(f"  漂移: http://localhost:{args.port}/steady/drift")
    print(f"  升级: POST http://localhost:{args.port}/steady/reload")
    print("=" * 56)
    server.serve_forever()


if __name__ == "__main__":
    main()
