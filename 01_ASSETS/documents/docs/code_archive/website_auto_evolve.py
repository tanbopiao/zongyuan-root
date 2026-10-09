
#!/usr/bin/env python3
"""
火斗云智AIOS 网页全自动进化机制
定时扫描所有域名所有页面，自动修复+优化+上报
"""
import os
import glob
import re
import requests
from datetime import datetime

GATEWAY_URL = "http://127.0.0.1:9120/api/truth/upsert"
ANCHOR_URL = "https://www.huodouai.com"

UNIFIED_NAV = f"""
<nav style="background: #fff; box-shadow: 0 2px 8px rgba(0,0,0,0.08); padding: 16px 24px; display: flex; align-items: center; justify-content: space-between; position: sticky; top: 0; z-index: 100;">
    <div style="display: flex; align-items: center; gap: 12px;">
        <div style="width: 36px; height: 36px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 8px; display: flex; align-items: center; justify-content: center; color: #fff; font-weight: 700; font-size: 16px;">火</div>
        <span style="font-size: 18px; font-weight: 600; color: #1a202c;">火斗云智</span>
    </div>
    <div style="display: flex; gap: 24px; align-items: center;">
        <a href="{ANCHOR_URL}/" style="color: #4a5568; text-decoration: none; font-size: 14px;">首页</a>
        <a href="{ANCHOR_URL}/products/" style="color: #4a5568; text-decoration: none; font-size: 14px;">产品</a>
        <a href="{ANCHOR_URL}/solutions/" style="color: #4a5568; text-decoration: none; font-size: 14px;">解决方案</a>
        <a href="{ANCHOR_URL}/docs/" style="color: #4a5568; text-decoration: none; font-size: 14px;">文档</a>
        <a href="{ANCHOR_URL}/pricing/" style="color: #4a5568; text-decoration: none; font-size: 14px;">定价</a>
        <a href="https://aios.huodouai.com/register.html" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: #fff; padding: 8px 16px; border-radius: 6px; text-decoration: none; font-size: 14px; font-weight: 500;">免费开始</a>
    </div>
</nav>
"""

UNIFIED_FOOTER = """
<footer style="background: #1a202c; color: #a0aec0; padding: 40px 24px; text-align: center; margin-top: 60px;">
    <p style="margin: 0 0 8px 0; font-size: 14px;">火斗云智 · 元极恒一自治体系</p>
    <p style="margin: 0; font-size: 12px; opacity: 0.7;">© 2026 火斗云智 · 保留所有权利</p>
</footer>
"""

websites = [
    "/www/wwwroot/huodouai.com",
    "/www/wwwroot/aios.huodouai.com",
    "/www/wwwroot/gov.huodouai.com",
    "/www/wwwroot/console.huodouai.com",
    "/www/wwwroot/docs.huodouai.com",
    "/www/wwwroot/status.huodouai.com",
]

def evolve_website(website_dir):
    all_html = glob.glob(os.path.join(website_dir, "**/*.html"), recursive=True)
    fixed = 0
    
    for filepath in all_html:
        with open(filepath, "r") as f:
            content = f.read()
        
        original = content
        
        # 修复1：没有统一导航的，加上
        if "火斗云智" not in content and "免费开始" not in content:
            if "<body>" in content:
                content = content.replace("<body>", "<body>\n" + UNIFIED_NAV, 1)
        
        # 修复2：没有统一页脚的，加上
        if "火斗云智 · 元极恒一自治体系" not in content:
            if "</body>" in content:
                content = content.replace("</body>", UNIFIED_FOOTER + "\n</body>", 1)
        
        # 修复3：旧的相对路径导航，替换成锚定主站的
        if '<nav style="background: #fff; box-shadow: 0 2px 8px' in content:
            content = re.sub(
                r'<nav style="background: #fff; box-shadow: 0 2px 8px.*?</nav>',
                UNIFIED_NAV,
                content,
                flags=re.DOTALL
            )
        
        if content != original:
            with open(filepath, "w") as f:
                f.write(content)
            fixed += 1
    
    return len(all_html), fixed

def report_result(total, fixed):
    payload = {
        "key": f"WEBSITE.AUTO-EVOLVE.{datetime.now().strftime('%Y%m%d%H%M')}",
        "value": f"网页自动进化：扫描{total}个页面，修复{fixed}个",
        "metadata": {
            "total_pages": total,
            "fixed_pages": fixed,
            "anchor": ANCHOR_URL
        }
    }
    
    try:
        requests.post(GATEWAY_URL, json=payload, timeout=10)
        print(f"[{datetime.now()}] ✅ 自动进化上报成功")
    except Exception as e:
        print(f"[{datetime.now()}] ❌ 自动进化上报失败: {e}")

def main():
    print("=" * 50)
    print("火斗云智AIOS 网页全自动进化机制启动")
    print("=" * 50)
    
    total_pages = 0
    total_fixed = 0
    
    for website_dir in websites:
        if not os.path.exists(website_dir):
            continue
        
        site_name = os.path.basename(website_dir)
        total, fixed = evolve_website(website_dir)
        print(f"✅ {site_name}: 扫描{total}页，修复{fixed}页")
        
        total_pages += total
        total_fixed += fixed
    
    print(f"\n=== 总计 ===")
    print(f"总扫描: {total_pages} 页")
    print(f"总修复: {total_fixed} 页")
    
    report_result(total_pages, total_fixed)

if __name__ == "__main__":
    main()
