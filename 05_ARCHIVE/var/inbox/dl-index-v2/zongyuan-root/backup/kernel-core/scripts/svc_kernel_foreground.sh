#!/bin/bash
# supervisor 前台 wrapper：kernel 主进程（保持 kernel_launch.sh status/stop 协议兼容）
ROOT="/home/user/Doubao/chats/38412149511142658/zongyuan-kernel"
export ZONGYUAN_PORT_BRAIN_PROXY=9081
export ZONGYUAN_PORT_BRAIN_ROUTER=9082
export ZONGYUAN_PORT_CAUSAL=9092
mkdir -p "$ROOT/var/run"
echo $$ > "$ROOT/var/run/kernel.pid"
exec /usr/bin/python3 "$ROOT/kernel/main.py"
