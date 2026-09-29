#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os

WEB_ROOT = '/www/wwwroot/huodouai.com'
BASE_URL = 'https://huodouai.com'

# 跳过的页面（错误页、内部页）
SKIP_FILES = {'404.html', '500.html'}

def get_canonical_url(filepath):
    """根据文件路径生成canonical URL"""
    rel_path = os.path.relpath(filepath, WEB_ROOT)
    # 如果是index.html，转为目录路径
    if rel_path.endswith('index.html'):
        rel_path = os.path.dirname(rel_path) + '/'
        if rel_path == './':
            rel_path = '/'
    else:
        rel_path = '/' + rel_path
    return BASE_URL + rel_path

def add_canonical(filepath):
    filename = os.path.basename(filepath)
    if filename in SKIP_FILES:
        return False, '跳过（错误页）'
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return False, '读取失败: %s' % str(e)
    
    # 检查是否已有canonical
    if 'rel="canonical"' in content or "rel='canonical'" in content:
        return False, '已有canonical'
    
    canonical_url = get_canonical_url(filepath)
    canonical_tag = '<link rel="canonical" href="%s">' % canonical_url
    
    # 在</head>之前插入
    if '</head>' in content:
        content = content.replace('</head>', '    ' + canonical_tag + '\n</head>', 1)
    else:
        return False, '未找到head标签'
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True, canonical_url
    except Exception as e:
        return False, '写入失败: %s' % str(e)

def main():
    print('=' * 60)
    print('批量添加canonical标签')
    print('=' * 60)
    
    success = 0
    skipped = 0
    failed = 0
    
    # 遍历所有HTML文件
    for root, dirs, files in os.walk(WEB_ROOT):
        # 跳过备份目录和归档目录
        if '_backup' in root or '/archive' in root or '/v2/' in root:
            continue
        for filename in files:
            if not filename.endswith('.html'):
                continue
            filepath = os.path.join(root, filename)
            result, msg = add_canonical(filepath)
            if result:
                success += 1
                if success <= 10:
                    print('  OK %s -> %s' % (os.path.relpath(filepath, WEB_ROOT), msg))
            elif '已有' in msg or '跳过' in msg:
                skipped += 1
            else:
                failed += 1
                print('  FAIL %s - %s' % (filepath, msg))
    
    print()
    print('=' * 60)
    print('完成: 成功%d, 跳过%d, 失败%d' % (success, skipped, failed))
    print('=' * 60)

if __name__ == '__main__':
    main()
