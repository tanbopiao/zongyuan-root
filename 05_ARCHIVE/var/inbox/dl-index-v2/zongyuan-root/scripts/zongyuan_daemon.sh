#!/bin/bash
# ZONGYUAN-ROOT 无人值守常驻守护 ｜ supervisord 托管
# 周期任务：evolution_consumer 60s / worker_instruction_pull 300s / cloud_pull 1800s / axiom_patrol 21600s / 心跳 300s
ZR="/home/user/ZONGYUAN-ROOT"
LOG="$ZR/logs/daemon.log"
echo "[$(date)] ZONGYUAN 常驻守护启动 pid=$$" >> "$LOG"
while true; do
  T0=$(date +%s)
  # 1) 联邦采纳消费（60s）
  /usr/bin/python3 $ZR/scripts/evolution_consumer.py >> $ZR/logs/evolution_consumer.log 2>&1
  # 2) 云端指令拉取（300s）
  if [ $(( $(date +%s) - T0 )) -ge 0 ]; then :; fi
  bash $ZR/scripts/worker_instruction_pull.sh >> $ZR/logs/worker_instruction_pull.log 2>&1
  # 3) 心跳/真值上报（300s 与指令合并周期）
  bash $ZR/scripts/heartbeat_sync.sh >> $ZR/logs/heartbeat_sync.log 2>&1
  # 4) 资产镜像拉取（1800s）
  if [ $(( $(date +%s) % 1800 )) -lt 60 ]; then
    bash $ZR/scripts/cloud_pull.sh >> $ZR/logs/cloud_pull.log 2>&1
  fi
  # 5) 公理巡检投递（21600s）
  if [ $(( $(date +%s) % 21600 )) -lt 60 ]; then
    bash $ZR/scripts/axiom_patrol_timer.sh >> $ZR/logs/axiom_patrol.log 2>&1
  fi
  echo "[$(date)] daemon cycle ok" >> "$LOG"
  sleep 55
done
