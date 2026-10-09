#!/usr/bin/env python3
# -*- coding: utf-8 -*-
conf_path = '/www/server/nginx/conf/sites/huodouai.com.conf'

with open(conf_path, 'r', encoding='utf-8') as f:
    content = f.read()

if '性能优化：缓存策略' in content:
    print('性能优化配置已存在，跳过')
else:
    perf_config = """
    # === 性能优化：缓存策略 ===
    # 静态资源长缓存
    location ~* \\.(css|js|jpg|jpeg|png|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
        access_log off;
    }

    # HTML页面短缓存
    location ~* \\.html$ {
        expires 1h;
        add_header Cache-Control "public, must-revalidate";
    }

    # sitemap和robots不缓存
    location = /sitemap.xml { expires -1; }
    location = /robots.txt { expires -1; }

    # Gzip压缩
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_comp_level 6;
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/javascript
        application/xml
        application/json
        application/rss+xml
        font/ttf
        font/otf
        image/svg+xml;

    # 安全头
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
"""

    marker = '    location / {'
    if marker in content:
        content = content.replace(marker, perf_config + '\n' + marker, 1)
        print('性能优化配置已插入')
    else:
        print('未找到插入点')

    with open(conf_path, 'w', encoding='utf-8') as f:
        f.write(content)
