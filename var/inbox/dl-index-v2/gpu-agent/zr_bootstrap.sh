#!/bin/bash
# ============================================================
# ZR-BOOTSTRAP 同源节点自启动引导 V1.0
# 用途: 写入crontab保活(worker掉线自动拉起) + 立即启动worker
# 位置: /mnt/workspace/zr_bootstrap.sh (持久层, 容器重建保留)
# 协议: NTFY-CONNECT-001 V1.4
# ============================================================
set -e
cd /mnt/workspace

# 1. 保活方案: 优先crontab, 不可用则降级supervisor (容器内常无crontab)
if command -v crontab >/dev/null 2>&1; then
  cat > /tmp/zr_cron.txt << 'EOF'
*/2 * * * * pgrep -f "zr_node_worker.py" >/dev/null || (cd /mnt/workspace && nohup python3 zr_node_worker.py >> worker_stdout.log 2>&1 &)
@reboot sleep 10 && bash /mnt/workspace/zr_bootstrap.sh
EOF
  crontab /tmp/zr_cron.txt 2>/dev/null && echo "保活: crontab 已安装(2分钟) + @reboot自启"
else
  # crontab 不可用 -> 启动 supervisor 保活守护 (while循环, 每60s)
  if ! pgrep -f "zr_supervisor.sh" >/dev/null 2>&1; then
    nohup bash /mnt/workspace/zr_supervisor.sh >> /mnt/workspace/supervisor.log 2>&1 &
    echo "保活: supervisor 守护已启动 (PID $!)"
  else
    echo "保活: supervisor 已在运行"
  fi
fi

# 2. 检查凭证目录 (持久层)
mkdir -p /mnt/workspace/.zr
chmod 700 /mnt/workspace/.zr
if [ -f /mnt/workspace/.zr/node_token.env ]; then
  echo "凭证: /mnt/workspace/.zr/node_token.env 已就位"
else
  echo "凭证: 未找到节点token, 请执行注入命令"
fi

# 3. 立即启动worker (若未运行)
if pgrep -f "zr_node_worker.py" >/dev/null 2>&1; then
  echo "worker: 已在运行 (PID $(pgrep -f 'zr_node_worker.py' | head -1))"
else
  nohup python3 zr_node_worker.py >> worker_stdout.log 2>&1 &
  sleep 2
  if pgrep -f "zr_node_worker.py" >/dev/null 2>&1; then
    echo "worker: 已启动 (PID $(pgrep -f 'zr_node_worker.py' | head -1))"
  else
    echo "worker: 启动失败, 检查 worker_stdout.log"
  fi
fi

echo "ZR-BOOTSTRAP-DONE"
