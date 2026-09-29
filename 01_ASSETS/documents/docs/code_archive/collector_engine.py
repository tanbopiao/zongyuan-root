"""
网页设计参考采集引擎 - 核心模块
负责自动采集全网高端网页设计参考
"""
import os
import sys
import json
import time
import hashlib
import requests
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup

@dataclass
class WebPageReference:
    """网页设计参考条目"""
    id: str
    url: str
    title: str
    description: str
    category: str  # ai_company/design_gallery/design_resource
    collected_at: str
    html_content: str = ""
    screenshot_path: str = ""
    colors: List[str] = field(default_factory=list)
    fonts: List[str] = field(default_factory=list)
    layout_type: str = ""
    design_score: float = 0.0
    ai_elements: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

class CollectorEngine:
    """采集引擎"""
    
    def __init__(self, config_path: str = None):
        self.config = self._load_config(config_path)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.config['collector']['user_agent'],
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        })
        self.collected_pages: List[WebPageReference] = []
        self.stats = {
            'total_collected': 0,
            'successful': 0,
            'failed': 0,
            'by_category': {}
        }
    
    def _load_config(self, config_path: str) -> Dict:
        """加载配置"""
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            'collector': {
                'request_timeout': 30,
                'retry_count': 3,
                'delay_between_requests': 2
            }
        }
    
    def fetch_page(self, url: str) -> Optional[str]:
        """获取网页内容"""
        timeout = self.config['collector']['request_timeout']
        retries = self.config['collector']['retry_count']
        delay = self.config['collector']['delay_between_requests']
        
        for attempt in range(retries):
            try:
                response = self.session.get(url, timeout=timeout, allow_redirects=True)
                response.raise_for_status()
                response.encoding = response.apparent_encoding or 'utf-8'
                return response.text
            except Exception as e:
                print(f"  ⚠️  获取失败 (尝试 {attempt+1}/{retries}): {url} - {e}")
                if attempt < retries - 1:
                    time.sleep(delay * (attempt + 1))
        return None
    
    def parse_page(self, url: str, html: str, category: str) -> WebPageReference:
        """解析网页内容"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # 提取标题
        title = soup.title.string.strip() if soup.title else url
        
        # 提取描述
        description = ""
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            description = meta_desc['content']
        
        # 生成唯一ID
        page_id = hashlib.md5(url.encode()).hexdigest()[:12]
        
        # 提取颜色
        colors = self._extract_colors(soup, html)
        
        # 提取字体
        fonts = self._extract_fonts(soup, html)
        
        # 分析布局
        layout_type = self._analyze_layout(soup)
        
        # 提取AI设计元素
        ai_elements = self._extract_ai_elements(soup, html)
        
        return WebPageReference(
            id=page_id,
            url=url,
            title=title,
            description=description,
            category=category,
            collected_at=datetime.now().isoformat(),
            html_content=html[:50000],  # 限制大小
            colors=colors,
            fonts=fonts,
            layout_type=layout_type,
            ai_elements=ai_elements
        )
    
    def _extract_colors(self, soup: BeautifulSoup, html: str) -> List[str]:
        """提取页面主要颜色"""
        colors = set()
        
        # 从内联样式提取
        for tag in soup.find_all(style=True):
            style = tag.get('style', '')
            import re
            color_matches = re.findall(r'#[0-9a-fA-F]{3,8}\b|rgba?\([^)]+\)', style)
            colors.update(color_matches)
        
        # 从CSS提取
        for style_tag in soup.find_all('style'):
            css = style_tag.string or ''
            import re
            color_matches = re.findall(r'#[0-9a-fA-F]{3,8}\b|rgba?\([^)]+\)', css)
            colors.update(color_matches)
        
        return list(colors)[:10]
    
    def _extract_fonts(self, soup: BeautifulSoup, html: str) -> List[str]:
        """提取页面字体"""
        fonts = set()
        
        # 从Google Fonts链接提取
        for link in soup.find_all('link', href=True):
            href = link['href']
            if 'fonts.googleapis.com' in href or 'fonts.gstatic.com' in href:
                fonts.add('Google Fonts')
        
        # 从内联样式提取font-family
        import re
        font_matches = re.findall(r'font-family:\s*([^;]+)', html)
        for match in font_matches:
            font = match.strip().split(',')[0].strip().strip("'\"")
            if font and len(font) < 50:
                fonts.add(font)
        
        return list(fonts)[:10]
    
    def _analyze_layout(self, soup: BeautifulSoup) -> str:
        """分析布局类型"""
        # 检测常见布局模式
        has_grid = bool(soup.find_all(class_=lambda x: x and 'grid' in x.lower()))
        has_flex = bool(soup.find_all(class_=lambda x: x and 'flex' in x.lower()))
        has_hero = bool(soup.find_all(class_=lambda x: x and 'hero' in x.lower()))
        has_sidebar = bool(soup.find_all(class_=lambda x: x and 'sidebar' in x.lower()))
        has_navbar = bool(soup.find_all(['nav', 'header']))
        has_footer = bool(soup.find_all('footer'))
        
        layout_features = []
        if has_hero: layout_features.append('hero_section')
        if has_grid: layout_features.append('grid_layout')
        if has_flex: layout_features.append('flex_layout')
        if has_sidebar: layout_features.append('sidebar')
        if has_navbar: layout_features.append('navbar')
        if has_footer: layout_features.append('footer')
        
        return '+'.join(layout_features) if layout_features else 'unknown'
    
    def _extract_ai_elements(self, soup: BeautifulSoup, html: str) -> List[str]:
        """提取AI相关设计元素"""
        ai_elements = []
        ai_keywords = ['ai', 'artificial intelligence', 'machine learning', 'gpt', 
                       'neural', 'deep learning', 'llm', 'chatbot', 'assistant',
                       'generate', 'model', 'algorithm', 'automation']
        
        text_content = soup.get_text().lower()
        for keyword in ai_keywords:
            if keyword in text_content:
                ai_elements.append(keyword)
        
        # 检测AI常见UI元素
        if soup.find_all(class_=lambda x: x and 'chat' in x.lower()):
            ai_elements.append('chat_interface')
        if soup.find_all(class_=lambda x: x and 'prompt' in x.lower()):
            ai_elements.append('prompt_input')
        if soup.find_all(class_=lambda x: x and 'generative' in x.lower()):
            ai_elements.append('generative_ui')
        
        return list(set(ai_elements))
    
    def collect_from_url(self, url: str, category: str = "general") -> Optional[WebPageReference]:
        """从单个URL采集"""
        print(f"  📥 采集: {url}")
        
        html = self.fetch_page(url)
        if not html:
            self.stats['failed'] += 1
            return None
        
        page_ref = self.parse_page(url, html, category)
        self.collected_pages.append(page_ref)
        self.stats['successful'] += 1
        self.stats['total_collected'] += 1
        self.stats['by_category'][category] = self.stats['by_category'].get(category, 0) + 1
        
        print(f"  ✅ 成功: {page_ref.title[:50]}")
        return page_ref
    
    def collect_batch(self, urls: List[str], category: str = "general") -> List[WebPageReference]:
        """批量采集"""
        results = []
        delay = self.config['collector']['delay_between_requests']
        
        for i, url in enumerate(urls):
            print(f"\n[{i+1}/{len(urls)}] ", end="")
            result = self.collect_from_url(url, category)
            if result:
                results.append(result)
            time.sleep(delay)
        
        return results
    
    def collect_from_config(self) -> List[WebPageReference]:
        """从配置文件中的源采集"""
        all_results = []
        
        # 采集AI公司官网
        print("\n🤖 采集AI公司官网设计参考...")
        ai_urls = self.config.get('sources', {}).get('ai_companies', [])
        results = self.collect_batch(ai_urls, 'ai_company')
        all_results.extend(results)
        
        # 采集设计画廊
        print("\n🎨 采集设计画廊网站...")
        gallery_urls = self.config.get('sources', {}).get('design_galleries', [])
        results = self.collect_batch(gallery_urls[:5], 'design_gallery')  # 限制数量
        all_results.extend(results)
        
        # 采集设计资源
        print("\n📚 采集设计资源网站...")
        resource_urls = self.config.get('sources', {}).get('design_resources', [])
        results = self.collect_batch(resource_urls[:3], 'design_resource')
        all_results.extend(results)
        
        return all_results
    
    def save_results(self, output_path: str):
        """保存采集结果"""
        os.makedirs(output_path, exist_ok=True)
        
        # 保存为JSON
        results_data = []
        for page in self.collected_pages:
            results_data.append({
                'id': page.id,
                'url': page.url,
                'title': page.title,
                'description': page.description,
                'category': page.category,
                'collected_at': page.collected_at,
                'colors': page.colors,
                'fonts': page.fonts,
                'layout_type': page.layout_type,
                'design_score': page.design_score,
                'ai_elements': page.ai_elements
            })
        
        output_file = os.path.join(output_path, f'collected_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 采集结果已保存: {output_file}")
        print(f"   共 {len(results_data)} 条参考")
        
        return output_file
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return self.stats

# 单例
_collector_engine = None

def get_collector_engine(config_path: str = None) -> CollectorEngine:
    """获取采集引擎单例"""
    global _collector_engine
    if _collector_engine is None:
        _collector_engine = CollectorEngine(config_path)
    return _collector_engine

if __name__ == "__main__":
    # 测试
    engine = get_collector_engine()
    print("采集引擎初始化完成")
    print(f"配置: {json.dumps(engine.config.get('collector', {}), indent=2)}")
