#!/usr/bin/env python3
"""修复Nginx 404状态码问题：静态文件不存在时返回404而非200"""

config_path = "/www/server/nginx/conf/sites/huodouai.com.conf"

with open(config_path, 'r') as f:
    content = f.read()

# 找到www.huodouai.com的server块中的location /块
# 在该块后添加静态文件404处理location
old_block = """    location / {
        root /www/wwwroot/www.huodouai.com;
        index index.html;
        try_files $uri $uri/ /index.html;
        # P0 缓存修复 (META-RULE-WEB-CACHE-001)
        add_header Cache-Control "no-cache, must-revalidate" always;
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header Referrer-Policy "strict-origin-when-cross-origin" always;
        add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;
        etag on;
    }"""

new_block = """    location / {
        root /www/wwwroot/www.huodouai.com;
        index index.html;
        try_files $uri $uri/ /index.html;
        # P0 缓存修复 (META-RULE-WEB-CACHE-001)
        add_header Cache-Control "no-cache, must-revalidate" always;
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header Referrer-Policy "strict-origin-when-cross-origin" always;
        add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;
        etag on;
    }

    # 静态文件404处理（不存在的静态资源返回404而非回退到index.html）
    location ~* \.(jpg|jpeg|png|gif|webp|ico|svg|css|js|woff|woff2|ttf|eot|json|xml|txt)$ {
        root /www/wwwroot/www.huodouai.com;
        try_files $uri =404;
        expires 30d;
        add_header Cache-Control "public, immutable";
        access_log off;
    }"""

if old_block in content:
    content = content.replace(old_block, new_block)
    print("✅ 已添加静态文件404处理location")
else:
    print("⚠️  未找到匹配的location /块，尝试其他方式...")
    # 尝试在location /块后插入
    import re
    pattern = r'(    location / \{\n        root /www/wwwroot/www\.huodouai\.com;\n        index index\.html;\n        try_files \$uri \$uri/ /index\.html;\n.*?\n    \})'
    match = re.search(pattern, content, re.DOTALL)
    if match:
        insert_pos = match.end()
        static_block = """

    # 静态文件404处理（不存在的静态资源返回404而非回退到index.html）
    location ~* \\.(jpg|jpeg|png|gif|webp|ico|svg|css|js|woff|woff2|ttf|eot|json|xml|txt)$ {
        root /www/wwwroot/www.huodouai.com;
        try_files $uri =404;
        expires 30d;
        add_header Cache-Control "public, immutable";
        access_log off;
    }"""
        content = content[:insert_pos] + static_block + content[insert_pos:]
        print("✅ 已通过正则匹配添加静态文件404处理")
    else:
        print("❌ 无法找到location /块，请手动检查")

with open(config_path, 'w') as f:
    f.write(content)

print("\n配置文件已更新")
