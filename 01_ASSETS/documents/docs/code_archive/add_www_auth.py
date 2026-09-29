#!/usr/bin/env python3
"""在www.huodouai.com的server块中也添加API鉴权和只读端点"""

conf_path = '/www/server/nginx/conf/sites/huodouai.com.conf'
API_KEY = "41d726948297035fb2828bcfab1f4abd52903a954e588d0e"

with open(conf_path, 'r') as f:
    content = f.read()

panel_config = """
    # ========== 记忆网关9120 /api/memory/ (需API Key) ==========
    location ^~ /api/memory/ {
        if ($http_x_api_key != "%s") {
            return 403;
        }
        proxy_pass http://127.0.0.1:9120/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 30s;
    }

    # ========== 记忆网关只读状态端点 (无需鉴权) ==========
    location = /api/v1/gateway/status {
        limit_except GET { deny all; }
        proxy_pass http://127.0.0.1:9120/api/status;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        add_header Cache-Control "max-age=60" always;
    }
""" % API_KEY

# 在www.huodouai.com的server_name后添加
www_marker = 'server_name www.huodouai.com;'
idx = content.find(www_marker)
if idx > 0:
    insert_pos = idx + len(www_marker)
    content = content[:insert_pos] + panel_config + content[insert_pos:]
    print("✅ www块已添加API鉴权和只读端点")
else:
    print("❌ 未找到www server_name")

with open(conf_path, 'w') as f:
    f.write(content)
