# 官网主页阶段B产品化升级（2026-10-10）
- 试用网关 try_gateway.py：:18090 → ARK Doubao-Seed-2.1-turbo(ep-20261008171222-97c7z)，系统提示注入体系身份，限流每IP每10分钟5次
- 公网 /try/chat：nginx location /try/ 反代（语法检查通过，配置备份 nginx.conf.bak_try_*）
- 试用页 /zr-agent-suite/try.html：黑金东方美学，真实对话+快捷问题+申请入口(→/gov/)；DeepSeek-Flash 因 reasoning 占满token弃用，切豆包
- zr-agent-suite 6处僵尸toast CTA → 真实链接（申请/洽谈→/gov/，立即试用→try.html）
- products.html 新增 ZR 自治内核专区（套餐/试用/中枢/申请治理）4卡 + 尾注商业化
- 验证：三页 HTTP200；端到端真实回复；限流 200-200-429-429-429-429；shot.py lint 0 console 错误
- 云端文件：/www/wwwroot/huodouai.com/{zr-agent-suite/{index,try}.html,products.html}；网关 /usr/local/bin/try_gateway.py
