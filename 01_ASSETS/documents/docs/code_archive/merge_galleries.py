#!/usr/bin/env python3
"""整合所有作品库到works-gallery-v2.html"""
import re

INDEX = "/www/wwwroot/www.huodouai.com/works-gallery-v2.html"

with open(INDEX, "r", encoding="utf-8") as f:
    content = f.read()

# 要追加的关键帧数据（从keyframe-gallery提取）
keyframes = '''
  // === 关键帧资产（从keyframe-gallery整合） ===
  {type:"image",title:"墟境封印破裂",url:"/assets/keyframes/ep01/S01-001_墟境封印破裂.jpg",model:"Seedance",size:"关键帧",duration:"EP01",category:"关键帧"},
  {type:"image",title:"万妖之眼",url:"/assets/keyframes/ep01/S01-002_万妖之眼.jpg",model:"Seedance",size:"关键帧",duration:"EP01",category:"关键帧"},
  {type:"image",title:"玄汐山门警报",url:"/assets/keyframes/ep01/S01-003_玄汐山门警报.jpg",model:"Seedance",size:"关键帧",duration:"EP01",category:"关键帧"},
  {type:"image",title:"妖云压境",url:"/assets/keyframes/ep01/S01-004_妖云压境.jpg",model:"Seedance",size:"关键帧",duration:"EP01",category:"关键帧"},
  {type:"image",title:"玄女战争形态降临",url:"/assets/keyframes/ep01/S01-005_玄女战争形态降临.jpg",model:"Seedance",size:"关键帧",duration:"EP01",category:"关键帧"},
  {type:"image",title:"玄女俯瞰山门",url:"/assets/keyframes/ep01/S01-006_玄女俯瞰山门.jpg",model:"Seedance",size:"关键帧",duration:"EP01",category:"关键帧"},
  {type:"image",title:"万妖潮冲锋",url:"/assets/keyframes/ep01/S01-007_万妖潮冲锋.jpg",model:"Seedance",size:"关键帧",duration:"EP01",category:"关键帧"},
  {type:"image",title:"玄女神兵斩妖",url:"/assets/keyframes/ep01/S01-008_玄女神兵斩妖.jpg",model:"Seedance",size:"关键帧",duration:"EP01",category:"关键帧"},
  {type:"image",title:"妖兽被击碎",url:"/assets/keyframes/ep01/S01-009_妖兽被击碎.jpg",model:"Seedance",size:"关键帧",duration:"EP01",category:"关键帧"},
  {type:"image",title:"真武大帝结阵",url:"/assets/keyframes/ep01/S01-010_真武大帝结阵.jpg",model:"Seedance",size:"关键帧",duration:"EP01",category:"关键帧"},
  {type:"image",title:"女娲天际剪影",url:"/assets/keyframes/ep01/S01-011_女娲天际剪影.jpg",model:"Seedance",size:"关键帧",duration:"EP01",category:"关键帧"},
  {type:"image",title:"未知巨兽浮现",url:"/assets/keyframes/ep01/S01-012_未知巨兽浮现结尾.jpg",model:"Seedance",size:"关键帧",duration:"EP01",category:"关键帧"},
  {type:"image",title:"红裙九尾狐 全身设定",url:"/assets/keyframes/characters/hongqun_jiuweihu_keyframe_01_fullbody.png",model:"Seedance",size:"角色设定",duration:"角色",category:"角色设定"},
  {type:"image",title:"红裙九尾狐 场景",url:"/assets/keyframes/characters/hongqun_jiuweihu_keyframe_02_scene.png",model:"Seedance",size:"角色设定",duration:"角色",category:"角色设定"},
  {type:"image",title:"九天玄女 全身设定",url:"/assets/keyframes/characters/jiutian_xuannv_keyframe_01_fullbody.png",model:"Seedance",size:"角色设定",duration:"角色",category:"角色设定"},
  {type:"image",title:"九天玄女 场景",url:"/assets/keyframes/characters/jiutian_xuannv_keyframe_02_scene.png",model:"Seedance",size:"角色设定",duration:"角色",category:"角色设定"},
  {type:"image",title:"太阴月神 全身设定",url:"/assets/keyframes/characters/taiyin_moon_god_keyframe_01_fullbody.png",model:"Seedance",size:"角色设定",duration:"角色",category:"角色设定"},
  {type:"image",title:"太阴月神 场景",url:"/assets/keyframes/characters/taiyin_moon_god_keyframe_02_scene.png",model:"Seedance",size:"角色设定",duration:"角色",category:"角色设定"},
  {type:"image",title:"西王母 全身设定",url:"/assets/keyframes/characters/xiwangmu_keyframe_01_fullbody.png",model:"Seedance",size:"角色设定",duration:"角色",category:"角色设定"},
  {type:"image",title:"西王母 场景",url:"/assets/keyframes/characters/xiwangmu_keyframe_02_scene.png",model:"Seedance",size:"角色设定",duration:"角色",category:"角色设定"},
  {type:"image",title:"金色符文星尘",url:"/assets/keyframes/goddess/01_金色符文星尘_竖屏.png",model:"Seedance",size:"竖屏",duration:"神女觉醒",category:"神女觉醒"},
  {type:"image",title:"黑色裂隙",url:"/assets/keyframes/goddess/02_黑色裂隙_竖屏.png",model:"Seedance",size:"竖屏",duration:"神女觉醒",category:"神女觉醒"},
  {type:"image",title:"神女觉醒",url:"/assets/keyframes/goddess/03_神女觉醒_竖屏.png",model:"Seedance",size:"竖屏",duration:"神女觉醒",category:"神女觉醒"},
  {type:"image",title:"九尾现身",url:"/assets/keyframes/goddess/04_九尾现身_竖屏.png",model:"Seedance",size:"竖屏",duration:"神女觉醒",category:"神女觉醒"},
  {type:"image",title:"苍玄降临",url:"/assets/keyframes/goddess/05_苍玄降临_竖屏.png",model:"Seedance",size:"竖屏",duration:"神女觉醒",category:"神女觉醒"},
  // === 昆仑演示视频（从kunlun/gallery整合） ===
  {type:"video",title:"昆仑万象演示",url:"/kunlun/videos/kunlun_wanxiang_demo.mp4",model:"通义万相",size:"5MB",duration:"16秒",category:"演示"},
  {type:"video",title:"昆仑真实AI演示",url:"/kunlun/videos/kunlun_real_ai_demo.mp4",model:"Agnes",size:"5MB",duration:"20秒",category:"演示"},
  {type:"video",title:"昆仑关键帧动效",url:"/kunlun/videos/kunlun_demo_5s.mp4",model:"ffmpeg",size:"2MB",duration:"14秒",category:"演示"},
'''

# 在WORKS数组的];前插入（找到最后一个条目后的];）
# 先找到"演示"类别的最后一个条目，然后在];前插入
# 简单方式：找到"// === 图片作品 ==="或最后一个];前
# 找到WORKS数组的结束位置
works_end = content.find("];", content.find("const WORKS"))
if works_end > 0:
    content = content[:works_end] + keyframes + content[works_end:]
    print("关键帧数据已合并")
else:
    print("未找到WORKS数组结束位置")

# 更新标题
content = content.replace("<title>作品库2.0 · 火斗云智AIOS</title>", 
    "<title>昆仑洞天 · 全域作品库 · 火斗云智AIOS</title>")

# 更新页脚
content = content.replace("作品库2.0", "昆仑洞天 · 全域作品库")

with open(INDEX, "w", encoding="utf-8") as f:
    f.write(content)

print("作品库整合完成")
