#!/usr/bin/env python3
"""首页增加政务AI品牌专区"""
INDEX = "/www/wwwroot/www.huodouai.com/index.html"

with open(INDEX, "r", encoding="utf-8") as f:
    content = f.read()

# 1. 在</style>前增加政务专区CSS（在昆仑专区CSS之后）
gov_css = """
/* ===== 政务AI品牌专区 ===== */
.gov-section {
  padding: 80px 0;
  background: linear-gradient(180deg, var(--bg-primary) 0%, #0a0f1a 50%, var(--bg-primary) 100%);
  position: relative;
  overflow: hidden;
}
.gov-section::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background: radial-gradient(ellipse at 70% 50%, rgba(59,130,246,0.06) 0%, transparent 60%);
  pointer-events: none;
}
.gov-header {
  text-align: center;
  margin-bottom: 50px;
  position: relative;
  z-index: 1;
}
.gov-label {
  color: #3b82f6;
  letter-spacing: 0.2em;
  font-size: 0.8rem;
  margin-bottom: 12px;
  opacity: 0.8;
}
.gov-title {
  font-size: 2.5rem;
  font-weight: 700;
  background: linear-gradient(120deg, #3b82f6, #60a5fa, #3b82f6);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  margin-bottom: 12px;
}
.gov-subtitle {
  color: var(--text-secondary, #a8a8b8);
  font-size: 1.05rem;
  max-width: 600px;
  margin: 0 auto;
}
.gov-showcase {
  display: grid;
  grid-template-columns: 1.2fr 1fr;
  gap: 40px;
  align-items: center;
  position: relative;
  z-index: 1;
  margin-bottom: 40px;
}
.gov-info {
  padding: 20px 0;
}
.gov-info h3 {
  font-size: 1.5rem;
  margin-bottom: 16px;
  color: var(--text-primary, #e8e8ec);
}
.gov-capabilities {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-bottom: 24px;
}
.gov-cap-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: rgba(59,130,246,0.05);
  border: 1px solid rgba(59,130,246,0.1);
  border-radius: 8px;
  font-size: 0.88rem;
  color: #ccc;
}
.gov-cap-item .cap-icon {
  font-size: 1.1rem;
}
.gov-cta-group {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}
.gov-btn-primary {
  display: inline-block;
  padding: 12px 28px;
  background: linear-gradient(120deg, #3b82f6, #2563eb);
  color: #fff;
  border-radius: 8px;
  font-weight: 600;
  font-size: 0.92rem;
  text-decoration: none;
  transition: all 0.3s ease;
}
.gov-btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(59,130,246,0.3);
}
.gov-btn-secondary {
  display: inline-block;
  padding: 12px 28px;
  background: transparent;
  color: #3b82f6;
  border: 1px solid rgba(59,130,246,0.3);
  border-radius: 8px;
  font-weight: 500;
  font-size: 0.92rem;
  text-decoration: none;
  transition: all 0.3s ease;
}
.gov-btn-secondary:hover {
  border-color: #3b82f6;
  background: rgba(59,130,246,0.08);
}
.gov-systems-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}
.gov-system-card {
  padding: 16px;
  background: rgba(59,130,246,0.04);
  border: 1px solid rgba(59,130,246,0.1);
  border-radius: 10px;
  text-align: center;
  transition: all 0.3s ease;
  text-decoration: none;
}
.gov-system-card:hover {
  border-color: rgba(59,130,246,0.3);
  background: rgba(59,130,246,0.08);
  transform: translateY(-2px);
}
.gov-system-icon {
  font-size: 1.5rem;
  margin-bottom: 8px;
}
.gov-system-name {
  font-size: 0.85rem;
  color: #ddd;
  font-weight: 500;
  margin-bottom: 4px;
}
.gov-system-tag {
  font-size: 0.7rem;
  color: #3b82f6;
  background: rgba(59,130,246,0.1);
  padding: 2px 8px;
  border-radius: 4px;
}
.gov-stats {
  display: flex;
  justify-content: center;
  gap: 60px;
  margin-top: 40px;
  padding-top: 30px;
  border-top: 1px solid rgba(59,130,246,0.1);
  position: relative;
  z-index: 1;
}
.gov-stat-item {
  text-align: center;
}
.gov-stat-num {
  font-size: 2rem;
  font-weight: 700;
  color: #3b82f6;
  margin-bottom: 4px;
}
.gov-stat-label {
  font-size: 0.82rem;
  color: #888;
}
@media (max-width: 900px) {
  .gov-showcase { grid-template-columns: 1fr; gap: 30px; }
  .gov-systems-grid { grid-template-columns: repeat(2, 1fr); }
  .gov-title { font-size: 1.8rem; }
  .gov-stats { gap: 30px; flex-wrap: wrap; }
}
@media (max-width: 576px) {
  .gov-section { padding: 50px 0; }
  .gov-capabilities { grid-template-columns: 1fr; }
  .gov-cta-group { flex-direction: column; }
  .gov-btn-primary, .gov-btn-secondary { text-align: center; }
  .gov-systems-grid { grid-template-columns: 1fr 1fr; }
}
"""

