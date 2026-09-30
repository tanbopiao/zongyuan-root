#!/bin/bash
# ============================================================
# video_archive_auto.sh
# 昆仑洞天视频自动化归档主脚本
# 功能：断点续传下载MP4 → SHA256校验 → 更新元数据 → 写入哈希链
# 用法：./video_archive_auto.sh <EP_ID> <DOWNLOAD_URL> [EXPIRY_TIME]
# ============================================================

set -e

EP_ID="$1"
DOWNLOAD_URL="$2"
EXPIRE_AT="${3:-unknown}"

ROOT="/home/user/.doubao/agent_mode/workspace/.user_skills/kunlun-autonomous-system/ZONGYUAN-ROOT"
META_ROOT="$ROOT/assets/media/jiutian_xuannu_video_meta/raw"
VIDEO_STORE="$ROOT/assets/media/jiutian_xuannu_video/${EP_ID}"
HASH_LEDGER="/home/user/Doubao/chats/38418284746129666/HASH-LEDGER.csv"
META_FILE="$META_ROOT/${EP_ID}.json"

# 校验参数
if [ -z "$EP_ID" ] || [ -z "$DOWNLOAD_URL" ]; then
    echo "用法: $0 <EP_ID> <DOWNLOAD_URL> [EXPIRE_AT]"
    echo "示例: $0 EP05 https://cdn.example.com/video.mp4 '2026-09-23 10:00:00'"
    exit 1
fi

mkdir -p "$VIDEO_STORE"

echo "========================================"
echo "昆仑洞天视频自动化归档"
echo "EP: $EP_ID"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================"

# Step1: 断点续传下载MP4
echo "[Step1] 开始下载: $DOWNLOAD_URL"
wget -c --show-progress -O "$VIDEO_STORE/${EP_ID}.mp4" "$DOWNLOAD_URL"

# Step2: 计算SHA256哈希
echo "[Step2] 计算SHA256哈希..."
cd "$VIDEO_STORE"
sha256sum "${EP_ID}.mp4" > SHA256.sum
FILE_HASH=$(cut -d' ' -f1 SHA256.sum)
FILE_SIZE=$(du -h "${EP_ID}.mp4" | cut -f1)
echo "  文件大小: $FILE_SIZE"
echo "  SHA256: $FILE_HASH"

# Step3: 更新元数据
echo "[Step3] 更新元数据..."
if [ -f "$META_FILE" ]; then
    # 已存在meta，更新字段
    jq --arg fp "$VIDEO_STORE/${EP_ID}.mp4" \
       --arg fh "$FILE_HASH" \
       --arg fs "$FILE_SIZE" \
       --arg now "$(date -Iseconds)" \
       '.local_archive=true
        | .local_file_path=$fp
        | .sha256=$fh
        | .file_size=$fs
        | .archived_at=$now' \
       "$META_FILE" > "${META_FILE}.tmp" && mv "${META_FILE}.tmp" "$META_FILE"
else
    # 新建meta
    cat > "$META_FILE" << EOF
{
  "series": "昆仑洞天·九天玄女",
  "episode": "$EP_ID",
  "task_id": "",
  "video_url": "",
  "download_url": "$DOWNLOAD_URL",
  "expire_at": "$EXPIRE_AT",
  "status": "generated",
  "local_archive": true,
  "local_file_path": "$VIDEO_STORE/${EP_ID}.mp4",
  "sha256": "$FILE_HASH",
  "file_size": "$FILE_SIZE",
  "archived_at": "$(date -Iseconds)",
  "source_node": "NODE-DEV-DOUBAO-WORK-001",
  "did": "DID-BR-000002"
}
EOF
fi

# Step4: 写入全局哈希链
echo "[Step4] 写入HASH-LEDGER..."
echo "$FILE_HASH  VIDEO/${EP_ID}/${EP_ID}.mp4 (local archive)" >> "$HASH_LEDGER"

echo ""
echo "========================================"
echo "✅ $EP_ID 归档完成"
echo "  本地路径: $VIDEO_STORE/${EP_ID}.mp4"
echo "  哈希: $FILE_HASH"
echo "  大小: $FILE_SIZE"
echo "========================================"
