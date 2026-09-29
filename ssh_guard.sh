#!/bin/bash
# SSH连通守护：authorized_keys被篡改自动恢复
BACKUP="/opt/ZONGYUAN-ROOT/backups/ssh/authorized_keys.latest"
TARGET="/root/.ssh/authorized_keys"
LOG="/opt/ZONGYUAN-ROOT/ssh_guard.log"

# 确保最新备份存在
if [ ! -f "$BACKUP" ]; then
    ls -t /opt/ZONGYUAN-ROOT/backups/ssh/authorized_keys.* 2>/dev/null | head -1 | xargs -I{} cp {} "$BACKUP"
fi

# 检查authorized_keys是否包含我们的公钥
if ! grep -q "zongyuan_deploy\|user@sandbox\|zongyuan-backup" "$TARGET" 2>/dev/null; then
    echo "[$(date)] authorized_keys异常，从备份恢复" >> "$LOG"
    cp "$BACKUP" "$TARGET"
    chmod 600 "$TARGET"
    chmod 700 /root/.ssh
    systemctl restart sshd
    echo "[$(date)] 已恢复，当前行数: $(wc -l < $TARGET)" >> "$LOG"
fi

# 更新最新备份
cp "$TARGET" "$BACKUP"
