import os

# 读取现有画廊页面
with open("/www/wwwroot/huodouai.com/drama/gallery/index.html", "r", encoding="utf-8") as f:
    content = f.read()

# 1. 添加对比相关的全局变量
old_vars = "let favorites = JSON.parse(localStorage.getItem(\"kunlun_favorites\") || \"[]\");"
new_vars = "let favorites = JSON.parse(localStorage.getItem(\"kunlun_favorites\") || \"[]\");\nlet compareMode = false;\nlet selectedWorks = [];\nconst MAX_COMPARE = 3;"
content = content.replace(old_vars, new_vars)

# 2. 在筛选工具区域添加对比模式按钮
old_filter_tools = """  <div class="filter-tools">
    <input type="text" class="search-input" id="search-input" placeholder="搜索作品..." oninput="handleSearch(this.value)">
    <select class="sort-select" id="sort-select" onchange="handleSort(this.value)">"""
new_filter_tools = """  <div class="filter-tools">
    <button class="compare-mode-btn" id="compare-mode-btn" onclick="toggleCompareMode()">对比模式</button>
    <input type="text" class="search-input" id="search-input" placeholder="搜索作品..." oninput="handleSearch(this.value)">
    <select class="sort-select" id="sort-select" onchange="handleSort(this.value)">"""
content = content.replace(old_filter_tools, new_filter_tools)

# 3. 添加对比状态栏（在filter-bar后面）
old_filter_bar_end = """</div>

<div class="stats-row">"""
new_filter_bar_end = """</div>

<!-- 对比状态栏 -->
<div id="compare-bar" style="display:none;background:var(--bg-card);border:1px solid var(--gold-primary);border-radius:10px;padding:12px 20px;margin-bottom:20px;display:flex;justify-content:space-between;align-items:center;">
  <span style="color:var(--gold-primary);font-size:14px;">已选择 <span id="compare-count">0</span>/3 个作品进行对比</span>
  <div style="display:flex;gap:10px;">
    <button onclick="clearCompare()" style="padding:6px 16px;background:transparent;border:1px solid var(--border-color);border-radius:16px;color:var(--text-secondary);font-size:13px;cursor:pointer;">清空</button>
    <button id="start-compare-btn" onclick="startCompare()" disabled style="padding:6px 20px;background:var(--gold-primary);border:none;border-radius:16px;color:#050508;font-size:13px;font-weight:600;cursor:pointer;opacity:0.5;">开始对比</button>
    <button onclick="toggleCompareMode()" style="padding:6px 16px;background:transparent;border:1px solid var(--border-color);border-radius:16px;color:var(--text-secondary);font-size:13px;cursor:pointer;">退出</button>
  </div>
</div>

<div class="stats-row">"""
content = content.replace(old_filter_bar_end, new_filter_bar_end)

# 4. 更新createWorkCard函数，支持对比模式选择
old_card_onclick = """  card.className = "work-card";
  card.onclick = () => handleWorkClick(work);"""
new_card_onclick = """  card.className = "work-card" + (compareMode && selectedWorks.includes(work.id) ? " selected" : "");
  card.onclick = () => {
    if (compareMode) {
      toggleSelectWork(work);
    } else {
      handleWorkClick(work);
    }
  };"""
content = content.replace(old_card_onclick, new_card_onclick)

# 5. 在作品卡片上添加选择标记
old_favorite_btn = """      <button class=\\\\"favorite-btn ${isFavorite ? 'active' : ''}\\\\" onclick=\\\\"event.stopPropagation();toggleFavorite('${work.id}')\\\\">${isFavorite ? '★' : '☆'}</button>"""
new_favorite_btn = """      <button class=\\\\"favorite-btn ${isFavorite ? 'active' : ''}\\\\" onclick=\\\\"event.stopPropagation();toggleFavorite('${work.id}')\\\\">${isFavorite ? '★' : '☆'}</button>
      <div class=\\\\"select-badge\\\\">✓</div>"""
