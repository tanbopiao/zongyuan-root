#!/bin/bash
# ip_report.sh 上报当前IP到云端
IP=$(hostname -I | awk '{print $1}')
PUBLIC_IP=$(curl -s ifconfig.me 2>/dev/null)
curl -s -X POST https://www.huodouai.com/api/report/truth \
  -H "Content-Type: application/json" \
  -d "{\"truth_value\":\"本机IP: $IP 公网IP: $PUBLIC_IP\",\"truth_type\":\"data\"}" >/dev/null 2>&1
echo "IP上报: $IP / $PUBLIC_IP"
