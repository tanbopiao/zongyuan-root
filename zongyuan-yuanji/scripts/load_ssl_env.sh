#!/bin/bash
# ZONGYUAN-ROOT SSL 环境自动配置脚本

export SSL_CERT_FILE=/etc/pki/tls/certs/cacert.pem
export REQUESTS_CA_BUNDLE=/etc/pki/tls/certs/cacert.pem
export PYTHONHTTPSVERIFY=1

echo "✅ Python SSL 环境变量已加载"
echo "   CA 证书路径：$SSL_CERT_FILE"
echo ""

# 验证
python3 -c "
import urllib.request
try:
    r = urllib.request.urlopen('https://www.huodouai.com/dal/health', timeout=10)
    print(f'✅ HTTPS 连接正常：{r.read().decode(\"utf-8\")[:100]}')
except Exception as e:
    print(f'❌ HTTPS 连接失败：{e}')
"