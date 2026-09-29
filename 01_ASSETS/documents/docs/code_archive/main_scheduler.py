"""
主调度器 - 协调采集、分析、知识库、输出全流程
"""
import os
import sys
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.collector_engine import get_collector_engine, WebPageReference
from analyzers.design_analyzer import get_design_analyzer
from knowledge_base.design_knowledge_base import get_knowledge_base

class MainScheduler:
    """主调度器"""
    
    def __init__(self, project_dir: str):
        self.project_dir = project_dir
        self.config_path = os.path.join(project_dir, 'config', 'settings.json')
        self.output_dir = os.path.join(project_dir, 'output')
        self.kb_dir = os.path.join(project_dir, 'knowledge_base')
        self.logs_dir = os.path.join(project_dir, 'logs')
        
        # 确保目录存在
        for d in [self.output_dir, self.kb_dir, self.logs_dir]:
            os.makedirs(d, exist_ok=True)
        
        # 初始化组件
        self.collector = get_collector_engine(self.config_path)
        self.analyzer = get_design_analyzer()
        self.kb = get_knowledge_base(self.kb_dir)
        
        self.run_stats = {
            'started_at': '',
            'completed_at': '',
            'collected': 0,
            'analyzed': 0,
            'knowledge_added': 0,
            'errors': []
        }
    
    def run_full_pipeline(self, urls: List[str] = None, category: str = "general") -> Dict:
        """运行完整流程：采集 -> 分析 -> 知识库 -> 输出"""
        print("=" * 60)
        print("  🚀 网页设计参考采集学习系统 - 完整流程启动")
        print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        self.run_stats['started_at'] = datetime.now().isoformat()
        
        # 阶段1: 采集
        print("\n📥 阶段1: 网页采集")
        print("-" * 60)
        
        if urls:
            collected_pages = self.collector.collect_batch(urls, category)
        else:
            collected_pages = self.collector.collect_from_config()
        
        self.run_stats['collected'] = len(collected_pages)
        print(f"\n  ✅ 采集完成: {len(collected_pages)} 个页面")
        
        if not collected_pages:
            print("  ⚠️  没有采集到页面，流程结束")
            return self.run_stats
        
        # 阶段2: 分析
        print("\n📊 阶段2: 设计分析")
        print("-" * 60)
        
        pages_data = []
        for page in collected_pages:
            pages_data.append({
                'url': page.url,
                'title': page.title,
                'description': page.description,
                'category': page.category,
                'colors': page.colors,
                'fonts': page.fonts,
                'layout_type': page.layout_type,
                'ai_elements': page.ai_elements,
                'html_content': page.html_content,
                'source_category': page.category
            })
        
        analysis_reports = self.analyzer.analyze_batch(pages_data)
        self.run_stats['analyzed'] = len(analysis_reports)
        print(f"\n  ✅ 分析完成: {len(analysis_reports)} 个报告")
        
        # 阶段3: 知识库
        print("\n🧠 阶段3: 知识库沉淀")
        print("-" * 60)
        
        total_added = 0
        for report in analysis_reports:
            report_dict = {
                'url': report.url,
                'title': report.title,
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
                'interactions': [{'pattern_name': i.pattern_name, 
                                  'description': i.description,
                                  'ai_relevance': i.ai_relevance} 
                                 for i in report.interactions],
                'ai_design_elements': report.ai_design_elements,
                'design_trends': report.design_trends,
                'source_category': pages_data[0].get('category', 'general') if pages_data else 'general'
            }
            added = self.kb.add_from_analysis_report(report_dict)
            total_added += added
        
        self.run_stats['knowledge_added'] = total_added
        print(f"\n  ✅ 知识库沉淀完成: 新增 {total_added} 条知识")
        print(f"  📚 知识库总条目: {self.kb.stats['total_entries']}")
        
        # 阶段4: 输出
        print("\n📤 阶段4: 生成输出")
        print("-" * 60)
        
        # 保存采集结果
        collected_file = self.collector.save_results(self.output_dir)
        
        # 保存分析结果
        analysis_file = self.analyzer.save_analysis(analysis_reports, self.output_dir)
        
        # 导出知识库摘要
        summary_file = self.kb.export_summary(self.output_dir)
        
        print(f"\n  ✅ 输出文件:")
        print(f"     - 采集结果: {collected_file}")
        print(f"     - 分析报告: {analysis_file}")
        print(f"     - 知识摘要: {summary_file}")
        
        self.run_stats['completed_at'] = datetime.now().isoformat()
        
        # 打印统计
        print("\n" + "=" * 60)
        print("  📊 运行统计")
        print("=" * 60)
        print(f"  采集页面: {self.run_stats['collected']}")
        print(f"  分析报告: {self.run_stats['analyzed']}")
        print(f"  知识新增: {self.run_stats['knowledge_added']}")
        print(f"  开始时间: {self.run_stats['started_at']}")
        print(f"  完成时间: {self.run_stats['completed_at']}")
        print("=" * 60)
        
        return self.run_stats
    
    def run_daily_collection(self):
        """每日定时采集"""
        print("🌅 每日定时采集任务启动")
        return self.run_full_pipeline()
    
    def run_weekly_deep_analysis(self):
        """每周深度分析"""
        print("📈 每周深度分析任务启动")
        # 这里可以添加更深入的分析逻辑
        return self.run_full_pipeline()

# 单例
_main_scheduler = None

def get_main_scheduler(project_dir: str = None) -> MainScheduler:
    """获取主调度器单例"""
    global _main_scheduler
    if _main_scheduler is None:
        _main_scheduler = MainScheduler(project_dir or os.getcwd())
    return _main_scheduler

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='网页设计参考采集学习系统')
    parser.add_argument('--urls', nargs='+', help='指定采集的URL列表')
    parser.add_argument('--category', default='general', help='URL分类')
    parser.add_argument('--project-dir', default='.', help='项目目录')
    args = parser.parse_args()
    
    scheduler = get_main_scheduler(args.project_dir)
    scheduler.run_full_pipeline(urls=args.urls, category=args.category)
