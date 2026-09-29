#!/usr/bin/env python3
"""首页增加昆仑洞天品牌专区"""
INDEX = "/www/wwwroot/www.huodouai.com/index.html"

with open(INDEX, "r", encoding="utf-8") as f:
    content = f.read()

# 1. 在</style>前增加昆仑专区CSS
kunlun_css = """
/* ===== 昆仑洞天品牌专区 ===== */
.kunlun-section {
  padding: 80px 0;
  background: linear-gradient(180deg, var(--bg-primary) 0%, #0d0a17 50%, var(--bg-primary) 100%);
  position: relative;
  overflow: hidden;
}
.kunlun-section::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background: radial-gradient(ellipse at 30% 50%, rgba(212,175,55,0.06) 0%, transparent 60%);
  pointer-events: none;
}
.kunlun-header {
  text-align: center;
  margin-bottom: 50px;
  position: relative;
  z-index: 1;
}
.kunlun-label {
  color: var(--accent-gold, #d4af37);
  letter-spacing: 0.2em;
  font-size: 0.8rem;
  margin-bottom: 12px;
  opacity: 0.8;
}
.kunlun-title {
  font-size: 2.5rem;
  font-weight: 700;
  background: linear-gradient(120deg, #d4af37, #f2d272, #d4af37);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  margin-bottom: 12px;
}
.kunlun-subtitle {
  color: var(--text-secondary, #a8a8b8);
  font-size: 1.05rem;
  max-width: 600px;
  margin: 0 auto;
}
.kunlun-showcase {
  display: grid;
  grid-template-columns: 1fr 1.2fr;
  gap: 40px;
  align-items: center;
  position: relative;
  z-index: 1;
  margin-bottom: 40px;
}
.kunlun-works {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}
.kunlun-work-card {
  aspect-ratio: 9/16;
  border-radius: 10px;
  overflow: hidden;
  position: relative;
  border: 1px solid rgba(212,175,55,0.15);
  transition: all 0.3s ease;
  cursor: pointer;
}
.kunlun-work-card:hover {
  transform: translateY(-4px);
  border-color: rgba(212,175,55,0.4);
  box-shadow: 0 12px 32px rgba(212,175,55,0.15);
}
.kunlun-work-card img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.kunlun-work-card .work-overlay {
  position: absolute;
  bottom: 0; left: 0; right: 0;
  padding: 8px;
  background: linear-gradient(transparent, rgba(0,0,0,0.8));
  font-size: 0.7rem;
  color: #ddd;
}
.kunlun-info {
  padding: 20px 0;
}
.kunlun-info h3 {
  font-size: 1.5rem;
  margin-bottom: 16px;
  color: var(--text-primary, #e8e8ec);
}
.kunlun-capabilities {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-bottom: 24px;
}
.kunlun-cap-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: rgba(212,175,55,0.05);
  border: 1px solid rgba(212,175,55,0.1);
  border-radius: 8px;
  font-size: 0.88rem;
  color: #ccc;
}
.kunlun-cap-item .cap-icon {
  font-size: 1.1rem;
}
.kunlun-cta-group {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}
.kunlun-btn-primary {
  display: inline-block;
  padding: 12px 28px;
  background: linear-gradient(120deg, #d4af37, #c49a27);
  color: #000;
  border-radius: 8px;
  font-weight: 600;
  font-size: 0.92rem;
  text-decoration: none;
  transition: all 0.3s ease;
}
.kunlun-btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(212,175,55,0.3);
}
.kunlun-btn-secondary {
  display: inline-block;
  padding: 12px 28px;
  background: transparent;
  color: #d4af37;
  border: 1px solid rgba(212,175,55,0.3);
  border-radius: 8px;
  font-weight: 500;
  font-size: 0.92rem;
  text-decoration: none;
  transition: all 0.3s ease;
}
.kunlun-btn-secondary:hover {
  border-color: #d4af37;
  background: rgba(212,175,55,0.08);
}
.kunlun-stats {
  display: flex;
  justify-content: center;
  gap: 60px;
  margin-top: 40px;
  padding-top: 30px;
  border-top: 1px solid rgba(212,175,55,0.1);
  position: relative;
  z-index: 1;
}
.kunlun-stat-item {
  text-align: center;
}
.kunlun-stat-num {
  font-size: 2rem;
  font-weight: 700;
  color: #d4af37;
  margin-bottom: 4px;
}
.kunlun-stat-label {
  font-size: 0.82rem;
  color: #888;
}
@media (max-width: 900px) {
  .kunlun-showcase { grid-template-columns: 1fr; gap: 30px; }
  .kunlun-works { grid-template-columns: repeat(3, 1fr); }
  .kunlun-title { font-size: 1.8rem; }
  .kunlun-stats { gap: 30px; flex-wrap: wrap; }
}
@media (max-width: 576px) {
  .kunlun-section { padding: 50px 0; }
  .kunlun-capabilities { grid-template-columns: 1fr; }
  .kunlun-cta-group { flex-direction: column; }
  .kunlun-btn-primary, .kunlun-btn-secondary { text-align: center; }
}
"""

