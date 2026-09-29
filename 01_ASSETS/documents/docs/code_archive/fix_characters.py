#!/usr/bin/env python3
"""角色宇宙页面：替换女娲和真武大帝的emoji占位为真实图片"""
INDEX = "/www/wwwroot/www.huodouai.com/characters.html"

with open(INDEX, "r", encoding="utf-8") as f:
    content = f.read()

# 替换女娲emoji占位
old_nvwa = '''<div class="character-card-image" style="background: linear-gradient(135deg,#2E1A1A,#4E2D2D); display:flex; align-items:center; justify-content:center;">
            <span style="font-size:4rem; opacity:0.4;">🌸</span>
          </div>'''
new_nvwa = '''<div class="character-card-image">
            <img src="/assets/keyframes/ep01/S01-011_女娲天际剪影.jpg" alt="女娲" style="width:100%;height:100%;object-fit:cover">
          </div>'''
content = content.replace(old_nvwa, new_nvwa)

# 替换真武大帝emoji占位
old_zhenwu = '''<div class="character-card-image" style="background: linear-gradient(135deg,#1A2E1A,#2D4E2D); display:flex; align-items:center; justify-content:center;">
            <span style="font-size:4rem; opacity:0.4;">⚔️</span>
          </div>'''
new_zhenwu = '''<div class="character-card-image">
            <img src="/assets/keyframes/ep01/S01-010_真武大帝结阵.jpg" alt="真武大帝" style="width:100%;height:100%;object-fit:cover">
          </div>'''
content = content.replace(old_zhenwu, new_zhenwu)

with open(INDEX, "w", encoding="utf-8") as f:
    f.write(content)

print("女娲和真武大帝图片替换完成")
