#!/bin/bash
# 多级自举：不依赖 crontab 的重置自愈
# 检测 cron/守护缺失 → 自动恢复（幂等，存在即跳过）
ZR=/home/user/ZONGYUAN-ROOT
LOG=$ZR/logs/self_bootstrap.log
ts(){ date '+%Y-%m-%d %H:%M:%S'; }
log(){ echo "[$(ts)] $*" >> $LOG; }

log "=== 自举检测开始 ==="
FIXED=0

# 1. cron 缺失 → 从备份恢复
CRON_N=$(crontab -l 2>/dev/null | wc -l)
if [ "$CRON_N" -lt 10 ]; then
  if [ -f "$ZR/config/cron-restore.txt" ]; then
    grep -v '^#' "$ZR/config/cron-restore.txt" | grep -v '^$' | crontab -
    log "cron 缺失(原$CRON_N条)→ 已恢复 $(crontab -l|wc -l) 条"
    FIXED=$((FIXED+1))
  else
    log "错误：cron 备份不存在，无法恢复"
  fi
else
  log "cron 正常 ($CRON_N 条)"
fi

# 2. supervisord 缺失 → 拉起
if ! pgrep -f "supervisord.*zongyuan" >/dev/null; then
  if [ -f "$ZR/config/supervisord-zongyuan.conf" ]; then
    sudo -n supervisord -c "$ZR/config/supervisord-zongyuan.conf" 2>>$LOG
    log "supervisord 未运行 → 已拉起"
    FIXED=$((FIXED+1))
  fi
else
  log "supervisord 在线"
fi

# 3. worker boot（幂等激活）
[ -x "$ZR/scripts/worker_kernel.sh" ] && bash "$ZR/scripts/worker_kernel.sh" boot >/dev/null 2>&1

log "=== 自举完成，修复 $FIXED 项 ==="
echo "bootstrap done, fixed=$FIXED"
