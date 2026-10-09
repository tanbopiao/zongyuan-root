#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re

conf_path = '/www/server/nginx/conf/sites/huodouai.com.conf'
with open(conf_path, 'r', encoding='utf-8') as f:
    content = f.read()

redirect_rules = """
    # === 架构重构：旧URL 301重定向 ===
    location = /index-new.html { return 301 /; }
    location = /index-new-v2.html { return 301 /; }
    location ^~ /v2/ { return 301 /; }
"""

marker = 'location = /memory-gateway { return 301 /memory-gateway.html; }'
if marker in content:
    content = content.replace(marker, marker + redirect_rules, 1)
    print('重定向规则已插入到memory-gateway之后')
else:
    print('未找到标记，使用备用插入点')
    alt_marker = 'location ~ /\\.(env|git|htaccess|htpasswd|svn|DS_Store)'
    if alt_marker in content:
        content = content.replace(alt_marker, redirect_rules.lstrip() + '    ' + alt_marker, 1)
        print('已插入到安全规则之前')
    else:
        print('错误：未找到任何插入点')
        exit(1)

with open(conf_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('配置文件已保存')
