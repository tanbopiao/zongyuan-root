#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
auto_report_daemon.py · 全自动云端联邦记忆池上报 sidecar V1.0
================================================================
确权: Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | ZR-NODE-DC2E51C0
职责: 监听新旧 result 主题的 done/online 事件 → 自动上报云端中枢联邦记忆池
      (节点级token鉴权, 零人工介入, 全自动)
设计: 低频轮询(60s)拉两个result主题增量(since=last, 只推进不倒退),
      提取 done/online 事件上报云端; 指数退避(5→60s)防限流, 连接压力极小
部署: 实例持久层 /mnt/workspace/auto_report_daemon.py
用法: nohup python3 /mnt/workspace/auto_report_daemon.py >> /mnt/workspace/report_daemon.log 2>&1 &
"""
import json, time, urllib.request, urllib.error, os

TOKEN_FILE = "/mnt/workspace/.zr/node_token.env"
GATEWAY = "https://www.huodouai.com/api/report/truth"
TOPICS = ["zongyuan-kunlun-2026-result", "zongyuan-kunlun-2026-zr-result"]
NODE = "ZR-NODE-MODEL-dsw-223619"
DID = "DID-BR-000002"

def load_token():
    """读节点token(持久层, 600权限)"""
    try:
        for line in open(TOKEN_FILE):
            if line.strip().startswith("ZR_NODE_TOKEN="):
                return line.strip().split("=", 1)[1].strip()
    except Exception:
        pass
    return os.environ.get("ZR_NODE_TOKEN", "")

def report(key, value):
    """上报云端联邦记忆池 (X-Capture-Token + X-DID)"""
    token = load_token()
    if not token:
        return {"ok": False, "error": "no-token"}
    body = json.dumps({
        "truth_key": key, "truth_value": value,
        "source_node": NODE, "truth_type": "rule", "confidence": 0.95,
    }, ensure_ascii=False).encode()
    req = urllib.request.Request(GATEWAY, data=body, headers={
        "X-Capture-Token": token, "X-DID": DID, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {"ok": False, "error": str(e)[:120]}

last_since = {}   # topic -> since (只推进不倒退)
backoff = 5
print(f"[daemon] 启动 | 监听 {TOPICS} | 上报 {GATEWAY}", flush=True)
while True:
    for t in TOPICS:
        since = last_since.get(t, int(time.time()) - 120)  # 首次: 最近2分钟
        try:
            url = f"https://ntfy.sh/{t}/json?poll=1&since={since}"
            raw = urllib.request.urlopen(url, timeout=15).read().decode("utf-8", errors="replace")
            backoff = 5  # 连接成功 → 重置退避
            events = []
            max_t = since
            for line in raw.split("\n"):
                line = line.strip()
                if not line:
                    continue
                try:
                    m = json.loads(line)
                except Exception:
                    continue
                et = m.get("time")
                if isinstance(et, (int, float)) and et > max_t:
                    max_t = int(et)
                raw_msg = m.get("message", "")
                try:
                    d = json.loads(raw_msg)
                except Exception:
                    continue
                if not isinstance(d, dict):
                    continue
                if d.get("type") in ("done", "online"):
                    events.append(d)
            last_since[t] = max_t if max_t > since else since
            for d in events[-5:]:  # 每主题每轮最多5条, 防刷屏
                key = f"ZR-EVENT.{t}.{d.get('type')}.{int(time.time())}"
                val = json.dumps({
                    "topic": t, "type": d.get("type"),
                    "node": d.get("node", "?"), "code": d.get("code", "-"),
                    "out": str(d.get("out", ""))[:200],
                }, ensure_ascii=False)
                r = report(key, val)
                if r.get("ok"):
                    print(f"[daemon] 已上报 {key} seq={r.get('seq','?')}", flush=True)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                print(f"[daemon] 限流429 | 退避 {backoff}s", flush=True)
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)
        except Exception as e:
            print(f"[daemon] {t} 拉取失败: {str(e)[:60]} | 退避 {backoff}s", flush=True)
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)
    time.sleep(60)
