"""
网页设计分析引擎 - 深度分析设计模式
包括配色分析、排版分析、布局分析、交互模式分析、AI设计元素分析
"""
import os
import sys
import json
import re
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from collections import Counter

@dataclass
class ColorPalette:
    """配色方案"""
    primary: str = ""
    secondary: str = ""
    accent: str = ""
    background: str = ""
    text: str = ""
    all_colors: List[str] = field(default_factory=list)
    color_scheme_type: str = ""  # monochromatic/analogous/complementary/triadic
    accessibility_score: float = 0.0

@dataclass
class TypographyProfile:
    """排版配置"""
    heading_font: str = ""
    body_font: str = ""
    mono_font: str = ""
    font_scale: str = ""  # modular_scale/golden_ratio/custom
    heading_sizes: List[int] = field(default_factory=list)
    line_height: float = 1.6
    letter_spacing: str = "normal"

@dataclass
class LayoutProfile:
    """布局配置"""
    layout_type: str = ""  # grid/flexbox/mixed
    grid_columns: int = 12
    max_width: str = "1200px"
    spacing_system: str = ""  # 4px/8px/12px base
    breakpoints: Dict[str, str] = field(default_factory=dict)
    component_patterns: List[str] = field(default_factory=list)

@dataclass
class InteractionPattern:
    """交互模式"""
    pattern_name: str = ""
    description: str = ""
    implementation: str = ""
    ai_relevance: float = 0.0

@dataclass
class DesignAnalysisReport:
    """设计分析报告"""
    url: str
    title: str
    analyzed_at: str
    color_palette: ColorPalette = field(default_factory=ColorPalette)
    typography: TypographyProfile = field(default_factory=TypographyProfile)
    layout: LayoutProfile = field(default_factory=LayoutProfile)
    interactions: List[InteractionPattern] = field(default_factory=list)
    ai_design_elements: List[str] = field(default_factory=list)
    overall_design_score: float = 0.0
    design_trends: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

