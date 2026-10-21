#!/usr/bin/env bash
# ============================================================
# ZONGYUAN 实例全域检查 一键执行器 (run_scan.sh)
# 确权: Ω₀⊂⊙∞⊂Ω | DID-BR-000002
# 用法(在魔搭 CPU/GPU 实例终端, 一行搞定):
#   bash run_scan.sh
# 功能: 拉取扫描脚本(魔搭gpu-agent) → 执行全域扫描 → 自动上报ntfy
# 结果去向: ntfy 主题 zongyuan-kunlun-2026-scan (本地侧可接收)
# ============================================================
set -uo pipefail
echo "════════════════════════════════════════════"
echo "  ZONGYUAN 实例全域检查 · 一键执行器"
echo "════════════════════════════════════════════"

# 1) 拉取扫描脚本 (若本目录不存在则从魔搭数据湖拉)
SCAN_PY="scan_environment.py"
if [ ! -f "./$SCAN_PY" ]; then
  echo "[1/3] 从魔搭拉取扫描脚本..."
  rm -rf /tmp/zr_scan_pull && git clone --depth 1 --filter=blob:none --sparse \
    "https://modelscope.cn/datasets/zongyuanroot/ZONGYUAN-SHARED-DATALAKE.git" /tmp/zr_scan_pull 2>/dev/null
  cd /tmp/zr_scan_pull && git sparse-checkout set gpu-agent 2>/dev/null
  if [ -f "gpu-agent/$SCAN_PY" ]; then
    cp "gpu-agent/$SCAN_PY" /tmp/zr_scan_pull/ 2>/dev/null
    cd /tmp/zr_scan_pull
    echo "  ✅ 已拉取"
  else
    echo "  ⚠️ 拉取失败, 请确认网络/仓库可访问; 若脚本已在当前目录则继续"
  fi
fi

# 2) 执行全域扫描
echo "[2/3] 执行全域扫描 (系统/GPU/端口/进程/文件/依赖/网络)..."
python3 "$SCAN_PY" --ntfy

# 3) 完成提示
echo "[3/3] ✅ 扫描完成, 报告已存档 scan_report_<ts>.json 并上报 ntfy"
echo "  本地侧将收到扫描报告并规划联通方案"
