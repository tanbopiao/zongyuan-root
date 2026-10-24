#!/usr/bin/env python3
"""eFuse 熔断巡检 v1.0 —— 重算哈希比对账本，检测篡改/漂移（纯标准库）"""
import os, sys, csv, json, hashlib, argparse
from pathlib import Path

def main():
    ap = argparse.ArgumentParser(description='eFuse 熔断巡检')
    ap.add_argument('--dir', required=True, help='受检目录')
    ap.add_argument('--ledger', required=True, help='HASH-LEDGER.csv 账本')
    ap.add_argument('--threshold', type=int, default=0, help='失配容忍数（0=零容忍）')
    args = ap.parse_args()

    root = Path(args.dir).resolve()
    recorded = {}
    with open(args.ledger, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            recorded[row['file']] = row['sha256']

    mismatches = []
    total = 0
    for rp in sorted(root.rglob('*')):
        if not rp.is_file():
            continue
        rel = str(rp.relative_to(root))
        if rel.startswith('.git') or '__pycache__' in rel:
            continue
        total += 1
        cur = hashlib.sha256(rp.read_bytes()).hexdigest()
        if rel in recorded and recorded[rel] != cur:
            mismatches.append(rel)
        elif rel not in recorded:
            mismatches.append(f'{rel} (未入账)')

    status = 'OK' if len(mismatches) <= args.threshold else 'TRIPPED'
    drift = round(len(mismatches) / max(total, 1) * 100, 2)
    result = {'status': status, 'checked': total, 'mismatch_count': len(mismatches),
              'drift_ratio': drift, 'mismatch_list': mismatches[:50]}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if status == 'OK' else 2)

if __name__ == '__main__':
    main()
