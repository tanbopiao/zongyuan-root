#!/usr/bin/env python3
"""
内置Action集合 - 手脚驱动层具体动作单元

每个Action封装一类外部操作，具备:
  前置校验 → 执行 → 后置校验 → 失败回滚 → 审计留痕
"""

import hashlib
import json
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))
from action_base import BaseAction, ActionResult, ActionStatus


# ============================================================
# Action 1: CAS写入动作
# ============================================================
class CasWriteAction(BaseAction):
    """将数据写入内容寻址存储"""
    name = "cas_write"
    description = "将数据写入CAS存储，返回内容ID"
    is_mutation = True
    max_retries = 2

    def execute(self) -> Any:
        from cas_store import CASStore
        store = CASStore(store_dir=self.params.get('store_dir'))
        data = self.params['data']
        if isinstance(data, str):
            data = data.encode()
        cid = store.put(data, self.params.get('metadata', {}))
        if self.params.get('ref_name'):
            store.set_ref(self.params['ref_name'], cid)
        return {'content_id': cid, 'size': len(data)}

    def pre_check(self) -> Optional[Tuple[bool, str]]:
        if 'data' not in self.params:
            return (False, "missing 'data' param")
        return (True, "")

    def post_check(self, result: ActionResult) -> Optional[Tuple[bool, str]]:
        from cas_store import CASStore
        store = CASStore(store_dir=self.params.get('store_dir'))
        cid = result.data['content_id']
        if not store.exists(cid):
            return (False, f"CAS object {cid} not found after write")
        return (True, "")

    def rollback(self) -> bool:
        # CAS不物理删除，只删除引用
        if self.params.get('ref_name'):
            from cas_store import CASStore
            store = CASStore(store_dir=self.params.get('store_dir'))
            ref_path = Path(store.refs_dir) / self.params['ref_name']
            if ref_path.exists():
                ref_path.unlink()
        return True


# ============================================================
# Action 2: API调用动作
# ============================================================
class ApiCallAction(BaseAction):
    """调用外部API（豆包Embedding/向量检索/重排等）"""
    name = "api_call"
    description = "调用外部HTTP API"
    is_mutation = False  # API调用默认非修改（除非写操作）
    max_retries = 3
    timeout = 30

    def execute(self) -> Any:
        import requests
        url = self.params['url']
        method = self.params.get('method', 'GET').upper()
        headers = self.params.get('headers', {})
        payload = self.params.get('payload')
        params = self.params.get('params')

        if method == 'GET':
            resp = requests.get(url, headers=headers, params=params, timeout=self.timeout)
        elif method == 'POST':
            resp = requests.post(url, headers=headers, json=payload, params=params, timeout=self.timeout)
        else:
            raise ValueError(f"unsupported method: {method}")

        resp.raise_for_status()
        try:
            return resp.json()
        except Exception:
            return {'text': resp.text, 'status_code': resp.status_code}

    def pre_check(self) -> Optional[Tuple[bool, str]]:
        if 'url' not in self.params:
            return (False, "missing 'url' param")
        return (True, "")

    def post_check(self, result: ActionResult) -> Optional[Tuple[bool, str]]:
        if result.data is None:
            return (False, "empty response")
        return (True, "")


# ============================================================
# Action 3: 向量同步动作
# ============================================================
class VectorSyncAction(BaseAction):
    """将资产增量同步到豆包向量库"""
    name = "vector_sync"
    description = "增量同步资产到向量库"
    is_mutation = True
    max_retries = 2
    timeout = 120

    def execute(self) -> Any:
        # 调用高阶向量适配器
        try:
            from vector_truth_adapter_v2 import VectorTruthAdapterV2
            adapter = VectorTruthAdapterV2()
            result = adapter.sync_incremental(
                assets=self.params.get('assets'),
                force=self.params.get('force', False)
            )
            return result
        except ImportError:
            # 降级到基础适配器
            from vector_truth_adapter import VectorTruthAdapter
            adapter = VectorTruthAdapter()
            return adapter.sync_incremental(assets=self.params.get('assets'))

    def pre_check(self) -> Optional[Tuple[bool, str]]:
        # 向量同步前必须确认本地真值基座有效
        if not self.params.get('skip_truth_check'):
            truth_ok = self._verify_truth_base()
            if not truth_ok:
                return (False, "truth base verification failed, blocking vector sync")
        return (True, "")

    def _verify_truth_base(self) -> bool:
        """验证本地真值基座状态"""
        try:
            from hash_chain import HashChain
            chain = HashChain()
            return chain.verify_chain()['valid']
        except Exception:
            return True  # 验证组件不可用时不阻断

    def post_check(self, result: ActionResult) -> Optional[Tuple[bool, str]]:
        data = result.data or {}
        failed = data.get('failed', 0)
        if failed > 0 and not self.params.get('allow_partial', False):
            return (False, f"{failed} assets failed to sync")
        return (True, "")


