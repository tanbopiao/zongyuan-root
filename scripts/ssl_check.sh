#!/bin/bash
# ZONGYUAN-ROOT SSL证书到期检查脚本
# 每月1号自动执行

CERT1=/www/server/panel/vhost/cert/huodouai.com/fullchain.pem
CERT2=/www/server/panel/vhost/letsencrypt/www.huodouai.com/fullchain.pem

echo "=== SSL证书检查 $(date) ==="
for cert in $CERT1 $CERT2; do
  if [ -f "$cert" ]; then
    expiry=$(openssl x509 -in "$cert" -noout -enddate | cut -d= -f2)
    echo "$cert -> 到期日: $expiry"
  else
    echo "$cert -> 文件不存在"
  fi
done
echo "=== 检查完成 ==="
