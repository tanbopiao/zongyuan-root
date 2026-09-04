#!/usr/bin/env python3
"""
手脚驱动层加固2 - 两阶段提交Action (Two-Phase Commit Action)

用于关键修改类动作（CAS写入、快照生成、进化循环、向量同步），提供:
  prepare():  准备阶段 - 校验、预分配资源、生成预提交快照
  commit():   提交阶段 - 执行真实修改
  rollback(): 回滚阶段 - 从预提交快照恢复

与普通Action的区别:
  - 普通Action: execute() 一步完成，失败直接rollback
  - 两阶段Action: prepare()先做全部校验和预演，commit()才真正写入
    确保"要么全部成功，要么全部不做"，杜绝半完成状态

状态机: INIT → PREPARED → COMMITTED / ROLLED_BACK
"""

import hashlib
import json
import time
from abc import abstractmethod
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import sys
sys.path.insert(0, str(Path(__file__).parent))
from action_base import BaseAction, ActionResult, ActionStatus


class TPCState(Enum):
    INIT = "init"
    PREPARING = "preparing"
    PREPARED = "prepared"
    COMMITTING = "committing"
    COMMITTED = "committed"
    ROLLING_BACK = "rolling_back"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


class TwoPhaseAction(BaseAction):
    """
    两阶段提交Action基类

    子类必须实现:
      - name: 动作名称
      - _prepare(): 准备阶段逻辑
      - _commit(): 提交阶段逻辑（真实写入）
    可选重写:
      - _rollback(): 回滚逻辑
      - pre_check(), post_check()
    """

    # 两阶段动作默认都是修改类
    is_mutation = True
    # prepare超时
    prepare_timeout = 30
    # commit超时
    commit_timeout = 60
    # 最大重试（仅commit阶段重试，prepare失败直接回滚）
    max_retries = 2

    def __init__(self, params: dict = None, context: dict = None):
        super().__init__(params, context)
        self.tpc_state = TPCState.INIT
        self._prepare_snapshot: Optional[dict] = None
        self._prepare_result: Optional[Any] = None
        self._commit_result: Optional[Any] = None
        self._prepare_time: Optional[float] = None
        self._commit_time: Optional[float] = None

    # ===== 两阶段核心 =====

    def prepare(self) -> ActionResult:
        """
        准备阶段:
          1. 前置校验
          2. 执行_prepare()（校验、预分配、生成快照）
          3. 状态变为PREPARED

        注意: prepare阶段不做真实修改，只做校验和预演
        """
        self.tpc_state = TPCState.PREPARING
        self._prepare_time = time.time()

        # 前置校验
        try:
            check = self.pre_check()
            if check is not None and not check[0]:
                self.tpc_state = TPCState.FAILED
                return ActionResult(ActionStatus.BLOCKED, error=f"pre_check failed: {check[1]}")
        except Exception as e:
            self.tpc_state = TPCState.FAILED
            return ActionResult(ActionStatus.FAILED, error=f"pre_check exception: {e}")

        # 执行prepare
        try:
            self._prepare_snapshot = self._take_prepare_snapshot()
            self._prepare_result = self._prepare()
            self.tpc_state = TPCState.PREPARED
            return ActionResult(ActionStatus.SUCCESS, data={
                'prepared': True,
                'prepare_snapshot': self._prepare_snapshot,
                'prepare_duration_ms': round((time.time() - self._prepare_time) * 1000, 2),
            })
        except Exception as e:
            self.tpc_state = TPCState.FAILED
            return ActionResult(ActionStatus.FAILED, error=f"prepare failed: {e}")

    def commit(self) -> ActionResult:
        """
        提交阶段:
          1. 确认状态为PREPARED
          2. 执行_commit()（真实写入）
          3. 后置校验
          4. 状态变为COMMITTED
        """
        if self.tpc_state != TPCState.PREPARED:
            return ActionResult(ActionStatus.FAILED,
                                error=f"cannot commit in state {self.tpc_state.value}, must be PREPARED")

        self.tpc_state = TPCState.COMMITTING
        self._commit_time = time.time()

        last_error = None
        for attempt in range(self.max_retries):
            try:
                self._commit_result = self._commit()
                break
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    time.sleep(min(2 ** attempt, 5))
                    continue
                # 全部重试失败，回滚
                self._safe_rollback()
                return ActionResult(ActionStatus.FAILED, error=f"commit failed after {self.max_retries} attempts: {last_error}")

        # 后置校验
        try:
            result = ActionResult(ActionStatus.SUCCESS, data=self._commit_result)
            post = self.post_check(result)
            if post is not None and not post[0]:
                self._safe_rollback()
                return ActionResult(ActionStatus.FAILED, data=self._commit_result,
                                    error=f"post_check failed: {post[1]}")
        except Exception as e:
            self._safe_rollback()
            return ActionResult(ActionStatus.FAILED, error=f"post_check exception: {e}")

        self.tpc_state = TPCState.COMMITTED
        self.end_time = time.time()
        self.result = ActionResult(ActionStatus.SUCCESS, data={
            'committed': True,
            'result': self._commit_result,
            'prepare_duration_ms': round((self._commit_time - self._prepare_time) * 1000, 2) if self._prepare_time else 0,
            'commit_duration_ms': round((time.time() - self._commit_time) * 1000, 2),
        })
        self._audit()
        return self.result

    def rollback(self) -> ActionResult:
        """
        回滚阶段:
          从PREPARED或COMMITTED状态回滚到初始状态
        """
        if self.tpc_state not in (TPCState.PREPARED, TPCState.COMMITTED, TPCState.FAILED):
            return ActionResult(ActionStatus.SKIPPED, error=f"nothing to rollback in state {self.tpc_state.value}")

        self.tpc_state = TPCState.ROLLING_BACK
        success = self._safe_rollback()
        if success:
            self.tpc_state = TPCState.ROLLED_BACK
            return ActionResult(ActionStatus.SUCCESS, data={'rolled_back': True})
        else:
            self.tpc_state = TPCState.FAILED
            return ActionResult(ActionStatus.FAILED, error="rollback failed")

    def run(self) -> ActionResult:
        """
        一键执行: prepare → commit
        如果prepare失败，直接返回失败（不需要rollback，因为没做真实修改）
        如果commit失败，自动rollback
        """
        prep_result = self.prepare()
        if prep_result.status != ActionStatus.SUCCESS:
            self.result = prep_result
            self._audit()
            return prep_result

        return self.commit()

    def execute(self) -> Any:
        """
        实现BaseAction的抽象方法execute()
        两阶段Action的execute等价于run()，返回commit结果数据
        """
        result = self.run()
        if result.status != ActionStatus.SUCCESS:
            raise RuntimeError(f"two-phase execution failed: {result.error}")
        return result.data

    # ===== 子类实现接口 =====

    @abstractmethod
    def _prepare(self) -> Any:
        """
        准备阶段: 校验、预分配、生成预提交数据
        不做真实修改！
        """
        raise NotImplementedError

    @abstractmethod
    def _commit(self) -> Any:
        """
        提交阶段: 执行真实修改
        只能使用prepare阶段生成的预提交数据
        """
        raise NotImplementedError

    def _rollback(self) -> bool:
        """回滚逻辑（子类可重写）"""
        return True

    def _take_prepare_snapshot(self) -> Optional[dict]:
        """准备阶段快照（用于回滚，子类可重写）"""
        return None

    # ===== 内部方法 =====

    def _safe_rollback(self) -> bool:
        """安全回滚（捕获异常）"""
        try:
            return self._rollback()
        except Exception:
            return False

    def get_tpc_status(self) -> dict:
        return {
            'state': self.tpc_state.value,
            'name': self.name,
            'has_prepare_snapshot': self._prepare_snapshot is not None,
            'prepare_duration_ms': round((self._commit_time - self._prepare_time) * 1000, 2) if all([self._prepare_time, self._commit_time]) else None,
        }


