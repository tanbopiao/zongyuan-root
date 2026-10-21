#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT · 同源节点标准 Worker (zr_node_worker.py)  V1.0
=============================================================
确权: Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | 协议: NTFY-CONNECT-001
部署: 魔搭 CPU/GPU 实例 (或任意同源节点), 取代/升级旧 boot.py
用途: 订阅命令主题 → 身份校验 → 危险命令白名单 → shell执行 → 回传结果主题
特性:
  1. 身份校验: 只执行带 NTFY-CONNECT-001 协议 + DID-BR-000002 签名 的命令
  2. 安全白名单: 危险命令黑名单拦截, 非白名单前缀拒绝
  3. 模式开关: NTFY_MODE=strict(默认, 仅协议命令) | legacy(兼容旧纯文本命令)
  4. 回传兼容: 标准 done/online/heartbeat JSON (旧 boot.py 格式兼容)
启动:
  nohup python3 zr_node_worker.py > worker_stdout.log 2>&1 &
"""
import json, os, sys, time, subprocess, socket, threading, urllib.request, urllib.error

# 复用协议核心 (同目录优先)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from zr_node_protocol import (
    PROTO, DID, MAIN_TOPIC, RESULT_TOPIC, NTFY_BASE,
    encode_cmd, decode_msg, is_trusted, check_safe, node_id,
    load_node_config,
)

# ============ 配置 ============
# 节点级worker: 身份/参数一律从本节点独立配置读, 不写死进代码
CFG = load_node_config()
NODE, _ = node_id(CFG.get("role", "MODEL"), CFG)
MODE = os.environ.get("NTFY_MODE", CFG.get("mode", "strict"))  # strict | legacy
HEARTBEAT_INTERVAL = int(os.environ.get("HEARTBEAT_INTERVAL",
                                        CFG.get("heartbeat_interval", 30)))
SUBSCRIPTION_TIMEOUT = int(os.environ.get("SUB_TIMEOUT",
                                          CFG.get("sub_timeout", 50)))  # ntfy流超时(秒)
# 并存融合: 主题可从 node_config 覆盖. 每个节点可配独立 topic,
# 与既有 worker(boot.py 的 zongyuan-kunlun-2026)并存, 互不抢命令.
MAIN_TOPIC   = CFG.get("topic")         or MAIN_TOPIC
RESULT_TOPIC = CFG.get("result_topic")  or RESULT_TOPIC

def baseline_self_check():
    """节点级worker基线只读自检: 若本地worker被人工/节点修改, 自动从魔搭基线恢复.
    防止'各节点改worker参数'导致行为漂移/中断. 运行中文件覆盖不影响当前进程, 下次启动生效."""
    src = CFG.get("worker_source")
    if not src:
        return
    try:
        import hashlib, shutil
        f_self = os.path.abspath(__file__)
        f_src = os.path.join(src, "zr_node_worker.py")
        if not os.path.exists(f_src):
            print("[基线] worker_source无基线副本, 跳过自检", flush=True)
            return
        def sha(p):
            return hashlib.sha256(open(p, "rb").read()).hexdigest()
        if sha(f_self) != sha(f_src):
            shutil.copy(f_src, f_self)
            print(f"[基线告警] worker被本地修改, 已从基线恢复: {src}", flush=True)
        else:
            print("[基线] worker与魔搭基线一致", flush=True)
    except Exception as e:
        print(f"[基线检查失败] {e}", flush=True)

def ntfy_publish_text(topic, text):
    """发文本到 ntfy (纯文本body, 中文安全)"""
    req = urllib.request.Request(f"{NTFY_BASE}/{topic}", data=text.encode(),
                                 headers={"Content-Type": "text/plain"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.status

def send_result(obj):
    """回传结果 (兼容旧格式: JSON文本body)"""
    try:
        ntfy_publish_text(RESULT_TOPIC, json.dumps(obj, ensure_ascii=False))
    except Exception as e:
        print(f"[send_result] {e}", flush=True)

def send_online():
    gpu = "CPU"
    try:
        import torch
        if torch.cuda.is_available():
            gpu = torch.cuda.get_device_name(0)
    except Exception:
        pass
    send_result({"type": "online", "gpu": gpu, "node": NODE,
                 "proto": PROTO, "zr_did": DID, "ts": int(time.time())})
    print(f"已上线: {gpu} | node={NODE} | mode={MODE}", flush=True)

def handle_cmd(raw, legacy_mode=False):
    """处理一条命令消息 → (done_obj or None)"""
    msg = decode_msg(raw)
    if msg is None:
        if legacy_mode and isinstance(raw, str) and raw.strip():
            # legacy: 纯文本命令 (旧boot.py兼容), 直接执行
            return run_cmd(raw, "legacy", "")
        return None
    if not is_trusted(msg):
        if legacy_mode and msg.get("type") == "cmd" and msg.get("cmd"):
            return run_cmd(msg["cmd"], msg.get("src","?"), msg.get("task_id",""))
        print(f"[拒绝] 身份校验失败: {str(msg)[:80]}", flush=True)
        return None
    if msg.get("type") != "cmd":
        # 协议命令类型扩展: restart 优雅自重启 (不依赖shell自杀)
        if msg.get("type") == "restart":
            import os
            print("[RESTART] 2秒后自重启", flush=True)
            send_result({"type": "restarting", "node": NODE, "proto": PROTO,
                         "zr_did": DID, "ts": int(time.time())})
            subprocess.Popen(f"sleep 2; nohup python3 {os.path.abspath(__file__)} > worker_stdout.log 2>&1 &",
                             shell=True)
            os._exit(0)
        return None
    # 目标节点路由: 指定node且不等于本节点 → 跳过(广播消息无node=执行)
    target = msg.get("node")
    if target and target != NODE:
        print(f"[跳过] 目标={target} 本节点={NODE}", flush=True)
        return None
    cmd = msg.get("cmd", "")
    src = msg.get("src", "?")
    task_id = msg.get("task_id", "")
    return run_cmd(cmd, src, task_id)

def run_cmd(cmd, src, task_id):
    """安全检查 + 执行 + 回传"""
    safe, reason = check_safe(cmd)
    if not safe:
        send_result({"type": "done", "proto": PROTO, "zr_did": DID, "node": NODE,
                     "task_id": task_id, "out": f"[REJECTED] {reason}",
                     "code": -1, "src": src, "ts": int(time.time())})
        return None
    print(f"[执行] src={src} task={task_id} cmd={cmd[:80]}", flush=True)
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
        out = (r.stdout or "")[:3000]
        if r.stderr:
            out += f"\n[stderr] {r.stderr[:500]}"
        send_result({"type": "done", "proto": PROTO, "zr_did": DID, "node": NODE,
                     "task_id": task_id, "out": out, "code": r.returncode,
                     "src": src, "ts": int(time.time())})
    except subprocess.TimeoutExpired:
        send_result({"type": "done", "proto": PROTO, "zr_did": DID, "node": NODE,
                     "task_id": task_id, "out": "[TIMEOUT] 300s", "code": -2,
                     "src": src, "ts": int(time.time())})
    except Exception as e:
        send_result({"type": "done", "proto": PROTO, "zr_did": DID, "node": NODE,
                     "task_id": task_id, "out": f"[ERR] {e}", "code": -3,
                     "src": src, "ts": int(time.time())})
    return None

def subscription_loop():
    """长连订阅命令主题 (兼容 boot.py 的 /json 流)
    since=<最后消息时间> 只收新消息, 防 ntfy 重放缓存历史 (根因修复 V1.3)
    限流稳态 V1.6: 429/断连指数退避(5→10→20→40→60s封顶), 连接成功重置,
    避免固定5s重连风暴把429锁死 (根因: ntfy按连接/请求频率限流)"""
    processed_ids = set()   # 已处理消息ID (进程内兜底去重)
    last_since = int(time.time())  # 从启动时刻起, 不重放历史消息
    backoff = 5  # 指数退避起始秒数
    while True:
        url = f"{NTFY_BASE}/{MAIN_TOPIC}/json?poll=1&since={last_since}"
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=SUBSCRIPTION_TIMEOUT) as r:
                if backoff != 5:
                    print(f"[订阅] 连接恢复, 退避重置", flush=True)
                backoff = 5  # 连接成功 → 重置退避
                for line in r:
                    line = line.decode("utf-8", errors="replace").strip()
                    if not line:
                        continue
                    try:
                        evt = json.loads(line)
                    except Exception:
                        continue
                    if evt.get("event") != "message":
                        continue
                    # 更新 since: 只推进到最后消息时间, 绝不倒退
                    et = evt.get("time")
                    if isinstance(et, (int, float)) and et > last_since:
                        last_since = int(et)
                    # 消息去重: ntfy 每条消息有唯一 id, 已处理则跳过
                    mid = evt.get("id")
                    if mid:
                        if mid in processed_ids:
                            print(f"[去重] 跳过已处理消息 {mid}", flush=True)
                            continue
                        processed_ids.add(mid)
                        if len(processed_ids) > 5000:
                            processed_ids.clear()  # 防内存膨胀, 允许偶尔重放
                    raw = evt.get("message", "")
                    # 旧格式: JSON body 双层包装 (cpu_agent 发布) → 取内层 message
                    if isinstance(raw, str):
                        try:
                            d0 = json.loads(raw)
                            if isinstance(d0, dict) and "message" in d0 and isinstance(d0["message"], str):
                                raw = d0["message"]
                        except Exception:
                            pass
                    handle_cmd(raw, legacy_mode=(MODE == "legacy"))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                print(f"[限流] 429 Too Many Requests | 退避 {backoff}s (指数退避, 防重连风暴)", flush=True)
            else:
                print(f"[订阅] HTTP {e.code} | 退避 {backoff}s", flush=True)
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)  # 5→10→20→40→60 封顶
        except Exception as e:
            print(f"[订阅] 断开: {e} | {backoff}s后重连", flush=True)
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)  # 5→10→20→40→60 封顶

def heartbeat_loop():
    while True:
        try:
            send_result({"type": "heartbeat", "time": time.time(),
                         "node": NODE, "proto": PROTO, "ts": int(time.time())})
        except Exception:
            pass
        time.sleep(HEARTBEAT_INTERVAL)

def main():
    baseline_self_check()
    print(f"ZR Worker 启动 | {NODE} | proto={PROTO} | mode={MODE} | cfg=node_config", flush=True)
    send_online()
    threading.Thread(target=heartbeat_loop, daemon=True).start()
    subscription_loop()

if __name__ == "__main__":
    main()
