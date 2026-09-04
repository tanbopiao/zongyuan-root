#!/bin/bash
# ZONGYUAN-ROOT 短剧视频归档锁档脚本
# 用法: ./archive_video.sh <video_file> <episode_id> <title>
VIDEO_FILE="$1"
EPISODE_ID="$2"
TITLE="$3"
OUTPUT_DIR="/opt/ZONGYUAN-ROOT/drama_output"
MANIFEST_DIR="$OUTPUT_DIR/manifests"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

if [ -z "$VIDEO_FILE" ] || [ ! -f "$VIDEO_FILE" ]; then
  echo "ERROR: 视频文件不存在"
  exit 1
fi

# 1. 计算SHA256
SHA256=$(sha256sum "$VIDEO_FILE" | awk '{print $1}')
FILE_SIZE=$(stat -c%s "$VIDEO_FILE")
FILE_NAME=$(basename "$VIDEO_FILE")

# 2. 生成manifest JSON
MANIFEST_FILE="$MANIFEST_DIR/${EPISODE_ID}_${TIMESTAMP}.json"
cat > "$MANIFEST_FILE" << EOF
{
  "episode_id": "$EPISODE_ID",
  "title": "$TITLE",
  "file_name": "$FILE_NAME",
  "file_size": $FILE_SIZE,
  "sha256": "$SHA256",
  "archive_time": "$(date -Iseconds)",
  "did": "DID-BR-000002",
  "trace_symbol": "Ω₀⊂⊙∞⊂Ω",
  "status": "archived",
  "url": "https://www.huodouai.com/drama/videos/$FILE_NAME"
}
EOF

# 3. 复制到官网可访问目录
cp "$VIDEO_FILE" /www/wwwroot/huodouai.com/drama/videos/

echo "✅ 归档完成"
echo "  视频: $FILE_NAME ($FILE_SIZE bytes)"
echo "  SHA256: $SHA256"
echo "  Manifest: $MANIFEST_FILE"
echo "  外网URL: https://www.huodouai.com/drama/videos/$FILE_NAME"
