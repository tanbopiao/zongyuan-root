#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
多副本备份工具（3-2-1原则）
将资产目录备份到多个目标位置，支持本地/NAS/云盘
用法：python3 multi_backup.py <源目录> --targets <目标1> <目标2> ...
"""
import os, sys, json, shutil, argparse, hashlib
from pathlib import Path
from datetime import datetime

def sha256_file(filepath, chunk_size=8192):
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk: break
            h.update(chunk)
    return h.hexdigest().upper()

def copy_directory(src, dst, verify=True):
    """复制目录，可选校验"""
    src = os.path.abspath(src)
    dst = os.path.abspath(dst)
    copied = 0
    skipped = 0
    failed = 0
    total_size = 0

    if not os.path.exists(dst):
        os.makedirs(dst, exist_ok=True)

    for root, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        rel_root = os.path.relpath(root, src)
        dst_root = os.path.join(dst, rel_root) if rel_root != '.' else dst
        os.makedirs(dst_root, exist_ok=True)

        for fname in files:
            if fname.startswith('.') or fname.endswith('.pyc'):
                continue
            src_file = os.path.join(root, fname)
            dst_file = os.path.join(dst_root, fname)

            # 如果目标已存在且哈希一致，跳过
            if os.path.exists(dst_file) and verify:
                if sha256_file(src_file) == sha256_file(dst_file):
                    skipped += 1
                    continue

            try:
                shutil.copy2(src_file, dst_file)
                total_size += os.path.getsize(src_file)
                copied += 1
            except Exception as e:
                print(f"  ❌ 复制失败: {src_file} -> {e}")
                failed += 1

    return copied, skipped, failed, total_size

def human_size(size):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} PB"

def main():
    parser = argparse.ArgumentParser(description='多副本备份工具（3-2-1原则）')
    parser.add_argument('source', help='源资产目录')
    parser.add_argument('--targets', nargs='+', required=True, help='备份目标目录（多个）')
    parser.add_argument('--no-verify', action='store_true', help='跳过哈希校验（更快）')
    parser.add_argument('--label', help='本次备份标签')
    args = parser.parse_args()

    src = os.path.abspath(args.source)
    if not os.path.isdir(src):
        print(f"错误：源目录不存在 {src}")
        sys.exit(1)

    verify = not args.no_verify
    label = args.label or f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    print(f"{'='*70}")
    print(f"  多副本备份")
    print(f"  DID: DID-BR-000002 | 确权: Ω₀⊂⊙∞⊂Ω")
    print(f"{'='*70}")
    print(f"源目录: {src}")
    print(f"备份标签: {label}")
    print(f"目标数: {len(args.targets)}")
    print(f"哈希校验: {'开启' if verify else '关闭'}")
    print()

    all_results = []
    for i, target in enumerate(args.targets, 1):
        target_path = os.path.abspath(os.path.join(target, label))
        print(f"[{i}/{len(args.targets)}] 备份到: {target_path}")
        copied, skipped, failed, total_size = copy_directory(src, target_path, verify)
        print(f"  复制: {copied} | 跳过(已存在): {skipped} | 失败: {failed} | 大小: {human_size(total_size)}")
        all_results.append({
            "target": target_path,
            "copied": copied,
            "skipped": skipped,
            "failed": failed,
            "size_bytes": total_size
        })
        print()

    # 生成备份记录
    record = {
        "did": "DID-BR-000002",
        "trace_mark": "Ω₀⊂⊙∞⊂Ω",
        "backup_label": label,
        "backup_time": datetime.now().isoformat(),
        "source": src,
        "targets": all_results,
        "total_copied": sum(r['copied'] for r in all_results),
        "total_failed": sum(r['failed'] for r in all_results)
    }

    record_path = os.path.join(src, f"_backup_record_{label}.json")
    with open(record_path, 'w', encoding='utf-8') as f:
        json.dump(record, f, indent=2, ensure_ascii=False)

    print(f"{'='*70}")
    print(f"✅ 备份完成")
    print(f"  总复制: {record['total_copied']} 个文件")
    print(f"  总失败: {record['total_failed']} 个文件")
    print(f"  备份记录: {record_path}")
    print(f"{'='*70}")

    if record['total_failed'] > 0:
        sys.exit(1)

if __name__ == "__main__":
    main()
