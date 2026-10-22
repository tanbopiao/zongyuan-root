#!/bin/bash
# 智能备份：只备份核心，不备份模型
TS=$(date +%Y%m%d)
DEST=/root/backups/core
mkdir -p $DEST
tar czf $DEST/core-$TS.tar.gz \
  --exclude='/opt/ZONGYUAN-ROOT/var/inbox/dl-index-v2' \
  --exclude='/opt/ZONGYUAN-ROOT/var/whitepaper-repo/media-library' \
  /root/zongyuan-yuanji/src   /root/zongyuan-yuanji/var   /root/zongyuan-yuanji/train_data   /www/wwwroot/huodouai.com/zhongshu/data/truth/truth.db   /www/wwwroot/huodouai.com/kunlun/frames   /root/gov-mid/gov/data   /opt/ZONGYUAN-ROOT   2>/dev/null
# 留7天
find $DEST -name 'core-*.tar.gz' -mtime +7 -delete
echo "backup done: $(ls -lh $DEST/core-$TS.tar.gz | awk '{print $5}')"
