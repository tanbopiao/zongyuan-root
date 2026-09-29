#!/usr/bin/env python3
"""修复drama和gov-ai的meta description"""

import os

files = [
    ("/www/wwwroot/huodouai.com/drama/index.html", "昆仑洞天全域资产可视化平台，短剧作品库、关键帧画廊、角色设定、AI生成作品统一展示，6大角色分类，12+视频，46+关键帧"),
    ("/www/wwwroot/www.huodouai.com/drama/index.html", "昆仑洞天全域资产可视化平台，短剧作品库、关键帧画廊、角色设定、AI生成作品统一展示，6大角色分类，12+视频，46+关键帧"),
    ("/www/wwwroot/huodouai.com/gov-ai/index.html", "面向政务场景的AI中台系统，智能审批、舆情监控、决策支持、数据可视化，13个子系统全部健康运行"),
    ("/www/wwwroot/www.huodouai.com/gov-ai/index.html", "面向政务场景的AI中台系统，智能审批、舆情监控、决策支持、数据可视化，13个子系统全部健康运行"),
]

for filepath, desc in files:
    if not os.path.exists(filepath):
        print(f"  ⚠️  {filepath} 不存在")
        continue
    
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    if 'name="description"' in content:
        print(f"  ⏭️  {filepath} 已有description")
        continue
    
    desc_meta = '  <meta name="description" content="' + desc + '">\n'
    
    # 尝试多种方式添加
    if '<meta charset="UTF-8">' in content:
        content = content.replace('<meta charset="UTF-8">', '<meta charset="UTF-8">\n' + desc_meta, 1)
    elif "<meta charset='UTF-8'>" in content:
        content = content.replace("<meta charset='UTF-8'>", "<meta charset='UTF-8'>\n" + desc_meta, 1)
    elif "<head>" in content:
        content = content.replace("<head>", "<head>\n" + desc_meta, 1)
    else:
        content = content.replace("<title>", desc_meta + "<title>", 1)
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  ✅ {filepath} 已添加description")

print("\n【最终验证】")
for page in ["index.html", "kunlun/index.html", "works-gallery-v2.html", "characters.html", "drama/index.html", "gov-ai/index.html", "performance.html"]:
    filepath = "/www/wwwroot/huodouai.com/" + page
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        has_title = "<title>" in content
        has_desc = 'name="description"' in content
        has_og = "og:title" in content
        has_twitter = "twitter:card" in content
        status = "✅" if (has_title and has_desc and has_og) else "⚠️"
        print(f"  {status} {page}: title={has_title}, desc={has_desc}, og={has_og}, twitter={has_twitter}")

print("\n✅ 全部修复完成")
