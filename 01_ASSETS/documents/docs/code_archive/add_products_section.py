
with open("/www/wwwroot/aios.huodouai.com/index.html", "r") as f:
    content = f.read()

# 产品矩阵HTML
product_section = """
<section class="section" id="products">
  <div class="container">
    <h2 class="section-title">产品矩阵</h2>
    <p class="section-subtitle">火斗云智AIOS · 全栈AI产品能力</p>
    
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 24px; margin-top: 40px;">
      
      <!-- 对话AI -->
      <div style="background: var(--bg-card); border: 1px solid var(--border-gold); border-radius: 16px; padding: 32px;">
        <div style="font-size: 32px; margin-bottom: 16px;">💬</div>
        <h3 style="margin-bottom: 12px; color: var(--gold);">元内核对话AI</h3>
        <p style="color: var(--text-secondary); margin-bottom: 20px;">规则驱动的AI对话，身份一致性，Markdown排版，对齐豆包体验</p>
        <a href="/chat.html" style="color: var(--gold); text-decoration: none;">立即体验 →</a>
      </div>
      
      <!-- 图片生成 -->
      <div style="background: var(--bg-card); border: 1px solid var(--border-gold); border-radius: 16px; padding: 32px;">
        <div style="font-size: 32px; margin-bottom: 16px;">🎨</div>
        <h3 style="margin-bottom: 12px; color: var(--gold);">图片生成</h3>
        <p style="color: var(--text-secondary); margin-bottom: 20px;">文生图，国风仙侠风格，黑金暗纹，伦勃朗光影</p>
        <a href="/image-generator.html" style="color: var(--gold); text-decoration: none;">立即生成 →</a>
      </div>
      
      <!-- 视频生成 -->
      <div style="background: var(--bg-card); border: 1px solid var(--border-gold); border-radius: 16px; padding: 32px;">
        <div style="font-size: 32px; margin-bottom: 16px;">🎬</div>
        <h3 style="margin-bottom: 12px; color: var(--gold);">视频生成</h3>
        <p style="color: var(--text-secondary); margin-bottom: 20px;">文生视频，火山方舟Seedance，国风仙侠短剧片段</p>
        <a href="/video-generator.html" style="color: var(--gold); text-decoration: none;">立即生成 →</a>
      </div>
      
      <!-- 全自动短剧 -->
      <div style="background: var(--bg-card); border: 1px solid var(--border-gold); border-radius: 16px; padding: 32px;">
        <div style="font-size: 32px; margin-bottom: 16px;">🎭</div>
        <h3 style="margin-bottom: 12px; color: var(--gold);">全自动短剧生成</h3>
        <p style="color: var(--text-secondary); margin-bottom: 20px;">输入剧情，一键完成：分镜→关键帧→视频</p>
        <a href="/auto-generator-v2.html" style="color: var(--gold); text-decoration: none;">立即创作 →</a>
      </div>
      
      <!-- API服务 -->
      <div style="background: var(--bg-card); border: 1px solid var(--border-gold); border-radius: 16px; padding: 32px;">
        <div style="font-size: 32px; margin-bottom: 16px;">🔌</div>
        <h3 style="margin-bottom: 12px; color: var(--gold);">元内核API</h3>
        <p style="color: var(--text-secondary); margin-bottom: 20px;">RESTful API，对话+图片+视频，按量计费</p>
        <a href="/api-pricing.html" style="color: var(--gold); text-decoration: none;">查看定价 →</a>
      </div>
      
      <!-- 注册 -->
      <div style="background: var(--bg-card); border: 1px solid var(--border-gold); border-radius: 16px; padding: 32px;">
        <div style="font-size: 32px; margin-bottom: 16px;">📝</div>
        <h3 style="margin-bottom: 12px; color: var(--gold);">免费注册</h3>
        <p style="color: var(--text-secondary); margin-bottom: 20px;">立即注册，免费1000次API调用额度</p>
        <a href="/register.html" style="color: var(--gold); text-decoration: none;">立即注册 →</a>
      </div>
      
    </div>
  </div>
</section>

"""

# 在architecture section前面插入
content = content.replace('<section class="section" id="architecture">', product_section + '<section class="section" id="architecture">')

# 更新导航栏，加产品矩阵
old_nav = '<li><a href="#architecture">核心架构</a></li>'
new_nav = '<li><a href="#products">产品矩阵</a></li>\n    <li><a href="#architecture">核心架构</a></li>'
content = content.replace(old_nav, new_nav)

with open("/tmp/index-v2.html", "w") as f:
    f.write(content)
print("✅ 产品矩阵section已添加")