content = content.replace("</style>", gov_css + "\n</style>")

# 2. 在昆仑洞天专区之后、核心架构之前插入政务专区HTML
gov_html = """
<!-- ===== 政务AI品牌专区 ===== -->
<section class="gov-section">
  <div class="container">
    <div class="gov-header">
      <div class="gov-label">GOVERNMENT AI PLATFORM</div>
      <h2 class="gov-title">政务AI中台</h2>
      <p class="gov-subtitle">火斗云智政务AI服务平台 V4.0 · 智能政务全链路解决方案</p>
    </div>
    <div class="gov-showcase">
      <div class="gov-info">
        <h3>四大核心能力</h3>
        <div class="gov-capabilities">
          <div class="gov-cap-item"><span class="cap-icon">🤖</span>智能政务问答</div>
          <div class="gov-cap-item"><span class="cap-icon">📝</span>公文自动处理</div>
          <div class="gov-cap-item"><span class="cap-icon">📊</span>政策智能分析</div>
          <div class="gov-cap-item"><span class="cap-icon">📈</span>大数据可视化</div>
        </div>
        <div class="gov-cta-group">
          <a href="https://gov.huodouai.com" target="_blank" class="gov-btn-primary">进入政务AI中台</a>
          <a href="https://gov.huodouai.com/gov-ai/" target="_blank" class="gov-btn-secondary">体验政务AI服务</a>
        </div>
      </div>
      <div class="gov-systems-grid">
        <a href="https://gov.huodouai.com/gov-ai/" target="_blank" class="gov-system-card">
          <div class="gov-system-icon">🤖</div>
          <div class="gov-system-name">AI服务平台</div>
          <div class="gov-system-tag">V4.0</div>
        </a>
        <a href="https://gov.huodouai.com/gov-dashboard/" target="_blank" class="gov-system-card">
          <div class="gov-system-icon">📊</div>
          <div class="gov-system-name">大数据看板</div>
          <div class="gov-system-tag">实时</div>
        </a>
        <a href="https://gov.huodouai.com/gov-admin/" target="_blank" class="gov-system-card">
          <div class="gov-system-icon">⚙️</div>
          <div class="gov-system-name">工作人员后台</div>
          <div class="gov-system-tag">管理</div>
        </a>
        <a href="https://gov.huodouai.com/gov-agents/" target="_blank" class="gov-system-card">
          <div class="gov-system-icon">🧑‍💼</div>
          <div class="gov-system-name">政务智能体</div>
          <div class="gov-system-tag">协同</div>
        </a>
        <a href="https://gov.huodouai.com/gov-canvas/" target="_blank" class="gov-system-card">
          <div class="gov-system-icon">🎨</div>
          <div class="gov-system-name">政务画布</div>
          <div class="gov-system-tag">编排</div>
        </a>
        <a href="https://gov.huodouai.com/gov-analytics/" target="_blank" class="gov-system-card">
          <div class="gov-system-icon">📈</div>
          <div class="gov-system-name">分析中心</div>
          <div class="gov-system-tag">洞察</div>
        </a>
        <a href="https://gov.huodouai.com/gov-cases/" target="_blank" class="gov-system-card">
          <div class="gov-system-icon">📋</div>
          <div class="gov-system-name">客户案例</div>
          <div class="gov-system-tag">实践</div>
        </a>
        <a href="https://gov.huodouai.com/gov-monitor/" target="_blank" class="gov-system-card">
          <div class="gov-system-icon">🖥️</div>
          <div class="gov-system-name">监控中心</div>
          <div class="gov-system-tag">运维</div>
        </a>
      </div>
    </div>
    <div class="gov-stats">
      <div class="gov-stat-item">
        <div class="gov-stat-num">13</div>
        <div class="gov-stat-label">子系统全可用</div>
      </div>
      <div class="gov-stat-item">
        <div class="gov-stat-num">4</div>
        <div class="gov-stat-label">核心平台</div>
      </div>
      <div class="gov-stat-item">
        <div class="gov-stat-num">6</div>
        <div class="gov-stat-label">业务应用</div>
      </div>
      <div class="gov-stat-item">
        <div class="gov-stat-num">V4.0</div>
        <div class="gov-stat-label">服务平台版本</div>
      </div>
    </div>
  </div>
</section>
"""

# 在id="architecture"的section之前插入（昆仑专区已经在architecture之前了，所以政务专区插在昆仑专区之后）
# 找到昆仑专区的结束标签</section>，然后在其后插入
content = content.replace(
    '<section class="section" id="architecture">',
    gov_html + '\n<section class="section" id="architecture">'
)

with open(INDEX, "w", encoding="utf-8") as f:
    f.write(content)

print("首页政务AI品牌专区已添加")
