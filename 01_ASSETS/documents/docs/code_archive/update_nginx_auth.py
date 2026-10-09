#!/usr/bin/env python3
"""修改Nginx配置：增加API鉴权 + 只读端点"""
import re

conf_path = '/www/server/nginx/conf/sites/huodouai.com.conf'
API_KEY = "41d726948297035fb2828bcfab1f4abd52903a954e588d0e"

with open(conf_path, 'r') as f:
    content = f.read()

# ===== 任务1：为/api/memory/增加X-API-Key鉴权 =====
old_memory = """    # ========== 记忆网关9120 /api/memory/ ==========
    location ^~ /api/memory/ {
        proxy_pass http://127.0.0.1:9120/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 30s;
    }"""

new_memory = """    # ========== 记忆网关9120 /api/memory/ (需API Key) ==========
    location ^~ /api/memory/ {
        # 所有公网访问必须携带X-API-Key
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
    }""" % API_KEY

if old_memory in content:
    content = content.replace(old_memory, new_memory)
    print("✅ /api/memory/ 已增加鉴权 + /api/v1/gateway/status 只读端点")
else:
    print("⚠️ 未找到原始/api/memory/配置，尝试模糊匹配")
    # 模糊匹配
    pattern = r'(# ========== 记忆网关9120.*?\n    location \^~ /api/memory/ \{.*?\n    \})'
    match = re.search(pattern, content, re.DOTALL)
    if match:
        content = content.replace(match.group(1), new_memory.strip())
        print("✅ 模糊匹配替换成功")
    else:
        print("❌ 无法找到配置块，请手动检查")

with open(conf_path, 'w') as f:
    f.write(content)

print("配置已写入")
