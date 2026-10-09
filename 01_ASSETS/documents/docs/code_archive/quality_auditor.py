"""
质量审核器 V1.0
对生成的可视化页面进行多维度质量审核。

确权：DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
"""

import re
import os
from typing import Dict, List, Tuple
from dataclasses import dataclass, field

from interfaces.mechanism_interfaces import AuditReport, AuditGrade, ProcessingResult


@dataclass
class AuditIssue:
    """审核问题"""
    dimension: str
    severity: str  # critical/warning/info
    message: str
    location: str = ""


class QualityAuditor:
    """质量审核器"""

    # 必需的HTML标签
    REQUIRED_TAGS = ['<!DOCTYPE html>', '<html', '<head', '<body',
                      '<meta charset', '<title', '<meta name="viewport"']

    # 安全相关检查
    SECURITY_PATTERNS = {
        'inline_script': r'<script[^>]*>[^<]*(?:eval|document\.write|innerHTML\s*=)',
        'external_script_http': r'<script[^>]*src="http://',
        'inline_style': r'style="[^"]*expression\(',
    }

    # 可访问性检查
    A11Y_PATTERNS = {
        'img_without_alt': r'<img(?![^>]*alt=)[^>]*>',
        'button_without_text': r'<button(?![^>]*>)[^>]*>\s*</button>',
        'link_without_text': r'<a(?![^>]*href=)[^>]*>',
    }

    def __init__(self, config: Dict = None):
        self.config = config or {}
        self._audit_count = 0

    def audit(self, html_content: str, page_id: str = "") -> AuditReport:
        """
        对HTML页面进行多维度质量审核

        Args:
            html_content: HTML内容
            page_id: 页面ID

        Returns:
            AuditReport审核报告
        """
        self._audit_count += 1
        issues: List[AuditIssue] = []
        dimensions: Dict[str, Dict] = {}

        # 1. 内容完整性审核
        content_score, content_issues = self._audit_content(html_content)
        issues.extend(content_issues)
        dimensions['content'] = {'score': content_score, 'status': self._score_status(content_score)}

        # 2. HTML结构审核
        structure_score, structure_issues = self._audit_structure(html_content)
        issues.extend(structure_issues)
        dimensions['structure'] = {'score': structure_score, 'status': self._score_status(structure_score)}

        # 3. 性能审核
        performance_score, performance_issues = self._audit_performance(html_content)
        issues.extend(performance_issues)
        dimensions['performance'] = {'score': performance_score, 'status': self._score_status(performance_score)}

        # 4. 可访问性审核
        a11y_score, a11y_issues = self._audit_accessibility(html_content)
        issues.extend(a11y_issues)
        dimensions['accessibility'] = {'score': a11y_score, 'status': self._score_status(a11y_score)}

        # 5. 安全审核
        security_score, security_issues = self._audit_security(html_content)
        issues.extend(security_issues)
        dimensions['security'] = {'score': security_score, 'status': self._score_status(security_score)}

        # 6. SEO审核
        seo_score, seo_issues = self._audit_seo(html_content)
        issues.extend(seo_issues)
        dimensions['seo'] = {'score': seo_score, 'status': self._score_status(seo_score)}

        # 计算综合评分
        weights = {
            'content': 0.25,
            'structure': 0.20,
            'performance': 0.15,
            'accessibility': 0.15,
            'security': 0.15,
            'seo': 0.10,
        }
        overall_score = sum(dimensions[d]['score'] * weights[d] for d in dimensions)
        overall_score = round(overall_score, 1)

        # 评定等级
        grade = self._score_to_grade(overall_score)

        # 是否认证通过（>=70分且无critical问题）
        has_critical = any(i.severity == 'critical' for i in issues)
        certified = overall_score >= 70 and not has_critical

        # 为每个维度添加issues
        for dim in dimensions:
            dim_issues = [i for i in issues if i.dimension == dim]
            dimensions[dim]['issues'] = [
                {'severity': i.severity, 'message': i.message, 'location': i.location}
                for i in dim_issues
            ]
            dimensions[dim]['issue_count'] = len(dim_issues)

        return AuditReport(
            page_id=page_id,
            overall_score=overall_score,
            grade=grade,
            dimensions=dimensions,
            issues=[
                {'dimension': i.dimension, 'severity': i.severity,
                 'message': i.message, 'location': i.location}
                for i in issues
            ],
            certified=certified,
            audit_time=self._now()
        )

    def audit_file(self, file_path: str) -> Tuple[AuditReport, str]:
        """审核HTML文件"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        page_id = os.path.splitext(os.path.basename(file_path))[0]
        report = self.audit(content, page_id)
        return report, content

    # ============================================================
    # 各维度审核方法
    # ============================================================

    def _audit_content(self, html: str) -> Tuple[float, List[AuditIssue]]:
        """内容完整性审核"""
        issues = []
        score = 100.0

        # 检查是否有实质内容
        text_content = re.sub(r'<[^>]+>', '', html)
        text_content = re.sub(r'\s+', ' ', text_content).strip()

        if len(text_content) < 50:
            issues.append(AuditIssue('content', 'critical', '页面内容过少（<50字符），可能为空页面'))
            score -= 50
        elif len(text_content) < 200:
            issues.append(AuditIssue('content', 'warning', '页面内容较少（<200字符）'))
            score -= 15

        # 检查标题
        title_match = re.search(r'<title>(.*?)</title>', html, re.DOTALL)
        if not title_match or not title_match.group(1).strip():
            issues.append(AuditIssue('content', 'critical', '页面缺少<title>标签或标题为空'))
            score -= 20

        # 检查是否有h1标题
        if '<h1' not in html:
            issues.append(AuditIssue('content', 'warning', '页面缺少<h1>主标题'))
            score -= 10

        return max(0, score), issues

    def _audit_structure(self, html: str) -> Tuple[float, List[AuditIssue]]:
        """HTML结构审核"""
        issues = []
        score = 100.0

        # 检查必需标签
        for tag in self.REQUIRED_TAGS:
            if tag.lower() not in html.lower():
                issues.append(AuditIssue('structure', 'critical', f'缺少必需标签: {tag}'))
                score -= 15

        # 检查标签闭合（简单检查）
        open_div = len(re.findall(r'<div[^>]*>', html))
        close_div = len(re.findall(r'</div>', html))
        if open_div != close_div:
            issues.append(AuditIssue('structure', 'warning',
                                      f'div标签不匹配: 开{open_div}个/闭{close_div}个'))
            score -= 10

        # 检查是否有CSS
        if '<style' not in html and 'rel="stylesheet"' not in html:
            issues.append(AuditIssue('structure', 'info', '页面未包含CSS样式'))
            score -= 5

        return max(0, score), issues

    def _audit_performance(self, html: str) -> Tuple[float, List[AuditIssue]]:
        """性能审核"""
        issues = []
        score = 100.0

        # 文件大小
        size_kb = len(html.encode('utf-8')) / 1024
        if size_kb > 500:
            issues.append(AuditIssue('performance', 'critical', f'HTML文件过大（{size_kb:.0f}KB），建议<500KB'))
            score -= 30
        elif size_kb > 200:
            issues.append(AuditIssue('performance', 'warning', f'HTML文件较大（{size_kb:.0f}KB），建议优化'))
            score -= 10

        # 检查内联大段CSS/JS
        style_blocks = re.findall(r'<style[^>]*>(.*?)</style>', html, re.DOTALL)
        total_css = sum(len(s) for s in style_blocks)
        if total_css > 50000:
            issues.append(AuditIssue('performance', 'warning', f'内联CSS过大（{total_css/1024:.0f}KB），建议外部化'))
            score -= 10

        # 检查是否有懒加载
        if '<img' in html and 'loading="lazy"' not in html:
            issues.append(AuditIssue('performance', 'info', '图片未使用懒加载（loading="lazy"）'))
            score -= 5

        return max(0, score), issues

    def _audit_accessibility(self, html: str) -> Tuple[float, List[AuditIssue]]:
        """可访问性审核"""
        issues = []
        score = 100.0

        # 图片alt属性
        img_matches = re.findall(r'<img[^>]*>', html)
        imgs_without_alt = [img for img in img_matches if 'alt=' not in img]
        if imgs_without_alt:
            issues.append(AuditIssue('accessibility', 'warning',
                                      f'{len(imgs_without_alt)}张图片缺少alt属性'))
            score -= min(20, len(imgs_without_alt) * 5)

        # 检查语言属性
        if 'lang=' not in html.split('>')[0] if '>' in html else True:
            if '<html' in html and 'lang=' not in re.search(r'<html[^>]*>', html).group(0):
                issues.append(AuditIssue('accessibility', 'info', '<html>标签缺少lang属性'))
                score -= 5

        # 检查颜色对比度（简单检查：是否有明确的文字颜色）
        if 'color:' not in html and 'color:' not in html:
            issues.append(AuditIssue('accessibility', 'info', '未明确设置文字颜色，可能影响对比度'))
            score -= 5

        return max(0, score), issues

    def _audit_security(self, html: str) -> Tuple[float, List[AuditIssue]]:
        """安全审核"""
        issues = []
        score = 100.0

        # 检查危险的内联脚本
        for name, pattern in self.SECURITY_PATTERNS.items():
            matches = re.findall(pattern, html, re.IGNORECASE)
            if matches:
                severity = 'critical' if name in ('inline_script',) else 'warning'
                issues.append(AuditIssue('security', severity,
                                          f'安全风险: {name}（发现{len(matches)}处）'))
                score -= 20 if severity == 'critical' else 10

        # 检查外部HTTP资源（非HTTPS）
        http_resources = re.findall(r'src="http://[^"]+"', html) + re.findall(r'href="http://[^"]+"', html)
        if http_resources:
            issues.append(AuditIssue('security', 'warning',
                                      f'发现{len(http_resources)}个HTTP非加密资源，建议使用HTTPS'))
            score -= 10

        return max(0, score), issues

    def _audit_seo(self, html: str) -> Tuple[float, List[AuditIssue]]:
        """SEO审核"""
        issues = []
        score = 100.0

        # meta description
        if 'name="description"' not in html and "name='description'" not in html:
            issues.append(AuditIssue('seo', 'warning', '缺少meta description标签'))
            score -= 15

        # meta keywords
        if 'name="keywords"' not in html and "name='keywords'" not in html:
            issues.append(AuditIssue('seo', 'info', '缺少meta keywords标签'))
            score -= 5

        # Open Graph
        if 'og:title' not in html:
            issues.append(AuditIssue('seo', 'info', '缺少Open Graph标签（社交分享优化）'))
            score -= 5

        # 标题长度
        title_match = re.search(r'<title>(.*?)</title>', html, re.DOTALL)
        if title_match:
            title_len = len(title_match.group(1).strip())
            if title_len > 70:
                issues.append(AuditIssue('seo', 'warning', f'标题过长（{title_len}字符），建议<70字符'))
                score -= 5
            elif title_len < 10:
                issues.append(AuditIssue('seo', 'info', f'标题过短（{title_len}字符），建议10-70字符'))
                score -= 3

        return max(0, score), issues

    # ============================================================
    # 辅助方法
    # ============================================================

    @staticmethod
    def _score_status(score: float) -> str:
        """分数转状态"""
        if score >= 90:
            return 'excellent'
        elif score >= 70:
            return 'good'
        elif score >= 50:
            return 'fair'
        else:
            return 'poor'

    @staticmethod
    def _score_to_grade(score: float) -> AuditGrade:
        """分数转等级"""
        if score >= 90:
            return AuditGrade.A_EXCELLENT
        elif score >= 75:
            return AuditGrade.B_GOOD
        elif score >= 60:
            return AuditGrade.C_PASS
        else:
            return AuditGrade.D_FAIL

    @staticmethod
    def _now() -> str:
        """当前时间字符串"""
        from datetime import datetime
        return datetime.now().isoformat()

    def get_status(self) -> Dict:
        """获取审核器状态"""
        return {
            "audit_count": self._audit_count,
            "audit_dimensions": ['content', 'structure', 'performance', 'accessibility', 'security', 'seo'],
            "status": "running",
        }
