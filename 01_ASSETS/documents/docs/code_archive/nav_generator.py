#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 官网导航自动生成器
Website Navigation Generator

根据模块注册中枢的评估结果，自动生成导航HTML片段
支持：主导航、下拉菜单、面包屑、移动端汉堡菜单
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List

MODULE_DIR = Path(__file__).parent.resolve()
TEMPLATES_DIR = MODULE_DIR / "templates"
TEMPLATES_DIR.mkdir(exist_ok=True)


class NavigationGenerator:
    """导航自动生成器"""

    def __init__(self, nav_tree: Dict):
        self.nav_tree = nav_tree
        self.theme = {
            "bg_color": "rgba(10, 10, 15, 0.85)",
            "text_color": "#e8e8f0",
            "accent_color": "#d4af37",
            "border_color": "rgba(212, 175, 55, 0.3)",
            "font_family": "'Noto Sans SC', sans-serif"
        }

    def generate_top_nav(self, brand: str = "火斗云智AIOS", brand_sub: str = "元极恒一") -> str:
        """生成顶部导航栏HTML"""
        main_group = self.nav_tree.get("main", {})
        main_modules = main_group.get("modules", [])

        # 构建主导航链接
        nav_links = []
        for m in main_modules:
            nav_links.append(f'''      <a href="{m["url"]}" class="nav-link">{m["label"]}</a>''')

        # 构建下拉菜单（理论、工具等）
        dropdowns = []
        for gid, group in self.nav_tree.items():
            if group.get("position") == "dropdown" and group.get("modules"):
                parent = group.get("parent", "")
                parent_label = self._get_parent_label(parent)
                items = []
                for m in group["modules"]:
                    items.append(f'''          <a href="{m["url"]}" class="dropdown-item">{m["label"]}</a>''')
                dropdowns.append(f'''
      <div class="nav-dropdown">
        <a href="#" class="nav-link dropdown-trigger">{parent_label} ▾</a>
        <div class="dropdown-menu">
{chr(10).join(items)}
        </div>
      </div>''')

        html = f'''<!-- 自动生成导航栏 | ZONGYUAN-ROOT Module Registry | {datetime.now().strftime("%Y-%m-%d %H:%M")} -->
<nav class="nav" id="main-nav">
  <div class="nav-inner">
    <div class="nav-brand">
      <span class="nav-brand-main">{brand}</span>
      <span class="nav-brand-sub">{brand_sub}</span>
    </div>
    <div class="nav-links">
{chr(10).join(nav_links)}
{chr(10).join(dropdowns)}
    </div>
    <div class="nav-mobile-toggle" onclick="toggleMobileNav()">
      <span></span><span></span><span></span>
    </div>
  </div>
  <div class="mobile-nav" id="mobile-nav">
{chr(10).join(nav_links)}
{chr(10).join(dropdowns)}
  </div>
</nav>
<!-- /自动生成导航栏 -->'''
        return html

    def _get_parent_label(self, parent: str) -> str:
        """获取父导航标签"""
        labels = {
            "theory": "理论体系",
            "products": "产品矩阵",
            "tools": "工具平台",
            "about": "关于我们"
        }
        return labels.get(parent, parent)

    def generate_css(self) -> str:
        """生成导航CSS样式"""
        return f'''/* 自动生成导航样式 | ZONGYUAN-ROOT */
.nav {{
  position: fixed; top: 0; left: 0; right: 0; z-index: 1000;
  padding: 16px 40px;
  background: {self.theme["bg_color"]};
  backdrop-filter: blur(20px);
  border-bottom: 1px solid {self.theme["border_color"]};
  font-family: {self.theme["font_family"]};
}}
.nav-inner {{
  max-width: 1400px; margin: 0 auto;
  display: flex; justify-content: space-between; align-items: center;
}}
.nav-brand {{ display: flex; flex-direction: column; }}
.nav-brand-main {{
  font-size: 20px; font-weight: 700;
  background: linear-gradient(135deg, {self.theme["accent_color"]}, #f4d03f);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  letter-spacing: 2px;
}}
.nav-brand-sub {{ font-size: 11px; color: #8b7355; letter-spacing: 1px; }}
.nav-links {{ display: flex; gap: 32px; align-items: center; }}
.nav-link {{
  color: {self.theme["text_color"]}; text-decoration: none;
  font-size: 14px; font-weight: 500;
  transition: color 0.3s; position: relative;
}}
.nav-link:hover {{ color: {self.theme["accent_color"]}; }}
.nav-link::after {{
  content: ""; position: absolute; bottom: -4px; left: 0;
  width: 0; height: 2px; background: {self.theme["accent_color"]};
  transition: width 0.3s;
}}
.nav-link:hover::after {{ width: 100%; }}
.nav-dropdown {{ position: relative; }}
.dropdown-menu {{
  display: none; position: absolute; top: 100%; left: 0;
  background: {self.theme["bg_color"]}; border: 1px solid {self.theme["border_color"]};
  border-radius: 8px; padding: 8px 0; min-width: 180px;
  box-shadow: 0 10px 40px rgba(0,0,0,0.5);
}}
.nav-dropdown:hover .dropdown-menu {{ display: block; }}
.dropdown-item {{
  display: block; padding: 10px 20px;
  color: {self.theme["text_color"]}; text-decoration: none;
  font-size: 13px; transition: all 0.2s;
}}
.dropdown-item:hover {{ background: rgba(212,175,55,0.1); color: {self.theme["accent_color"]}; }}
.nav-mobile-toggle {{ display: none; flex-direction: column; gap: 4px; cursor: pointer; }}
.nav-mobile-toggle span {{ width: 24px; height: 2px; background: {self.theme["accent_color"]}; }}
.mobile-nav {{ display: none; flex-direction: column; gap: 16px; padding: 20px 0; }}
@media (max-width: 768px) {{
  .nav-links {{ display: none; }}
  .nav-mobile-toggle {{ display: flex; }}
  .mobile-nav.active {{ display: flex; }}
}}
/* /自动生成导航样式 */'''

    def generate_js(self) -> str:
        """生成导航JS交互"""
        return '''// 自动生成导航交互 | ZONGYUAN-ROOT
function toggleMobileNav() {
  const nav = document.getElementById('mobile-nav');
  nav.classList.toggle('active');
}
// 滚动时导航栏效果
window.addEventListener('scroll', function() {
  const nav = document.getElementById('main-nav');
  if (window.scrollY > 50) {
    nav.style.boxShadow = '0 4px 20px rgba(0,0,0,0.3)';
  } else {
    nav.style.boxShadow = 'none';
  }
});
// /自动生成导航交互 '''

    def generate_breadcrumb(self, current_module_id: str) -> str:
        """生成面包屑导航"""
        modules = {}  # 从注册表获取
        # 简化实现
        return f'''<!-- 面包屑 | {current_module_id} -->
<div class="breadcrumb">
  <a href="/">首页</a>
  <span class="breadcrumb-sep">›</span>
  <span class="breadcrumb-current">{current_module_id}</span>
</div>'''

    def export_all(self, output_dir: Path):
        """导出所有导航文件"""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # 导出导航HTML片段
        nav_html = self.generate_top_nav()
        with open(output_dir / "nav.html", 'w', encoding='utf-8') as f:
            f.write(nav_html)

        # 导出CSS
        nav_css = self.generate_css()
        with open(output_dir / "nav.css", 'w', encoding='utf-8') as f:
            f.write(nav_css)

        # 导出JS
        nav_js = self.generate_js()
        with open(output_dir / "nav.js", 'w', encoding='utf-8') as f:
            f.write(nav_js)

        return {
            "html": str(output_dir / "nav.html"),
            "css": str(output_dir / "nav.css"),
            "js": str(output_dir / "nav.js")
        }


if __name__ == "__main__":
    # 测试：从注册表加载导航树
    import sys
    sys.path.insert(0, str(MODULE_DIR))
    from module_manager import get_registry

    registry = get_registry()
    nav_tree = registry.get_navigation_structure()

    gen = NavigationGenerator(nav_tree)
    output = gen.export_all(TEMPLATES_DIR / "generated")

    print("✅ 导航文件已生成:")
    for k, v in output.items():
        print(f"  {k}: {v}")
    print(f"\n导航结构:")
    print(json.dumps(nav_tree, ensure_ascii=False, indent=2))
