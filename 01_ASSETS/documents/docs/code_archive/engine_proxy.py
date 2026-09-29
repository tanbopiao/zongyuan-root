#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
引擎集群 Socket 按需激活代理层 V1.0
DID: DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
功能: 轻量代理层，监听代理端口，转发到目标引擎端口，记录调用频率。
      第一阶段: 纯转发+监控（不休眠引擎）
      第二阶段: 空闲超时后可休眠引擎，请求到来时唤醒
用法:
  python3 engine_proxy.py --config proxy_config.json
  python3 engine_proxy.py --status
"""
import os
import sys
import json
import time
import socket
import threading
import argparse
import subprocess
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

# ---------- 常量 ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGS_DIR = os.path.join(BASE_DIR, "logs")
STATE_FILE = os.path.join(BASE_DIR, "proxy_state.json")
DEFAULT_CONFIG = os.path.join(BASE_DIR, "proxy_config.json")
DID = "DID-BR-000002"
TRACE = "Ω₀⊂⊙∞⊂Ω"
ADAPTIVE_CONFIG = {"enabled": False}  # 智能超时配置(从配置文件加载)
FORWARDER_REGISTRY = {}  # 引擎名->ProxyForwarder实例(用于API管理)


def log(msg, level="INFO"):
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{level}] {msg}"
    print(line)
    os.makedirs(LOGS_DIR, exist_ok=True)
    with open(os.path.join(LOGS_DIR, "engine_proxy.log"), "a") as f:
        f.write(line + "\n")


# ---------- 调用统计 ----------
class CallStats:
    def __init__(self):
        self.stats = {}  # engine_name -> {count, last_call, total_bytes}
        self.lock = threading.Lock()
        self._load()

    def _load(self):
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE) as f:
                    self.stats = json.load(f)
            except Exception:
                self.stats = {}

    def _save(self):
        with open(STATE_FILE, "w") as f:
            json.dump(self.stats, f, ensure_ascii=False, indent=2)

    def record(self, engine_name, bytes_transferred=0):
        with self.lock:
            if engine_name not in self.stats:
                self.stats[engine_name] = {"count": 0, "last_call": None, "total_bytes": 0, "first_seen": datetime.now().isoformat(), "call_history": []}
            s = self.stats[engine_name]
            s["count"] += 1
            s["last_call"] = datetime.now().isoformat()
            s["total_bytes"] += bytes_transferred
            # 保留最近100条调用时间戳(用于频率计算)
            if "call_history" not in s:
                s["call_history"] = []
            s["call_history"].append(datetime.now().isoformat())
            if len(s["call_history"]) > 100:
                s["call_history"] = s["call_history"][-100:]
            self._save()

    def get_recent_freq(self, engine_name, window_seconds=3600):
        """计算最近window_seconds内的调用频率(次/小时)"""
        s = self.get(engine_name)
        history = s.get("call_history", [])
        if not history:
            return 0
        now = datetime.now()
        count = 0
        for ts in history:
            try:
                t = datetime.fromisoformat(ts)
                if (now - t).total_seconds() <= window_seconds:
                    count += 1
            except Exception:
                pass
        return count

    def get(self, engine_name):
        return self.stats.get(engine_name, {})

    def all(self):
        return self.stats


stats = CallStats()


# ---------- TCP 转发代理 ----------
class ProxyForwarder(threading.Thread):
    """单个引擎的TCP转发代理"""
    def __init__(self, engine_config):
        super().__init__(daemon=True)
        self.name = engine_config["name"]
        self.proxy_port = engine_config["proxy_port"]
        self.target_host = engine_config.get("target_host", "127.0.0.1")
        self.target_port = engine_config["target_port"]
        self.idle_timeout = engine_config.get("idle_timeout", 300)  # 秒
        self.sleep_mode = engine_config.get("sleep_mode", False)  # 第二阶段
        self.engine_cmd = engine_config.get("engine_cmd", "")  # 唤醒命令
        self.engine_stop_cmd = engine_config.get("engine_stop_cmd", "")  # 休眠命令
        self.running = False
        self._is_sleeping = False

    def _wake_engine(self):
        """第二阶段: 唤醒休眠引擎"""
        if not self.sleep_mode or not self.engine_cmd:
            return
        if not self._is_sleeping:
            return  # 已在运行，无需唤醒
        log(f"唤醒引擎: {self.name} ({self.engine_cmd})")
        try:
            subprocess.Popen(self.engine_cmd, shell=True, cwd="/opt/ZONGYUAN-ROOT")
            time.sleep(2)  # 等待引擎启动
            self._is_sleeping = False
            log(f"引擎已唤醒: {self.name}")
        except Exception as e:
            log(f"唤醒失败: {e}", "ERROR")

    def _sleep_engine(self):
        """第二阶段: 空闲超时后休眠引擎"""
        if not self.sleep_mode or not self.engine_stop_cmd:
            return
        if self._is_sleeping:
            return  # 已休眠
        log(f"休眠引擎(空闲超时): {self.name} ({self.engine_stop_cmd})")
        try:
            subprocess.Popen(self.engine_stop_cmd, shell=True, cwd="/opt/ZONGYUAN-ROOT")
            time.sleep(1)
            self._is_sleeping = True
            log(f"引擎已休眠: {self.name}")
        except Exception as e:
            log(f"休眠失败: {e}", "ERROR")

    def _adaptive_timeout(self):
        """智能超时自适应: 根据调用频率动态调整idle_timeout"""
        global ADAPTIVE_CONFIG
        if not ADAPTIVE_CONFIG.get("enabled", False):
            return
        freq = stats.get_recent_freq(self.name, 3600)  # 最近1小时调用次数
        high = ADAPTIVE_CONFIG.get("high_freq_threshold", 5)
        low = ADAPTIVE_CONFIG.get("low_freq_threshold", 1)
        min_t = ADAPTIVE_CONFIG.get("min_timeout", 120)
        max_t = ADAPTIVE_CONFIG.get("max_timeout", 600)
        old_timeout = self.idle_timeout
        if freq >= high:
            # 高频引擎: 缩短超时，更快休眠(因为很快会被再次唤醒)
            self.idle_timeout = min_t
        elif freq <= low:
            # 低频引擎: 延长超时，避免频繁唤醒休眠
            self.idle_timeout = max_t
        else:
            # 中频: 保持默认
            self.idle_timeout = 300
        if self.idle_timeout != old_timeout:
            log(f"智能超时调整 [{self.name}]: 频率={freq}次/h, {old_timeout}s->{self.idle_timeout}s")

    def _idle_monitor(self):
        """空闲监控线程: 智能超时调整 + 超时休眠"""
        check_count = 0
        while self.running:
            time.sleep(30)  # 每30秒检查一次
            check_count += 1
            if not self.sleep_mode:
                continue
            # 每5次检查(2.5分钟)做一次智能超时调整
            if check_count % 5 == 0:
                self._adaptive_timeout()
            if self._is_sleeping:
                continue
            s = stats.get(self.name)
            last_call = s.get("last_call")
            if not last_call:
                continue
            try:
                last_time = datetime.fromisoformat(last_call)
                idle_seconds = (datetime.now() - last_time).total_seconds()
                if idle_seconds > self.idle_timeout:
                    self._sleep_engine()
            except Exception:
                pass

    def _pipe(self, src, dst, engine_name):
        """双向数据转发"""
        try:
            while True:
                data = src.recv(4096)
                if not data:
                    break
                dst.sendall(data)
                stats.record(engine_name, len(data))
        except Exception:
            pass
        finally:
            try:
                src.close()
            except Exception:
                pass
            try:
                dst.close()
            except Exception:
                pass

    def handle_client(self, client_sock):
        try:
            # 第二阶段: 如果引擎休眠，先唤醒
            if self.sleep_mode:
                self._wake_engine()
            # 连接目标引擎
            target = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            target.settimeout(10)
            target.connect((self.target_host, self.target_port))
            target.settimeout(None)
            # 双向转发
            t1 = threading.Thread(target=self._pipe, args=(client_sock, target, self.name), daemon=True)
            t2 = threading.Thread(target=self._pipe, args=(target, client_sock, self.name), daemon=True)
            t1.start()
            t2.start()
            t1.join()
            t2.join()
        except Exception as e:
            log(f"代理连接失败 [{self.name}]: {e}", "WARN")
            try:
                client_sock.close()
            except Exception:
                pass

    def run(self):
        self.running = True
        # 启动空闲监控线程（休眠模式下）
        if self.sleep_mode:
            threading.Thread(target=self._idle_monitor, daemon=True).start()
            log(f"空闲监控已启动 [{self.name}]: 超时={self.idle_timeout}s")
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            server.bind(("0.0.0.0", self.proxy_port))
            server.listen(50)
            log(f"代理启动 [{self.name}]: 0.0.0.0:{self.proxy_port} -> {self.target_host}:{self.target_port}")
            while self.running:
                client, _ = server.accept()
                threading.Thread(target=self.handle_client, args=(client,), daemon=True).start()
        except Exception as e:
            log(f"代理启动失败 [{self.name}]: {e}", "ERROR")
        finally:
            server.close()


# ---------- 状态HTTP服务 ----------
class StatusHandler(BaseHTTPRequestHandler):
    def _json_response(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/status":
            # 包含各引擎当前休眠状态和超时配置
            engines_data = stats.all()
            for name, fwd in FORWARDER_REGISTRY.items():
                if name in engines_data:
                    engines_data[name]["sleeping"] = fwd._is_sleeping
                    engines_data[name]["idle_timeout"] = fwd.idle_timeout
                    engines_data[name]["sleep_mode"] = fwd.sleep_mode
            data = {
                "service": "engine_proxy",
                "version": "V1.2",
                "did": DID,
                "trace": TRACE,
                "adaptive_timeout": ADAPTIVE_CONFIG,
                "engines": engines_data,
                "uptime": time.time() - START_TIME,
            }
            self._json_response(data)
        elif self.path.startswith("/api/engine/") and self.path.endswith("/sleep"):
            # A2E管理API: 强制休眠指定引擎
            name = self.path.split("/api/engine/")[1].split("/sleep")[0]
            fwd = FORWARDER_REGISTRY.get(name)
            if fwd and fwd.sleep_mode:
                fwd._sleep_engine()
                self._json_response({"success": True, "engine": name, "action": "sleep"})
            else:
                self._json_response({"success": False, "error": "engine not found or sleep_mode disabled"}, 404)
        elif self.path.startswith("/api/engine/") and self.path.endswith("/wake"):
            # A2E管理API: 强制唤醒指定引擎
            name = self.path.split("/api/engine/")[1].split("/wake")[0]
            fwd = FORWARDER_REGISTRY.get(name)
            if fwd and fwd.sleep_mode:
                fwd._wake_engine()
                self._json_response({"success": True, "engine": name, "action": "wake"})
            else:
                self._json_response({"success": False, "error": "engine not found"}, 404)
        elif self.path == "/visualize" or self.path == "/":
            # 可视化监控页面
            html_path = os.path.join(BASE_DIR, "visualize.html")
            if os.path.exists(html_path):
                with open(html_path, "r", encoding="utf-8") as f:
                    body = f.read().encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:
                self._json_response({"error": "visualize.html not found"}, 404)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # 静默


START_TIME = time.time()


# ---------- 主入口 ----------
def main():
    parser = argparse.ArgumentParser(description="引擎集群按需激活代理层")
    parser.add_argument("--config", default=DEFAULT_CONFIG, help="代理配置文件")
    parser.add_argument("--status", action="store_true", help="查看代理状态")
    parser.add_argument("--status-port", type=int, default=9200, help="状态HTTP端口")
    args = parser.parse_args()

    if args.status:
        # 查询运行中代理状态
        try:
            import urllib.request
            with urllib.request.urlopen(f"http://127.0.0.1:{args.status_port}/status", timeout=5) as r:
                print(r.read().decode("utf-8"))
        except Exception as e:
            print(f"代理未运行或不可达: {e}")
        return

    # 加载配置
    if not os.path.exists(args.config):
        print(f"配置文件不存在: {args.config}")
        print("请创建 proxy_config.json，格式见文档")
        sys.exit(1)

    with open(args.config) as f:
        config = json.load(f)

    engines = config.get("engines", [])
    if not engines:
        print("配置中无引擎")
        sys.exit(1)

    # 从配置读取状态端口（覆盖默认）
    if config.get("status_port"):
        args.status_port = config["status_port"]

    # 加载智能超时自适应配置
    global ADAPTIVE_CONFIG
    ADAPTIVE_CONFIG = config.get("adaptive_timeout", {"enabled": False})
    if ADAPTIVE_CONFIG.get("enabled"):
        log(f"智能超时自适应已启用: min={ADAPTIVE_CONFIG.get('min_timeout')}s, max={ADAPTIVE_CONFIG.get('max_timeout')}s")

    log(f"引擎代理层启动，共 {len(engines)} 个引擎代理")
    log(f"模式: {'休眠激活' if any(e.get('sleep_mode') for e in engines) else '监控转发(第一阶段)'}")

    # 启动各引擎代理并注册到全局注册表(用于API管理)
    global FORWARDER_REGISTRY
    forwarders = []
    for ec in engines:
        fwd = ProxyForwarder(ec)
        fwd.start()
        forwarders.append(fwd)
        FORWARDER_REGISTRY[ec["name"]] = fwd

    # 启动状态HTTP服务
    status_server = HTTPServer(("0.0.0.0", args.status_port), StatusHandler)
    status_thread = threading.Thread(target=status_server.serve_forever, daemon=True)
    status_thread.start()
    log(f"状态服务: http://0.0.0.0:{args.status_port}/status")

    # 主循环
    try:
        while True:
            time.sleep(60)
            # 每分钟输出一次统计摘要
            for name, s in stats.all().items():
                log(f"统计 [{name}]: 调用={s.get('count',0)}, 最后={s.get('last_call','N/A')}")
    except KeyboardInterrupt:
        log("收到中断信号，停止代理层")
        for fwd in forwarders:
            fwd.running = False
        status_server.shutdown()


if __name__ == "__main__":
    main()
