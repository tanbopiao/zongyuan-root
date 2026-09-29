#!/usr/bin/env python3
"""安全加固脚本：补全安全头 + 敏感路径拦截"""
import os

SECURITY_HEADERS = '''    # 安全头
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Strict-Transport-Security "max-age=31536000" always;

    # 敏感路径拦截
    location ~ /\.(git|env|svn|hg|bak|old|orig|sql|conf|config)$ { deny all; return 404; }
    location ~* /(backup|backups|\.backup|\.git|\.env|\.svn)/ { deny all; return 404; }
    location ~* \.(bak|old|orig|save|swp|tmp|sql|conf|config|ini|log)$ { deny all; return 404; }

'''

SITES_DIR = '/www/server/nginx/conf/sites'
TARGET_SITES = ['kunlun.huodouai.com.conf', 'ops.huodouai.com.conf', 'api.huodouai.com.conf']

def add_security_to_https_block(filepath):
    with open(filepath, 'r') as f:
        content = f.read()
    
    if 'X-Frame-Options' in content:
        print(f'  {os.path.basename(filepath)}: 已有安全头，跳过')
        return False
    
    # 找到HTTPS server块中的 root 或 index 行之后插入
    # 找到第二个server块（HTTPS）
    servers = content.split('server {')
    if len(servers) >= 3:
        # 在HTTPS块（第三个部分，index 2）的root/index之后插入
        https_block = servers[2]
        # 找到root或index行
        lines = https_block.split('\n')
        insert_idx = None
        for i, line in enumerate(lines):
            if line.strip().startswith('root ') or line.strip().startswith('index '):
                insert_idx = i + 1
                # 继续找下一个非空行（可能是index行）
                while insert_idx < len(lines) and (lines[insert_idx].strip().startswith('index ') or lines[insert_idx].strip() == ''):
                    insert_idx += 1
                break
        
        if insert_idx:
            lines.insert(insert_idx, SECURITY_HEADERS)
            servers[2] = '\n'.join(lines)
            content = 'server {'.join(servers)
            with open(filepath, 'w') as f:
                f.write(content)
            print(f'  {os.path.basename(filepath)}: 已添加安全头和敏感路径拦截')
            return True
        else:
            print(f'  {os.path.basename(filepath)}: 未找到插入点')
            return False
    else:
        print(f'  {os.path.basename(filepath)}: server块结构异常')
        return False

if __name__ == '__main__':
    print('开始安全加固...')
    modified = 0
    for site in TARGET_SITES:
        filepath = os.path.join(SITES_DIR, site)
        if os.path.exists(filepath):
            if add_security_to_https_block(filepath):
                modified += 1
        else:
            print(f'  {site}: 文件不存在')
    print(f'\n完成，修改了{modified}个配置文件')
