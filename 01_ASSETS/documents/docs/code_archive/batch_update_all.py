
import os
import glob

# 统一导航栏
UNIFIED_NAV = """
<nav style="background: #fff; box-shadow: 0 2px 8px rgba(0,0,0,0.08); padding: 16px 24px; display: flex; align-items: center; justify-content: space-between; position: sticky; top: 0; z-index: 100;">
    <div style="display: flex; align-items: center; gap: 12px;">
        <div style="width: 36px; height: 36px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 8px; display: flex; align-items: center; justify-content: center; color: #fff; font-weight: 700; font-size: 16px;">火</div>
        <span style="font-size: 18px; font-weight: 600; color: #1a202c;">火斗云智AIOS</span>
    </div>
    <div style="display: flex; gap: 24px; align-items: center;">
        <a href="/index.html" style="color: #4a5568; text-decoration: none; font-size: 14px;">首页</a>
        <a href="/tools.html" style="color: #4a5568; text-decoration: none; font-size: 14px;">工具</a>
        <a href="/solutions.html" style="color: #4a5568; text-decoration: none; font-size: 14px;">行业方案</a>
        <a href="/custom-kernel.html" style="color: #4a5568; text-decoration: none; font-size: 14px;">元内核定制</a>
        <a href="/kunlun.html" style="color: #4a5568; text-decoration: none; font-size: 14px;">昆仑洞天</a>
        <a href="/api-pricing.html" style="color: #4a5568; text-decoration: none; font-size: 14px;">定价</a>
        <a href="/register.html" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: #fff; padding: 8px 16px; border-radius: 6px; text-decoration: none; font-size: 14px; font-weight: 500;">免费注册</a>
    </div>
</nav>
"""

# 统一页脚
UNIFIED_FOOTER = """
<footer style="background: #1a202c; color: #a0aec0; padding: 40px 24px; text-align: center; margin-top: 60px;">
    <p style="margin: 0 0 8px 0; font-size: 14px;">火斗云智AIOS · 元极恒一自治体系</p>
    <p style="margin: 0; font-size: 12px; opacity: 0.7;">© 2026 火斗云智 · 保留所有权利</p>
</footer>
"""

website_dir = "/www/wwwroot/aios.huodouai.com"

# 找出所有html文件
all_html = glob.glob(os.path.join(website_dir, "**/*.html"), recursive=True)

updated = 0
skipped = 0
for filepath in all_html:
    filename = os.path.basename(filepath)
    
    # 已经有统一导航的跳过
    with open(filepath, "r") as f:
        content = f.read()
    
    if "火斗云智AIOS" in content and "免费注册" in content:
        skipped += 1
        continue
    
    # 在<body>标签后插入导航
    if "<body>" in content:
        content = content.replace("<body>", "<body>\n" + UNIFIED_NAV, 1)
    
    # 在</body>前插入页脚
    if "</body>" in content:
        content = content.replace("</body>", UNIFIED_FOOTER + "\n</body>", 1)
    
    with open(filepath, "w") as f:
        f.write(content)
    
    updated += 1
    print(f"✅ 已更新: {os.path.relpath(filepath, website_dir)}")

print(f"\n=== 总计 ===")
print(f"总文件数: {len(all_html)}")
print(f"已更新: {updated}")
print(f"已跳过（已有导航）: {skipped}")
