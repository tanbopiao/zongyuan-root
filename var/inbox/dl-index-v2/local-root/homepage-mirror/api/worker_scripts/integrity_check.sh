#!/bin/bash
# integrity_check.sh 文件完整性校验
ROOT="/home/user/ZONGYUAN-ROOT"
HASH_FILE="$ROOT/.integrity.sha256"

# 首次生成基线
if [ ! -f "$HASH_FILE" ]; then
  find "$ROOT/operators" "$ROOT/hooks" "$ROOT/scripts" "$ROOT/卷宗" -type f -exec sha256sum {} \; > "$HASH_FILE"
  echo "基线已生成"
  exit 0
fi

# 校验
CHANGED=0
while read -r hash file; do
  if [ -f "$file" ]; then
    NOW=$(sha256sum "$file" | awk '{print $1}')
    if [ "$NOW" != "$hash" ]; then
      echo "篡改检测: $file"
      CHANGED=$((CHANGED+1))
    fi
  fi
done < "$HASH_FILE"

if [ $CHANGED -gt 0 ]; then
  curl -s -X POST https://www.huodouai.com/api/report/truth \
    -H "Content-Type: application/json" \
    -d "{\"truth_value\":\"完整性告警 篡改文件数:$CHANGED\",\"truth_type\":\"risk\"}" >/dev/null 2>&1
  echo "告警: $CHANGED 个文件被篡改"
else
  echo "完整性校验通过"
fi
