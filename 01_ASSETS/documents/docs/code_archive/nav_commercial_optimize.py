#!/usr/bin/env python3
# 导航商业化优化脚本
file_path = "/www/wwwroot/huodouai.com/index.html"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. 在产品矩阵下拉中添加"客户案例"链接
old_pricing = '          <a href="/commercial.html">商业方案</a>\n          <a href="/pricing.html">定价</a>'
new_pricing = '          <a href="/commercial.html">商业方案</a>\n          <a href="/cases.html">客户案例</a>\n          <a href="/pricing.html">定价</a>'

if old_pricing in content:
    content = content.replace(old_pricing, new_pricing)
    print("✅ 已添加客户案例到产品矩阵下拉")
else:
    print("⚠️ 未找到产品矩阵下拉的pricing位置")
    if '<a href="/commercial.html">商业方案</a>' in content:
        content = content.replace(
            '<a href="/commercial.html">商业方案</a>',
            '<a href="/commercial.html">商业方案</a>\n          <a href="/cases.html">客户案例</a>'
        )
        print("✅ 已通过备用方式添加客户案例")

# 2. 在导航右侧添加CTA按钮
cta_html = '''      <div class="nav-cta" style="display:flex;align-items:center;gap:12px;margin-left:20px;">
        <a href="/cases.html" style="color:#bbb;text-decoration:none;font-size:13.5px;transition:color .2s;white-space:nowrap;" onmouseover="this.style.color='#d4af37'" onmouseout="this.style.color='#bbb'">客户案例</a>
        <a href="/book-demo.html" style="background:linear-gradient(135deg,#d4af37,#b8941f);color:#1a1a2e;padding:8px 20px;border-radius:8px;text-decoration:none;font-size:13.5px;font-weight:600;transition:all .2s;white-space:nowrap;box-shadow:0 4px 15px rgba(212,175,55,0.3);" onmouseover="this.style.transform='translateY(-2px)';this.style.boxShadow='0 6px 20px rgba(212,175,55,0.4)'" onmouseout="this.style.transform='translateY(0)';this.style.boxShadow='0 4px 15px rgba(212,175,55,0.3)'">预约演示</a>
      </div>
'''

# 找到nav-menu结束位置
old_nav_end = '        </div>\n      </div>\n    </div>\n  </div>\n</nav>'
new_nav_end = '        </div>\n      </div>\n' + cta_html + '    </div>\n  </div>\n</nav>'

if old_nav_end in content:
    content = content.replace(old_nav_end, new_nav_end)
    print("✅ 已添加预约演示CTA按钮到导航右侧")
else:
    print("⚠️ 未找到导航结束位置，尝试备用方式")
    idx = content.rfind("</nav>")
    if idx > 0:
        before_nav = content[:idx]
        menu_end = before_nav.rfind("</div>\n    </div>\n  </div>")
        if menu_end > 0:
            content = content[:menu_end] + cta_html + content[menu_end:]
            print("✅ 已通过备用方式添加CTA按钮")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("\n✅ 导航商业化优化完成！")
print("  - 客户案例已添加到产品矩阵下拉")
print("  - 预约演示CTA按钮已添加到导航右侧")
