import os
import json

# 读取works_data.json获取角色相关作品
with open("/www/wwwroot/huodouai.com/drama/works_data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

works = data.get("works", [])

# 按角色分组
character_works = {}
for work in works:
    char = work.get("character", "未分类")
    if char not in character_works:
        character_works[char] = []
    character_works[char].append(work)

# 角色定义
characters = [
    {
        "name": "九天玄女",
        "title": "兵法之神 · 创世之战核心",
        "description": "九天玄女，俗称九天娘娘、九天老母，是中国上古神话中的女神。她是兵法之神、术数之神，曾助黄帝战胜蚩尤，传授兵符、宝剑、奇门遁甲。在昆仑洞天宇宙中，她是创世之战的核心角色。",
        "forms": ["红裙凤冠·战争形态", "月白玄黑·修真形态", "银淡紫·星夜形态"],
        "abilities": ["兵法推演", "术数神通", "兵符宝剑", "奇门遁甲"],
        "color": "#c0392b"
    },
    {
        "name": "太阴月神",
        "title": "月之主宰 · 星夜守护者",
        "description": "太阴月神，掌管月亮与潮汐的上古女神。她在星夜中守护着昆仑洞天的宁静，拥有操控月光与潮汐的力量。她的性格清冷而温柔，是九天玄女的重要盟友。",
        "forms": ["月白玄黑·月神形态", "银蓝星夜·星轨形态"],
        "abilities": ["月光操控", "潮汐之力", "星轨推演", "梦境守护"],
        "color": "#2980b9"
    },
    {
        "name": "女娲",
        "title": "创世之母 · 补天造人",
        "description": "女娲，中国上古神话中的创世女神。她抟土造人，炼石补天，是中华民族的人文始祖。在昆仑洞天宇宙中，她是创世的源头，拥有创造与修复的至高力量。",
        "forms": ["七彩石·补天形态", "黄土·造人形态"],
        "abilities": ["抟土造人", "炼石补天", "创造之力", "生命之源"],
        "color": "#27ae60"
    },
    {
        "name": "西王母",
        "title": "昆仑之主 · 瑶池金母",
        "description": "西王母，又称瑶池金母、王母娘娘，是昆仑仙境的主宰。她掌管不死药与修仙之道，是昆仑洞天宇宙中的最高权威之一。她的瑶池仙境是众神聚会的圣地。",
        "forms": ["金冠华服·王母形态", "道骨仙风·修真形态"],
        "abilities": ["不死灵药", "修仙之道", "瑶池仙境", "众神之主"],
        "color": "#8e44ad"
    },
    {
        "name": "赤华狐影",
        "title": "赤狐仙子 · 灵动化身",
        "description": "赤华狐影，昆仑洞天中的灵动狐仙。她拥有变幻莫测的身法与魅惑众生的容颜，是九天玄女的得力助手。她的赤华之火可以净化邪祟，照亮黑暗。",
        "forms": ["赤华九尾·狐仙形态", "红裙飘逸·人形形态"],
        "abilities": ["九尾变幻", "赤华之火", "魅惑之术", "灵动身法"],
        "color": "#e74c3c"
    }
]

# 为每个角色添加作品数量
for char in characters:
    char["work_count"] = len(character_works.get(char["name"], []))

# 生成角色卡片HTML
character_cards_html = ""
for i, char in enumerate(characters):
    # 获取该角色的第一张作品作为展示图
    char_works = character_works.get(char["name"], [])
    if char_works:
        img_src = char_works[0].get("thumbnail", "")
        img_html = f'<img src="{img_src}" alt="{char["name"]}" style="width:100%;height:100%;object-fit:cover;">'
    else:
        img_html = f'<div class="character-image-placeholder">{char["name"][0]}</div>'
    
    forms_html = "".join([f'<span class="form-tag">{form}</span>' for form in char["forms"]])
    
    character_cards_html += f"""
    <div class="character-card" onclick="showCharacterDetail('{char['name']}')" style="animation-delay: {i*0.1}s;">
      <div class="character-image" style="border-left: 4px solid {char['color']};">
        {img_html}
        <div class="character-image-overlay"></div>
        <div class="character-work-count">{char['work_count']} 作品</div>
      </div>
      <div class="character-info">
        <h3 class="character-name">{char['name']}</h3>
        <p class="character-title">{char['title']}</p>
        <p class="character-description">{char['description'][:80]}...</p>
        <div class="character-forms">{forms_html}</div>
      </div>
    </div>"""

# 生成角色详情数据（JSON）
characters_json = json.dumps(characters, ensure_ascii=False)

# 生成完整HTML
html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>昆仑洞天 · 角色宇宙 | 东方神话AI创世</title>
<meta name="description" content="昆仑洞天角色宇宙 - 九天玄女、太阴月神、女娲、西王母等上古神祇的AI角色设定与形象展示。">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;600;700;900&family=Noto+Sans+SC:wght@300;400;500;700&display=swap" rel="stylesheet">
<style>
:root {{
  --bg-primary: #0a0a0f; --bg-secondary: #12121a; --bg-card: #1a1a24;
  --gold-primary: #d4af37; --gold-light: #f4d03f; --gold-dark: #b8860b;
  --text-primary: #f0f0f0; --text-secondary: #a0a0b0; --text-muted: #606070;
  --border-color: #2a2a3a;
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: "Noto Sans SC", sans-serif; background: var(--bg-primary); color: var(--text-primary); line-height: 1.6; }}

/* 统一导航栏 */
.zy-unified-nav {{ position: fixed; top: 0; left: 0; right: 0; z-index: 9999; background: rgba(5, 5, 8, 0.95); backdrop-filter: blur(10px); border-bottom: 1px solid rgba(212, 175, 55, 0.2); padding: 0 20px; height: 56px; display: flex; align-items: center; justify-content: space-between; }}
.zy-nav-logo {{ display: flex; align-items: center; gap: 10px; text-decoration: none; color: #d4af37; font-size: 18px; font-weight: 700; }}
.zy-nav-logo-icon {{ width: 32px; height: 32px; background: linear-gradient(135deg, #d4af37, #b8941f); border-radius: 6px; display: flex; align-items: center; justify-content: center; color: #050508; font-size: 16px; font-weight: 900; }}
.zy-nav-links {{ display: flex; align-items: center; gap: 24px; list-style: none; margin: 0; padding: 0; }}
.zy-nav-links a {{ color: #a89880; text-decoration: none; font-size: 14px; transition: color 0.3s; white-space: nowrap; }}
.zy-nav-links a:hover {{ color: #d4af37; }}
.zy-nav-toggle {{ display: none; background: none; border: none; color: #d4af37; font-size: 24px; cursor: pointer; padding: 8px; }}
.zy-nav-mobile {{ display: none; position: fixed; top: 56px; left: 0; right: 0; background: rgba(5, 5, 8, 0.98); border-bottom: 1px solid rgba(212, 175, 55, 0.2); padding: 16px 20px; z-index: 9998; }}
.zy-nav-mobile a {{ display: block; padding: 12px 0; color: #a89880; text-decoration: none; font-size: 15px; border-bottom: 1px solid rgba(212, 175, 55, 0.1); }}
@media (max-width: 768px) {{ .zy-nav-links {{ display: none; }} .zy-nav-toggle {{ display: block; }} .zy-nav-mobile.open {{ display: block; }} }}

.hero {{ margin-top: 56px; padding: 60px 20px 40px; text-align: center; position: relative; }}
.hero::before {{ content: ""; position: absolute; top: 0; left: 50%; transform: translateX(-50%); width: 800px; height: 400px; background: radial-gradient(ellipse, rgba(212,175,55,0.1) 0%, transparent 70%); pointer-events: none; }}
.hero-subtitle {{ font-size: 13px; letter-spacing: 6px; color: var(--gold-primary); text-transform: uppercase; margin-bottom: 16px; }}
.hero-title {{ font-family: "Noto Serif SC", serif; font-size: 48px; font-weight: 900; margin-bottom: 16px; background: linear-gradient(135deg, #fff 0%, var(--gold-light) 50%, var(--gold-primary) 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }}
.hero-description {{ font-size: 16px; color: var(--text-secondary); max-width: 600px; margin: 0 auto; }}
.characters-section {{ padding: 0 20px 80px; max-width: 1400px; margin: 0 auto; }}
.section-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 40px; }}
.section-title {{ font-family: "Noto Serif SC", serif; font-size: 24px; font-weight: 700; }}
.section-title::before {{ content: ""; display: inline-block; width: 4px; height: 24px; background: var(--gold-primary); margin-right: 12px; vertical-align: middle; border-radius: 2px; }}
.characters-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 30px; }}
.character-card {{ background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 16px; overflow: hidden; transition: all 0.4s; cursor: pointer; opacity: 0; animation: fadeInUp 0.6s ease forwards; }}
.character-card:hover {{ transform: translateY(-8px); border-color: var(--gold-primary); box-shadow: 0 20px 40px rgba(212,175,55,0.15); }}
.character-image {{ width: 100%; aspect-ratio: 3/4; background: linear-gradient(135deg, #1a1a24, #2d1b4e); display: flex; align-items: center; justify-content: center; position: relative; overflow: hidden; }}
.character-image img {{ width: 100%; height: 100%; object-fit: cover; }}
.character-image-placeholder {{ font-family: "Noto Serif SC", serif; font-size: 72px; font-weight: 900; color: rgba(212,175,55,0.3); }}
.character-image-overlay {{ position: absolute; bottom: 0; left: 0; right: 0; height: 50%; background: linear-gradient(to top, rgba(0,0,0,0.8), transparent); }}
.character-work-count {{ position: absolute; top: 12px; right: 12px; background: rgba(0,0,0,0.7); padding: 4px 12px; border-radius: 12px; font-size: 12px; color: var(--gold-primary); backdrop-filter: blur(4px); }}
.character-info {{ padding: 24px; }}
.character-name {{ font-family: "Noto Serif SC", serif; font-size: 22px; font-weight: 700; margin-bottom: 8px; background: linear-gradient(135deg, var(--gold-light), var(--gold-primary)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }}
.character-title {{ font-size: 13px; color: var(--gold-primary); margin-bottom: 12px; }}
.character-description {{ font-size: 14px; color: var(--text-secondary); line-height: 1.7; margin-bottom: 16px; }}
.character-forms {{ display: flex; flex-wrap: wrap; gap: 8px; }}
.form-tag {{ padding: 4px 12px; background: rgba(212,175,55,0.1); border: 1px solid rgba(212,175,55,0.3); border-radius: 12px; font-size: 11px; color: var(--gold-primary); }}

/* 角色详情模态框 */
.character-modal {{ position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.9); z-index: 10000; display: none; align-items: center; justify-content: center; padding: 20px; }}
.character-modal.active {{ display: flex; }}
.character-modal-content {{ background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 16px; max-width: 900px; width: 100%; max-height: 90vh; overflow-y: auto; position: relative; }}
.character-modal-close {{ position: absolute; top: 16px; right: 16px; background: rgba(0,0,0,0.5); border: none; color: #fff; font-size: 24px; cursor: pointer; width: 40px; height: 40px; border-radius: 50%; z-index: 10; }}
.character-modal-close:hover {{ background: rgba(212,175,55,0.3); }}
.character-modal-hero {{ height: 300px; position: relative; overflow: hidden; }}
.character-modal-hero img {{ width: 100%; height: 100%; object-fit: cover; }}
.character-modal-hero-overlay {{ position: absolute; bottom: 0; left: 0; right: 0; height: 60%; background: linear-gradient(to top, var(--bg-card), transparent); }}
.character-modal-hero-info {{ position: absolute; bottom: 20px; left: 30px; right: 30px; }}
.character-modal-name {{ font-family: "Noto Serif SC", serif; font-size: 36px; font-weight: 900; margin-bottom: 8px; background: linear-gradient(135deg, #fff, var(--gold-light)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }}
.character-modal-title {{ font-size: 16px; color: var(--gold-primary); }}
.character-modal-body {{ padding: 30px; }}
.character-modal-section {{ margin-bottom: 30px; }}
.character-modal-section-title {{ font-size: 18px; font-weight: 700; color: var(--gold-primary); margin-bottom: 16px; display: flex; align-items: center; gap: 10px; }}
.character-modal-section-title::before {{ content: ""; width: 4px; height: 20px; background: var(--gold-primary); border-radius: 2px; }}
.character-modal-description {{ font-size: 15px; color: var(--text-secondary); line-height: 1.8; }}
.abilities-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 12px; }}
.ability-item {{ background: var(--bg-secondary); padding: 12px 16px; border-radius: 8px; text-align: center; font-size: 14px; color: var(--text-primary); border: 1px solid var(--border-color); }}
.forms-tabs {{ display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; }}
.form-tab {{ padding: 8px 16px; background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: 20px; font-size: 13px; color: var(--text-secondary); cursor: pointer; transition: all 0.3s; }}
.form-tab.active {{ background: var(--gold-primary); color: #050508; border-color: var(--gold-primary); font-weight: 600; }}
.character-works-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 12px; }}
.character-work-item {{ aspect-ratio: 3/4; border-radius: 8px; overflow: hidden; cursor: pointer; transition: transform 0.3s; border: 1px solid var(--border-color); }}
.character-work-item:hover {{ transform: scale(1.05); border-color: var(--gold-primary); }}
.character-work-item img {{ width: 100%; height: 100%; object-fit: cover; }}
.footer {{ padding: 40px; text-align: center; border-top: 1px solid var(--border-color); color: var(--text-muted); font-size: 13px; }}
.footer-identity {{ margin-top: 8px; color: var(--gold-dark); font-size: 12px; }}
@keyframes fadeInUp {{ from {{ opacity: 0; transform: translateY(30px); }} to {{ opacity: 1; transform: translateY(0); }} }}
@media (max-width: 768px) {{
  .hero-title {{ font-size: 32px; }}
  .character-modal-hero {{ height: 200px; }}
  .character-modal-name {{ font-size: 28px; }}
  .character-modal-body {{ padding: 20px; }}
}}
</style>
</head>
<body>
  <!-- 统一导航栏 -->
  <nav class="zy-unified-nav">
    <a href="https://www.huodouai.com/" class="zy-nav-logo"><div class="zy-nav-logo-icon">昆</div><span>火斗云智AIOS</span></a>
    <ul class="zy-nav-links">
      <li><a href="https://www.huodouai.com/">首页</a></li>
      <li><a href="https://www.huodouai.com/drama/">作品库</a></li>
      <li><a href="https://www.huodouai.com/drama/characters/" style="color:#d4af37;">角色宇宙</a></li>
      <li><a href="https://www.huodouai.com/drama/pipeline.html">生产流水线</a></li>
      <li><a href="https://www.huodouai.com/drama/qc-report.html">质检报告</a></li>
      <li><a href="https://www.huodouai.com/gov/">政务AI</a></li>
    </ul>
    <button class="zy-nav-toggle" onclick="document.querySelector('.zy-nav-mobile').classList.toggle('open')">☰</button>
  </nav>
  <div class="zy-nav-mobile">
    <a href="https://www.huodouai.com/">首页</a>
    <a href="https://www.huodouai.com/drama/">作品库</a>
    <a href="https://www.huodouai.com/drama/characters/">角色宇宙</a>
    <a href="https://www.huodouai.com/drama/pipeline.html">生产流水线</a>
    <a href="https://www.huodouai.com/drama/qc-report.html">质检报告</a>
    <a href="https://www.huodouai.com/gov/">政务AI</a>
  </div>

  <section class="hero">
    <p class="hero-subtitle">CHARACTER UNIVERSE</p>
    <h1 class="hero-title">角色宇宙</h1>
    <p class="hero-description">上古神祇，栩栩如生。九天玄女、太阴月神、女娲等东方神祇在数字世界中苏醒。</p>
  </section>

  <section class="characters-section">
    <div class="section-header">
      <h2 class="section-title">核心角色</h2>
      <span style="color: var(--text-muted); font-size: 14px;">共 {len(characters)} 位角色</span>
    </div>
    <div class="characters-grid">
      {character_cards_html}
    </div>
  </section>

  <!-- 角色详情模态框 -->
  <div class="character-modal" id="character-modal" onclick="if(event.target===this)closeCharacterModal()">
    <div class="character-modal-content">
      <button class="character-modal-close" onclick="closeCharacterModal()">×</button>
      <div class="character-modal-hero">
        <img id="modal-character-image" src="" alt="">
        <div class="character-modal-hero-overlay"></div>
        <div class="character-modal-hero-info">
          <h2 class="character-modal-name" id="modal-character-name"></h2>
          <p class="character-modal-title" id="modal-character-title"></p>
        </div>
      </div>
      <div class="character-modal-body">
        <div class="character-modal-section">
          <h3 class="character-modal-section-title">角色简介</h3>
          <p class="character-modal-description" id="modal-character-description"></p>
        </div>
        <div class="character-modal-section">
          <h3 class="character-modal-section-title">能力技能</h3>
          <div class="abilities-grid" id="modal-character-abilities"></div>
        </div>
        <div class="character-modal-section">
          <h3 class="character-modal-section-title">形态切换</h3>
          <div class="forms-tabs" id="modal-character-forms"></div>
        </div>
        <div class="character-modal-section">
          <h3 class="character-modal-section-title">相关作品</h3>
          <div class="character-works-grid" id="modal-character-works"></div>
        </div>
      </div>
    </div>
  </div>

  <footer class="footer">
    <p>© 2026 昆仑洞天 · 火斗云智AIOS · 保留所有权利</p>
    <p class="footer-identity">Ω₀⊂⊙∞⊂Ω · DID-BR-000002</p>
  </footer>

  <script>
  const characters = {characters_json};
  const characterWorks = {json.dumps(character_works, ensure_ascii=False)};
  
  function showCharacterDetail(name) {{
    const char = characters.find(c => c.name === name);
    if (!char) return;
    
    const works = characterWorks[name] || [];
    
    // 设置角色信息
    document.getElementById("modal-character-name").textContent = char.name;
    document.getElementById("modal-character-title").textContent = char.title;
    document.getElementById("modal-character-description").textContent = char.description;
    
    // 设置角色图片
    const charImg = works.length > 0 ? works[0].thumbnail : "";
    document.getElementById("modal-character-image").src = charImg;
    
    // 设置能力
    document.getElementById("modal-character-abilities").innerHTML = 
      char.abilities.map(a => `<div class="ability-item">${{a}}</div>`).join("");
    
    // 设置形态标签
    document.getElementById("modal-character-forms").innerHTML = 
      char.forms.map((f, i) => `<div class="form-tab ${{i===0?'active':''}}" onclick="switchForm(this)">${{f}}</div>`).join("");
    
    // 设置相关作品
    document.getElementById("modal-character-works").innerHTML = 
      works.slice(0, 12).map(w => 
        `<div class="character-work-item" onclick="window.open('https://www.huodouai.com/drama/','_blank')">
          <img src="${{w.thumbnail}}" alt="${{w.title}}">
        </div>`
      ).join("") || '<p style="color:var(--text-muted);grid-column:1/-1;text-align:center;padding:20px;">暂无相关作品</p>';
    
    document.getElementById("character-modal").classList.add("active");
    document.body.style.overflow = "hidden";
  }}
  
  function closeCharacterModal() {{
    document.getElementById("character-modal").classList.remove("active");
    document.body.style.overflow = "";
  }}
  
  function switchForm(tab) {{
    document.querySelectorAll(".form-tab").forEach(t => t.classList.remove("active"));
    tab.classList.add("active");
  }}
  
  // ESC键关闭模态框
  document.addEventListener("keydown", (e) => {{
    if (e.key === "Escape") closeCharacterModal();
  }});
  </script>
</body>
</html>"""

# 写入文件
with open("/www/wwwroot/huodouai.com/drama/characters/index.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print("✅ 角色宇宙页面已升级")
print(f"  角色数量: {len(characters)}")
print(f"  新增功能:")
print(f"    - 角色详情模态框")
print(f"    - 多形态切换标签")
print(f"    - 能力技能展示")
print(f"    - 相关作品展示（从works_data.json动态加载）")
print(f"    - 真实角色图片")
print(f"    - 作品数量统计")
