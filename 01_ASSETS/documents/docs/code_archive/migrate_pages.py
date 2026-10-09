#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import shutil
import re

WEB_ROOT = '/www/wwwroot/huodouai.com'
BASE_URL = 'https://huodouai.com'

# 迁移映射表：旧路径(相对根目录) -> 新路径(相对根目录)
# 采用复制策略，不删除原文件
MIGRATION_MAP = {
    # === 产品中心 /products/ ===
    'products.html': 'products/index.html',
    'vector.html': 'products/vector-kb.html',
    'kb-saas.html': 'products/vector-kb-saas.html',
    'gov-line.html': 'products/gov-ai.html',
    'workbench.html': 'products/workbench.html',
    'kunlun-drama.html': 'products/kunlun-drama.html',
    'drama-factory.html': 'products/drama-factory.html',
    'ai-gateway.html': 'products/ai-gateway.html',
    'token-gateway.html': 'products/token-gateway.html',
    'dlp-gateway.html': 'products/dlp-gateway.html',
    'notary-api.html': 'products/notary-api.html',
    'ai-asset-lock.html': 'products/ai-asset-lock.html',
    'character-ai.html': 'products/character-ai.html',
    'agent-network.html': 'products/agent-network.html',
    'agent-studio.html': 'products/agent-studio.html',
    'aios-image.html': 'products/aios-image.html',
    'engines.html': 'products/engines.html',
    'product-map.html': 'products/product-map.html',
    'product-matrix.html': 'products/product-matrix.html',
    
    # === 解决方案 /solutions/ ===
    'solutions.html': 'solutions/index.html',
    'cases.html': 'solutions/cases.html',
    'compare.html': 'solutions/compare.html',
    'roi-calculator.html': 'solutions/roi-calculator.html',
    'ecosystem-line.html': 'solutions/ecosystem.html',
    'content-line.html': 'solutions/content-production.html',
    'education-line.html': 'solutions/education.html',
    
    # === 技术架构 /architecture/ ===
    'architecture.html': 'architecture/index.html',
    'architecture-deep.html': 'architecture/deep-dive.html',
    'microkernel-architecture.html': 'architecture/microkernel.html',
    'decision-intelligence.html': 'architecture/decision-intelligence.html',
    'commercial.html': 'architecture/commercial.html',
    'diff.html': 'architecture/diff.html',
    'safe-evolution.html': 'architecture/safe-evolution.html',
    'governance.html': 'architecture/governance.html',
    
    # === 白皮书 /whitepapers/ ===
    'whitepaper.html': 'whitepapers/aios-v1.html',
    'high-order-state.html': 'whitepapers/high-order-state.html',
    'startup-loop-defense-whitepaper.html': 'whitepapers/startup-loop-defense.html',
    
    # === 开发者 /docs/ ===
    'docs.html': 'docs/index.html',
    'developers.html': 'docs/developers.html',
    'developer-center.html': 'docs/developer-center.html',
    'prometheus-api-docs.html': 'docs/prometheus-api.html',
    'opensource.html': 'docs/opensource.html',
    'changelog.html': 'docs/changelog.html',
    
    # === 博客 /blog/ ===
    'blog.html': 'blog/index.html',
    
    # === 关于我们 /about/ ===
    'about-line.html': 'about/index.html',
    'philosophy.html': 'about/philosophy.html',
    'research.html': 'about/research.html',
    'education.html': 'about/education.html',
    'knowledge.html': 'about/knowledge.html',
    'book-demo.html': 'about/book-demo.html',
    'logo-design.html': 'about/logo-design.html',
    'partners.html': 'about/partners.html',
    
    # === 定价 /pricing/ (已存在目录，复制index) ===
    'pricing.html': 'pricing/index.html',
    
    # === 内部系统 /internal/ ===
    'monitor.html': 'internal/monitor.html',
    'ops-monitor.html': 'internal/ops-monitor.html',
    'server-monitor.html': 'internal/server-monitor.html',
    'status.html': 'internal/status.html',
    'status-center.html': 'internal/status-center.html',
    'kernel-status.html': 'internal/kernel-status.html',
    'kernel-lock-visual.html': 'internal/kernel-lock-visual.html',
    'semantic-dashboard.html': 'internal/semantic-dashboard.html',
    'ops-center.html': 'internal/ops-center.html',
    'checker.html': 'internal/checker.html',
    'drift.html': 'internal/drift.html',
    'search.html': 'internal/search.html',
    'demo.html': 'internal/demo.html',
    'portal.html': 'internal/portal.html',
}

