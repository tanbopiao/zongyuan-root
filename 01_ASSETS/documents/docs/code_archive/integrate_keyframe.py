#!/usr/bin/env python3
"""部署关键帧资产库后的集成操作"""
import os

# 1. 加入官网导航
with open("/www/wwwroot/www.huodouai.com/index.html") as f:
    content = f.read()
if "/keyframe-gallery.html" not in content:
    old = '<a href="/search.html">全站搜索</a>'
    new = '<a href="/keyframe-gallery.html">关键帧资产库</a>\n          <a href="/search.html">全站搜索</a>'
    content = content.replace(old, new)
    with open("/www/wwwroot/www.huodouai.com/index.html", "w") as f:
        f.write(content)
    print("✅ 已加入官网导航")
else:
    print("⚠️ 导航已存在")

# 2. 在昆仑作品库添加入口
with open("/www/wwwroot/www.huodouai.com/kunlun/gallery.html") as f:
    content = f.read()
if "keyframe-gallery" not in content:
    old = '<div class="video-grid" id="videoGrid">'
    new = '<div style="text-align:center;margin:20px 0"><a href="/keyframe-gallery.html" style="display:inline-block;padding:10px 24px;background:rgba(212,175,55,0.15);color:#d4af37;text-decoration:none;border-radius:8px;border:1px solid rgba(212,175,55,0.3);font-size:0.9em">浏览关键帧资产库（25张高质量） →</a></div>\n    <div class="video-grid" id="videoGrid">'
    content = content.replace(old, new)
    with open("/www/wwwroot/www.huodouai.com/kunlun/gallery.html", "w") as f:
        f.write(content)
    print("✅ 已在昆仑作品库添加入口")

# 3. 双root同步
os.system("cp /www/wwwroot/www.huodouai.com/index.html /www/wwwroot/huodouai.com/index.html")
os.system("cp /www/wwwroot/www.huodouai.com/kunlun/gallery.html /www/wwwroot/huodouai.com/kunlun/gallery.html")
print("✅ 双root同步完成")
