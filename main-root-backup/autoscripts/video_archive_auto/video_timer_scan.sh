#!/bin/bash
# ============================================================
# video_timer_scan.sh
# 昆仑洞天视频资产CDN定时巡检脚本
# 功能：扫描全部视频meta，监控CDN有效期，临近过期自动下载
# 触发：crontab 每6小时执行一次
# ============================================================

ROOT="/home/user/.doubao/agent_mode/workspace/.user_skills/kunlun-autonomous-system/ZONGYUAN-ROOT"
META_ROOT="$ROOT/assets/media/jiutian_xuannu_video_meta/raw"
AUTO_SCRIPT="$ROOT/autoscripts/video_archive_auto/video_archive_auto.sh"
HASH_LEDGER="/home/user/Doubao/chats/38418284746129666/HASH-LEDGER.csv"
LOG_FILE="$ROOT/autoscripts/video_archive_auto/scan_log.log"
ALERT_THRESHOLD=14400  # 剩余有效期<4小时（秒）触发预下载

echo "========================================" >> "$LOG_FILE"
echo "巡检时间: $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"

if [ ! -d "$META_ROOT" ]; then
    echo "[WARN] 元数据目录不存在: $META_ROOT" >> "$LOG_FILE"
    exit 0
fi

shopt -s nullglob
meta_files=("$META_ROOT"/EP*.json)

if [ ${#meta_files[@]} -eq 0 ]; then
    echo "[INFO] 暂无视频元数据记录" >> "$LOG_FILE"
    exit 0
fi

for meta_file in "${meta_files[@]}"; do
    EP_ID=$(basename "$meta_file" .json)

    # 检查是否有jq
    if ! command -v jq &> /dev/null; then
        echo "[ERROR] jq未安装，请先安装jq" >> "$LOG_FILE"
        exit 1
    fi

    LOCAL_ARCHIVE=$(jq -r '.local_archive // false' "$meta_file")
    DOWNLOAD_URL=$(jq -r '.download_url // ""' "$meta_file")
    EXPIRE_AT=$(jq -r '.expire_at // "unknown"' "$meta_file")
    CDN_EXPIRED=$(jq -r '.cdn_expired // false' "$meta_file")

    # 已本地归档，跳过
    if [ "$LOCAL_ARCHIVE" = "true" ]; then
        echo "[$EP_ID] ✅ 本地资产已固化，跳过巡检" >> "$LOG_FILE"
        continue
    fi

    # 已标记CDN过期
    if [ "$CDN_EXPIRED" = "true" ]; then
        echo "[$EP_ID] ⚠️ CDN链接已过期，等待重生成" >> "$LOG_FILE"
        continue
    fi

    # 无下载URL
    if [ -z "$DOWNLOAD_URL" ] || [ "$DOWNLOAD_URL" = "null" ]; then
        echo "[$EP_ID] ⚠️ 无download_url，标记待捕获" >> "$LOG_FILE"
        continue
    fi

    # 计算剩余有效期
    if [ "$EXPIRE_AT" = "unknown" ] || [ "$EXPIRE_AT" = "null" ]; then
        echo "[$EP_ID] ⚠️ 无expire_at时间戳，无法判断" >> "$LOG_FILE"
        continue
    fi

    NOW_TS=$(date +%s)
    EXPIRE_TS=$(date -d "$EXPIRE_AT" +%s 2>/dev/null || echo "0")
    REMAIN_SEC=$(( EXPIRE_TS - NOW_TS ))

    if [ "$REMAIN_SEC" -le 0 ]; then
        echo "[$EP_ID] ⚠️ CDN链接已过期（剩余${REMAIN_SEC}秒），标记失效" >> "$LOG_FILE"
        jq '.cdn_expired=true' "$meta_file" > "${meta_file}.tmp" && mv "${meta_file}.tmp" "$meta_file"
    elif [ "$REMAIN_SEC" -le "$ALERT_THRESHOLD" ]; then
        echo "[$EP_ID] ⚠️ CDN即将过期（剩余${REMAIN_SEC}秒），启动自动下载" >> "$LOG_FILE"
        bash "$AUTO_SCRIPT" "$EP_ID" "$DOWNLOAD_URL" "$EXPIRE_AT" >> "$LOG_FILE" 2>&1
    else
        HOURS=$(( REMAIN_SEC / 3600 ))
        echo "[$EP_ID] ✅ CDN正常，剩余有效期约${HOURS}小时" >> "$LOG_FILE"
    fi
done

echo "" >> "$LOG_FILE"
echo "巡检完成" >> "$LOG_FILE"
