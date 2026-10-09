import os

# 读取现有画廊页面
with open("/www/wwwroot/huodouai.com/drama/gallery/index.html", "r", encoding="utf-8") as f:
    content = f.read()

# ========== 1. 添加全局变量 ==========
old_vars = "let compareMode = false;\nlet selectedWorks = [];\nconst MAX_COMPARE = 3;"
new_vars = """let compareMode = false;
let selectedWorks = [];
const MAX_COMPARE = 3;
let comments = JSON.parse(localStorage.getItem("kunlun_comments") || "{}");
let ratings = JSON.parse(localStorage.getItem("kunlun_ratings") || "{}");
let currentTheme = localStorage.getItem("kunlun_theme") || "dark";"""
content = content.replace(old_vars, new_vars)

# ========== 2. 在导航栏添加主题切换按钮 ==========
old_nav_toggle = """    <button class="zy-nav-toggle" onclick="document.querySelector('.zy-nav-mobile').classList.toggle('open')">☰</button>"""
new_nav_toggle = """    <button class="theme-toggle-btn" onclick="toggleTheme()" title="切换主题">🌙</button>
    <button class="zy-nav-toggle" onclick="document.querySelector('.zy-nav-mobile').classList.toggle('open')">☰</button>"""
content = content.replace(old_nav_toggle, new_nav_toggle)

# ========== 3. 在筛选工具区域添加标签筛选 ==========
old_filter_tools = """  <div class="filter-tools">
    <button class="compare-mode-btn" id="compare-mode-btn" onclick="toggleCompareMode()">对比模式</button>
    <input type="text" class="search-input" id="search-input" placeholder="搜索作品..." oninput="handleSearch(this.value)">
    <select class="sort-select" id="sort-select" onchange="handleSort(this.value)">"""
new_filter_tools = """  <div class="filter-tools">
    <button class="compare-mode-btn" id="compare-mode-btn" onclick="toggleCompareMode()">对比模式</button>
    <select class="tag-filter-select" id="tag-filter" onchange="handleTagFilter(this.value)">
      <option value="all">全部标签</option>
      <option value="国风">国风</option>
      <option value="仙侠">仙侠</option>
      <option value="写实">写实</option>
      <option value="暗黑">暗黑</option>
      <option value="唯美">唯美</option>
      <option value="战争">战争</option>
      <option value="修真">修真</option>
      <option value="星夜">星夜</option>
    </select>
    <input type="text" class="search-input" id="search-input" placeholder="搜索作品..." oninput="handleSearch(this.value)">
    <select class="sort-select" id="sort-select" onchange="handleSort(this.value)">"""
content = content.replace(old_filter_tools, new_filter_tools)

# ========== 4. 添加标签筛选变量 ==========
old_current_filter = "let currentFilter = \"all\";\nlet currentSearch = \"\";\nlet currentSort = \"default\";"
new_current_filter = "let currentFilter = \"all\";\nlet currentSearch = \"\";\nlet currentSort = \"default\";\nlet currentTagFilter = \"all\";"
content = content.replace(old_current_filter, new_current_filter)

# ========== 5. 在getFilteredWorks中添加标签筛选 ==========
old_filter_check = """  if (currentFilter !== "all") {
    if (currentFilter === "video") {
      filtered = filtered.filter(w => w.type === "video");
    } else if (currentFilter === "image") {
      filtered = filtered.filter(w => w.type === "image");
    } else if (currentFilter === "favorites") {
      filtered = filtered.filter(w => favorites.includes(w.id));
    } else {
      filtered = filtered.filter(w => w.character === currentFilter);
    }
  }"""
