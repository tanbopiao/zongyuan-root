#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
boot_hardened.py · boot.py 最小健壮性加固版 V1.2
================================================
确权: Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | ZR-NODE-DC2E51C0
原则: 复用成果/融合并存/不替换不破坏 —— 本文件是既有 boot.py 的缺陷修复版:
      - 既有行为 100% 保留: 订阅旧主题 zongyuan-kunlun-2026, 纯文本命令当shell执行,
        结果回传 zongyuan-kunlun-2026-result (格式 {type,out,code})
      - 仅新增健壮性: 订阅 try/except + 指数退避(5→60s封顶, 连接成功重置),
        根治 "ntfy 429 限流 → 无异常处理 → 进程崩溃" 缺陷 (与 zr_node_worker V1.6 同策略)
      - 纯标准库(urllib), 无第三方依赖
部署: 替换 /mnt/workspace/OMEGA-BRAIN/boot.py (原版先备份 boot.py.orig)
用法: cd /mnt/workspace/OMEGA-BRAIN && nohup python3 boot.py > boot_stdout.log 2>&1 &
"""
import json, time, subprocess, urllib.request, urllib.error

T = "zongyuan-kunlun-2026"  # 旧生态命令主题 (与 zr_node_worker 新主题 -zr 并存隔离)
NTFY = "https://ntfy.sh"

def send(data):
    """回传结果主题 (与既有 boot.py 完全一致: {type,out,code})"""
    try:
        req = urllib.request.Request(f"{NTFY}/{T}-result", data=json.dumps(data).encode())
        urllib.request.urlopen(req, timeout=10)
    except Exception:
        pass

try:
    import torch
    gpu = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU"
except Exception:
    gpu = "CPU"
send({"type": "online", "gpu": gpu})
print(f"[boot] 已上线: {gpu}", flush=True)

backoff = 5  # 指数退避起始 (5→10→20→40→60 封顶)
last_since = int(time.time())  # 从启动时刻起, 不重放历史 (防ntfy缓存重放)
while True:
    try:
        send({"type": "heartbeat", "time": time.time()})
        url = f"{NTFY}/{T}/json?poll=1&since={last_since}"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=60) as r:
            if backoff != 5:
                print("[boot] 订阅恢复, 退避重置", flush=True)
            backoff = 5  # 连接成功 → 重置退避
            for line in r:
                line = line.decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                if d.get("event") != "message":
                    continue
                et = d.get("time")
                if isinstance(et, (int, float)) and et > last_since:
                    last_since = int(et)  # since 只推进, 绝不倒退
                cmd = d.get("message")
                if not cmd:
                    continue
                print(f"[boot] 执行: {str(cmd)[:60]}", flush=True)
                try:
                    res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
                    out = (res.stdout or "")[:1500]
                    if res.stderr:
                        out += f"\n[stderr] {res.stderr[:300]}"
                    send({"type": "done", "out": out, "code": res.returncode})
                except subprocess.TimeoutExpired:
                    send({"type": "done", "out": "[TIMEOUT] 300s", "code": -2})
                except Exception as e:
                    send({"type": "done", "out": f"[ERR] {e}", "code": -1})
    except urllib.error.HTTPError as e:
        if e.code == 429:
            print(f"[boot] 限流 429 | 退避 {backoff}s", flush=True)
        else:
            print(f"[boot] HTTP {e.code} | 退避 {backoff}s", flush=True)
        time.sleep(backoff)
        backoff = min(backoff * 2, 60)  # 5→10→20→40→60 封顶
    except Exception as e:
        print(f"[boot] 断开: {str(e)[:60]} | 退避 {backoff}s", flush=True)
        time.sleep(backoff)
        backoff = min(backoff * 2, 60)
