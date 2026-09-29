import os

# 读取现有画廊页面
with open("/www/wwwroot/huodouai.com/drama/gallery/index.html", "r", encoding="utf-8") as f:
    content = f.read()

# 1. 在createWorkCard函数中添加hover预加载事件
old_card_append = """  works.forEach((work, index) => {
    const card = createWorkCard(work);
    card.style.animationDelay = ((i % PAGE_SIZE) * 0.03) + "s";
    grid.appendChild(card);
  });"""

new_card_append = """  works.forEach((work, index) => {
    const card = createWorkCard(work);
    card.style.animationDelay = ((i % PAGE_SIZE) * 0.03) + "s";
    
    // 视频hover预加载
    if (work.type === "video" && work.video_url) {
      card.addEventListener("mouseenter", () => preloadVideo(work.video_url));
    }
    
    grid.appendChild(card);
  });"""

content = content.replace(old_card_append, new_card_append)

# 2. 添加预加载视频的函数（在copyShareLink函数后面）
old_copy_end = """  } else {
    document.execCommand("copy");
    btn.textContent = "已复制 ✓";
    btn.classList.add("copied");
    setTimeout(() => {
      btn.textContent = "复制链接";
      btn.classList.remove("copied");
    }, 2000);
  }
}"""

new_copy_end = """  } else {
    document.execCommand("copy");
    btn.textContent = "已复制 ✓";
    btn.classList.add("copied");
    setTimeout(() => {
      btn.textContent = "复制链接";
      btn.classList.remove("copied");
    }, 2000);
  }
}

// 视频预加载缓存
const preloadedVideos = new Set();

function preloadVideo(url) {
  if (preloadedVideos.has(url)) return;
  preloadedVideos.add(url);
  
  // 创建隐藏的video元素来预加载
  const video = document.createElement("video");
  video.preload = "auto";
  video.src = url;
  video.muted = true;
  video.playsInline = true;
  
  // 只加载前几秒的数据
  video.addEventListener("loadedmetadata", () => {
    try {
      video.currentTime = 0.1;
    } catch (e) {}
  });
  
  // 加载完成后移除元素（保留缓存）
  video.addEventListener("canplaythrough", () => {
    setTimeout(() => {
      if (video.parentNode) {
        video.parentNode.removeChild(video);
      }
    }, 1000);
  });
  
  // 添加到页面（隐藏）
  video.style.display = "none";
  video.style.position = "absolute";
  video.style.width = "0";
  video.style.height = "0";
  document.body.appendChild(video);
  
  // 30秒后如果还没播放，移除元素
  setTimeout(() => {
    if (video.parentNode) {
      video.parentNode.removeChild(video);
    }
  }, 30000);
}"""

content = content.replace(old_copy_end, new_copy_end)

# 3. 在作品卡片上添加hover提示（视频卡片显示"hover预加载中"）
old_play_button = """      ${isVideo ? "<div class=\\\\"play-button\\\\">▶</div>" : ""}"""
new_play_button = """      ${isVideo ? "<div class=\\\\"play-button\\\\">▶</div><div class=\\\\"hover-preload-tip\\\\">点击播放</div>" : ""}"""
content = content.replace(old_play_button, new_play_button)

# 4. 添加hover提示的CSS样式（在select-badge样式后面）
old_select_badge_css = """.select-badge {
  display: none;
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 48px;
  height: 48px;
  background: rgba(212,175,55,0.9);
  border-radius: 50%;
  color: #050508;
  font-size: 24px;
  font-weight: 900;
  align-items: center;
  justify-content: center;
  z-index: 3;
}"""

new_select_badge_css = """.select-badge {
  display: none;
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 48px;
  height: 48px;
  background: rgba(212,175,55,0.9);
  border-radius: 50%;
  color: #050508;
  font-size: 24px;
  font-weight: 900;
  align-items: center;
  justify-content: center;
  z-index: 3;
}
.hover-preload-tip {
  position: absolute;
  bottom: 8px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(0,0,0,0.7);
  color: #fff;
  font-size: 11px;
  padding: 4px 10px;
  border-radius: 10px;
  opacity: 0;
  transition: opacity 0.3s;
  z-index: 2;
  white-space: nowrap;
}
.work-card:hover .hover-preload-tip {
  opacity: 1;
}"""

content = content.replace(old_select_badge_css, new_select_badge_css)

# 写入文件
with open("/www/wwwroot/huodouai.com/drama/gallery/index.html", "w", encoding="utf-8") as f:
    f.write(content)

print("✅ 画廊页面已更新，添加视频hover预加载功能")
print("  预加载方式: hover时创建隐藏video元素预加载")
print("  缓存机制: Set去重，避免重复预加载")
print("  自动清理: 30秒后自动移除预加载元素")
