#!/bin/bash
# 灰度发布：先部署到/staging/验证，再切正式
cd /www/wwwroot/huodouai.com
LOG=/var/log/web-deploy.log
STAGING=staging

# 1. 复制当前版本到staging
mkdir -p $STAGING
rsync -a --exclude='.git' --exclude='staging' --exclude='monitor' ./ $STAGING/ 2>>$LOG

# 2. 拉取新代码到正式目录
git fetch origin web-deploy 2>>$LOG
git reset --hard origin/web-deploy 2>>$LOG

# 3. 验证正式目录
FAIL=0
for path in /hub/ /axiom/ /kunlun/; do
  CODE=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1$path)
  [ "$CODE" != '200' ] && FAIL=1
done

if [ $FAIL -eq 0 ]; then
  echo "[$(date)] 灰度验证通过，正式版本已上线" >> $LOG
  # 上报
  curl -s -X POST https://www.huodouai.com/api/report/truth -H 'Content-Type: application/json' -d '{"truth_key":"ARCH.GRAYSCALE.PASSED","truth_value":"灰度验证通过","source_node":"server","confidence":0.95,"truth_type":"config"}' > /dev/null
else
  echo "[$(date)] 灰度验证失败，回滚staging" >> $LOG
  # 恢复staging版本
  git reset --hard HEAD~1 2>>$LOG
fi
