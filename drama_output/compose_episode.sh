#!/bin/bash
# ZONGYUAN-ROOT 短剧单集合成脚本
# 用法: ./compose_episode.sh <EP_ID> <分镜JSON>
# 功能: 烧录中文字幕 → concat合成 → 归档 → 更新状态
set -e

EP_ID="$1"
STORYBOARD="$2"
DRAMA_ROOT="/opt/ZONGYUAN-ROOT/drama_output"
WWW_VIDEOS="/www/wwwroot/huodouai.com/drama/videos"
FONT="/usr/share/fonts/google-noto-cjk/NotoSansCJK-Regular.ttc"
FFMPEG="/usr/bin/ffmpeg"
STATE_FILE="$DRAMA_ROOT/manifests/drama_state.json"

if [ -z "$EP_ID" ] || [ -z "$STORYBOARD" ]; then
  echo "用法: $0 <EP_ID> <分镜JSON路径>"
  echo "示例: $0 EP01 /path/to/storyboard.json"
  exit 1
fi

WORK_DIR="$DRAMA_ROOT/tasks/compose_${EP_ID}_$(date +%s)"
mkdir -p "$WORK_DIR"
echo "=== 合成 $EP_ID ==="
echo "工作目录: $WORK_DIR"

# 提取该集旁白文本
python3 << PYEOF
import json
sb = json.load(open("$STORYBOARD"))
ep = next((e for e in sb["episodes"] if str(e["episode"]).zfill(2) == "$EP_ID".replace("EP","") or f"EP{str(e['episode']).zfill(2)}" == "$EP_ID"), None)
if not ep:
    # 尝试数字匹配
    ep_num = int("$EP_ID".replace("EP",""))
    ep = next((e for e in sb["episodes"] if e["episode"] == ep_num), None)
if not ep:
    print("ERROR: 未找到$EP_ID")
    exit(1)
for i, shot in enumerate(ep["shots"], 1):
    text = shot.get("narration", "").replace("'", "'\\''").replace('"', '\\"')
    with open(f"$WORK_DIR/sub_{i:02d}.txt", "w") as f:
        f.write(text)
    print(f"  镜{i}: {text[:30]}")
print(f"TITLE:{ep['title']}")
PYEOF

TITLE=$(python3 -c "
import json
sb=json.load(open('$STORYBOARD'))
ep_num=int('$EP_ID'.replace('EP',''))
ep=next((e for e in sb['episodes'] if e['episode']==ep_num),None)
print(ep['title'] if ep else 'unknown')
")

# 逐镜烧录字幕
SUBBED_LIST=""
for i in 1 2 3 4 5; do
  SRC_VIDEO="$DRAMA_ROOT/videos/${EP_ID}_S${i}_raw.mp4"
  if [ ! -f "$SRC_VIDEO" ]; then
    # 尝试其他命名
    SRC_VIDEO=$(find $DRAMA_ROOT/videos -name "${EP_ID}*S${i}*" -o -name "${EP_ID}*shot${i}*" 2>/dev/null | head -1)
  fi
  if [ -z "$SRC_VIDEO" ] || [ ! -f "$SRC_VIDEO" ]; then
    echo "ERROR: 镜${i}视频不存在，跳过合成"
    exit 1
  fi
  SUB_TEXT=$(cat "$WORK_DIR/sub_${i}.txt" 2>/dev/null)
  OUT_VIDEO="$WORK_DIR/seg_${i}.mp4"
  if [ -n "$SUB_TEXT" ]; then
    echo "  烧录字幕 镜${i}: $SRC_VIDEO"
    $FFMPEG -i "$SRC_VIDEO" -vf "drawtext=fontfile=$FONT:text='${SUB_TEXT}':fontsize=42:fontcolor=white:borderw=3:bordercolor=black@0.8:x=(w-text_w)/2:y=h-140" -c:a copy "$OUT_VIDEO" -y -loglevel error
  else
    cp "$SRC_VIDEO" "$OUT_VIDEO"
  fi
  SUBBED_LIST="$SUBBED_LIST $OUT_VIDEO"
done

# concat合成
CONCAT_FILE="$WORK_DIR/concat.txt"
> "$CONCAT_FILE"
for v in $SUBBED_LIST; do
  echo "file '$v'" >> "$CONCAT_FILE"
done
OUTPUT="$DRAMA_ROOT/videos/${EP_ID}_FINAL.mp4"
echo "  合成整集: $OUTPUT"
$FFMPEG -f concat -safe 0 -i "$CONCAT_FILE" -c copy "$OUTPUT" -y -loglevel error

# 归档
echo "  归档..."
bash $DRAMA_ROOT/archive_video.sh "$OUTPUT" "$EP_ID" "$TITLE"

# 更新状态
python3 << PYEOF
import json, os
state_file = "$STATE_FILE"
state = json.load(open(state_file)) if os.path.exists(state_file) else {"drama_id":"昆仑洞天","episodes":{}}
ep_id = "$EP_ID"
state.setdefault("episodes",{}).setdefault(ep_id,{})["status"] = "archived"
state["episodes"][ep_id]["composed_at"] = "$(date -Iseconds)"
state["episodes"][ep_id]["output"] = "$OUTPUT"
json.dump(state, open(state_file,"w"), ensure_ascii=False, indent=2)
print(f"  状态更新: {ep_id} = archived")
PYEOF

echo "=== $EP_ID 合成完成 ==="
echo "输出: $OUTPUT"
