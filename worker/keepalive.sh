#!/bin/bash
# ZONGYUAN-ROOT 云端Worker保活: 每分钟检查,挂了自动拉起
if ! pgrep -f "worker_loop.py" > /dev/null 2>&1; then
    cd /home/user/Doubao/chats/38439832899843586/worker
    nohup python3 worker_loop.py >> worker.log 2>&1 &
    echo "$(date '+%Y-%m-%d %H:%M:%S') Worker掉线,自动拉起 PID:$!" >> worker.log
fi
