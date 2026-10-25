#!/bin/bash
# 每次自动固化成果为基底
DATE=$(date +%Y%m%d)
cd /root/zongyuan-yuanji
tar -czf /root/zongyuan-yuanji/var/baseline/baseline-$DATE.tar.gz src/ var/laws/ scripts/
echo "$(date) baseline saved" >> /root/zongyuan-yuanji/var/baseline.log
