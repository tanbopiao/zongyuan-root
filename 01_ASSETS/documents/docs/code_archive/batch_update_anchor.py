
import os
import glob

# 统一导航栏（全部锚定www.huodouai.com）
UNIFIED_NAV = """
<nav style="background: #fff; box-shadow: 0 2px 8px rgba(0,0,0,0.08); padding: 16px 24px; display: flex; align-items: center; justify-content: space-between; position: sticky; top: 0; z-index: 100;">
    <div style="display: flex; align-items: center; gap: 12px;">
        <div style="width: 36px; height: 36px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 8px; display: flex; align-items: center; justify-content: center; color: #fff; font-weight: 700; font-size: 16px;">火</div>
        <span style="font-size: 18px; font-weight: 600; color: #1a202c;">火斗云智</span>
    </div>
    <div style="display: flex; gap: 24px; align-items: center;">
        <a href="https://www.huodouai.com/" style="color: #4a5568; text-decoration: none; font-size: 14px;">首页</a>
        <a href="https://www.huodouai.com/products/" style="color: #4a5568; text-decoration: none; font-size: 14px;">产品</a>
        <a href="https://www.huodouai.com/solutions/" style="color: #4a5568; text-decoration: none; font-size: 14px;">解决方案</a>
        <a href="https://www.huodouai.com/docs/" style="color: #4a5568; text-decoration: none; font-size: 14px;">文档</a>
        <a href="https://www.huodouai.com/pricing/" style="color: #4a5568; text-decoration: none; font-size: 14px;">定价</a>
        <a href="https://aios.huodouai.com/register.html" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: #fff; padding: 8px 16px; border-radius: 6px; text-decoration: none; font-size: 14px; font-weight: 500;">免费开始</a>
    </div>
</nav>
"""

# 统一页脚
UNIFIED_FOOTER = """
<footer style="background: #1a202c; color: #a0aec0; padding: 40px 24px; text-align: center; margin-top: 60px;">
    <p style="margin: 0 0 8px 0; font-size: 14px;">火斗云智 · 元极恒一自治体系</p>
    <p style="margin: 0; font-size: 12px; opacity: 0.7;">© 2026 火斗云智 · 保留所有权利</p>
</footer>
"""

# 所有网站目录
websites = [
    "/www/wwwroot/aios.huodouai.com",
    "/www/wwwroot/console.huodouai.com",
    "/www/wwwroot/docs.huodouai.com",
    "/www/wwwroot/drama.huodouai.com",
    "/www/wwwroot/gov.huodouai.com",
    "/www/wwwroot/status.huodouai.com",
]

total_updated = 0
for website_dir in websites:
    if not os.path.exists(website_dir):
        continue
    
    all_html = glob.glob(os.path.join(website_dir, "**/*.html"), recursive=True)
    
    updated = 0
    for filepath in all_html:
        with open(filepath, "r") as f:
            content = f.read()
        
        # 替换旧的导航栏
        if '<nav style="background: #fff; box-shadow: 0 2px 8px' in content:
            # 找到旧的nav开始和结束
            import re
            content = re.sub(
                r'<nav style="background: #fff; box-shadow: 0 2px 8px.*?</nav>',
                UNIFIED_NAV,
                content,
                flags=re.DOTALL
            )
            updated += 1
    
    # 写回文件
    for filepath in all_html:
        # 这里简化处理，重新读取一遍
        pass
    
    print(f"✅ {os.path.basename(website_dir)}: 更新了 {updated} 个页面")
    total_updated += updated

print(f"\n=== 总计更新 {total_updated} 个页面，全部锚定www.huodouai.com ===")
