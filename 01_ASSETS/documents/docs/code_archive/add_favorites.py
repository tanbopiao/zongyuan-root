import os

# 读取现有画廊页面
with open("/www/wwwroot/huodouai.com/drama/gallery/index.html", "r", encoding="utf-8") as f:
    content = f.read()

# 1. 添加收藏相关的全局变量
old_vars = "let displayedCount = 0;\nconst PAGE_SIZE = 24;\nlet isLoading = false;"
new_vars = "let displayedCount = 0;\nconst PAGE_SIZE = 24;\nlet isLoading = false;\nlet favorites = JSON.parse(localStorage.getItem(\"kunlun_favorites\") || \"[]\");"
content = content.replace(old_vars, new_vars)

# 2. 在筛选按钮中添加"我的收藏"
old_filter_btns = """    <button class="filter-btn" data-filter="女娲">女娲</button>
  </div>"""
new_filter_btns = """    <button class="filter-btn" data-filter="女娲">女娲</button>
    <button class="filter-btn" data-filter="favorites">⭐ 我的收藏</button>
  </div>"""
content = content.replace(old_filter_btns, new_filter_btns)

# 3. 更新getFilteredWorks函数，支持收藏筛选
old_filter_check = """  if (currentFilter !== "all") {
    if (currentFilter === "video") {
      filtered = filtered.filter(w => w.type === "video");
    } else if (currentFilter === "image") {
      filtered = filtered.filter(w => w.type === "image");
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
  }"""
content = content.replace(old_filter_check, new_filter_check)

# 4. 更新createWorkCard函数，添加收藏按钮
old_card_qc = """      <div class=\\\\"work-qc-badge\\\\">${qcBadge}</div>"""
new_card_qc = """      <div class=\\\\"work-qc-badge\\\\">${qcBadge}</div>
      <button class=\\\\"favorite-btn ${isFavorite ? 'active' : ''}\\\\" onclick=\\\\"event.stopPropagation();toggleFavorite('${work.id}')\\\\">${isFavorite ? '★' : '☆'}</button>"""
content = content.replace(old_card_qc, new_card_qc)

# 5. 在createWorkCard函数中添加isFavorite变量
old_is_video = """  const isVideo = work.type === "video";"""
new_is_video = """  const isVideo = work.type === "video";
  const isFavorite = favorites.includes(work.id);"""
content = content.replace(old_is_video, new_is_video)

# 6. 添加收藏相关的CSS样式（在qc-badge样式后面）
old_qc_css = """.qc-pending { background: rgba(149,165,166,0.8); color: #fff; }"""
new_qc_css = """.qc-pending { background: rgba(149,165,166,0.8); color: #fff; }
.favorite-btn {
  position: absolute;
  top: 8px;
  left: 8px;
  z-index: 2;
  background: rgba(0,0,0,0.5);
  border: none;
  color: #fff;
  font-size: 18px;
  cursor: pointer;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s;
  backdrop-filter: blur(4px);
}
.favorite-btn:hover { background: rgba(212,175,55,0.3); transform: scale(1.1); }
.favorite-btn.active { color: #f1c40f; background: rgba(241,196,15,0.2); }"""
content = content.replace(old_qc_css, new_qc_css)

# 7. 添加收藏切换函数（在handleSort函数后面）
old_handle_sort_end = """function handleSort(value) {
  currentSort = value;
  applyFilters();
}"""
new_handle_sort_end = """function handleSort(value) {
  currentSort = value;
  applyFilters();
}

function toggleFavorite(workId) {
  const index = favorites.indexOf(workId);
  if (index > -1) {
    favorites.splice(index, 1);
  } else {
    favorites.push(workId);
  }
  localStorage.setItem("kunlun_favorites", JSON.stringify(favorites));
  
  // 更新当前显示的卡片
  const cards = document.querySelectorAll(".work-card");
  cards.forEach(card => {
    const btn = card.querySelector(".favorite-btn");
    if (btn) {
      const isFav = favorites.includes(btn.getAttribute("onclick").match(/'([^']+)'/)[1]);
      btn.classList.toggle("active", isFav);
      btn.textContent = isFav ? "★" : "☆";
    }
  });
  
  // 如果当前在收藏筛选，重新渲染
  if (currentFilter === "favorites") {
    applyFilters();
  }
}"""
content = content.replace(old_handle_sort_end, new_handle_sort_end)

# 写入文件
with open("/www/wwwroot/huodouai.com/drama/gallery/index.html", "w", encoding="utf-8") as f:
    f.write(content)

print("✅ 画廊页面已更新，添加作品收藏功能")
print("  收藏存储: localStorage (kunlun_favorites)")
print("  收藏筛选: ⭐ 我的收藏 标签")
print("  收藏按钮: 卡片左上角 ☆/★")
