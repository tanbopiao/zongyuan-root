#!/bin/bash
# 共享文件写前锁 - 多窗口并发冲突防护
# 用法: source shared_file_lock.sh && lock_file <file_path> <window_id>

LOCK_DIR="/opt/ZONGYUAN-ROOT/.file_locks"
mkdir -p "$LOCK_DIR"

lock_file() {
    local FILE="$1"
    local WINDOW="$2"
    local LOCK_FILE="$LOCK_DIR/$(echo "$FILE" | md5sum | cut -d' ' -f1).lock"
    
    # 检查是否有其他窗口持有锁
    if [ -f "$LOCK_FILE" ]; then
        local HOLDER=$(cat "$LOCK_FILE" | head -1)
        local HOLD_TIME=$(stat -c %Y "$LOCK_FILE")
        local NOW=$(date +%s)
        local AGE=$((NOW - HOLD_TIME))
        if [ "$HOLDER" != "$WINDOW" ] && [ "$AGE" -lt 300 ]; then
            echo "❌ 锁冲突: $FILE 被窗口[$HOLDER]持有(${AGE}秒前)，等待或联系该窗口释放"
            return 1
        fi
        # 超过5分钟的锁视为过期，强制获取
        if [ "$AGE" -ge 300 ]; then
            echo "⚠️  锁过期(>${AGE}s)，强制获取: $FILE"
        fi
    fi
    
    echo "$WINDOW" > "$LOCK_FILE"
    echo "$(date -Iseconds)" >> "$LOCK_FILE"
    echo "✅ 锁获取成功: $FILE (窗口:$WINDOW)"
    return 0
}

unlock_file() {
    local FILE="$1"
    local LOCK_FILE="$LOCK_DIR/$(echo "$FILE" | md5sum | cut -d' ' -f1).lock"
    rm -f "$LOCK_FILE"
    echo "🔓 锁释放: $FILE"
}

list_locks() {
    echo "=== 当前持有锁的文件 ==="
    for f in "$LOCK_DIR"/*.lock; do
        [ -f "$f" ] || continue
        local HOLDER=$(head -1 "$f")
        local TIME=$(sed -n '2p' "$f")
        echo "  $(basename $f): 窗口[$HOLDER] @ $TIME"
    done
}
