#!/usr/bin/env python3
"""彻底重写导航：删除重复CSS，用一套干净的纯CSS方案"""
import re

INDEX = "/www/wwwroot/www.huodouai.com/index.html"

with open(INDEX, "r", encoding="utf-8") as f:
    content = f.read()

# 1. 删除第一套重复的导航CSS（第474行开始的"重构导航"块）
# 找到第一个"/* ===== 重构导航"到第二个"/* ===== 重构导航"之间的内容
first_nav_start = content.find("/* ===== 重构导航")
if first_nav_start > 0:
    # 找到这个CSS块的结束（下一个.nav-unified{或@media之后）
    # 简单方式：找到第二个"/* ===== 重构导航"或"/* ===== 旧导航"
    second_nav_start = content.find("/* ===== 重构导航", first_nav_start + 10)
    if second_nav_start > 0:
        # 删除第一套（从first到second之前）
        # 但要保留@media (max-width:768px)里的内容
        # 更简单：直接删除第一套完整块
        block_end = content.find("/* ===== 重构导航：8分类", first_nav_start + 10)
        if block_end > 0:
            # 找到这个块的结束（</style>之前或下一个大注释）
            # 找到@media(max-width:900px){...}的结束
            css_block = content[first_nav_start:block_end]
            content = content[:first_nav_start] + content[block_end:]
            print("已删除第一套重复导航CSS")

# 2. 确保checkbox在nav前面
if 'id="navCheck"' not in content:
    content = content.replace('<nav class="nav-unified"', 
        '<input type="checkbox" id="navCheck" style="display:none">\n<nav class="nav-unified"', 1)

# 3. 确保button是label
content = content.replace(
    '<button class="nav-toggle" id="navToggle" aria-label="菜单">\n      <span></span><span></span><span></span>\n    </button>',
    '<label class="nav-toggle" for="navCheck" aria-label="菜单">\n      <span></span><span></span><span></span>\n    </label>'
)

# 4. 在</style>前注入干净的导航CSS（覆盖所有旧样式）
clean_nav_css = """
/* ===== 干净版导航（纯CSS，无JS依赖） ===== */
#navCheck{display:none}
.nav-unified{position:fixed!important;top:0!important;left:0!important;right:0!important;z-index:9999!important;background:rgba(10,10,15,0.95)!important;backdrop-filter:blur(12px);border-bottom:1px solid rgba(212,175,55,0.15);height:52px}
.nav-container{max-width:1200px;margin:0 auto;padding:0 16px;display:flex;align-items:center;justify-content:space-between;height:52px}
.nav-brand{font-size:16px;font-weight:700;background:linear-gradient(135deg,#f4e4bc,#d4af37);-webkit-background-clip:text;-webkit-text-fill-color:transparent;text-decoration:none}
.nav-toggle{display:none;cursor:pointer;padding:8px;background:none;border:none;flex-direction:column;gap:5px}
.nav-toggle span{width:22px;height:2px;background:#d4af37;transition:all .3s;border-radius:2px;display:block}
.nav-menu{display:flex;align-items:center;gap:2px}
.nav-item{position:relative}
.nav-item>a{display:block;padding:8px 10px;color:#bbb;text-decoration:none;font-size:13px;border-radius:6px;white-space:nowrap}
.nav-item>a:hover{color:#d4af37;background:rgba(212,175,55,0.08)}
.nav-item.has-dropdown>a::after{content:" ▾";font-size:10px;opacity:.6}
.dropdown{position:absolute;top:100%;left:0;min-width:170px;background:rgba(15,15,25,0.98);border:1px solid rgba(212,175,55,0.2);border-radius:10px;padding:6px;display:none;z-index:10001;box-shadow:0 8px 32px rgba(0,0,0,0.5)}
.nav-item.has-dropdown:hover .dropdown{display:block}
.dropdown a{display:block;padding:8px 12px;color:#aaa;text-decoration:none;font-size:13px;border-radius:6px}
.dropdown a:hover{color:#d4af37;background:rgba(212,175,55,0.08)}

/* 移动端 */
@media (max-width:900px){
  .nav-toggle{display:flex}
  .nav-menu{position:fixed!important;top:52px!important;left:0!important;right:0!important;bottom:0!important;background:rgba(10,10,15,0.98)!important;flex-direction:column!important;align-items:stretch!important;gap:0!important;padding:10px 16px!important;overflow-y:auto!important;transform:translateX(100%)!important;transition:transform .3s!important;z-index:9998!important;display:flex!important}
  .nav-item>a{padding:14px 12px;font-size:15px;border-bottom:1px solid rgba(255,255,255,0.05)}
  .nav-item.has-dropdown>a::after{content:" +";font-size:18px;float:right}
  .dropdown{position:static!important;display:none!important;background:transparent!important;border:none!important;box-shadow:none!important;padding:0 0 0 20px!important}
  .nav-item.has-dropdown:active .dropdown{display:block!important}
  .nav-item.has-dropdown:focus-within .dropdown{display:block!important}
}

/* checkbox控制菜单显示 */
#navCheck:checked ~ .nav-unified .nav-menu{transform:translateX(0)!important}
#navCheck:checked ~ .nav-unified .nav-toggle span:nth-child(1){transform:rotate(45deg) translate(5px,5px)}
#navCheck:checked ~ .nav-unified .nav-toggle span:nth-child(2){opacity:0}
#navCheck:checked ~ .nav-unified .nav-toggle span:nth-child(3){transform:rotate(-45deg) translate(7px,-6px)}

body{padding-top:52px!important}
@media (max-width:900px){body{padding-top:52px!important}}
"""

last_style = content.rfind("</style>")
content = content[:last_style] + clean_nav_css + content[last_style:]

# 5. 删除旧的JS导航代码（如果有）
js_start = content.find("// ===== 移动端导航交互 =====")
if js_start > 0:
    js_end = content.find("// 平滑滚动", js_start)
    if js_end > 0:
        content = content[:js_start] + content[js_end:]

with open(INDEX, "w", encoding="utf-8") as f:
    f.write(content)

print("导航已彻底重写为干净纯CSS方案")
