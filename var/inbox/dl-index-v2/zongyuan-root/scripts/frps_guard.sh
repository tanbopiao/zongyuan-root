#!/bin/bash
# ============================================================
# frps_guard.sh — 元极恒一内核守护链路 v1.1
# 事件ID: KERNEL-GUARD-FRPS-001
# 锚定: Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | NODE-DEV-DOUBAO-WORK-001
# 守护目标: frps(7000) 主隧道实例（保持 nohup 运行形态，不引入 systemd）
# 观测目标: frps-legacy(7100) 仅只读观测/告警，不接管（已由 systemd 管理）
# 元法则: META-RULE-012 MR12-4（定时任务全局互斥锁，禁止并发）
#          META-RULE-WORKER-HARDENING-001（脚本只读加固，哈希登记）
# 约束: 正常运行期零干扰（只读探测）；仅事件触发时拉起/上报；不模糊 pkill
# 变更记录: v1.0→v1.1 锁升级为 mkdir 原子锁（修复 cron 与手动并发双拉起致 7500 端口竞争）
# ============================================================
LOCK_DIR=/tmp/frps_guard.lock
LOG=/opt/ZONGYUAN-ROOT/logs/frps_guard.log
MAIN_CFG=/opt/frp/frps.toml
GW=https://www.huodouai.com/api/report/truth
TS=$(date +%s)
STAMP=$(date '+%Y-%m-%d %H:%M:%S')

# ---- 原子互斥锁（META-RULE-012 MR12-4：同一节点同一任务禁止并发执行）----
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  exit 0   # 已有守护实例在运行，静默退出
fi
trap 'rmdir "$LOCK_DIR" 2>/dev/null' EXIT

log() { echo "[$STAMP] $1" >> "$LOG"; }

report() {
  curl -sS -m 8 -X POST "$GW" \
    -H "X-DID: DID-BR-000002" -H "Content-Type: application/json" \
    -d "{\"key\":\"$1\",\"value\":{\"event\":\"$2\",\"node\":\"lhins-laotwc5e\",\"did\":\"DID-BR-000002\",\"detail\":\"$3\",\"ts\":$TS}}" >/dev/null 2>&1
}

port_listening() { ss -tln 2>/dev/null | grep -qE ':'"$1"' '; }

# ---- 1) 主实例 7000 守护（崩溃自愈）----
if ! port_listening 7000; then
  log "WARN 7000 未监听，守护拉起"
  nohup /opt/frp/frps -c "$MAIN_CFG" >> /opt/frp/frps.log 2>&1 &
  sleep 8
  if port_listening 7000; then
    log "INFO 7000 已恢复监听"
    report "frps_guard_revive_${TS}" "frps_guard_revive" "7000 restarted by guard"
  else
    # 首次拉起失败（如端口竞争）：清理僵留后重试一次
    log "WARN 7000 首拉起未就绪，二次重试"
    pkill -f 'frps -c /opt/frp/frps.toml' 2>/dev/null
    sleep 2
    nohup /opt/frp/frps -c "$MAIN_CFG" >> /opt/frp/frps.log 2>&1 &
    sleep 8
    if port_listening 7000; then
      log "INFO 7000 二次拉起成功"
      report "frps_guard_revive_${TS}" "frps_guard_revive" "7000 restarted(2nd) by guard"
    else
      log "ERROR 7000 拉起失败，升级告警"
      report "frps_guard_fail_${TS}" "frps_guard_fail" "7000 NOT listening after revive"
    fi
  fi
fi

# ---- 2) legacy 7100 只读观测（不接管）----
if ! port_listening 7100; then
  log "WARN legacy(7100) 未监听（systemd 管辖，仅观测告警）"
  report "frps_guard_legacy_down_${TS}" "frps_guard_legacy_down" "7100 not listening (systemd-managed, observe only)"
fi

exit 0
