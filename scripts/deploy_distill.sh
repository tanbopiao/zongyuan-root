#!/bin/bash
# deploy_distill.sh · 三维算力蒸馏引擎 全自动部署 (挂 cron + 首次运行)
# DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | 元极恒一 V11
R=/home/user/ZONGYUAN-ROOT
PY="$R/scripts/compute_distill_engine.py"

chmod 755 "$PY" "$R/scripts/deploy_distill.sh"

# 挂 cron: 每小时整点跑一次三维算力蒸馏 (防重复)
( crontab -l 2>/dev/null | grep -v 'compute_distill_engine'; \
  echo "0 * * * * python3 $PY --n 6 >> $R/logs/compute_distill.log 2>&1" ) | crontab -

echo "== cron =="
crontab -l | grep compute_distill_engine

# 首次运行: 端到端三维蒸馏闭环 (降级采样, 机制真实运行)
echo "== first run =="
python3 "$PY" --n 6
