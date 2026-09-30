#!/bin/bash
# ============================================================
# tri_state_archive_hook.sh
# 三态合一自动归档钩子
# 功能：接收生成资源URL → 自动下载 → SHA256校验 → 元数据写入 → 哈希链确权
# 触发：图片/视频生成API返回后自动调用
# 用法：
#   ./tri_state_archive_hook.sh --type video --ep EP05 --url <URL> [--expire <TIME>] [--title <标题>]
#   ./tri_state_archive_hook.sh --type image --series jiutian --ep EP01 --seq 01 --url <URL> --desc <描述>
# ============================================================

set -e

ROOT="/home/user/.doubao/agent_mode/workspace/.user_skills/kunlun-autonomous-system/ZONGYUAN-ROOT"
HASH_LEDGER="/home/user/Doubao/chats/38418284746129666/HASH-LEDGER.csv"
META_ROOT="$ROOT/assets/media/jiutian_xuannu_video_meta/raw"
VIDEO_STORE="$ROOT/assets/media/jiutian_xuannu_video"
IMAGE_STORE="$ROOT/assets/images/jiutian_xuannu"
LOG_FILE="$ROOT/autoscripts/tri_state_hook/archive_hook.log"

# 参数解析
TYPE=""
EP=""
URL=""
EXPIRE=""
TITLE=""
DESC=""
SEQ=""
SERIES="jiutian_xuannu"

while [[ $# -gt 0 ]]; do
    case $1 in
        --type) TYPE="$2"; shift 2 ;;
        --ep) EP="$2"; shift 2 ;;
        --url) URL="$2"; shift 2 ;;
        --expire) EXPIRE="$2"; shift 2 ;;
        --title) TITLE="$2"; shift 2 ;;
        --desc) DESC="$2"; shift 2 ;;
        --seq) SEQ="$2"; shift 2 ;;
        --series) SERIES="$2"; shift 2 ;;
        *) echo "未知参数: $1"; exit 1 ;;
    esac
done

# 校验必填参数
if [ -z "$TYPE" ] || [ -z "$EP" ] || [ -z "$URL" ]; then
    echo "用法: $0 --type <video|image> --ep <EP_ID> --url <URL> [其他可选参数]"
    exit 1
fi

# 确定存储路径
if [ "$TYPE" = "video" ]; then
    STORE_DIR="$VIDEO_STORE/$EP"
    EXT="mp4"
    mkdir -p "$STORE_DIR"
    FILE_PATH="$STORE_DIR/$EP.$EXT"
    META_FILE="$META_ROOT/$EP.json"
elif [ "$TYPE" = "image" ]; then
    STORE_DIR="$IMAGE_STORE/$EP"
    EXT="png"
    mkdir -p "$STORE_DIR"
    SEQ_PAD=$(printf "%02d" "$SEQ")
    FILE_PATH="$STORE_DIR/${SEQ_PAD}_${TITLE}.$EXT"
    META_FILE="$META_ROOT/${EP}_keyframes.json"
else
    echo "不支持的类型: $TYPE (仅支持 video/image)"
    exit 1
fi

echo "========================================" >> "$LOG_FILE"
echo "[三态握手] $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG_FILE"
echo "  类型: $TYPE" >> "$LOG_FILE"
echo "  剧集: $EP" >> "$LOG_FILE"
echo "  URL: $URL" >> "$LOG_FILE"

# Step1: 下载资源
echo "[Step1] 下载$TYPE资源..." >> "$LOG_FILE"
wget -q -c -O "$FILE_PATH" "$URL"

if [ ! -f "$FILE_PATH" ]; then
    echo "[ERROR] 下载失败: $URL" >> "$LOG_FILE"
    exit 1
fi

FILE_SIZE=$(du -h "$FILE_PATH" | cut -f1)
echo "  文件大小: $FILE_SIZE" >> "$LOG_FILE"

