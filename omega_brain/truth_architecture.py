#!/usr/bin/env python3
"""
四真值架构体系 (Four-Truth Architecture)

ZONGYUAN-ROOT 本源体系的真值统一框架，定义四种真值域:

  1. 设计真值 (Design Truth)   - 架构设计、方案文档、公理定理
  2. 代码真值 (Code Truth)     - 实际代码实现、模块结构、接口定义
  3. 运行真值 (Runtime Truth)  - 实际运行数据、执行结果、指标日志
  4. 规划真值 (Planning Truth) - 未来规划、演进路径、待办任务

核心原则:
  - 四真值必须可交叉校验，任何不一致即为漂移
  - 设计真值是源头，代码真值是实现，运行真值是验证，规划真值是方向
  - 任何修改必须同步更新对应真值域，禁止单域修改
  - 每日进化循环执行四真值一致性校验

真值链: 设计 → 代码 → 运行 → (反馈) → 设计修正
        规划 → 设计 → 代码 → 运行
"""

import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent))


class TruthDomain(Enum):
    DESIGN = "design"      # 设计真值
    CODE = "code"          # 代码真值
    RUNTIME = "runtime"    # 运行真值
    PLANNING = "planning"  # 规划真值


class TruthItem:
    """真值条目"""

    def __init__(self, item_id: str, domain: TruthDomain, title: str,
                 content: Any, source: str = "", version: str = "1.0.0",
                 dependencies: List[str] = None, status: str = "active"):
        self.item_id = item_id
        self.domain = domain
        self.title = title
        self.content = content
        self.source = source
        self.version = version
        self.dependencies = dependencies or []
        self.status = status  # active/deprecated/draft
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.updated_at = self.created_at
        self.hash = self._compute_hash()

    def _compute_hash(self) -> str:
        content = json.dumps({
            'item_id': self.item_id,
            'domain': self.domain.value,
            'title': self.title,
            'content': self._serialize_content(self.content),
            'version': self.version,
            'dependencies': sorted(self.dependencies),
        }, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(content.encode()).hexdigest()

    @staticmethod
    def _serialize_content(content):
        if isinstance(content, (str, int, float, bool)):
            return content
        if isinstance(content, bytes):
            return content.hex()
        if isinstance(content, (list, tuple)):
            return [TruthItem._serialize_content(x) for x in content]
        if isinstance(content, dict):
            return {k: TruthItem._serialize_content(v) for k, v in content.items()}
        if hasattr(content, '__dict__'):
            return str(content)
        return str(content)

    def update(self, content: Any = None, version: str = None, status: str = None):
        """更新真值条目"""
        if content is not None:
            self.content = content
        if version is not None:
            self.version = version
        if status is not None:
            self.status = status
        self.updated_at = datetime.now(timezone.utc).isoformat()
        self.hash = self._compute_hash()

    def to_dict(self) -> dict:
        return {
            'item_id': self.item_id,
            'domain': self.domain.value,
            'title': self.title,
            'content': self._serialize_content(self.content),
            'source': self.source,
            'version': self.version,
            'dependencies': self.dependencies,
            'status': self.status,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'hash': self.hash,
        }

    @classmethod
    def from_dict(cls, d: dict) -> 'TruthItem':
        item = cls(
            item_id=d['item_id'],
            domain=TruthDomain(d['domain']),
            title=d['title'],
            content=d.get('content'),
            source=d.get('source', ''),
            version=d.get('version', '1.0.0'),
            dependencies=d.get('dependencies', []),
            status=d.get('status', 'active'),
        )
        item.created_at = d.get('created_at', item.created_at)
        item.updated_at = d.get('updated_at', item.updated_at)
        item.hash = d.get('hash', item.hash)
        return item


class TruthArchitecture:
    """
    四真值架构统一管理器

    职责:
      - 管理四个真值域的条目存储
      - 执行四真值交叉校验（一致性检测）
      - 追踪真值依赖关系（设计→代码→运行→规划）
      - 生成真值快照和Merkle根
      - 识别漂移并输出修复建议
    """

    VERSION = "1.0.0"

    def __init__(self, store_dir: str = None):
        self.store_dir = Path(store_dir) if store_dir else Path(__file__).parent.parent / 'truth_architecture'
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self._items: Dict[str, TruthItem] = {}
        self._load()

    def _store_file(self, domain: TruthDomain) -> Path:
        return self.store_dir / f'truth_{domain.value}.json'

    def _load(self):
        for domain in TruthDomain:
            f = self._store_file(domain)
            if f.exists():
                try:
                    with open(f) as fp:
                        data = json.load(fp)
                        for item_data in data.get('items', []):
                            item = TruthItem.from_dict(item_data)
                            self._items[item.item_id] = item
                except Exception:
                    pass

    def _save_domain(self, domain: TruthDomain):
        items = [item.to_dict() for item in self._items.values() if item.domain == domain]
        # 计算域Merkle根
        hashes = [item['hash'] for item in items]
        domain_root = self._merkle_root(hashes)
        data = {
            'domain': domain.value,
            'version': self.VERSION,
            'updated_at': datetime.now(timezone.utc).isoformat(),
            'item_count': len(items),
            'merkle_root': domain_root,
            'items': items,
        }
        with open(self._store_file(domain), 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @staticmethod
    def _merkle_root(hashes: List[str]) -> str:
        if not hashes:
            return hashlib.sha256(b'empty').hexdigest()
        level = sorted(hashes)
        while len(level) > 1:
            next_level = []
            for i in range(0, len(level), 2):
                left = level[i]
                right = level[i + 1] if i + 1 < len(level) else left
                next_level.append(hashlib.sha256((left + right).encode()).hexdigest())
            level = next_level
        return level[0]

    # ===== 真值条目管理 =====

    def add(self, item_id: str, domain: TruthDomain, title: str,
            content: Any, source: str = "", version: str = "1.0.0",
            dependencies: List[str] = None) -> TruthItem:
        """添加真值条目"""
        if item_id in self._items:
            raise ValueError(f"truth item already exists: {item_id}")
        item = TruthItem(item_id, domain, title, content, source, version, dependencies)
        self._items[item_id] = item
        self._save_domain(domain)
        return item

    def get(self, item_id: str) -> Optional[TruthItem]:
        return self._items.get(item_id)

    def update(self, item_id: str, content: Any = None, version: str = None,
               status: str = None) -> Optional[TruthItem]:
        """更新真值条目"""
        item = self._items.get(item_id)
        if not item:
            return None
        item.update(content, version, status)
        self._save_domain(item.domain)
        return item

    def deprecate(self, item_id: str) -> bool:
        """废弃真值条目"""
        item = self._items.get(item_id)
        if not item:
            return False
        item.update(status='deprecated')
        self._save_domain(item.domain)
        return True

    def list_by_domain(self, domain: TruthDomain, active_only: bool = True) -> List[TruthItem]:
        items = [i for i in self._items.values() if i.domain == domain]
        if active_only:
            items = [i for i in items if i.status == 'active']
        return sorted(items, key=lambda i: i.item_id)

    # ===== 四真值交叉校验 =====

    def cross_validate(self) -> dict:
        """
        执行四真值交叉校验

        校验规则:
          1. 设计真值中的每个模块，必须有对应的代码真值实现
          2. 代码真值中的每个模块，必须有对应的运行真值验证
          3. 规划真值中的每个任务，必须有对应的设计真值来源
          4. 运行真值中的异常，必须反馈到设计真值或规划真值
          5. 四真值版本号必须一致或有明确的演进关系

        Returns:
            {
                'valid': bool,
                'total_checks': int,
                'passed': int,
                'drifts': [ {type, domain, item_id, severity, description} ],
                'domain_stats': {domain: count},
            }
        """
        drifts = []
        checks = 0
        passed = 0

        design_items = self.list_by_domain(TruthDomain.DESIGN, active_only=False)
        code_items = self.list_by_domain(TruthDomain.CODE, active_only=False)
        runtime_items = self.list_by_domain(TruthDomain.RUNTIME)
        planning_items = self.list_by_domain(TruthDomain.PLANNING)

        # 校验1: 设计→代码 映射
        checks += 1
        design_ids = {i.item_id for i in design_items}
        code_deps = set()
        for item in code_items:
            code_deps.update(item.dependencies)
        missing_code = design_ids - code_deps - {i.item_id for i in code_items}
        if missing_code:
            drifts.append({
                'type': 'design_without_code',
                'domain': 'design→code',
                'items': sorted(missing_code),
                'severity': 'P1',
                'description': f'{len(missing_code)} design items have no code implementation',
            })
        else:
            passed += 1

        # 校验2: 代码→运行 映射（只检查active状态的代码项）
        checks += 1
        active_code_items = [i for i in code_items if i.status == 'active']
        code_ids = {i.item_id for i in active_code_items}
        runtime_deps = set()
        for item in runtime_items:
            runtime_deps.update(item.dependencies)
        missing_runtime = code_ids - runtime_deps - {i.item_id for i in runtime_items}
        if missing_runtime:
            drifts.append({
                'type': 'code_without_runtime',
                'domain': 'code→runtime',
                'items': sorted(missing_runtime),
                'severity': 'P2',
                'description': f'{len(missing_runtime)} code items have no runtime verification',
            })
        else:
            passed += 1

        # 校验3: 规划→设计 映射
        checks += 1
        planning_deps = set()
        for item in planning_items:
            planning_deps.update(item.dependencies)
        missing_design = planning_deps - design_ids
        if missing_design:
            valid_missing = {d for d in missing_design if d}
            if valid_missing:
                drifts.append({
                    'type': 'planning_without_design',
                    'domain': 'planning→design',
                    'items': sorted(valid_missing),
                    'severity': 'P3',
                    'description': f'{len(valid_missing)} planning items reference non-existent design',
                })
        else:
            passed += 1

        # 校验4: 版本一致性
        checks += 1
        versions = {}
        for domain in TruthDomain:
            domain_versions = {i.version for i in self.list_by_domain(domain)}
            versions[domain.value] = list(domain_versions)
        # 检查是否有明显的版本断层
        all_versions = set()
        for v in versions.values():
            all_versions.update(v)
        if len(all_versions) > 3:
            drifts.append({
                'type': 'version_fragmentation',
                'domain': 'all',
                'versions': versions,
                'severity': 'P3',
                'description': f'{len(all_versions)} distinct versions across domains, possible fragmentation',
            })
        else:
            passed += 1

        # 校验5: 哈希完整性（所有条目哈希可复算）
        checks += 1
        hash_valid = True
        for item in self._items.values():
            expected = item._compute_hash()
            if expected != item.hash:
                hash_valid = False
                drifts.append({
                    'type': 'hash_mismatch',
                    'domain': item.domain.value,
                    'item_id': item.item_id,
                    'severity': 'P0',
                    'description': f'item hash mismatch, possible tampering',
                })
        if hash_valid:
            passed += 1

        domain_stats = {d.value: len(self.list_by_domain(d)) for d in TruthDomain}

        return {
            'valid': len(drifts) == 0,
            'total_checks': checks,
            'passed': passed,
            'failed': checks - passed,
            'drifts': drifts,
            'domain_stats': domain_stats,
            'total_items': len(self._items),
            'validated_at': datetime.now(timezone.utc).isoformat(),
        }

    # ===== 真值快照 =====

    def snapshot(self) -> dict:
        """生成四真值架构全局快照"""
        domain_roots = {}
        for domain in TruthDomain:
            items = self.list_by_domain(domain, active_only=False)
            hashes = [i.hash for i in items]
            domain_roots[domain.value] = self._merkle_root(hashes)

        # 全局Merkle根 = 四个域根的Merkle
        global_root = self._merkle_root(list(domain_roots.values()))

        snapshot = {
            'snapshot_id': f'TRUTH-ARCH-{datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")}',
            'architecture_version': self.VERSION,
            'global_merkle_root': global_root,
            'domain_merkle_roots': domain_roots,
            'domain_stats': {d.value: len(self.list_by_domain(d)) for d in TruthDomain},
            'total_items': len(self._items),
            'created_at': datetime.now(timezone.utc).isoformat(),
            'did': 'DID-BR-000002',
            'sovereign_root': 'Ω-TAN-7-001',
            'trace_symbol': 'Ω₀⊂⊙∞⊂Ω',
        }

        # 保存快照
        snapshot_path = self.store_dir / 'snapshots' / f'{snapshot["snapshot_id"]}.json'
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        with open(snapshot_path, 'w') as f:
            json.dump(snapshot, f, indent=2, ensure_ascii=False)
        snapshot['snapshot_path'] = str(snapshot_path)

        return snapshot

    def get_status(self) -> dict:
        """获取四真值架构状态"""
        return {
            'version': self.VERSION,
            'total_items': len(self._items),
            'domains': {
                d.value: {
                    'count': len(self.list_by_domain(d)),
                    'active': len([i for i in self.list_by_domain(d) if i.status == 'active']),
                    'deprecated': len([i for i in self.list_by_domain(d) if i.status == 'deprecated']),
                } for d in TruthDomain
            },
            'store_dir': str(self.store_dir),
        }


# 全局单例
_global_truth_arch: Optional[TruthArchitecture] = None

def get_global_truth_arch() -> TruthArchitecture:
    global _global_truth_arch
    if _global_truth_arch is None:
        _global_truth_arch = TruthArchitecture()
    return _global_truth_arch
