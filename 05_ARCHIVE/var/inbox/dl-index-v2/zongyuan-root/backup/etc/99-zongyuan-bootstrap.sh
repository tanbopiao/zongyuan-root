#!/bin/bash
# ZONGYUAN self-bootstrap anchor ｜ 重建于 2026-09-28 沙箱溯源
if [ -f /home/user/ZONGYUAN-ROOT/scripts/self_bootstrap.sh ]; then
  bash /home/user/ZONGYUAN-ROOT/scripts/self_bootstrap.sh >/dev/null 2>&1 || true
fi
