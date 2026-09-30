#!/bin/bash
# ZONGYUAN-ROOT 元自治循环 cron 任务
PY=/usr/bin/python3
SKILL=/home/user/.doubao/agent_mode/workspace/.user_skills

# 每小时守护巡检（心跳+健康检查+自动备份）
0 * * * * $PY $SKILL/zongyuan-autonomous-core/scripts/meta_daemon.py --once >> /home/user/files/zongyuan-persist/logs/daemon_hourly.log 2>&1

# 每6小时灾备备份（多副本）
0 */6 * * * $PY $SKILL/meta-order-lock-archive/scripts/disaster_recovery.py --mode backup --source-dir /home/user/Doubao/chats/38418284746129666/zongyuan-root --backup-dir /home/user/files/zongyuan-persist/backups --backup-type incremental --replica-id LOCAL-REP-001 >> /home/user/files/zongyuan-persist/logs/dr_6h.log 2>&1

# 每日哈希自校验（Merkle完整性）
30 4 * * * $PY $SKILL/meta-order-lock-archive/scripts/self_healing.py --kernel /home/user/.doubao/agent_mode/workspace/ZONGYUAN-ROOT/snapshots/kernel.json --workspace /home/user/Doubao/chats/38418284746129666/zongyuan-root --mode full >> /home/user/files/zongyuan-persist/logs/heal_daily.log 2>&1
30 2 * * * /home/user/files/zongyuan-persist/security_hardening.sh
