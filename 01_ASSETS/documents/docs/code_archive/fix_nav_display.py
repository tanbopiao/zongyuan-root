#!/usr/bin/env python3
"""导航终极修复：用display控制，不用transform"""
import re

INDEX = "/www/wwwroot/www.huodouai.com/index.html"

with open(INDEX, "r", encoding="utf-8") as f:
    content = f.read()

# 找到干净版导航CSS块，替换移动端菜单的显示方式
old_mobile = """.nav-menu{position:fixed!important;top:52px!important;left:0!important;right:0!important;bottom:0!important;background:rgba(10,10,15,0.98)!important;flex-direction:column!important;align-items:stretch!important;gap:0!important;padding:10px 16px!important;overflow-y:auto!important;transform:translateX(100%)!important;transition:transform .3s!important;z-index:9998!important;display:flex!important}"""

new_mobile = """.nav-menu{position:fixed!important;top:52px!important;left:0!important;right:0!important;bottom:0!important;background:rgba(10,10,15,0.98)!important;flex-direction:column!important;align-items:stretch!important;gap:0!important;padding:10px 16px!important;overflow-y:auto!important;z-index:9998!important;display:none!important}"""

content = content.replace(old_mobile, new_mobile)

# 替换checkbox控制方式：从transform改为display
old_checked = "#navCheck:checked ~ .nav-unified .nav-menu{transform:translateX(0)!important}"
new_checked = "#navCheck:checked ~ .nav-unified .nav-menu{display:flex!important}"
content = content.replace(old_checked, new_checked)

with open(INDEX, "w", encoding="utf-8") as f:
    f.write(content)

print("导航已改为display控制方案")
