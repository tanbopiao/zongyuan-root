#!/bin/bash
# SSL证书到期监控，到期前30天告警
EXPIRY=$(echo | openssl s_client -connect huodouai.com:443 -servername huodouai.com 2>/dev/null | openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2)
EXPIRY_TS=$(date -d "$EXPIRY" +%s)
NOW_TS=$(date +%s)
DAYS_LEFT=$(( (EXPIRY_TS - NOW_TS) / 86400 ))
echo "[$(date)] SSL证书剩余天数: $DAYS_LEFT天 (到期: $EXPIRY)" >> /opt/ZONGYUAN-ROOT/logs/ssl_monitor.log
if [ $DAYS_LEFT -le 30 ]; then
    echo "[$(date)] WARNING: SSL证书将在$DAYS_LEFT天后到期，请及时续期！" >> /opt/ZONGYUAN-ROOT/logs/ssl_monitor.log
fi
