#!/bin/bash
# 锁定基准，不更新
echo "=== CI巡检：锁定基准模式 ==="
echo "基准: seed_baseline_20261005_135800"
echo "策略: 只检查漂移，不更新基线"
python3 /root/zongyuan-yuanji/src/seed_verify.py 2>&1 | tail -5
echo "=== 完成 ==="
