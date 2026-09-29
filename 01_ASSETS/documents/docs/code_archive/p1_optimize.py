#!/usr/bin/env python3
"""P1优化：子目录入口+移动端适配+SEO"""
import os, re

WWW = "/www/wwwroot/www.huodouai.com"

# ===== 1. 首页导航添加可视化看板入口 =====
index_path = os.path.join(WWW, "index.html")
with open(index_path, encoding="utf-8") as f:
    idx = f.read()

# 在"资产中心"下拉中添加可视化看板入口
old_dropdown = '''<div class="dropdown">
          <a href="/digital-assets.html">数字资产</a>
          <a href="/asset-center.html">资产中心</a>
          <a href="/experience-kb.html">经验库</a>
          <a href="/ledger.html">真值账本</a>
        </div>'''

new_dropdown = '''<div class="dropdown">
          <a href="/digital-assets.html">数字资产</a>
          <a href="/asset-center.html">资产中心</a>
          <a href="/experience-kb.html">经验库</a>
          <a href="/ledger.html">真值账本</a>
          <a href="/aios/visual/cloud_brain_dashboard.html">云脑仪表盘</a>
          <a href="/aios/visual/kernel-dashboard.html">内核仪表盘</a>
          <a href="/aios/visual/memory_gateway_monitor.html">记忆网关监控</a>
          <a href="/aios/visual/scheduler_monitor_dashboard.html">调度器监控</a>
          <a href="/aios/index.html">AIOS资产中心</a>
        </div>'''

if old_dropdown in idx:
    idx = idx.replace(old_dropdown, new_dropdown)
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(idx)
    print("✅ 首页导航添加可视化看板入口")
else:
    print("⚠️ 导航结构不匹配，跳过")

# ===== 2. 给无@media的页面添加基础移动端适配 =====
no_responsive = [
    "change-ledger.html", "digital-assets.html", "experience-kb.html",
    "global-audit-report.html", "high-capabilities.html", "lightweight-strategy.html",
    "meta-rules-v2.html", "sitemap.html", "standardization-center.html",
    "standard-sop.html", "system-dashboard.html", "truth-transmutation.html"
]

mobile_css = """
/* ===== 移动端适配 ===== */
@media (max-width: 768px) {
  body { padding: 10px !important; }
  .container, .sm-container { max-width: 100% !important; padding: 0 12px !important; }
  h1 { font-size: 1.5em !important; }
  h2 { font-size: 1.2em !important; }
  .sm-grid { grid-template-columns: 1fr !important; }
  table { font-size: 0.85em; }
  img { max-width: 100% !important; height: auto !important; }
}
"""

added = 0
for page in no_responsive:
    fpath = os.path.join(WWW, page)
    if not os.path.exists(fpath):
        continue
    with open(fpath, encoding="utf-8", errors="ignore") as f:
        content = f.read()
    if "@media" not in content and "</style>" in content:
        content = content.replace("</style>", mobile_css + "</style>", 1)
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(content)
        added += 1

print(f"✅ {added}个页面添加移动端适配")

# ===== 3. 给无meta description的页面添加SEO =====
no_seo = [
    "change-ledger.html", "digital-assets.html", "experience-kb.html",
    "global-audit-report.html", "high-capabilities.html", "lightweight-strategy.html",
    "meta-rules-v2.html", "portal.html", "standardization-center.html",
    "standard-sop.html", "status.html", "system-dashboard.html",
    "truth-transmutation.html"
]

seo_descriptions = {
    "change-ledger.html": "火斗云智AIOS系统变更台账，记录所有系统更新与优化历史",
    "digital-assets.html": "火斗云智AIOS数字资产中心，真值资产可视化展示",
    "experience-kb.html": "火斗云智AIOS经验知识库，沉淀最佳实践与方法论",
    "global-audit-report.html": "火斗云智AIOS全域审计报告，体系健康度全维度评估",
    "high-capabilities.html": "火斗云智AIOS高阶能力中心，展示前沿AI能力",
    "lightweight-strategy.html": "火斗云智AIOS轻量化优先战略，体验与效率最优稳态",
    "meta-rules-v2.html": "火斗云智AIOS系统开发元规则V2.0，轻量化优先准则",
    "portal.html": "火斗云智AIOS门户入口",
    "standardization-center.html": "火斗云智AIOS标准化中心，规范与标准管理",
    "standard-sop.html": "火斗云智AIOS标准作业流程SOP",
    "status.html": "火斗云智AIOS系统状态中心",
    "system-dashboard.html": "火斗云智AIOS实时系统仪表盘",
    "truth-transmutation.html": "火斗云智AIOS真值转化引擎，真值提炼与转化",
}

seo_added = 0
for page in no_seo:
    fpath = os.path.join(WWW, page)
    if not os.path.exists(fpath):
        continue
    with open(fpath, encoding="utf-8", errors="ignore") as f:
        content = f.read()
    if 'name="description"' not in content and "<head>" in content:
        desc = seo_descriptions.get(page, "火斗云智AIOS")
        meta_tag = f'<meta name="description" content="{desc}">'
        content = content.replace("<head>", "<head>\n" + meta_tag, 1)
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(content)
        seo_added += 1

print(f"✅ {seo_added}个页面添加SEO meta description")

print("\n✅ P1优化完成")
