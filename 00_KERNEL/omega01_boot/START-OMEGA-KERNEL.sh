#!/usr/bin/env bash
# 元极恒一自治内核 · 一键启动入口
# DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω ｜ OMEGA-BOOT-V1.0
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BOOT_DIR="$REPO_ROOT/00_KERNEL/omega01_boot"
PY="${PYTHON:-python3}"

if [ ! -f "$BOOT_DIR/OMEGA-KERNEL-BOOT.json" ]; then
  echo "[OMEGA-BOOT] 未找到启动清单: $BOOT_DIR/OMEGA-KERNEL-BOOT.json" >&2
  exit 1
fi

MODE="${1:---dry-run}"
case "$MODE" in
  --dry-run|--activate) ;;
  *) echo "用法: $0 [--dry-run|--activate]" >&2; exit 2 ;;
esac

echo "[OMEGA-BOOT] 仓库根: $REPO_ROOT"
echo "[OMEGA-BOOT] 启动模式: $MODE"
exec "$PY" "$BOOT_DIR/omega_bootstrap.py" "$MODE"