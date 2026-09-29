#!/usr/bin/env python3
"""
导航清理工具 v1.0
- 移除页面原有导航（class="nav"），只保留统一导航（nav-unified）
- 优化统一导航菜单项，合并重复，全域可达
"""

import os
import re

MAIN_SITE = "/www/wwwroot/www.huodouai.com"
ALT_SITE = "/www/wwwroot/huodouai.com"

# 优化后的统一导航（精简版，8个核心入口，清晰分隔）
OPTIMIZED_NAV = '''<!-- 统一导航 -->
<style>
.nav-unified {
    position: fixed; top: 0; left: 0; right: 0; z-index: 1000;
    background: rgba(10,10,15,0.95); backdrop-filter: blur(10px);
    border-bottom: 1px solid rgba(212,175,55,0.2);
    padding: 0 30px; display: flex; align-items: center; justify-content: space-between;
    height: 52px;
}
.nav-unified .brand {
    color: #d4af37; font-size: 1.05em; font-weight: bold; text-decoration: none;
    letter-spacing: 0.5px;
}
.nav-unified .links { display: flex; align-items: center; gap: 0; }
.nav-unified .links a {
    color: #aaa; text-decoration: none; font-size: 0.88em;
    padding: 0 14px; height: 52px; display: flex; align-items: center;
    transition: color 0.3s, background 0.3s;
    border-left: 1px solid rgba(255,255,255,0.05);
}
.nav-unified .links a:first-child { border-left: none; }
.nav-unified .links a:hover { color: #d4af37; background: rgba(212,175,55,0.08); }
.nav-unified .links a.external { color: #8BC8EA; }
.nav-unified .links a.external:hover { color: #d4af37; }
@media (max-width: 768px) {
    .nav-unified { padding: 0 12px; height: 44px; }
    .nav-unified .brand { font-size: 0.9em; }
    .nav-unified .links a { padding: 0 8px; font-size: 0.75em; height: 44px; }
    body { padding-top: 44px !important; }
}
body { padding-top: 52px !important; }
</style>
<nav class="nav-unified">
    <a href="/" class="brand">火斗云智 AIOS</a>
    <div class="links">
        <a href="/architecture.html">架构</a>
        <a href="/engines.html">引擎</a>
        <a href="/digital-assets.html">数字资产</a>
        <a href="/philosophy.html">思想</a>
        <a href="/governance.html">治理</a>
        <a href="https://drama.huodouai.com" target="_blank" class="external">短剧 ↗</a>
        <a href="https://gov.huodouai.com" target="_blank" class="external">政务 ↗</a>
        <a href="https://docs.huodouai.com" target="_blank" class="external">文档 ↗</a>
    </div>
</nav>
'''


def remove_old_nav(content):
    """移除旧导航 <nav class="nav">...</nav>"""
    # 匹配 <nav class="nav"> 到 </nav>
    pattern = r'<nav class="nav">.*?</nav>'
    new_content, count = re.subn(pattern, '', content, flags=re.DOTALL)
    return new_content, count


def replace_unified_nav(content):
    """替换旧的统一导航为优化版"""
    # 移除旧的统一导航（从 <!-- 统一导航 --> 到 </nav>）
    pattern = r'<!-- 统一导航 -->.*?</nav>\s*'
    new_content = re.sub(pattern, OPTIMIZED_NAV, content, flags=re.DOTALL)
    return new_content


def process_file(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        original = content

        # 移除旧导航
        content, old_removed = remove_old_nav(content)

        # 替换统一导航为优化版
        if "nav-unified" in content:
            content = replace_unified_nav(content)

        if content != original:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            return True, old_removed
        return False, 0
    except Exception as e:
        print(f"  错误 {filepath}: {e}")
        return False, 0


def main():
    total_processed = 0
    total_old_removed = 0

    for site_dir in [MAIN_SITE, ALT_SITE]:
        if not os.path.exists(site_dir):
            continue
        for filename in os.listdir(site_dir):
            if not filename.endswith(".html"):
                continue
            filepath = os.path.join(site_dir, filename)
            if not os.path.isfile(filepath):
                continue

            changed, old_removed = process_file(filepath)
            if changed:
                total_processed += 1
                total_old_removed += old_removed

    print("✅ 导航清理完成")
    print(f"  处理页面: {total_processed}个")
    print(f"  移除旧导航: {total_old_removed}处")
    print(f"  统一导航已优化为8个核心入口")
    print("")
    print("  导航结构:")
    print("    [品牌] 架构 | 引擎 | 数字资产 | 思想 | 治理 | 短剧↗ | 政务↗ | 文档↗")


if __name__ == "__main__":
    main()
