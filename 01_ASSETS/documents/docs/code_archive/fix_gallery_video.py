#!/usr/bin/env python3
"""数字画廊：视频卡片改为占位div，不预加载video元素"""
INDEX = "/www/wwwroot/www.huodouai.com/works-gallery-v2.html"

with open(INDEX, "r", encoding="utf-8") as f:
    content = f.read()

# 替换视频渲染：从<video>改为占位div
old_video_render = '''    if(w.type==="video"){
      media = '<div class="media"><span class="type-badge">▶ 视频</span><span class="model-badge">'+w.model+'</span><div class="play-icon"></div><video preload="none" muted loop playsinline onclick="event.stopPropagation();openLB('+idx+')" onmouseenter="this.preload=\\'auto\\';this.play().catch(()=>{})" onmouseleave="this.pause();this.currentTime=0"><source src="'+w.url+'" type="video/mp4"></video></div>';
    }'''

new_video_render = '''    if(w.type==="video"){
      media = '<div class="media"><span class="type-badge">▶ 视频</span><span class="model-badge">'+w.model+'</span><div class="play-icon"></div><div class="thumb-placeholder"><div class="ph-icon">▶</div><div class="ph-text">'+w.duration+'</div></div></div>';
    }'''

content = content.replace(old_video_render, new_video_render)

with open(INDEX, "w", encoding="utf-8") as f:
    f.write(content)

print("视频卡片已改为占位div")
