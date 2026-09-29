#!/usr/bin/env python3
"""
L6 审计层 - append-only不可变审计日志

所有写入操作生成审计条目，形成哈希链。
审计日志只追加，不修改不删除。
每个条目包含: 操作类型、操作者、数据哈希、时间戳、前一条目哈希。

篡改任何条目 = 后续所有条目哈希失效。
"""

import hashlib
import json
import os
import sys
import fcntl
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


class AuditLog:
    """append-only审计日志（哈希链结构）"""

    def __init__(self, log_dir: str = None, chain_id: str = 'default'):
        self.log_dir = Path(log_dir) if log_dir else Path(__file__).parent.parent / 'audit_logs'
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.chain_id = chain_id
        self.log_file = self.log_dir / f'audit_{chain_id}.jsonl'
        self.index_file = self.log_dir / f'index_{chain_id}.json'
        self._lock_file = self.log_dir / f'{chain_id}.lock'
        self._init_chain()

    def _init_chain(self):
        """初始化创世块"""
        if not self.log_file.exists():
            genesis = self._make_entry(
                op_type='GENESIS',
                operator='system',
                data_hash='0' * 64,
                details={'chain_id': self.chain_id, 'created_at': datetime.now(timezone.utc).isoformat()},
                prev_hash='0' * 64,
                seq=0,
            )
            with open(self.log_file, 'w') as f:
                f.write(json.dumps(genesis, ensure_ascii=False) + '\n')
            self._update_index(genesis)

    def _make_entry(self, op_type: str, operator: str, data_hash: str,
                    details: dict, prev_hash: str, seq: int) -> dict:
        """构造审计条目"""
        timestamp = datetime.now(timezone.utc).isoformat()
        entry = {
            'seq': seq,
            'timestamp': timestamp,
            'op_type': op_type,
            'operator': operator,
            'data_hash': data_hash,
            'prev_hash': prev_hash,
            'details': details or {},
        }
        # 条目哈希 = SHA256(除hash字段外的所有内容)
        entry_content = {k: v for k, v in entry.items()}
        entry['hash'] = hashlib.sha256(
            json.dumps(entry_content, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()
        return entry

    def _get_last_entry(self) -> dict:
        """获取最后一条目"""
        if not self.log_file.exists():
            return None
        last = None
        with open(self.log_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    last = json.loads(line)
        return last

    def _update_index(self, entry: dict):
        """更新索引"""
        index = {
            'chain_id': self.chain_id,
            'last_seq': entry['seq'],
            'last_hash': entry['hash'],
            'last_timestamp': entry['timestamp'],
            'total_entries': entry['seq'] + 1,
            'updated_at': datetime.now(timezone.utc).isoformat(),
        }
        with open(self.index_file, 'w') as f:
            json.dump(index, f, ensure_ascii=False, indent=2)

    def append(self, op_type: str, operator: str, data_hash: str,
               details: dict = None) -> dict:
        """
        追加审计条目（线程安全，文件锁）

        Args:
            op_type: 操作类型 (WRITE/UPDATE/DELETE/LOCK/EVOLVE/SYNC/etc)
            operator: 操作者 (system/user/scheduled/api/daemon)
            data_hash: 被操作数据的SHA256
            details: 附加信息

        Returns:
            审计条目
        """
        with open(self._lock_file, 'w') as lockf:
            fcntl.flock(lockf, fcntl.LOCK_EX)
            try:
                last = self._get_last_entry()
                prev_hash = last['hash'] if last else '0' * 64
                seq = (last['seq'] + 1) if last else 0

                entry = self._make_entry(
                    op_type=op_type,
                    operator=operator,
                    data_hash=data_hash,
                    details=details,
                    prev_hash=prev_hash,
                    seq=seq,
                )

                with open(self.log_file, 'a') as f:
                    f.write(json.dumps(entry, ensure_ascii=False) + '\n')

                self._update_index(entry)
                return entry
            finally:
                fcntl.flock(lockf, fcntl.LOCK_UN)

    def verify_chain(self) -> dict:
        """
        验证审计链完整性

        Returns:
            {'valid': bool, 'total': int, 'broken_at': int or None, 'details': [...]}
        """
        if not self.log_file.exists():
            return {'valid': False, 'error': 'log file not found'}

        entries = []
        with open(self.log_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))

        if not entries:
            return {'valid': False, 'error': 'empty log'}

        broken = []
        prev_hash = '0' * 64
        for i, entry in enumerate(entries):
            # 验证seq连续
            if entry['seq'] != i:
                broken.append({'seq': i, 'reason': f'seq mismatch: expected {i}, got {entry["seq"]}'})
                continue
            # 验证prev_hash
            if entry['prev_hash'] != prev_hash:
                broken.append({'seq': i, 'reason': f'prev_hash mismatch'})
                continue
            # 验证hash
            entry_content = {k: v for k, v in entry.items() if k != 'hash'}
            expected_hash = hashlib.sha256(
                json.dumps(entry_content, sort_keys=True, ensure_ascii=False).encode()
            ).hexdigest()
            if entry['hash'] != expected_hash:
                broken.append({'seq': i, 'reason': f'hash mismatch'})
                continue
            prev_hash = entry['hash']

        return {
            'valid': len(broken) == 0,
            'total': len(entries),
            'broken_count': len(broken),
            'broken_at': broken[0]['seq'] if broken else None,
            'broken_details': broken[:5],
            'genesis_hash': entries[0]['hash'],
            'latest_hash': entries[-1]['hash'],
        }

    def get_entry(self, seq: int) -> Optional[dict]:
        """按序号获取条目"""
        with open(self.log_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    entry = json.loads(line)
                    if entry['seq'] == seq:
                        return entry
        return None

    def get_by_data_hash(self, data_hash: str) -> list:
        """按数据哈希查找所有相关条目"""
        results = []
        with open(self.log_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    entry = json.loads(line)
                    if entry.get('data_hash') == data_hash:
                        results.append(entry)
        return results

    def get_by_op_type(self, op_type: str) -> list:
        """按操作类型查找"""
        results = []
        with open(self.log_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    entry = json.loads(line)
                    if entry.get('op_type') == op_type:
                        results.append(entry)
        return results

    def stats(self) -> dict:
        """统计信息"""
        if not self.log_file.exists():
            return {'total': 0}
        op_counts = {}
        operator_counts = {}
        total = 0
        with open(self.log_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    entry = json.loads(line)
                    total += 1
                    op = entry.get('op_type', 'UNKNOWN')
                    operator = entry.get('operator', 'unknown')
                    op_counts[op] = op_counts.get(op, 0) + 1
                    operator_counts[operator] = operator_counts.get(operator, 0) + 1
        return {
            'chain_id': self.chain_id,
            'total': total,
            'by_op_type': dict(sorted(op_counts.items(), key=lambda x: -x[1])),
            'by_operator': dict(sorted(operator_counts.items(), key=lambda x: -x[1])),
        }

    def export_chain_hash(self) -> str:
        """导出链根哈希（用于外部锚定）"""
        last = self._get_last_entry()
        return last['hash'] if last else '0' * 64


# 便捷函数：全局审计实例
_default_audit = None

def get_audit(chain_id: str = 'zongyuan_root') -> AuditLog:
    """获取全局审计实例"""
    global _default_audit
    if _default_audit is None or _default_audit.chain_id != chain_id:
        _default_audit = AuditLog(chain_id=chain_id)
    return _default_audit

def audit(op_type: str, operator: str, data_hash: str, details: dict = None) -> dict:
    """便捷审计记录"""
    return get_audit().append(op_type, operator, data_hash, details)


def main():
    """CLI入口"""
    import argparse
    parser = argparse.ArgumentParser(description='Append-only Audit Log')
    sub = parser.add_subparsers(dest='command')

    # append
    a_p = sub.add_parser('append', help='Append audit entry')
    a_p.add_argument('--op', required=True, help='Operation type')
    a_p.add_argument('--operator', default='system', help='Operator')
    a_p.add_argument('--hash', required=True, help='Data hash (SHA256)')
    a_p.add_argument('--details', default='{}', help='Details JSON')

    # verify
    sub.add_parser('verify', help='Verify audit chain integrity')

    # stats
    sub.add_parser('stats', help='Audit log statistics')

    # get
    g_p = sub.add_parser('get', help='Get entry by seq')
    g_p.add_argument('--seq', type=int, required=True)

    # export
    sub.add_parser('export', help='Export chain root hash')

    args = parser.parse_args()
    log = AuditLog()

    if args.command == 'append':
        details = json.loads(args.details) if args.details else {}
        entry = log.append(args.op, args.operator, args.hash, details)
        print(json.dumps(entry, ensure_ascii=False, indent=2))
    elif args.command == 'verify':
        result = log.verify_chain()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == 'stats':
        print(json.dumps(log.stats(), ensure_ascii=False, indent=2))
    elif args.command == 'get':
        entry = log.get_entry(args.seq)
        print(json.dumps(entry, ensure_ascii=False, indent=2) if entry else 'Not found')
    elif args.command == 'export':
        print(log.export_chain_hash())
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
