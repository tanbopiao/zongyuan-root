#!/bin/bash
# =====================================================================
# ZONGYUAN-ROOT Worker 内核总调度（全自动集成入口 · 无人值守增强版 v1.2）
# 锚定：DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω ｜ NODE-DEV-DOUBAO-WORK-001
# 集成：中枢受控 worker（心跳/指令/API）+ 图片视频自动归档（入队队列轮询）
#       + 全域锁档六环节（zongyuan-auto-lock）+ 系统状态监控 + rsync 续传
#       + watchdog 高频自愈（激活/触发/自启无人值守闭环）
# 用法：
#   worker_kernel.sh boot       开机自启完整激活：worker + rsync + 补锁档 + 激活台账
#   worker_kernel.sh watchdog   高频自愈（cron 每分钟）：worker保活/归档即时消费/补锁档/rsync续传
#   worker_kernel.sh tick       周期心跳（cron 每 5 分钟）：worker 保活 + 归档消费 + rsync 续传
#   worker_kernel.sh lock       全域锁档（zongyuan-auto-lock 六环节）
#   worker_kernel.sh monitor    系统状态监控（CPU/内存/磁盘/端口 → 落盘+上报）
#   worker_kernel.sh archive <payload_json>     归档单次入口
#   worker_kernel.sh enqueue <payload_json>     归档投递：校验→入队→立即消费→激活台账
# 幂等：全部 append-only；重复执行安全；失败不阻塞主流程
# =====================================================================
set -uo pipefail

ROOT="/home/user/ZONGYUAN-ROOT"
DID="DID-BR-000002"
SKILL_SCRIPT="/home/user/.doubao/agent_mode/workspace/.user_skills/zongyuan-auto-lock/scripts/zongyuan_full_lock.py"
INBOX="$ROOT/var/inbox"
ACT_DIR="$ROOT/var/activation"
LOG="$ROOT/logs/worker_kernel.log"
WORKER_ID="worker-kernel-001"
LOCK_HOURS=24   # 超过 24h 无全域锁档 → 自动补锁档

mkdir -p "$INBOX/done" "$INBOX/failed" "$ACT_DIR"
ts() { date '+%Y-%m-%dT%H:%M:%S%z'; }
tsn() { date +%s; }
logmsg() { echo "[$(ts)] $*" >> "$LOG"; }

# ---------- 激活台账（append-only + 索引） ----------
activate() {
  local action="$1" detail="$2" status="$3"
  local ts_h; ts_h=$(ts)
  local rec="{\"ts\":\"$ts_h\",\"action\":\"$action\",\"status\":\"$status\",\"detail\":\"$detail\",\"DID\":\"$DID\"}"
  local f="$ACT_DIR/activation-$(date +%Y%m%d-%H%M%S).json"
  echo "$rec" > "$f"
  local idx="$ACT_DIR/00-激活索引.json"
  if [ -f "$idx" ]; then
    python3 - "$idx" "$ts_h" "$action" "$status" <<'PYEOF'
import json, sys
idx_path, ts_h, action, status = sys.argv[1:5]
try:
    d = json.load(open(idx_path, encoding='utf-8'))
except Exception:
    d = {"title": "ZONGYUAN-ROOT 节点激活台账", "node": "NODE-DEV-DOUBAO-WORK-001", "records": []}
d["records"].append({"ts": ts_h, "action": action, "status": status})
json.dump(d, open(idx_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
PYEOF
  else
    echo "{\"title\":\"ZONGYUAN-ROOT 节点激活台账\",\"node\":\"NODE-DEV-DOUBAO-WORK-001\",\"records\":[{\"ts\":\"$ts_h\",\"action\":\"$action\",\"status\":\"$status\"}]}" > "$idx"
  fi
  logmsg "activate: $action | $status | $f"
}

# ---------- worker 保活 ----------
ensure_kernel() {
  # 脑内核保活：down 则拉起（kernel_launch.sh start 幂等）
  local st; st=$(bash "/home/user/Doubao/chats/38412149511142658/zongyuan-kernel/scripts/kernel_launch.sh" status 2>&1 | head -c 20)
  case "$st" in
    running*) logmsg "kernel 正常: $st" ;;
    *)
      logmsg "kernel down($st)，自动拉起"
      bash "/home/user/Doubao/chats/38412149511142658/zongyuan-kernel/scripts/kernel_launch.sh" start >> "$ROOT/logs/kernel_autoheal.log" 2>&1
      sleep 3
      st=$(bash "/home/user/Doubao/chats/38412149511142658/zongyuan-kernel/scripts/kernel_launch.sh" status 2>&1 | head -c 20)
      logmsg "kernel 拉起后: $st" ;;
  esac
}

