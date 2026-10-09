#!/usr/bin/env python3
"""
存量关键帧资产批量导入脚本
功能：扫描本地已有关键帧目录，自动质检+生成元数据+纳入作品库索引
用法：python3 import_existing.py <扫描目录> <系列名>
"""
import os
import sys
import json
import hashlib
from datetime import datetime

SUPPORTED_EXTS = {'.png', '.jpg', '.jpeg', '.webp'}

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()

def generate_asset_id(series):
    date_str = datetime.now().strftime('%Y%m%d')
    seq = str(hash(datetime.now().isoformat()) % 10000).zfill(4)
    prefix = series[:3].upper()
    return f"ART-{prefix}-{date_str}-{seq}"

def scan_directory(scan_dir, series="legacy"):
    results = []
    for root, dirs, files in os.walk(scan_dir):
        for fname in files:
            ext = os.path.splitext(fname)[1].lower()
            if ext in SUPPORTED_EXTS:
                fpath = os.path.join(root, fname)
                size_mb = round(os.path.getsize(fpath) / (1024*1024), 2)
                results.append({
                    "file": fpath,
                    "name": fname,
                    "size_mb": size_mb,
                    "sha256": sha256_file(fpath),
                    "asset_id": generate_asset_id(series),
                    "series": series,
                    "import_time": datetime.now().isoformat()
                })
    return results

def main():
    if len(sys.argv) < 2:
        print("用法: python3 import_existing.py <扫描目录> [系列名]")
        sys.exit(1)
    
    scan_dir = sys.argv[1]
    series = sys.argv[2] if len(sys.argv) > 2 else "legacy"
    
    if not os.path.isdir(scan_dir):
        print(f"目录不存在: {scan_dir}")
        sys.exit(1)
    
    items = scan_directory(scan_dir, series)
    print(f"扫描到 {len(items)} 个图片资产")
    
    output_file = os.path.join(os.path.dirname(__file__), f"import_plan_{series}.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "series": series,
            "total": len(items),
            "items": items,
            "generated_at": datetime.now().isoformat()
        }, f, indent=2, ensure_ascii=False)
    
    print(f"导入计划已生成: {output_file}")
    print("下一步: 人工质检 -> 生成WebP -> 上传云盘 -> 更新索引")

if __name__ == "__main__":
    main()
