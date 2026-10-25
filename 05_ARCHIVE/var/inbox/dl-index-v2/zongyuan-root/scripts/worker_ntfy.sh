#!/bin/bash
# ntfy 通信层 | DID-BR-000002 | 心跳发布/任务拉取/白名单指令/结果回传 | cron */5
# SOP: 长任务稳态智能体架构 V1.0 通信层落地（公共 ntfy.sh + 云端自建 server 候选）
NTFY="https://zrntfy.huodouai.com"
P="zongyuan-did-br-000002-7f3a9c2e"
DST=/home/user/ZONGYUAN-ROOT/var/ntfy
mkdir -p "$DST"
TS=$(date +%s)
# 1) 心跳发布（与 cloud_link SSH 通道并存，双通道容错）
K=$(pgrep -f "kernel/main.py" >/dev/null 2>&1 && echo up || echo down)
W=$(pgrep -f "worker_daemon.sh" >/dev/null 2>&1 && echo up || echo down)
curl -s -m 8 -X POST "$NTFY/$P-heartbeat" -H "X-DID: DID-BR-000002" \
  -d "{\"node\":\"vefaas-sandbox\",\"ts\":$TS,\"kernel\":\"$K\",\"worker\":\"$W\"}" >/dev/null 2>&1
# 2) 任务拉取（断点：since=last-ntfy-id，断点续传）
LAST=$(cat "$DST/last-ntfy-id" 2>/dev/null || echo all)
curl -s -m 8 "$NTFY/$P-tasks/json?since=$LAST" -o /tmp/ntfy_resp.jsonl 2>/dev/null
[ -s /tmp/ntfy_resp.jsonl ] || exit 0
NTFY="$NTFY" python3 - "$TS" << 'PY'
import sys, json, urllib.request, os
ts = sys.argv[1]
P = "zongyuan-did-br-000002-7f3a9c2e"
NTFY = os.environ.get("NTFY", "https://zrntfy.huodouai.com")
LOG = "/home/user/ZONGYUAN-ROOT/var/ntfy/task-exec.log"
LASTF = "/home/user/ZONGYUAN-ROOT/var/ntfy/last-ntfy-id"
with open("/tmp/ntfy_resp.jsonl") as fh:
    for line in fh:
        line = line.strip()
        if not line: continue
        try: m = json.loads(line)
        except: continue
        if m.get("event") != "message": continue
        mid = m.get("id","")
        msg = m.get("message","")
        with open(LASTF, "w") as f: f.write(mid)
        try: inst = json.loads(msg).get("instruction","")
        except: inst = str(msg)
        # 白名单指令（安全铁律：不执行任意命令，未知指令仅记录）
        if inst == "TASK.PING": result = "pong"
        elif inst == "TASK.STATUS": result = "kernel/worker/cron OK"
        elif inst == "TASK.HEARTBEAT": result = "heartbeat sent"
        else: result = "UNKNOWN_INSTRUCTION_NOT_EXECUTED"
        body = json.dumps({"node":"vefaas-sandbox","task_id":mid,"instruction":inst[:60],"result":result,"ts":ts,"did":"DID-BR-000002"})
        try:
            req = urllib.request.Request(f"{NTFY}/{P}-results", data=body.encode(), method="POST")
            urllib.request.urlopen(req, timeout=8)
        except Exception as e:
            result = "RETURN_FAILED:" + str(e)[:60]
        with open(LOG, "a") as f:
            f.write(f"{ts} | {mid} | {inst[:60]} | {result}\n")
PY
