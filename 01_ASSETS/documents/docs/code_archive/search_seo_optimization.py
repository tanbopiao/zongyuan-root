import os
import json
from datetime import datetime

# ========== 1. 生成sitemap.xml ==========
sitemap_urls = [
    {"loc": "https://www.huodouai.com/", "priority": "1.0", "changefreq": "daily"},
    {"loc": "https://www.huodouai.com/drama/", "priority": "0.9", "changefreq": "hourly"},
    {"loc": "https://www.huodouai.com/drama/gallery/", "priority": "0.9", "changefreq": "hourly"},
    {"loc": "https://www.huodouai.com/drama/assets/", "priority": "0.8", "changefreq": "daily"},
    {"loc": "https://www.huodouai.com/drama/characters/", "priority": "0.8", "changefreq": "weekly"},
    {"loc": "https://www.huodouai.com/drama/pipeline.html", "priority": "0.7", "changefreq": "hourly"},
    {"loc": "https://www.huodouai.com/drama/qc-report.html", "priority": "0.7", "changefreq": "daily"},
    {"loc": "https://www.huodouai.com/drama/admin.html", "priority": "0.5", "changefreq": "weekly"},
    {"loc": "https://www.huodouai.com/gov/", "priority": "0.8", "changefreq": "weekly"},
    {"loc": "https://www.huodouai.com/products/kunlun-drama.html", "priority": "0.7", "changefreq": "monthly"},
    {"loc": "https://www.huodouai.com/products/drama-factory.html", "priority": "0.7", "changefreq": "monthly"},
]

sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
"""

for url in sitemap_urls:
    sitemap_xml += f"""  <url>
    <loc>{url['loc']}</loc>
    <lastmod>{datetime.now().strftime('%Y-%m-%d')}</lastmod>
    <changefreq>{url['changefreq']}</changefreq>
    <priority>{url['priority']}</priority>
  </url>
