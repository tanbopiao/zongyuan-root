#!/usr/bin/env python3
"""为短剧和政务Nginx配置添加API代理（HTTPS块）"""
import re

def fix_drama():
    conf_path = '/www/server/nginx/conf/sites/drama.huodouai.com.conf'
    with open(conf_path, 'r') as f:
        content = f.read()
    
    if content.count('/api/production/') >= 2:
        print('短剧: 已有代理，跳过')
        return
    
    matches = list(re.finditer(r'    location / \{', content))
    if len(matches) < 2:
        print('短剧: 未找到足够的location /')
        return
    
    last_match = matches[-1]
    insert = '''    # 短剧产线API (8628 完整版)
    location /api/production/ {
        proxy_pass http://127.0.0.1:8628/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 300s;
        client_max_body_size 500m;
    }

    # 短剧流水线API (8626)
    location /api/pipeline/ {
        proxy_pass http://127.0.0.1:8626/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 300s;
    }

'''
    content = content[:last_match.start()] + insert + content[last_match.start():]
    with open(conf_path, 'w') as f:
        f.write(content)
    print('短剧: HTTPS块已添加8628/8626代理')

def fix_gov():
    conf_path = '/www/server/nginx/conf/sites/gov.huodouai.com.conf'
    with open(conf_path, 'r') as f:
        content = f.read()
    
    if content.count('/gov-api/v1/') >= 2:
        print('政务: 已有代理，跳过')
        return
    
    matches = list(re.finditer(r'    location / \{', content))
    if len(matches) < 2:
        print('政务: 未找到足够的location /')
        return
    
    last_match = matches[-1]
    insert = '''    # 政务AI网关 (8200)
    location /gov-api/v1/ {
        proxy_pass http://127.0.0.1:8200/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 60s;
    }

    # 政务API服务 (8201)
    location /gov-api/service/ {
        proxy_pass http://127.0.0.1:8201/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 60s;
    }

    # 政务数据大屏 (8203)
    location /gov-api/dashboard/ {
        proxy_pass http://127.0.0.1:8203/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 60s;
    }

    # 政务主权根API (8031)
    location /gov-api/ {
        proxy_pass http://127.0.0.1:8031;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

'''
    content = content[:last_match.start()] + insert + content[last_match.start():]
    with open(conf_path, 'w') as f:
        f.write(content)
    print('政务: HTTPS块已添加8200/8201/8203代理')

if __name__ == '__main__':
    fix_drama()
    fix_gov()
    print('完成')