# 构建链接替换映射（用于更新页面内的href）
LINK_REPLACEMENTS = {}
for old, new in MIGRATION_MAP.items():
    # 旧链接格式：/old.html 或 old.html
    LINK_REPLACEMENTS['/' + old] = '/' + new
    LINK_REPLACEMENTS[old] = new
    # index.html的特殊处理
    if new.endswith('index.html'):
        dir_path = '/' + os.path.dirname(new) + '/'
        LINK_REPLACEMENTS['/' + old] = dir_path

def update_internal_links(content, file_rel_path):
    """更新页面内的内部链接"""
    for old_link, new_link in LINK_REPLACEMENTS.items():
        # 替换 href="/old.html" 格式
        content = content.replace('href="%s"' % old_link, 'href="%s"' % new_link)
        # 替换 href='old.html' 格式
        content = content.replace("href='%s'" % old_link, "href='%s'" % new_link)
    return content

def update_canonical(content, new_rel_path):
    """更新canonical标签"""
    if new_rel_path.endswith('index.html'):
        canonical_url = BASE_URL + '/' + os.path.dirname(new_rel_path) + '/'
    else:
        canonical_url = BASE_URL + '/' + new_rel_path
    
    # 替换现有的canonical
    content = re.sub(
        r'<link rel="canonical" href="[^"]*">',
        '<link rel="canonical" href="%s">' % canonical_url,
        content
    )
    return content

def add_noindex(content):
    """为内部页面添加noindex标签"""
    noindex_tag = '<meta name="robots" content="noindex, nofollow">'
    if 'name="robots"' not in content:
        content = content.replace('</head>', '    ' + noindex_tag + '\n</head>', 1)
    return content

def migrate_page(old_rel, new_rel):
    """迁移单个页面"""
    old_path = os.path.join(WEB_ROOT, old_rel)
    new_path = os.path.join(WEB_ROOT, new_rel)
    
    if not os.path.exists(old_path):
        return False, '源文件不存在'
    
    # 创建目标目录
    os.makedirs(os.path.dirname(new_path), exist_ok=True)
    
    # 读取源文件
    with open(old_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 更新内部链接
    content = update_internal_links(content, new_rel)
    
    # 更新canonical
    content = update_canonical(content, new_rel)
    
    # 内部页面添加noindex
    if new_rel.startswith('internal/'):
        content = add_noindex(content)
    
    # 写入新文件
    with open(new_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return True, '已迁移到 %s' % new_rel

def main():
    print('=' * 60)
    print('架构重构阶段二：页面批量迁移')
    print('=' * 60)
    print('策略：复制到新位置，旧文件保留（配合301重定向）')
    print()
    
    success = 0
    failed = 0
    failed_list = []
    
    for old_rel, new_rel in sorted(MIGRATION_MAP.items()):
        result, msg = migrate_page(old_rel, new_rel)
        if result:
            success += 1
            print('  OK %s -> %s' % (old_rel, new_rel))
        else:
            failed += 1
            failed_list.append('%s: %s' % (old_rel, msg))
            print('  FAIL %s - %s' % (old_rel, msg))
    
    print()
    print('=' * 60)
    print('迁移完成: 成功%d, 失败%d' % (success, failed))
    if failed_list:
        print('失败列表:')
        for f in failed_list:
            print('  - %s' % f)
    print('=' * 60)
    print()
    
    # 验证新文件
    print('验证：新目录文件统计')
    for d in ['products', 'solutions', 'architecture', 'whitepapers', 'docs', 'about', 'internal', 'blog']:
        dpath = os.path.join(WEB_ROOT, d)
        if os.path.exists(dpath):
            count = len([f for f in os.listdir(dpath) if f.endswith('.html')])
            print('  /%s/: %d 个页面' % (d, count))

if __name__ == '__main__':
    main()
