#!/usr/bin/env python3
"""重构官网导航：8分类+下拉+响应式汉堡菜单"""
import re

with open("/www/wwwroot/www.huodouai.com/index.html", "r") as f:
    content = f.read()

# 新导航HTML
new_nav = '''<nav class="nav-unified" id="mainNav">
  <div class="nav-container">
    <a href="/" class="nav-brand">火斗云智 AIOS</a>
    <button class="nav-toggle" id="navToggle" aria-label="菜单">
      <span></span><span></span><span></span>
    </button>
    <div class="nav-menu" id="navMenu">
      <div class="nav-item"><a href="/">首页</a></div>
      <div class="nav-item has-dropdown">
        <a href="/products.html">产品矩阵</a>
        <div class="dropdown">
          <a href="/products.html">产品总览</a>
          <a href="/product-matrix.html">产品矩阵图</a>
          <a href="/product-map.html">产品地图</a>
          <a href="/commercial.html">商业方案</a>
          <a href="/pricing.html">定价</a>
        </div>
      </div>
      <div class="nav-item has-dropdown">
        <a href="/agent-network.html">智能体</a>
        <div class="dropdown">
          <a href="/agent-network.html">智能体网络</a>
          <a href="/agent-embodiment.html">智能体实体化</a>
          <a href="/high-capabilities.html">高阶能力中心</a>
        </div>
      </div>
      <div class="nav-item has-dropdown">
        <a href="/central-brain.html">中枢大脑</a>
        <div class="dropdown">
          <a href="/central-brain.html">中枢大脑</a>
          <a href="/brain-strategy.html">战略全景</a>
          <a href="/kernel-memory.html">内核记忆</a>
          <a href="/kernel-status.html">内核状态</a>
        </div>
      </div>
      <div class="nav-item has-dropdown">
        <a href="/architecture.html">技术架构</a>
        <div class="dropdown">
          <a href="/architecture.html">架构总览</a>
          <a href="/microkernel-architecture.html">微内核架构</a>
          <a href="/whitepaper.html">技术白皮书</a>
          <a href="/developers.html">开发者中心</a>
          <a href="/docs.html">文档</a>
        </div>
      </div>
      <div class="nav-item has-dropdown">
        <a href="/solutions.html">解决方案</a>
        <div class="dropdown">
          <a href="https://gov.huodouai.com" target="_blank">政务AI ↗</a>
          <a href="https://drama.huodouai.com" target="_blank">短剧生产 ↗</a>
          <a href="/education.html">普惠教育</a>
          <a href="https://kunlun.huodouai.com" target="_blank">昆仑洞天 ↗</a>
        </div>
      </div>
      <div class="nav-item has-dropdown">
        <a href="/digital-assets.html">资产中心</a>
        <div class="dropdown">
          <a href="/digital-assets.html">数字资产</a>
          <a href="/asset-center.html">资产中心</a>
          <a href="/experience-kb.html">经验库</a>
          <a href="/ledger.html">真值账本</a>
        </div>
      </div>
      <div class="nav-item has-dropdown">
        <a href="/auto-pipeline.html">更多</a>
        <div class="dropdown">
          <a href="/auto-pipeline.html">自动化流水线</a>
          <a href="/evolution-strategy.html">进化战略</a>
          <a href="/global-learning.html">全网学习</a>
          <a href="/status-center.html">状态中心</a>
          <a href="/workbench.html">工作台</a>
          <a href="/search.html">全站搜索</a>
        </div>
      </div>
    </div>
  </div>
</nav>'''

