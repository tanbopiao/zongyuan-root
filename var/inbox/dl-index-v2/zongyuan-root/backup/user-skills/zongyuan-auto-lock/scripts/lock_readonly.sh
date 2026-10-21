#!/bin/bash
# 持久层只读锁档 + 人工审批解锁（lock_readonly）
# 锚定：DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω ｜ 重建于 2026-09-28 23:15（沙箱还原后恢复）
# 职责：
#   apply   对静态基线资产应用只读锁档（chmod 444 + chattr +i 尝试，失败退化）
#   unlock  人工审批解锁指定路径（记录审计留痕）→ 修改完成后用 relock 重新加锁
#   relock  重新加锁指定路径
#   status  保护清单状态
# 说明：动态流水层（HASH-LEDGER/audit/var/truth/var/heartbeat/var/activation/var/fusion/var/patrol/var/run/vector_store/logs）保持可写，不锁。
# 用法：bash lock_readonly.sh {apply|unlock <path>|relock <path>|status}
ZR="/home/user/ZONGYUAN-ROOT"
KERNEL="/home/user/Doubao/chats/38412149511142658/zongyuan-kernel"
SK="/home/user/.doubao/agent_mode/workspace/.user_skills"
AUDIT="$KERNEL/var/audit/audit.jsonl"
MANIFEST="$ZR/var/readonly-lock-manifest.json"
ts(){ date '+%Y-%m-%dT%H:%M:%S%z'; }
audit(){ python3 - "$1" <<'EOF'
import json, sys, io, datetime
rec = {"ts": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
       "event": "kernel.truth", "actor": "operator", "action": "readonly-lock",
       "result": "ok", "detail": sys.argv[1]}
with io.open("/home/user/Doubao/chats/38412149511142658/zongyuan-kernel/var/audit/audit.jsonl", "a", encoding="utf-8") as f:
    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
EOF
}

# 静态保护清单（目录→仅锁内部文件，目录保持可写以便追加新回执/脚本；动态流水层明确排除）
PATHS=(
  "$KERNEL/config/kernel.json"
  "$ZR/config/cron-restore.txt"
  "$ZR/config/supervisord-zongyuan.conf"
  "$ZR/scripts"/*.sh
  "$ZR/scripts"/*.py
  "$ZR/tools"/*.py
  "$ZR/hooks"/*.sh
  "$ZR/SOP-STEADY-STATE-20260927.md"
  "$ZR/卷宗"/*.json
  "$ZR/卷宗"/*.md
  "$KERNEL/config/meta_laws"/*.json
  "$KERNEL/scripts"/*.py
  "$KERNEL/scripts"/*.sh
  "$SK/zongyuan-auto-lock/SKILL.md"
  "$SK/zongyuan-auto-lock/scripts"/*.py
  "$SK/zongyuan-auto-lock/scripts"/*.sh
  "$SK/intelligent-orchestrator/SKILL.md"
  "$SK/intelligent-orchestrator/scripts"/*.py
  "/etc/profile.d/99-zongyuan-bootstrap.sh"
)

apply_lock(){
  local manifest=()
  for p in "${PATHS[@]}"; do
    [ -e "$p" ] || continue
    # 锁档策略 v2（冲突消解 CONFLICT-20260929-001）：可执行脚本保留执行位用 555，数据文件 444
    case "$p" in
      *.sh|*.py|*.pl|*.rb) chmod 555 "$p" 2>/dev/null ;;
      *) chmod 444 "$p" 2>/dev/null ;;
    esac
    chattr +i "$p" 2>/dev/null || true
    manifest+=("$p")
  done
  python3 - "$(ts)" "${manifest[@]}" <<'EOF'
import json, sys, io
out = {"event": "readonly-lock-apply", "applied_at": sys.argv[1],
       "protected": sys.argv[2:], "note": "静态基线文件只读；目录与动态流水层未锁；修改需 unlock 人工审批"}
with io.open("/home/user/ZONGYUAN-ROOT/var/readonly-lock-manifest.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print("MANIFEST:", len(sys.argv[2:]), "项已保护")
EOF
  audit "只读锁档 apply：${#PATHS[@]}个文件已保护，修改需人工审批"
}

unlock_one(){
  local p="$1"
  [ -e "$p" ] || { echo "不存在: $p"; exit 1; }
  chattr -i "$p" 2>/dev/null || true
  chmod 644 "$p" 2>/dev/null
  audit "人工审批解锁: $p（可修改，完成后 relock 重新加锁）"
  echo "UNLOCKED: $p"
}

relock_one(){
  local p="$1"
  [ -e "$p" ] || { echo "不存在: $p"; exit 1; }
  case "$p" in
    *.sh|*.py|*.pl|*.rb) chmod 555 "$p" 2>/dev/null ;;
    *) chmod 444 "$p" 2>/dev/null ;;
  esac
  chattr +i "$p" 2>/dev/null || true
  audit "重新加锁: $p"
  echo "RELOCKED: $p"
}

case "${1:-status}" in
  apply) apply_lock ;;
  unlock) [ -n "$2" ] && unlock_one "$2" || echo "用法: lock_readonly.sh unlock <path>" ;;
  relock) [ -n "$2" ] && relock_one "$2" || echo "用法: lock_readonly.sh relock <path>" ;;
  status)
    python3 - <<'EOF'
import json, io
try:
    d = json.load(io.open("/home/user/ZONGYUAN-ROOT/var/readonly-lock-manifest.json", encoding="utf-8"))
    print(f"已保护 {len(d.get('protected', []))} 项 | applied_at: {d.get('applied_at')}")
except Exception as e:
    print("未应用或清单缺失:", e)
EOF
    ;;
  *) echo "用法: lock_readonly.sh {apply|unlock <path>|relock <path>|status}" ;;
esac
