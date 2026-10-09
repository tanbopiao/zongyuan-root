#!/usr/bin/env python3
"""为所有核心页面添加图片懒加载"""
import re
import os

pages = [
    "/www/wwwroot/huodouai.com/index.html",
    "/www/wwwroot/huodouai.com/kunlun/index.html",
    "/www/wwwroot/huodouai.com/works-gallery-v2.html",
    "/www/wwwroot/huodouai.com/characters.html",
    "/www/wwwroot/huodouai.com/drama/index.html",
    "/www/wwwroot/huodouai.com/education.html",
]

def add_lazy_loading(filepath):
    if not os.path.exists(filepath):
        print(f"  ⚠️  {filepath} 不存在")
        return
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # 统计原始img数量
    original_imgs = len(re.findall(r'<img\s', content))
    
    # 为没有loading属性的img添加loading="lazy"
    # 匹配<img ...>，排除已有loading属性的
    def add_lazy(match):
        tag = match.group(0)
        if 'loading=' in tag:
            return tag
        # 在<img后添加loading="lazy"
        return tag.replace('<img ', '<img loading="lazy" ', 1)
    
    content = re.sub(r'<img\s[^>]*>', add_lazy, content)
    
    # 统计修改后img数量和懒加载数量
    new_imgs = len(re.findall(r'<img\s', content))
    lazy_imgs = len(re.findall(r'<img\s+loading="lazy"', content))
    
    with open(filepath, 'w') as f:
        f.write(content)
    
    print(f"  ✅ {os.path.basename(os.path.dirname(filepath))}/{os.path.basename(filepath)}: {new_imgs}个img, {lazy_imgs}个懒加载")

print("【为核心页面添加图片懒加载】")
for page in pages:
    add_lazy_loading(page)

print("\n完成")
