#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
资产清单导出工具
扫描指定目录，生成SHA256哈希台账 + 资产包元数据
用法：python3 export_asset_manifest.py <资产目录> [--output <输出文件>]
"""
import os, sys, json, hashlib, argparse
from pathlib import Path
from datetime import datetime

DID = "DID-BR-000002"
TRACE_MARK = "Ω₀⊂⊙∞⊂Ω"

def sha256_file(filepath, chunk_size=8192):
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk: break
            h.update(chunk)
    return h.hexdigest().upper()

def scan_directory(dir_path):
    assets = []
    total_size = 0
    for root, dirs, files in os.walk(dir_path):
        # 跳过隐藏目录和临时目录
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
        for fname in sorted(files):
            if fname.startswith('.') or fname.endswith('.pyc'):
                continue
            fpath = os.path.join(root, fname)
            rel_path = os.path.relpath(fpath, dir_path)
            size = os.path.getsize(fpath)
            total_size += size
            file_hash = sha256_file(fpath)
            ext = Path(fname).suffix.lower()
            # 推断资产类型
            asset_type = infer_type(ext)
            assets.append({
                "path": rel_path,
                "filename": fname,
                "extension": ext,
                "size_bytes": size,
                "size_human": human_size(size),
                "sha256": file_hash,
                "asset_type": asset_type,
                "tier": infer_tier(rel_path, asset_type)
            })
    return assets, total_size

def infer_type(ext):
    doc_types = {'.md', '.txt', '.pdf', '.docx', '.doc', '.rtf', '.html', '.htm'}
    sheet_types = {'.csv', '.xlsx', '.xls', '.tsv'}
    slide_types = {'.pptx', '.ppt'}
    image_types = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.bmp'}
    video_types = {'.mp4', '.mov', '.avi', '.mkv', '.webm'}
    audio_types = {'.mp3', '.wav', '.ogg', '.flac', '.m4a'}
    code_types = {'.py', '.js', '.ts', '.java', '.c', '.cpp', '.h', '.go', '.rs', '.sh', '.bash'}
    data_types = {'.json', '.xml', '.yaml', '.yml', '.sql', '.db', '.sqlite'}
    archive_types = {'.zip', '.tar', '.gz', '.7z', '.rar'}
    if ext in doc_types: return "document"
    if ext in sheet_types: return "spreadsheet"
    if ext in slide_types: return "presentation"
    if ext in image_types: return "image"
    if ext in video_types: return "video"
    if ext in audio_types: return "audio"
    if ext in code_types: return "code"
    if ext in data_types: return "data"
    if ext in archive_types: return "archive"
    return "other"

def infer_tier(rel_path, asset_type):
    p = rel_path.lower()
    # 钻石级：终稿、核心源码、锁档台账
    if any(k in p for k in ['final', '终稿', '定稿', 'locked', 'ledger', '台账', 'core', '核心']):
        return "diamond"
    if asset_type in ['code', 'document'] and 'draft' not in p and 'tmp' not in p:
        return "gold"
    if any(k in p for k in ['draft', '草稿', 'test', '测试', 'tmp', '临时']):
        return "bronze"
    return "silver"

def human_size(size):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} PB"

def calc_merkle_root(hashes):
    if not hashes: return None
    nodes = sorted(hashes)
    while len(nodes) > 1:
        new_nodes = []
        for i in range(0, len(nodes), 2):
            if i + 1 < len(nodes):
                combined = nodes[i] + nodes[i+1]
            else:
                combined = nodes[i] + nodes[i]
            new_nodes.append(hashlib.sha256(combined.encode()).hexdigest().upper())
        nodes = new_nodes
    return nodes[0]

def main():
    parser = argparse.ArgumentParser(description='资产清单导出工具')
    parser.add_argument('directory', help='待扫描的资产目录')
    parser.add_argument('--output', '-o', help='输出清单文件路径')
    parser.add_argument('--parent-hash', help='父卷宗哈希')
    args = parser.parse_args()

    dir_path = os.path.abspath(args.directory)
    if not os.path.isdir(dir_path):
        print(f"错误：目录不存在 {dir_path}")
        sys.exit(1)

    print(f"扫描目录: {dir_path}")
    assets, total_size = scan_directory(dir_path)

    # 计算Merkle根
    all_hashes = [a['sha256'] for a in assets]
    merkle_root = calc_merkle_root(all_hashes)

    # 分级统计
    tier_stats = {}
    type_stats = {}
    for a in assets:
        tier_stats[a['tier']] = tier_stats.get(a['tier'], 0) + 1
        type_stats[a['asset_type']] = type_stats.get(a['asset_type'], 0) + 1

    manifest = {
        "manifest_version": "1.0",
        "did": DID,
        "trace_mark": TRACE_MARK,
        "source_directory": dir_path,
        "export_time": datetime.now().isoformat(),
        "parent_hash": args.parent_hash or "",
        "summary": {
            "total_files": len(assets),
            "total_size_bytes": total_size,
            "total_size_human": human_size(total_size),
            "merkle_root": merkle_root,
            "tier_distribution": tier_stats,
            "type_distribution": type_stats
        },
        "assets": assets
    }

    # 输出
    output_path = args.output or os.path.join(dir_path, "_asset_manifest.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    # 同时输出人类可读的txt版本
    txt_path = output_path.replace('.json', '.txt')
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(f"资产清单台账\n")
        f.write(f"DID: {DID}\n")
        f.write(f"确权: {TRACE_MARK}\n")
        f.write(f"导出时间: {manifest['export_time']}\n")
        f.write(f"源目录: {dir_path}\n")
        f.write(f"文件总数: {len(assets)}\n")
        f.write(f"总大小: {human_size(total_size)}\n")
        f.write(f"Merkle根: {merkle_root}\n")
        f.write(f"\n分级统计:\n")
        for tier, count in sorted(tier_stats.items()):
            f.write(f"  {tier}: {count} 个文件\n")
        f.write(f"\n类型统计:\n")
        for atype, count in sorted(type_stats.items()):
            f.write(f"  {atype}: {count} 个文件\n")
        f.write(f"\n文件明细:\n")
        f.write(f"{'SHA256':<66} {'大小':>10} {'等级':<8} {'类型':<12} 路径\n")
        f.write("-" * 120 + "\n")
        for a in assets:
            f.write(f"{a['sha256']:<66} {a['size_human']:>10} {a['tier']:<8} {a['asset_type']:<12} {a['path']}\n")

    print(f"\n✅ 导出完成")
    print(f"  文件总数: {len(assets)}")
    print(f"  总大小: {human_size(total_size)}")
    print(f"  Merkle根: {merkle_root}")
    print(f"  分级: {tier_stats}")
    print(f"  JSON清单: {output_path}")
    print(f"  TXT清单:  {txt_path}")

if __name__ == "__main__":
    main()
