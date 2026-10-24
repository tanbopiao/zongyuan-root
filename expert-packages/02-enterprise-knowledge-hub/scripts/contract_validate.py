#!/usr/bin/env python3
"""契约校验 v1.0 —— 账本 schema 校验 + 不可变重算 + 冲突消解报告（纯标准库）

用法:
  python3 contract_validate.py --ledger <账本.json> [--root <知识根目录>]
    [--policy newer_kept]

退出码: 0=校验通过(可含已标记冲突)；1=硬错误(schema/哈希失配)；2=DID 缺失。
"""
import sys, json, hashlib, argparse
from pathlib import Path

REQUIRED = ['entry_id', 'department', 'did', 'sha256', 'timestamp', 'tags', 'path', 'size']


def main():
    ap = argparse.ArgumentParser(description='企业知识中枢 · 契约校验/冲突消解')
    ap.add_argument('--ledger', required=True)
    ap.add_argument('--root', default='', help='可选：知识根目录，用于重算哈希校验不可变性')
    ap.add_argument('--policy', default='newer_kept', choices=['newer_kept'])
    args = ap.parse_args()

    lp = Path(args.ledger)
    ledger = json.loads(lp.read_text(encoding='utf-8'))
    entries = ledger.get('entries', [])
    errors, conflicts = [], []

    if not ledger.get('did'):
        print('ERR: 账本缺少 did 字段', file=sys.stderr)
        sys.exit(2)

    # 1) schema 校验
    for e in entries:
        miss = [k for k in REQUIRED if k not in e]
        if miss:
            errors.append(f"{e.get('entry_id','?')} 缺字段: {miss}")
        if len(e.get('sha256', '')) != 64:
            errors.append(f"{e.get('entry_id','?')} sha256 长度非法")

    # 2) 不可变性重算（可选）
    if args.root:
        root = Path(args.root).resolve()
        for e in entries:
            fp = root / e['path']
            if not fp.exists():
                errors.append(f"原文缺失: {e['path']}")
                continue
            real = hashlib.sha256(fp.read_bytes()).hexdigest()
            if real != e['sha256']:
                errors.append(f"哈希失配(可能被篡改): {e['path']}")

    # 3) 冲突消解：同路径不同 sha256
    by_path = {}
    for e in entries:
        by_path.setdefault(e['path'], []).append(e)
    for path, group in by_path.items():
        uniq_hash = {x['sha256'] for x in group}
        if len(uniq_hash) > 1:
            group_sorted = sorted(group, key=lambda x: x['timestamp'])
            kept = group_sorted[-1]
            for old in group_sorted[:-1]:
                old['conflict'] = True
                conflicts.append({
                    'path': path,
                    'kept_entry_id': kept['entry_id'],
                    'obsolete_entry_id': old['entry_id'],
                    'reason': '同路径不同哈希；时间戳较新者保留，旧者标记 conflict',
                })

    result = {
        'ledger_id': ledger.get('ledger_id'),
        'checked_entries': len(entries),
        'departments': sorted({e.get('department', '') for e in entries}),
        'updated': ledger.get('updated'),
        'conflict_count': len(conflicts),
        'conflicts': conflicts,
        'error_count': len(errors),
        'errors': errors[:20],
        'immutability_checked': bool(args.root),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))

    # 回写 conflict 标记（不覆盖原文条目，仅追加标记）
    if conflicts:
        lp.write_text(json.dumps(ledger, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f'[Contract] 已回写 {len(conflicts)} 条 conflict 标记（旧条目不删除）')

    sys.exit(1 if errors else 0)


if __name__ == '__main__':
    main()
