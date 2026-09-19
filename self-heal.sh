#!/bin/bash
# 自愈系统：自动检测问题并修复
cd /www/wwwroot/huodouai.com
LOG=/var/log/self-heal.log
echo "[$(date)] === 自愈检查 ===" >> $LOG
ACTIONS=0

# 1. 检查Nginx是否运行
if ! systemctl is-active nginx | grep -q active; then
  echo "[$(date)] Nginx未运行，重启" >> $LOG
  systemctl start nginx
  ACTIONS=$((ACTIONS+1))
fi

# 2. 检查磁盘空间
USAGE=$(df / | awk 'NR==2{print $5}' | tr -d '%')
if [ $USAGE -gt 90 ]; then
  echo "[$(date)] 磁盘${USAGE}%，清理日志" >> $LOG
  find /var/log -name '*.log' -mtime +7 -delete 2>/dev/null
  journalctl --vacuum-time=3d 2>/dev/null
  ACTIONS=$((ACTIONS+1))
fi

# 3. 检查Git仓库是否损坏
if ! git fsck 2>/dev/null | grep -q error; then
  echo "[$(date)] Git仓库正常" >> $LOG
else
  echo "[$(date)] Git仓库损坏，重新clone" >> $LOG
  git fetch origin web-deploy 2>/dev/null
  git reset --hard origin/web-deploy 2>/dev/null
  ACTIONS=$((ACTIONS+1))
fi

# 4. 检查deploy.sh是否可执行
if [ ! -x deploy.sh ]; then
  chmod +x deploy.sh
  echo "[$(date)] 修复deploy.sh权限" >> $LOG
  ACTIONS=$((ACTIONS+1))
fi

# 5. 检查记忆网关API
if ! curl -s --max-time 3 http://127.0.0.1:9120/ | grep -q healthy; then
  echo "[$(date)] 记忆网关异常，重启" >> $LOG
  # 找到网关进程并重启
  pkill -f '9120.*gateway' 2>/dev/null
  sleep 2
  cd /opt/ZONGYUAN-ROOT && nohup python3 -m adapters.comm_protocol.gateway_server >> /dev/null 2>&1 &
  ACTIONS=$((ACTIONS+1))
fi

echo "[$(date)] 自愈完成: $ACTIONS个修复" >> $LOG

# 有修复时上报
if [ $ACTIONS -gt 0 ]; then
  curl -s -X POST https://www.huodouai.com/api/report/truth     -H 'Content-Type: application/json'     -d "{\"truth_key\":\"ARCH.SELF_HEAL.REPAIRED\",\"truth_value\":\"自愈系统修复$ACTIONS个问题\",\"source_node\":\"server-123.207.202.158\",\"confidence\":0.9,\"truth_type\":\"config\"}" > /dev/null
fi
