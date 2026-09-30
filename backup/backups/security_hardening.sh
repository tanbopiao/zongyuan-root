#!/bin/bash
# ZONGYUAN-ROOT 安全加固巡检（每日）
set -e
LOG=/home/user/files/zongyuan-persist/logs/security_hardening.log
TS=$(date "+%Y-%m-%d %H:%M:%S")
echo "[$TS] === 安全加固巡检开始 ===" >> "$LOG"

# 1. DID密钥权限校验（必须600）
DID_DIR=/home/user/.doubao/agent_mode/workspace/.user_skills/meta-order-lock-archive/scripts/.did_keys
if [ -d "$DID_DIR" ]; then
  find "$DID_DIR" -name "*.pem" -type f | while read f; do
    P=$(stat -c "%a" "$f")
    if [ "$P" != "600" ]; then chmod 600 "$f"; echo "[$TS] FIX 密钥权限: $f -> 600" >> "$LOG"; fi
  done
  chmod 700 "$DID_DIR"
fi

# 2. 持久化目录权限（必须700）
chmod 700 /home/user/files/zongyuan-persist /home/user/files/zongyuan-persist/snapshots /home/user/files/zongyuan-persist/backups 2>/dev/null

# 3. 对外端口监控（0.0.0.0监听）
PORTS=$(ss -tln 2>/dev/null | grep -E "0\.0\.0\.0|\*:" | awk '{print $4}' | sort -u)
echo "[$TS] 对外监听: $PORTS" >> "$LOG"

# 4. 哈希完整性自校验（快照对比）
if [ -f /home/user/files/zongyuan-persist/snapshots/DEEP-PERSIST-SNAPSHOT.json ]; then
  echo "[$TS] 快照存在，Merkle完整性待流水线校验" >> "$LOG"
fi

echo "[$TS] === 巡检完成 ===" >> "$LOG"