content = content.replace(old_favorite_btn, new_favorite_btn)

# 6. 添加对比相关的CSS样式
old_favorite_css = """.favorite-btn.active { color: #f1c40f; background: rgba(241,196,15,0.2); }"""
new_favorite_css = """.favorite-btn.active { color: #f1c40f; background: rgba(241,196,15,0.2); }
.compare-mode-btn {
  padding: 8px 16px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 20px;
  color: var(--text-primary);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.3s;
}
.compare-mode-btn:hover { border-color: var(--gold-primary); color: var(--gold-primary); }
.compare-mode-btn.active { background: var(--gold-primary); color: #050508; border-color: var(--gold-primary); font-weight: 600; }
.work-card.selected { border-color: var(--gold-primary); box-shadow: 0 0 20px rgba(212,175,55,0.3); }
.work-card.selected .select-badge { display: flex; }
.select-badge {
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
.compare-modal { max-width: 1200px !important; width: 95vw !important; }
.compare-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; padding: 20px; }
.compare-item { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 12px; overflow: hidden; }
.compare-item-media { width: 100%; height: 300px; background: #000; display: flex; align-items: center; justify-content: center; }
.compare-item-media img, .compare-item-media video { max-width: 100%; max-height: 300px; object-fit: contain; }
.compare-item-info { padding: 16px; }
.compare-item-title { font-size: 16px; font-weight: 700; color: var(--gold-primary); margin-bottom: 12px; word-break: break-all; }
.compare-item-row { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid rgba(212,175,55,0.1); font-size: 13px; }
.compare-item-label { color: var(--text-secondary); }
.compare-item-value { color: var(--text-primary); font-weight: 600; }
.compare-score-high { color: #27ae60; }
.compare-score-mid { color: #f39c12; }
.compare-score-low { color: #e74c3c; }"""
content = content.replace(old_favorite_css, new_favorite_css)

