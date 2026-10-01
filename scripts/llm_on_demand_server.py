#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
llm_on_demand_server.py — 云服务器 CPU 推理自治内核 · 按需拉起网关
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | 2026-10-01
技术集成批次: INTEGRATE-20261001-AIFILM-TECH → 按需启动模式②

功能:
  1. 平时零进程常驻(本网关仅占 ~20MB), 模型进程按需拉起
  2. HTTP 请求到来 → 检测模型进程 → 未存活则拉起后端 → 等待就绪 → 转发推理 → 返回
  3. 空闲超时自动 kill 模型进程, 释放内存(默认 5 分钟)
  4. 冷热分层: 热模型常驻(keep_alive=true) / 冷模型按需(keep_alive=false)
  5. 完整日志: 启动/加载/推理/释放/错误 全记录

后端支持(通过 config 切换):
  - ollama        : ollama serve + ollama run (推荐, 最简单)
  - llama_cpp     : llama-server -m <model> (llama.cpp 官方 server)
  - openai_compat : 任意 OpenAI 兼容 API (仅转发, 不拉起)

依赖: 纯 Python 标准库, 零第三方依赖 (python3.8+)
"""
import json
import logging
import os
import signal
import subprocess
import sys
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# ============ 配置 ============
CONFIG_DEFAULT = {
    "listen_host": "127.0.0.1",
    "listen_port": 8777,
    "backend": "ollama",                 # ollama | llama_cpp | openai_compat
    "model": "qwen2.5:3b",               # ollama 模型名 / llama.cpp 模型路径
    "quant": "q4_K_M",                   # llama.cpp 量化标签(仅日志)
    "keep_alive": False,                 # True=热模型常驻 False=冷模型按需
    "idle_timeout_sec": 300,             # 空闲多少秒后自动释放模型进程
    "start_timeout_sec": 120,            # 拉起模型进程的最大等待秒数
    "max_context": 8192,                 # 上下文长度
    "ollama_bin": "ollama",              # ollama 可执行文件路径(默认PATH, 可填绝对路径)
    "llama_server_bin": "llama-server",  # llama.cpp server 可执行文件路径
    "openai_compat_url": "http://127.0.0.1:8080/v1/chat/completions",
    "openai_compat_key": "none",
    "log_file": "/var/log/llm_on_demand.log" if os.path.exists("/var/log") else "/tmp/llm_on_demand.log"
}

CONFIG = dict(CONFIG_DEFAULT)
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "..", "config", "llm_on_demand_config.json")
if os.path.exists(CONFIG_PATH):
    try:
        with open(CONFIG_PATH) as f:
            CONFIG.update(json.load(f))
    except Exception as e:
        print(f"[warn] 配置读取失败({e}), 使用默认配置")

# ============ 日志 ============
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(CONFIG["log_file"], encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger("llm-ondemand")

# ============ 模型进程管理 ============
class ModelProcess:
    """模型进程生命周期管理: 按需拉起 / 空闲释放 / 健康探测"""
    def __init__(self, cfg):
        self.cfg = cfg
        self.proc = None          # subprocess.Popen
        self.lock = threading.Lock()
        self.last_use = 0.0
        self.ready_port = None    # 后端就绪端口(ollama:11434 / llama:8080)
        self.state = "stopped"    # stopped | starting | ready

    # ---------- 拉起 ----------
    def start(self):
        with self.lock:
            if self.state == "ready" and self.proc and self.proc.poll() is None:
                return True
            if self.state == "starting":
                return self._wait_ready()
            log.info(f"按需拉起模型进程 backend={self.cfg['backend']} model={self.cfg['model']}")
            self.state = "starting"
            try:
                if self.cfg["backend"] == "ollama":
                    self._start_ollama()
                elif self.cfg["backend"] == "llama_cpp":
                    self._start_llama_cpp()
                else:
                    self.state = "ready"  # openai_compat 为远端转发, 无本地进程
                    return True
            except Exception as e:
                log.error(f"拉起失败: {e}")
                self.state = "stopped"
                return False
            ok = self._wait_ready()
            if ok:
                log.info(f"模型就绪 model={self.cfg['model']} backend_port={self.ready_port}")
            return ok

    def _start_ollama(self):
        bin_path = self.cfg["ollama_bin"]
        # 若 ollama serve 已在运行则复用, 否则拉起
        if not self._probe("http://127.0.0.1:11434/api/tags"):
            subprocess.Popen([bin_path, "serve"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.ready_port = 11434
        # 检查模型是否已本地存在(避免对已导入/已拉取的模型重复 pull)
        try:
            with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=5) as r:
                tags = json.loads(r.read().decode())
                local = {m["name"] for m in tags.get("models", [])}
            if self.cfg["model"] in local:
                log.info(f"模型已本地存在, 跳过 pull: {self.cfg['model']}")
                return
        except Exception:
            pass
        # 预热: 拉取模型(不存在时才拉)
        subprocess.run([bin_path, "pull", self.cfg["model"]],
                       timeout=self.cfg["start_timeout_sec"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def _start_llama_cpp(self):
        self.ready_port = 8080
        cmd = [
            self.cfg["llama_server_bin"],
            "-m", self.cfg["model"],
            "--port", "8080",
            "--ctx-size", str(self.cfg["max_context"]),
        ]
        if self.cfg["quant"]:
            cmd += ["--alias", self.cfg["model"]]
        self.proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )

    def _wait_ready(self):
        deadline = time.time() + self.cfg["start_timeout_sec"]
        while time.time() < deadline:
            if self.cfg["backend"] == "ollama":
                if self._probe(f"http://127.0.0.1:{self.ready_port}/api/tags"):
                    self.state = "ready"
                    return True
            elif self.cfg["backend"] == "llama_cpp":
                if self.proc and self.proc.poll() is not None:
                    log.error("llama-server 进程退出")
                    self.state = "stopped"
                    return False
                if self._probe(f"http://127.0.0.1:{self.ready_port}/health"):
                    self.state = "ready"
                    return True
            time.sleep(2)
        log.error("等待模型就绪超时")
        self.state = "stopped"
        return False

    @staticmethod
    def _probe(url):
        try:
            with urllib.request.urlopen(url, timeout=3) as r:
                return r.status == 200
        except Exception:
            return False

    # ---------- 推理 ----------
    def infer(self, messages, **kw):
        self.last_use = time.time()
        if self.cfg["backend"] == "ollama":
            return self._infer_ollama(messages, **kw)
        if self.cfg["backend"] == "llama_cpp":
            return self._infer_llama_cpp(messages, **kw)
        return self._infer_openai_compat(messages, **kw)

    def _infer_ollama(self, messages, **kw):
        prompt = messages[-1]["content"] if messages else ""
        body = {"model": self.cfg["model"], "prompt": prompt, "stream": False,
                "options": {"num_ctx": self.cfg["max_context"]}}
        body.update(kw)
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.ready_port}/api/generate",
            data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.loads(r.read().decode())

    def _infer_llama_cpp(self, messages, **kw):
        payload = {"messages": messages, "max_tokens": kw.get("max_tokens", 1024),
                   "temperature": kw.get("temperature", 0.7)}
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.ready_port}/v1/chat/completions",
            data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.loads(r.read().decode())

    def _infer_openai_compat(self, messages, **kw):
        payload = {"model": self.cfg["model"], "messages": messages}
        payload.update(kw)
        req = urllib.request.Request(
            self.cfg["openai_compat_url"], data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {self.cfg['openai_compat_key']}"})
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.loads(r.read().decode())

    # ---------- 释放 ----------
    def release(self):
        with self.lock:
            if self.proc and self.proc.poll() is None:
                log.info(f"空闲超时, 释放模型进程 model={self.cfg['model']}")
                os.killpg(os.getpgid(self.proc.pid), signal.SIGTERM)
                try:
                    self.proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    self.proc.kill()
            self.proc = None
            self.state = "stopped"

    # ---------- 状态 ----------
    def stats(self):
        return {
            "state": self.state,
            "backend": self.cfg["backend"],
            "model": self.cfg["model"],
            "keep_alive": self.cfg["keep_alive"],
            "last_use": self.last_use,
            "idle_sec": int(time.time() - self.last_use) if self.last_use else -1,
            "proc_alive": bool(self.proc and self.proc.poll() is None)
        }


# ============ HTTP 服务 ============
model = ModelProcess(CONFIG)

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        log.info("HTTP %s %s", self.address_string(), fmt % args)

    def _send(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self._send(200, {"status": "ok", "state": model.state})
        elif self.path == "/stats":
            self._send(200, model.stats())
        elif self.path == "/stop":
            model.release()
            self._send(200, {"status": "released"})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path == "/v1/chat/completions":
            try:
                length = int(self.headers.get("Content-Length", 0))
                payload = json.loads(self.rfile.read(length).decode())
                messages = payload.get("messages", [])
                if not messages:
                    self._send(400, {"error": "messages required"})
                    return
                # 按需拉起(冷模型) 或 复用(热模型)
                if not model.cfg["keep_alive"]:
                    ok = model.start()
                    if not ok:
                        self._send(503, {"error": "model start failed"})
                        return
                result = model.infer(messages, **{k: v for k, v in payload.items() if k != "messages"})
                log.info(f"推理完成 messages={len(messages)} tokens_ok=True")
                self._send(200, result)
            except Exception as e:
                log.error(f"推理异常: {e}")
                self._send(500, {"error": str(e)})
        elif self.path == "/stop":
            model.release()
            self._send(200, {"status": "released"})
        else:
            self._send(404, {"error": "not found"})


def idle_reaper():
    """空闲回收线程: 定期检查, 冷模型空闲超时即释放"""
    while True:
        time.sleep(30)
        try:
            if (not model.cfg["keep_alive"] and model.state == "ready"
                    and model.last_use
                    and time.time() - model.last_use > model.cfg["idle_timeout_sec"]):
                model.release()
        except Exception as e:
            log.error(f"reaper异常: {e}")


def main():
    threading.Thread(target=idle_reaper, daemon=True).start()
    server = ThreadingHTTPServer((CONFIG["listen_host"], CONFIG["listen_port"]), Handler)
    log.info(f"按需推理网关已启动: http://{CONFIG['listen_host']}:{CONFIG['listen_port']}")
    log.info(f"配置: backend={CONFIG['backend']} model={CONFIG['model']} "
             f"keep_alive={CONFIG['keep_alive']} idle_timeout={CONFIG['idle_timeout_sec']}s")
    if CONFIG["keep_alive"]:
        log.info("热模型模式: 立即预热常驻")
        model.start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        model.release()
        server.shutdown()


if __name__ == "__main__":
    main()
