"""
可视化生成引擎 V1.0
将成果自动转化为可视化HTML网页，支持多种模板类型。

确权：DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
"""

import os
import re
import html
import json
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from interfaces.mechanism_interfaces import (
    ResultMetadata, ResultType, ProcessingResult, AuditReport, AuditGrade
)


@dataclass
class GeneratedPage:
    """生成的可视化页面"""
    page_id: str
    title: str
    html_content: str
    template_type: str
    metadata: Dict
    generated_at: str
    file_size: int = 0
    output_path: str = ""


class VisualizationEngine:
    """可视化生成引擎"""

    # 支持的模板类型
    SUPPORTED_TEMPLATES = ['doc', 'data', 'code', 'generic', 'card']

    # 主题配色（深色科技风，橙绿主色调）
    THEME = {
        'bg_primary': '#0a0e1a',
        'bg_secondary': '#111827',
        'bg_card': '#1a2332',
        'text_primary': '#f3f4f6',
        'text_secondary': '#9ca3af',
        'accent_orange': '#f59e0b',
        'accent_green': '#10b981',
        'accent_blue': '#3b82f6',
        'border': '#2d3748',
        'gradient': 'linear-gradient(135deg, #f59e0b 0%, #10b981 100%)',
    }

    def __init__(self, output_dir: str = None, config: Dict = None):
        self.output_dir = output_dir or os.path.join(os.getcwd(), 'output')
        self.config = config or {}
        self._generated_count = 0
        os.makedirs(self.output_dir, exist_ok=True)

    def generate(self, metadata: ResultMetadata, content: str,
                 template_type: str = None) -> ProcessingResult:
        """
        生成可视化网页

        Args:
            metadata: 成果元数据
            content: 成果内容
            template_type: 模板类型（doc/data/code/generic/card），None则自动选择

        Returns:
            ProcessingResult，data中包含generated_page
        """
        # 自动选择模板
        if template_type is None:
            template_type = self._auto_select_template(metadata, content)

        # 根据模板类型生成
        generators = {
            'doc': self._generate_doc_page,
            'data': self._generate_data_page,
            'code': self._generate_code_page,
            'card': self._generate_card_page,
            'generic': self._generate_generic_page,
        }

        generator = generators.get(template_type, self._generate_generic_page)

        try:
            page = generator(metadata, content)
            self._generated_count += 1

            # 保存到文件
            output_path = os.path.join(self.output_dir, f"{page.page_id}.html")
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(page.html_content)
            page.output_path = output_path
            page.file_size = os.path.getsize(output_path)

            return ProcessingResult(
                success=True,
                message=f"可视化页面生成成功: {page.title} ({template_type}模板, {page.file_size}字节)",
                data={
                    "generated_page": {
                        "page_id": page.page_id,
                        "title": page.title,
                        "template_type": template_type,
                        "output_path": page.output_path,
                        "file_size": page.file_size,
                        "file_size_human": self._human_size(page.file_size),
                        "generated_at": page.generated_at,
                    },
                    "metadata": page.metadata,
                },
                processing_time_ms=0
            )

        except Exception as e:
            return ProcessingResult(
                success=False,
                message=f"可视化页面生成失败: {str(e)}",
                errors=[str(e)]
            )

    def _auto_select_template(self, metadata: ResultMetadata, content: str) -> str:
        """自动选择模板类型"""
        result_type = metadata.result_type

        if result_type == ResultType.DOCUMENT:
            return 'doc'
        elif result_type == ResultType.DATA:
            return 'data'
        elif result_type == ResultType.CODE:
            return 'code'
        elif result_type in (ResultType.MEDIA, ResultType.VISUALIZATION):
            return 'card'
        else:
            return 'generic'

    # ============================================================
    # 模板生成器
    # ============================================================

    def _generate_doc_page(self, metadata: ResultMetadata, content: str) -> GeneratedPage:
        """生成文档型可视化页面（DocViz）"""
        page_id = f"doc-{metadata.content_hash[:12]}"
        title = metadata.result_name

        # 解析Markdown标题生成目录
        toc = self._extract_toc(content)

        # 转换Markdown为HTML（基础转换）
        body_html = self._markdown_to_html(content)

        # 元数据HTML
        meta_html = self._generate_metadata_html(metadata)

        html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(title)} - 火斗云智AIOS</title>
