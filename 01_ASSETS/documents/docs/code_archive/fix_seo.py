#!/usr/bin/env python3
"""修复全站SEO缺失项：drama视频preload、gov-ai/performance OG标签、drama description"""

import os

base = "/www/wwwroot/huodouai.com/"
base2 = "/www/wwwroot/www.huodouai.com/"

def fix_file(filepath, fixes):
    """对文件应用修复"""
    if not os.path.exists(filepath):
        return False
    
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    changed = False
    for fix_name, fix_func in fixes:
        new_content = fix_func(content)
        if new_content != content:
            content = new_content
            changed = True
            print(f"    ✅ {fix_name}")
    
    if changed:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
    
    return changed

# 修复1：drama页面video重复preload
def fix_drama_preload(content):
    # 移除preload=none，保留preload="metadata"
    return content.replace('preload=none ', '').replace('preload=none', '')

# 修复2：添加OG标签
def add_og_tags(url, title, desc):
    def fix(content):
        if "og:title" in content:
            return content
        og_meta = f'''
  <!-- Open Graph -->
  <meta property="og:type" content="website">
  <meta property="og:url" content="{url}">
  <meta property="og:title" content="{title}">
  <meta property="og:description" content="{desc}">
  <meta property="og:image" content="https://www.huodouai.com/assets/og-cover.jpg">
  <meta property="og:site_name" content="火斗云智AIOS">
  <meta property="og:locale" content="zh_CN">
'''
        return content.replace("</title>", "</title>" + og_meta, 1)
    return fix

# 修复3：添加meta description
def add_description(desc):
    def fix(content):
        if 'name="description"' in content:
            return content
        desc_meta = f'  <meta name="description" content="{desc}">\n'
        return content.replace('<meta charset="UTF-8">', '<meta charset="UTF-8">\n' + desc_meta, 1)
    return fix

print("【修复drama页面】")
drama_fixes = [
    ("移除重复preload=none", fix_drama_preload),
    ("添加meta description", add_description("昆仑洞天全域资产可视化平台，短剧作品库、关键帧画廊、角色设定、AI生成作品统一展示，6大角色分类，12+视频，46+关键帧")),
]
for b in [base, base2]:
    filepath = b + "drama/index.html"
    if os.path.exists(filepath):
        print(f"  {filepath}")
        fix_file(filepath, drama_fixes)

print("\n【修复gov-ai页面】")
gov_fixes = [
    ("添加OG标签", add_og_tags(
        "https://www.huodouai.com/gov-ai/",
        "政务AI服务平台 - 火斗云智智慧政务解决方案",
        "面向政务场景的AI中台系统，智能审批、舆情监控、决策支持、数据可视化，13个子系统全部健康运行"
    )),
]
for b in [base, base2]:
    filepath = b + "gov-ai/index.html"
    if os.path.exists(filepath):
        print(f"  {filepath}")
        fix_file(filepath, gov_fixes)

print("\n【修复performance页面】")
perf_fixes = [
    ("添加OG标签", add_og_tags(
        "https://www.huodouai.com/performance.html",
        "性能监控面板 - 火斗云智AIOS",
        "火斗云智AIOS全站性能监控面板，实时展示网站加载速度、资源优化、安全状态、SEO指标"
    )),
]
for b in [base, base2]:
    filepath = b + "performance.html"
    if os.path.exists(filepath):
        print(f"  {filepath}")
        fix_file(filepath, perf_fixes)

print("\n【最终验证】")
for page in ["index.html", "kunlun/index.html", "works-gallery-v2.html", "characters.html", "drama/index.html", "gov-ai/index.html", "performance.html"]:
    filepath = base + page
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        has_title = "<title>" in content
        has_desc = 'name="description"' in content
        has_og = "og:title" in content
        print(f"  {page}: title={'✅' if has_title else '❌'}, desc={'✅' if has_desc else '❌'}, og={'✅' if has_og else '❌'}")

print("\n✅ 全部SEO修复完成")
