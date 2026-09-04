#!/usr/bin/env python3
"""
手脚驱动层加固1 - 执行哈希链 (Execution Hash Chain)

每个Action执行结果生成哈希，并与前一个执行结果哈希链接，形成不可篡改的执行链。
任何一条执行记录被篡改，后续哈希全部断裂，可被检测。

与ZONGYUAN-ROOT现有hash_chain.py的区别:
  - hash_chain.py: 全局资产/状态哈希链
  - execution_hash_chain.py: 专属于手脚驱动层的执行记录哈希链
"""

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


class ExecutionHashChain:
    """
    执行哈希链

    每条执行记录结构:
    {
        seq: 递增序号,
        task_id: 任务ID,
        action_name: 动作名称,
        status: 执行状态,
        result_hash: 执行结果的SHA256,
        prev_hash: 前一条记录的哈希,
        hash: 本条记录哈希 = SHA256(seq + task_id + action_name + status + result_hash + prev_hash + timestamp),
        timestamp: 执行时间,
        operator: 操作者,
        metadata: 附加元数据
    }
    """

    def __init__(self, chain_file: str = None):
        self.chain_file = Path(chain_file) if chain_file else Path(__file__).parent.parent / 'executor' / 'execution_hash_chain.json'
        self.chain_file.parent.mkdir(parents=True, exist_ok=True)
        self._chain: List[dict] = []
        self._load()

    def _load(self):
        if self.chain_file.exists():
            try:
                with open(self.chain_file) as f:
                    self._chain = json.load(f)
            except Exception:
                self._chain = []

    def _save(self):
        with open(self.chain_file, 'w') as f:
            json.dump(self._chain, f, indent=2, ensure_ascii=False)

    def _compute_hash(self, entry: dict) -> str:
        """计算执行记录哈希"""
        content = json.dumps({
            'seq': entry['seq'],
            'task_id': entry['task_id'],
            'action_name': entry['action_name'],
            'status': entry['status'],
            'result_hash': entry['result_hash'],
            'prev_hash': entry['prev_hash'],
            'timestamp': entry['timestamp'],
            'operator': entry.get('operator', ''),
        }, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(content.encode()).hexdigest()

    @staticmethod
    def _hash_result(result: Any) -> str:
        """对执行结果做哈希"""
        if result is None:
            return hashlib.sha256(b'null').hexdigest()
        if isinstance(result, (str, int, float, bool)):
            return hashlib.sha256(str(result).encode()).hexdigest()
        try:
            return hashlib.sha256(json.dumps(result, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        except Exception:
            return hashlib.sha256(str(result).encode()).hexdigest()

    def append(self, task_id: str, action_name: str, status: str,
               result: Any = None, operator: str = "system",
               metadata: dict = None, error: str = None) -> dict:
        """
        追加一条执行记录

        Returns:
            完整的执行记录（含哈希）
        """
        prev_hash = self._chain[-1]['hash'] if self._chain else hashlib.sha256(b'GENESIS').hexdigest()
        seq = len(self._chain)

        entry = {
            'seq': seq,
            'task_id': task_id,
            'action_name': action_name,
            'status': status,
            'result_hash': self._hash_result(result),
            'prev_hash': prev_hash,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'operator': operator,
            'error': error,
            'metadata': metadata or {},
        }
        entry['hash'] = self._compute_hash(entry)
        self._chain.append(entry)
        self._save()
        return entry

    def verify_chain(self) -> dict:
        """
        验证整条执行哈希链的完整性

        Returns:
            {'valid': bool, 'broken_at': int or None, 'total': int}
        """
        for i, entry in enumerate(self._chain):
            # 验证prev_hash
            if i == 0:
                expected_prev = hashlib.sha256(b'GENESIS').hexdigest()
            else:
                expected_prev = self._chain[i - 1]['hash']
            if entry['prev_hash'] != expected_prev:
                return {'valid': False, 'broken_at': i, 'reason': f'prev_hash mismatch at seq {i}', 'total': len(self._chain)}

            # 验证hash
            expected_hash = self._compute_hash(entry)
            if entry['hash'] != expected_hash:
                return {'valid': False, 'broken_at': i, 'reason': f'hash mismatch at seq {i}', 'total': len(self._chain)}

        return {'valid': True, 'broken_at': None, 'total': len(self._chain)}

    def get_latest(self) -> Optional[dict]:
        return self._chain[-1] if self._chain else None

    def get_by_task_id(self, task_id: str) -> List[dict]:
        return [e for e in self._chain if e['task_id'] == task_id]

    def get_by_action(self, action_name: str) -> List[dict]:
        return [e for e in self._chain if e['action_name'] == action_name]

    def stats(self) -> dict:
        status_counts = {}
        for e in self._chain:
            status_counts[e['status']] = status_counts.get(e['status'], 0) + 1
        return {
            'total_records': len(self._chain),
            'status_distribution': status_counts,
            'latest_seq': self._chain[-1]['seq'] if self._chain else -1,
            'latest_hash': self._chain[-1]['hash'] if self._chain else None,
        }

    def export_chain(self, output_file: str = None) -> str:
        """导出执行链为JSON文件"""
        output = Path(output_file) if output_file else self.chain_file
        with open(output, 'w') as f:
            json.dump(self._chain, f, indent=2, ensure_ascii=False)
        return str(output)

    def truncate(self, keep_last_n: int = 1000):
        """截断链，保留最近N条（用于存储优化，截断前需导出归档）"""
        if len(self._chain) > keep_last_n:
            # 保留被截断部分的最后一条哈希作为新的genesis
            cutoff = len(self._chain) - keep_last_n
            new_genesis_hash = self._chain[cutoff - 1]['hash'] if cutoff > 0 else hashlib.sha256(b'GENESIS').hexdigest()
            self._chain = self._chain[cutoff:]
            # 重新编号
            for i, entry in enumerate(self._chain):
                entry['seq'] = i
                if i == 0:
                    entry['prev_hash'] = new_genesis_hash
                else:
                    entry['prev_hash'] = self._chain[i - 1]['hash']
                entry['hash'] = self._compute_hash(entry)
            self._save()


# 全局单例
_global_exec_chain: Optional[ExecutionHashChain] = None

def get_global_exec_chain() -> ExecutionHashChain:
    global _global_exec_chain
    if _global_exec_chain is None:
        _global_exec_chain = ExecutionHashChain()
    return _global_exec_chain
