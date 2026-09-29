#!/usr/bin/env python3
"""昆仑主页：emoji占位替换为真实关键帧"""
INDEX = "/www/wwwroot/www.huodouai.com/kunlun/index.html"

with open(INDEX, "r", encoding="utf-8") as f:
    content = f.read()

# 1. 精选作品大图1：九天玄女·战争形态 → 玄女战争形态关键帧
old1 = '''<div class="gallery-item-image" style="background: linear-gradient(135deg, #1A1A2E 0%, #2D1B4E 50%, #1A1A2E 100%); display: flex; align-items: center; justify-content: center;">
            <span style="font-size: 80px; opacity: 0.4;">⚔️</span>
          </div>'''
new1 = '''<div class="gallery-item-image" style="background: linear-gradient(135deg, #1A1A2E 0%, #2D1B4E 50%, #1A1A2E 100%);">
            <img src="/assets/keyframes/ep01/S01-005_玄女战争形态降临.jpg" alt="九天玄女·战争形态" style="width:100%;height:100%;object-fit:cover">
          </div>'''
content = content.replace(old1, new1)

# 2. 精选作品大图2：太阴月神·星夜形态 → 太阴月神场景
old2 = '''<div class="gallery-item-image" style="background: linear-gradient(135deg, #0F1A2E 0%, #1E3A5F 50%, #0F1A2E 100%); display: flex; align-items: center; justify-content: center;">
            <span style="font-size: 80px; opacity: 0.4;">🌙</span>
          </div>'''
new2 = '''<div class="gallery-item-image" style="background: linear-gradient(135deg, #0F1A2E 0%, #1E3A5F 50%, #0F1A2E 100%);">
            <img src="/assets/keyframes/characters/taiyin_moon_god_keyframe_02_scene.png" alt="太阴月神·星夜形态" style="width:100%;height:100%;object-fit:cover">
          </div>'''
content = content.replace(old2, new2)

# 3. 小图1：女娲补天 → 神女觉醒
old3 = '''<div class="gallery-item-image" style="background: linear-gradient(135deg, #2E1A1A 0%, #4E2D2D 50%, #2E1A1A 100%); display: flex; align-items: center; justify-content: center;">
            <span style="font-size: 48px; opacity: 0.4;">🔥</span>
          </div>'''
new3 = '''<div class="gallery-item-image" style="background: linear-gradient(135deg, #2E1A1A 0%, #4E2D2D 50%, #2E1A1A 100%);">
            <img src="/assets/keyframes/goddess/03_神女觉醒_竖屏.png" alt="神女觉醒" style="width:100%;height:100%;object-fit:cover">
          </div>'''
content = content.replace(old3, new3)

# 4. 小图2：昆仑仙境 → 玄汐山门警报
old4 = '''<div class="gallery-item-image" style="background: linear-gradient(135deg, #1A2E1A 0%, #2D4E2D 50%, #1A2E1A 100%); display: flex; align-items: center; justify-content: center;">
            <span style="font-size: 48px; opacity: 0.4;">⛰️</span>
          </div>'''
new4 = '''<div class="gallery-item-image" style="background: linear-gradient(135deg, #1A2E1A 0%, #2D4E2D 50%, #1A2E1A 100%);">
            <img src="/assets/keyframes/ep01/S01-003_玄汐山门警报.jpg" alt="昆仑仙境" style="width:100%;height:100%;object-fit:cover">
          </div>'''
content = content.replace(old4, new4)

# 5. 小图3：上古符文 → 金色符文星尘
old5 = '''<div class="gallery-item-image" style="background: linear-gradient(135deg, #2E2D1A 0%, #4E4A2D 50%, #2E2D1A 100%); display: flex; align-items: center; justify-content: center;">
            <span style="font-size: 48px; opacity: 0.4;">📜</span>
          </div>'''
new5 = '''<div class="gallery-item-image" style="background: linear-gradient(135deg, #2E2D1A 0%, #4E4A2D 50%, #2E2D1A 100%);">
            <img src="/assets/keyframes/goddess/01_金色符文星尘_竖屏.png" alt="上古符文" style="width:100%;height:100%;object-fit:cover">
          </div>'''
content = content.replace(old5, new5)

# 6. 小图4：创世之光 → 九尾现身
old6 = '''<div class="gallery-item-image" style="background: linear-gradient(135deg, #1A1A2E 0%, #3D2D5F 50%, #1A1A2E 100%); display: flex; align-items: center; justify-content: center;">
            <span style="font-size: 48px; opacity: 0.4;">✨</span>
          </div>'''
new6 = '''<div class="gallery-item-image" style="background: linear-gradient(135deg, #1A1A2E 0%, #3D2D5F 50%, #1A1A2E 100%);">
            <img src="/assets/keyframes/goddess/04_九尾现身_竖屏.png" alt="创世之光" style="width:100%;height:100%;object-fit:cover">
          </div>'''
content = content.replace(old6, new6)

# 7. 角色主展示：玄女文字 → 九天玄女全身关键帧
old_char = '''<div class="character-image">
          <div class="character-image-inner">玄女</div>
        </div>'''
new_char = '''<div class="character-image">
          <img src="/assets/keyframes/characters/jiutian_xuannv_keyframe_01_fullbody.png" alt="九天玄女" style="width:100%;height:100%;object-fit:cover">
        </div>'''
content = content.replace(old_char, new_char)

with open(INDEX, "w", encoding="utf-8") as f:
    f.write(content)

print("昆仑主页真实作品替换完成")
