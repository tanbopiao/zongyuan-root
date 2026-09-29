#!/usr/bin/env python3
"""修复HTML中的.png图片URL为.webp"""

import re
import os
import glob

# 要修复的HTML文件
html_files = [
    "/www/wwwroot/huodouai.com/works-gallery-v2.html",
]

# 也扫描其他HTML文件
for f in glob.glob("/www/wwwroot/huodouai.com/*.html"):
    if f not in html_files:
        html_files.append(f)

for filepath in html_files:
    if not os.path.exists(filepath):
        continue
    
    # 检查是否有.png引用
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    
    if ".png" not in content:
        continue
    
    # 统计替换前的.png数量
    png_count_before = content.count(".png")
    
    # 替换图片URL中的.png为.webp（在引号内或括号内）
    # 匹配 .png" 或 .png' 或 .png) 
    content = re.sub(r'\.png(["\')])', r'.webp\1', content)
    
    # 统计替换后的.png数量
    png_count_after = content.count(".png")
    
    if png_count_before != png_count_after:
        # 写入文件
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"✅ {os.path.basename(filepath)}: 替换 {png_count_before - png_count_after} 个 .png -> .webp")
    else:
        print(f"ℹ️  {os.path.basename(filepath)}: 无需要替换的图片URL")

print("\n🎉 修复完成！")