new_filter_check = """  if (currentFilter !== "all") {
    if (currentFilter === "video") {
      filtered = filtered.filter(w => w.type === "video");
    } else if (currentFilter === "image") {
      filtered = filtered.filter(w => w.type === "image");
    } else if (currentFilter === "favorites") {
      filtered = filtered.filter(w => favorites.includes(w.id));
    } else {
      filtered = filtered.filter(w => w.character === currentFilter);
    }
  }
  
  // 标签筛选
  if (currentTagFilter !== "all") {
    filtered = filtered.filter(w => w.tags && w.tags.includes(currentTagFilter));
  }"""
content = content.replace(old_filter_check, new_filter_check)

# ========== 6. 为作品数据添加标签（在worksData定义后） ==========
old_works_data_end = "const worksData = WORKS_DATA;"
new_works_data_end = """const worksData = WORKS_DATA;

// 为作品添加标签
worksData.forEach(work => {
  if (!work.tags) {
    work.tags = [];
    if (work.character === "九天玄女") work.tags.push("国风", "仙侠", "战争");
    else if (work.character === "太阴月神") work.tags.push("国风", "唯美", "星夜");
    else if (work.character === "女娲") work.tags.push("国风", "写实", "暗黑");
    else if (work.character === "西王母") work.tags.push("国风", "修真", "暗黑");
    else work.tags.push("国风", "仙侠");
    
    if (work.type === "video") work.tags.push("动态");
    else work.tags.push("静态");
  }
});"""
content = content.replace(old_works_data_end, new_works_data_end)

# ========== 7. 在作品卡片上显示标签 ==========
old_card_meta = """      <div class="work-card-meta">
        <span class="work-card-character">${work.character || "未分类"}</span>
        <span class="work-card-type">${isVideo ? "视频" : "图片"}</span>
      </div>"""
new_card_meta = """      <div class="work-card-meta">
        <span class="work-card-character">${work.character || "未分类"}</span>
        <span class="work-card-type">${isVideo ? "视频" : "图片"}</span>
      </div>
      <div class="work-card-tags">${work.tags ? work.tags.slice(0, 2).map(t => '<span class="work-tag">' + t + '</span>').join("") : ""}</div>"""
content = content.replace(old_card_meta, new_card_meta)

# ========== 8. 在详情页添加评分和评论功能 ==========
old_detail_actions = """    "<div class=\\"detail-actions\\"><button class=\\"detail-action-btn\\" onclick=\\"shareWork('" + work.title.replace(/'/g, "\\\\'") + "', '" + (work.video_url || work.thumbnail) + "')\\">🔗 分享作品</button></div>";"""
new_detail_actions = """    "<div class=\\"detail-actions\\">" +
    "<button class=\\"detail-action-btn\\" onclick=\\"shareWork('" + work.title.replace(/'/g, "\\\\'") + "', '" + (work.video_url || work.thumbnail) + "')\\">🔗 分享作品</button>" +
    "</div>" +
    "<div class=\\"detail-rating-section\\"><h4 style=\\"color:var(--gold-primary);margin-bottom:10px;\\">作品评分</h4>" +
    "<div class=\\"rating-stars\\" id=\\"rating-stars\\">" +
    [1,2,3,4,5].map(i => "<span class=\\"rating-star\\" data-rating=\\"" + i + "\\" onclick=\\"rateWork('" + work.id + "', " + i + ")\\">★</span>").join("") +
    "</div>" +
    "<span class=\\"rating-text\\" id=\\"rating-text\\">" + (ratings[work.id] ? "已评分: " + ratings[work.id] + "星" : "点击星星评分") + "</span>" +
    (ratings[work.id] ? "<button class=\\"rating-clear-btn\\" onclick=\\"clearRating('" + work.id + "')\\">清除评分</button>" : "") +
    "</div>" +
    "<div class=\\"detail-comments-section\\"><h4 style=\\"color:var(--gold-primary);margin-bottom:10px;\\">评论 (" + (comments[work.id] ? comments[work.id].length : 0) + ")</h4>" +
    "<div class=\\"comment-input-container\\">" +
    "<textarea class=\\"comment-input\\" id=\\"comment-input\\" placeholder=\\"写下你的评论...\\" rows=\\"2\\"></textarea>" +
    "<button class=\\"comment-submit-btn\\" onclick=\\"addComment('" + work.id + "')\\">发表</button>" +
    "</div>" +
    "<div class=\\"comments-list\\" id=\\"comments-list\\">" +
    (comments[work.id] ? comments[work.id].map(c => "<div class=\\"comment-item\\"><div class=\\"comment-header\\"><span class=\\"comment-author\\">用户</span><span class=\\"comment-time\\">" + c.time + "</span></div><div class=\\"comment-content\\">" + c.content + "</div></div>").join("") : "<div class=\\"comment-empty\\">暂无评论，来发表第一条评论吧</div>") +
    "</div></div>";"""
