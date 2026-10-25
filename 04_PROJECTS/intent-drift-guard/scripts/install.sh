#!/usr/bin/env bash
# intent-drift-guard 安装脚本
# 用法: bash scripts/install.sh [--bge]   (--bge: 安装 BGE-m3 后端依赖)
set -euo pipefail
cd "$(dirname "$0")/.."

echo "[1/4] Python 版本检查 (要求 >= 3.9)"
python3 - <<'PY'
import sys
assert sys.version_info >= (3, 9), f"Python>=3.9 required, got {sys.version}"
print(f"  OK python {sys.version.split()[0]}")
PY

echo "[2/4] 核心语法编译检查 (纯标准库, 无必须依赖)"
python3 -m compileall -q intent_drift_guard
echo "  OK compileall"

echo "[3/4] 安装依赖"
if [[ "${1:-}" == "--bge" ]]; then
  python3 -m pip install -r requirements-bge.txt
  echo "  OK BGE-m3 后端依赖已安装"
else
  echo "  OK 核心零第三方依赖 (如需 BGE-m3: bash scripts/install.sh --bge)"
fi

echo "[4/4] 快速自检 (完整自测: python3 tests/selftest.py)"
PYTHONPATH=. python3 tests/selftest.py --quick
echo "安装完成."
