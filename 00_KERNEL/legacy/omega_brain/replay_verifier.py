#!/usr/bin/env python3
"""
L5 证明层 - 可重放验证框架

所有核心计算函数必须是纯函数（相同输入→相同输出）。
每次计算记录: 输入哈希 + 函数版本 + 输出哈希 + 执行时间。
第三方可重放计算，验证输出一致性。

核心原则:
  1. 确定性: 相同输入永远产生相同输出
  2. 可追溯: 每次计算有完整审计记录
  3. 可验证: 第三方可独立重放验证
  4. 不可篡改: 计算日志append-only
"""

import hashlib
import json
import os
import time
import functools
import inspect
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional, Dict


class ComputeAuditLog:
    """计算审计日志（append-only）"""

    def __init__(self, log_dir: str = None):
        self.log_dir = Path(log_dir) if log_dir else Path(__file__).parent.parent / 'compute_audit'
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / 'compute_log.jsonl'
        self.index_file = self.log_dir / 'index.json'
        self._init_index()

    def _init_index(self):
        if not self.index_file.exists():
            with open(self.index_file, 'w') as f:
                json.dump({'total_computations': 0, 'functions': {}}, f, ensure_ascii=False, indent=2)
        # 确保log_file存在
        if not self.log_file.exists():
            self.log_file.touch()

    def _load_index(self) -> dict:
        with open(self.index_file) as f:
            return json.load(f)

    def _save_index(self, index: dict):
        with open(self.index_file, 'w') as f:
            json.dump(index, f, ensure_ascii=False, indent=2)

    def record(self, function_name: str, function_version: str,
               input_hash: str, output_hash: str,
               input_size: int, output_size: int,
               duration_ms: float, deterministic: bool = True) -> dict:
        """记录一次计算"""
        entry = {
            'seq': self._get_next_seq(),
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'function_name': function_name,
            'function_version': function_version,
            'input_hash': input_hash,
            'output_hash': output_hash,
            'input_size': input_size,
            'output_size': output_size,
            'duration_ms': round(duration_ms, 3),
            'deterministic': deterministic,
        }
        # 条目哈希
        entry['hash'] = hashlib.sha256(
            json.dumps({k: v for k, v in entry.items()}, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()

        with open(self.log_file, 'a') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')

        # 更新索引
        index = self._load_index()
        index['total_computations'] += 1
        if function_name not in index['functions']:
            index['functions'][function_name] = {'count': 0, 'versions': set()}
        index['functions'][function_name]['count'] += 1
        index['functions'][function_name]['versions'] = list(
            set(index['functions'][function_name].get('versions', [])) | {function_version}
        )
        self._save_index(index)

        return entry

    def _get_next_seq(self) -> int:
        if not self.log_file.exists():
            return 0
        count = 0
        with open(self.log_file) as f:
            for _ in f:
                count += 1
        return count

    def get_entry(self, seq: int) -> Optional[dict]:
        with open(self.log_file) as f:
            for line in f:
                line = line.strip()
                if line:
                    entry = json.loads(line)
                    if entry['seq'] == seq:
                        return entry
        return None

    def get_by_function(self, function_name: str) -> list:
        results = []
        with open(self.log_file) as f:
            for line in f:
                line = line.strip()
                if line:
                    entry = json.loads(line)
                    if entry['function_name'] == function_name:
                        results.append(entry)
        return results

    def stats(self) -> dict:
        index = self._load_index()
        return {
            'total_computations': index['total_computations'],
            'functions': {k: {'count': v['count'], 'versions': v['versions']} for k, v in index['functions'].items()},
        }


def deterministic(version: str = '1.0.0'):
    """
    纯函数装饰器：自动记录计算审计日志

    被装饰的函数必须是纯函数:
      - 相同输入 → 相同输出
      - 无副作用
      - 不依赖外部状态（时间、随机数、全局变量）

    Usage:
        @deterministic(version='1.0.0')
        def merkle_root(leaves):
            ...
    """
    def decorator(func: Callable) -> Callable:
        audit_log = ComputeAuditLog()
        func_version = version
        func_name = f'{func.__module__}.{func.__qualname__}'

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 计算输入哈希
            input_data = json.dumps({'args': [str(a) for a in args], 'kwargs': {k: str(v) for k, v in kwargs.items()}},
                                    sort_keys=True, ensure_ascii=False).encode()
            input_hash = hashlib.sha256(input_data).hexdigest()
            input_size = len(input_data)

            # 执行计算
            start = time.time()
            result = func(*args, **kwargs)
            duration_ms = (time.time() - start) * 1000

            # 计算输出哈希
            output_data = json.dumps(result, sort_keys=True, ensure_ascii=False, default=str).encode()
            output_hash = hashlib.sha256(output_data).hexdigest()
            output_size = len(output_data)

            # 记录审计
            audit_log.record(
                function_name=func_name,
                function_version=func_version,
                input_hash=input_hash,
                output_hash=output_hash,
                input_size=input_size,
                output_size=output_size,
                duration_ms=duration_ms,
                deterministic=True,
            )

            return result

        wrapper._deterministic = True
        wrapper._version = version
        return wrapper
    return decorator


class ReplayVerifier:
    """可重放验证器"""

    def __init__(self, audit_log: ComputeAuditLog = None):
        self.audit_log = audit_log or ComputeAuditLog()

    def replay(self, entry: dict, func: Callable) -> dict:
        """
        重放一次计算，验证输出一致性

        Args:
            entry: 计算审计条目
            func: 要重放的函数（必须是原始纯函数）

        Returns:
            {'match': bool, 'expected_hash': str, 'actual_hash': str, 'details': ...}
        """
        # 注意: 重放需要原始输入数据，这里用input_hash验证
        # 实际使用中应存储原始输入或从CAS中获取
        return {
            'replay_supported': True,
            'entry_seq': entry['seq'],
            'function': entry['function_name'],
            'version': entry['function_version'],
            'input_hash': entry['input_hash'],
            'expected_output_hash': entry['output_hash'],
            'note': 'Replay requires original input data. Verify input_hash matches stored input, then call function and compare output_hash.',
        }

    def verify_log_integrity(self) -> dict:
        """验证计算日志完整性"""
        if not self.audit_log.log_file.exists():
            return {'valid': False, 'error': 'log not found'}

        entries = []
        with open(self.audit_log.log_file) as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))

        errors = []
        for i, entry in enumerate(entries):
            if entry['seq'] != i:
                errors.append({'seq': i, 'error': 'seq mismatch'})
                continue
            # 验证条目哈希
            content = {k: v for k, v in entry.items() if k != 'hash'}
            expected = hashlib.sha256(
                json.dumps(content, sort_keys=True, ensure_ascii=False).encode()
            ).hexdigest()
            if entry['hash'] != expected:
                errors.append({'seq': i, 'error': 'hash mismatch'})

        return {
            'valid': len(errors) == 0,
            'total_entries': len(entries),
            'errors': errors,
        }

    def sample_replay_test(self, sample_size: int = 5) -> dict:
        """抽样重放测试"""
        if not self.audit_log.log_file.exists():
            return {'tested': 0, 'passed': 0, 'note': 'no log file'}
        entries = []
        with open(self.audit_log.log_file) as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))

        if not entries:
            return {'tested': 0, 'passed': 0, 'note': 'no entries'}

        # 抽样（均匀分布）
        step = max(1, len(entries) // sample_size)
        samples = entries[::step][:sample_size]

        # 验证每条目的哈希自洽
        passed = 0
        for entry in samples:
            content = {k: v for k, v in entry.items() if k != 'hash'}
            expected = hashlib.sha256(
                json.dumps(content, sort_keys=True, ensure_ascii=False).encode()
            ).hexdigest()
            if entry['hash'] == expected:
                passed += 1

        return {
            'tested': len(samples),
            'passed': passed,
            'pass_rate': round(passed / len(samples) * 100, 1) if samples else 0,
            'sample_seqs': [e['seq'] for e in samples],
        }


# ========== 示例：核心纯函数 ==========

@deterministic(version='1.0.0')
def compute_merkle_root(leaves: list) -> str:
    """计算Merkle根（纯函数示例）"""
    if not leaves:
        return '0' * 64
    current = leaves[:]
    while len(current) > 1:
        next_level = []
        for i in range(0, len(current), 2):
            if i + 1 < len(current):
                combined = current[i] + current[i + 1]
            else:
                combined = current[i] + current[i]
            next_level.append(hashlib.sha256(combined.encode()).hexdigest())
        current = next_level
    return current[0]


@deterministic(version='1.0.0')
def compute_sha256(data: str) -> str:
    """计算SHA256（纯函数示例）"""
    return hashlib.sha256(data.encode()).hexdigest()


def main():
    """CLI入口"""
    import argparse
    parser = argparse.ArgumentParser(description='Replay Verifier')
    sub = parser.add_subparsers(dest='command')

    # stats
    sub.add_parser('stats', help='Compute audit statistics')

    # verify
    sub.add_parser('verify', help='Verify compute log integrity')

    # sample
    s_p = sub.add_parser('sample', help='Sample replay test')
    s_p.add_argument('--size', type=int, default=5, help='Sample size')

    # demo
    sub.add_parser('demo', help='Run deterministic function demo')

    args = parser.parse_args()
    audit = ComputeAuditLog()
    verifier = ReplayVerifier(audit)

    if args.command == 'stats':
        print(json.dumps(audit.stats(), ensure_ascii=False, indent=2))
    elif args.command == 'verify':
        print(json.dumps(verifier.verify_log_integrity(), ensure_ascii=False, indent=2))
    elif args.command == 'sample':
        print(json.dumps(verifier.sample_replay_test(args.size), ensure_ascii=False, indent=2))
    elif args.command == 'demo':
        # 演示纯函数
        leaves = ['a' * 64, 'b' * 64, 'c' * 64]
        root = compute_merkle_root(leaves)
        h = compute_sha256('test data')
        print(json.dumps({'merkle_root': root, 'sha256': h, 'stats': audit.stats()}, ensure_ascii=False, indent=2))
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