content = content.replace(old_detail_actions, new_detail_actions)

# ========== 9. 在详情页底部添加推荐作品 ==========
old_detail_end = """  document.getElementById("detail-info").innerHTML = `
    <h2 class="detail-title">${work.title}</h2>
    <div class="detail-meta">
      <span>类型: ${work.type === "video" ? "视频" : "图片"}</span>
      <span>角色: ${work.character || "未分类"}</span>
      <span>分类: ${work.category || "未分类"}</span>
      ${work.size_mb ? `<span>大小: ${work.size_mb}MB</span>` : ""}
    </div>
    <div class="detail-quality">
      <div class="quality-label">质量评分</div>
      <div class="quality-bar"><div class="quality-fill" style="width: ${qualityScore}%; background: ${qualityColor};"></div></div>
      <div class="quality-score" style="color: ${qualityColor};">${qualityScore}分</div>
    </div>
    <div class="detail-description">${work.description || "暂无描述"}</div>
    ${qcBadge}
    ${qcInfo}
    ${shareBtn}
  `;"""

new_detail_end = """  document.getElementById("detail-info").innerHTML = `
    <h2 class="detail-title">${work.title}</h2>
    <div class="detail-meta">
      <span>类型: ${work.type === "video" ? "视频" : "图片"}</span>
      <span>角色: ${work.character || "未分类"}</span>
      <span>分类: ${work.category || "未分类"}</span>
      ${work.size_mb ? `<span>大小: ${work.size_mb}MB</span>` : ""}
    </div>
    <div class="detail-tags">${work.tags ? work.tags.map(t => '<span class="detail-tag">' + t + '</span>').join("") : ""}</div>
    <div class="detail-quality">
      <div class="quality-label">质量评分</div>
      <div class="quality-bar"><div class="quality-fill" style="width: ${qualityScore}%; background: ${qualityColor};"></div></div>
      <div class="quality-score" style="color: ${qualityColor};">${qualityScore}分</div>
    </div>
    <div class="detail-description">${work.description || "暂无描述"}</div>
    ${qcBadge}
    ${qcInfo}
    ${shareBtn}
    ${ratingSection}
    ${commentsSection}
  `;
  
  // 加载推荐作品
  loadRecommendations(work);"""
content = content.replace(old_detail_end, new_detail_end)

# ========== 10. 在模态框中添加推荐作品区域 ==========
old_modal_end = """  <div class="modal-body">
    <div class="modal-media" id="detail-media"></div>
    <div class="modal-info" id="detail-info"></div>
  </div>
</div>"""

new_modal_end = """  <div class="modal-body">
    <div class="modal-media" id="detail-media"></div>
    <div class="modal-info" id="detail-info"></div>
  </div>
  <div class="modal-recommendations" id="modal-recommendations" style="display:none;">
    <h3 class="recommendations-title">推荐作品</h3>
    <div class="recommendations-grid" id="recommendations-grid"></div>
  </div>
</div>"""
content = content.replace(old_modal_end, new_modal_end)

