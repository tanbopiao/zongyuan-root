#!/bin/bash
echo 'SSL证书检查:'
echo 'huodouai.com:'
echo | openssl s_client -servername huodouai.com -connect huodouai.com:443 2>/dev/null | openssl x509 -noout -dates 2>/dev/null
echo 'www.huodouai.com:'
echo | openssl s_client -servername www.huodouai.com -connect www.huodouai.com:443 2>/dev/null | openssl x509 -noout -dates 2>/dev/null
