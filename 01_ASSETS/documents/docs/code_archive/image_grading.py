#!/usr/bin/env python3
"""
图片五级分级脚本 v1.0
S/A/B/C/D 分级
"""
import os
import json
import shutil
from PIL import Image
from datetime import datetime

STORAGE_BASE = "/opt/storage/images"
DRAMA_BASE = "/www/wwwroot/huodouai.com/drama"
GALLERY_S_DIR = "/www/wwwroot/huodouai.com/gallery/s"

os.makedirs(GALLERY_S_DIR, exist_ok=True)

def grade_image(filepath):
    """对单张图片进行分级"""
    grade = 'C'
    score = 50
    reasons = []
    
    try:
        size_kb = os.path.getsize(filepath) / 1024
        
        with Image.open(filepath) as img:
            w, h = img.width, img.height
            ratio = w / h if h > 0 else 0
            
            # S级标准：≥1080x1920, ≥500KB, 9:16±5%
            if w >= 1080 and h >= 1920 and size_kb >= 500 and abs(ratio - 9/16) < 0.1:
                grade = 'S'
                score = 95
                reasons.append('高分辨率+竖屏比例')
            # A级标准：≥720x1280, ≥200KB, 9:16±10%
            elif w >= 720 and h >= 1280 and size_kb >= 200 and abs(ratio - 9/16) < 0.2:
                grade = 'A'
                score = 80
                reasons.append('高质量+竖屏比例')
            # B级标准：≥480x720, ≥100KB
            elif w >= 480 and h >= 720 and size_kb >= 100:
                grade = 'B'
                score = 65
                reasons.append('可用素材')
            # C级：其他
            else:
                grade = 'C'
                score = 45
                reasons.append('待优化')
            
            # 额外加分：接近9:16的竖屏
            if abs(ratio - 9/16) < 0.05:
                score += 5
                reasons.append('完美竖屏比例')
            
            # 检查是否是纯色/空白
            if w > 100 and h > 100:
                small = img.resize((8, 8))
                pixels = list(small.getdata())
                if pixels:
                    avg_r = sum(p[0] for p in pixels) / len(pixels)
                    avg_g = sum(p[1] for p in pixels) / len(pixels)
                    avg_b = sum(p[2] for p in pixels) / len(pixels)
                    # 计算方差（简单版）
                    variance = sum(abs(p[0]-avg_r) + abs(p[1]-avg_g) + abs(p[2]-avg_b) for p in pixels) / (len(pixels) * 3)
                    if variance < 5:
                        grade = 'D'
                        score = 10
                        reasons.append('纯色/空白图')
    
    except Exception as e:
        grade = 'D'
        score = 0
        reasons.append(f'损坏: {str(e)[:30]}')
    
    return {
        'path': filepath,
        'grade': grade,
        'score': score,
        'reasons': reasons,
        'size_kb': round(size_kb, 1) if 'size_kb' in dir() else 0,
        'resolution': f"{w}x{h}" if 'w' in dir() else 'unknown'
    }

def main():
    print(f"=== 图片五级分级开始 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
    print()
    
    all_images = []
    
    # 扫描storage
    print("扫描storage/images/...")
    for root, dirs, files in os.walk(STORAGE_BASE):
        for f in files:
            if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                all_images.append(os.path.join(root, f))
    
    # 扫描drama
    print("扫描drama/...")
    for root, dirs, files in os.walk(DRAMA_BASE):
        for f in files:
            if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                all_images.append(os.path.join(root, f))
    
    print(f"总计：{len(all_images)} 张图片")
    print()
    
    # 分级
    grades = {'S': [], 'A': [], 'B': [], 'C': [], 'D': []}
    
    for i, img_path in enumerate(all_images):
        result = grade_image(img_path)
        grades[result['grade']].append(result)
        if (i+1) % 500 == 0:
            print(f"  已分级 {i+1}/{len(all_images)}...")
    
    # 输出统计
    print()
    print("=== 分级结果 ===")
    for g in ['S', 'A', 'B', 'C', 'D']:
        count = len(grades[g])
        pct = round(count / len(all_images) * 100, 1)
        print(f"  {g}级: {count} 张 ({pct}%)")
    
    # S级精品复制到专门目录
    print()
    print(f"=== 复制S级精品到 {GALLERY_S_DIR} ===")
    s_copied = 0
    for item in grades['S']:
        src = item['path']
        fname = os.path.basename(src)
        dst = os.path.join(GALLERY_S_DIR, fname)
        try:
            shutil.copy2(src, dst)
            s_copied += 1
        except Exception as e:
            pass
    
    print(f"  已复制 {s_copied} 张S级精品")
    
    # 保存分级报告
    report = {
        'timestamp': datetime.now().isoformat(),
        'total': len(all_images),
        'grade_counts': {g: len(grades[g]) for g in ['S', 'A', 'B', 'C', 'D']},
        's_grade_samples': [{'path': item['path'], 'score': item['score']} for item in grades['S'][:20]]
    }
    
    report_path = '/opt/auto-evolve/image_grading_report.json'
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print()
    print(f"分级报告: {report_path}")
    print("=== 分级完成 ===")

if __name__ == '__main__':
    main()
