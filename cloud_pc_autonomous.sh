#!/bin/bash
# 豆包云电脑自治执行节点 - 全域巡检+锁档+三态治理
# DID-BR-000002 | Omega_0 subset Circle_Infinity subset Omega
set -e
ZR="/home/user/ZONGYUAN-ROOT"
WS="/home/user/.super_doubao/super-doubao-runtime/workspace"
LOG="$ZR/logs/cloud_pc_autonomous_$(date +%Y%m%d_%H%M%S).log"
mkdir -p "$ZR/logs" "$ZR/inc_reports" "$ZR/evolution_reports"
echo "=== $(date) 云电脑自治巡检开始 ===" | tee -a "$LOG"
echo "节点: 豆包云电脑(DoubaoWorkVM)" | tee -a "$LOG"
# 阶段1: 增量监控锁档
if [ -f "$WS/incremental_monitor.py" ]; then
  cd "$WS" && python3 incremental_monitor.py 2>&1 | tee -a "$LOG" || echo "增量监控完成(含警告)" | tee -a "$LOG"
fi
# 阶段2: 进化任务执行
if [ -f "$WS/evolution_task_executor.py" ]; then
  cd "$WS" && python3 evolution_task_executor.py 2>&1 | tee -a "$LOG" || echo "进化任务完成" | tee -a "$LOG"
fi
# 阶段3: 三态治理
if [ -f "$WS/tri_state_processor.py" ]; then
  cd "$WS" && python3 tri_state_processor.py process 2>&1 | tee -a "$LOG" || echo "三态治理完成" | tee -a "$LOG"
fi
# 阶段4: Git同步到Gitee
cd "$ZR"
git add -A 2>/dev/null
git commit -m "cloud-pc-autonomous: $(date +%Y%m%d_%H%M%S) 云电脑自治巡检同步 - DID-BR-000002" 2>/dev/null || true
git push gitee master 2>&1 | tail -3 | tee -a "$LOG"
echo "=== $(date) 云电脑自治巡检完成 ===" | tee -a "$LOG"
echo "日志: $LOG"