content = content.replace("</style>", kunlun_css + "\n</style>")

# 2. 在Hero之后、核心架构之前插入昆仑专区HTML
kunlun_html = """
<!-- ===== 昆仑洞天品牌专区 ===== -->
<section class="kunlun-section">
  <div class="container">
    <div class="kunlun-header">
      <div class="kunlun-label">ORIENTAL MYTHOLOGY AI UNIVERSE</div>
      <h2 class="kunlun-title">昆仑洞天</h2>
      <p class="kunlun-subtitle">东方神话AI创世宇宙 · 以AI之力重塑东方神话史诗</p>
    </div>
    <div class="kunlun-showcase">
      <div class="kunlun-works">
        <a href="/works-gallery-v2.html" class="kunlun-work-card">
          <img src="/assets/keyframes/ep01/S01-005_玄女战争形态降临.jpg" alt="九天玄女">
          <div class="work-overlay">九天玄女·战争形态</div>
        </a>
        <a href="/works-gallery-v2.html" class="kunlun-work-card">
          <img src="/assets/keyframes/goddess/03_神女觉醒_竖屏.png" alt="神女觉醒">
          <div class="work-overlay">神女觉醒</div>
        </a>
        <a href="/works-gallery-v2.html" class="kunlun-work-card">
          <img src="/assets/keyframes/characters/taiyin_moon_god_keyframe_02_scene.png" alt="太阴月神">
          <div class="work-overlay">太阴月神·星夜</div>
        </a>
      </div>
      <div class="kunlun-info">
        <h3>四大创世能力</h3>
        <div class="kunlun-capabilities">
          <div class="kunlun-cap-item"><span class="cap-icon">🎨</span>图像生成</div>
          <div class="kunlun-cap-item"><span class="cap-icon">🎬</span>视频生成</div>
          <div class="kunlun-cap-item"><span class="cap-icon">📽️</span>短剧生产</div>
          <div class="kunlun-cap-item"><span class="cap-icon">👤</span>角色宇宙</div>
        </div>
        <div class="kunlun-cta-group">
          <a href="/kunlun/" class="kunlun-btn-primary">进入昆仑洞天</a>
          <a href="/drama/" class="kunlun-btn-secondary">体验短剧生产</a>
        </div>
      </div>
    </div>
    <div class="kunlun-stats">
      <div class="kunlun-stat-item">
        <div class="kunlun-stat-num">2907+</div>
        <div class="kunlun-stat-label">AI生成作品</div>
      </div>
      <div class="kunlun-stat-item">
        <div class="kunlun-stat-num">6+</div>
        <div class="kunlun-stat-label">东方神话角色</div>
      </div>
      <div class="kunlun-stat-item">
        <div class="kunlun-stat-num">3</div>
        <div class="kunlun-stat-label">形态切换</div>
      </div>
      <div class="kunlun-stat-item">
        <div class="kunlun-stat-num">100%</div>
        <div class="kunlun-stat-label">资产确权锁档</div>
      </div>
    </div>
  </div>
</section>
"""

# 在id="architecture"的section之前插入
content = content.replace('<section class="section" id="architecture">', kunlun_html + '\n<section class="section" id="architecture">')

with open(INDEX, "w", encoding="utf-8") as f:
    f.write(content)

print("首页昆仑洞天品牌专区已添加")
