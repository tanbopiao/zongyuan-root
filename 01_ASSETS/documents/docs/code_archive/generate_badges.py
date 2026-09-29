#!/usr/bin/env python3
"""
EMMS工程化落地成熟度评级徽章生成器
生成E0-E7八个等级的SVG徽章
"""
import os

# 八级定义
LEVELS = [
    {"level": "E0", "name": "概念级", "color": "#9ca3af", "desc": "仅有概念和理论，无实际实现"},
    {"level": "E1", "name": "原型级", "color": "#94a3b8", "desc": "有原型实现，但不可用于生产"},
    {"level": "E2", "name": "Demo级", "color": "#f59e0b", "desc": "可演示的Demo，功能不完整"},
    {"level": "E3", "name": "试用级", "color": "#eab308", "desc": "可试用，有基本功能但不稳定"},
    {"level": "E4", "name": "可用级", "color": "#a3e635", "desc": "可正常使用，功能基本完整"},
    {"level": "E5", "name": "生产级", "color": "#10b981", "desc": "可用于生产环境，稳定可靠"},
    {"level": "E6", "name": "企业级", "color": "#3b82f6", "desc": "企业级标准，支持大规模部署"},
    {"level": "E7", "name": "生态级", "color": "#8b5cf6", "desc": "形成生态，有社区和商业支持"},
]

def generate_badge(level_info, output_dir="badges"):
    """生成单个等级的SVG徽章"""
    level = level_info["level"]
    name = level_info["name"]
    color = level_info["color"]
    
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="200" height="60" viewBox="0 0 200 60">
  <defs>
    <linearGradient id="grad_{level}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{color};stop-opacity:1" />
      <stop offset="100%" style="stop-color:{color};stop-opacity:0.7" />
    </linearGradient>
  </defs>
  <rect x="0" y="0" width="200" height="60" rx="8" fill="#0a0e17" stroke="{color}" stroke-width="2"/>
  <rect x="0" y="0" width="60" height="60" rx="8" fill="url(#grad_{level})"/>
  <text x="30" y="38" font-family="Arial, sans-serif" font-size="24" font-weight="bold" fill="#000" text-anchor="middle">{level}</text>
  <text x="125" y="28" font-family="Arial, sans-serif" font-size="14" font-weight="bold" fill="{color}" text-anchor="middle">EMMS评级</text>
  <text x="125" y="48" font-family="Arial, sans-serif" font-size="16" font-weight="bold" fill="#e5e7eb" text-anchor="middle">{name}</text>
</svg>'''
    
    filepath = os.path.join(output_dir, f"emms-badge-{level.lower()}.svg")
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(svg)
    return filepath

def generate_html_preview(output_dir="badges"):
    """生成HTML预览页面"""
    html = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>EMMS评级徽章预览</title>
<style>
body{font-family:Arial,sans-serif;background:#0a0e17;color:#e5e7eb;padding:40px;max-width:900px;margin:0 auto}
h1{text-align:center;margin-bottom:40px}
.badge-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:30px}
.badge-item{text-align:center;padding:20px;background:#111827;border-radius:12px;border:1px solid #1f2937}
.badge-item img{margin-bottom:15px}
.badge-item .level{font-size:1.2rem;font-weight:bold;margin-bottom:5px}
.badge-item .desc{font-size:.85rem;color:#9ca3af}
</style>
</head>
<body>
<h1>EMMS工程化落地成熟度评级徽章</h1>
<div class="badge-grid">
'''
    
    for level_info in LEVELS:
        level = level_info["level"]
        name = level_info["name"]
        color = level_info["color"]
        desc = level_info["desc"]
        html += f'''  <div class="badge-item">
    <img src="emms-badge-{level.lower()}.svg" alt="{level} {name}">
    <div class="level" style="color:{color}">{level} {name}</div>
    <div class="desc">{desc}</div>
  </div>
'''
    
    html += '''</div>
</body>
</html>'''
    
    filepath = os.path.join(output_dir, "index.html")
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html)
    return filepath

def main():
    output_dir = "badges"
    os.makedirs(output_dir, exist_ok=True)
    
    print("EMMS评级徽章生成器")
    print("=" * 40)
    
    generated = []
    for level_info in LEVELS:
        filepath = generate_badge(level_info, output_dir)
        generated.append(filepath)
        print(f"  ✅ {level_info['level']} {level_info['name']}: {filepath}")
    
    preview = generate_html_preview(output_dir)
    print(f"  ✅ HTML预览: {preview}")
    
    print()
    print(f"共生成 {len(generated)} 个徽章 + 1个预览页面")
    print(f"输出目录: {output_dir}/")

if __name__ == "__main__":
    main()