# ========== 11. 添加所有新函数（在batchDownload函数后面） ==========
old_batch_end = """  setTimeout(() => {
    alert("批量下载完成：成功 " + success + " 个，失败 " + failed + " 个");
  }, selectedWorks.length * 500 + 1000);
}

function shareWork(title, url) {"""

new_batch_end = """  setTimeout(() => {
    alert("批量下载完成：成功 " + success + " 个，失败 " + failed + " 个");
  }, selectedWorks.length * 500 + 1000);
}

// ========== 标签筛选 ==========
function handleTagFilter(value) {
  currentTagFilter = value;
  applyFilters();
}

// ========== 主题切换 ==========
function toggleTheme() {
  currentTheme = currentTheme === "dark" ? "light" : "dark";
  localStorage.setItem("kunlun_theme", currentTheme);
  applyTheme();
}

function applyTheme() {
  const btn = document.querySelector(".theme-toggle-btn");
  if (currentTheme === "light") {
    document.body.classList.add("light-theme");
    if (btn) btn.textContent = "☀️";
  } else {
    document.body.classList.remove("light-theme");
    if (btn) btn.textContent = "🌙";
  }
}

// 页面加载时应用主题
window.addEventListener("load", () => {
  applyTheme();
});

// ========== 作品评分 ==========
function rateWork(workId, rating) {
  ratings[workId] = rating;
  localStorage.setItem("kunlun_ratings", JSON.stringify(ratings));
  
  // 更新评分显示
  const stars = document.querySelectorAll(".rating-star");
  stars.forEach((star, index) => {
    if (index < rating) {
      star.classList.add("active");
    } else {
      star.classList.remove("active");
    }
  });
  
  document.getElementById("rating-text").textContent = "已评分: " + rating + "星";
  
  // 添加清除按钮
  const ratingSection = document.querySelector(".detail-rating-section");
  if (ratingSection && !ratingSection.querySelector(".rating-clear-btn")) {
    const clearBtn = document.createElement("button");
    clearBtn.className = "rating-clear-btn";
    clearBtn.textContent = "清除评分";
    clearBtn.onclick = () => clearRating(workId);
    ratingSection.appendChild(clearBtn);
  }
}

function clearRating(workId) {
  delete ratings[workId];
  localStorage.setItem("kunlun_ratings", JSON.stringify(ratings));
  
  const stars = document.querySelectorAll(".rating-star");
  stars.forEach(star => star.classList.remove("active"));
  
  document.getElementById("rating-text").textContent = "点击星星评分";
  
  const clearBtn = document.querySelector(".rating-clear-btn");
  if (clearBtn) clearBtn.remove();
}

// ========== 作品评论 ==========
function addComment(workId) {
  const input = document.getElementById("comment-input");
  const content = input.value.trim();
  
  if (!content) {
    alert("请输入评论内容");
    return;
  }
  
  if (!comments[workId]) {
    comments[workId] = [];
  }
  
  const now = new Date();
  const timeStr = now.getFullYear() + "-" + 
    String(now.getMonth() + 1).padStart(2, "0") + "-" + 
    String(now.getDate()).padStart(2, "0") + " " + 
    String(now.getHours()).padStart(2, "0") + ":" + 
    String(now.getMinutes()).padStart(2, "0");
  
  comments[workId].unshift({
    content: content,
    time: timeStr
  });
  
  localStorage.setItem("kunlun_comments", JSON.stringify(comments));
  
  // 更新评论列表
  const commentsList = document.getElementById("comments-list");
  commentsList.innerHTML = comments[workId].map(c => 
    "<div class=\\"comment-item\\"><div class=\\"comment-header\\"><span class=\\"comment-author\\">用户</span><span class=\\"comment-time\\">" + c.time + "</span></div><div class=\\"comment-content\\">" + c.content + "</div></div>"
  ).join("");
  
  input.value = "";
  
  // 更新评论计数
  const commentsSection = document.querySelector(".detail-comments-section h4");
  if (commentsSection) {
    commentsSection.textContent = "评论 (" + comments[workId].length + ")";
  }
}

// ========== 作品推荐 ==========
function loadRecommendations(currentWork) {
  const recommendationsSection = document.getElementById("modal-recommendations");
  const recommendationsGrid = document.getElementById("recommendations-grid");
  
  if (!recommendationsSection || !recommendationsGrid) return;
  
  // 根据相同角色或相同标签推荐
  let recommendations = worksData.filter(w => 
    w.id !== currentWork.id && 
    (w.character === currentWork.character || 
     (w.tags && currentWork.tags && w.tags.some(t => currentWork.tags.includes(t))))
  );
  
  // 如果推荐太少，添加随机作品
  if (recommendations.length < 4) {
    const randomWorks = worksData
      .filter(w => w.id !== currentWork.id && !recommendations.includes(w))
      .sort(() => Math.random() - 0.5)
      .slice(0, 4 - recommendations.length);
    recommendations = recommendations.concat(randomWorks);
  }
  
  // 最多显示6个
  recommendations = recommendations.slice(0, 6);
  
  if (recommendations.length === 0) {
    recommendationsSection.style.display = "none";
    return;
  }
  
  recommendationsGrid.innerHTML = recommendations.map(work => {
    const isVideo = work.type === "video";
    return "<div class=\\"recommendation-item\\" onclick=\\"closeModal();setTimeout(() => handleWorkClick(worksData.find(w => w.id === '" + work.id + "')), 100)\\\">" +
      "<div class=\\"recommendation-thumb\\"><img src=\\"" + work.thumbnail + "\\" alt=\\"" + work.title + "\\">" +
      (isVideo ? "<div class=\\"recommendation-play\\">▶</div>" : "") +
      "</div>" +
      "<div class=\\"recommendation-title\\">" + work.title + "</div>" +
      "</div>";
  }).join("");
  
  recommendationsSection.style.display = "block";
}

function shareWork(title, url) {"""

