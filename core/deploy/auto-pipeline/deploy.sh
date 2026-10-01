#!/bin/bash
# ZONGYUAN-ROOT 自动部署脚本
# 确权: DID-BR-000002 | Ω₀⊂⊙∞⊂Ω

REPO_DIR="/var/www/huodouai-website"
LOG_FILE="/var/log/zongyuan-deploy.log"

echo "[$(date)] === 自动部署开始 ===" >> "$LOG_FILE"

# 1. 拉取最新代码
cd "$REPO_DIR"
echo "[$(date)] 拉取 web-deploy 分支..." >> "$LOG_FILE"
git pull origin web-deploy >> "$LOG_FILE" 2>&1

# 2. 部署静态文件
echo "[$(date)] 部署静态文件..." >> "$LOG_FILE"
# Nginx 直接从 repo 目录提供服务，无需额外拷贝

# 3. 健康检查
echo "[$(date)] 健康检查..." >> "$LOG_FILE"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/drama/works_data.json)
if [ "$HTTP_CODE" = "200" ]; then
    echo "[$(date)] ✅ 健康检查通过" >> "$LOG_FILE"
    STATUS="success"
else
    echo "[$(date)] ❌ 健康检查失败: HTTP $HTTP_CODE" >> "$LOG_FILE"
    STATUS="failed"
fi

# 4. 上报真值
curl -s --max-time 10 -X POST https://www.huodouai.com/api/report/truth \
  -H "Content-Type: application/json" \
  -H "X-DID: DID-BR-000002" \
  -d "{\"truth_key\":\"DEPLOY.AUTO.COMPLETED\",\"truth_value\":\"$STATUS\",\"source_node\":\"NODE-CLOUD-HUB-001\",\"confidence\":0.99,\"truth_type\":\"deploy\"}" >> /dev/null

echo "[$(date)] === 自动部署完成: $STATUS ===" >> "$LOG_FILE"
