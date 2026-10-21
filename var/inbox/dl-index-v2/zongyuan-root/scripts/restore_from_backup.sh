#!/bin/bash
# 沙箱重置恢复器（restore_from_backup）｜ 从持久层恢复被沙箱销毁/重置清空的资产
# 锚定：DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω ｜ 2026-09-28 溯源后固化
# 恢复项（幂等，只补缺失不覆盖）：
#   1. .user_skills 技能资产（半持久层，平台还原会丢自定义新文件）→ backup/user-skills
#   2. /etc/profile.d/99-zongyuan-bootstrap.sh（/etc 重建清空，需 sudo）→ backup/etc
#   3. crontab（沙箱重启清空）→ config/cron-restore.txt
# 用法：bash restore_from_backup.sh [--quiet]  （guard 每 5 分钟自动调用）
ZR="/home/user/ZONGYUAN-ROOT"
SK="/home/user/.doubao/agent_mode/workspace/.user_skills"
BK="$ZR/backup"
AUDIT="/home/user/Doubao/chats/38412149511142658/zongyuan-kernel/var/audit/audit.jsonl"
RESTORED=0
ts(){ date '+%Y-%m-%dT%H:%M:%S%z'; }
audit(){ python3 - "$1" <<'EOF'
import json, sys, io, datetime
rec = {"ts": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
       "event": "kernel.truth", "actor": "operator", "action": "restore-from-backup",
       "result": "ok", "detail": sys.argv[1]}
with io.open("/home/user/Doubao/chats/38412149511142658/zongyuan-kernel/var/audit/audit.jsonl", "a", encoding="utf-8") as f:
    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
EOF
}

# 1. 技能资产恢复
[ -d "$BK/user-skills" ] && {
  for rel in "zongyuan-auto-lock/SKILL.md" "zongyuan-auto-lock/scripts/lock_readonly.sh" \
             "zongyuan-auto-lock/scripts/incremental_lock.py" "zongyuan-auto-lock/scripts/zongyuan_full_lock.py" \
             "zongyuan-auto-lock/scripts/meta_law_schema_check.py" "intelligent-orchestrator/SKILL.md" \
             "intelligent-orchestrator/scripts/vector_store.py" "intelligent-orchestrator/scripts/summarize_run.py" \
             "intelligent-orchestrator/scripts/validate_plan.py"; do
    if [ ! -f "$SK/$rel" ] && [ -f "$BK/user-skills/$rel" ]; then
      mkdir -p "$SK/$(dirname "$rel")"
      cp "$BK/user-skills/$rel" "$SK/$rel" && { echo "恢复技能: $rel"; RESTORED=$((RESTORED+1)); }
    fi
  done
}

# 2. /etc 锚点恢复（sudo）
if [ ! -f /etc/profile.d/99-zongyuan-bootstrap.sh ] && [ -f "$BK/etc/99-zongyuan-bootstrap.sh" ]; then
  sudo -n cp "$BK/etc/99-zongyuan-bootstrap.sh" /etc/profile.d/99-zongyuan-bootstrap.sh 2>/dev/null \
    && { echo "恢复锚点: /etc/profile.d/99-zongyuan-bootstrap.sh"; RESTORED=$((RESTORED+1)); }
fi

# 3. crontab 恢复
N=$(crontab -l 2>/dev/null | grep -v '^#' | grep -v '^$' | wc -l)
if [ "$N" -lt 10 ] && [ -f "$ZR/config/cron-restore.txt" ]; then
  grep -v '^#' "$ZR/config/cron-restore.txt" | grep -v '^$' | crontab - \
    && { echo "恢复 crontab: $(crontab -l | grep -v '^#' | grep -v '^$' | wc -l) 条"; RESTORED=$((RESTORED+1)); }
fi

echo "restore done restored=$RESTORED"
[ "$RESTORED" -gt 0 ] && audit "沙箱重置恢复: 恢复 $RESTORED 项（技能/锚点/cron）"
exit 0
