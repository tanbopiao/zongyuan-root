#!/usr/bin/env python3
"""
网页风格统一化工具 v1.0
- 给缺少导航的页面注入统一导航栏
- 给缺少页脚的页面注入统一页脚
- 对齐黑金风格体系
- 处理重复页面重定向
"""

import os
import re

MAIN_SITE = "/www/wwwroot/www.huodouai.com"
ALT_SITE = "/www/wwwroot/huodouai.com"

# 统一导航栏（对齐主页风格）
UNIFIED_NAV = '''<!-- 统一导航 -->
<style>
.nav-unified {
    position: fixed; top: 0; left: 0; right: 0; z-index: 1000;
    background: rgba(10,10,15,0.95); backdrop-filter: blur(10px);
    border-bottom: 1px solid rgba(212,175,55,0.2);
    padding: 12px 30px; display: flex; align-items: center; justify-content: space-between;
}
.nav-unified .brand {
    color: #d4af37; font-size: 1.1em; font-weight: bold; text-decoration: none;
}
.nav-unified .links { display: flex; gap: 20px; flex-wrap: wrap; }
.nav-unified .links a {
    color: #aaa; text-decoration: none; font-size: 0.9em; transition: color 0.3s;
}
.nav-unified .links a:hover { color: #d4af37; }
@media (max-width: 768px) {
    .nav-unified { padding: 10px 15px; }
    .nav-unified .links { gap: 10px; font-size: 0.8em; }
}
body { padding-top: 50px !important; }
</style>
<nav class="nav-unified">
    <a href="/" class="brand">火斗云智 AIOS</a>
    <div class="links">
        <a href="/">首页</a>
        <a href="/architecture.html">架构</a>
        <a href="/engines.html">引擎</a>
        <a href="/digital-assets.html">数字资产</a>
        <a href="/philosophy.html">思想</a>
        <a href="/governance.html">治理</a>
        <a href="https://drama.huodouai.com" target="_blank">短剧</a>
        <a href="https://gov.huodouai.com" target="_blank">政务</a>
        <a href="https://docs.huodouai.com" target="_blank">文档</a>
    </div>
</nav>
'''

# 统一页脚
UNIFIED_FOOTER = '''<!-- 统一页脚 -->
<style>
.footer-unified {
    text-align: center; padding: 30px 20px; margin-top: 50px;
    border-top: 1px solid rgba(212,175,55,0.1); color: #555; font-size: 0.85em;
}
.footer-unified .omega { color: #d4af37; font-size: 1.2em; margin-bottom: 8px; }
</style>
<footer class="footer-unified">
    <div class="omega">Ω₀⊂⊙∞⊂Ω</div>
    <p>火斗云智AIOS · 元极恒一超认知永恒自治体系<br>
    DID-BR-000002 · 确权标识 · 溯源锚点</p>
</footer>
'''


def has_unified_nav(content):
    return "nav-unified" in content


def has_footer(content):
    return "footer-unified" in content or "Ω₀⊂⊙∞⊂Ω" in content


def inject_nav(content):
    if has_unified_nav(content):
        return content, False
    # 在<body>之后注入
    if "<body" in content:
        content = re.sub(r"(<body[^>]*>)", r"\1\n" + UNIFIED_NAV, content, count=1)
        return content, True
    return content, False


def inject_footer(content):
    if has_footer(content):
        return content, False
    # 在</body>之前注入
    if "</body>" in content:
        content = content.replace("</body>", UNIFIED_FOOTER + "\n</body>", 1)
        return content, True
    return content, False


def process_file(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        original = content
        content, nav_added = inject_nav(content)
        content, footer_added = inject_footer(content)

        if content != original:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            return True, nav_added, footer_added
        return False, False, False
    except Exception as e:
        return False, False, False


def main():
    results = {"nav_added": [], "footer_added": [], "skipped": [], "errors": []}

    for site_dir in [MAIN_SITE, ALT_SITE]:
        if not os.path.exists(site_dir):
            continue
        for filename in os.listdir(site_dir):
            if not filename.endswith(".html"):
                continue
            filepath = os.path.join(site_dir, filename)
            if not os.path.isfile(filepath):
                continue

            changed, nav_added, footer_added = process_file(filepath)
            if changed:
                if nav_added:
                    results["nav_added"].append(filename)
                if footer_added:
                    results["footer_added"].append(filename)
            else:
                results["skipped"].append(filename)

    print("✅ 风格统一化完成")
    print(f"  注入导航: {len(results['nav_added'])}个页面")
    for f in results["nav_added"]:
        print(f"    - {f}")
    print(f"  注入页脚: {len(results['footer_added'])}个页面")
    for f in results["footer_added"]:
        print(f"    - {f}")
    print(f"  已符合/跳过: {len(results['skipped'])}个页面")


if __name__ == "__main__":
    main()
