#!/usr/bin/env python3
"""
官网存量资产迁移脚本
功能：将官网原有静态资源迁移到标准 /portfolio/ 目录结构
用法：python3 migrate_site_assets.py <官网静态目录> <目标目录>
"""
import os
import sys
import shutil
import json
import hashlib
from datetime import datetime

IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.svg'}

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()

def classify_image(fname, series_hints):
    """根据文件名判断系列"""
    name_lower = fname.lower()
    for series, keywords in series_hints.items():
        for kw in keywords:
            if kw in name_lower:
                return series
    return "official"

def main():
    if len(sys.argv) < 3:
        print("用法: python3 migrate_site_assets.py <官网静态目录> <目标目录>")
        sys.exit(1)
    
    src_dir = sys.argv[1]
    dst_dir = sys.argv[2]
    
    series_hints = {
        "kunlun": ["kunlun", "昆仑", "九天", "女娲", "keyframe", "帧"],
        "blog": ["blog", "cover", "csdn", "掘金", "封面"],
        "official": ["logo", "banner", "hero", "bg", "背景"]
    }
    
    moved = []
    for root, dirs, files in os.walk(src_dir):
        for fname in files:
            ext = os.path.splitext(fname)[1].lower()
            if ext not in IMAGE_EXTS:
                continue
            
            src_path = os.path.join(root, fname)
            series = classify_image(fname, series_hints)
            
            # 目标路径
            series_dir = os.path.join(dst_dir, series)
            os.makedirs(series_dir, exist_ok=True)
            dst_path = os.path.join(series_dir, fname)
            
            shutil.copy2(src_path, dst_path)
            moved.append({
                "old_path": src_path,
                "new_path": dst_path,
                "series": series,
                "sha256": sha256_file(dst_path),
                "size_kb": round(os.path.getsize(dst_path)/1024, 1)
            })
    
    report = {
        "migration_time": datetime.now().isoformat(),
        "total_moved": len(moved),
        "by_series": {},
        "files": moved
    }
    for m in moved:
        s = m["series"]
        report["by_series"][s] = report["by_series"].get(s, 0) + 1
    
    report_path = os.path.join(os.path.dirname(__file__), "migration_report.json")
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"✅ 迁移完成: {len(moved)}个文件")
    for s, c in report["by_series"].items():
        print(f"  {s}: {c}个")
    print(f"报告: {report_path}")

if __name__ == "__main__":
    main()