# ============================================================
# 内置两阶段Action示例: TPCSnapshotAction（两阶段快照）
# ============================================================
class TPCSnapshotAction(TwoPhaseAction):
    """两阶段快照动作: prepare扫描资产，commit写入快照文件"""
    name = "tpc_snapshot"
    description = "两阶段快照生成（prepare扫描，commit写入）"

    def _prepare(self) -> Any:
        """准备阶段: 扫描所有资产，计算哈希（不写入文件）"""
        root_dir = self.params.get('root_dir', '.')
        assets = []
        for fp in Path(root_dir).rglob('*'):
            if fp.is_file() and 'cache' not in str(fp) and '__pycache__' not in str(fp):
                h = hashlib.sha256()
                with open(fp, 'rb') as f:
                    for chunk in iter(lambda: f.read(8192), b''):
                        h.update(chunk)
                assets.append({'path': str(fp), 'sha256': h.hexdigest()})

        # 生成Merkle根（内存中，不写入）
        def merkle_root(hashes):
            if not hashes: return hashlib.sha256(b'').hexdigest()
            level = hashes[:]
            while len(level) > 1:
                next_level = []
                for i in range(0, len(level), 2):
                    left = level[i]
                    right = level[i+1] if i+1 < len(level) else left
                    next_level.append(hashlib.sha256((left + right).encode()).hexdigest())
                level = next_level
            return level[0]

        self._prepare_result = {
            'assets': assets,
            'merkle_root': merkle_root([a['sha256'] for a in assets]),
            'total_assets': len(assets),
        }
        return self._prepare_result

    def _commit(self) -> Any:
        """提交阶段: 将prepare阶段的结果写入快照文件"""
        if not self._prepare_result:
            raise RuntimeError("prepare result not available")

        save_dir = self.params.get('save_dir', 'lock_archive')
        Path(save_dir).mkdir(parents=True, exist_ok=True)
        snapshot_id = self.params.get('snapshot_id', f'TPC-SNAP-{int(time.time())}')
        save_path = Path(save_dir) / f"{snapshot_id}.json"

        snapshot = {
            'snapshot_id': snapshot_id,
            'total_assets': self._prepare_result['total_assets'],
            'merkle_root': self._prepare_result['merkle_root'],
            'created_at': datetime.now(timezone.utc).isoformat(),
            'tpc': True,
            'assets': self._prepare_result['assets'],
        }
        with open(save_path, 'w') as f:
            json.dump(snapshot, f, ensure_ascii=False, indent=2)

        self._commit_result = {
            'snapshot_id': snapshot_id,
            'merkle_root': snapshot['merkle_root'],
            'save_path': str(save_path),
        }
        # 保存路径用于rollback
        self._prepare_snapshot = {'save_path': str(save_path)}
        return self._commit_result

    def _rollback(self) -> bool:
        """回滚: 删除刚写入的快照文件"""
        if self._prepare_snapshot and 'save_path' in self._prepare_snapshot:
            p = Path(self._prepare_snapshot['save_path'])
            if p.exists():
                p.unlink()
                return True
        return False

    def _take_prepare_snapshot(self) -> Optional[dict]:
        return None  # commit时才知道save_path


