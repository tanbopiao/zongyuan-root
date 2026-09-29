#!/usr/bin/env python3
"""综合优化：约束放松 + 网页加载效率"""

# ========== 优化1：lightweight页面 ==========
page1 = "/www/wwwroot/www.huodouai.com/lightweight-strategy-v2.html"
with open(page1, encoding="utf-8") as f:
    c1 = f.read()

# 1a. 放松约束：去掉第5条禁止，改为允许介绍真实业务
old_constraint = "const SYSTEM_CONSTRAINT = '你是火斗云智AIOS官方智能体，必须严格遵守：1.对外品牌统一用火斗云智AIOS/火斗云智系统；2.核心理念：轻量化优先+网页即智能体身体；3.确权DID-BR-000002，溯源Omega_0 subset circle_infinity subset Omega；4.回答简洁专业不超过200字；5.禁止提及昆仑洞天/短剧/东方神女；6.零成本运行；7.以最优稳态为决策准则';"
new_constraint = "const SYSTEM_CONSTRAINT = '你是火斗云智AIOS官方智能体，必须严格遵守：1.对外品牌统一用火斗云智AIOS/火斗云智系统；2.核心理念：轻量化优先+网页即智能体身体；3.确权DID-BR-000002，溯源Omega_0 subset circle_infinity subset Omega；4.回答简洁专业，重点突出；5.可以介绍火斗云智AIOS旗下所有产品和作品（包括昆仑洞天短剧、数字画廊、政务AI等），基于真实信息回答；6.零成本运行；7.以最优稳态为决策准则';"
c1 = c1.replace(old_constraint, new_constraint)
print("✅ 约束已放松：允许介绍真实业务")

# 1b. echarts异步加载（不阻塞首屏）
old_echarts = '<script src="/assets/echarts.min.js"></script>'
new_echarts = '<script>window.addEventListener("load",function(){var s=document.createElement("script");s.src="/assets/echarts.min.js";s.onload=function(){if(window.initCharts)initCharts();};document.body.appendChild(s);});</script>'
c1 = c1.replace(old_echarts, new_echarts)

# 把echarts初始化代码包装成initCharts函数
old_init = "const c1 = echarts.init"
new_init = "function initCharts(){const c1 = echarts.init"
c1 = c1.replace(old_init, new_init)

# 在echarts代码结束后添加闭合括号
# 找到第二个echarts.init后的setOption结束位置
old_c2_setoption = "c2.setOption(option2);"
new_c2_setoption = "c2.setOption(option2);}if(window.echarts)initCharts();"
c1 = c1.replace(old_c2_setoption, new_c2_setoption)
print("✅ echarts改为异步加载（首屏不阻塞）")

# 1c. 增加响应式适配
old_media = "@media(max-width:768px){.hero h1{font-size:1.6em}.section{padding:18px}.chart{height:280px}.tier{width:95%!important}}"
new_media = """@media(max-width:768px){.hero h1{font-size:1.6em}.section{padding:18px}.chart{height:280px}.tier{width:95%!important}}
@media(max-width:480px){.hero h1{font-size:1.3em}.stats-grid{grid-template-columns:1fr 1fr}.chat-panel{right:10px;left:10px;width:auto}}
@media(prefers-reduced-motion:reduce){*{animation-duration:0.01ms!important;transition-duration:0.01ms!important}}"""
c1 = c1.replace(old_media, new_media)
print("✅ 响应式适配增强（增加480px断点+减少动画偏好）")

with open(page1, "w", encoding="utf-8") as f:
    f.write(c1)

# ========== 优化2：数字画廊页面 ==========
page2 = "/www/wwwroot/www.huodouai.com/digital-gallery-v3.html"
with open(page2, encoding="utf-8") as f:
    c2 = f.read()

