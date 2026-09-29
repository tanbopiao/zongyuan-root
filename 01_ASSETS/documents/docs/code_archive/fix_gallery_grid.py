#!/usr/bin/env python3
"""数字画廊改为9:16竖屏网格布局+缩略图占位"""
import re

INDEX = "/www/wwwroot/www.huodouai.com/works-gallery-v2.html"

with open(INDEX, "r", encoding="utf-8") as f:
    content = f.read()

# 1. 替换瀑布流CSS为竖屏网格
old_css = """/* 瀑布流：CSS Columns方案 */
.masonry{columns:4 260px;column-gap:14px}
@media(max-width:1024px){.masonry{columns:3}}
@media(max-width:768px){.masonry{columns:2}}
@media(max-width:480px){.masonry{columns:1}}
.card{break-inside:avoid;margin-bottom:14px;background:linear-gradient(145deg,#1a1a2e,#16213e);border:1px solid rgba(212,175,55,0.1);border-radius:10px;overflow:hidden;cursor:pointer;transition:all .3s;opacity:0;animation:fadeIn .4s forwards;position:relative}"""

new_css = """/* 竖屏网格：9:16固定比例 */
.masonry{display:grid;grid-template-columns:repeat(5,1fr);gap:12px}
@media(max-width:1200px){.masonry{grid-template-columns:repeat(4,1fr)}}
@media(max-width:900px){.masonry{grid-template-columns:repeat(3,1fr)}}
@media(max-width:600px){.masonry{grid-template-columns:repeat(2,1fr);gap:8px}}
.card{background:linear-gradient(145deg,#1a1a2e,#16213e);border:1px solid rgba(212,175,55,0.1);border-radius:10px;overflow:hidden;cursor:pointer;transition:all .3s;opacity:0;animation:fadeIn .4s forwards;position:relative;display:flex;flex-direction:column}"""

content = content.replace(old_css, new_css)

# 2. 媒体区域固定9:16比例
old_media = """.card .media{position:relative;width:100%;background:#000;overflow:hidden}
.card .media img,.card .media video{width:100%;display:block;object-fit:cover}"""

new_media = """.card .media{position:relative;width:100%;aspect-ratio:9/16;background:#000;overflow:hidden;display:flex;align-items:center;justify-content:center}
.card .media img,.card .media video{width:100%;height:100%;object-fit:cover;display:block}
.card .media .thumb-placeholder{width:100%;height:100%;background:linear-gradient(135deg,#0a0a15,#1a1a2e);display:flex;align-items:center;justify-content:center;flex-direction:column;gap:8px}
.card .media .thumb-placeholder .ph-icon{font-size:28px;opacity:0.3}
.card .media .thumb-placeholder .ph-text{font-size:10px;color:#555}"""

content = content.replace(old_media, new_media)

# 3. 播放图标缩小
old_play = """.card .media .play-icon{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);width:44px;height:44px;background:rgba(0,0,0,0.6);border-radius:50%;display:flex;align-items:center;justify-content:center;z-index:2;transition:all .2s}"""
new_play = """.card .media .play-icon{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);width:36px;height:36px;background:rgba(0,0,0,0.6);border-radius:50%;display:flex;align-items:center;justify-content:center;z-index:2;transition:all .2s}"""
content = content.replace(old_play, new_play)

old_play_after = """.card .play-icon::after{content:'';border-style:solid;border-width:8px 0 8px 14px;border-color:transparent transparent transparent #fff;margin-left:3px}"""
new_play_after = """.card .play-icon::after{content:'';border-style:solid;border-width:6px 0 6px 10px;border-color:transparent transparent transparent #fff;margin-left:2px}"""
content = content.replace(old_play_after, new_play_after)

# 4. 信息区域缩小
old_info = """.card .info{padding:10px 12px}
.card .info h4{color:#ddd;font-size:0.85em;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-bottom:3px}
.card .info p{color:#666;font-size:0.72em}
.card .info .meta{display:flex;justify-content:space-between;margin-top:5px;font-size:0.68em;color:#555}"""
new_info = """.card .info{padding:8px 10px;flex-shrink:0}
.card .info h4{color:#ddd;font-size:0.78em;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-bottom:2px}
.card .info p{color:#666;font-size:0.68em}
.card .info .meta{display:flex;justify-content:space-between;margin-top:4px;font-size:0.62em;color:#555}"""
content = content.replace(old_info, new_info)

# 5. 修改渲染逻辑：视频用占位图，不预加载
old_render = """    let media;
    if(w.type === "video"){
      media = '<div class="media"><video muted playsinline preload="none" poster=""><source src="'+w.url+'" type="video/mp4"></video><div class="type-badge">视频</div><div class="model-badge">'+w.model+'</div><div class="play-icon"></div></div>';
    } else {
      media = '<div class="media"><img src="'+w.url+'" alt="'+w.title+'" loading="lazy"><div class="type-badge">图片</div><div class="model-badge">'+w.model+'</div></div>';
    }"""

# 先看看实际的渲染代码是什么样的
# 从之前的grep看，第171-181行是渲染逻辑
# 让我用更通用的方式替换

with open(INDEX, "w", encoding="utf-8") as f:
    f.write(content)

print("竖屏网格CSS已应用")
