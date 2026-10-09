import os

# 读取现有画廊页面
with open("/www/wwwroot/huodouai.com/drama/gallery/index.html", "r", encoding="utf-8") as f:
    content = f.read()

# 1. 添加无限滚动相关的全局变量
old_vars = "let currentFilter = \"all\";\nlet currentSearch = \"\";\nlet currentSort = \"default\";"
new_vars = "let currentFilter = \"all\";\nlet currentSearch = \"\";\nlet currentSort = \"default\";\nlet displayedCount = 0;\nconst PAGE_SIZE = 24;\nlet isLoading = false;"
content = content.replace(old_vars, new_vars)

# 2. 修改renderFilteredWorks函数，支持分页
old_render = """function renderFilteredWorks(works) {
  const grid = document.getElementById("works-grid");
  grid.innerHTML = "";
  if (works.length === 0) {
    grid.innerHTML = "<div style=\\"grid-column:1/-1;text-align:center;padding:60px;color:var(--text-muted);\\">未找到匹配的作品</div>";
    return;
  }
  works.forEach((work, index) => {
    const card = createWorkCard(work);
    card.style.animationDelay = (index * 0.05) + "s";
    grid.appendChild(card);
  });
}"""

new_render = """function renderFilteredWorks(works) {
  const grid = document.getElementById("works-grid");
  grid.innerHTML = "";
  displayedCount = 0;
  
  if (works.length === 0) {
    grid.innerHTML = "<div style=\\"grid-column:1/-1;text-align:center;padding:60px;color:var(--text-muted);\\">未找到匹配的作品</div>";
    return;
  }
  
  // 显示第一页
  loadMoreWorks(works);
  
  // 显示加载更多按钮
  const loadMoreContainer = document.getElementById("load-more-container");
  if (loadMoreContainer) {
    if (works.length > PAGE_SIZE) {
      loadMoreContainer.style.display = "block";
      document.getElementById("load-more-btn").textContent = "加载更多 (" + (works.length - PAGE_SIZE) + "个作品)";
    } else {
      loadMoreContainer.style.display = "none";
    }
  }
}

function loadMoreWorks(works) {
  if (isLoading) return;
  isLoading = true;
  
  const grid = document.getElementById("works-grid");
  const nextCount = Math.min(displayedCount + PAGE_SIZE, works.length);
  
  for (let i = displayedCount; i < nextCount; i++) {
    const work = works[i];
    const card = createWorkCard(work);
    card.style.animationDelay = ((i % PAGE_SIZE) * 0.03) + "s";
    grid.appendChild(card);
  }
  
  displayedCount = nextCount;
  isLoading = false;
  
  // 更新加载更多按钮
  const loadMoreContainer = document.getElementById("load-more-container");
  if (loadMoreContainer) {
    const remaining = works.length - displayedCount;
    if (remaining > 0) {
      loadMoreContainer.style.display = "block";
      document.getElementById("load-more-btn").textContent = "加载更多 (" + remaining + "个作品)";
    } else {
      loadMoreContainer.style.display = "none";
    }
  }
}

// 无限滚动
window.addEventListener("scroll", () => {
  if (isLoading) return;
  
  const scrollPosition = window.innerHeight + window.scrollY;
  const pageHeight = document.documentElement.scrollHeight;
  
  // 当滚动到距离底部200px时自动加载更多
  if (scrollPosition >= pageHeight - 200) {
    const filtered = getFilteredWorks();
    if (displayedCount < filtered.length) {
      loadMoreWorks(filtered);
    }
  }
});

function getFilteredWorks() {
  let filtered = [...worksData];
  
  if (currentFilter !== "all") {
    if (currentFilter === "video") {
      filtered = filtered.filter(w => w.type === "video");
    } else if (currentFilter === "image") {
      filtered = filtered.filter(w => w.type === "image");
    } else {
      filtered = filtered.filter(w => w.character === currentFilter);
    }
  }
  
  if (currentSearch) {
    filtered = filtered.filter(w => 
      w.title.toLowerCase().includes(currentSearch) ||
      (w.character && w.character.toLowerCase().includes(currentSearch)) ||
      (w.category && w.category.toLowerCase().includes(currentSearch))
    );
  }
  
  switch (currentSort) {
    case "quality-desc":
      filtered.sort((a, b) => (b.quality_score || 0) - (a.quality_score || 0));
      break;
    case "quality-asc":
      filtered.sort((a, b) => (a.quality_score || 0) - (b.quality_score || 0));
      break;
    case "name-asc":
      filtered.sort((a, b) => a.title.localeCompare(b.title, "zh-CN"));
      break;
    case "name-desc":
      filtered.sort((a, b) => b.title.localeCompare(a.title, "zh-CN"));
      break;
    case "video-first":
      filtered.sort((a, b) => (b.type === "video" ? 1 : 0) - (a.type === "video" ? 1 : 0));
      break;
    case "image-first":
      filtered.sort((a, b) => (b.type === "image" ? 1 : 0) - (a.type === "image" ? 1 : 0));
      break;
  }
  
  return filtered;
}"""