<style>
{self._base_css()}
{self._doc_css()}
</style>
</head>
<body>
<div class="page-container">
  <header class="page-header">
    <div class="header-badge">📄 文档成果</div>
    <h1 class="page-title">{html.escape(title)}</h1>
    <div class="header-meta">{meta_html}</div>
  </header>
  <div class="content-layout">
    <nav class="toc-sidebar">
      <h3>📑 目录导航</h3>
      {toc}
    </nav>
    <main class="doc-content">
      {body_html}
    </main>
  </div>
  <footer class="page-footer">
    <div class="footer-info">
      <span>🔗 Ω₀⊂⊙∞⊂Ω</span>
      <span>DID-BR-000002</span>
      <span>火斗云智AIOS</span>
      <span>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</span>
    </div>
  </footer>
</div>
<script>{self._base_js()}</script>
</body>
</html>"""

        return GeneratedPage(
            page_id=page_id,
            title=title,
            html_content=html_content,
            template_type='doc',
            metadata=self._metadata_to_dict(metadata),
            generated_at=datetime.now().isoformat()
        )

    def _generate_data_page(self, metadata: ResultMetadata, content: str) -> GeneratedPage:
        """生成数据型可视化页面（DataViz）"""
        page_id = f"data-{metadata.content_hash[:12]}"
        title = metadata.result_name

        # 尝试解析数据
        data_info = self._parse_data_content(content)
        meta_html = self._generate_metadata_html(metadata)

        html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(title)} - 火斗云智AIOS</title>
<style>
{self._base_css()}
{self._data_css()}
</style>
</head>
<body>
<div class="page-container">
  <header class="page-header">
    <div class="header-badge">📊 数据成果</div>
    <h1 class="page-title">{html.escape(title)}</h1>
    <div class="header-meta">{meta_html}</div>
  </header>
  <div class="data-stats">
    <div class="stat-card">
      <div class="stat-value">{data_info.get('rows', 'N/A')}</div>
      <div class="stat-label">数据行数</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">{data_info.get('cols', 'N/A')}</div>
      <div class="stat-label">字段数</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">{data_info.get('format', 'N/A')}</div>
      <div class="stat-label">数据格式</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">{self._human_size(metadata.size_bytes)}</div>
      <div class="stat-label">文件大小</div>
    </div>
  </div>
  <main class="data-content">
    <h2>📋 数据预览</h2>
    <div class="data-table-container">
      {data_info.get('table_html', '<p>数据预览暂不可用</p>')}
    </div>
  </main>
  <footer class="page-footer">
    <div class="footer-info">
      <span>🔗 Ω₀⊂⊙∞⊂Ω</span>
      <span>DID-BR-000002</span>
      <span>火斗云智AIOS</span>
    </div>
  </footer>
</div>
</body>
</html>"""

        return GeneratedPage(
            page_id=page_id,
            title=title,
            html_content=html_content,
            template_type='data',
            metadata=self._metadata_to_dict(metadata),
            generated_at=datetime.now().isoformat()
        )

    def _generate_code_page(self, metadata: ResultMetadata, content: str) -> GeneratedPage:
        """生成代码型可视化页面（CodeViz）"""
        page_id = f"code-{metadata.content_hash[:12]}"
        title = metadata.result_name
        meta_html = self._generate_metadata_html(metadata)

        # 代码统计
        lines = content.split('\n')
        code_stats = {
            'total_lines': len(lines),
            'non_empty_lines': sum(1 for l in lines if l.strip()),
            'comment_lines': sum(1 for l in lines if l.strip().startswith(('#', '//', '/*', '*'))),
        }

        escaped_code = html.escape(content)

        html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(title)} - 火斗云智AIOS</title>