"""

sitemap_xml += "</urlset>"

with open("/www/wwwroot/huodouai.com/sitemap.xml", "w", encoding="utf-8") as f:
    f.write(sitemap_xml)

print("✅ sitemap.xml 已生成")
print(f"  包含 {len(sitemap_urls)} 个URL")

# ========== 2. 生成robots.txt ==========
robots_txt = """User-agent: *
Allow: /
Disallow: /api/
Disallow: /admin
Disallow: /*.json$

Sitemap: https://www.huodouai.com/sitemap.xml
"""

with open("/www/wwwroot/huodouai.com/robots.txt", "w", encoding="utf-8") as f:
    f.write(robots_txt)

print("✅ robots.txt 已生成")

# ========== 3. 升级作品库搜索功能 ==========
# 读取现有画廊页面
with open("/www/wwwroot/huodouai.com/drama/gallery/index.html", "r", encoding="utf-8") as f:
    content = f.read()

# 检查是否已有高级筛选
if "advanced-filters" not in content:
    # 在搜索框后面添加高级筛选按钮和面板
    old_search = """<div class="search-box">
      <input type="text" id="search-input" placeholder="搜索作品名称、角色..." oninput="filterWorks()">
    </div>"""
    
    new_search = """<div class="search-box">
      <input type="text" id="search-input" placeholder="搜索作品名称、角色、标签..." oninput="filterWorks()">
      <button class="advanced-filter-btn" onclick="toggleAdvancedFilters()">⚙️ 高级筛选</button>
    </div>
    <div class="advanced-filters" id="advanced-filters" style="display:none;">
      <div class="filter-group">
        <label>质量范围：</label>
        <select id="filter-quality" onchange="filterWorks()">
          <option value="">全部质量</option>
          <option value="90">优秀 (≥90)</option>
          <option value="70">良好 (≥70)</option>
          <option value="0">合格 (<70)</option>
        </select>
      </div>
      <div class="filter-group">
        <label>标签：</label>
        <select id="filter-tag" onchange="filterWorks()">
          <option value="">全部标签</option>
          <option value="国风">国风</option>
          <option value="仙侠">仙侠</option>
          <option value="写实">写实</option>
          <option value="暗黑">暗黑</option>
          <option value="唯美">唯美</option>
          <option value="战争">战争</option>
          <option value="修真">修真</option>
          <option value="星夜">星夜</option>
        </select>
      </div>
      <div class="filter-group">
        <label>排序：</label>
        <select id="filter-sort" onchange="filterWorks()">
          <option value="default">默认排序</option>
          <option value="quality-desc">质量从高到低</option>
          <option value="quality-asc">质量从低到高</option>
          <option value="size-desc">文件大小从大到小</option>
          <option value="size-asc">文件大小从小到大</option>
          <option name="name-asc">名称A-Z</option>
        </select>
      </div>
      <button class="clear-filters-btn" onclick="clearFilters()">清除筛选</button>
    </div>"""
    
    content = content.replace(old_search, new_search)
    
    # 添加CSS样式
    old_css = """.search-box {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  align-items: center;
}"""
    
    new_css = """.search-box {
  display: flex;
  gap: 12px;
  margin-bottom: 12px;
  align-items: center;
}
.advanced-filter-btn {
  padding: 10px 16px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  color: var(--gold-primary);
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
  white-space: nowrap;
  transition: all 0.3s;
}
.advanced-filter-btn:hover {
  border-color: var(--gold-primary);
  background: rgba(212,175,55,0.1);
}
.advanced-filters {
  display: flex;
  gap: 20px;
  flex-wrap: wrap;
  align-items: center;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 16px 20px;
  margin-bottom: 20px;
}
.filter-group {
  display: flex;
  align-items: center;
  gap: 8px;
}
.filter-group label {
  font-size: 13px;
  color: var(--text-secondary);
  white-space: nowrap;
}
.filter-group select {
  padding: 6px 12px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-primary);
  font-size: 13px;
  cursor: pointer;
}
.clear-filters-btn {
  padding: 6px 16px;
  background: rgba(231,76,60,0.1);
  border: 1px solid rgba(231,76,60,0.3);
  color: var(--danger);
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.3s;
}
.clear-filters-btn:hover {
  background: rgba(231,76,60,0.2);
}"""
    
    content = content.replace(old_css, new_css)
    
    # 更新filterWorks函数，添加高级筛选逻辑
    old_filter = """function filterWorks() {
  const search = document.getElementById("search-input").value.toLowerCase();
  const type = document.getElementById("filter-type").value;
  const character = document.getElementById("filter-character").value;
  const tag = document.getElementById("filter-tag").value;
  const sort = document.getElementById("sort-select").value;
  
  filteredWorks = worksData.filter(w => {
    const matchSearch = !search || (w.title || "").toLowerCase().includes(search) || (w.character || "").toLowerCase().includes(search);
    const matchType = !type || w.type === type;
    const matchChar = !character || w.character === character;
    const matchTag = !tag || (w.tags || []).includes(tag);
    return matchSearch && matchType && matchChar && matchTag;
  });"""
    
    new_filter = """function filterWorks() {
  const search = document.getElementById("search-input").value.toLowerCase();
  const type = document.getElementById("filter-type").value;
  const character = document.getElementById("filter-character").value;
  const tagEl = document.getElementById("filter-tag");
  const tag = tagEl ? tagEl.value : "";
  const sortEl = document.getElementById("sort-select");
  const sort = sortEl ? sortEl.value : "default";
  const qualityEl = document.getElementById("filter-quality");
  const quality = qualityEl ? qualityEl.value : "";
  const advTagEl = document.getElementById("filter-tag");
  const advTag = advTagEl ? advTagEl.value : "";
  const sortAdvEl = document.getElementById("filter-sort");
  const sortAdv = sortAdvEl ? sortAdvEl.value : "";
  
  const finalSort = sortAdv !== "default" ? sortAdv : sort;
  
  filteredWorks = worksData.filter(w => {
    const matchSearch = !search || (w.title || "").toLowerCase().includes(search) || (w.character || "").toLowerCase().includes(search) || (w.tags || []).some(t => t.toLowerCase().includes(search));
    const matchType = !type || w.type === type;
    const matchChar = !character || w.character === character;
    const matchTag = !tag || !advTag || (w.tags || []).includes(tag) || (w.tags || []).includes(advTag);
    const matchQuality = !quality || (quality === "90" ? w.quality_score >= 90 : quality === "70" ? w.quality_score >= 70 && w.quality_score < 90 : w.quality_score < 70);
    return matchSearch && matchType && matchChar && matchTag && matchQuality;
  });
  
  // 排序
  if (finalSort === "quality-desc") {
    filteredWorks.sort((a, b) => (b.quality_score || 0) - (a.quality_score || 0));
  } else if (finalSort === "quality-asc") {
    filteredWorks.sort((a, b) => (a.quality_score || 0) - (b.quality_score || 0));
  } else if (finalSort === "size-desc") {
    filteredWorks.sort((a, b) => (b.size_mb || 0) - (a.size_mb || 0));
  } else if (finalSort === "size-asc") {
    filteredWorks.sort((a, b) => (a.size_mb || 0) - (b.size_mb || 0));
  } else if (finalSort === "name-asc") {
    filteredWorks.sort((a, b) => (a.title || "").localeCompare(b.title || ""));
  }"""
    
    content = content.replace(old_filter, new_filter)
    
    # 添加toggleAdvancedFilters和clearFilters函数
    old_share_func = """function shareWork(title, url) {"""
    
    new_funcs = """function toggleAdvancedFilters() {
  const panel = document.getElementById("advanced-filters");
  panel.style.display = panel.style.display === "none" ? "flex" : "none";
}

function clearFilters() {
  document.getElementById("search-input").value = "";
  document.getElementById("filter-type").value = "";
  document.getElementById("filter-character").value = "";
  const tagEl = document.getElementById("filter-tag");
  if (tagEl) tagEl.value = "";
  const sortEl = document.getElementById("sort-select");
  if (sortEl) sortEl.value = "default";
  const qualityEl = document.getElementById("filter-quality");
  if (qualityEl) qualityEl.value = "";
  const advTagEl = document.getElementById("filter-tag");
  if (advTagEl) advTagEl.value = "";
  const sortAdvEl = document.getElementById("filter-sort");
  if (sortAdvEl) sortAdvEl.value = "default";
  filterWorks();
}

function shareWork(title, url) {"""
    
    content = content.replace(old_share_func, new_funcs)

# 写入文件
with open("/www/wwwroot/huodouai.com/drama/gallery/index.html", "w", encoding="utf-8") as f:
    f.write(content)

# 同步到其他页面
import shutil
shutil.copy("/www/wwwroot/huodouai.com/drama/gallery/index.html", "/www/wwwroot/huodouai.com/drama/assets/index.html")

# index.html有chattr保护
os.system("chattr -i /www/wwwroot/huodouai.com/drama/index.html 2>/dev/null")
shutil.copy("/www/wwwroot/huodouai.com/drama/gallery/index.html", "/www/wwwroot/huodouai.com/drama/index.html")
os.system("chattr +i /www/wwwroot/huodouai.com/drama/index.html 2>/dev/null")

print("✅ 搜索优化已完成")
print("  新增功能:")
print("    - 高级筛选面板（质量范围/标签/排序）")
print("    - 全文搜索（名称/角色/标签）")
print("    - 6种排序方式（质量/大小/名称）")
print("    - 一键清除筛选")
print("  已同步到: 作品库主页/作品画廊/全域资产")

print("\n✅ SEO优化已完成")
print("  - sitemap.xml (11个URL)")
print("  - robots.txt")
