#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
火斗云智 AIOS — 本地持久层管理器（最小实现）
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω

为 truth_evolution_engine 归档链路补齐缺失依赖（原设计落点即 /workspace/scripts/services）。
接口契约完全来自内核调用方实测：
    pm = PersistenceManager()
    pm.is_locked() / pm.unlock() / pm.write_truth(truth_id, category, content, metadata) / pm.lock(lock_version)
流程语义（内核注释）：解锁 → 写入 → 重新锁档

轻量化约束：
  - 仅标准库；落盘 truths.jsonl + index.json + lock_state.json（均在 /workspace/evolution/persistent_layer/）
  - write_truth 按 truth_id 幂等：已归档不重复落盘（增量优先、缓存复用）
  - 每条记录带 SHA256，可溯源可锁档
"""
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

DEFAULT_STORE = Path("/workspace/evolution/persistent_layer")


class PersistenceManager:
    """本地持久层管理器：解锁 → 写入 → 重新锁档。"""

    def __init__(self, store_dir: Optional[Path] = None):
        self.store_dir = Path(store_dir) if store_dir else DEFAULT_STORE
        self.truths_file = self.store_dir / "truths.jsonl"
        self.index_file = self.store_dir / "index.json"
        self.lock_file = self.store_dir / "lock_state.json"
        self.store_dir.mkdir(parents=True, exist_ok=True)

    # ---- 锁态 ----
    def is_locked(self) -> bool:
        if not self.lock_file.exists():
            return False
        try:
            return bool(json.loads(self.lock_file.read_text(encoding="utf-8")).get("locked"))
        except (json.JSONDecodeError, OSError):
            return False

    def unlock(self, reason: str = "write_pending") -> None:
        self._set_lock(locked=False, reason=reason)

    def lock(self, lock_version: str = "V2.0", reason: str = "write_done") -> None:
        self._set_lock(locked=True, reason=reason, lock_version=lock_version)

    def _set_lock(self, locked: bool, reason: str, lock_version: Optional[str] = None) -> None:
        state = {
            "locked": locked,
            "reason": reason,
            "lock_version": lock_version,
            "updated_at": datetime.now().isoformat(),
        }
        self.lock_file.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    # ---- 索引 ----
    def _load_index(self) -> Dict[str, Any]:
        if not self.index_file.exists():
            return {}
        try:
            return json.loads(self.index_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_index(self, index: Dict[str, Any]) -> None:
        self.index_file.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")

    def has_truth(self, truth_id: str) -> bool:
        """truth_id 是否已归档（幂等门禁）。"""
        return truth_id in self._load_index()

    # ---- 写入 ----
    def write_truth(self, truth_id: str, category: str, content: str,
                    metadata: Optional[Dict[str, Any]] = None) -> bool:
        """写入一条真值；按 truth_id 幂等（已存在则不重复落盘，返回 True）。"""
        index = self._load_index()
        if truth_id in index:
            return True  # 幂等：已归档

        sha256 = hashlib.sha256(content.encode("utf-8")).hexdigest()
        record = {
            "truth_id": truth_id,
            "category": category,
            "content": content,
            "metadata": metadata or {},
            "sha256": sha256,
            "written_at": datetime.now().isoformat(),
        }
        with open(self.truths_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

        index[truth_id] = {
            "category": category,
            "sha256": sha256,
            "written_at": record["written_at"],
        }
        self._save_index(index)
        return True

    def stats(self) -> Dict[str, Any]:
        """持久层统计。"""
        index = self._load_index()
        return {
            "total_truths": len(index),
            "locked": self.is_locked(),
            "store_dir": str(self.store_dir),
        }


__all__ = ["PersistenceManager"]

if __name__ == "__main__":
    print(json.dumps(PersistenceManager().stats(), ensure_ascii=False, indent=2))
