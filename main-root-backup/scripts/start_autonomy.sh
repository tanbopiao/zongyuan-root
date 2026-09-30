#!/bin/bash
# ZONGYUAN-ROOT 自治进程启动守护
# DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
KROOT="/home/user/.doubao/agent_mode/workspace/.user_skills/kunlun-autonomous-system/ZONGYUAN-ROOT"
cd "$KROOT"

# 检查并启动heartbeat
if ! pgrep -f "heartbeat_v2.py" > /dev/null 2>&1; then
  nohup python3 scripts/heartbeat_v2.py >> logs/heartbeat.log 2>&1 &
  echo "[$(date)] heartbeat_v2 启动" >> logs/autonomy_guard.log
fi

# 检查并启动op_poller
if ! pgrep -f "op_poller.py" > /dev/null 2>&1; then
  nohup python3 scripts/op_poller.py >> logs/op_poller.log 2>&1 &
  echo "[$(date)] op_poller 启动" >> logs/autonomy_guard.log
fi
