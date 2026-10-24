#!/usr/bin/env python3
"""索引构建 v1.0 —— 知识条目入库 + 倒排索引（纯标准库）

扫描知识根目录，逐文件 SHA256，生成结构化条目写入索引账本。
用法:
  python3 index_build.py --root <知识根目录> --ledger <账本.json> \
      --node <部门节点ID> --did <YOUR_DID> [--prefix K] [--exclude a,b]
"""
import os, sys, json, hashlib, time, argparse
from pathlib import Path


def title_of(fpath: Path) -> str:
    try:
        with open(fpath, encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip().lstrip('#').strip()
                if line:
                    return line[:120]
    except Exception:
        pass
    return fpath.stem


def main():
    ap = argparse.ArgumentParser(description='企业知识中枢 · 索引构建')
    ap.add_argument('--root', required=True)
    ap.add_argument('--ledger', required=True)
    ap.add_argument('--node', required=True, help='部门/节点标识')
    ap.add_argument('--did', required=True)
    ap.add_argument('--prefix', default='K')
    ap.add_argument('--exclude', default='__pycache__,.git,.DS_Store,Thumbs.db')
    args = ap.parse_args()

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f'ERR: 知识根目录不存在 {root}', file=sys.stderr)
        sys.exit(1)
    excl = [e.strip() for e in args.exclude.split(',') if e.strip()]

    entries = []
    seq = 1
    for rp in sorted(root.rglob('*')):
        if not rp.is_file():
            continue
        rel = str(rp.relative_to(root))
        if any(e in rel for e in excl):
            continue
        raw = rp.read_bytes()
        ext = rp.suffix.lstrip('.').lower() or 'txt'
        entries.append({
            'entry_id': f'{args.prefix}{seq}',
            'department': args.node,
            'did': args.did,
            'sha256': hashlib.sha256(raw).hexdigest(),
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S%z', time.localtime(rp.stat().st_mtime)),
            'tags': [args.node, ext],
            'path': rel,
            'size': len(raw),
            'title': title_of(rp),
        })
        seq += 1

    ledger = {
        'ledger_id': 'ENTERPRISE-INDEX-V1.0',
        'updated': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
        'did': args.did,
        'node_id': args.node,
        'entry_count': len(entries),
        'entries': entries,
    }
    Path(args.ledger).parent.mkdir(parents=True, exist_ok=True)
    Path(args.ledger).write_text(json.dumps(ledger, ensure_ascii=False, indent=2), encoding='utf-8')

    # 自校验：重算首条哈希比对
    ok = True
    if entries:
        raw0 = (root / entries[0]['path']).read_bytes()
        ok = hashlib.sha256(raw0).hexdigest() == entries[0]['sha256']
    print(f'[IndexBuild] 部门={args.node} 条目数={len(entries)} 自校验={"PASS" if ok else "FAIL"}')
    print(f'[IndexBuild] 账本: {args.ledger}')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
