#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import datetime
from urllib.parse import quote

WEB_ROOT = '/www/wwwroot/huodouai.com'
BASE_URL = 'https://huodouai.com'
SITEMAP_PATH = os.path.join(WEB_ROOT, 'sitemap.xml')

# 排除的目录
EXCLUDE_DIRS = {'archive', 'v2', '_backup_nav_inject', 'backup', '.git', 'node_modules'}

# 高优先级页面（首页、产品页等）
HIGH_PRIORITY = {'', 'index.html', 'products.html', 'solutions.html', 'architecture.html', 
                 'whitepaper.html', 'pricing.html', 'book-demo.html', 'about-line.html',
                 'contact/index.html', 'products/index.html', 'solutions/index.html',
                 'architecture/index.html', 'whitepapers/index.html', 'docs/index.html',
                 'blog/index.html', 'gov-ai/index.html', 'workbench/index.html',
                 'drama/kunlun/index.html'}

# 中优先级页面
MEDIUM_PRIORITY = {'vector.html', 'kb-saas.html', 'gov-line.html', 'kunlun-drama.html',
                   'ai-gateway.html', 'token-gateway.html', 'dlp-gateway.html',
                   'notary-api.html', 'ai-asset-lock.html', 'cases.html', 'compare.html',
                   'roadmap.html', 'roi-calculator.html', 'philosophy.html', 'research.html',
                   'education.html', 'knowledge.html', 'developers.html', 'docs.html',
                   'blog.html', 'opensource.html', 'security-compliance.html',
                   'high-order-state.html', 'microkernel-architecture.html',
                   'decision-intelligence.html', 'startup-loop-defense-whitepaper.html'}

def get_url_priority(rel_path):
    """根据页面路径设置优先级"""
    if rel_path in HIGH_PRIORITY or rel_path == '':
        return '1.0', 'weekly'
    if rel_path in MEDIUM_PRIORITY:
        return '0.8', 'monthly'
    # 产品子页面
    if rel_path.startswith('products/') or rel_path.startswith('solutions/'):
        return '0.8', 'monthly'
    # 博客文章
    if rel_path.startswith('blog/') and rel_path != 'blog/index.html':
        return '0.7', 'yearly'
    # 白皮书
    if 'whitepaper' in rel_path:
        return '0.7', 'yearly'
    # 文档
    if rel_path.startswith('docs/'):
        return '0.6', 'monthly'
    # 默认
    return '0.5', 'monthly'

def get_lastmod(filepath):
    """获取文件最后修改时间"""
    mtime = os.path.getmtime(filepath)
    return datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d')

def generate_sitemap():
    urls = []
    
    for root, dirs, files in os.walk(WEB_ROOT):
        # 排除目录
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not d.startswith('.')]
        
        for filename in files:
            if not filename.endswith('.html'):
                continue
            # 跳过错误页
            if filename in ('404.html', '500.html'):
                continue
            
            filepath = os.path.join(root, filename)
            rel_path = os.path.relpath(filepath, WEB_ROOT)
            
            # 转换为URL路径
            if rel_path.endswith('index.html'):
                url_path = os.path.dirname(rel_path)
                if url_path == '.':
                    url_path = ''
                else:
                    url_path = url_path + '/'
            else:
                url_path = rel_path
            
            # 构建完整URL
            url = BASE_URL + '/' + quote(url_path) if url_path else BASE_URL + '/'
            
            priority, changefreq = get_url_priority(rel_path)
            lastmod = get_lastmod(filepath)
            
            urls.append({
                'loc': url,
                'lastmod': lastmod,
                'changefreq': changefreq,
                'priority': priority
            })
    
    # 按优先级排序
    urls.sort(key=lambda x: -float(x['priority']))
    
    # 生成XML
    xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml_content += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    
    for u in urls:
        xml_content += '  <url>\n'
        xml_content += '    <loc>%s</loc>\n' % u['loc']
        xml_content += '    <lastmod>%s</lastmod>\n' % u['lastmod']
        xml_content += '    <changefreq>%s</changefreq>\n' % u['changefreq']
        xml_content += '    <priority>%s</priority>\n' % u['priority']
        xml_content += '  </url>\n'
    
    xml_content += '</urlset>\n'
    
    with open(SITEMAP_PATH, 'w', encoding='utf-8') as f:
        f.write(xml_content)
    
    return len(urls)

def main():
    print('=' * 60)
    print('自动生成sitemap.xml')
    print('=' * 60)
    
    count = generate_sitemap()
    print('已生成 %d 个URL条目' % count)
    print('文件路径: %s' % SITEMAP_PATH)
    print('文件大小: %d bytes' % os.path.getsize(SITEMAP_PATH))
    print()
    
    # 显示前10条
    print('前10条URL:')
    with open(SITEMAP_PATH, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        loc_count = 0
        for line in lines:
            if '<loc>' in line:
                print('  %s' % line.strip())
                loc_count += 1
                if loc_count >= 10:
                    break
    
    print()
    print('=' * 60)

if __name__ == '__main__':
    main()
