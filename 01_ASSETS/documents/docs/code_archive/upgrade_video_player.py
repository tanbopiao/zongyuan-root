import os

# 读取现有画廊页面
with open("/www/wwwroot/huodouai.com/drama/gallery/index.html", "r", encoding="utf-8") as f:
    content = f.read()

# 1. 找到handleWorkClick函数中视频播放的部分，替换为增强版播放器
old_video_play = """  if (work.type === "video" && work.video_url) {
    media.innerHTML = '<video id="modal-video" src="' + work.video_url + '" controls autoplay style="width:100%;max-height:70vh;background:#000;border-radius:8px;"></video>';
  } else {
    media.innerHTML = '<img src="' + work.thumbnail + '" alt="' + work.title + '" style="width:100%;max-height:70vh;object-fit:contain;border-radius:8px;">';
  }"""

new_video_play = """  if (work.type === "video" && work.video_url) {
    media.innerHTML = '<div class="video-player-container">' +
      '<video id="modal-video" src="' + work.video_url + '" autoplay playsinline style="width:100%;max-height:60vh;background:#000;border-radius:8px 8px 0 0;"></video>' +
      '<div class="video-controls">' +
      '<div class="video-progress-bar" id="video-progress-bar">' +
      '<div class="video-progress-fill" id="video-progress-fill"></div>' +
      '<div class="video-progress-thumb" id="video-progress-thumb"></div>' +
      '</div>' +
      '<div class="video-controls-row">' +
      '<button class="video-ctrl-btn" onclick="prevVideo()" title="上一个">⏮</button>' +
      '<button class="video-ctrl-btn" id="play-pause-btn" onclick="togglePlayPause()" title="播放/暂停">⏸</button>' +
      '<button class="video-ctrl-btn" onclick="nextVideo()" title="下一个">⏭</button>' +
      '<span class="video-time" id="video-time">00:00 / 00:00</span>' +
      '<div class="video-speed-control">' +
      '<button class="video-ctrl-btn" id="speed-btn" onclick="toggleSpeedMenu()" title="倍速">1x</button>' +
      '<div class="speed-menu" id="speed-menu">' +
      '<button onclick="setSpeed(0.5)">0.5x</button>' +
      '<button onclick="setSpeed(1)">1x</button>' +
      '<button onclick="setSpeed(1.5)">1.5x</button>' +
      '<button onclick="setSpeed(2)">2x</button>' +
      '</div></div>' +
      '<button class="video-ctrl-btn" onclick="toggleMute()" id="mute-btn" title="静音">🔊</button>' +
      '<input type="range" class="video-volume" id="video-volume" min="0" max="1" step="0.1" value="1" oninput="setVolume(this.value)">' +
      '<button class="video-ctrl-btn" onclick="toggleFullscreen()" title="全屏">⛶</button>' +
      '</div></div></div>';
    
    // 初始化视频事件
    setTimeout(initVideoPlayer, 100);
  } else {
    media.innerHTML = '<img src="' + work.thumbnail + '" alt="' + work.title + '" style="width:100%;max-height:70vh;object-fit:contain;border-radius:8px;">';
  }"""

content = content.replace(old_video_play, new_video_play)

# 2. 添加视频播放器CSS样式（在recommendation-title样式后面）
old_rec_title_css = """.recommendations-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--gold-primary);
  margin-bottom: 16px;
}"""

new_rec_title_css = """.recommendations-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--gold-primary);
  margin-bottom: 16px;
}

/* 视频播放器 */
.video-player-container {
  background: #000;
  border-radius: 8px;
  overflow: hidden;
}
.video-controls {
  background: linear-gradient(to top, rgba(0,0,0,0.9), rgba(0,0,0,0.7));
  padding: 8px 12px;
}
.video-progress-bar {
  width: 100%;
  height: 6px;
  background: rgba(255,255,255,0.2);
  border-radius: 3px;
  cursor: pointer;
  margin-bottom: 8px;
  position: relative;
}
.video-progress-fill {
  height: 100%;
  background: var(--gold-primary);
  border-radius: 3px;
  width: 0%;
  transition: width 0.1s;
}
.video-progress-thumb {
  position: absolute;
  top: 50%;
  left: 0%;
  transform: translate(-50%, -50%);
  width: 12px;
  height: 12px;
  background: var(--gold-primary);
  border-radius: 50%;
  opacity: 0;
  transition: opacity 0.2s;
}
.video-progress-bar:hover .video-progress-thumb {
  opacity: 1;
}
.video-controls-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.video-ctrl-btn {
  background: none;
  border: none;
  color: #fff;
  font-size: 16px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  transition: background 0.2s;
}
.video-ctrl-btn:hover {
  background: rgba(255,255,255,0.1);
}
.video-time {
  color: rgba(255,255,255,0.8);
  font-size: 12px;
  font-family: monospace;
  flex: 1;
}
.video-speed-control {
  position: relative;
}
.speed-menu {
  display: none;
  position: absolute;
  bottom: 100%;
  right: 0;
  background: rgba(0,0,0,0.95);
  border-radius: 6px;
  padding: 4px;
  margin-bottom: 4px;
  min-width: 60px;
}
.speed-menu.show {
  display: block;
}
.speed-menu button {
  display: block;
  width: 100%;
  background: none;
  border: none;
  color: #fff;
  font-size: 12px;
  padding: 6px 12px;
  cursor: pointer;
  border-radius: 4px;
  text-align: center;
}
.speed-menu button:hover {
  background: rgba(212,175,55,0.3);
}
.video-volume {
  width: 60px;
  height: 4px;
  -webkit-appearance: none;
  background: rgba(255,255,255,0.2);
  border-radius: 2px;
  outline: none;
}
.video-volume::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 10px;
  height: 10px;
  background: var(--gold-primary);
  border-radius: 50%;
  cursor: pointer;
}"""

