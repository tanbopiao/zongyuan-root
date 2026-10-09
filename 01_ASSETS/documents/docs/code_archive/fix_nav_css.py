#!/usr/bin/env python3
"""用纯CSS checkbox方案重写移动端导航，不依赖JS"""
import re

INDEX = "/www/wwwroot/www.huodouai.com/index.html"

with open(INDEX, "r", encoding="utf-8") as f:
    content = f.read()

# 1. 在nav前添加checkbox
old_nav = '<nav class="nav-unified" id="mainNav">'
new_nav = '''<input type="checkbox" id="navCheck" style="display:none">
<nav class="nav-unified" id="mainNav">'''
content = content.replace(old_nav, new_nav, 1)

# 2. 把button改成label
old_button = '''    <button class="nav-toggle" id="navToggle" aria-label="菜单">
      <span></span><span></span><span></span>
    </button>'''
new_button = '''    <label class="nav-toggle" for="navCheck" aria-label="菜单">
      <span></span><span></span><span></span>
    </label>'''
content = content.replace(old_button, new_button, 1)

# 3. 在</style>前添加纯CSS导航控制（覆盖之前的JS依赖）
pure_css = """
/* ===== 纯CSS移动端导航（checkbox方案，不依赖JS） ===== */
#navCheck:checked ~ .nav-unified .nav-menu {
  transform: translateX(0) !important;
  visibility: visible !important;
}
#navCheck:checked ~ .nav-unified .nav-toggle span:nth-child(1) {
  transform: rotate(45deg) translate(5px, 5px);
}
#navCheck:checked ~ .nav-unified .nav-toggle span:nth-child(2) {
  opacity: 0;
}
#navCheck:checked ~ .nav-unified .nav-toggle span:nth-child(3) {
  transform: rotate(-45deg) translate(7px, -6px);
}
/* 移动端下拉菜单：用checkbox嵌套太复杂，改用target+hover兼容 */
@media (max-width: 900px) {
  .nav-item.has-dropdown > a::after { content: " +"; font-size: 16px; }
  .nav-item.has-dropdown:active .dropdown,
  .nav-item.has-dropdown:focus .dropdown { display: block; }
  .dropdown { display: none; }
  .nav-item.has-dropdown .dropdown { display: none; }
  .nav-item.has-dropdown:active .dropdown,
  .nav-item.has-dropdown:focus-within .dropdown { display: block; }
}
"""

last_style = content.rfind("</style>")
content = content[:last_style] + pure_css + content[last_style:]

# 4. 移除之前注入的JS导航代码（保留平滑滚动）
# 找到我们注入的导航JS块并删除
nav_js_start = content.find("// ===== 移动端导航交互 =====")
if nav_js_start > 0:
    nav_js_end = content.find("// 平滑滚动", nav_js_start)
    if nav_js_end > 0:
        content = content[:nav_js_start] + content[nav_js_end:]

with open(INDEX, "w", encoding="utf-8") as f:
    f.write(content)

print("纯CSS导航方案已应用")
