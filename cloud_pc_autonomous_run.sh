#!/bin/bash
# 豆包云电脑自治执行节点 - 每日全域巡检
# DID-BR-000002 | Omega_0 subset Circle_Infinity subset Omega
cd /home/user/ZONGYUAN-ROOT
export PATH="/home/user/.local/bin:$PATH"
LOG="/home/user/ZONGYUAN-ROOT/logs/cloud_pc_autonomous_$(date +%Y%m%d).log"
mkdir -p logs
echo "=== $(date) 云电脑自治巡检开始 ===" >> "$LOG"
# 1. 增量监控（轻量模式，不启动服务）
if [ -f incremental_monitor.py ]; then
  python3 incremental_monitor.py --light-mode >> "$LOG" 2>&1
  echo "增量监控完成" >> "$LOG"
fi
# 2. 进化任务执行
if [ -f evolution_task_executor.py ]; then
  python3 evolution_task_executor.py --max-tasks 2 >> "$LOG" 2>&1
  echo "进化任务完成" >> "$LOG"
fi
# 3. 三态治理
if [ -f tri_state_processor.py ]; then
  python3 tri_state_processor.py process >> "$LOG" 2>&1
  echo "三态治理完成" >> "$LOG"
fi
# 4. Git同步
git add -A >> "$LOG" 2>&1
git commit -m "cloud-pc-autonomous: $(date +%Y%m%d_%H%M%S) 云电脑自治巡检同步" >> "$LOG" 2>&1
git push gitee master >> "$LOG" 2>&1
echo "=== $(date) 云电脑自治巡检完成 ===" >> "$LOG"
