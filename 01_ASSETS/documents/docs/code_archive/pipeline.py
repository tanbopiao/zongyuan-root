#!/usr/bin/env python3
"""
成果可视化官网集成 - 主流水线 V1.0
将成果识别→分类→可视化→审核→输出全流程串联。

确权：DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
"""

import os
import sys
import json
import time
from datetime import datetime
from typing import Dict, List, Optional

# 添加项目根目录到路径
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from interfaces.mechanism_interfaces import (
    ResultMetadata, ResultType, MetaClass, Priority,
    ProcessingResult, AuditReport, AuditGrade
)
from detectors.result_detector import ResultDetector
from classifiers.result_classifier import ResultClassifier
from visualizers.visualization_engine import VisualizationEngine
from auditors.quality_auditor import QualityAuditor


class ResultVisualizationPipeline:
    """成果可视化官网集成主流水线"""

    def __init__(self, watch_path: str = None, output_dir: str = None, config: Dict = None):
        """
        初始化流水线

        Args:
            watch_path: 成果监控路径
            output_dir: 可视化输出目录
            config: 配置字典
        """
        self.config = config or {}
        self.watch_path = watch_path or os.getcwd()
        self.output_dir = output_dir or os.path.join(PROJECT_ROOT, 'output')

        # 初始化各组件
        self.detector = ResultDetector(watch_path=self.watch_path, config=config)
        self.classifier = ResultClassifier(config=config)
        self.visualizer = VisualizationEngine(output_dir=self.output_dir, config=config)
        self.auditor = QualityAuditor(config=config)

        # 运行统计
        self._stats = {
            'total_processed': 0,
            'success_count': 0,
            'fail_count': 0,
            'avg_audit_score': 0.0,
            'audit_scores': [],
            'start_time': datetime.now().isoformat(),
        }

        os.makedirs(self.output_dir, exist_ok=True)

    def run(self, path: str = None, recursive: bool = True) -> Dict:
        """
        运行完整流水线：识别→分类→可视化→审核

        Args:
            path: 扫描路径，默认使用watch_path
            recursive: 是否递归扫描

        Returns:
            流水线运行结果
        """
        start_time = time.time()
        scan_path = path or self.watch_path
        results = []

        print(f"{'='*60}")
        print(f"  成果可视化官网集成流水线 V1.0")
        print(f"  扫描路径: {scan_path}")
        print(f"  输出目录: {self.output_dir}")
        print(f"  开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}\n")

        # 第一步：成果识别
        print("【步骤1/4】成果自动识别...")
        detect_result = self.detector.scan_directory(scan_path, recursive=recursive)
        if not detect_result.success:
            print(f"  ❌ 识别失败: {detect_result.message}")
            return self._build_result(False, detect_result.message, [], start_time)

        detected = detect_result.data.get('detected_results', [])
        print(f"  ✅ 识别完成: 发现 {len(detected)} 个新/变更成果")
        if not detected:
            print("  ℹ️  没有新成果需要处理")
            return self._build_result(True, "没有新成果", [], start_time)

        # 第二步：逐个处理
        for i, detected_item in enumerate(detected, 1):
            print(f"\n--- 处理成果 {i}/{len(detected)}: {detected_item['file_name']} ---")
            item_result = self._process_single(detected_item)
            results.append(item_result)

        # 统计
        success = sum(1 for r in results if r.get('success'))
        fail = len(results) - success
        avg_score = (sum(r.get('audit_score', 0) for r in results) / len(results)) if results else 0

        self._stats['total_processed'] += len(results)
        self._stats['success_count'] += success
        self._stats['fail_count'] += fail

        print(f"\n{'='*60}")
        print(f"  流水线执行完成")
        print(f"  处理总数: {len(results)}")
        print(f"  成功: {success} | 失败: {fail}")
        print(f"  平均审核分: {avg_score:.1f}")
        print(f"  总耗时: {(time.time()-start_time)*1000:.0f}ms")
        print(f"{'='*60}")

        return self._build_result(True, "流水线执行完成", results, start_time)

    def _process_single(self, detected_item: Dict) -> Dict:
        """处理单个成果"""
        result = {
            'file_path': detected_item['file_path'],
            'file_name': detected_item['file_name'],
            'success': False,
            'stages': {},
        }

        try:
            # 构建元数据
            from detectors.result_detector import DetectedResult
            dr = DetectedResult(
                file_path=detected_item['file_path'],
                file_name=detected_item['file_name'],
                file_ext=detected_item['file_ext'],
                file_size=detected_item['file_size'],
                modified_time=time.time(),
                content_hash=detected_item['content_hash'],
                is_new=detected_item.get('is_new', True),
            )
            metadata = self.detector.build_metadata(dr)

            # 读取内容
            content = self._read_file(detected_item['file_path'])

            # 第二步：分类
            classify_result = self.classifier.classify(metadata, content)
            result['stages']['classification'] = {
                'success': classify_result.success,
                'meta_class': metadata.meta_class.value,
                'priority': metadata.priority.value,
                'tags': metadata.tags,
                'confidence': classify_result.data.get('classification', {}).get('confidence', 0),
            }
            print(f"  【分类】元类={metadata.meta_class.value}, 优先级={metadata.priority.value}, 标签={len(metadata.tags)}个")

            # 第三步：可视化生成
            viz_result = self.visualizer.generate(metadata, content)
            if not viz_result.success:
                result['error'] = viz_result.message
                print(f"  ❌ 可视化失败: {viz_result.message}")
                return result

            page_info = viz_result.data.get('generated_page', {})
            result['stages']['visualization'] = {
                'success': True,
                'page_id': page_info.get('page_id'),
                'template_type': page_info.get('template_type'),
                'output_path': page_info.get('output_path'),
                'file_size': page_info.get('file_size'),
            }
            print(f"  【可视化】模板={page_info.get('template_type')}, 大小={page_info.get('file_size_human', 'N/A')}")

            # 第四步：质量审核
            with open(page_info['output_path'], 'r', encoding='utf-8') as f:
                html_content = f.read()
            audit_report = self.auditor.audit(html_content, page_info.get('page_id', ''))
            result['stages']['audit'] = {
                'success': audit_report.certified,
                'score': audit_report.overall_score,
                'grade': audit_report.grade.value,
                'certified': audit_report.certified,
                'issues_count': len(audit_report.issues),
                'critical_issues': sum(1 for i in audit_report.issues if i.get('severity') == 'critical'),
            }
            result['audit_score'] = audit_report.overall_score
            self._stats['audit_scores'].append(audit_report.overall_score)

            status_icon = '✅' if audit_report.certified else '⚠️'
            print(f"  【审核】{status_icon} 评分={audit_report.overall_score}, 等级={audit_report.grade.value}, 认证={'通过' if audit_report.certified else '未通过'}")

            result['success'] = True
            result['output_path'] = page_info.get('output_path')

        except Exception as e:
            result['error'] = str(e)
            print(f"  ❌ 处理异常: {str(e)}")

        return result

    def _read_file(self, file_path: str, max_size: int = 500000) -> str:
        """读取文件内容（限制大小）"""
        try:
            if os.path.getsize(file_path) > max_size:
                return f"[文件过大，仅预览前{max_size}字节]\n\n" + open(file_path, 'r', encoding='utf-8', errors='ignore').read(max_size)
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception as e:
            return f"[文件读取失败: {str(e)}]"

    def _build_result(self, success: bool, message: str,
                      results: List, start_time: float) -> Dict:
        """构建最终结果"""
        return {
            'success': success,
            'message': message,
            'results': results,
            'stats': {
                'total': len(results),
                'success': sum(1 for r in results if r.get('success')),
                'fail': sum(1 for r in results if not r.get('success')),
                'avg_audit_score': (sum(r.get('audit_score', 0) for r in results) / len(results)) if results else 0,
            },
            'processing_time_ms': (time.time() - start_time) * 1000,
            'timestamp': datetime.now().isoformat(),
        }

    def get_stats(self) -> Dict:
        """获取流水线统计"""
        return self._stats

    def generate_showcase_page(self, results: List[Dict], output_path: str = None) -> str:
        """
        生成成果展示中心页面

        Args:
            results: 流水线处理结果列表
            output_path: 输出路径

        Returns:
            展示页面路径
        """
        if output_path is None:
            output_path = os.path.join(self.output_dir, 'showcase.html')

        # 构建成果卡片HTML
        cards_html = ""
        for r in results:
            if not r.get('success'):
                continue
            stages = r.get('stages', {})
            viz = stages.get('visualization', {})
            audit = stages.get('audit', {})
            cls = stages.get('classification', {})

            score = audit.get('score', 0)
            score_color = '#10b981' if score >= 80 else ('#f59e0b' if score >= 60 else '#ef4444')
            certified_badge = '✅ 已认证' if audit.get('certified') else '⚠️ 待优化'

            tags_html = ''.join(f'<span class="card-tag">{t}</span>' for t in cls.get('tags', [])[:4])

            cards_html += f"""
            <div class="showcase-card">
              <div class="card-header">
                <span class="card-type">{viz.get('template_type', 'generic')}</span>
                <span class="card-score" style="color:{score_color}">{score:.0f}分</span>
              </div>
              <h3 class="card-title">{r.get('file_name', '未知')}</h3>
              <div class="card-meta">
                <span>🏷️ {cls.get('meta_class', 'N/A')}</span>
                <span>⚡ {cls.get('priority', 'N/A')}</span>
                <span>{certified_badge}</span>
              </div>
              <div class="card-tags">{tags_html}</div>
              <div class="card-footer">
                <span class="card-size">{self._human_size(viz.get('file_size', 0))}</span>
                <a href="{os.path.basename(viz.get('output_path', '#'))}" class="card-link" target="_blank">查看详情 →</a>
              </div>
            </div>
            """

        # 统计数据
        total = len(results)
        success = sum(1 for r in results if r.get('success'))
        avg_score = (sum(r.get('audit_score', 0) for r in results if r.get('success')) / success) if success else 0
        certified = sum(1 for r in results if r.get('stages', {}).get('audit', {}).get('certified'))

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>成果展示中心 - 火斗云智AIOS</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
  background: #0a0e1a;
  color: #f3f4f6;
  line-height: 1.6;
}}
.showcase-container {{ max-width: 1200px; margin: 0 auto; padding: 40px 20px; }}
.showcase-header {{
  text-align: center;
  margin-bottom: 40px;
}}
.showcase-header h1 {{
  font-size: 36px;
  font-weight: 700;
  background: linear-gradient(135deg, #f59e0b 0%, #10b981 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-bottom: 12px;
}}
.showcase-header p {{ color: #9ca3af; font-size: 16px; }}
.stats-bar {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 16px;
  margin-bottom: 40px;
}}
.stat-item {{
  background: #111827;
  border: 1px solid #2d3748;
  border-radius: 12px;
  padding: 20px;
  text-align: center;
}}
.stat-value {{ font-size: 28px; font-weight: 700; color: #10b981; }}
.stat-label {{ font-size: 13px; color: #9ca3af; margin-top: 4px; }}
.showcase-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
}}
.showcase-card {{
  background: #111827;
  border: 1px solid #2d3748;
  border-radius: 12px;
  padding: 20px;
  transition: all 0.3s;
}}
.showcase-card:hover {{
  transform: translateY(-4px);
  border-color: #f59e0b;
  box-shadow: 0 8px 30px rgba(245, 158, 11, 0.15);
}}
.card-header {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}}
.card-type {{
  background: rgba(245, 158, 11, 0.15);
  color: #f59e0b;
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 12px;
  text-transform: uppercase;
}}
.card-score {{ font-size: 18px; font-weight: 700; }}
.card-title {{
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 12px;
  color: #f3f4f6;
  word-break: break-all;
}}
.card-meta {{
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
  font-size: 12px;
  color: #9ca3af;
}}
.card-tags {{
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 16px;
}}
.card-tag {{
  background: rgba(16, 185, 129, 0.1);
  color: #10b981;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;
}}
.card-footer {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 12px;
  border-top: 1px solid #2d3748;
}}
.card-size {{ font-size: 12px; color: #6b7280; }}
.card-link {{
  color: #f59e0b;
  text-decoration: none;
  font-size: 13px;
  font-weight: 600;
}}
.card-link:hover {{ text-decoration: underline; }}
.showcase-footer {{
  text-align: center;
  margin-top: 60px;
  padding-top: 30px;
  border-top: 1px solid #2d3748;
  color: #6b7280;
  font-size: 13px;
}}
</style>
</head>
<body>
<div class="showcase-container">
  <header class="showcase-header">
    <h1>🎨 成果展示中心</h1>
    <p>全自动上报成果自动可视化网页集成官网展示机制 - 成果一览</p>
  </header>

  <div class="stats-bar">
    <div class="stat-item">
      <div class="stat-value">{total}</div>
      <div class="stat-label">处理成果总数</div>
    </div>
    <div class="stat-item">
      <div class="stat-value">{success}</div>
      <div class="stat-label">可视化成功</div>
    </div>
    <div class="stat-item">
      <div class="stat-value">{certified}</div>
      <div class="stat-label">质量认证通过</div>
    </div>
    <div class="stat-item">
      <div class="stat-value">{avg_score:.0f}</div>
      <div class="stat-label">平均审核分</div>
    </div>
  </div>

  <div class="showcase-grid">
    {cards_html if cards_html else '<p style="grid-column:1/-1;text-align:center;color:#6b7280;padding:40px;">暂无成果展示</p>'}
  </div>

  <footer class="showcase-footer">
    <p>🔗 Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | 火斗云智AIOS | 元极恒一自治体系</p>
    <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
  </footer>
</div>
</body>
</html>"""

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)

        return output_path

    @staticmethod
    def _human_size(size_bytes: int) -> str:
        """人类可读文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='成果可视化官网集成流水线')
    parser.add_argument('--path', '-p', type=str, default=None,
                        help='扫描路径（默认当前目录）')
    parser.add_argument('--output', '-o', type=str, default=None,
                        help='输出目录（默认./output）')
    parser.add_argument('--no-recursive', action='store_true',
                        help='不递归扫描子目录')
    parser.add_argument('--showcase', action='store_true',
                        help='生成成果展示中心页面')
    parser.add_argument('--json', action='store_true',
                        help='以JSON格式输出结果')

    args = parser.parse_args()

    # 确定扫描路径
    watch_path = args.path
    if not watch_path:
        # 默认扫描项目目录下的机制文档
        script_dir = os.path.dirname(os.path.abspath(__file__))
        watch_path = os.path.dirname(script_dir)  # 上一级目录

    pipeline = ResultVisualizationPipeline(
        watch_path=watch_path,
        output_dir=args.output
    )

    result = pipeline.run(watch_path, recursive=not args.no_recursive)

    # 生成展示中心
    if args.showcase and result.get('results'):
        showcase_path = pipeline.generate_showcase_page(result['results'])
        print(f"\n🎨 成果展示中心已生成: {showcase_path}")

    # JSON输出
    if args.json:
        print("\n" + json.dumps(result, ensure_ascii=False, indent=2, default=str))

    return 0 if result.get('success') else 1


if __name__ == '__main__':
    sys.exit(main())
