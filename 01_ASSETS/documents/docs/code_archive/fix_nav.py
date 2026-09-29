import re

with open("/www/wwwroot/huodouai.com/index.html", "r", encoding="utf-8") as f:
    html = f.read()

new_nav = '''<nav class="nav-unified" id="mainNav">
  <div class="nav-container">
    <a href="/" class="nav-brand">火斗云智 AIOS</a>
    <label class="nav-toggle" for="navCheck" aria-label="菜单">
      <span></span><span></span><span></span>
    </label>
    <div class="nav-menu" id="navMenu">
      <div class="nav-item"><a href="/">首页</a></div>
      <div class="nav-item has-dropdown">
        <a href="/products.html">产品矩阵</a>
        <div class="dropdown">
          <a href="/products.html">产品总览</a>
          <a href="/product-matrix.html">产品矩阵图</a>
          <a href="/commercial.html">商业方案</a>
          <a href="/cases.html">客户案例</a>
          <a href="/pricing.html">定价方案</a>
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
          <a href="/kernel-status.html">内核状态</a>
          <a href="/unified-console.html">统一控制台</a>
        </div>
      </div>
      <div class="nav-item has-dropdown">
        <a href="/works-gallery-v2.html">作品中心</a>
        <div class="dropdown">
          <a href="/works-gallery-v2.html">作品库V2</a>
          <a href="/drama/">短剧作品库</a>
          <a href="/kunlun/">昆仑洞天</a>
          <a href="/keyframe-gallery.html">关键帧资产库</a>
          <a href="/digital-gallery-v3.html">数字画廊</a>
        </div>
      </div>
      <div class="nav-item has-dropdown">
        <a href="/architecture.html">技术架构</a>
        <div class="dropdown">
          <a href="/architecture.html">架构总览</a>
          <a href="/microkernel-architecture.html">微内核架构</a>
          <a href="/whitepaper.html">技术白皮书</a>
          <a href="/developers.html">开发者中心</a>
          <a href="/docs.html">文档中心</a>
        </div>
      </div>
      <div class="nav-item has-dropdown">
        <a href="/governance.html">治理战略</a>
        <div class="dropdown">
          <a href="/governance.html">治理体系</a>
          <a href="/philosophy.html">思想体系</a>
          <a href="/evolution-strategy.html">进化战略</a>
          <a href="/lightweight-strategy.html">轻量化战略</a>
          <a href="/global-learning.html">全网学习</a>
        </div>
      </div>
      <div class="nav-item has-dropdown">
        <a href="/digital-assets.html">资产中心</a>
        <div class="dropdown">
          <a href="/digital-assets.html">数字资产</a>
          <a href="/asset-center.html">资产中心</a>
          <a href="/ledger.html">真值账本</a>
          <a href="/experience-kb.html">经验库</a>
          <a href="/aios/index.html">AIOS资产中心</a>
        </div>
      </div>
      <div class="nav-item has-dropdown">
        <a href="/aios/visual/cloud_brain_dashboard.html">实时监控</a>
        <div class="dropdown">
          <a href="/aios/visual/cloud_brain_dashboard.html">云脑仪表盘</a>
          <a href="/aios/visual/kernel-dashboard.html">内核仪表盘</a>
          <a href="/aios/visual/memory_gateway_monitor.html">记忆网关监控</a>
          <a href="/aios/visual/scheduler_monitor_dashboard.html">调度器监控</a>
          <a href="/system-dashboard.html">系统仪表盘</a>
          <a href="/status-center.html">状态中心</a>
        </div>
      </div>
      <div class="nav-item has-dropdown">
        <a href="/auto-pipeline.html">更多</a>
        <div class="dropdown">
          <a href="/auto-pipeline.html">自动化流水线</a>
          <a href="/model-compare-lab.html">模型对比实验室</a>
          <a href="/education.html">普惠教育</a>
          <a href="/search.html">全站搜索</a>
          <a href="/performance.html">性能监控</a>
          <a href="https://gov.huodouai.com" target="_blank">政务AI ↗</a>
          <a href="https://status.huodouai.com" target="_blank">实时状态站 ↗</a>
        </div>
      </div>
      <div class="nav-cta" style="display:flex;align-items:center;gap:12px;margin-left:20px;">
        <a href="/book-demo.html" style="background:linear-gradient(135deg,#d4af37,#b8941f);color:#1a1a2e;padding:8px 20px;border-radius:8px;text-decoration:none;font-size:13.5px;font-weight:600;transition:all .2s;white-space:nowrap;box-shadow:0 4px 15px rgba(212,175,55,0.3);" onmouseover="this.style.transform='translateY(-2px)';this.style.boxShadow='0 6px 20px rgba(212,175,55,0.4)'" onmouseout="this.style.transform='translateY(0)';this.style.boxShadow='0 4px 15px rgba(212,175,55,0.3)'">预约演示</a>
      </div>
    </div>
  </div>
</nav>'''

pattern = r'<nav class="nav-unified" id="mainNav">.*?</nav>'
match = re.search(pattern, html, flags=re.DOTALL)
if match:
    new_html = html[:match.start()] + new_nav + html[match.end():]
    with open("/www/wwwroot/huodouai.com/index.html", "w", encoding="utf-8") as f:
        f.write(new_html)
    print("导航替换成功")
    print("原导航长度:", len(match.group(0)))
    print("新导航长度:", len(new_nav))
else:
    print("未找到导航部分")