# 2a. 移除外部字体CDN，使用系统字体
old_font = '<link rel="stylesheet" href="https://miaoda.feishu.cn/fonts/css2?family=Noto+Serif+SC:wght@400;600;700;900&family=Noto+Sans+SC:wght@300;400;500;700&display=swap">'
new_font = '<!-- 字体使用系统栈，消除外部CDN请求 -->'
c2 = c2.replace(old_font, new_font)
print("✅ 移除外部字体CDN（使用系统字体）")

# 2b. 缩略图懒加载（给video-thumb添加data-src，首屏只加载前6个）
# 这个比较复杂，先简化：给缩略图背景添加loading优化
# 实际上CSS background-image不支持懒加载，需要用IntersectionObserver
# 简单方案：首屏只渲染前6个视频卡片，滚动时再加载更多
old_render = "function renderVideos(){"
new_render = """let videosLoaded = 0;
function renderVideos(){
  const row = document.getElementById("videoRow");
  const videos = curFilter==="keyframe" ? [] : VIDEOS;
  document.getElementById("videoCount").textContent = videos.length + "件";
  document.getElementById("videoSection").style.display = videos.length ? "block" : "none";
  // 首屏只渲染前6个，其余滚动加载
  const firstBatch = videos.slice(0,6);
  const restBatch = videos.slice(6);
  row.innerHTML = firstBatch.map((v,i)=>renderVideoCard(v, allWorks.indexOf(v))).join("");
  videosLoaded = 6;
  if(restBatch.length){
    const observer = new IntersectionObserver((entries)=>{
      entries.forEach(e=>{
        if(e.isIntersecting){
          row.insertAdjacentHTML("beforeend", restBatch.map((v,i)=>renderVideoCard(v, allWorks.indexOf(v))).join(""));
          observer.disconnect();
        }
      });
    }, {rootMargin: "200px"});
    const sentinel = document.createElement("div");
    sentinel.id = "videoSentinel";
    sentinel.style.height = "10px";
    row.appendChild(sentinel);
    observer.observe(sentinel);
  }
}
function renderVideoCard(v, idx){
  return '<div class="frame-card" onclick="openImmersive('+idx+')">'+
    '<div class="frame">'+
      '<span class="badge">▶ '+v.cat+'</span>'+
      '<span class="model-tag">'+v.model+'</span>'+
      '<div class="video-thumb" data-url="'+v.url+'" style="background-image:url(/assets/videos/thumbs'+v.url.replace('/assets/videos','').replace('.mp4','.jpg')+');background-size:cover;background-position:center"><div class="play-btn">▶</div></div>'+
      '<div class="play-overlay"><div class="play-btn"></div></div>'+
    '</div>'+
    '<div class="info"><h4>'+v.title+'</h4><p>'+v.model+' · '+v.size+'</p></div>'+
  '</div>';
}
// 旧函数保留兼容
function _renderVideosOld(){"""
c2 = c2.replace(old_render, new_render)
print("✅ 视频缩略图懒加载（首屏6个，滚动加载其余）")

# 2c. 增加响应式适配
old_gallery_media = "@media(max-width:768px){.hero h1{font-size:1.5em}.grid{grid-template-columns:repeat(2,1fr)}.frame-row{grid-template-columns:repeat(2,1fr)}}"
new_gallery_media = """@media(max-width:768px){.hero h1{font-size:1.5em}.grid{grid-template-columns:repeat(2,1fr)}.frame-row{grid-template-columns:repeat(2,1fr)}}
@media(max-width:480px){.grid{grid-template-columns:1fr}.frame-row{grid-template-columns:1fr}.ai-guide-panel{width:calc(100vw - 40px);right:20px}}
@media(prefers-reduced-motion:reduce){*{animation-duration:0.01ms!important;transition-duration:0.01ms!important}}"""
c2 = c2.replace(old_gallery_media, new_gallery_media)
print("✅ 数字画廊响应式增强")

with open(page2, "w", encoding="utf-8") as f:
    f.write(c2)

print("\n✅ 综合优化完成")
