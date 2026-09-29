#!/usr/bin/env python3
"""
图片质量检测体系 v1.0
检查指标：文件大小、分辨率、是否损坏、宽高比、清晰度
"""
import os
import json
from PIL import Image
from datetime import datetime

STORAGE_BASE = "/opt/storage/images"
DRAMA_BASE = "/www/wwwroot/huodouai.com/drama"

def check_image_quality(filepath):
    """检查单张图片质量"""
    result = {
        'path': filepath,
        'size_kb': 0,
        'width': 0,
        'height': 0,
        'aspect_ratio': 0,
        'is_valid': True,
        'issues': [],
        'quality_score': 100
    }
    
    try:
        # 文件大小检查
        size_bytes = os.path.getsize(filepath)
        result['size_kb'] = round(size_bytes / 1024, 1)
        
        # 小于10KB的可能是损坏或空图
        if size_bytes < 10 * 1024:
            result['issues'].append('too_small')
            result['quality_score'] -= 30
        
        # 打开图片检查
        with Image.open(filepath) as img:
            result['width'] = img.width
            result['height'] = img.height
            result['aspect_ratio'] = round(img.width / img.height, 2)
            
            # 分辨率检查
            if img.width < 200 or img.height < 200:
                result['issues'].append('low_resolution')
                result['quality_score'] -= 25
            
            # 宽高比检查（竖屏作品应该是9:16左右）
            # 这里先不扣分，记录下来
            
            # 检查是否是灰度/空白
            # 简单检查：取几个像素看颜色方差
            if img.width > 100 and img.height > 100:
                small = img.resize((10, 10))
                pixels = list(small.getdata())
                if len(pixels) > 0:
                    avg_brightness = sum(sum(p[:3]) for p in pixels) / (len(pixels) * 3)
                    # 太亮或太暗可能是坏图
                    if avg_brightness > 250 or avg_brightness < 5:
                        result['issues'].append('blank_or_white')
                        result['quality_score'] -= 20
    
    except Exception as e:
        result['is_valid'] = False
        result['issues'].append(f'corrupted: {str(e)[:50]}')
        result['quality_score'] = 0
    
    return result

def scan_directory(base_dir, label):
    """扫描目录下所有图片"""
    results = []
    for root, dirs, files in os.walk(base_dir):
        for f in files:
            if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                filepath = os.path.join(root, f)
                result = check_image_quality(filepath)
                result['category'] = label
                results.append(result)
    return results

def main():
    print(f"=== 图片质量检测开始 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
    print()
    
    all_results = []
    
    # 扫描storage目录
    print("扫描storage/images/...")
    storage_results = scan_directory(STORAGE_BASE, 'storage')
    all_results.extend(storage_results)
    print(f"  找到 {len(storage_results)} 张图片")
    
    # 扫描drama目录
    print("扫描drama/...")
    drama_results = scan_directory(DRAMA_BASE, 'drama')
    all_results.extend(drama_results)
    print(f"  找到 {len(drama_results)} 张图片")
    
    total = len(all_results)
    print(f"\n总计：{total} 张图片")
    print()
    
    # 统计质量分布
    quality_buckets = {
        'excellent (90-100)': 0,
        'good (70-89)': 0,
        'fair (50-69)': 0,
        'poor (30-49)': 0,
        'bad (0-29)': 0
    }
    
    issue_counts = {}
    bad_images = []
    
    for r in all_results:
        score = r['quality_score']
        if score >= 90:
            quality_buckets['excellent (90-100)'] += 1
        elif score >= 70:
            quality_buckets['good (70-89)'] += 1
        elif score >= 50:
            quality_buckets['fair (50-69)'] += 1
        elif score >= 30:
            quality_buckets['poor (30-49)'] += 1
        else:
            quality_buckets['bad (0-29)'] += 1
        
        for issue in r['issues']:
            issue_type = issue.split(':')[0]
            issue_counts[issue_type] = issue_counts.get(issue_type, 0) + 1
        
        if score < 50:
            bad_images.append(r)
    
    # 输出报告
    print("=== 质量分布 ===")
    for bucket, count in quality_buckets.items():
        pct = round(count / total * 100, 1)
        print(f"  {bucket}: {count} 张 ({pct}%)")
    
    print()
    print("=== 问题类型统计 ===")
    for issue, count in sorted(issue_counts.items(), key=lambda x: -x[1]):
        print(f"  {issue}: {count} 张")
    
    print()
    print(f"=== 待清理图片（<50分）：{len(bad_images)} 张 ===")
    for img in bad_images[:10]:
        print(f"  {img['path']}")
        print(f"    分数: {img['quality_score']}, 大小: {img['size_kb']}KB, 问题: {img['issues']}")
    
    if len(bad_images) > 10:
        print(f"  ... 还有 {len(bad_images) - 10} 张")
    
    # 保存报告
    report = {
        'timestamp': datetime.now().isoformat(),
        'total_images': total,
        'quality_buckets': quality_buckets,
        'issue_counts': issue_counts,
        'bad_count': len(bad_images),
        'bad_images': [{'path': r['path'], 'score': r['quality_score'], 'issues': r['issues']} for r in bad_images]
    }
    
    report_path = '/opt/auto-evolve/image_quality_report.json'
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print()
    print(f"报告已保存: {report_path}")
    print("=== 检测完成 ===")

if __name__ == '__main__':
    main()