content = content.replace(old_rec_title_css, new_rec_title_css)

# 3. 添加视频播放器相关函数（在loadRecommendations函数后面）
old_load_rec_end = """  recommendationsSection.style.display = "block";
}

function shareWork(title, url) {"""

new_load_rec_end = """  recommendationsSection.style.display = "block";
}

// ========== 视频播放器功能 ==========
let currentVideoIndex = -1;

function initVideoPlayer() {
  const video = document.getElementById("modal-video");
  if (!video) return;
  
  // 找到当前视频在作品列表中的索引
  const allWorks = getFilteredWorks();
  const videoWorks = allWorks.filter(w => w.type === "video");
  currentVideoIndex = videoWorks.findIndex(w => w.title === document.querySelector(".detail-title")?.textContent);
  
  // 播放进度更新
  video.addEventListener("timeupdate", updateProgress);
  
  // 播放/暂停状态更新
  video.addEventListener("play", () => {
    document.getElementById("play-pause-btn").textContent = "⏸";
  });
  video.addEventListener("pause", () => {
    document.getElementById("play-pause-btn").textContent = "▶";
  });
  
  // 点击进度条跳转
  document.getElementById("video-progress-bar").addEventListener("click", seekVideo);
  
  // 视频结束自动播放下一个
  video.addEventListener("ended", nextVideo);
  
  // 初始化音量
  video.volume = 1;
}

function updateProgress() {
  const video = document.getElementById("modal-video");
  if (!video) return;
  
  const percent = (video.currentTime / video.duration) * 100;
  document.getElementById("video-progress-fill").style.width = percent + "%";
  document.getElementById("video-progress-thumb").style.left = percent + "%";
  
  const currentTime = formatTime(video.currentTime);
  const duration = formatTime(video.duration);
  document.getElementById("video-time").textContent = currentTime + " / " + duration;
}

function formatTime(seconds) {
  if (isNaN(seconds)) return "00:00";
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return String(mins).padStart(2, "0") + ":" + String(secs).padStart(2, "0");
}

function seekVideo(e) {
  const video = document.getElementById("modal-video");
  if (!video) return;
  
  const rect = e.currentTarget.getBoundingClientRect();
  const percent = (e.clientX - rect.left) / rect.width;
  video.currentTime = percent * video.duration;
}

function togglePlayPause() {
  const video = document.getElementById("modal-video");
  if (!video) return;
  
  if (video.paused) {
    video.play();
  } else {
    video.pause();
  }
}

function toggleSpeedMenu() {
  document.getElementById("speed-menu").classList.toggle("show");
}

function setSpeed(speed) {
  const video = document.getElementById("modal-video");
  if (!video) return;
  
  video.playbackRate = speed;
  document.getElementById("speed-btn").textContent = speed + "x";
  document.getElementById("speed-menu").classList.remove("show");
}

function toggleMute() {
  const video = document.getElementById("modal-video");
  if (!video) return;
  
  video.muted = !video.muted;
  document.getElementById("mute-btn").textContent = video.muted ? "🔇" : "🔊";
}

function setVolume(value) {
  const video = document.getElementById("modal-video");
  if (!video) return;
  
  video.volume = value;
  if (value == 0) {
    video.muted = true;
    document.getElementById("mute-btn").textContent = "🔇";
  } else {
    video.muted = false;
    document.getElementById("mute-btn").textContent = "🔊";
  }
}

function toggleFullscreen() {
  const container = document.querySelector(".video-player-container");
  if (!container) return;
  
  if (document.fullscreenElement) {
    document.exitFullscreen();
  } else {
    container.requestFullscreen();
  }
}

function prevVideo() {
  const videoWorks = getFilteredWorks().filter(w => w.type === "video");
  if (videoWorks.length === 0) return;
  
  currentVideoIndex = (currentVideoIndex - 1 + videoWorks.length) % videoWorks.length;
  const work = videoWorks[currentVideoIndex];
  closeModal();
  setTimeout(() => handleWorkClick(work), 200);
}

function nextVideo() {
  const videoWorks = getFilteredWorks().filter(w => w.type === "video");
  if (videoWorks.length === 0) return;
  
  currentVideoIndex = (currentVideoIndex + 1) % videoWorks.length;
  const work = videoWorks[currentVideoIndex];
  closeModal();
  setTimeout(() => handleWorkClick(work), 200);
}

// 点击其他地方关闭倍速菜单
document.addEventListener("click", (e) => {
  if (!e.target.closest(".video-speed-control")) {
    const menu = document.getElementById("speed-menu");
    if (menu) menu.classList.remove("show");
  }
});

function shareWork(title, url) {"""

content = content.replace(old_load_rec_end, new_load_rec_end)

# 写入文件
with open("/www/wwwroot/huodouai.com/drama/gallery/index.html", "w", encoding="utf-8") as f:
    f.write(content)

print("✅ 画廊页面已更新，视频播放器升级完成")
print("  新增功能:")
print("    - 自定义控制栏（播放/暂停/进度条）")
print("    - 倍速播放（0.5x/1x/1.5x/2x）")
print("    - 全屏模式")
print("    - 连续播放（上一个/下一个）")
print("    - 音量控制+静音")
print("    - 播放结束自动下一个")
