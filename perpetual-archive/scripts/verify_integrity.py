#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
资产完整性校验工具（防Bit Rot）
校验指定目录中所有文件的SHA256哈希与台账是否一致
用法：python3 verify_integrity.py <资产目录> [--manifest <清单文件>]
"""
import os, sys, json, hashlib, argparse
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

def verify_directory(dir_path, manifest_path):
    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)

    expected_assets = {a['path']: a for a in manifest['assets']}
    results = []
    passed = 0
    failed = 0
    missing = 0
    extra = 0

    # 检查台账中的文件
    for rel_path, expected in expected_assets.items():
        fpath = os.path.join(dir_path, rel_path)
        if not os.path.exists(fpath):
            results.append({"path": rel_path, "status": "MISSING", "expected": expected['sha256'], "actual": None})
            missing += 1
            continue
        actual_hash = sha256_file(fpath)
        if actual_hash == expected['sha256']:
            results.append({"path": rel_path, "status": "OK", "expected": expected['sha256'], "actual": actual_hash})
            passed += 1
        else:
            results.append({"path": rel_path, "status": "CORRUPTED", "expected": expected['sha256'], "actual": actual_hash})
            failed += 1

    # 检查目录中是否有台账外的文件
    for root, dirs, files in os.walk(dir_path):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for fname in files:
            if fname.startswith('.') or fname.startswith('_asset_manifest'):
                continue
            fpath = os.path.join(root, fname)
            rel_path = os.path.relpath(fpath, dir_path)
            if rel_path not in expected_assets:
                results.append({"path": rel_path, "status": "EXTRA", "expected": None, "actual": sha256_file(fpath)})
                extra += 1

    return results, passed, failed, missing, extra

def main():
    parser = argparse.ArgumentParser(description='资产完整性校验工具')
    parser.add_argument('directory', help='待校验的资产目录')
    parser.add_argument('--manifest', help='资产清单文件（默认目录下_asset_manifest.json）')
    parser.add_argument('--fix', action='store_true', help='尝试从备份修复损坏文件（需配置备份路径）')
    parser.add_argument('--backup-dir', help='备份目录路径（用于修复）')
    args = parser.parse_args()

    dir_path = os.path.abspath(args.directory)
    manifest_path = args.manifest or os.path.join(dir_path, "_asset_manifest.json")

    if not os.path.exists(manifest_path):
        print(f"错误：清单文件不存在 {manifest_path}")
        print("请先运行 export_asset_manifest.py 生成清单")
        sys.exit(1)

    print(f"校验目录: {dir_path}")
    print(f"清单文件: {manifest_path}")
    print(f"校验时间: {datetime.now().isoformat()}")
    print("-" * 80)

    results, passed, failed, missing, extra = verify_directory(dir_path, manifest_path)

    # 输出结果
    if failed > 0:
        print("\n❌ 损坏文件:")
        for r in results:
            if r['status'] == 'CORRUPTED':
                print(f"  {r['path']}")
                print(f"    期望: {r['expected']}")
                print(f"    实际: {r['actual']}")

    if missing > 0:
        print("\n⚠️  缺失文件:")
        for r in results:
            if r['status'] == 'MISSING':
                print(f"  {r['path']}")

    if extra > 0:
        print("\nℹ️  台账外文件:")
        for r in results:
            if r['status'] == 'EXTRA':
                print(f"  {r['path']}")

    # 尝试修复
    if args.fix and args.backup_dir and (failed > 0 or missing > 0):
        print("\n🔧 尝试从备份修复...")
        backup_dir = os.path.abspath(args.backup_dir)
        fixed = 0
        for r in results:
            if r['status'] in ['CORRUPTED', 'MISSING']:
                backup_path = os.path.join(backup_dir, r['path'])
                if os.path.exists(backup_path):
                    target_path = os.path.join(dir_path, r['path'])
                    os.makedirs(os.path.dirname(target_path), exist_ok=True)
                    import shutil
                    shutil.copy2(backup_path, target_path)
                    fixed += 1
                    print(f"  ✅ 已修复: {r['path']}")
                else:
                    print(f"  ❌ 备份中未找到: {r['path']}")
        print(f"修复完成: {fixed} 个文件")

    # 汇总
    total = passed + failed + missing
    print("\n" + "=" * 80)
    print(f"校验汇总:")
    print(f"  ✅ 通过: {passed}")
    print(f"  ❌ 损坏: {failed}")
    print(f"  ⚠️  缺失: {missing}")
    print(f"  ℹ️  台账外: {extra}")
    print(f"  总计: {total}")
    if failed == 0 and missing == 0:
        print(f"\n✅ 全部文件完整性校验通过，无Bit Rot")
    else:
        print(f"\n⚠️  发现问题，请及时处理")
        sys.exit(1)

if __name__ == "__main__":
    main()
