#!/usr/bin/env python3
"""修复生成台账页面"""
import json, os

LEDGER_PATH = "/opt/ZONGYUAN-ROOT/data/change_ledger.json"
WWW_ROOT = "/www/wwwroot/www.huodouai.com"

with open(LEDGER_PATH) as f:
    LEDGER = json.load(f)

entries_html = ""
for e in LEDGER["entries"]:
    status_color = "#4ade80" if e["status"] == "verified" else "#fbbf24"
    url_link = e.get("url", "—")
    if url_link != "—":
        url_link = '<a href="' + url_link + '" style="color:#d4af37;text-decoration:none">' + url_link + "</a>"
    impact = "、".join(e["impact"])
    entries_html += (
        '<div style="background:rgba(0,0,0,0.2);border-radius:8px;padding:14px;margin-bottom:10px;border-left:3px solid #d4af37">'
        '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">'
        '<span style="color:#d4af37;font-weight:bold;font-size:0.9em">' + e["title"] + '</span>'
        '<span style="color:' + status_color + ';font-size:0.75em">' + e["status"] + '</span>'
        '</div>'
        '<div style="color:#ddd;font-size:0.88em;margin-bottom:6px">' + e["content"] + '</div>'
        '<div style="color:#666;font-size:0.72em;margin-top:6px">影响: ' + impact + ' | 链接: ' + url_link + '</div>'
        '</div>'
    )

services_html = ""
for port, desc in LEDGER["active_services"].items():
    services_html += (
        '<div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.05)">'
        '<span style="color:#d4af37;font-family:monospace">:' + port + '</span>'
        '<span style="color:#aaa;font-size:0.85em">' + desc + '</span>'
        '</div>'
    )

rules_html = ""
for k, v in LEDGER["deployment_rules"].items():
    rules_html += (
        '<div style="padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.05)">'
        '<strong style="color:#d4af37;font-size:0.85em">' + k + '</strong>'
        '<div style="color:#aaa;font-size:0.8em;margin-top:3px">' + v + '</div>'
        '</div>'
    )

html = (
    '<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">'
    '<meta name="viewport" content="width=device-width,initial-scale=1">'
    '<title>变更台账 · 火斗云智AIOS</title>'
    '<link rel="stylesheet" href="https://miaoda.feishu.cn/fonts/css2?family=Noto+Serif+SC:wght@400;700;900&family=Noto+Sans+SC:wght@300;400;500;700&display=swap">'
    '<style>*{margin:0;padding:0;box-sizing:border-box}body{background:#0a0a0f;color:#e0e0e0;font-family:"Noto Sans SC",sans-serif}.wrap{max-width:1000px;margin:0 auto;padding:40px 20px}.back{color:#d4af37;text-decoration:none;font-size:0.9em}.hero{text-align:center;padding:20px 0 30px}.hero h1{font-family:"Noto Serif SC",serif;font-size:2em;background:linear-gradient(135deg,#f4e4bc,#d4af37);-webkit-background-clip:text;-webkit-text-fill-color:transparent}.hero .sub{color:#888;font-size:0.85em;margin-top:8px}.section{margin:25px 0}.section h2{font-family:"Noto Serif SC",serif;color:#d4af37;font-size:1.2em;margin-bottom:14px;padding-left:12px;border-left:3px solid #d4af37}.card{background:linear-gradient(145deg,#1a1a2e,#16213e);border:1px solid rgba(212,175,55,0.1);border-radius:12px;padding:18px}footer{text-align:center;margin-top:30px;padding-top:16px;border-top:1px solid rgba(212,175,55,0.1);color:#666;font-size:0.78em}footer .did{color:#d4af37;font-family:monospace;margin-top:5px}</style>'
    '</head><body><div class="wrap">'
    '<a href="/" class="back">← 返回首页</a>'
    '<div class="hero"><h1>系统变更台账</h1><div class="sub">所有开发端口必读 · 避免重复试错 · 最后更新: ' + LEDGER["last_updated"] + '</div></div>'
    '<div class="section"><h2>📋 变更记录（' + str(len(LEDGER["entries"])) + '条）</h2><div class="card">' + entries_html + '</div></div>'
    '<div class="section"><h2>🔧 活跃服务</h2><div class="card">' + services_html + '</div></div>'
    '<div class="section"><h2>📏 部署铁律</h2><div class="card">' + rules_html + '</div></div>'
    '</div><footer>火斗云智AIOS · 变更台账V1.0<div class="did">Ω₀⊂⊙∞⊂Ω · DID-BR-000002 · 全域同步 · 避免试错</div></footer>'
    '</body></html>'
)

page_path = os.path.join(WWW_ROOT, "change-ledger.html")
with open(page_path, "w") as f:
    f.write(html)
os.system("cp " + page_path + " /www/wwwroot/huodouai.com/change-ledger.html")
print("✅ 台账页面已重新生成:", len(html), "bytes")
