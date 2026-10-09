import os

# 读取现有画廊页面
with open("/www/wwwroot/huodouai.com/drama/gallery/index.html", "r", encoding="utf-8") as f:
    content = f.read()

# 1. 在详情页的质检信息后面添加分享按钮
old_detail_qc_end = """    (qcResult ? "<div class=\\"detail-qc-info\\"><h4 style=\\"color:var(--gold-primary);margin-bottom:8px;\\">质检详情</h4>" +
      "<p>检测时间: " + (qcResult.checked_at || "未知") + "</p>" +
      "<p>多手问题: " + (qcResult.has_multi_hand ? "❌ 存在" : "✅ 无") + "</p>" +
      "<p>肢体畸形: " + (qcResult.has_deformity ? "❌ 存在" : "✅ 无") + "</p>" +
      (qcResult.issues && qcResult.issues.length > 0 ? "<p>问题列表: " + qcResult.issues.join(", ") + "</p>" : "") +
      "</div>" : "<div class=\\"detail-qc-info\\"><p style=\\"color:var(--text-muted);\\">该作品尚未经过自动质检</p></div>");"""

new_detail_qc_end = """    (qcResult ? "<div class=\\"detail-qc-info\\"><h4 style=\\"color:var(--gold-primary);margin-bottom:8px;\\">质检详情</h4>" +
      "<p>检测时间: " + (qcResult.checked_at || "未知") + "</p>" +
      "<p>多手问题: " + (qcResult.has_multi_hand ? "❌ 存在" : "✅ 无") + "</p>" +
      "<p>肢体畸形: " + (qcResult.has_deformity ? "❌ 存在" : "✅ 无") + "</p>" +
      (qcResult.issues && qcResult.issues.length > 0 ? "<p>问题列表: " + qcResult.issues.join(", ") + "</p>" : "") +
      "</div>" : "<div class=\\"detail-qc-info\\"><p style=\\"color:var(--text-muted);\\">该作品尚未经过自动质检</p></div>") +
    "<div class=\\"detail-actions\\"><button class=\\"detail-action-btn\\" onclick=\\"shareWork('" + work.title.replace(/'/g, "\\\\'") + "', '" + (work.video_url || work.thumbnail) + "')\\">🔗 分享作品</button></div>";"""

content = content.replace(old_detail_qc_end, new_detail_qc_end)

# 2. 添加分享相关的CSS样式（在detail-qc-info样式后面）
old_detail_qc_css = """.detail-qc-info { margin-top: 16px; padding: 16px; background: var(--bg-secondary); border-radius: 8px; font-size: 13px; color: var(--text-secondary); line-height: 1.8; }"""
new_detail_qc_css = """.detail-qc-info { margin-top: 16px; padding: 16px; background: var(--bg-secondary); border-radius: 8px; font-size: 13px; color: var(--text-secondary); line-height: 1.8; }
.detail-actions { margin-top: 16px; display: flex; gap: 10px; }
.detail-action-btn { padding: 10px 20px; background: var(--gold-primary); border: none; border-radius: 20px; color: #050508; font-size: 14px; font-weight: 600; cursor: pointer; transition: all 0.3s; }
.detail-action-btn:hover { background: var(--gold-light); transform: translateY(-1px); }
.share-modal { max-width: 480px !important; width: 90vw !important; }
.share-content { padding: 30px; text-align: center; }
.share-title { font-size: 22px; font-weight: 700; color: var(--gold-primary); margin-bottom: 20px; }
.share-qr { width: 180px; height: 180px; margin: 0 auto 20px; background: #fff; padding: 10px; border-radius: 8px; }
.share-qr img { width: 100%; height: 100%; }
.share-link-container { display: flex; gap: 8px; margin-bottom: 16px; }
.share-link-input { flex: 1; padding: 10px 14px; background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: 8px; color: var(--text-primary); font-size: 12px; outline: none; }
.share-copy-btn { padding: 10px 16px; background: var(--gold-primary); border: none; border-radius: 8px; color: #050508; font-size: 13px; font-weight: 600; cursor: pointer; white-space: nowrap; }
.share-copy-btn:hover { background: var(--gold-light); }
.share-copy-btn.copied { background: #27ae60; color: #fff; }
.share-tip { font-size: 12px; color: var(--text-muted); margin-top: 12px; }"""
content = content.replace(old_detail_qc_css, new_detail_qc_css)

# 3. 添加分享相关的函数（在startCompare函数后面）
old_start_compare_end = """  media.innerHTML = compareHTML;
  info.innerHTML = "";
  modal.classList.add("active");
}"""

new_start_compare_end = """  media.innerHTML = compareHTML;
  info.innerHTML = "";
  modal.classList.add("active");
}

function shareWork(title, url) {
  const modal = document.getElementById("video-modal");
  const media = document.getElementById("detail-media");
  const info = document.getElementById("detail-info");
  
  modal.querySelector(".modal-content").classList.add("share-modal");
  
  const fullUrl = "https://www.huodouai.com/drama/gallery/?work=" + encodeURIComponent(title);
  const qrUrl = "https://api.qrserver.com/v1/create-qr-code/?size=160x160&data=" + encodeURIComponent(fullUrl);
  
  media.innerHTML = '<div class="share-content">' +
    '<div class="share-title">分享作品</div>' +
    '<div class="share-qr"><img src="' + qrUrl + '" alt="分享二维码"></div>' +
    '<div class="share-link-container">' +
    '<input type="text" class="share-link-input" id="share-link-input" value="' + fullUrl + '" readonly>' +
    '<button class="share-copy-btn" id="share-copy-btn" onclick="copyShareLink()">复制链接</button>' +
    '</div>' +
    '<div class="share-tip">扫描二维码或复制链接分享给朋友</div>' +
    '</div>';
  info.innerHTML = "";
  modal.classList.add("active");
}

function copyShareLink() {
  const input = document.getElementById("share-link-input");
  const btn = document.getElementById("share-copy-btn");
  
  input.select();
  input.setSelectionRange(0, 99999);
  
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(input.value).then(() => {
      btn.textContent = "已复制 ✓";
      btn.classList.add("copied");
      setTimeout(() => {
        btn.textContent = "复制链接";
        btn.classList.remove("copied");
      }, 2000);
    }).catch(() => {
      document.execCommand("copy");
      btn.textContent = "已复制 ✓";
      btn.classList.add("copied");
      setTimeout(() => {
        btn.textContent = "复制链接";
        btn.classList.remove("copied");
      }, 2000);
    });
  } else {
    document.execCommand("copy");
    btn.textContent = "已复制 ✓";
    btn.classList.add("copied");
    setTimeout(() => {
      btn.textContent = "复制链接";
      btn.classList.remove("copied");
    }, 2000);
  }
}

// 页面加载时检查是否有work参数，如果有则自动打开该作品
window.addEventListener("load", () => {
  const urlParams = new URLSearchParams(window.location.search);
  const workName = urlParams.get("work");
  if (workName) {
    setTimeout(() => {
      const work = worksData.find(w => w.title === decodeURIComponent(workName));
      if (work) {
        handleWorkClick(work);
      }
    }, 500);
  }
});"""

content = content.replace(old_start_compare_end, new_start_compare_end)

# 写入文件
with open("/www/wwwroot/huodouai.com/drama/gallery/index.html", "w", encoding="utf-8") as f:
    f.write(content)

print("✅ 画廊页面已更新，添加作品分享功能")
print("  分享方式: 二维码 + 复制链接")
print("  二维码API: api.qrserver.com (免费)")
print("  深度链接: ?work=作品名 自动打开该作品")