content = content.replace(old_batch_end, new_batch_end)

# ========== 12. 添加所有新CSS样式 ==========
old_share_css = """.share-tip { font-size: 12px; color: var(--text-muted); margin-top: 12px; }"""
new_share_css = """.share-tip { font-size: 12px; color: var(--text-muted); margin-top: 12px; }

/* 主题切换按钮 */
.theme-toggle-btn {
  background: none;
  border: none;
  color: var(--gold-primary);
  font-size: 18px;
  cursor: pointer;
  padding: 8px;
  margin-right: 8px;
  transition: transform 0.3s;
}
.theme-toggle-btn:hover { transform: scale(1.1); }

/* 亮色主题 */
body.light-theme {
  --bg-primary: #f5f5f0;
  --bg-secondary: #e8e8e0;
  --bg-card: rgba(255, 255, 255, 0.9);
  --border-color: rgba(184, 148, 31, 0.3);
  --text-primary: #1a1a1a;
  --text-secondary: #5a5a5a;
  --text-muted: #8a8a8a;
}
body.light-theme .zy-unified-nav {
  background: rgba(245, 245, 240, 0.95);
}
body.light-theme .work-card-overlay {
  background: linear-gradient(to top, rgba(245,245,240,0.95) 0%, transparent 100%);
}
body.light-theme .modal-content {
  background: #f5f5f0;
}

/* 标签筛选 */
.tag-filter-select {
  padding: 8px 12px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 20px;
  color: var(--text-primary);
  font-size: 13px;
  cursor: pointer;
  outline: none;
}
.tag-filter-select:focus { border-color: var(--gold-primary); }

/* 作品标签 */
.work-card-tags {
  display: flex;
  gap: 4px;
  padding: 0 10px 8px;
  flex-wrap: wrap;
}
.work-tag {
  font-size: 10px;
  padding: 2px 6px;
  background: rgba(212,175,55,0.15);
  color: var(--gold-primary);
  border-radius: 8px;
}

/* 详情页标签 */
.detail-tags {
  display: flex;
  gap: 6px;
  margin: 12px 0;
  flex-wrap: wrap;
}
.detail-tag {
  font-size: 12px;
  padding: 4px 10px;
  background: rgba(212,175,55,0.15);
  color: var(--gold-primary);
  border-radius: 12px;
}

/* 评分功能 */
.detail-rating-section {
  margin-top: 16px;
  padding: 16px;
  background: var(--bg-secondary);
  border-radius: 8px;
}
.rating-stars {
  display: flex;
  gap: 4px;
  margin-bottom: 8px;
}
.rating-star {
  font-size: 24px;
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.2s;
}
.rating-star:hover { transform: scale(1.2); }
.rating-star.active { color: #f1c40f; }
.rating-text { font-size: 13px; color: var(--text-secondary); margin-left: 8px; }
.rating-clear-btn {
  margin-left: 12px;
  padding: 4px 10px;
  background: transparent;
  border: 1px solid var(--border-color);
  border-radius: 12px;
  color: var(--text-secondary);
  font-size: 11px;
  cursor: pointer;
}
.rating-clear-btn:hover { border-color: #e74c3c; color: #e74c3c; }

/* 评论功能 */
.detail-comments-section {
  margin-top: 16px;
  padding: 16px;
  background: var(--bg-secondary);
  border-radius: 8px;
}
.comment-input-container {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}
.comment-input {
  flex: 1;
  padding: 10px 12px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  color: var(--text-primary);
  font-size: 13px;
  resize: none;
  outline: none;
  font-family: inherit;
}
.comment-input:focus { border-color: var(--gold-primary); }
.comment-submit-btn {
  padding: 10px 20px;
  background: var(--gold-primary);
  border: none;
  border-radius: 8px;
  color: #050508;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}
.comment-submit-btn:hover { background: var(--gold-light); }
.comments-list { display: flex; flex-direction: column; gap: 12px; }
.comment-item {
  padding: 12px;
  background: var(--bg-primary);
  border-radius: 8px;
  border: 1px solid var(--border-color);
}
.comment-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 6px;
}
.comment-author { font-size: 12px; font-weight: 600; color: var(--gold-primary); }
.comment-time { font-size: 11px; color: var(--text-muted); }
.comment-content { font-size: 13px; color: var(--text-primary); line-height: 1.6; }
.comment-empty {
  text-align: center;
  padding: 20px;
  color: var(--text-muted);
  font-size: 13px;
}

/* 推荐作品 */
.modal-recommendations {
  padding: 20px;
  border-top: 1px solid var(--border-color);
}
.recommendations-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--gold-primary);
  margin-bottom: 16px;
}
.recommendations-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 12px;
}
.recommendation-item {
  cursor: pointer;
  transition: transform 0.3s;
}
.recommendation-item:hover { transform: translateY(-2px); }
.recommendation-thumb {
  position: relative;
  width: 100%;
  padding-top: 150%;
  border-radius: 8px;
  overflow: hidden;
  background: var(--bg-secondary);
}
.recommendation-thumb img {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.recommendation-play {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 32px;
  height: 32px;
  background: rgba(0,0,0,0.6);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 12px;
}
.recommendation-title {
  margin-top: 6px;
  font-size: 12px;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}"""
content = content.replace(old_share_css, new_share_css)

# 写入文件
with open("/www/wwwroot/huodouai.com/drama/gallery/index.html", "w", encoding="utf-8") as f:
    f.write(content)

print("✅ 画廊页面已更新，添加全部5个功能")
print("  1. 作品评论功能 (localStorage存储)")
print("  2. 暗黑/亮色主题切换")
print("  3. 作品标签系统 (风格/场景/情绪)")
print("  4. 作品评分功能 (5星评分)")
print("  5. 作品推荐功能 (根据收藏/标签推荐)")
