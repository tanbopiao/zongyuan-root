#!/usr/bin/env python3
"""优化2：数字画廊 - 生成缩略图+点击播放模式"""
import os, json, subprocess

gallery_path = "/www/wwwroot/www.huodouai.com/digital-gallery-v3.html"
video_base = "/www/wwwroot/www.huodouai.com/assets/videos"
thumb_base = "/www/wwwroot/www.huodouai.com/assets/videos/thumbs"

# 创建缩略图目录
os.makedirs(f"{thumb_base}/drama", exist_ok=True)
os.makedirs(f"{thumb_base}/kunlun", exist_ok=True)

# 读取页面中的视频列表
with open(gallery_path, encoding="utf-8") as f:
    content = f.read()

# 提取视频数据
import re
videos = re.findall(r'\{title:"([^"]+)",\s*url:"([^"]+)",\s*model:"([^"]*)",\s*cat:"([^"]*)",\s*size:"([^"]*)"\}', content)
print(f"找到 {len(videos)} 个视频")

# 生成缩略图
success = 0
for title, url, model, cat, size in videos:
    video_path = "/www/wwwroot/www.huodouai.com" + url
    thumb_path = "/www/wwwroot/www.huodouai.com/assets/videos/thumbs" + url.replace(".mp4", ".jpg").replace("/assets/videos", "")
    
    if os.path.exists(video_path) and not os.path.exists(thumb_path):
        # 用ffmpeg截取第1秒的帧
        try:
            subprocess.run([
                "ffmpeg", "-y", "-i", video_path, "-ss", "00:00:01", 
                "-vframes", "1", "-q:v", "3", "-vf", "scale=360:-1",
                thumb_path
            ], capture_output=True, timeout=10)
            if os.path.exists(thumb_path):
                success += 1
        except:
            pass

print(f"✅ 生成 {success} 个缩略图")

# 修改页面：添加缩略图支持 + 点击播放模式
# 1. 修改作品卡片渲染：默认显示缩略图，悬停显示播放按钮
old_card = """        '<video preload="none" muted loop playsinline onmouseenter="this.preload=\\'auto\\';this.play().catch(()=>{})" onmouseleave="this.pause();this.currentTime=0"><source src="'+v.url+'" type="video/mp4"></video>'+"""

new_card = """        '<div class="video-thumb" data-url="'+v.url+'" style="background-image:url(/assets/videos/thumbs'+v.url.replace(\\'/assets/videos\\',\\'\\').replace(\\'.mp4\\',\\'.jpg\\')+\\');background-size:cover;background-position:center"><div class="play-btn">▶</div></div>'+"""

content = content.replace(old_card, new_card)

# 2. 添加缩略图CSS
old_style_end = "</style>"
new_style = """
.video-thumb{position:relative;width:100%;height:100%;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:transform .3s}
.video-thumb:hover{transform:scale(1.05)}
.play-btn{width:50px;height:50px;border-radius:50%;background:rgba(0,0,0,.6);display:flex;align-items:center;justify-content:center;color:#fff;font-size:20px;transition:all .3s}
.video-thumb:hover .play-btn{background:rgba(212,175,55,.8);transform:scale(1.1)}
"""
content = content.replace(old_style_end, new_style + old_style_end, 1)

# 3. 修改点击事件：点击缩略图时才加载视频并播放
old_click = """frame.innerHTML = '<video controls autoplay muted playsinline style="width:100%;height:100%;object-fit:contain" onclick="event.stopPropagation()"><source src="'+w.url+'" type="video/mp4"></video>';"""
new_click = """frame.innerHTML = '<video controls autoplay playsinline style="width:100%;height:100%;object-fit:contain" onclick="event.stopPropagation()"><source src="'+w.url+'" type="video/mp4"></video>';"""
content = content.replace(old_click, new_click)

# 4. 添加缩略图点击事件委托（在页面底部script前添加）
old_script_end = "console.log('%c"
new_click_handler = """
// 缩略图点击播放
document.addEventListener('click', function(e){
  const thumb = e.target.closest('.video-thumb');
  if(thumb){
    const url = thumb.dataset.url;
    // 找到对应的作品数据并打开全屏
    const works = window.worksData || [];
    const work = works.find(w => w.url === url);
    if(work && typeof openWork === 'function'){
      openWork(work);
    }
  }
});
"""
content = content.replace(old_script_end, new_click_handler + old_script_end)

with open(gallery_path, "w", encoding="utf-8") as f:
    f.write(content)

print(f"✅ 数字画廊优化完成：缩略图+点击播放")
print(f"   文件大小: {len(content)} 字节")