# 7. 添加对比相关的函数（在toggleFavorite函数后面）
old_toggle_favorite_end = """  // 如果当前在收藏筛选，重新渲染
  if (currentFilter === "favorites") {
    applyFilters();
  }
}"""
new_toggle_favorite_end = """  // 如果当前在收藏筛选，重新渲染
  if (currentFilter === "favorites") {
    applyFilters();
  }
}

function toggleCompareMode() {
  compareMode = !compareMode;
  selectedWorks = [];
  const btn = document.getElementById("compare-mode-btn");
  const compareBar = document.getElementById("compare-bar");
  
  if (compareMode) {
    btn.classList.add("active");
    btn.textContent = "退出对比";
    compareBar.style.display = "flex";
  } else {
    btn.classList.remove("active");
    btn.textContent = "对比模式";
    compareBar.style.display = "none";
  }
  
  updateCompareBar();
  applyFilters();
}

function toggleSelectWork(work) {
  const index = selectedWorks.findIndex(w => w.id === work.id);
  if (index > -1) {
    selectedWorks.splice(index, 1);
  } else {
    if (selectedWorks.length >= MAX_COMPARE) {
      alert("最多只能选择" + MAX_COMPARE + "个作品进行对比");
      return;
    }
    selectedWorks.push(work);
  }
  updateCompareBar();
  applyFilters();
}

function updateCompareBar() {
  document.getElementById("compare-count").textContent = selectedWorks.length;
  const btn = document.getElementById("start-compare-btn");
  if (selectedWorks.length >= 2) {
    btn.disabled = false;
    btn.style.opacity = "1";
  } else {
    btn.disabled = true;
    btn.style.opacity = "0.5";
  }
}

function clearCompare() {
  selectedWorks = [];
  updateCompareBar();
  applyFilters();
}

function startCompare() {
  if (selectedWorks.length < 2) {
    alert("请至少选择2个作品进行对比");
    return;
  }
  
  const modal = document.getElementById("video-modal");
  const media = document.getElementById("detail-media");
  const info = document.getElementById("detail-info");
  
  // 修改模态框样式为对比模式
  modal.querySelector(".modal-content").classList.add("compare-modal");
  
  // 生成对比内容
  let compareHTML = '<div class="compare-grid">';
  selectedWorks.forEach(work => {
    const qcResult = qcResults[work.title + ".mp4"] || qcResults[work.title + ".jpg"] || qcResults[work.title + ".png"] || {};
    const qualityScore = qcResult.quality_score || work.quality_score || 0;
    const scoreClass = qualityScore >= 90 ? "compare-score-high" : qualityScore >= 70 ? "compare-score-mid" : "compare-score-low";
    const multiHand = qcResult.has_multi_hand ? "❌" : "✅";
    const deformity = qcResult.has_deformity ? "❌" : "✅";
    const passed = qcResult.passed ? "✅ 通过" : "❌ 未通过";
    
    compareHTML += '<div class="compare-item">';
    compareHTML += '<div class="compare-item-media">';
    if (work.type === "video" && work.video_url) {
      compareHTML += '<video src="' + work.video_url + '" controls></video>';
    } else {
      compareHTML += '<img src="' + work.thumbnail + '" alt="' + work.title + '">';
    }
    compareHTML += '</div>';
    compareHTML += '<div class="compare-item-info">';
    compareHTML += '<div class="compare-item-title">' + work.title + '</div>';
    compareHTML += '<div class="compare-item-row"><span class="compare-item-label">类型</span><span class="compare-item-value">' + (work.type === "video" ? "视频" : "图片") + '</span></div>';
    compareHTML += '<div class="compare-item-row"><span class="compare-item-label">角色</span><span class="compare-item-value">' + (work.character || "-") + '</span></div>';
    compareHTML += '<div class="compare-item-row"><span class="compare-item-label">分类</span><span class="compare-item-value">' + (work.category || "-") + '</span></div>';
    compareHTML += '<div class="compare-item-row"><span class="compare-item-label">质量评分</span><span class="compare-item-value ' + scoreClass + '">' + qualityScore + '分</span></div>';
    compareHTML += '<div class="compare-item-row"><span class="compare-item-label">质检状态</span><span class="compare-item-value">' + passed + '</span></div>';
    compareHTML += '<div class="compare-item-row"><span class="compare-item-label">多手问题</span><span class="compare-item-value">' + multiHand + '</span></div>';
    compareHTML += '<div class="compare-item-row"><span class="compare-item-label">肢体畸形</span><span class="compare-item-value">' + deformity + '</span></div>';
    if (work.size_mb) {
      compareHTML += '<div class="compare-item-row"><span class="compare-item-label">文件大小</span><span class="compare-item-value">' + work.size_mb + 'MB</span></div>';
    }
    compareHTML += '</div></div>';
  });
  compareHTML += '</div>';
  
  media.innerHTML = compareHTML;
  info.innerHTML = "";
  modal.classList.add("active");
}"""

content = content.replace(old_toggle_favorite_end, new_toggle_favorite_end)

# 8. 修改closeModal函数，移除对比模式样式
old_close_modal = """function closeModal() {
  document.getElementById("video-modal").classList.remove("active");
  const video = document.getElementById("modal-video");
  if (video) { video.pause(); video.src = ""; }
}"""
new_close_modal = """function closeModal() {
  document.getElementById("video-modal").classList.remove("active");
  document.querySelector(".modal-content").classList.remove("compare-modal");
  const video = document.getElementById("modal-video");
  if (video) { video.pause(); video.src = ""; }
}"""
content = content.replace(old_close_modal, new_close_modal)

# 写入文件
with open("/www/wwwroot/huodouai.com/drama/gallery/index.html", "w", encoding="utf-8") as f:
    f.write(content)

print("✅ 画廊页面已更新，添加作品对比功能")
print("  对比模式: 点击对比模式按钮进入")
print("  选择数量: 最多3个作品")
print("  对比内容: 质量评分/质检状态/多手问题/肢体畸形/文件大小")
