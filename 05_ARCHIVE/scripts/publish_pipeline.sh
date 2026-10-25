#!/bin/bash
# ============================================================
# ZONGYUAN-ROOT 统一发布管线 publish_pipeline.sh
# P0-1: 脚本入库→适配预检→分发→远端验证→回执上报
# 依据 META-LAW-CLOUD-AUTONOMY-V1.0（禁硬编码跨环境路径）
# 用法: publish_pipeline.sh <源文件|目录> [云端目标相对路径]
# 例:   publish_pipeline.sh scripts/foo.py scripts/foo.py
# ============================================================
set -e
SRC="$1"; DEST="${2:-$(basename "$1")}"
REMOTE=/opt/ZONGYUAN-ROOT
TS=$(date +%Y%m%dT%H%M%S)
[ -z "$SRC" ] && { echo "用法: $0 <源文件|目录> [云端目标相对路径]"; exit 1; }
[ ! -e "$SRC" ] && { echo "[FAIL] 源不存在: $SRC"; exit 1; }

echo "=== P0-1 发布管线: $SRC -> $REMOTE/$DEST ==="

# ① 本地适配预检：跨环境路径残留
echo "--- ① 本地适配预检 ---"
BAD=$(grep -rlE '/home/user/Doubao|Doubao/chats' "$SRC" 2>/dev/null | grep -v "$(basename "$0")" | grep -vE '05_ARCHIVE|/docs/|/website/|01_ASSETS|\.bak' | head -10 || true)
if [ -n "$BAD" ]; then
  echo "[FAIL] 存在跨环境路径残留，禁止发布:"
  echo "$BAD"
  exit 2
fi
echo "预检通过: 无跨环境路径残留"

# ② 语法校验
echo "--- ② 语法校验 ---"
case "$SRC" in
  *.py) python3 -m py_compile "$SRC" && echo "py_compile OK" ;;
  *.sh) bash -n "$SRC" && echo "bash -n OK" ;;
esac

# ③ 分发到云端
echo "--- ③ 分发到云端 $REMOTE/$DEST ---"
ssh -o BatchMode=yes -o ConnectTimeout=8 huodouai-cloud "mkdir -p $REMOTE/$(dirname "$DEST")"
scp -o BatchMode=yes -q -r "$SRC" "huodouai-cloud:$REMOTE/$DEST"
echo "scp 完成"

# ④ 远端验证
echo "--- ④ 云端验证 ---"
ssh -o BatchMode=yes -o ConnectTimeout=8 huodouai-cloud "
  bash /usr/local/bin/cloud_env_selfheal.sh --check >/dev/null 2>&1 && echo '云端预检 PASS' || echo '云端预检 FAIL'
  case '$DEST' in
    *.py) python3 -m py_compile $REMOTE/$DEST 2>&1 && echo '远端 py_compile OK' ;;
    *.sh) bash -n $REMOTE/$DEST 2>&1 && echo '远端 bash -n OK' ;;
  esac
" 2>&1 | tail -2

# ⑤ 回执上报
echo "--- ⑤ 回执上报 ---"
curl -s -m 12 -X POST "https://www.huodouai.com/api/report/truth" \
  -H "Content-Type: application/json" -H "X-DID: DID-BR-000002" \
  -H "X-Capture-Token: ZR-CAPTURE-2026-OMEGA-d04bb54ba2a55a7d" \
  -d "{\"key\":\"PUBLISH-PIPELINE.$TS\",\"value\":{\"event\":\"publish pipeline\",\"src\":\"$SRC\",\"dest\":\"$REMOTE/$DEST\",\"metalaw\":\"META-LAW-CLOUD-AUTONOMY-V1.0\",\"did\":\"DID-BR-000002\"}}" | head -c 80
echo ""
echo "[DONE] 发布完成: $DEST"
