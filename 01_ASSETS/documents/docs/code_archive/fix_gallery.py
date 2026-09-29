#!/usr/bin/env python3
"""修复works-gallery-v2.html的URL路径，清理测试视频"""

import os

filepath = "/www/wwwroot/huodouai.com/works-gallery-v2.html"
filepath2 = "/www/wwwroot/www.huodouai.com/works-gallery-v2.html"

# 备份
os.system(f"cp {filepath} {filepath}.bak")
print("  ✅ 已备份原文件")

with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# 修复视频URL
content = content.replace("https://drama.huodouai.com/videos/", "/drama/videos/")
content = content.replace("https://drama.huodouai.com/drama/videos/", "/drama/videos/")

# 修复关键帧URL
content = content.replace("/assets/keyframes/ep01/", "/drama/keyframes/ep01/")
content = content.replace("/assets/keyframes/characters/", "/drama/gallery/keyframes/")
content = content.replace("/assets/keyframes/goddess/", "/drama/gallery/keyframes/")
content = content.replace("/assets/keyframes/", "/drama/keyframes/")

# 移除测试类视频条目
lines = content.split("\n")
new_lines = []
skip_block = False
brace_count = 0

for line in lines:
    stripped = line.strip()
    # 检测测试类视频开始
    if not skip_block and ("测试" in stripped) and ("type:" in stripped or "type :" in stripped):
        skip_block = True
        brace_count = stripped.count("{") - stripped.count("}")
        continue
    if skip_block:
        brace_count += stripped.count("{") - stripped.count("}")
        if brace_count <= 0:
            skip_block = False
        continue
    new_lines.append(line)

content = "\n".join(new_lines)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

# 双root同步
os.system(f"cp {filepath} {filepath2}")

print("  ✅ URL路径已修复")
print("  ✅ 测试类视频已移除")

# 统计
video_count = content.count('type:"video"') + content.count("type:'video'")
image_count = content.count('type:"image"') + content.count("type:'image'")
print(f"  视频作品: {video_count} 个")
print(f"  图片作品: {image_count} 个")
print(f"  总计: {video_count + image_count} 个作品")

# 抽样验证
print("\n【修复后的URL抽样】")
import re
urls = re.findall(r'url:"([^"]*)"', content)
for url in urls[:8]:
    print(f"  {url}")
