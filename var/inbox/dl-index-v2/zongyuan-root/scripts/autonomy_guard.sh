#!/bin/bash
# 自治守护（autonomy_guard）｜ 定时自动拉起整个内核与自治系统（幂等）
# 锚定：DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω
# 检查项：crond / supervisord-zongyuan / zongyuan_daemon / 脑内核三端口 / worker-kernel-001 / cron条目
# 用法：bash autonomy_guard.sh [--quiet]   （cron 每 5 分钟）
ZR="/home/user/ZONGYUAN-ROOT"
KERNEL="/home/user/Doubao/chats/38412149511142658/zongyuan-kernel"
LOG="$ZR/logs/autonomy_guard.log"
ts(){ date '+%Y-%m-%d %H:%M:%S'; }
log(){ [ "$1" != "--quiet" ] && echo "[$(ts)] $2" >> "$LOG"; }
FIXED=0

# 0. 沙箱重置恢复（技能/锚点/cron 幂等补齐）
bash "$ZR/scripts/restore_from_backup.sh" --quiet >> "$LOG" 2>&1

# 1. crond 守护
if ! pgrep -x cron >/dev/null 2>&1 && ! pgrep -f "/usr/sbin/cron" >/dev/null 2>&1; then
  sudo -n service cron start >/dev/null 2>&1 || sudo -n /usr/sbin/cron >/dev/null 2>&1
  sleep 1
  if pgrep -f "/usr/sbin/cron" >/dev/null 2>&1; then log "$1" "crond 拉起"; FIXED=$((FIXED+1)); fi
fi

# 2. supervisord-zongyuan
if ! pgrep -f "supervisord.*zongyuan" >/dev/null 2>&1; then
  if [ -f "$ZR/config/supervisord-zongyuan.conf" ]; then
    sudo -n supervisord -c "$ZR/config/supervisord-zongyuan.conf" >> "$LOG" 2>&1
    sleep 2
    pgrep -f "supervisord.*zongyuan" >/dev/null 2>&1 && { log "$1" "supervisord-zongyuan 拉起"; FIXED=$((FIXED+1)); }
  fi
fi

# 3. zongyuan_daemon（supervisord 托管，down 则重启）
if ! pgrep -f "zongyuan_daemon.sh" >/dev/null 2>&1; then
  sudo -n supervisorctl -c "$ZR/config/supervisord-zongyuan.conf" restart zongyuan_daemon >> "$LOG" 2>&1
  sleep 2
  pgrep -f "zongyuan_daemon.sh" >/dev/null 2>&1 && { log "$1" "zongyuan_daemon 拉起"; FIXED=$((FIXED+1)); }
fi

# 4. 脑内核三端口（9081/9082/9092）
if ! ss -tln 2>/dev/null | grep -qE ":(9081|9082|9092) "; then
  bash "$KERNEL/scripts/kernel_launch.sh" start >> "$LOG" 2>&1
  sleep 3
  ss -tln 2>/dev/null | grep -qE ":(9081|9082|9092) " && { log "$1" "脑内核拉起"; FIXED=$((FIXED+1)); }
fi

# 5. worker-kernel-001
if ! pgrep -f "worker_daemon.sh worker-kernel-001" >/dev/null 2>&1; then
  bash "$ZR/scripts/worker_kernel.sh" boot >> "$LOG" 2>&1
  sleep 2
  pgrep -f "worker_daemon.sh worker-kernel-001" >/dev/null 2>&1 && { log "$1" "worker-kernel-001 拉起"; FIXED=$((FIXED+1)); }
fi

# 6. cron 条目 <10 → 自举恢复
N=$(crontab -l 2>/dev/null | grep -v '^#' | grep -v '^$' | wc -l)
if [ "$N" -lt 10 ]; then
  bash "$ZR/scripts/self_bootstrap.sh" >> "$LOG" 2>&1
  log "$1" "cron 自举恢复"
  FIXED=$((FIXED+1))
fi

echo "[$(ts)] guard cycle ok fixed=$FIXED" >> "$LOG"
[ "$1" != "--quiet" ] && echo "guard done fixed=$FIXED"
exit 0