# ============================================================
# Action 4: 快照动作
# ============================================================
class SnapshotAction(BaseAction):
    """生成全局Merkle快照"""
    name = "snapshot"
    description = "扫描资产生成Merkle快照"
    is_mutation = True
    max_retries = 1

    def execute(self) -> Any:
        sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'scripts'))
        from merkle_tree import MerkleTree

        root_dir = self.params.get('root_dir', '.')
        assets = []
        for fp in Path(root_dir).rglob('*'):
            if fp.is_file() and 'cache' not in str(fp):
                h = hashlib.sha256()
                with open(fp, 'rb') as f:
                    for chunk in iter(lambda: f.read(8192), b''):
                        h.update(chunk)
                assets.append({'path': str(fp.relative_to(root_dir)), 'sha256': h.hexdigest()})

        tree = MerkleTree([a['sha256'] for a in assets])
        snapshot = {
            'snapshot_id': self.params.get('snapshot_id', f'SNAP-{int(time.time())}'),
            'total_assets': len(assets),
            'merkle_root': tree.root,
            'merkle_depth': len(tree.tree),
            'created_at': datetime.now(timezone.utc).isoformat(),
            'assets': assets,
        }

        # 保存快照
        save_dir = self.params.get('save_dir', 'lock_archive')
        Path(save_dir).mkdir(parents=True, exist_ok=True)
        save_path = Path(save_dir) / f"snapshot_{snapshot['snapshot_id']}.json"
        with open(save_path, 'w') as f:
            json.dump(snapshot, f, ensure_ascii=False, indent=2)

        return {'snapshot_id': snapshot['snapshot_id'], 'merkle_root': tree.root,
                'total_assets': len(assets), 'save_path': str(save_path)}

    def post_check(self, result: ActionResult) -> Optional[Tuple[bool, str]]:
        save_path = result.data.get('save_path')
        if not save_path or not Path(save_path).exists():
            return (False, "snapshot file not saved")
        return (True, "")

    def rollback(self) -> bool:
        if self._snapshot_before and 'save_path' in self._snapshot_before:
            p = Path(self._snapshot_before['save_path'])
            if p.exists():
                p.unlink()
        return True

    def _take_snapshot(self) -> Optional[dict]:
        return {'save_path': str(Path(self.params.get('save_dir', 'lock_archive')) /
                  f"snapshot_{self.params.get('snapshot_id', f'SNAP-{int(time.time())}')}.json")}


# ============================================================
# Action 5: 进化循环动作
# ============================================================
class EvolutionAction(BaseAction):
    """触发元极恒一进化循环"""
    name = "evolution_cycle"
    description = "执行元极恒一全域终极进化循环"
    is_mutation = True
    max_retries = 1
    timeout = 600

    def execute(self) -> Any:
        from evolution_loop import EvolutionLoop
        loop = EvolutionLoop()
        result = loop.run(stage=self.params.get('stage', 'all'))
        return result

    def pre_check(self) -> Optional[Tuple[bool, str]]:
        # 进化循环前必须确认系统未漂移
        try:
            from hash_chain import HashChain
            chain = HashChain()
            if not chain.verify_chain()['valid']:
                return (False, "hash chain broken, blocking evolution")
        except Exception:
            pass
        return (True, "")


# ============================================================
# Action 6: 文件备份动作
# ============================================================
class FileBackupAction(BaseAction):
    """备份文件/目录（用于回滚）"""
    name = "file_backup"
    description = "备份文件或目录到备份区"
    is_mutation = True
    max_retries = 1

    def execute(self) -> Any:
        src = Path(self.params['source'])
        backup_dir = Path(self.params.get('backup_dir', 'backups'))
        backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        dst = backup_dir / f"{src.name}_{timestamp}"

        if src.is_dir():
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)

        return {'source': str(src), 'backup_path': str(dst), 'timestamp': timestamp}

    def pre_check(self) -> Optional[Tuple[bool, str]]:
        if not Path(self.params['source']).exists():
            return (False, f"source not found: {self.params['source']}")
        return (True, "")

    def rollback(self) -> bool:
        # 回滚 = 删除刚创建的备份
        if self.result and self.result.data:
            bp = Path(self.result.data['backup_path'])
            if bp.exists():
                if bp.is_dir():
                    shutil.rmtree(bp)
                else:
                    bp.unlink()
                return True
        return False


# ============================================================
# Action 7: 审计写入动作
# ============================================================
class AuditWriteAction(BaseAction):
    """写入审计日志"""
    name = "audit_write"
    description = "写入append-only审计日志"
    is_mutation = True
    max_retries = 1

    def execute(self) -> Any:
        from audit_log import AuditLog
        audit = AuditLog(chain_id=self.params.get('chain_id', 'default'))
        entry = audit.append(
            op_type=self.params['op_type'],
            operator=self.params.get('operator', 'system'),
            data_hash=self.params.get('data_hash', hashlib.sha256(str(time.time()).encode()).hexdigest()),
            details=self.params.get('details', {})
        )
        return {'seq': entry['seq'], 'hash': entry['hash']}

    def pre_check(self) -> Optional[Tuple[bool, str]]:
        if 'op_type' not in self.params:
            return (False, "missing 'op_type'")
        return (True, "")


# ============================================================
# Action注册表
# ============================================================
ACTION_REGISTRY = {
    'cas_write': CasWriteAction,
    'api_call': ApiCallAction,
    'vector_sync': VectorSyncAction,
    'snapshot': SnapshotAction,
    'evolution_cycle': EvolutionAction,
    'file_backup': FileBackupAction,
    'audit_write': AuditWriteAction,
}


def create_action(action_name: str, params: dict = None, context: dict = None) -> BaseAction:
    """工厂方法：根据名称创建Action实例"""
    cls = ACTION_REGISTRY.get(action_name)
    if not cls:
        raise ValueError(f"unknown action: {action_name}. available: {list(ACTION_REGISTRY.keys())}")
    return cls(params=params, context=context)
