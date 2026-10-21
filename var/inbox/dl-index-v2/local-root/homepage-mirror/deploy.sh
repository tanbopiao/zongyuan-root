#!/bin/bash
set -e
cd /www/wwwroot/huodouai.com
LOG=/var/log/web-deploy.log
echo "[$(date)] === 开始部署 ===" >> $LOG

OLD_HEAD=$(git rev-parse HEAD)
echo "[$(date)] 旧版本: $OLD_HEAD" >> $LOG

git fetch origin web-deploy 2>>$LOG
git reset --hard origin/web-deploy 2>>$LOG
NEW_HEAD=$(git rev-parse HEAD)
echo "[$(date)] 新版本: $NEW_HEAD" >> $LOG

if [ "$OLD_HEAD" = "$NEW_HEAD" ]; then
  echo "[$(date)] 无更新，跳过" >> $LOG
  exit 0
fi

FAIL=0
for path in /hub/ /axiom/ /kunlun/ /truth-engine/ /cte/; do
  CODE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1$path)
  if [ "$CODE" != "200" ]; then
    echo "[$(date)] 验证失败: $path 返回 $CODE" >> $LOG
    FAIL=1
  fi
done

SENSITIVE=$(grep -rl '元极恒一\|超认知\|硅基生命\|黎曼流形' . --include='*.html' 2>/dev/null | grep -v '.bak' | grep -v 'backup' | wc -l)
if [ "$SENSITIVE" -gt 0 ]; then
  echo "[$(date)] 敏感词残留: $SENSITIVE 文件" >> $LOG
  FAIL=1
fi

if [ $FAIL -eq 1 ]; then
  echo "[$(date)] 验证失败，回滚到 $OLD_HEAD" >> $LOG
  git reset --hard $OLD_HEAD 2>>$LOG
  STATUS="rolledback"
else
  echo "[$(date)] 部署成功" >> $LOG
  STATUS="deployed"
fi

curl -s -X POST https://www.huodouai.com/api/report/truth \
  -H "Content-Type: application/json" \
  -d "{\"truth_key\":\"ARCH.DEPLOY.AUTO_${STATUS^^}\",\"truth_value\":\"部署$STATUS: $OLD_HEAD -> $NEW_HEAD, 敏感词$SENSITIVE\",\"source_node\":\"server-123.207.202.158\",\"confidence\":0.95,\"truth_type\":\"config\"}" > /dev/null

echo "[$(date)] === 部署结束: $STATUS ===" >> $LOG
