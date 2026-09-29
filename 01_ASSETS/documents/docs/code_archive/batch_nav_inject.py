#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import shutil
import time

WEB_ROOT = '/www/wwwroot/huodouai.com'
BACKUP_DIR = '/www/wwwroot/huodouai.com/_backup_nav_inject'

# 不适合添加导航栏的页面（错误页、内部系统页、有独立布局的页面）
SKIP_FILES = {
    '500.html',           # 错误页
    '404.html',           # 错误页（已有导航）
    'demo.html',          # 演示页，独立布局
    'kernel-lock-visual.html',  # 内部可视化窗口
    'kernel-status.html',       # 内部状态面板
    'semantic-dashboard.html',  # 内部仪表盘
    'ops-monitor.html',         # 内部监控
    'server-monitor.html',      # 监控面板，独立布局
    'status-center.html',       # 状态中心
    'search.html',              # 搜索页，可能有独立布局
    'checker.html',             # 工具页，独立布局
    'edu-chat.html',            # 对话页，独立布局
}

# 统一导航栏HTML（精简版，核心链接）
NAV_HTML = '''<nav class="hd-nav">
<div class="hd-nav-inner">
<a href="/" class="hd-nav-logo">火斗云智 AIOS</a>
<div class="hd-nav-links">
<a href="/products.html">产品中心</a>
<a href="/solutions.html">解决方案</a>
<a href="/architecture.html">技术架构</a>
<a href="/whitepaper.html">技术白皮书</a>
<a href="/blog.html">技术博客</a>
<a href="/docs.html">开发者文档</a>
<a href="/pricing.html">定价</a>
<a href="/book-demo.html">预约演示</a>
</div>
</div>
</nav>
'''

# 统一页脚HTML
FOOTER_HTML = '''<footer class="hd-footer">
<div class="hd-footer-inner">
<div class="hd-footer-links">
<a href="/products.html">产品</a>
<a href="/solutions.html">解决方案</a>
<a href="/architecture.html">架构</a>
<a href="/whitepaper.html">白皮书</a>
<a href="/docs.html">文档</a>
<a href="/pricing.html">定价</a>
<a href="/book-demo.html">联系我们</a>
</div>
<div class="hd-footer-copyright">© 2026 火斗云智 AIOS · 元极恒一超认知自治操作系统</div>
</div>
</footer>
'''

# 导航栏和页脚的CSS样式
NAV_CSS = '''
<style>
.hd-nav{position:fixed;top:0;left:0;right:0;z-index:10000;background:rgba(10,10,15,.92);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);border-bottom:1px solid rgba(255,255,255,.08);padding:10px 20px}
.hd-nav-inner{max-width:1200px;margin:0 auto;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px}
.hd-nav-logo{font-size:17px;font-weight:700;background:linear-gradient(90deg,#c9a7e8,#8BC8EA);-webkit-background-clip:text;-webkit-text-fill-color:transparent;text-decoration:none}
.hd-nav-links{display:flex;gap:18px;flex-wrap:wrap;align-items:center}
.hd-nav-links a{color:#9ca3af;text-decoration:none;font-size:13px;transition:color .25s}
.hd-nav-links a:hover{color:#c9a7e8}
.hd-footer{background:#0a0a0f;border-top:1px solid rgba(255,255,255,.06);padding:28px 20px;margin-top:40px}
.hd-footer-inner{max-width:1200px;margin:0 auto;text-align:center}
.hd-footer-links{display:flex;gap:20px;justify-content:center;flex-wrap:wrap;margin-bottom:14px}
.hd-footer-links a{color:#6b7280;text-decoration:none;font-size:13px;transition:color .25s}
.hd-footer-links a:hover{color:#c9a7e8}
.hd-footer-copyright{color:#4b5563;font-size:12px}
body{padding-top:52px}
@media(max-width:768px){.hd-nav-links{gap:12px}.hd-nav-links a{font-size:12px}}
</style>
'''

def has_nav(content):
    return 'class="hd-nav"' in content or 'class="nav"' in content or '<nav' in content

def has_footer(content):
    return 'class="hd-footer"' in content or '<footer' in content

def inject_nav_footer(filepath):
    filename = os.path.basename(filepath)
    
    if filename in SKIP_FILES:
        return False, '跳过（不适合添加导航）'
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return False, '读取失败: %s' % str(e)
    
    need_nav = not has_nav(content)
    need_footer = not has_footer(content)
    
    if not need_nav and not need_footer:
        return False, '已有导航和页脚'
    
    # 备份
    os.makedirs(BACKUP_DIR, exist_ok=True)
    backup_path = os.path.join(BACKUP_DIR, filename + '.bak')
    shutil.copy2(filepath, backup_path)
    
    modified = False
    
    # 注入CSS（在</head>之前）
    if need_nav and '</head>' in content and 'hd-nav' not in content:
        content = content.replace('</head>', NAV_CSS + '</head>', 1)
        modified = True
    
    # 注入导航栏（在<body>之后）
    if need_nav:
        if '<body>' in content:
            content = content.replace('<body>', '<body>' + NAV_HTML, 1)
            modified = True
        elif '<body ' in content:
            # 处理带属性的body标签
            import re
            content = re.sub(r'(<body[^>]*>)', r'\1' + NAV_HTML, content, count=1)
            modified = True
    
    # 注入页脚（在</body>之前）
    if need_footer and '</body>' in content:
        content = content.replace('</body>', FOOTER_HTML + '</body>', 1)
        modified = True
    
    if modified:
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, '成功（导航:%s 页脚:%s）' % ('是' if need_nav else '否', '是' if need_footer else '否')
        except Exception as e:
            return False, '写入失败: %s' % str(e)
    
    return False, '未修改'

def main():
    print('=' * 60)
    print('火斗云智官网统一导航栏和页脚批量注入')
    print('=' * 60)
    print('备份目录: %s' % BACKUP_DIR)
    print()
    
    success = 0
    skipped = 0
    failed = 0
    results = []
    
    for filename in sorted(os.listdir(WEB_ROOT)):
        if not filename.endswith('.html'):
            continue
        filepath = os.path.join(WEB_ROOT, filename)
        if not os.path.isfile(filepath):
            continue
        
        result, msg = inject_nav_footer(filepath)
        if result:
            success += 1
            print('  OK %s - %s' % (filename, msg))
            results.append((filename, msg))
        elif '跳过' in msg or '已有' in msg:
            skipped += 1
        else:
            failed += 1
            print('  FAIL %s - %s' % (filename, msg))
    
    print()
    print('=' * 60)
    print('注入完成: 成功%d, 跳过%d, 失败%d' % (success, skipped, failed))
    print('备份文件保存在: %s' % BACKUP_DIR)
    print('=' * 60)
    
    # 验证
    print()
    print('验证: 检查注入后的导航栏覆盖率')
    total = 0
    with_nav = 0
    with_footer = 0
    for filename in sorted(os.listdir(WEB_ROOT)):
        if not filename.endswith('.html'):
            continue
        filepath = os.path.join(WEB_ROOT, filename)
        if not os.path.isfile(filepath):
            continue
        total += 1
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                c = f.read()
            if has_nav(c):
                with_nav += 1
            if has_footer(c):
                with_footer += 1
        except:
            pass
    print('总页面: %d' % total)
    print('有导航栏: %d (%.0f%%)' % (with_nav, with_nav*100/total))
    print('有页脚: %d (%.0f%%)' % (with_footer, with_footer*100/total))

if __name__ == '__main__':
    main()
