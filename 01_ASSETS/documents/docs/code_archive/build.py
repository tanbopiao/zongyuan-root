#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
火斗云智 AIOS - 静态站点生成器 (SSG)
基于 Jinja2 + Markdown，轻量级无Node.js依赖
"""
import os
import re
import shutil
import markdown
from jinja2 import Environment, FileSystemLoader

# 配置
BASE_DIR = '/opt/huodouai-ssg'
SRC_DIR = os.path.join(BASE_DIR, 'src')
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')
COMPONENTS_DIR = os.path.join(SRC_DIR, 'components')
LAYOUTS_DIR = os.path.join(SRC_DIR, 'layouts')
CONTENT_DIR = os.path.join(SRC_DIR, 'content')
ASSETS_DIR = os.path.join(SRC_DIR, 'assets')

BASE_URL = 'https://huodouai.com'

def parse_front_matter(text):
    """解析Markdown文件的YAML front matter"""
    match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)', text, re.DOTALL)
    if not match:
        return {}, text
    
    fm_text = match.group(1)
    content = match.group(2)
    
    metadata = {}
    current_key = None
    for line in fm_text.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        # 列表项
        if line.startswith('- ') and current_key:
            if isinstance(metadata.get(current_key), list):
                metadata[current_key].append(line[2:].strip().strip('"').strip("'"))
            continue
        # key: value
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if value == '':
                metadata[key] = []
                current_key = key
            else:
                metadata[key] = value
                current_key = None
    
    return metadata, content

def build_markdown_page(md_path, rel_path, env):
    """构建单个Markdown页面"""
    with open(md_path, 'r', encoding='utf-8') as f:
        text = f.read()
    
    metadata, md_content = parse_front_matter(text)
    
    # Markdown转HTML
    html_content = markdown.markdown(
        md_content,
        extensions=['extra', 'codehilite', 'toc', 'tables', 'fenced_code']
    )
    
    # 确定输出路径
    if rel_path.startswith('blog/'):
        output_rel = rel_path.replace('.md', '.html')
        active_page = 'blog'
    elif rel_path.startswith('whitepapers/'):
        output_rel = rel_path.replace('.md', '.html')
        active_page = 'whitepapers'
    else:
        output_rel = rel_path.replace('.md', '.html')
        active_page = metadata.get('category', '')
    
    # 渲染模板
    template = env.get_template('post.html')
    html = template.render(
        title=metadata.get('title', '未命名'),
        description=metadata.get('description', ''),
        keywords=','.join(metadata.get('tags', [])),
        canonical=metadata.get('canonical', BASE_URL + '/' + output_rel),
        content=html_content,
        metadata=metadata,
        active_page=active_page,
        date=metadata.get('date', ''),
        author=metadata.get('author', ''),
        tags=metadata.get('tags', [])
    )
    
    # 写入输出
    output_path = os.path.join(OUTPUT_DIR, output_rel)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    return output_rel, metadata

def copy_assets():
    """复制静态资源"""
    if os.path.exists(ASSETS_DIR):
        for item in os.listdir(ASSETS_DIR):
            src = os.path.join(ASSETS_DIR, item)
            dst = os.path.join(OUTPUT_DIR, item)
            if os.path.isdir(src):
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)

def main():
    print('=' * 60)
    print('火斗云智 AIOS - 静态站点生成器')
    print('=' * 60)
    print()
    
    # 清理输出目录
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR)
    
    # 配置Jinja2
    env = Environment(
        loader=FileSystemLoader([LAYOUTS_DIR, COMPONENTS_DIR, SRC_DIR]),
        autoescape=False
    )
    
    # 构建Markdown页面
    pages = []
    for root, dirs, files in os.walk(CONTENT_DIR):
        for filename in files:
            if not filename.endswith('.md') or filename.startswith('_'):
                continue
            md_path = os.path.join(root, filename)
            rel_path = os.path.relpath(md_path, CONTENT_DIR)
            output_rel, metadata = build_markdown_page(md_path, rel_path, env)
            pages.append((output_rel, metadata))
            print('  构建: %s -> %s' % (rel_path, output_rel))
    
    # 复制静态资源
    copy_assets()
    
    print()
    print('=' * 60)
    print('构建完成: %d 个页面' % len(pages))
    print('输出目录: %s' % OUTPUT_DIR)
    print('=' * 60)
    
    # 列出输出
    print()
    print('输出文件:')
    for root, dirs, files in os.walk(OUTPUT_DIR):
        for f in sorted(files):
            rel = os.path.relpath(os.path.join(root, f), OUTPUT_DIR)
            size = os.path.getsize(os.path.join(root, f))
            print('  %s (%d bytes)' % (rel, size))

if __name__ == '__main__':
    main()