<style>
{self._base_css()}
{self._code_css()}
</style>
</head>
<body>
<div class="page-container">
  <header class="page-header">
    <div class="header-badge">💻 代码成果</div>
    <h1 class="page-title">{html.escape(title)}</h1>
    <div class="header-meta">{meta_html}</div>
  </header>
  <div class="code-stats">
    <div class="stat-card"><div class="stat-value">{code_stats['total_lines']}</div><div class="stat-label">总行数</div></div>
    <div class="stat-card"><div class="stat-value">{code_stats['non_empty_lines']}</div><div class="stat-label">有效行</div></div>
    <div class="stat-card"><div class="stat-value">{code_stats['comment_lines']}</div><div class="stat-label">注释行</div></div>
    <div class="stat-card"><div class="stat-value">{metadata.format.upper()}</div><div class="stat-label">语言</div></div>
  </div>
  <main class="code-content">
    <div class="code-toolbar">
      <span class="code-filename">{html.escape(metadata.result_name)}.{metadata.format}</span>
      <button class="copy-btn" onclick="copyCode()">📋 复制代码</button>
    </div>
    <pre class="code-block"><code>{escaped_code}</code></pre>
  </main>
  <footer class="page-footer">
    <div class="footer-info">
      <span>🔗 Ω₀⊂⊙∞⊂Ω</span>
      <span>DID-BR-000002</span>
      <span>火斗云智AIOS</span>
    </div>
  </footer>
</div>
<script>
function copyCode() {{
  const code = document.querySelector('.code-block code').textContent;
  navigator.clipboard.writeText(code).then(() => {{
    const btn = document.querySelector('.copy-btn');
    btn.textContent = '✅ 已复制';
    setTimeout(() => btn.textContent = '📋 复制代码', 2000);
  }});
}}
</script>
</body>
</html>"""

        return GeneratedPage(
            page_id=page_id,
            title=title,
            html_content=html_content,
            template_type='code',
            metadata=self._metadata_to_dict(metadata),
            generated_at=datetime.now().isoformat()
        )

    def _generate_card_page(self, metadata: ResultMetadata, content: str) -> GeneratedPage:
        """生成卡片型可视化页面（CardViz，用于多媒体/可视化成果）"""
        page_id = f"card-{metadata.content_hash[:12]}"
        title = metadata.result_name
        meta_html = self._generate_metadata_html(metadata)

        html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(title)} - 火斗云智AIOS</title>
<style>{self._base_css()}{self._card_css()}</style>
</head>
<body>
<div class="page-container">
  <header class="page-header">
    <div class="header-badge">🎴 成果卡片</div>
    <h1 class="page-title">{html.escape(title)}</h1>
    <div class="header-meta">{meta_html}</div>
  </header>
  <main class="card-content">
    <div class="result-card">
      <div class="card-header">
        <div class="card-title">{html.escape(title)}</div>
        <div class="card-type">{metadata.result_type.value}</div>
      </div>
      <div class="card-body">
        <div class="card-section">
          <h4>📌 成果信息</h4>
          <ul>
            <li><strong>成果ID:</strong> {metadata.result_id}</li>
            <li><strong>类型:</strong> {metadata.result_type.value}</li>
            <li><strong>元类:</strong> {metadata.meta_class.value}</li>
            <li><strong>格式:</strong> {metadata.format}</li>
            <li><strong>大小:</strong> {self._human_size(metadata.size_bytes)}</li>
            <li><strong>版本:</strong> {metadata.version}</li>
            <li><strong>置信度:</strong> {metadata.confidence}</li>
            <li><strong>优先级:</strong> {metadata.priority.value}</li>
          </ul>
        </div>
        <div class="card-section">
          <h4>🏷️ 标签</h4>
          <div class="tag-list">
            {''.join(f'<span class="tag">{html.escape(t)}</span>' for t in metadata.tags)}
          </div>
        </div>
        <div class="card-section">
          <h4>🔗 确权信息</h4>
          <ul>
            <li><strong>内容哈希:</strong> <code>{metadata.content_hash[:32]}...</code></li>
            <li><strong>DID:</strong> DID-BR-000002</li>
            <li><strong>溯源标识:</strong> Ω₀⊂⊙∞⊂Ω</li>
          </ul>
        </div>
      </div>
    </div>
  </main>
  <footer class="page-footer">
    <div class="footer-info">
      <span>🔗 Ω₀⊂⊙∞⊂Ω</span>
      <span>DID-BR-000002</span>
      <span>火斗云智AIOS</span>
    </div>
  </footer>
</div>
</body>
</html>"""

        return GeneratedPage(
            page_id=page_id,
            title=title,
            html_content=html_content,
            template_type='card',
            metadata=self._metadata_to_dict(metadata),
            generated_at=datetime.now().isoformat()
        )

    def _generate_generic_page(self, metadata: ResultMetadata, content: str) -> GeneratedPage:
        """生成通用型可视化页面"""
        page_id = f"generic-{metadata.content_hash[:12]}"
        title = metadata.result_name
        meta_html = self._generate_metadata_html(metadata)
        escaped_content = html.escape(content[:5000])

        html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(title)} - 火斗云智AIOS</title>
