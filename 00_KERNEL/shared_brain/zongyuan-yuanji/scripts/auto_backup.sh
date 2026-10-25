#!/bin/bash
TS=$(date +%Y%m%d-%H%M%S)
DIR=/root/backups
mkdir -p $DIR
# 打包wrapper+policies+frames列表
cd /root/zongyuan-yuanji
tar czf $DIR/yuanji-$TS.tar.gz src/wrapper.py src/api_router.py var/keys.json var/cache_stats.json 2>/dev/null
tar czf $DIR/gov-$TS.tar.gz -C /root/gov-mid/gov data/policies.json 2>/dev/null
# 只留最近7天
find $DIR -name "*.tar.gz" -mtime +7 -delete
echo "backup done: $TS"
ls -lh $DIR/*.tar.gz | tail -3
