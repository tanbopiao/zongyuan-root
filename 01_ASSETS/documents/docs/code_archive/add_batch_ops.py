import os

# 读取现有画廊页面
with open("/www/wwwroot/huodouai.com/drama/gallery/index.html", "r", encoding="utf-8") as f:
    content = f.read()

# 1. 在对比状态栏中添加批量操作按钮
old_compare_bar_buttons = """  <div style="display:flex;gap:10px;">
    <button onclick="clearCompare()" style="padding:6px 16px;background:transparent;border:1px solid var(--border-color);border-radius:16px;color:var(--text-secondary);font-size:13px;cursor:pointer;">清空</button>
    <button id="start-compare-btn" onclick="startCompare()" disabled style="padding:6px 20px;background:var(--gold-primary);border:none;border-radius:16px;color:#050508;font-size:13px;font-weight:600;cursor:pointer;opacity:0.5;">开始对比</button>
    <button onclick="toggleCompareMode()" style="padding:6px 16px;background:transparent;border:1px solid var(--border-color);border-radius:16px;color:var(--text-secondary);font-size:13px;cursor:pointer;">退出</button>
  </div>"""

new_compare_bar_buttons = """  <div style="display:flex;gap:10px;flex-wrap:wrap;">
    <button onclick="batchFavorite()" style="padding:6px 16px;background:transparent;border:1px solid var(--gold-primary);border-radius:16px;color:var(--gold-primary);font-size:13px;cursor:pointer;">⭐ 批量收藏</button>
    <button onclick="batchDownload()" style="padding:6px 16px;background:transparent;border:1px solid var(--gold-primary);border-radius:16px;color:var(--gold-primary);font-size:13px;cursor:pointer;">⬇ 批量下载</button>
    <button onclick="clearCompare()" style="padding:6px 16px;background:transparent;border:1px solid var(--border-color);border-radius:16px;color:var(--text-secondary);font-size:13px;cursor:pointer;">清空</button>
    <button id="start-compare-btn" onclick="startCompare()" disabled style="padding:6px 20px;background:var(--gold-primary);border:none;border-radius:16px;color:#050508;font-size:13px;font-weight:600;cursor:pointer;opacity:0.5;">开始对比</button>
    <button onclick="toggleCompareMode()" style="padding:6px 16px;background:transparent;border:1px solid var(--border-color);border-radius:16px;color:var(--text-secondary);font-size:13px;cursor:pointer;">退出</button>
  </div>"""

content = content.replace(old_compare_bar_buttons, new_compare_bar_buttons)

# 2. 添加批量操作函数（在startCompare函数后面）
old_start_compare_end = """  media.innerHTML = compareHTML;
  info.innerHTML = "";
  modal.classList.add("active");
}

function shareWork(title, url) {"""

new_start_compare_end = """  media.innerHTML = compareHTML;
  info.innerHTML = "";
  modal.classList.add("active");
}

function batchFavorite() {
  if (selectedWorks.length === 0) {
    alert("请先选择作品");
    return;
  }
  
  let added = 0;
  selectedWorks.forEach(work => {
    if (!favorites.includes(work.id)) {
      favorites.push(work.id);
      added++;
    }
  });
  
  localStorage.setItem("kunlun_favorites", JSON.stringify(favorites));
  alert("已收藏 " + added + " 个作品（共选择 " + selectedWorks.length + " 个）");
  applyFilters();
}

function batchDownload() {
  if (selectedWorks.length === 0) {
    alert("请先选择作品");
    return;
  }
  
  if (selectedWorks.length > 5) {
    if (!confirm("您选择了 " + selectedWorks.length + " 个作品，批量下载可能需要较长时间，是否继续？")) {
      return;
    }
  }
  
  let success = 0;
  let failed = 0;
  
  selectedWorks.forEach((work, index) => {
    setTimeout(() => {
      const url = work.video_url || work.thumbnail;
      const filename = work.title + (work.type === "video" ? ".mp4" : ".jpg");
      
      // 使用fetch下载
      fetch(url)
        .then(response => response.blob())
        .then(blob => {
          const link = document.createElement("a");
          link.href = URL.createObjectURL(blob);
          link.download = filename;
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
          URL.revokeObjectURL(link.href);
          success++;
        })
        .catch(() => {
          // 如果fetch失败，尝试直接打开链接
          window.open(url, "_blank");
          failed++;
        });
    }, index * 500); // 每个下载间隔500ms，避免同时下载太多
  });
  
  setTimeout(() => {
    alert("批量下载完成：成功 " + success + " 个，失败 " + failed + " 个");
  }, selectedWorks.length * 500 + 1000);
}

function shareWork(title, url) {"""

content = content.replace(old_start_compare_end, new_start_compare_end)

# 写入文件
with open("/www/wwwroot/huodouai.com/drama/gallery/index.html", "w", encoding="utf-8") as f:
    f.write(content)

print("✅ 画廊页面已更新，添加作品批量操作功能")
print("  批量收藏: 一键收藏所有选中的作品")
print("  批量下载: 下载选中的作品（间隔500ms，避免同时下载太多）")
print("  下载限制: 超过5个会提示确认")
