"""
设计知识库 - 存储和管理设计参考知识
支持去重、分类、检索、统计
"""
import os
import sys
import json
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from collections import Counter, defaultdict

@dataclass
class KnowledgeEntry:
    """知识条目"""
    id: str
    type: str  # color_palette/typography/layout/interaction/trend/recommendation
    title: str
    content: Dict[str, Any]
    source_url: str
    source_category: str
    created_at: str
    tags: List[str] = field(default_factory=list)
    usage_count: int = 0
    rating: float = 0.0

class DesignKnowledgeBase:
    """设计知识库"""
    
    def __init__(self, base_path: str = "./knowledge_base"):
        self.base_path = base_path
        os.makedirs(base_path, exist_ok=True)
        self.entries: Dict[str, KnowledgeEntry] = {}
        self.index = defaultdict(list)
        self.stats = {
            'total_entries': 0,
            'by_type': Counter(),
            'by_category': Counter(),
            'by_source': Counter(),
            'top_tags': Counter()
        }
        self._load()
    
    def _get_entry_file(self, entry_id: str) -> str:
        """获取条目文件路径"""
        return os.path.join(self.base_path, f"{entry_id}.json")
    
    def _load(self):
        """加载知识库"""
        if not os.path.exists(self.base_path):
            return
        
        for filename in os.listdir(self.base_path):
            if filename.endswith('.json'):
                try:
                    filepath = os.path.join(self.base_path, filename)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    entry = KnowledgeEntry(
                        id=data['id'],
                        type=data['type'],
                        title=data['title'],
                        content=data['content'],
                        source_url=data.get('source_url', ''),
                        source_category=data.get('source_category', ''),
                        created_at=data.get('created_at', datetime.now().isoformat()),
                        tags=data.get('tags', []),
                        usage_count=data.get('usage_count', 0),
                        rating=data.get('rating', 0.0)
                    )
                    
                    self.entries[entry.id] = entry
                    self._update_index(entry)
                    self.stats['total_entries'] += 1
                    self.stats['by_type'][entry.type] += 1
                    self.stats['by_category'][entry.source_category] += 1
                    self.stats['by_source'][entry.source_url] += 1
                    for tag in entry.tags:
                        self.stats['top_tags'][tag] += 1
                        
                except Exception as e:
                    print(f"  ⚠️  加载条目失败: {filename} - {e}")
    
    def _update_index(self, entry: KnowledgeEntry):
        """更新索引"""
        self.index[entry.type].append(entry.id)
        for tag in entry.tags:
            self.index[f"tag:{tag}"].append(entry.id)
        if entry.source_category:
            self.index[f"category:{entry.source_category}"].append(entry.id)
    
    def _generate_id(self, type_name: str, content: Dict) -> str:
        """生成唯一ID"""
        content_str = json.dumps(content, sort_keys=True)
        hash_str = hashlib.md5(f"{type_name}:{content_str}".encode()).hexdigest()[:12]
        return f"{type_name}_{hash_str}"
    
    def add_entry(self, type_name: str, title: str, content: Dict,
                  source_url: str = "", source_category: str = "",
                  tags: List[str] = None) -> Optional[KnowledgeEntry]:
        """添加知识条目"""
        entry_id = self._generate_id(type_name, content)
        
        # 去重检查
        if entry_id in self.entries:
            self.entries[entry_id].usage_count += 1
            return self.entries[entry_id]
        
        entry = KnowledgeEntry(
            id=entry_id,
            type=type_name,
            title=title,
            content=content,
            source_url=source_url,
            source_category=source_category,
            created_at=datetime.now().isoformat(),
            tags=tags or []
        )
        
        # 保存到文件
        try:
            filepath = self._get_entry_file(entry_id)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump({
                    'id': entry.id,
                    'type': entry.type,
                    'title': entry.title,
                    'content': entry.content,
                    'source_url': entry.source_url,
                    'source_category': entry.source_category,
                    'created_at': entry.created_at,
                    'tags': entry.tags,
                    'usage_count': entry.usage_count,
                    'rating': entry.rating
                }, f, ensure_ascii=False, indent=2)
            
            self.entries[entry_id] = entry
            self._update_index(entry)
            self.stats['total_entries'] += 1
            self.stats['by_type'][type_name] += 1
            if source_category:
                self.stats['by_category'][source_category] += 1
            for tag in (tags or []):
                self.stats['top_tags'][tag] += 1
            
            return entry
        except Exception as e:
            print(f"  ⚠️  保存条目失败: {e}")
            return None
    
    def add_from_analysis_report(self, report: Dict) -> int:
        """从分析报告批量添加知识"""
        added_count = 0
        
        # 添加配色方案
        colors = report.get('color_palette', {})
        if colors.get('all_colors'):
            self.add_entry(
                type_name='color_palette',
                title=f"{report.get('title', 'Unknown')} - 配色方案",
                content=colors,
                source_url=report.get('url', ''),
                source_category=report.get('source_category', ''),
                tags=['colors', colors.get('color_scheme_type', '')]
            )
            added_count += 1
        
        # 添加排版配置
        typography = report.get('typography', {})
        if typography.get('heading_font'):
            self.add_entry(
                type_name='typography',
                title=f"{report.get('title', 'Unknown')} - 排版配置",
                content=typography,
                source_url=report.get('url', ''),
                source_category=report.get('source_category', ''),
                tags=['typography', typography.get('font_scale', '')]
            )
            added_count += 1
        
        # 添加布局配置
        layout = report.get('layout', {})
        if layout.get('layout_type'):
            self.add_entry(
                type_name='layout',
                title=f"{report.get('title', 'Unknown')} - 布局配置",
                content=layout,
                source_url=report.get('url', ''),
                source_category=report.get('source_category', ''),
                tags=['layout', layout.get('spacing_system', '')]
            )
            added_count += 1
        
        # 添加交互模式
        for interaction in report.get('interactions', []):
            self.add_entry(
                type_name='interaction',
                title=interaction.get('pattern_name', 'Unknown'),
                content=interaction,
                source_url=report.get('url', ''),
                source_category=report.get('source_category', ''),
                tags=['interaction', 'ai' if interaction.get('ai_relevance', 0) > 0.7 else '']
            )
            added_count += 1
        
        # 添加设计趋势
        for trend in report.get('design_trends', []):
            self.add_entry(
                type_name='trend',
                title=trend,
                content={'name': trend, 'source': report.get('title', '')},
                source_url=report.get('url', ''),
                source_category=report.get('source_category', ''),
                tags=['trend', trend]
            )
            added_count += 1
        
        # 添加AI设计元素
        for element in report.get('ai_design_elements', []):
            self.add_entry(
                type_name='ai_element',
                title=element,
                content={'name': element, 'source': report.get('title', '')},
                source_url=report.get('url', ''),
                source_category=report.get('source_category', ''),
                tags=['ai', element]
            )
            added_count += 1
        
        return added_count
    
    def search(self, query: str, type_filter: str = None, 
               tag_filter: str = None, limit: int = 20) -> List[KnowledgeEntry]:
        """搜索知识库"""
        results = []
        query_lower = query.lower()
        
        for entry in self.entries.values():
            # 类型过滤
            if type_filter and entry.type != type_filter:
                continue
            
            # 标签过滤
            if tag_filter and tag_filter not in entry.tags:
                continue
            
            # 关键词匹配
            if (query_lower in entry.title.lower() or
                query_lower in entry.type.lower() or
                any(query_lower in tag.lower() for tag in entry.tags)):
                results.append(entry)
        
        # 按使用次数和评分排序
        results.sort(key=lambda x: (x.usage_count, x.rating), reverse=True)
        return results[:limit]
    
    def get_by_type(self, type_name: str, limit: int = 50) -> List[KnowledgeEntry]:
        """按类型获取"""
        entries = [e for e in self.entries.values() if e.type == type_name]
        entries.sort(key=lambda x: x.usage_count, reverse=True)
        return entries[:limit]
    
    def get_top_trends(self, limit: int = 10) -> List[Dict]:
        """获取热门设计趋势"""
        trend_entries = self.get_by_type('trend', limit=100)
        trend_counter = Counter()
        for entry in trend_entries:
            trend_counter[entry.title] += 1
        
        return [{'name': name, 'count': count} for name, count in trend_counter.most_common(limit)]
    
    def get_top_colors(self, limit: int = 10) -> List[Dict]:
        """获取热门配色"""
        color_entries = self.get_by_type('color_palette', limit=100)
        color_counter = Counter()
        for entry in color_entries:
            colors = entry.content.get('all_colors', [])
            for color in colors[:3]:  # 只统计前3个主色
                color_counter[color] += 1
        
        return [{'color': color, 'count': count} for color, count in color_counter.most_common(limit)]
    
    def get_top_fonts(self, limit: int = 10) -> List[Dict]:
        """获取热门字体"""
        typography_entries = self.get_by_type('typography', limit=100)
        font_counter = Counter()
        for entry in typography_entries:
            heading = entry.content.get('heading_font', '')
            body = entry.content.get('body_font', '')
            if heading:
                font_counter[heading] += 1
            if body:
                font_counter[body] += 1
        
        return [{'font': font, 'count': count} for font, count in font_counter.most_common(limit)]
    
    def get_ai_design_patterns(self, limit: int = 10) -> List[Dict]:
        """获取AI设计模式"""
        ai_entries = self.get_by_type('ai_element', limit=100)
        ai_counter = Counter()
        for entry in ai_entries:
            ai_counter[entry.title] += 1
        
        return [{'pattern': name, 'count': count} for name, count in ai_counter.most_common(limit)]
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            'total_entries': self.stats['total_entries'],
            'by_type': dict(self.stats['by_type']),
            'by_category': dict(self.stats['by_category']),
            'top_tags': dict(self.stats['top_tags'].most_common(20)),
            'top_trends': self.get_top_trends(),
            'top_colors': self.get_top_colors(),
            'top_fonts': self.get_top_fonts(),
            'ai_design_patterns': self.get_ai_design_patterns()
        }
    
    def export_summary(self, output_path: str) -> str:
        """导出知识库摘要"""
        os.makedirs(output_path, exist_ok=True)
        
        summary = {
            'generated_at': datetime.now().isoformat(),
            'stats': self.get_stats(),
            'top_color_palettes': [
                {'title': e.title, 'colors': e.content.get('all_colors', [])}
                for e in self.get_by_type('color_palette', limit=5)
            ],
            'top_typography': [
                {'title': e.title, 'fonts': e.content}
                for e in self.get_by_type('typography', limit=5)
            ],
            'top_layouts': [
                {'title': e.title, 'layout': e.content}
                for e in self.get_by_type('layout', limit=5)
            ],
            'top_interactions': [
                {'title': e.title, 'pattern': e.content}
                for e in self.get_by_type('interaction', limit=10)
            ],
            'design_trends': self.get_top_trends(limit=15),
            'ai_design_patterns': self.get_ai_design_patterns(limit=10)
        }
        
        output_file = os.path.join(output_path, f'knowledge_summary_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        return output_file

# 单例
_knowledge_base = None

def get_knowledge_base(base_path: str = None) -> DesignKnowledgeBase:
    """获取知识库单例"""
    global _knowledge_base
    if _knowledge_base is None:
        _knowledge_base = DesignKnowledgeBase(base_path or "./knowledge_base")
    return _knowledge_base

if __name__ == "__main__":
    kb = get_knowledge_base()
    print("设计知识库初始化完成")
    print(f"已加载条目: {kb.stats['total_entries']}")
