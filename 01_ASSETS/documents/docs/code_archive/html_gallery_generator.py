"""
HTML画廊生成器 - 生成可视化的设计参考画廊页面
"""
import os
import json
from datetime import datetime
from typing import Dict, List, Any

class HTMLGalleryGenerator:
    """HTML画廊生成器"""
    
    def __init__(self, output_dir: str = "./output"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def generate_gallery(self, collected_data: List[Dict], 
                          analysis_data: List[Dict],
                          knowledge_summary: Dict,
                          title: str = "AI网页设计参考画廊") -> str:
        """生成HTML画廊页面"""
        
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0a0a0f;
            color: #e0e0e0;
            line-height: 1.6;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; padding: 40px 20px; }}
        header {{
            text-align: center;
            margin-bottom: 60px;
            padding: 60px 20px;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            border-radius: 20px;
            margin-bottom: 40px;
        }}
        h1 {{
            font-size: 3em;
            background: linear-gradient(135deg, #00d4ff, #7b2ff7);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 10px;
        }}
        .subtitle {{ color: #888; font-size: 1.1em; }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 60px;
        }}
        .stat-card {{
            background: linear-gradient(135deg, #1a1a2e, #16213e);
            padding: 30px;
            border-radius: 15px;
            text-align: center;
            border: 1px solid #2a2a4a;
        }}
        .stat-number {{
            font-size: 2.5em;
            font-weight: bold;
            background: linear-gradient(135deg, #00d4ff, #7b2ff7);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .stat-label {{ color: #888; margin-top: 5px; }}
        .section {{ margin-bottom: 60px; }}
        .section-title {{
            font-size: 1.8em;
            margin-bottom: 30px;
            padding-bottom: 15px;
            border-bottom: 2px solid #2a2a4a;
            color: #00d4ff;
        }}
        .gallery-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 25px;
        }}
        .gallery-card {{
            background: linear-gradient(135deg, #1a1a2e, #16213e);
            border-radius: 15px;
            overflow: hidden;
            border: 1px solid #2a2a4a;
            transition: transform 0.3s, box-shadow 0.3s;
        }}
        .gallery-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 10px 40px rgba(0, 212, 255, 0.2);
        }}
        .card-header {{
            padding: 20px;
            background: linear-gradient(135deg, #0f3460, #16213e);
        }}
        .card-title {{ font-size: 1.2em; font-weight: bold; margin-bottom: 5px; }}
        .card-url {{ color: #00d4ff; font-size: 0.85em; word-break: break-all; }}
        .card-body {{ padding: 20px; }}
        .card-section {{ margin-bottom: 15px; }}
        .card-section-title {{
            font-size: 0.85em;
            color: #888;
            text-transform: uppercase;
            margin-bottom: 8px;
            letter-spacing: 1px;
        }}
        .color-palette {{ display: flex; gap: 8px; flex-wrap: wrap; }}
        .color-swatch {{
            width: 35px;
            height: 35px;
            border-radius: 8px;
            border: 2px solid #333;
        }}
        .tag {{
            display: inline-block;
            padding: 4px 12px;
            background: rgba(0, 212, 255, 0.1);
            color: #00d4ff;
            border-radius: 20px;
            font-size: 0.8em;
            margin: 3px;
        }}
        .score {{
            display: inline-block;
            padding: 5px 15px;
            background: linear-gradient(135deg, #00d4ff, #7b2ff7);
            color: #000;
            border-radius: 20px;
            font-weight: bold;
            font-size: 0.9em;
        }}
        .trends-list {{ display: flex; flex-wrap: wrap; gap: 10px; }}
        .trend-item {{
            padding: 8px 16px;
            background: rgba(123, 47, 247, 0.1);
            border: 1px solid #7b2ff7;
            border-radius: 25px;
            color: #b388ff;
        }}
        footer {{
            text-align: center;
            padding: 40px;
            color: #666;
            border-top: 1px solid #2a2a4a;
            margin-top: 60px;
        }}
        .ai-badge {{
            display: inline-block;
            padding: 3px 10px;
            background: linear-gradient(135deg, #ff6b6b, #ee5a24);
            color: white;
            border-radius: 15px;
            font-size: 0.75em;
            margin-left: 8px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>{title}</h1>
            <p class="subtitle">全自动采集 · 智能分析 · 知识沉淀 · 设计参考库</p>
            <p style="color: #666; margin-top: 10px;">生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </header>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number">{len(collected_data)}</div>
                <div class="stat-label">采集网站</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{len(analysis_data)}</div>
                <div class="stat-label">分析报告</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{knowledge_summary.get('stats', {}).get('total_entries', 0)}</div>
                <div class="stat-label">知识条目</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{len(knowledge_summary.get('design_trends', []))}</div>
                <div class="stat-label">设计趋势</div>
            </div>
        </div>

        <div class="section">
            <h2 class="section-title">🔥 热门设计趋势</h2>
            <div class="trends-list">
"""
        
        # 添加趋势
        for trend in knowledge_summary.get('design_trends', [])[:15]:
            html += f'                <span class="trend-item">{trend.get("name", "")} ({trend.get("count", 0)})</span>\n'
        
        html += """            </div>
        </div>

        <div class="section">
            <h2 class="section-title">🎨 热门配色方案</h2>
            <div class="gallery-grid">
"""
        
        # 添加配色
        for palette in knowledge_summary.get('top_color_palettes', [])[:6]:
            colors = palette.get('colors', [])[:6]
            color_html = ''.join([f'<div class="color-swatch" style="background: {c};"></div>' for c in colors])
            html += f"""                <div class="gallery-card">
                    <div class="card-header">
                        <div class="card-title">{palette.get('title', 'Unknown')[:40]}</div>
                    </div>
                    <div class="card-body">
                        <div class="card-section">
                            <div class="card-section-title">配色方案</div>
                            <div class="color-palette">{color_html}</div>
                        </div>
                    </div>
                </div>
"""
        
        html += """            </div>
        </div>

        <div class="section">
            <h2 class="section-title">📐 网站设计参考画廊</h2>
            <div class="gallery-grid">
"""
        
        # 添加网站卡片
        for i, (collected, analysis) in enumerate(zip(collected_data[:12], analysis_data[:12])):
            colors = collected.get('colors', [])[:6]
            color_html = ''.join([f'<div class="color-swatch" style="background: {c};"></div>' for c in colors])
            
            fonts = collected.get('fonts', [])[:3]
            font_html = ''.join([f'<span class="tag">{f}</span>' for f in fonts])
            
            trends = analysis.get('design_trends', [])[:5]
            trend_html = ''.join([f'<span class="tag">{t}</span>' for t in trends])
            
            ai_elements = collected.get('ai_elements', [])
            ai_badge = '<span class="ai-badge">AI设计</span>' if ai_elements else ''
            
            score = analysis.get('overall_design_score', 0)
            
            html += f"""                <div class="gallery-card">
                    <div class="card-header">
                        <div class="card-title">{collected.get('title', 'Unknown')[:50]}{ai_badge}</div>
                        <div class="card-url">{collected.get('url', '')}</div>
                    </div>
                    <div class="card-body">
                        <div class="card-section">
                            <div class="card-section-title">设计评分</div>
                            <span class="score">{score}/1.0</span>
                        </div>
                        <div class="card-section">
                            <div class="card-section-title">配色方案</div>
                            <div class="color-palette">{color_html}</div>
                        </div>
                        <div class="card-section">
                            <div class="card-section-title">字体</div>
                            {font_html}
                        </div>
                        <div class="card-section">
                            <div class="card-section-title">设计趋势</div>
                            {trend_html}
                        </div>
                    </div>
                </div>
"""
        
        html += f"""            </div>
        </div>

        <footer>
            <p>🤖 由AI网页设计参考采集学习系统自动生成</p>
            <p>Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | ZONGYUAN-ROOT元极恒一自治体系</p>
            <p style="margin-top: 10px; color: #444;">火斗云智AIOS · 网页设计参考库</p>
        </footer>
    </div>
</body>
</html>"""
        
        output_file = os.path.join(self.output_dir, f'design_gallery_{datetime.now().strftime("%Y%m%d_%H%M%S")}.html')
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)
        
        return output_file

# 单例
_gallery_generator = None

def get_gallery_generator(output_dir: str = None) -> HTMLGalleryGenerator:
    """获取画廊生成器单例"""
    global _gallery_generator
    if _gallery_generator is None:
        _gallery_generator = HTMLGalleryGenerator(output_dir or "./output")
    return _gallery_generator

if __name__ == "__main__":
    print("HTML画廊生成器初始化完成")
