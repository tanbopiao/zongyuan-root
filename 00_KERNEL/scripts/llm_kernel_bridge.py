#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
llm_kernel_bridge.py — 自治内核 ↔ 按需算力 桥接器 v1.0
ZONGYUAN-ROOT 自治内核 · DID-BR-000002 · Ω₀⊂⊙∞⊂Ω
接入批次: LLM-ONDEMAND-20261001-B → 本地自治内核动力源接入

功能:
  1. 内核脚本(meta_cognition/truth_generator/evolve_closed_loop等)调用本桥接器获取推理
  2. 自动探测按需网关(127.0.0.1:8777), 网关未起则尝试拉起
  3. 推理失败自动重试(最多2次), 网关不可用返回结构化错误
  4. 冷模型模式: 调用即拉起, 空闲自动释放(内存最小负载)
  5. 内置内核专用prompt模板: 元法则提炼/真值评估/决策判断/内容生成

用法:
  python3 llm_kernel_bridge.py chat "你的问题"
  python3 llm_kernel_bridge.py refine "原始素材" --type meta_law
  python3 llm_kernel_bridge.py decide "决策问题" --threshold 80
  python3 llm_kernel_bridge.py status
"""
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request

GATEWAY = "http://127.0.0.1:8777"
MODEL = "qwen2.5:3b"
BRIDGE_PATH = os.path.dirname(os.path.abspath(__file__))
COLD_STORE = os.path.dirname(os.path.dirname(BRIDGE_PATH))  # 00_KERNEL/scripts → 冷存储根
GATEWAY_SCRIPT = os.path.join(COLD_STORE, "scripts", "llm_on_demand_server.py")

# 内核专用 prompt 模板
TEMPLATES = {
    "refine": (
        "你是一位元法则提炼专家。从以下素材中提炼稳定、可复用的真值规则，"
        "按JSON格式输出: {{'truth_type': 'meta_law|rule|decision|asset|risk', "
        "'title': '简短标题', 'content': '规则正文', 'risk_tag': 'low|medium|high'}}。"
        "素材如下:\n{source}"
    ),
    "decide": (
        "你是一位自主进化决策评估专家。判断以下方案是否值得执行, 输出百分制评分(0-100)与简短理由。"
        "评分<80则建议不执行, >=80建议执行。JSON输出: {{'score': 0, 'verdict': 'execute|reject', "
        "'reason': '一句话理由'}}。方案如下:\n{source}"
    ),
    "generate": (
        "你是一位技术文档写作者。根据要求生成结构化内容, 输出精炼、可落地的文本。要求如下:\n{source}"
    ),
}


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%S+0800", time.localtime())


# ---------- 网关探测 ----------
def gateway_alive() -> bool:
    try:
        with urllib.request.urlopen(GATEWAY + "/health", timeout=3) as r:
            return r.status == 200
    except Exception:
        return False


def ensure_gateway():
    """网关未运行则拉起(冷启动网关进程)"""
    if gateway_alive():
        return True
    if not os.path.exists(GATEWAY_SCRIPT):
        return False
    try:
        subprocess.Popen(
            ["python3", GATEWAY_SCRIPT],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        # 等待网关就绪(最多15秒)
        deadline = time.time() + 15
        while time.time() < deadline:
            if gateway_alive():
                return True
            time.sleep(1)
    except Exception:
        pass
    return False


# ---------- 推理 ----------
def chat(prompt: str, max_retries: int = 2) -> dict:
    if not ensure_gateway():
        return {"ok": False, "error": "gateway_unavailable",
                "msg": "按需网关未运行且无法拉起"}
    payload = {"model": MODEL, "messages": [{"role": "user", "content": prompt}],
               "stream": False}
    for attempt in range(max_retries + 1):
        try:
            req = urllib.request.Request(
                GATEWAY + "/v1/chat/completions",
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=300) as r:
                data = json.loads(r.read().decode())
            resp = data.get("response", "")
            if not resp and data.get("message"):
                resp = data["message"].get("content", "")
            return {"ok": True, "response": resp, "attempt": attempt + 1,
                    "model": MODEL, "ts": now()}
        except Exception as e:
            if attempt < max_retries:
                time.sleep(2)
                continue
            return {"ok": False, "error": str(e), "attempt": attempt + 1,
                    "msg": "推理失败(网关可能繁忙或模型未就绪)"}


def apply_template(tname: str, source: str) -> str:
    t = TEMPLATES.get(tname)
    if not t:
        return source
    return t.format(source=source)


# ---------- 内核专用调用 ----------
def refine(source: str, truth_type: str = "meta_law") -> dict:
    prompt = apply_template("refine", source)
    return chat(prompt)


def decide(source: str, threshold: int = 80) -> dict:
    r = chat(apply_template("decide", source))
    if not r["ok"]:
        return r
    # 尝试解析 JSON 评分(兼容单/双引号)
    try:
        import re
        m = re.search(r'\{[^{}]*"score"[^{}]*\}', r["response"]) or \
            re.search(r"\{[^{}]*'score'[^{}]*\}", r["response"])
        if m:
            j = json.loads(m.group(0).replace("'", '"'))
            r["score"] = int(j.get("score", 0))
            r["verdict"] = j.get("verdict", "reject")
            r["threshold"] = threshold
            r["pass"] = r["score"] >= threshold
    except Exception:
        r["score"] = None
        r["pass"] = None
    return r


def generate(source: str) -> dict:
    return chat(apply_template("generate", source))


def status() -> dict:
    gw = gateway_alive()
    st = {"gateway": "online" if gw else "offline", "model": MODEL, "ts": now()}
    if gw:
        try:
            with urllib.request.urlopen(GATEWAY + "/stats", timeout=3) as r:
                st["gateway_stats"] = json.loads(r.read().decode())
        except Exception:
            pass
    return st


# ---------- CLI ----------
def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd = sys.argv[1]
    if cmd == "status":
        print(json.dumps(status(), ensure_ascii=False, indent=1))
        return
    if cmd == "chat" and len(sys.argv) >= 3:
        print(json.dumps(chat(" ".join(sys.argv[2:])), ensure_ascii=False, indent=1))
        return
    if cmd == "refine" and len(sys.argv) >= 3:
        t = "meta_law"
        if "--type" in sys.argv:
            i = sys.argv.index("--type")
            if i + 1 < len(sys.argv):
                t = sys.argv[i + 1]
        print(json.dumps(refine(" ".join([a for a in sys.argv[2:] if not a.startswith("--") and a not in (t,)]), t),
                         ensure_ascii=False, indent=1))
        return
    if cmd == "decide" and len(sys.argv) >= 3:
        th = 80
        args = [a for a in sys.argv[2:] if not a.startswith("--")]
        if "--threshold" in sys.argv:
            i = sys.argv.index("--threshold")
            if i + 1 < len(sys.argv):
                try:
                    th = int(sys.argv[i + 1])
                except ValueError:
                    pass
        print(json.dumps(decide(" ".join(args), th), ensure_ascii=False, indent=1))
        return
    if cmd == "generate" and len(sys.argv) >= 3:
        print(json.dumps(generate(" ".join(sys.argv[2:])), ensure_ascii=False, indent=1))
        return
    print(f"未知命令: {cmd}")


if __name__ == "__main__":
    main()