<style>{self._base_css()}</style>
</head>
<body>
<div class="page-container">
  <header class="page-header">
    <div class="header-badge">📦 通用成果</div>
    <h1 class="page-title">{html.escape(title)}</h1>
    <div class="header-meta">{meta_html}</div>
  </header>
  <main class="generic-content">
    <h2>📄 内容预览</h2>
    <pre class="content-preview">{escaped_content}</pre>
  </main>
  <footer class="page-footer">
    <div class="footer-info">
      <span>🔗 Ω₀⊂⊙∞⊂Ω</span>
      <span>DID-BR-000002</span>
      <span>火斗云智AIOS</span>
    </div>
  </footer>
</div>
</body>
</html>"""

        return GeneratedPage(
            page_id=page_id,
            title=title,
            html_content=html_content,
            template_type='generic',
            metadata=self._metadata_to_dict(metadata),
            generated_at=datetime.now().isoformat()
        )

    # ============================================================
    # 辅助方法
    # ============================================================

    def _extract_toc(self, markdown: str) -> str:
        """从Markdown提取目录"""
        headings = re.findall(r'^(#{1,4})\s+(.+)$', markdown, re.MULTILINE)
        if not headings:
            return '<p class="toc-empty">暂无目录</p>'

        toc_items = []
        for hashes, title in headings[:30]:  # 最多30个
            level = len(hashes)
            anchor = hashlib.md5(title.encode()).hexdigest()[:8]
            toc_items.append(
                f'<a class="toc-item toc-level-{level}" href="#{anchor}">{html.escape(title.strip())}</a>'
            )
        return '\n'.join(toc_items)

    def _markdown_to_html(self, markdown: str) -> str:
        """基础Markdown转HTML"""
        lines = markdown.split('\n')
        html_lines = []
        in_code_block = False
        in_list = False

        for line in lines:
            # 代码块
            if line.strip().startswith('```'):
                if in_code_block:
                    html_lines.append('</code></pre>')
                    in_code_block = False
                else:
                    html_lines.append('<pre><code>')
                    in_code_block = True
                continue

            if in_code_block:
                html_lines.append(html.escape(line))
                continue

            # 标题
            heading_match = re.match(r'^(#{1,6})\s+(.+)$', line)
            if heading_match:
                if in_list:
                    html_lines.append('</ul>')
                    in_list = False
                level = len(heading_match.group(1))
                title = heading_match.group(2).strip()
                anchor = hashlib.md5(title.encode()).hexdigest()[:8]
                html_lines.append(f'<h{level} id="{anchor}">{html.escape(title)}</h{level}>')
                continue

            # 列表
            list_match = re.match(r'^[\-\*]\s+(.+)$', line)
            if list_match:
                if not in_list:
                    html_lines.append('<ul>')
                    in_list = True
                html_lines.append(f'<li>{html.escape(list_match.group(1))}</li>')
                continue
            elif in_list and line.strip():
                html_lines.append('</ul>')
                in_list = False

            # 粗体
            line = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', line)
            # 斜体
            line = re.sub(r'\*(.+?)\*', r'<em>\1</em>', line)
            # 行内代码
            line = re.sub(r'`(.+?)`', r'<code>\1</code>', line)
            # 链接
            line = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', line)

            # 空行
            if not line.strip():
                html_lines.append('')
            elif not line.startswith('<'):
                html_lines.append(f'<p>{line}</p>')

        if in_list:
            html_lines.append('</ul>')
        if in_code_block:
            html_lines.append('</code></pre>')

        return '\n'.join(html_lines)

    def _parse_data_content(self, content: str) -> Dict:
        """解析数据内容"""
        result = {'rows': 0, 'cols': 0, 'format': 'unknown', 'table_html': ''}

        # 尝试JSON
        try:
            data = json.loads(content)
            if isinstance(data, list):
                result['rows'] = len(data)
                if data and isinstance(data[0], dict):
                    result['cols'] = len(data[0])
                    result['format'] = 'JSON Array'
                    result['table_html'] = self._json_to_table(data[:50])
            elif isinstance(data, dict):
                result['rows'] = 1
                result['cols'] = len(data)
                result['format'] = 'JSON Object'
                result['table_html'] = self._dict_to_table(data)
            return result
        except (json.JSONDecodeError, ValueError):
            pass

        # 尝试CSV
        lines = content.strip().split('\n')
        if len(lines) > 1 and (',' in lines[0] or '\t' in lines[0]):
            delimiter = ',' if ',' in lines[0] else '\t'
            headers = lines[0].split(delimiter)
            result['cols'] = len(headers)
            result['rows'] = len(lines) - 1
            result['format'] = 'CSV' if delimiter == ',' else 'TSV'
            result['table_html'] = self._csv_to_table(lines[:51], delimiter)
            return result

        result['format'] = 'text'
        result['table_html'] = f'<pre>{html.escape(content[:2000])}</pre>'
        return result

    def _json_to_table(self, data: List[Dict]) -> str:
        """JSON数组转HTML表格"""
        if not data:
            return '<p>无数据</p>'
        headers = list(data[0].keys())
        rows_html = ''.join(
            '<tr>' + ''.join(f'<td>{html.escape(str(row.get(h, "")))[:100]}</td>' for h in headers) + '</tr>'
            for row in data
        )
        return f'<table class="data-table"><thead><tr>{"".join(f"<th>{html.escape(h)}</th>" for h in headers)}</tr></thead><tbody>{rows_html}</tbody></table>'

    def _dict_to_table(self, data: Dict) -> str:
        """字典转HTML表格"""
        rows = ''.join(f'<tr><th>{html.escape(k)}</th><td>{html.escape(str(v))[:200]}</td></tr>' for k, v in data.items())
        return f'<table class="data-table"><tbody>{rows}</tbody></table>'

    def _csv_to_table(self, lines: List[str], delimiter: str) -> str:
        """CSV转HTML表格"""
        if not lines:
            return '<p>无数据</p>'
        headers = lines[0].split(delimiter)
        rows = ''.join(
            '<tr>' + ''.join(f'<td>{html.escape(cell)[:100]}</td>' for cell in line.split(delimiter)) + '</tr>'
            for line in lines[1:]
        )
        return f'<table class="data-table"><thead><tr>{"".join(f"<th>{html.escape(h)}</th>" for h in headers)}</tr></thead><tbody>{rows}</tbody></table>'

    def _generate_metadata_html(self, metadata: ResultMetadata) -> str:
        """生成元数据HTML"""
        tags_html = ''.join(f'<span class="meta-tag">{html.escape(t)}</span>' for t in metadata.tags[:5])
        return f"""
        <div class="meta-row">
          <span class="meta-item">📁 {metadata.result_type.value}</span>
          <span class="meta-item">🏷️ {metadata.meta_class.value}</span>
          <span class="meta-item">⚡ {metadata.priority.value}</span>
          <span class="meta-item">📊 置信度 {metadata.confidence}</span>
          <span class="meta-item">📅 {metadata.created_at[:10]}</span>
        </div>
        <div class="meta-tags">{tags_html}</div>
        """

    def _metadata_to_dict(self, metadata: ResultMetadata) -> Dict:
        """元数据转字典"""
        return {
            'result_id': metadata.result_id,
            'result_name': metadata.result_name,
            'result_type': metadata.result_type.value,
            'meta_class': metadata.meta_class.value,
            'format': metadata.format,
            'size_bytes': metadata.size_bytes,
            'created_at': metadata.created_at,
            'version': metadata.version,
            'tags': metadata.tags,
            'priority': metadata.priority.value,
            'confidence': metadata.confidence,
            'content_hash': metadata.content_hash,
        }

    @staticmethod
    def _human_size(size_bytes: int) -> str:
        """人类可读文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"

    # ============================================================
    # CSS样式
    # ============================================================

    def _base_css(self) -> str:
        """基础CSS"""
        t = self.THEME
        return f"""
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
  background: {t['bg_primary']};
  color: {t['text_primary']};
  line-height: 1.6;
}}
.page-container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
.page-header {{
  background: {t['bg_secondary']};
  border: 1px solid {t['border']};
  border-radius: 12px;
  padding: 30px;
  margin-bottom: 20px;
  border-left: 4px solid {t['accent_orange']};
}}
.header-badge {{
  display: inline-block;
  background: {t['gradient']};
  color: #000;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 12px;
}}
.page-title {{
  font-size: 28px;
  font-weight: 700;
  margin-bottom: 16px;
  background: {t['gradient']};
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}}
.meta-row {{ display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 12px; }}
.meta-item {{
  background: {t['bg_card']};
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 13px;
  color: {t['text_secondary']};
}}
.meta-tags {{ display: flex; flex-wrap: wrap; gap: 8px; }}
.meta-tag {{
  background: rgba(16, 185, 129, 0.15);
  color: {t['accent_green']};
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 12px;
  border: 1px solid rgba(16, 185, 129, 0.3);
}}
.page-footer {{
  margin-top: 40px;
  padding: 20px;
  text-align: center;
  border-top: 1px solid {t['border']};
  color: {t['text_secondary']};
  font-size: 13px;
}}
.footer-info {{ display: flex; justify-content: center; flex-wrap: wrap; gap: 20px; }}
h1, h2, h3, h4 {{ color: {t['text_primary']}; margin: 20px 0 12px; }}
h2 {{ font-size: 22px; border-bottom: 2px solid {t['border']}; padding-bottom: 8px; }}
p {{ margin-bottom: 12px; color: {t['text_secondary']}; }}
ul, ol {{ margin-left: 20px; margin-bottom: 12px; }}
li {{ margin-bottom: 6px; color: {t['text_secondary']}; }}
code {{
  background: {t['bg_card']};
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 13px;
  color: {t['accent_orange']};
}}
pre {{
  background: {t['bg_secondary']};
  border: 1px solid {t['border']};
  border-radius: 8px;
  padding: 16px;
  overflow-x: auto;
  margin-bottom: 16px;
}}
pre code {{ background: none; padding: 0; color: {t['text_primary']}; }}
a {{ color: {t['accent_blue']}; text-decoration: none; }}
a:hover {{ text-decoration: underline; }}
"""

    def _doc_css(self) -> str:
        """文档型CSS"""
        t = self.THEME
        return f"""
.content-layout {{ display: flex; gap: 20px; align-items: flex-start; }}
.toc-sidebar {{
  width: 250px;
  flex-shrink: 0;
  background: {t['bg_secondary']};
  border: 1px solid {t['border']};
  border-radius: 12px;
  padding: 20px;
  position: sticky;
  top: 20px;
  max-height: 80vh;
  overflow-y: auto;
}}
.toc-sidebar h3 {{ font-size: 16px; margin-top: 0; color: {t['accent_orange']}; }}
.toc-item {{
  display: block;
  padding: 6px 10px;
  margin-bottom: 4px;
  border-radius: 6px;
  font-size: 13px;
  color: {t['text_secondary']};
  transition: all 0.2s;
}}
.toc-item:hover {{ background: {t['bg_card']}; color: {t['text_primary']}; text-decoration: none; }}
.toc-level-1 {{ font-weight: 600; }}
.toc-level-2 {{ padding-left: 20px; }}
.toc-level-3 {{ padding-left: 30px; font-size: 12px; }}
.toc-level-4 {{ padding-left: 40px; font-size: 12px; }}
.doc-content {{
  flex: 1;
  background: {t['bg_secondary']};
  border: 1px solid {t['border']};
  border-radius: 12px;
  padding: 30px;
  min-width: 0;
}}
.doc-content h1 {{ font-size: 24px; }}
.doc-content h2 {{ font-size: 20px; }}
@media (max-width: 900px) {{
  .content-layout {{ flex-direction: column; }}
  .toc-sidebar {{ width: 100%; position: static; max-height: none; }}
}}
"""

    def _data_css(self) -> str:
        """数据型CSS"""
        t = self.THEME
        return f"""
.data-stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 16px; margin-bottom: 20px; }}
.stat-card {{
  background: {t['bg_secondary']};
  border: 1px solid {t['border']};
  border-radius: 12px;
  padding: 20px;
  text-align: center;
  transition: transform 0.2s;
}}
.stat-card:hover {{ transform: translateY(-2px); border-color: {t['accent_green']}; }}
.stat-value {{ font-size: 28px; font-weight: 700; color: {t['accent_green']}; }}
.stat-label {{ font-size: 13px; color: {t['text_secondary']}; margin-top: 4px; }}
.data-content {{
  background: {t['bg_secondary']};
  border: 1px solid {t['border']};
  border-radius: 12px;
  padding: 30px;
}}
.data-table-container {{ overflow-x: auto; margin-top: 16px; }}
.data-table {{
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}}
.data-table th {{
  background: {t['bg_card']};
  padding: 10px 12px;
  text-align: left;
  border-bottom: 2px solid {t['accent_orange']};
  color: {t['accent_orange']};
  font-weight: 600;
  white-space: nowrap;
}}
.data-table td {{
  padding: 8px 12px;
  border-bottom: 1px solid {t['border']};
  color: {t['text_secondary']};
}}
.data-table tr:hover {{ background: {t['bg_card']}; }}
"""

    def _code_css(self) -> str:
        """代码型CSS"""
        t = self.THEME
        return f"""
.code-stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 16px; margin-bottom: 20px; }}
.code-content {{
  background: {t['bg_secondary']};
  border: 1px solid {t['border']};
  border-radius: 12px;
  overflow: hidden;
}}
.code-toolbar {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 20px;
  background: {t['bg_card']};
  border-bottom: 1px solid {t['border']};
}}
.code-filename {{ font-family: monospace; font-size: 14px; color: {t['accent_orange']}; }}
.copy-btn {{
  background: {t['gradient']};
  color: #000;
  border: none;
  padding: 6px 16px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  transition: opacity 0.2s;
}}
.copy-btn:hover {{ opacity: 0.9; }}
.code-block {{
  margin: 0;
  border: none;
  border-radius: 0;
  max-height: 600px;
  overflow: auto;
}}
.code-block code {{ font-family: 'Fira Code', 'Consolas', monospace; font-size: 13px; line-height: 1.5; }}
"""

    def _card_css(self) -> str:
        """卡片型CSS"""
        t = self.THEME
        return f"""
.card-content {{ padding: 20px 0; }}
.result-card {{
  background: {t['bg_secondary']};
  border: 1px solid {t['border']};
  border-radius: 16px;
  overflow: hidden;
  max-width: 700px;
  margin: 0 auto;
}}
.card-header {{
  background: {t['gradient']};
  padding: 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}}
.card-title {{ font-size: 20px; font-weight: 700; color: #000; }}
.card-type {{
  background: rgba(0,0,0,0.2);
  color: #fff;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  text-transform: uppercase;
}}
.card-body {{ padding: 24px; }}
.card-section {{ margin-bottom: 24px; }}
.card-section h4 {{ color: {t['accent_orange']}; margin-bottom: 12px; font-size: 16px; }}
.card-section ul {{ list-style: none; margin-left: 0; }}
.card-section li {{
  padding: 6px 0;
  border-bottom: 1px solid {t['border']};
  color: {t['text_secondary']};
}}
.card-section li strong {{ color: {t['text_primary']}; margin-right: 8px; }}
.tag-list {{ display: flex; flex-wrap: wrap; gap: 8px; }}
.tag {{
  background: rgba(245, 158, 11, 0.15);
  color: {t['accent_orange']};
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 13px;
  border: 1px solid rgba(245, 158, 11, 0.3);
}}
"""

    def _base_js(self) -> str:
        """基础JS"""
        return """
// 目录平滑滚动
document.querySelectorAll('.toc-item').forEach(item => {
  item.addEventListener('click', e => {
    e.preventDefault();
    const target = document.querySelector(item.getAttribute('href'));
    if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });
});
"""

    def get_status(self) -> Dict:
        """获取引擎状态"""
        return {
            "generated_count": self._generated_count,
            "supported_templates": self.SUPPORTED_TEMPLATES,
            "output_dir": self.output_dir,
            "status": "running",
        }
