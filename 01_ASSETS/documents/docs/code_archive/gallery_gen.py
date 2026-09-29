#!/usr/bin/env python3
"""
作品库页面自动生成器
从数据库读取媒体文件，自动生成瀑布流展示页面
支持分类筛选、搜索、标签、元信息展示
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

# 确权标识
DID = "DID-BR-000002"
TRACE_MARK = "Ω₀⊂⊙∞⊂Ω"

class GalleryGenerator:
    """作品库页面生成器"""
    
    def __init__(self, db, output_dir: str = "/opt/storage/media/gallery"):
        self.db = db
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_file_url(self, file_info: Dict) -> str:
        """获取文件的访问URL（相对路径）"""
        storage_path = file_info['storage_path']
        # 转换为相对URL：假设storage根目录在 /opt/storage/media
        # 作品库页面在 /opt/storage/media/gallery
        # 所以相对路径是 ../
        if storage_path.startswith('/opt/storage/media/'):
            relative = storage_path.replace('/opt/storage/media/', '../')
            return relative
        return storage_path
    
    def _get_thumbnail_url(self, file_info: Dict) -> str:
        """获取缩略图URL（视频用第一帧，图片用原图）"""
        # 简化版：图片用原图，视频暂时用占位图
        if file_info['file_type'] == 'image':
            return self._get_file_url(file_info)
        elif file_info['file_type'] == 'video':
            # 视频缩略图可以后续用ffmpeg生成，这里先用占位
            return "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='400' height='300'%3E%3Crect fill='%231a1a2e' width='400' height='300'/%3E%3Ctext fill='%23f59e0b' font-size='48' x='50%25' y='50%25' text-anchor='middle' dy='.3em'%3E▶%3C/text%3E%3C/svg%3E"
        else:
            return "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='400' height='300'%3E%3Crect fill='%231a1a2e' width='400' height='300'/%3E%3Ctext fill='%23f59e0b' font-size='24' x='50%25' y='50%25' text-anchor='middle' dy='.3em'%3E媒体文件%3C/text%3E%3C/svg%3E"
    
    def generate_index_page(self) -> str:
        """生成作品库首页"""
        # 获取统计信息
        stats = self.db.get_stats()
        tags = self.db.get_all_tags()
        
        # 获取最近的文件（按类型分组，每种类型取最新的）
        recent_images = self.db.list_files(file_type='image', limit=24)
        recent_videos = self.db.list_files(file_type='video', limit=12)
        recent_all = self.db.list_files(limit=48)
        
        # 生成图片卡片HTML
        def generate_card(file_info):
            file_url = self._get_file_url(file_info)
            thumb_url = self._get_thumbnail_url(file_info)
            file_type = file_info['file_type']
            type_icon = {'image': '🖼️', 'video': '🎬', 'audio': '🎵', 'other': '📁'}.get(file_type, '📁')
            title = file_info.get('title') or file_info['filename']
            tags_html = ''.join([f'<span class="tag">{t}</span>' for t in file_info.get('tags', [])[:3]])
            size_mb = round(file_info['file_size'] / 1024 / 1024, 2)
            date_str = file_info['created_at'][:10] if file_info.get('created_at') else ''
            hash_short = file_info['file_hash'][:8]
            
            # 视频卡片用video标签
            if file_type == 'video':
                media_html = f'''<video class="card-media" src="{file_url}" muted loop playsinline preload="metadata"></video>'''
            else:
                media_html = f'''<img class="card-media" src="{thumb_url}" alt="{title}" loading="lazy">'''
            
            return f'''
            <div class="gallery-card" data-type="{file_type}" data-hash="{file_info['file_hash']}">
                <a href="{file_url}" target="_blank" class="card-link">
                    <div class="card-media-wrapper">
                        {media_html}
                        <div class="card-type-badge">{type_icon} {file_type}</div>
                    </div>
                    <div class="card-info">
                        <div class="card-title">{title}</div>
                        <div class="card-meta">
                            <span>{size_mb} MB</span>
                            <span>·</span>
                            <span>{date_str}</span>
                        </div>
                        <div class="card-tags">{tags_html}</div>
                        <div class="card-hash">#{hash_short}</div>
                    </div>
                </a>
            </div>'''
        
        images_html = '\n'.join([generate_card(f) for f in recent_images])
        videos_html = '\n'.join([generate_card(f) for f in recent_videos])
        all_html = '\n'.join([generate_card(f) for f in recent_all])
        
        tags_html = ''.join([f'<button class="filter-tag" data-tag="{t["name"]}">{t["name"]} ({t["count"]})</button>' for t in tags[:20]])
        
        html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="火斗云智AI作品库 - 豆包APP生成的图片视频自动归档展示，元秩序确权锁档">
    <title>火斗云智 · AI作品库</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0a0a0f;
            color: #e0e0e0;
            min-height: 100vh;
        }}
        .header {{
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            padding: 40px 20px;
            text-align: center;
            border-bottom: 1px solid #2a2a4a;
        }}
        .header h1 {{
            font-size: 2.5em;
            background: linear-gradient(135deg, #f59e0b, #10b981);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
        }}
        .header p {{ color: #888; font-size: 1.1em; }}
        .stats-bar {{
            display: flex;
            justify-content: center;
            gap: 40px;
            margin-top: 20px;
            flex-wrap: wrap;
        }}
        .stat-item {{ text-align: center; }}
        .stat-num {{ font-size: 1.8em; font-weight: bold; color: #f59e0b; }}
        .stat-label {{ font-size: 0.85em; color: #888; }}
        .container {{ max-width: 1400px; margin: 0 auto; padding: 30px 20px; }}
        .filters {{
            display: flex;
            gap: 10px;
            margin-bottom: 30px;
            flex-wrap: wrap;
            align-items: center;
        }}
        .filter-btn {{
            padding: 8px 16px;
            border: 1px solid #3a3a5a;
            background: transparent;
            color: #aaa;
            border-radius: 20px;
            cursor: pointer;
            transition: all 0.3s;
            font-size: 0.9em;
        }}
        .filter-btn:hover, .filter-btn.active {{
            background: #f59e0b;
            color: #000;
            border-color: #f59e0b;
        }}
        .search-box {{
            flex: 1;
            min-width: 200px;
            padding: 8px 16px;
            border: 1px solid #3a3a5a;
            background: #1a1a2e;
            color: #e0e0e0;
            border-radius: 20px;
            font-size: 0.9em;
        }}
        .search-box:focus {{ outline: none; border-color: #f59e0b; }}
        .section-title {{
            font-size: 1.5em;
            margin: 30px 0 20px;
            color: #f59e0b;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .gallery-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 20px;
        }}
        .gallery-card {{
            background: #1a1a2e;
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid #2a2a4a;
            transition: all 0.3s;
        }}
        .gallery-card:hover {{
            transform: translateY(-4px);
            border-color: #f59e0b;
            box-shadow: 0 10px 30px rgba(245, 158, 11, 0.2);
        }}
        .card-link {{ text-decoration: none; color: inherit; display: block; }}
        .card-media-wrapper {{
            position: relative;
            aspect-ratio: 4/3;
            overflow: hidden;
            background: #0a0a0f;
        }}
        .card-media {{
            width: 100%;
            height: 100%;
            object-fit: cover;
        }}
        .card-type-badge {{
            position: absolute;
            top: 10px;
            left: 10px;
            background: rgba(0,0,0,0.7);
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 0.8em;
        }}
        .card-info {{ padding: 15px; }}
        .card-title {{
            font-size: 1em;
            font-weight: 600;
            margin-bottom: 8px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        .card-meta {{
            font-size: 0.8em;
            color: #888;
            margin-bottom: 8px;
            display: flex;
            gap: 6px;
        }}
        .card-tags {{ display: flex; gap: 5px; flex-wrap: wrap; margin-bottom: 8px; }}
        .tag {{
            font-size: 0.7em;
            padding: 2px 8px;
            background: #2a2a4a;
            border-radius: 10px;
            color: #10b981;
        }}
        .card-hash {{
            font-size: 0.75em;
            color: #666;
            font-family: monospace;
        }}
        .footer {{
            text-align: center;
            padding: 40px 20px;
            color: #666;
            font-size: 0.85em;
            border-top: 1px solid #2a2a4a;
            margin-top: 50px;
        }}
        .footer .did {{ color: #f59e0b; font-family: monospace; }}
        @media (max-width: 768px) {{
            .header h1 {{ font-size: 1.8em; }}
            .gallery-grid {{ grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 10px; }}
            .stats-bar {{ gap: 20px; }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔥 火斗云智 · AI作品库</h1>
        <p>豆包APP生成的图片视频 · 自动归档 · 元秩序确权锁档</p>
        <div class="stats-bar">
            <div class="stat-item">
                <div class="stat-num">{stats['total_files']}</div>
                <div class="stat-label">总作品数</div>
            </div>
            <div class="stat-item">
                <div class="stat-num">{stats['type_counts'].get('image', 0)}</div>
                <div class="stat-label">图片</div>
            </div>
            <div class="stat-item">
                <div class="stat-num">{stats['type_counts'].get('video', 0)}</div>
                <div class="stat-label">视频</div>
            </div>
            <div class="stat-item">
                <div class="stat-num">{stats['total_size_mb']} MB</div>
                <div class="stat-label">总大小</div>
            </div>
            <div class="stat-item">
                <div class="stat-num">{stats['archive_counts'].get('archived', 0)}</div>
                <div class="stat-label">已确权</div>
            </div>
        </div>
    </div>
    
    <div class="container">
        <div class="filters">
            <button class="filter-btn active" data-filter="all">全部</button>
            <button class="filter-btn" data-filter="image">🖼️ 图片</button>
            <button class="filter-btn" data-filter="video">🎬 视频</button>
            <input type="text" class="search-box" placeholder="搜索作品名称、标签、哈希..." id="searchInput">
        </div>
        
        <div class="filter-tags" style="margin-bottom: 20px; display: flex; gap: 8px; flex-wrap: wrap;">
            {tags_html}
        </div>
        
        <div class="section-title">✨ 最新作品</div>
        <div class="gallery-grid" id="galleryGrid">
            {all_html}
        </div>
    </div>
    
    <div class="footer">
        <p>火斗云智AIOS · 元极恒一自治体系 · 全自动图片视频归档展示系统</p>
        <p class="did">确权DID: {DID} | 溯源: {TRACE_MARK}</p>
        <p>最后更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    <script>
        // 筛选功能
        document.querySelectorAll('.filter-btn').forEach(btn => {{
            btn.addEventListener('click', function() {{
                document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
                this.classList.add('active');
                const filter = this.dataset.filter;
                document.querySelectorAll('.gallery-card').forEach(card => {{
                    if (filter === 'all' || card.dataset.type === filter) {{
                        card.style.display = 'block';
                    }} else {{
                        card.style.display = 'none';
                    }}
                }});
            }});
        }});
        
        // 搜索功能
        document.getElementById('searchInput').addEventListener('input', function() {{
            const query = this.value.toLowerCase();
            document.querySelectorAll('.gallery-card').forEach(card => {{
                const title = card.querySelector('.card-title').textContent.toLowerCase();
                const hash = card.dataset.hash.toLowerCase();
                const tags = card.querySelector('.card-tags').textContent.toLowerCase();
                if (title.includes(query) || hash.includes(query) || tags.includes(query)) {{
                    card.style.display = 'block';
                }} else {{
                    card.style.display = 'none';
                }}
            }});
        }});
        
        // 标签筛选
        document.querySelectorAll('.filter-tag').forEach(tag => {{
            tag.addEventListener('click', function() {{
                const tagName = this.dataset.tag;
                document.querySelectorAll('.gallery-card').forEach(card => {{
                    const tags = card.querySelector('.card-tags').textContent;
                    if (tags.includes(tagName)) {{
                        card.style.display = 'block';
                    }} else {{
                        card.style.display = 'none';
                    }}
                }});
            }});
        }});
        
        // 视频悬停播放
        document.querySelectorAll('.gallery-card video').forEach(video => {{
            video.parentElement.parentElement.addEventListener('mouseenter', () => video.play());
            video.parentElement.parentElement.addEventListener('mouseleave', () => video.pause());
        }});
    </script>
</body>
</html>'''
        
        # 写入文件
        output_path = self.output_dir / "index.html"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        return str(output_path)
    
    def regenerate_all(self) -> Dict:
        """重新生成所有作品库页面"""
        results = {}
        
        # 生成首页
        index_path = self.generate_index_page()
        results['index'] = index_path
        
        # 获取统计
        stats = self.db.get_stats()
        results['stats'] = stats
        results['generated_at'] = datetime.now().isoformat()
        
        return results


if __name__ == "__main__":
    print("作品库页面生成器模块加载完成")
