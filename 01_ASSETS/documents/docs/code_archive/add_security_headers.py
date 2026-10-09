#!/usr/bin/env python3
"""在Nginx配置的所有HTML location块中添加安全头"""

config_path = "/www/server/nginx/conf/sites/huodouai.com.conf"

security_headers = """        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header Referrer-Policy "strict-origin-when-cross-origin" always;
        add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;"""

with open(config_path, 'r') as f:
    content = f.read()

# 找到所有HTML location块，检查是否有安全头
# 模式：location ~* \.html$ { ... }
import re

# 找到所有HTML location块的位置
html_locations = list(re.finditer(r'location\s+~\*\s*\\?\.html\$\s*\{', content))

print(f"找到 {len(html_locations)} 个HTML location块")

for i, match in enumerate(html_locations):
    start = match.start()
    # 找到块的结束位置（匹配大括号）
    brace_count = 0
    end = start
    for j in range(start, len(content)):
        if content[j] == '{':
            brace_count += 1
        elif content[j] == '}':
            brace_count -= 1
            if brace_count == 0:
                end = j
                break
    
    block = content[start:end+1]
    
    # 检查是否已有安全头
    if 'Strict-Transport-Security' in block:
        print(f"  块{i+1}: 已有安全头，跳过")
    else:
        print(f"  块{i+1}: 无安全头，添加中...")
        # 在add_header Cache-Control行后插入安全头
        if 'add_header Cache-Control' in block:
            new_block = block.replace(
                'add_header Cache-Control',
                security_headers + '\n        add_header Cache-Control',
                1
            )
            content = content[:start] + new_block + content[end+1:]
            print(f"    ✅ 已添加安全头")
        else:
            print(f"    ⚠️  未找到Cache-Control行，手动检查")

with open(config_path, 'w') as f:
    f.write(content)

print("\n配置文件已更新")
print(f"安全头总数: {content.count('Strict-Transport-Security')}")