class DesignAnalyzer:
    """设计分析引擎"""
    
    def __init__(self):
        self.color_theories = self._init_color_theories()
        self.design_trends_db = self._init_design_trends()
    
    def _init_color_theories(self) -> Dict:
        """初始化色彩理论知识库"""
        return {
            'monochromatic': '单色配色 - 使用同一色相的不同明度和饱和度',
            'analogous': '类比配色 - 使用色轮上相邻的颜色',
            'complementary': '互补配色 - 使用色轮上相对的颜色',
            'triadic': '三角配色 - 使用色轮上等距的三种颜色',
            'tetradic': '四方配色 - 使用色轮上两对互补色',
            'neutral': '中性配色 - 以黑白灰为主，点缀色为辅',
            'gradient': '渐变配色 - 使用渐变色作为主视觉'
        }
    
    def _init_design_trends(self) -> List[Dict]:
        """初始化设计趋势数据库"""
        return [
            {'name': 'glassmorphism', 'description': '玻璃拟态 - 半透明模糊背景', 'year': 2024, 'popularity': 0.85},
            {'name': 'neumorphism', 'description': '新拟态 - 柔和的内阴影和外阴影', 'year': 2023, 'popularity': 0.6},
            {'name': 'brutalism', 'description': '粗野主义 - 原始、大胆、高对比度', 'year': 2024, 'popularity': 0.7},
            {'name': 'minimalism', 'description': '极简主义 - 少即是多', 'year': 2024, 'popularity': 0.95},
            {'name': 'dark_mode', 'description': '暗色模式 - 深色背景为主', 'year': 2024, 'popularity': 0.9},
            {'name': 'gradients', 'description': '渐变色彩 - 丰富的渐变色', 'year': 2024, 'popularity': 0.88},
            {'name': '3d_elements', 'description': '3D元素 - 三维图形和动画', 'year': 2024, 'popularity': 0.75},
            {'name': 'micro_interactions', 'description': '微交互 - 精细的交互动画', 'year': 2024, 'popularity': 0.92},
            {'name': 'ai_generated', 'description': 'AI生成设计 - AI辅助的设计元素', 'year': 2024, 'popularity': 0.8},
            {'name': 'bento_grid', 'description': '便当盒网格 - 模块化卡片布局', 'year': 2024, 'popularity': 0.82},
            {'name': 'typography_centric', 'description': '排版为中心 - 大字体主导视觉', 'year': 2024, 'popularity': 0.78},
            {'name': 'custom_cursors', 'description': '自定义光标 - 独特的鼠标指针', 'year': 2024, 'popularity': 0.65},
            {'name': 'scroll_animations', 'description': '滚动动画 - 滚动触发的动画效果', 'year': 2024, 'popularity': 0.85},
            {'name': 'asymmetric_layouts', 'description': '不对称布局 - 打破传统网格', 'year': 2024, 'popularity': 0.7},
            {'name': 'organic_shapes', 'description': '有机形状 - 自然流畅的曲线', 'year': 2024, 'popularity': 0.72}
        ]
    
    def analyze_colors(self, colors: List[str]) -> ColorPalette:
        """分析配色方案"""
        palette = ColorPalette()
        palette.all_colors = colors[:10]
        
        if not colors:
            return palette
        
        # 简单分类：假设前几个是主要颜色
        if len(colors) >= 1:
            palette.primary = colors[0]
        if len(colors) >= 2:
            palette.secondary = colors[1]
        if len(colors) >= 3:
            palette.accent = colors[2]
        
        # 判断配色类型（简化版）
        if len(colors) <= 3:
            palette.color_scheme_type = 'minimal'
        elif len(colors) <= 5:
            palette.color_scheme_type = 'balanced'
        else:
            palette.color_scheme_type = 'rich'
        
        # 可访问性评分（简化版）
        palette.accessibility_score = min(1.0, len(colors) / 8.0)
        
        return palette
    
    def analyze_typography(self, fonts: List[str], html: str = "") -> TypographyProfile:
        """分析排版配置"""
        profile = TypographyProfile()
        
        if fonts:
            profile.heading_font = fonts[0] if fonts else ""
            profile.body_font = fonts[1] if len(fonts) > 1 else fonts[0] if fonts else ""
        
        # 检测字体比例
        if any('Inter' in f for f in fonts):
            profile.font_scale = 'modular_scale'
        elif any('Playfair' in f for f in fonts):
            profile.font_scale = 'golden_ratio'
        else:
            profile.font_scale = 'custom'
        
        # 常见标题字号
        profile.heading_sizes = [96, 60, 48, 36, 24, 20]
        
        return profile
    
    def analyze_layout(self, layout_type: str, html: str = "") -> LayoutProfile:
        """分析布局配置"""
        profile = LayoutProfile()
        profile.layout_type = layout_type
        
        # 检测网格系统
        if 'grid' in layout_type.lower():
            profile.grid_columns = 12
            profile.spacing_system = '8px_base'
        elif 'flex' in layout_type.lower():
            profile.spacing_system = '4px_base'
        else:
            profile.spacing_system = 'custom'
        
        # 常见断点
        profile.breakpoints = {
            'mobile': '640px',
            'tablet': '768px',
            'desktop': '1024px',
            'wide': '1280px'
        }
        
        # 检测组件模式
        patterns = []
        if 'hero' in layout_type.lower():
            patterns.append('hero_section')
        if 'navbar' in layout_type.lower():
            patterns.append('sticky_navbar')
        if 'footer' in layout_type.lower():
            patterns.append('multi_column_footer')
        if 'sidebar' in layout_type.lower():
            patterns.append('sidebar_navigation')
        profile.component_patterns = patterns
        
        return profile
    
    def analyze_interactions(self, html: str, ai_elements: List[str]) -> List[InteractionPattern]:
        """分析交互模式"""
        interactions = []
        
        # 检测常见交互模式
        if 'chat' in html.lower() or 'chat_interface' in ai_elements:
            interactions.append(InteractionPattern(
                pattern_name='conversational_ui',
                description='对话式UI - 类似聊天的交互界面',
                implementation='message_list + input_box + typing_indicator',
                ai_relevance=0.95
            ))
        
        if 'prompt' in html.lower() or 'prompt_input' in ai_elements:
            interactions.append(InteractionPattern(
                pattern_name='prompt_engineering_ui',
                description='提示词工程界面 - AI提示输入和优化',
                implementation='textarea + suggestions + history',
                ai_relevance=0.9
            ))
        
        if 'generate' in html.lower() or 'generative' in ai_elements:
            interactions.append(InteractionPattern(
                pattern_name='generative_content',
                description='生成式内容 - 实时生成内容展示',
                implementation='streaming_output + progress + variants',
                ai_relevance=0.88
            ))
        
        # 通用交互模式
        interactions.append(InteractionPattern(
            pattern_name='micro_interactions',
            description='微交互 - 按钮悬停、状态变化等',
            implementation='css_transitions + javascript_events',
            ai_relevance=0.5
        ))
        
        interactions.append(InteractionPattern(
            pattern_name='scroll_animations',
            description='滚动动画 - 滚动触发的视觉效果',
            implementation='intersection_observer + css_animations',
            ai_relevance=0.4
        ))
        
        return interactions
    
    def detect_design_trends(self, html: str, colors: List[str], 
                              fonts: List[str], ai_elements: List[str]) -> List[str]:
        """检测设计趋势"""
        detected = []
        text_lower = html.lower()
        
        # 暗色模式
        if any(c in text_lower for c in ['#000', '#111', '#1a1a', 'dark', 'bg-gray-900']):
            detected.append('dark_mode')
        
        # 渐变
        if 'gradient' in text_lower or any('linear-gradient' in c for c in colors):
            detected.append('gradients')
        
        # 玻璃拟态
        if any(c in text_lower for c in ['backdrop-filter', 'backdropBlur', 'glass']):
            detected.append('glassmorphism')
        
        # 极简主义
        if len(colors) <= 4 and len(fonts) <= 2:
            detected.append('minimalism')
        
        # AI生成设计
        if ai_elements:
            detected.append('ai_generated')
        
        # 便当盒网格
        if 'bento' in text_lower or 'grid' in text_lower:
            detected.append('bento_grid')
        
        # 微交互
        if any(c in text_lower for c in ['transition', 'hover', 'animation']):
            detected.append('micro_interactions')
        
        return list(set(detected))
    
    def generate_recommendations(self, report: DesignAnalysisReport) -> List[str]:
        """生成设计改进建议"""
        recommendations = []
        
        # 配色建议
        if report.color_palette.accessibility_score < 0.5:
            recommendations.append('提升配色对比度，确保可访问性WCAG AA标准')
        
        if len(report.color_palette.all_colors) > 8:
            recommendations.append('精简配色方案，主色不超过3-5种')
        
        # 排版建议
        if not report.typography.heading_font:
            recommendations.append('定义清晰的字体层级，使用现代无衬线字体')
        
        # 布局建议
        if 'grid' not in report.layout.layout_type.lower():
            recommendations.append('考虑使用CSS Grid实现更灵活的布局')
        
        # AI设计建议
        if not report.ai_design_elements:
            recommendations.append('融入AI设计元素，如对话式UI、生成式内容展示')
        
        # 趋势建议
        if 'dark_mode' not in report.design_trends:
            recommendations.append('考虑支持暗色模式，符合现代设计趋势')
        
        if 'micro_interactions' not in report.design_trends:
            recommendations.append('增加微交互，提升用户体验')
        
        return recommendations[:5]
    
    def analyze_page(self, page_data: Dict) -> DesignAnalysisReport:
        """分析单个页面"""
        report = DesignAnalysisReport(
            url=page_data.get('url', ''),
            title=page_data.get('title', ''),
            analyzed_at=datetime.now().isoformat()
        )
        
        # 分析各维度
        report.color_palette = self.analyze_colors(page_data.get('colors', []))
        report.typography = self.analyze_typography(page_data.get('fonts', []))
        report.layout = self.analyze_layout(page_data.get('layout_type', ''))
        report.interactions = self.analyze_interactions(
            page_data.get('html_content', ''), 
            page_data.get('ai_elements', [])
        )
        report.ai_design_elements = page_data.get('ai_elements', [])
        report.design_trends = self.detect_design_trends(
            page_data.get('html_content', ''),
            page_data.get('colors', []),
            page_data.get('fonts', []),
            page_data.get('ai_elements', [])
        )
        
        # 计算总体设计评分
        score = 0.0
        score += min(0.2, len(report.color_palette.all_colors) / 20)
        score += min(0.15, len(report.typography.heading_font) / 50)
        score += min(0.15, len(report.layout.component_patterns) / 10)
        score += min(0.2, len(report.interactions) / 10)
        score += min(0.15, len(report.ai_design_elements) / 10)
        score += min(0.15, len(report.design_trends) / 10)
        report.overall_design_score = round(score, 2)
        
        # 生成建议
        report.recommendations = self.generate_recommendations(report)
        
        return report
    
    def analyze_batch(self, pages: List[Dict]) -> List[DesignAnalysisReport]:
        """批量分析"""
        reports = []
        for page in pages:
            report = self.analyze_page(page)
            reports.append(report)
            print(f"  📊 分析完成: {report.title[:40]} - 评分: {report.overall_design_score}")
        return reports
    
    def save_analysis(self, reports: List[DesignAnalysisReport], output_path: str):
        """保存分析结果"""
        os.makedirs(output_path, exist_ok=True)
        
        reports_data = []
        for report in reports:
            reports_data.append({
                'url': report.url,
                'title': report.title,
                'analyzed_at': report.analyzed_at,
                'color_palette': {
                    'primary': report.color_palette.primary,
                    'secondary': report.color_palette.secondary,
                    'accent': report.color_palette.accent,
                    'all_colors': report.color_palette.all_colors,
                    'color_scheme_type': report.color_palette.color_scheme_type,
                    'accessibility_score': report.color_palette.accessibility_score
                },
                'typography': {
                    'heading_font': report.typography.heading_font,
                    'body_font': report.typography.body_font,
                    'font_scale': report.typography.font_scale
                },
                'layout': {
                    'layout_type': report.layout.layout_type,
                    'grid_columns': report.layout.grid_columns,
                    'spacing_system': report.layout.spacing_system,
                    'component_patterns': report.layout.component_patterns
                },
                'interactions': [{'name': i.pattern_name, 'ai_relevance': i.ai_relevance} for i in report.interactions],
                'ai_design_elements': report.ai_design_elements,
                'overall_design_score': report.overall_design_score,
                'design_trends': report.design_trends,
                'recommendations': report.recommendations
            })
        
        output_file = os.path.join(output_path, f'analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(reports_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 分析结果已保存: {output_file}")
        return output_file

# 单例
_design_analyzer = None

def get_design_analyzer() -> DesignAnalyzer:
    """获取设计分析引擎单例"""
    global _design_analyzer
    if _design_analyzer is None:
        _design_analyzer = DesignAnalyzer()
    return _design_analyzer

if __name__ == "__main__":
    analyzer = get_design_analyzer()
    print("设计分析引擎初始化完成")
    print(f"已加载设计趋势: {len(analyzer.design_trends_db)} 条")
