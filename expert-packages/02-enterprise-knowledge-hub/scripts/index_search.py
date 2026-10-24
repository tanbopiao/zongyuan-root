#!/usr/bin/env python3
"""跨节点检索 v1.0 —— DID 同源校验 + 全域索引池检索（纯标准库）

用法:
  python3 index_search.py --ledger <账本.json> --did <YOUR_DID> --keyword <词> \
      [--fields tags,path,title]
退出码: 0=命中或未命中(均正常)；2=DID 同源校验失败。
"""
import sys, json, argparse
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(description='企业知识中枢 · 跨节点检索')
    ap.add_argument('--ledger', required=True)
    ap.add_argument('--did', required=True, help='调用方 DID，须与账本归属 DID 一致')
    ap.add_argument('--keyword', required=True)
    ap.add_argument('--fields', default='tags,path,title')
    args = ap.parse_args()

    lp = Path(args.ledger)
    if not lp.exists():
        print(f'ERR: 索引账本缺失 {lp}', file=sys.stderr)
        sys.exit(1)
    ledger = json.loads(lp.read_text(encoding='utf-8'))

    # OP-04 同源身份校验
    if args.did != ledger.get('did'):
        print(f'拒绝访问: 调用方 DID={args.did} 与账本归属 DID={ledger.get("did")} 不一致')
        sys.exit(2)
    print(f'同源校验通过: {args.did}')

    fields = [f.strip() for f in args.fields.split(',') if f.strip()]
    kw = args.keyword.lower()
    hits = []
    for e in ledger.get('entries', []):
        blob = ''
        for f in fields:
            v = e.get(f, '')
            if isinstance(v, list):
                blob += ' '.join(str(x) for x in v) + ' '
            else:
                blob += str(v) + ' '
        if kw in blob.lower():
            hits.append(e)

    print(f'检索词="{args.keyword}" 命中型={len(hits)}')
    for e in hits:
        tags = ','.join(e.get('tags', []))
        print(f"{e['entry_id']} | {e.get('department','')} | {e['path']} | "
              f"{e['sha256'][:16]} | {e['timestamp']} | [{tags}]")
    if not hits:
        print('（无命中；仅返回元信息，原文需按需受控拉取）')


if __name__ == '__main__':
    main()
