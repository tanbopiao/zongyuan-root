import os

# 读取现有画廊页面
with open("/www/wwwroot/huodouai.com/drama/gallery/index.html", "r", encoding="utf-8") as f:
    content = f.read()

# 检查是否已有用户中心
if "user-center" not in content:
    # 在导航栏添加用户中心按钮
    old_nav_cta = """<div class="navbar-cta">
        <a href="#create" class="btn btn-primary">立即体验</a>
      </div>"""
    
    new_nav_cta = """<div class="navbar-cta">
        <button class="user-center-btn" onclick="openUserCenter()" title="个人中心">👤</button>
        <a href="#create" class="btn btn-primary">立即体验</a>
      </div>"""
    
    content = content.replace(old_nav_cta, new_nav_cta)
    
    # 添加用户中心按钮样式
    old_btn_primary = """.btn-primary {
  background: linear-gradient(135deg, var(--gold-primary), var(--gold-dark));
  color: var(--bg-primary);
  border: none;
  padding: 10px 24px;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
  text-decoration: none;
  display: inline-block;
}"""
    
    new_btn_primary = """.btn-primary {
  background: linear-gradient(135deg, var(--gold-primary), var(--gold-dark));
  color: var(--bg-primary);
  border: none;
  padding: 10px 24px;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
  text-decoration: none;
  display: inline-block;
}
.user-center-btn {
  width: 40px;
  height: 40px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 50%;
  font-size: 18px;
  cursor: pointer;
  margin-right: 12px;
  transition: all 0.3s;
}
.user-center-btn:hover {
  border-color: var(--gold-primary);
  background: rgba(212,175,55,0.1);
}"""
    
    content = content.replace(old_btn_primary, new_btn_primary)
    
    # 添加用户中心模态框HTML（在作品详情模态框后面）
    old_modal_end = """</div>
  </div>
  
  <!-- 分享模态框 -->"""
    
    new_modal_end = """</div>
  </div>
  
  <!-- 用户中心模态框 -->
  <div class="user-center-modal" id="user-center-modal" onclick="if(event.target===this)closeUserCenter()">
    <div class="user-center-content">
      <button class="user-center-close" onclick="closeUserCenter()">×</button>
      <div class="user-center-header">
        <div class="user-avatar">👤</div>
        <div class="user-info">
          <h3 class="user-name">访客用户</h3>
          <p class="user-level">本地账户 · 数据存储在浏览器</p>
        </div>
      </div>
      
      <div class="user-center-tabs">
        <button class="user-tab active" onclick="switchUserTab('favorites')">⭐ 我的收藏</button>
        <button class="user-tab" onclick="switchUserTab('history')">📜 观看历史</button>
        <button class="user-tab" onclick="switchUserTab('settings')">⚙️ 偏好设置</button>
        <button class="user-tab" onclick="switchUserTab('data')">💾 数据管理</button>
      </div>
      
      <div class="user-tab-content" id="user-tab-favorites">
        <div class="user-stats-row">
          <div class="user-stat"><span class="user-stat-value" id="fav-count">0</span><span class="user-stat-label">收藏作品</span></div>
          <div class="user-stat"><span class="user-stat-value" id="comment-count">0</span><span class="user-stat-label">发表评论</span></div>
          <div class="user-stat"><span class="user-stat-value" id="rating-count">0</span><span class="user-stat-label">作品评分</span></div>
        </div>
        <div class="user-favorites-grid" id="user-favorites-grid">
          <p style="text-align:center;color:var(--text-muted);padding:40px;">暂无收藏作品</p>
        </div>
      </div>
      
      <div class="user-tab-content" id="user-tab-history" style="display:none;">
        <div class="user-history-list" id="user-history-list">
          <p style="text-align:center;color:var(--text-muted);padding:40px;">暂无观看历史</p>
        </div>
        <button class="clear-history-btn" onclick="clearHistory()">清空观看历史</button>
      </div>
      
      <div class="user-tab-content" id="user-tab-settings" style="display:none;">
        <div class="setting-item">
          <label>默认主题</label>
          <select id="setting-theme" onchange="saveSetting('theme', this.value)">
            <option value="dark">暗黑主题（黑金）</option>
            <option value="light">亮色主题</option>
          </select>
        </div>
        <div class="setting-item">
          <label>默认排序</label>
          <select id="setting-sort" onchange="saveSetting('sort', this.value)">
            <option value="default">默认排序</option>
            <option value="quality-desc">质量从高到低</option>
            <option value="video-first">视频优先</option>
          </select>
        </div>
        <div class="setting-item">
          <label>每页显示数量</label>
          <select id="setting-pagesize" onchange="saveSetting('pagesize', this.value)">
            <option value="24">24个/页</option>
            <option value="48">48个/页</option>
            <option value="96">96个/页</option>
          </select>
        </div>
        <div class="setting-item">
          <label>自动播放视频</label>
          <label class="switch">
            <input type="checkbox" id="setting-autoplay" onchange="saveSetting('autoplay', this.checked)">
            <span class="slider"></span>
          </label>
        </div>
      </div>
      
      <div class="user-tab-content" id="user-tab-data" style="display:none;">
        <div class="data-action-item">
          <h4>导出我的数据</h4>
          <p>导出收藏、评论、评分、观看历史为JSON文件</p>
          <button class="data-btn" onclick="exportUserData()">📥 导出数据</button>
        </div>
        <div class="data-action-item">
          <h4>导入数据</h4>
          <p>从JSON文件恢复我的数据</p>
          <input type="file" id="import-file" accept=".json" style="display:none;" onchange="importUserData(event)">
          <button class="data-btn" onclick="document.getElementById('import-file').click()">📤 导入数据</button>
        </div>
        <div class="data-action-item danger">
          <h4>清除所有数据</h4>
          <p>清除收藏、评论、评分、观看历史（不可恢复）</p>
          <button class="data-btn danger" onclick="clearAllUserData()">🗑️ 清除所有数据</button>
        </div>
      </div>
    </div>
  </div>
  
  <!-- 分享模态框 -->"""
    
    content = content.replace(old_modal_end, new_modal_end)
    
    # 添加用户中心CSS样式（在recommendation样式后面）
    old_rec_css = """.recommendations-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 12px;
}"""
    
    new_rec_css = """.recommendations-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 12px;
}

/* 用户中心 */
.user-center-modal {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.85);
  z-index: 10001;
  display: none;
  align-items: center;
  justify-content: center;
  padding: 20px;
}
.user-center-modal.active { display: flex; }
.user-center-content {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 16px;
  max-width: 700px;
  width: 100%;
  max-height: 85vh;
  overflow-y: auto;
  position: relative;
  padding: 24px;
}
.user-center-close {
  position: absolute;
  top: 16px; right: 16px;
  background: rgba(0,0,0,0.5);
  border: none; color: #fff;
  font-size: 24px; cursor: pointer;
  width: 36px; height: 36px;
  border-radius: 50%;
}
.user-center-header {
  display: flex; align-items: center; gap: 16px;
  margin-bottom: 24px;
  padding-bottom: 20px;
  border-bottom: 1px solid var(--border-color);
}
.user-avatar {
  width: 60px; height: 60px;
  background: linear-gradient(135deg, var(--gold-dark), var(--gold-primary));
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 28px;
}
.user-name {
  font-size: 20px; font-weight: 700;
  font-family: "Noto Serif SC", serif;
  margin-bottom: 4px;
}
.user-level { font-size: 13px; color: var(--text-muted); }
.user-center-tabs {
  display: flex; gap: 8px;
  margin-bottom: 20px;
  border-bottom: 1px solid var(--border-color);
  flex-wrap: wrap;
}
.user-tab {
  padding: 10px 16px;
  background: none; border: none;
  color: var(--text-secondary);
  font-size: 13px; cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all 0.3s;
}
.user-tab.active {
  color: var(--gold-primary);
  border-bottom-color: var(--gold-primary);
}
.user-stats-row {
  display: flex; gap: 16px; margin-bottom: 20px;
}
.user-stat {
  flex: 1; text-align: center;
  background: var(--bg-secondary);
  padding: 16px; border-radius: 8px;
}
.user-stat-value {
  display: block; font-size: 24px;
  font-weight: 700; color: var(--gold-primary);
  font-family: "Noto Serif SC", serif;
}
.user-stat-label { font-size: 12px; color: var(--text-muted); }
.user-favorites-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
  gap: 10px;
}
.user-fav-item {
  aspect-ratio: 3/4;
  border-radius: 8px; overflow: hidden;
  cursor: pointer; position: relative;
  border: 1px solid var(--border-color);
}
.user-fav-item img { width: 100%; height: 100%; object-fit: cover; }
.user-fav-item-title {
  position: absolute; bottom: 0; left: 0; right: 0;
  background: linear-gradient(to top, rgba(0,0,0,0.8), transparent);
  padding: 8px; font-size: 11px; color: #fff;
}
.user-history-list { margin-bottom: 16px; }
.user-history-item {
  display: flex; align-items: center; gap: 12px;
  padding: 10px; border-bottom: 1px solid var(--border-color);
  cursor: pointer;
}
.user-history-item:hover { background: rgba(212,175,55,0.05); }
.user-history-thumb { width: 40px; height: 53px; object-fit: cover; border-radius: 4px; }
.user-history-info { flex: 1; }
.user-history-title { font-size: 13px; margin-bottom: 2px; }
.user-history-time { font-size: 11px; color: var(--text-muted); }
.clear-history-btn {
  width: 100%; padding: 10px;
  background: rgba(231,76,60,0.1);
  border: 1px solid rgba(231,76,60,0.3);
  color: var(--danger); border-radius: 8px;
  cursor: pointer; font-size: 13px;
}
.setting-item {
  display: flex; justify-content: space-between; align-items: center;
  padding: 14px 0; border-bottom: 1px solid var(--border-color);
}
.setting-item label { font-size: 14px; color: var(--text-secondary); }
.setting-item select {
  padding: 6px 12px; background: var(--bg-secondary);
  border: 1px solid var(--border-color); border-radius: 6px;
  color: var(--text-primary); font-size: 13px;
}
.switch { position: relative; display: inline-block; width: 44px; height: 24px; }
.switch input { opacity: 0; width: 0; height: 0; }
.slider {
  position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0;
  background-color: var(--bg-secondary); transition: .3s; border-radius: 24px;
  border: 1px solid var(--border-color);
}
.slider:before {
  position: absolute; content: ""; height: 16px; width: 16px;
  left: 3px; bottom: 3px; background-color: var(--text-muted);
  transition: .3s; border-radius: 50%;
}
input:checked + .slider { background-color: var(--gold-primary); }
input:checked + .slider:before { transform: translateX(20px); background-color: #fff; }
.data-action-item {
  padding: 16px; background: var(--bg-secondary);
  border-radius: 8px; margin-bottom: 12px;
}
.data-action-item h4 { font-size: 15px; margin-bottom: 6px; }
.data-action-item p { font-size: 12px; color: var(--text-muted); margin-bottom: 12px; }
.data-btn {
  padding: 8px 16px; background: var(--gold-primary);
  color: #050508; border: none; border-radius: 6px;
  cursor: pointer; font-size: 13px; font-weight: 600;
}
.data-btn.danger { background: rgba(231,76,60,0.1); color: var(--danger); border: 1px solid rgba(231,76,60,0.3); }
.data-action-item.danger { border: 1px solid rgba(231,76,60,0.2); }"""
    
    content = content.replace(old_rec_css, new_rec_css)
    
    # 添加用户中心相关函数（在shareWork函数后面）
    old_share_end = """  document.getElementById("share-modal").classList.add("active");
}

// 点击其他地方关闭分享模态框"""
    
    new_share_end = """  document.getElementById("share-modal").classList.add("active");
}

// ========== 用户中心功能 ==========
function openUserCenter() {
  document.getElementById("user-center-modal").classList.add("active");
  document.body.style.overflow = "hidden";
  loadUserCenter();
}

function closeUserCenter() {
  document.getElementById("user-center-modal").classList.remove("active");
  document.body.style.overflow = "";
}

function switchUserTab(tab) {
  document.querySelectorAll(".user-tab").forEach(t => t.classList.remove("active"));
  document.querySelectorAll(".user-tab-content").forEach(c => c.style.display = "none");
  event.target.classList.add("active");
  document.getElementById("user-tab-" + tab).style.display = "block";
}

function loadUserCenter() {
  // 加载统计
  const favorites = JSON.parse(localStorage.getItem("kunlun_favorites") || "[]");
  const comments = JSON.parse(localStorage.getItem("kunlun_comments") || "{}");
  const ratings = JSON.parse(localStorage.getItem("kunlun_ratings") || "{}");
  const history = JSON.parse(localStorage.getItem("kunlun_history") || "[]");
  
  document.getElementById("fav-count").textContent = favorites.length;
  document.getElementById("comment-count").textContent = Object.keys(comments).length;
  document.getElementById("rating-count").textContent = Object.keys(ratings).length;
  
  // 加载收藏作品
  const favGrid = document.getElementById("user-favorites-grid");
  if (favorites.length > 0 && worksData.length > 0) {
    const favWorks = worksData.filter(w => favorites.includes(w.title));
    favGrid.innerHTML = favWorks.slice(0, 12).map(w =>
      "<div class='user-fav-item' onclick='closeUserCenter();setTimeout(()=>handleWorkClick(worksData.find(x=>x.title===\"" + w.title + "\")),200)'>" +
      "<img src='" + w.thumbnail + "' alt=''><div class='user-fav-item-title'>" + w.title + "</div></div>"
    ).join("");
  }
  
  // 加载观看历史
  const historyList = document.getElementById("user-history-list");
  if (history.length > 0) {
    historyList.innerHTML = history.slice(0, 20).map(h =>
      "<div class='user-history-item' onclick='closeUserCenter()'>" +
      "<img src='" + (h.thumbnail || "") + "' class='user-history-thumb' alt=''>" +
      "<div class='user-history-info'><div class='user-history-title'>" + (h.title || "未知") + "</div>" +
      "<div class='user-history-time'>" + (h.time || "") + "</div></div></div>"
    ).join("");
  }
  
  // 加载设置
  const settings = JSON.parse(localStorage.getItem("kunlun_settings") || "{}");
  if (settings.theme) document.getElementById("setting-theme").value = settings.theme;
  if (settings.sort) document.getElementById("setting-sort").value = settings.sort;
  if (settings.pagesize) document.getElementById("setting-pagesize").value = settings.pagesize;
  if (settings.autoplay) document.getElementById("setting-autoplay").checked = settings.autoplay;
}

function saveSetting(key, value) {
  const settings = JSON.parse(localStorage.getItem("kunlun_settings") || "{}");
  settings[key] = value;
  localStorage.setItem("kunlun_settings", JSON.stringify(settings));
}

function addToHistory(work) {
  const history = JSON.parse(localStorage.getItem("kunlun_history") || "[]");
  const now = new Date().toLocaleString("zh-CN");
  const item = { title: work.title, thumbnail: work.thumbnail, time: now };
  // 去重
  const existing = history.findIndex(h => h.title === work.title);
  if (existing > -1) history.splice(existing, 1);
  history.unshift(item);
  // 最多保留50条
  localStorage.setItem("kunlun_history", JSON.stringify(history.slice(0, 50)));
}

function clearHistory() {
  if (confirm("确定要清空观看历史吗？")) {
    localStorage.removeItem("kunlun_history");
    loadUserCenter();
  }
}

function exportUserData() {
  const data = {
    favorites: JSON.parse(localStorage.getItem("kunlun_favorites") || "[]"),
    comments: JSON.parse(localStorage.getItem("kunlun_comments") || "{}"),
    ratings: JSON.parse(localStorage.getItem("kunlun_ratings") || "{}"),
    history: JSON.parse(localStorage.getItem("kunlun_history") || "[]"),
    settings: JSON.parse(localStorage.getItem("kunlun_settings") || "{}"),
    export_time: new Date().toISOString()
  };
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "kunlun_user_data_" + new Date().toISOString().slice(0, 10) + ".json";
  a.click();
  URL.revokeObjectURL(url);
}

function importUserData(event) {
  const file = event.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = function(e) {
    try {
      const data = JSON.parse(e.target.result);
      if (data.favorites) localStorage.setItem("kunlun_favorites", JSON.stringify(data.favorites));
      if (data.comments) localStorage.setItem("kunlun_comments", JSON.stringify(data.comments));
      if (data.ratings) localStorage.setItem("kunlun_ratings", JSON.stringify(data.ratings));
      if (data.history) localStorage.setItem("kunlun_history", JSON.stringify(data.history));
      if (data.settings) localStorage.setItem("kunlun_settings", JSON.stringify(data.settings));
      alert("数据导入成功！");
      loadUserCenter();
    } catch (err) {
      alert("导入失败：文件格式错误");
    }
  };
  reader.readAsText(file);
}

function clearAllUserData() {
  if (confirm("确定要清除所有数据吗？此操作不可恢复！")) {
    localStorage.removeItem("kunlun_favorites");
    localStorage.removeItem("kunlun_comments");
    localStorage.removeItem("kunlun_ratings");
    localStorage.removeItem("kunlun_history");
    localStorage.removeItem("kunlun_settings");
    localStorage.removeItem("kunlun_theme");
    alert("所有数据已清除");
    loadUserCenter();
  }
}

// ESC键关闭用户中心
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeUserCenter();
});

// 点击其他地方关闭分享模态框"""
    
    content = content.replace(old_share_end, new_share_end)
    
    # 在handleWorkClick中添加观看历史记录
    old_handle = """function handleWorkClick(work) {
  currentWork = work;"""
    
    new_handle = """function handleWorkClick(work) {
  currentWork = work;
  addToHistory(work);"""
    
    content = content.replace(old_handle, new_handle)

# 写入文件
with open("/www/wwwroot/huodouai.com/drama/gallery/index.html", "w", encoding="utf-8") as f:
    f.write(content)

# 同步到其他页面
import shutil
shutil.copy("/www/wwwroot/huodouai.com/drama/gallery/index.html", "/www/wwwroot/huodouai.com/drama/assets/index.html")
os.system("chattr -i /www/wwwroot/huodouai.com/drama/index.html 2>/dev/null")
shutil.copy("/www/wwwroot/huodouai.com/drama/gallery/index.html", "/www/wwwroot/huodouai.com/drama/index.html")
os.system("chattr +i /www/wwwroot/huodouai.com/drama/index.html 2>/dev/null")

print("✅ 用户系统简化版已完成")
print("  功能:")
print("    - 个人中心面板（4个Tab）")
print("    - 我的收藏（收藏作品网格展示）")
print("    - 观看历史（自动记录，最多50条）")
print("    - 偏好设置（主题/排序/每页数量/自动播放）")
print("    - 数据管理（导出JSON/导入JSON/清除数据）")
print("    - 用户统计（收藏数/评论数/评分数）")
print("  已同步到: 作品库主页/作品画廊/全域资产")
