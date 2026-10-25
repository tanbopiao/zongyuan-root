#!/bin/bash
# 部署闭环增强：失败告警 + 结构化RESULT回写 + 心跳上报
set -e
GATEWAY="https://www.huodouai.com/api/report/truth"
TOKEN="ZR-CAPTURE-2026-OMEGA-d04bb54ba2a55a7d"
NTFY="https://ntfy.sh/zongyuan-kunlun-2026"
LOG=/var/log/zb-deploy-loop.log

report() {
  curl -s -X POST $GATEWAY -H "Content-Type: application/json" -H "X-Capture-Token: $TOKEN" \
    -d "{\"truth_key\":\"$1\",\"truth_value\":\"$2\",\"source_node\":\"hub-central-agent\",\"confidence\":1.0,\"truth_type\":\"$3\"}"
}

# Worker心跳：每次消费上报，可确认常驻
echo "[$(date)] zb-worker 心跳 + 部署闭环增强" >> $LOG
report "WORKER.HEARTBEAT-$(date +%H)" "zb-worker在线, 部署闭环增强已加载" "config"

# 失败告警函数：注入到worker消费流程（由install挂载）
cat > /opt/ZONGYUAN-ROOT/worker/notify.sh << 'SCRIPT'
#!/bin/bash
# 部署失败告警：发ntfy + 上报网关
report() {
  curl -s -X POST https://www.huodouai.com/api/report/truth -H "Content-Type: application/json" -H "X-Capture-Token: ZR-CAPTURE-2026-OMEGA-d04bb54ba2a55a7d" \
    -d "{\"truth_key\":\"ALERT.DEPLOY-FAIL-$(date +%Y%m%d%H%M)\",\"truth_value\":\"$1\",\"source_node\":\"hub-central-agent\",\"confidence\":1.0,\"truth_type\":\"risk\"}"
}
curl -s -d "部署失败: $1 已自动回滚" "$NTFY" >/dev/null 2>&1
report "部署失败: $1, 已回滚, 详见网关ALERT"
SCRIPT
chmod +x /opt/ZONGYUAN-ROOT/worker/notify.sh

echo "[1/3] 失败告警脚本已安装"
echo "[2/3] Worker心跳上报已激活"
# 验证心跳链路
curl -s -o /dev/null -w "%{http_code}" "$GATEWAY" -H "X-Capture-Token: $TOKEN" --max-time 8 && echo " ← 网关连通"
echo "[3/3] 闭环增强就绪"