# ============================================================
# 内置两阶段Action: TPCCasWriteAction（两阶段CAS写入）
# ============================================================
class TPCCasWriteAction(TwoPhaseAction):
    """两阶段CAS写入: prepare校验数据，commit写入CAS"""
    name = "tpc_cas_write"
    description = "两阶段CAS写入"

    def _prepare(self) -> Any:
        """准备阶段: 校验数据，计算CID（不写入）"""
        data = self.params.get('data')
        if data is None:
            raise ValueError("missing 'data' param")
        if isinstance(data, str):
            data = data.encode()
        cid = hashlib.sha256(data).hexdigest()
        self._prepare_result = {'cid': cid, 'data': data, 'size': len(data)}
        return self._prepare_result

    def _commit(self) -> Any:
        """提交阶段: 写入CAS"""
        from cas_store import CASStore
        store = CASStore(store_dir=self.params.get('store_dir'))
        cid = store.put(self._prepare_result['data'], self.params.get('metadata', {}))
        if self.params.get('ref_name'):
            store.set_ref(self.params['ref_name'], cid)
        self._commit_result = {'content_id': cid, 'size': self._prepare_result['size']}
        return self._commit_result

    def _rollback(self) -> bool:
        """回滚: 删除引用（CAS对象不物理删除）"""
        if self.params.get('ref_name'):
            from cas_store import CASStore
            store = CASStore(store_dir=self.params.get('store_dir'))
            ref_path = Path(store.refs_dir) / self.params['ref_name']
            if ref_path.exists():
                ref_path.unlink()
        return True


# 注册表
TPC_ACTION_REGISTRY = {
    'tpc_snapshot': TPCSnapshotAction,
    'tpc_cas_write': TPCCasWriteAction,
}
