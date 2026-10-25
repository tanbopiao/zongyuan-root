#!/bin/bash
# ============================================================
# ZR-SUPERVISOR 同源节点保活守护 V1.0
# 用途: crontab/systemd 不可用时的降级保活方案
#       每60s检查 zr_node_worker.py, 掉线自动拉起
# 启动: nohup bash /mnt/workspace/zr_supervisor.sh >> /mnt/workspace/supervisor.log 2>&1 &
# 注意: 不跨容器重启(重启后需重跑 bootstrap 或手动启动)
# ============================================================
while true; do
  if ! pgrep -f "zr_node_worker.py" >/dev/null 2>&1; then
    cd /mnt/workspace
    nohup python3 /mnt/workspace/zr_node_worker.py >> /mnt/workspace/worker_stdout.log 2>&1 &
    echo "[$(date '+%F %T')] worker 掉线, 已重新拉起 PID $!" >> /mnt/workspace/supervisor.log
  fi
  sleep 60
done
