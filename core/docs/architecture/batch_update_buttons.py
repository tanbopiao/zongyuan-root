import re

# 产品页和对应体验地址的映射
product_map = {
    "ai-asset-lock.html": "/kernel-lock-visual.html",
    "ai-gateway.html": "/workbench/",
    "kb-saas.html": "/workbench/",
    "dlp-gateway.html": "/book-demo.html",
    "drama-factory.html": "/kunlun/",
    "character-ai.html": "/agent-studio.html",
    "drift.html": "/book-demo.html",
    "notary-api.html": "/kernel-lock-visual.html",
    "agent-network.html": "/agent-studio.html",
    "solutions.html": "/book-demo.html",
}

base_dir = "/www/wwwroot/huodouai.com/"

for filename, demo_url in product_map.items():
    filepath = base_dir + filename
    try:
        with open(filepath, "r") as f:
            content = f.read()
        
        # 找hero-buttons块，替换里面的内容
        new_buttons = '<div class="hero-buttons">\n                <a href="' + demo_url + '" class="btn btn-gold">在线体验</a>\n                <a href="/book-demo.html" class="btn btn-outline">预约演示</a>\n            </div>'
        
        # 替换hero-buttons块（从<div class="hero-buttons">到下一个</div>）
        pattern = r'<div class="hero-buttons">.*?</div>'
        content = re.sub(pattern, new_buttons, content, flags=re.DOTALL, count=1)
        
        with open(filepath, "w") as f:
            f.write(content)
        
        print(f"✅ {filename} → {demo_url}")
    except Exception as e:
        print(f"❌ {filename}: {e}")

print("\n全部完成")