ensure_worker() {
  local st
  st=$(bash "$ROOT/scripts/worker_controlled.sh" status "$WORKER_ID" 2>&1)
  if [[ "$st" != healthy* ]]; then
    bash "$ROOT/scripts/worker_controlled.sh" start "$WORKER_ID" >> "$LOG" 2>&1 || true
    st=$(bash "$ROOT/scripts/worker_controlled.sh" status "$WORKER_ID" 2>&1)
    logmsg "ensure_worker: 重新拉起 -> $st"
  fi
  echo "$st"
}

# ---------- 归档入队队列消费 ----------
consume_inbox() {
  local n=0
  for task in "$INBOX"/*.json; do
    [ -e "$task" ] || continue
    local TASK_ID; TASK_ID=$(basename "$task")
    local PAYLOAD; PAYLOAD=$(cat "$task")
    logmsg "consume: 处理归档任务 $TASK_ID"
    local RESULT
    RESULT=$(bash "$ROOT/hooks/hook_trigger_archive.sh" "$PAYLOAD" 2>&1)
    if echo "$RESULT" | grep -q '"result":"success"'; then
      mv "$task" "$INBOX/done/$TASK_ID.done"
      logmsg "consume: $TASK_ID 归档成功 $RESULT"
      n=$((n + 1))
    else
      mv "$task" "$INBOX/failed/$TASK_ID.failed"
      logmsg "consume: $TASK_ID 归档失败 $RESULT"
    fi
  done
  echo "$n"
}

# ---------- rsync 续传 ----------
flush_rsync() {
  bash "$ROOT/scripts/rsync_flush_pending.sh" >> "$LOG" 2>&1 || true
}

# ---------- 锁档新鲜度检查（> LOCK_HOURS 小时未锁档 → 补锁档） ----------
needs_lock() {
  local latest
  latest=$(ls -t "$ROOT/卷宗"/GLOBAL-LOCK-ZONGYUAN-ROOT-FULL-*.json 2>/dev/null | head -1)
  if [ -z "$latest" ]; then echo "yes"; return; fi
  local mtime now age
  mtime=$(stat -c %Y "$latest"); now=$(tsn); age=$(( (now - mtime) / 3600 ))
  if [ "$age" -ge "$LOCK_HOURS" ]; then echo "yes"; else echo "no"; fi
}

# ---------- boot：开机自启完整激活 ----------
boot() {
  logmsg "=== boot 开机自启完整激活 ==="
  ensure_kernel
  local st; st=$(ensure_worker)
  flush_rsync
  # 补锁档：最近 24h 无全域锁档则自动补跑
  if [ "$(needs_lock)" = "yes" ]; then
    logmsg "boot: 检测到 ${LOCK_HOURS}h 内无锁档，自动补跑"
    lock
  fi
  activate boot "$st / rsync续传" ok
  logmsg "=== boot 完成 ==="
}

# ---------- watchdog：高频自愈（cron 每分钟） ----------
watchdog() {
  logmsg "=== watchdog 自愈 ==="
  ensure_kernel
  local st; st=$(ensure_worker)
  local consumed; consumed=$(consume_inbox)
  [ "$consumed" -gt 0 ] && logmsg "watchdog: 即时消费归档任务 $consumed 个"
  flush_rsync
  if [ "$(needs_lock)" = "yes" ]; then
    logmsg "watchdog: 超 ${LOCK_HOURS}h 未锁档，自动触发"
    lock
  fi
  local brief="worker:${st%% *} / inbox_consumed:${consumed}"
  activate watchdog "$brief" ok
  logmsg "=== watchdog 完成 ==="
}

# ---------- tick：周期心跳（cron 每 5 分钟） ----------
tick() {
  logmsg "=== tick 周期 ==="
  local st; st=$(ensure_worker)
  consume_inbox >/dev/null
  flush_rsync
  activate tick "${st%% *}" ok
  logmsg "=== tick 完成 ==="
}

# ---------- lock：全域锁档 ----------
lock() {
  logmsg "=== lock 全域锁档 ==="
  python3 "$SKILL_SCRIPT" >> "$LOG" 2>&1 || logmsg "lock: 全域锁档执行异常"
  activate lock "zongyuan-auto-lock 六环节" ok
  logmsg "=== lock 完成 ==="
}

# ---------- monitor：系统状态监控 ----------
monitor() {
  logmsg "=== monitor 系统状态监控 ==="
  bash "$ROOT/scripts/system_status_monitor.sh" >> "$ROOT/logs/system_status.log" 2>&1 || logmsg "monitor: 监控执行异常"
  activate monitor "system_status" ok
  logmsg "=== monitor 完成 ==="
}

# ---------- archive：归档单次入口 ----------
archive() {
  local PAYLOAD="${1:-}"
  if [ -z "$PAYLOAD" ]; then
    echo '{"result":"failed","reason":"empty_payload"}'; return 2
  fi
  bash "$ROOT/hooks/hook_trigger_archive.sh" "$PAYLOAD"
}

# ---------- enqueue：归档投递（校验→入队→立即消费） ----------
enqueue() {
  local PAYLOAD="${1:-}"
  if [ -z "$PAYLOAD" ]; then
    echo '{"result":"failed","reason":"empty_payload"}'; return 2
  fi
  # 载荷校验：task_type + DID + asset_kind
  local ok
  ok=$(echo "$PAYLOAD" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    print('invalid'); sys.exit()
if d.get('task_type') != 'auto_archive_asset' or d.get('DID') != '$DID':
    print('bad_protocol'); sys.exit()
if d.get('asset_kind') not in ('image', 'video') or not d.get('session_temp_url'):
    print('bad_payload'); sys.exit()
print('ok')
")
  if [ "$ok" != "ok" ]; then
    echo "{\"result\":\"rejected\",\"reason\":\"$ok\"}"; return 3
  fi
  local f="$INBOX/enqueue-$(date +%Y%m%d-%H%M%S-%N).json"
  echo "$PAYLOAD" > "$f"
  logmsg "enqueue: 任务入队 $f"
  local consumed; consumed=$(consume_inbox)
  activate enqueue "inbox=$f consumed=$consumed" ok
  echo "{\"result\":\"queued_and_consumed\",\"file\":\"$f\",\"consumed\":$consumed}"
}

# ---------- 分发 ----------
case "${1:-}" in
  boot)    boot ;;
  watchdog) watchdog ;;
  tick)    tick ;;
  lock)    lock ;;
  dispatch)  # 算子调度器：消费 task_inbox 契约（修复版 operator_dispatcher V1.1）
    python3 /home/user/ZONGYUAN-ROOT/tools/operator_dispatcher.py
    ;;
  monitor) monitor ;;
  archive) archive "${2:-}" ;;
  enqueue) enqueue "${2:-}" ;;
  *) echo "用法: worker_kernel.sh {boot|watchdog|tick|lock|monitor|dispatch|archive|enqueue}"; exit 2 ;;
esac
