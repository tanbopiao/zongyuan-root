#!/usr/bin/env bash
# FM-Core 模型资产拉取脚本
# 用法：./fetch_models.sh
# 逻辑：文件已存在且尺寸符合预期 → 跳过；缺失 → 多源下载并校验尺寸。
set -uo pipefail
cd "$(dirname "$0")"
mkdir -p model

MIRROR="${HF_MIRROR:-https://hf-mirror.com}"
FALLBACK="https://huggingface.co"

# 名称 | 目标相对路径 | 预期字节数 | 源repo | 源相对路径
ASSETS=(
  "bge-small-zh ONNX(int8)|model/bge-small-zh-int8.onnx|23903394|Xenova/bge-small-zh-v1.5|onnx/model_int8.onnx"
  "bge tokenizer.json|model/tokenizer.json|439125|Xenova/bge-small-zh-v1.5|tokenizer.json"
  "bge vocab.txt|model/vocab.txt|109540|Xenova/bge-small-zh-v1.5|vocab.txt"
  "MiniMind2 Q4_K_M GGUF|model/minimind2-Q4_K_M.gguf|66418688|jingyaogong/MiniMind2-gguf|minimind2-Q4_K_M.gguf"
)

fetch_one() {
  local label="$1" dest="$2" want="$3" repo="$4" src="$5"
  if [ -f "$dest" ]; then
    local got; got=$(stat -c%s "$dest" 2>/dev/null || echo 0)
    if [ "$got" = "$want" ]; then echo "[跳过] $label 已就位 ($got bytes)"; return 0; fi
    echo "[重下] $label 尺寸不符 ($got/$want)"
    rm -f "$dest"
  fi
  for base in "$MIRROR" "$FALLBACK"; do
    local url="$base/$repo/resolve/main/$src"
    echo "[下载] $label <- $url"
    if curl -fL --retry 3 --retry-delay 2 --max-time 900 -o "$dest" "$url"; then
      local got; got=$(stat -c%s "$dest" 2>/dev/null || echo 0)
      if [ "$got" = "$want" ]; then echo "[完成] $label ($got bytes)"; return 0; fi
      echo "[校验失败] $label 尺寸 $got ≠ 预期 $want"
      rm -f "$dest"
    fi
  done
  echo "[失败] $label —— 两个源都不可用。请手工取得文件放入 $dest（预期 $want 字节）。"
  return 1
}

rc=0
for row in "${ASSETS[@]}"; do
  IFS='|' read -r label dest want repo src <<< "$row"
  fetch_one "$label" "$dest" "$want" "$repo" "$src" || rc=1
done

echo
if [ "$rc" = 0 ]; then
  echo "[OK] 模型资产齐全，可启动服务。"
  head -c 4 model/minimind2-Q4_K_M.gguf | od -An -c | head -1
else
  echo "[WARN] 部分资产缺失，fm_agent 启动会报错。"
fi
exit $rc
