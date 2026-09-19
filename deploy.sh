#!/bin/bash
cd /www/wwwroot/huodouai.com
git pull origin web-deploy
echo "[$(date)] 部署完成" >> /var/log/web-deploy.log
# 上报中枢
curl -s -X POST https://www.huodouai.com/api/report/truth   -H 'Content-Type: application/json'   -d "{\"truth_key\":\"ARCH.DEPLOY.AUTO_PULL\",\"truth_value\":\"自动部署完成\",\"source_node\":\"server-123.207.202.158\",\"confidence\":0.9,\"truth_type\":\"config\"}" > /dev/null