content = content.replace(old_render, new_render)

# 3. 简化applyFilters函数（使用getFilteredWorks）
old_apply = """function applyFilters() {
  let filtered = [...worksData];
  
  // 分类筛选
  if (currentFilter !== "all") {
    if (currentFilter === "video") {
      filtered = filtered.filter(w => w.type === "video");
    } else if (currentFilter === "image") {
      filtered = filtered.filter(w => w.type === "image");
    } else {
      filtered = filtered.filter(w => w.character === currentFilter);
    }
  }
  
  // 搜索筛选
  if (currentSearch) {
    filtered = filtered.filter(w => 
      w.title.toLowerCase().includes(currentSearch) ||
      (w.character && w.character.toLowerCase().includes(currentSearch)) ||
      (w.category && w.category.toLowerCase().includes(currentSearch))
    );
  }
  
  // 排序
  switch (currentSort) {
    case "quality-desc":
      filtered.sort((a, b) => (b.quality_score || 0) - (a.quality_score || 0));
      break;
    case "quality-asc":
      filtered.sort((a, b) => (a.quality_score || 0) - (b.quality_score || 0));
      break;
    case "name-asc":
      filtered.sort((a, b) => a.title.localeCompare(b.title, "zh-CN"));
      break;
    case "name-desc":
      filtered.sort((a, b) => b.title.localeCompare(a.title, "zh-CN"));
      break;
    case "video-first":
      filtered.sort((a, b) => (b.type === "video" ? 1 : 0) - (a.type === "video" ? 1 : 0));
      break;
    case "image-first":
      filtered.sort((a, b) => (b.type === "image" ? 1 : 0) - (a.type === "image" ? 1 : 0));
      break;
  }
  
  renderFilteredWorks(filtered);
}"""

new_apply = """function applyFilters() {
  const filtered = getFilteredWorks();
  renderFilteredWorks(filtered);
}"""

content = content.replace(old_apply, new_apply)

# 4. 在works-grid后面添加加载更多按钮
old_grid_end = "</div>\n  </div>\n</section>"
new_grid_end = """</div>
  <div id="load-more-container" style="text-align:center;margin-top:30px;display:none;">
    <button id="load-more-btn" onclick="loadMoreWorks(getFilteredWorks())" style="padding:12px 32px;background:var(--bg-card);border:1px solid var(--border-color);border-radius:24px;color:var(--gold-primary);font-size:14px;cursor:pointer;transition:all 0.3s;">加载更多</button>
  </div>
  </div>
</section>"""

content = content.replace(old_grid_end, new_grid_end)

# 写入文件
with open("/www/wwwroot/huodouai.com/drama/gallery/index.html", "w", encoding="utf-8") as f:
    f.write(content)

print("✅ 画廊页面已更新，添加无限滚动功能")
print("  每页显示:", "24个作品")
print("  自动加载:", "滚动到底部200px时自动加载")
print("  手动加载:", "加载更多按钮")