# 新导航CSS（插入到</style>前）
new_css = '''
/* ===== 重构导航：8分类+下拉+响应式 ===== */
.nav-unified{position:fixed;top:0;left:0;right:0;z-index:1000;background:rgba(10,10,15,0.92);backdrop-filter:blur(12px);border-bottom:1px solid rgba(212,175,55,0.15)}
.nav-container{max-width:1200px;margin:0 auto;padding:0 20px;display:flex;align-items:center;justify-content:space-between;height:56px}
.nav-brand{font-family:'Noto Serif SC',serif;font-size:17px;font-weight:700;background:linear-gradient(135deg,#f4e4bc,#d4af37);-webkit-background-clip:text;-webkit-text-fill-color:transparent;text-decoration:none;white-space:nowrap}
.nav-menu{display:flex;align-items:center;gap:4px}
.nav-item{position:relative}
.nav-item>a{display:block;padding:8px 12px;color:#bbb;text-decoration:none;font-size:13.5px;transition:color .2s;border-radius:6px;white-space:nowrap}
.nav-item>a:hover{color:#d4af37;background:rgba(212,175,55,0.06)}
.nav-item.has-dropdown>a::after{content:"▾";font-size:10px;margin-left:4px;opacity:.6}
.dropdown{position:absolute;top:100%;left:0;min-width:160px;background:rgba(20,20,30,0.98);border:1px solid rgba(212,175,55,0.2);border-radius:10px;padding:6px;opacity:0;visibility:hidden;transform:translateY(8px);transition:all .2s;box-shadow:0 8px 32px rgba(0,0,0,0.4)}
.nav-item.has-dropdown:hover .dropdown{opacity:1;visibility:visible;transform:translateY(0)}
.dropdown a{display:block;padding:8px 12px;color:#aaa;text-decoration:none;font-size:13px;border-radius:6px;transition:all .15s}
.dropdown a:hover{color:#d4af37;background:rgba(212,175,55,0.08)}
.nav-toggle{display:none;flex-direction:column;gap:5px;background:none;border:none;cursor:pointer;padding:8px}
.nav-toggle span{width:22px;height:2px;background:#d4af37;transition:all .3s;border-radius:2px}
@media(max-width:900px){
  .nav-toggle{display:flex}
  .nav-menu{position:fixed;top:56px;left:0;right:0;bottom:0;background:rgba(10,10,15,0.98);flex-direction:column;align-items:stretch;gap:0;padding:10px 16px;overflow-y:auto;transform:translateX(100%);transition:transform .3s}
  .nav-menu.active{transform:translateX(0)}
  .nav-item>a{padding:12px 14px;font-size:15px;border-bottom:1px solid rgba(255,255,255,0.05)}
  .dropdown{position:static;opacity:1;visibility:visible;transform:none;box-shadow:none;border:none;background:transparent;padding:0 0 0 16px;display:none}
  .nav-item.has-dropdown.open .dropdown{display:block}
  .nav-item.has-dropdown>a::after{content:"+";font-size:16px;float:right}
  .nav-item.has-dropdown.open>a::after{content:"−"}
}
'''

# 新导航JS（插入到</body>前）
new_js = '''<script>
document.getElementById("navToggle").addEventListener("click",function(){
  document.getElementById("navMenu").classList.toggle("active");
  this.classList.toggle("active");
});
document.querySelectorAll(".nav-item.has-dropdown>a").forEach(function(a){
  a.addEventListener("click",function(e){
    if(window.innerWidth<=900){
      e.preventDefault();
      this.parentElement.classList.toggle("open");
    }
  });
});
</script>
'''

# 1. 替换nav部分
content = re.sub(r'<nav class="nav-unified".*?</nav>', new_nav, content, count=1, flags=re.DOTALL)

# 2. 在</style>前插入新CSS
if new_css.strip() not in content:
    content = content.replace("</style>", new_css + "\n</style>")

# 3. 在</body>前插入新JS
if "navToggle" not in content:
    content = content.replace("</body>", new_js + "\n</body>")

with open("/www/wwwroot/www.huodouai.com/index.html", "w") as f:
    f.write(content)

print("✅ 导航重构完成")
print("  主分类: 8个（首页/产品矩阵/智能体/中枢大脑/技术架构/解决方案/资产中心/更多）")
print("  下拉项: 30+个")
print("  响应式: 桌面水平+手机汉堡菜单")
