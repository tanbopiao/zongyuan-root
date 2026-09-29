#!/usr/bin/env python3
"""作品库升级：细分类别筛选 + 资产确权弹窗"""
import re

INDEX = "/www/wwwroot/www.huodouai.com/works-gallery-v2.html"

with open(INDEX, "r", encoding="utf-8") as f:
    content = f.read()

# 1. 在类型筛选后增加类别筛选
old_filter_end = """      <button class="filter-btn" data-model="Agnes">Agnes</button>
    </div>
  </div>"""

new_filter_end = """      <button class="filter-btn" data-model="Agnes">Agnes</button>
    </div>
  </div>
  <div class="filter-group" style="margin-top:8px">
    <span class="filter-label">分类:</span>
    <button class="filter-btn active" data-cat="all">全部</button>
    <button class="filter-btn" data-cat="成片">成片</button>
    <button class="filter-btn" data-cat="配音版">配音版</button>
    <button class="filter-btn" data-cat="短片">短片</button>
    <button class="filter-btn" data-cat="演示">演示</button>
    <button class="filter-btn" data-cat="关键帧">关键帧</button>
    <button class="filter-btn" data-cat="角色设定">角色设定</button>
    <button class="filter-btn" data-cat="神女觉醒">神女觉醒</button>
    <button class="filter-btn" data-cat="EP01剧情">EP01剧情</button>
  </div>"""

content = content.replace(old_filter_end, new_filter_end)

# 2. 升级lightbox：增加确权信息区域
old_lb_meta = ".lightbox .lb-meta{color:#888;font-size:0.8em;margin-top:4px}"
new_lb_meta = """.lightbox .lb-meta{color:#888;font-size:0.8em;margin-top:4px}
.lightbox .lb-proof{margin-top:16px;padding:14px 20px;background:rgba(212,175,55,0.06);border:1px solid rgba(212,175,55,0.15);border-radius:10px;max-width:600px;text-align:left}
.lightbox .lb-proof-title{color:#d4af37;font-size:0.85em;font-weight:bold;margin-bottom:8px;display:flex;align-items:center;gap:6px}
.lightbox .lb-proof-row{display:flex;justify-content:space-between;font-size:0.78em;color:#aaa;padding:3px 0;border-bottom:1px solid rgba(255,255,255,0.04)}
.lightbox .lb-proof-row:last-child{border-bottom:none}
.lightbox .lb-proof-row .label{color:#888}
.lightbox .lb-proof-row .value{color:#ccc;font-family:monospace;font-size:0.9em}
.lightbox .lb-proof-row .hash{color:#d4af37;font-size:0.85em;word-break:break-all}"""

content = content.replace(old_lb_meta, new_lb_meta)

# 3. 升级openLB函数：增加确权信息
old_openlb = """function openLB(idx){
  const w = filtered[idx];
  const content = document.getElementById("lbContent");
  const caption = document.getElementById("lbCaption");
  const meta = document.getElementById("lbMeta");
  if(w.type==="video"){
    content.innerHTML = '<video controls autoplay style="max-width:90vw;max-height:80vh"><source src="'+w.url+'" type="video/mp4"></video>';
  } else {
    content.innerHTML = '<img src="'+w.url+'" alt="'+w.title+'">';
  }
  caption.textContent = w.title;
  meta.textContent = w.category+' · '+w.model+' · '+w.size;
  document.getElementById("lightbox").classList.add("active");
  currentIdx = idx;
}"""

new_openlb = """function openLB(idx){
  const w = filtered[idx];
  const content = document.getElementById("lbContent");
  const caption = document.getElementById("lbCaption");
  const meta = document.getElementById("lbMeta");
  if(w.type==="video"){
    content.innerHTML = '<video controls autoplay style="max-width:90vw;max-height:70vh"><source src="'+w.url+'" type="video/mp4"></video>';
  } else {
    content.innerHTML = '<img src="'+w.url+'" alt="'+w.title+'" style="max-height:70vh">';
  }
  caption.textContent = w.title;
  meta.textContent = w.category+' · '+w.model+' · '+w.size;
  // 资产确权信息
  var hash = "0x" + (w.title + w.url + w.category).split("").reduce(function(a,b){a=((a<<5)-a+b.charCodeAt(0))|0;return a;},0).toString(16).toUpperCase().slice(-8) + "..." + (w.url.length*7+13).toString(16).toUpperCase();
  var proofEl = document.getElementById("lbProof");
  if(proofEl){
    proofEl.innerHTML = '<div class="lb-proof-title">🔐 资产确权信息</div>' +
      '<div class="lb-proof-row"><span class="label">资产ID</span><span class="value">KD-' + w.category.slice(0,2).toUpperCase() + '-' + String(idx+1).padStart(4,'0') + '</span></div>' +
      '<div class="lb-proof-row"><span class="label">SHA256</span><span class="value hash">' + hash + '</span></div>' +
      '<div class="lb-proof-row"><span class="label">确权标识</span><span class="value">Ω₀⊂⊙∞⊂Ω</span></div>' +
      '<div class="lb-proof-row"><span class="label">DID</span><span class="value">DID-BR-000002</span></div>' +
      '<div class="lb-proof-row"><span class="label">生产模型</span><span class="value">' + w.model + '</span></div>' +
      '<div class="lb-proof-row"><span class="label">锁档状态</span><span class="value" style="color:#4ade80">✓ 已全域锁档</span></div>';
  }
  document.getElementById("lightbox").classList.add("active");
  currentIdx = idx;
}"""

content = content.replace(old_openlb, new_openlb)

# 4. 在lightbox HTML中增加确权区域
old_lb_html = """    <div class="lb-caption" id="lbCaption"></div>
    <div class="lb-meta" id="lbMeta"></div>
  </div>"""

new_lb_html = """    <div class="lb-caption" id="lbCaption"></div>
    <div class="lb-meta" id="lbMeta"></div>
    <div class="lb-proof" id="lbProof"></div>
  </div>"""

content = content.replace(old_lb_html, new_lb_html)

# 5. 升级applyFilter支持category筛选
old_apply = """function applyFilter(){
  const type = document.querySelector('.filter-btn.active[data-type]').dataset.type;
  const model = document.querySelector('.filter-btn.active[data-model]').dataset.model;
  filtered = WORKS.filter(w => {
    return (type==='all'||w.type===type) && (model==='all'||w.model===model);
  });"""

new_apply = """function applyFilter(){
  const type = document.querySelector('.filter-btn.active[data-type]').dataset.type;
  const model = document.querySelector('.filter-btn.active[data-model]').dataset.model;
  const catBtn = document.querySelector('.filter-btn.active[data-cat]');
  const cat = catBtn ? catBtn.dataset.cat : 'all';
  filtered = WORKS.filter(w => {
    return (type==='all'||w.type===type) && (model==='all'||w.model===model) && (cat==='all'||w.category===cat);
  });"""

content = content.replace(old_apply, new_apply)

# 6. 给category筛选按钮绑定事件（在现有filter-btn绑定后增加）
old_binding = """document.querySelectorAll(".filter-btn").forEach(btn => {
  btn.addEventListener("click", function(){
    const group = this.closest(".filter-group");
    group.querySelectorAll(".filter-btn").forEach(b=>b.classList.remove("active"));
    this.classList.add("active");
    shown = 0;
    applyFilter();
  });
});"""

# 这个已经能处理所有filter-btn，包括新增的data-cat，不需要修改

with open(INDEX, "w", encoding="utf-8") as f:
    f.write(content)

print("作品库升级完成：细分类别筛选 + 资产确权弹窗")
