#!/usr/bin/env bash
# ============================================================================
# preflight_check.sh — 昆仑洞天关键帧画廊 部署前本地自检
# 在【本地】执行（不需要服务器通道），仅做只读检查：
#   1. 画廊 HTML 文件是否存在、大小是否合理
#   2. 解析内嵌帧数据（keyframes / modelscope 图片 URL）数量
#   3. 抽样 5 个图片 URL，验证 302→200 跳转链是否通畅
#   4. 检查页面是否含确权标识
# 退出码：0=全部通过；1=存在阻断项
# ============================================================================
set -euo pipefail

# ---- 默认画廊文件路径（可用环境变量覆盖）----
HTML_SRC="${HTML_SRC:-/home/user/Doubao/chats/1128121028098/kunlun-create-link/昆仑洞天作品关键帧画廊.html}"

PASS=0
FAIL=0
WARN=0

ok()   { echo "  ✅ $1"; PASS=$((PASS+1)); }
bad()  { echo "  ❌ $1"; FAIL=$((FAIL+1)); }
warn() { echo "  ⚠️  $1"; WARN=$((WARN+1)); }

echo "═══════════════════════════════════════════════════════"
echo "  昆仑洞天关键帧画廊 · 部署前自检"
echo "  HTML_SRC = $HTML_SRC"
echo "═══════════════════════════════════════════════════════"
echo ""

# ---------- 1. 文件存在性 ----------
echo "【1/4】画廊 HTML 文件检查"
if [ -f "$HTML_SRC" ]; then
    size=$(wc -c < "$HTML_SRC")
    lines=$(wc -l < "$HTML_SRC")
    ok "文件存在: $HTML_SRC ($((size/1024)) KB, ${lines} 行)"
    if [ "$size" -lt 10000 ]; then
        warn "文件偏小 (<10KB)，可能是模板未填充数据，请确认"
    fi
else
    bad "文件不存在: $HTML_SRC —— 请先确认画廊已生成，或 export HTML_SRC=正确路径"
    echo ""
    echo "自检未通过，终止。"
    exit 1
fi
echo ""

# ---------- 2. 帧数据 / 图片 URL 数量 ----------
echo "【2/4】内嵌帧数据与图片 URL 统计"
FRAME_COUNT=$(grep -oE 'keyframes' "$HTML_SRC" | wc -l || true)
IMG_URLS=$(grep -oE 'https://www\.modelscope\.cn/api/v1/datasets/[^"'"'"' ]+' "$HTML_SRC" | awk '!seen[$0]++' || true)
IMG_COUNT=$(echo "$IMG_URLS" | grep -c . || true)
echo "  keyframes 关键字出现次数: $FRAME_COUNT"
echo "  唯一 modelscope 图片 URL 数: $IMG_COUNT"
if [ "$IMG_COUNT" -ge 10 ]; then
    ok "图片 URL 数量充足 ($IMG_COUNT 张)"
else
    warn "图片 URL 数量偏少 ($IMG_COUNT)，画廊可能不完整"
fi
echo ""

# ---------- 3. 抽样 5 个图片 URL 验证 302→200 ----------
echo "【3/4】抽样 5 个图片 URL 可达性验证（302→200）"
SAMPLE=$(echo "$IMG_URLS" | head -5)
SAMPLE_NUM=0
while IFS= read -r u; do
    [ -z "$u" ] && continue
    SAMPLE_NUM=$((SAMPLE_NUM+1))
    first_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 -I "$u" 2>/dev/null || echo "000")
    final_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 15 -L "$u" 2>/dev/null || echo "000")
    if [ "$first_code" = "302" ] && [ "$final_code" = "200" ]; then
        ok "样本#${SAMPLE_NUM}: 302→200 ✓"
    elif [ "$final_code" = "200" ]; then
        warn "样本#${SAMPLE_NUM}: 首跳=$first_code 最终=200（非 302，但可访问）"
    else
        bad "样本#${SAMPLE_NUM}: 首跳=$first_code 最终=$final_code —— 图片不可访问！"
    fi
done <<< "$SAMPLE"
echo ""

# ---------- 4. 确权标识 ----------
echo "【4/4】确权标识内嵌检查"
for tag in "DID-BR-000002" "Ω₀⊂⊙∞⊂Ω" "ZONGYUAN-ROOT"; do
    if grep -qF "$tag" "$HTML_SRC"; then
        ok "内嵌标识: $tag"
    else
        warn "未找到标识: $tag（请确认画廊页脚/头部是否完整）"
    fi
done
echo ""

# ---------- 汇总 ----------
echo "═══════════════════════════════════════════════════════"
echo "  自检结果: ✅ 通过 $PASS 项 | ❌ 失败 $FAIL 项 | ⚠️  警告 $WARN 项"
echo "═══════════════════════════════════════════════════════"
if [ "$FAIL" -gt 0 ]; then
    echo "❌ 存在阻断项，请修复后再部署。"
    exit 1
else
    echo "✅ 自检通过（警告项可酌情处理），可以继续部署。"
    exit 0
fi