# Step2: 计算SHA256
echo "[Step2] 计算SHA256..." >> "$LOG_FILE"
FILE_HASH=$(sha256sum "$FILE_PATH" | awk '{print $1}')
echo "  SHA256: $FILE_HASH" >> "$LOG_FILE"

# Step3: 更新/创建元数据
echo "[Step3] 写入元数据..." >> "$LOG_FILE"
mkdir -p "$(dirname "$META_FILE")"

if [ "$TYPE" = "video" ]; then
    if [ -f "$META_FILE" ]; then
        jq --arg fp "$FILE_PATH" \
           --arg fh "$FILE_HASH" \
           --arg fs "$FILE_SIZE" \
           --arg now "$(date -Iseconds)" \
           --arg url "$URL" \
           --arg expire "${EXPIRE:-unknown}" \
           '.local_archive=true
            | .local_file_path=$fp
            | .sha256=$fh
            | .file_size=$fs
            | .archived_at=$now
            | .download_url=$url
            | .expire_at=$expire
            | .status="local_archived"
            | .cdn_expired=false' \
           "$META_FILE" > "${META_FILE}.tmp" && mv "${META_FILE}.tmp" "$META_FILE"
    else
        cat > "$META_FILE" << EOF
{
  "series": "昆仑洞天·九天玄女",
  "episode": "$EP",
  "title": "$TITLE",
  "duration": "",
  "aspect_ratio": "9:16",
  "model": "Seedance 2.0 Mini",
  "task_id": "",
  "video_url": "$URL",
  "download_url": "$URL",
  "expire_at": "$EXPIRE",
  "status": "local_archived",
  "local_archive": true,
  "local_file_path": "$FILE_PATH",
  "sha256": "$FILE_HASH",
  "file_size": "$FILE_SIZE",
  "archived_at": "$(date -Iseconds)",
  "source_node": "NODE-DEV-DOUBAO-WORK-001",
  "did": "DID-BR-000002",
  "cdn_expired": false
}
EOF
    fi
else
    # 图片元数据
    if [ -f "$META_FILE" ]; then
        jq --arg fp "$FILE_PATH" \
           --arg fh "$FILE_HASH" \
           --arg seq "$SEQ" \
           --arg desc "$DESC" \
           --arg now "$(date -Iseconds)" \
           '.keyframes += [{seq:$seq, desc:$desc, file:$fp, sha256:$fh, archived_at:$now}]' \
           "$META_FILE" > "${META_FILE}.tmp" && mv "${META_FILE}.tmp" "$META_FILE"
    else
        cat > "$META_FILE" << EOF
{
  "series": "昆仑洞天·九天玄女",
  "episode": "$EP",
  "type": "keyframes",
  "keyframes": [
    {
      "seq": "$SEQ",
      "desc": "$DESC",
      "file": "$FILE_PATH",
      "sha256": "$FILE_HASH",
      "archived_at": "$(date -Iseconds)"
    }
  ],
  "source_node": "NODE-DEV-DOUBAO-WORK-001",
  "did": "DID-BR-000002"
}
EOF
    fi
fi

# Step4: 写入全局哈希链
echo "[Step4] 写入HASH-LEDGER..." >> "$LOG_FILE"
echo "$FILE_HASH  ${TYPE^^}/$EP/$(basename "$FILE_PATH")" >> "$HASH_LEDGER"

echo "[Step5] 归档完成" >> "$LOG_FILE"
echo "  本地路径: $FILE_PATH" >> "$LOG_FILE"
echo "  大小: $FILE_SIZE" >> "$LOG_FILE"
echo "  哈希: $FILE_HASH" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

# 输出归档结果（供逻辑态读取）
echo "✅ 三态握手完成"
echo "  类型: $TYPE"
echo "  剧集: $EP"
echo "  本地路径: $FILE_PATH"
echo "  文件大小: $FILE_SIZE"
echo "  SHA256: $FILE_HASH"
