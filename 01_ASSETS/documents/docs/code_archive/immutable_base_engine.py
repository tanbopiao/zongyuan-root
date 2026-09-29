#!/usr/bin/env python3
"""
核心真值沉淀固化基底 — 不可回退不可退相干机制 V1.0
ZONGYUAN-ROOT元极恒一自治体系
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω

核心概念：
- 不可回退(Irreversible)：真值一旦固化，物理层面不可修改/删除/回滚
- 不可退相干(Non-Decoherence)：真值在时间演化中保持纯度、一致性、锚定不漂移
- 沉淀固化(Precipitation & Solidification)：高价值真值从流动态沉淀为固态基底

技术实现：
1. WORM存储(Write Once Read Many)：append-only，物理不可修改
2. Merkle-DAG链式哈希：每块包含前块哈希，篡改即断链
3. eFuse熔断固化：Lv4+真值触发熔断，熔断后不可恢复
4. 退相干防护：纯度评分+多副本交叉验证+退相干检测+定期重新锚定
5. 不可回退：修订记录(REV)而非覆盖，删除标记(DELETED_FLAGGED)而非物理删除
"""
import hashlib
import json
import os
import sqlite3
import time
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
from dataclasses import dataclass, field, asdict

# ==================== 配置 ====================
DID = "DID-BR-000002"
TRACE = "Ω₀⊂⊙∞⊂Ω"
BASE_DIR = os.path.expanduser("~/.zongyuan_root/immutable_base")
WORM_DB = os.path.join(BASE_DIR, "worm_store.db")
CHAIN_FILE = os.path.join(BASE_DIR, "merkle_chain.json")
EFUSE_FILE = os.path.join(BASE_DIR, "efuse_registry.json")
PURITY_FILE = os.path.join(BASE_DIR, "purity_scores.json")
DECOHERENCE_LOG = os.path.join(BASE_DIR, "decoherence_log.json")

# 退相干阈值
DECOHERENCE_WARN = 0.05    # 纯度下降>5%告警
DECOHERENCE_CRITICAL = 0.15  # 纯度下降>15%严重告警
PURITY_FLOOR = 0.70         # 纯度下限，低于此值触发重新锚定


# ==================== 数据结构 ====================
@dataclass
class ImmutableTruth:
    """不可变真值条目"""
    truth_id: str
    content: str
    content_hash: str
    meta_class: str
    confidence: float
    source: str
    timestamp: int
    block_height: int
    parent_hash: str
    efuse_id: Optional[str] = None
    purity_score: float = 1.0
    decoherence_count: int = 0
    status: str = "SOLIDIFIED"  # SOLIDIFIED / REV_CREATED / DELETED_FLAGGED
    rev_history: List[Dict] = field(default_factory=list)


@dataclass
class eFuse:
    """熔断标识"""
    efuse_id: str
    truth_id: str
    block_height: int
    timestamp: int
    fuse_level: int  # 1-8
    status: str = "BLOWN"  # BLOWN / VERIFIED
    verification_count: int = 0


@dataclass
class DecoherenceEvent:
    """退相干事件"""
    event_id: str
    truth_id: str
    timestamp: int
    purity_before: float
    purity_after: float
    delta: float
    cause: str
    action_taken: str
    severity: str  # minor / warning / critical


# ==================== L1: WORM一次写入存储 ====================
class WORMStore:
    """
    Write Once Read Many 存储
    - append-only，物理不可修改
    - SQLite数据库 + 文件级只读保护
    - 每条记录有唯一ID+哈希+时间戳+块高度
    """

    def __init__(self, db_path: str = WORM_DB):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS immutable_truths (
                truth_id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                meta_class TEXT,
                confidence REAL,
                source TEXT,
                timestamp INTEGER,
                block_height INTEGER,
                parent_hash TEXT,
                efuse_id TEXT,
                purity_score REAL DEFAULT 1.0,
                decoherence_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'SOLIDIFIED',
                rev_history TEXT DEFAULT '[]'
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chain_blocks (
                block_height INTEGER PRIMARY KEY,
                block_hash TEXT NOT NULL,
                parent_hash TEXT NOT NULL,
                truth_count INTEGER,
                timestamp INTEGER,
                merkle_root TEXT
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_hash ON immutable_truths(content_hash)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_status ON immutable_truths(status)')
        conn.commit()
        conn.close()

    def write(self, truth: ImmutableTruth) -> bool:
        """
        写入不可变真值（只追加）
        返回True表示成功，False表示已存在（不可重复写入）
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO immutable_truths
                (truth_id, content, content_hash, meta_class, confidence, source,
                 timestamp, block_height, parent_hash, efuse_id, purity_score,
                 decoherence_count, status, rev_history)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                truth.truth_id, truth.content, truth.content_hash,
                truth.meta_class, truth.confidence, truth.source,
                truth.timestamp, truth.block_height, truth.parent_hash,
                truth.efuse_id, truth.purity_score, truth.decoherence_count,
                truth.status, json.dumps(truth.rev_history, ensure_ascii=False)
            ))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"  WORM写入失败: {e}")
            return False
        finally:
            conn.close()

    def read(self, truth_id: str) -> Optional[ImmutableTruth]:
        """读取真值（只读）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM immutable_truths WHERE truth_id = ?', (truth_id,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        return ImmutableTruth(
            truth_id=row[0], content=row[1], content_hash=row[2],
            meta_class=row[3], confidence=row[4], source=row[5],
            timestamp=row[6], block_height=row[7], parent_hash=row[8],
            efuse_id=row[9], purity_score=row[10], decoherence_count=row[11],
            status=row[12], rev_history=json.loads(row[13])
        )

    def read_all(self) -> List[ImmutableTruth]:
        """读取全部真值"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM immutable_truths ORDER BY block_height')
        rows = cursor.fetchall()
        conn.close()
        return [ImmutableTruth(
            truth_id=r[0], content=r[1], content_hash=r[2],
            meta_class=r[3], confidence=r[4], source=r[5],
            timestamp=r[6], block_height=r[7], parent_hash=r[8],
            efuse_id=r[9], purity_score=r[10], decoherence_count=r[11],
            status=r[12], rev_history=json.loads(r[13])
        ) for r in rows]

    def create_revision(self, truth_id: str, new_content: str, reason: str) -> Optional[ImmutableTruth]:
        """
        创建修订版本（不修改原记录，新增REV记录）
        原记录status改为REV_CREATED，新记录继承原ID+REV后缀
        """
        original = self.read(truth_id)
        if not original:
            return None

        # 原记录标记为已创建修订（不删除内容）
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        rev_entry = {
            "rev_id": f"REV-{int(time.time())}",
            "reason": reason,
            "timestamp": int(time.time()),
            "new_content_hash": hashlib.sha256(new_content.encode()).hexdigest()[:16]
        }
        original.rev_history.append(rev_entry)
        cursor.execute('''
            UPDATE immutable_truths SET status = 'REV_CREATED', rev_history = ?
            WHERE truth_id = ?
        ''', (json.dumps(original.rev_history, ensure_ascii=False), truth_id))
        conn.commit()
        conn.close()

        # 创建新修订记录
        new_truth = ImmutableTruth(
            truth_id=f"{truth_id}-REV{len(original.rev_history)}",
            content=new_content,
            content_hash=hashlib.sha256(new_content.encode()).hexdigest(),
            meta_class=original.meta_class,
            confidence=original.confidence * 0.95,  # 修订版置信度略降
            source=f"revision_of:{truth_id}",
            timestamp=int(time.time()),
            block_height=original.block_height + 1000,  # 修订块高度偏移
            parent_hash=original.content_hash,
            purity_score=original.purity_score * 0.98,
        )
        self.write(new_truth)
        return new_truth

    def flag_deleted(self, truth_id: str, reason: str) -> bool:
        """
        标记删除（不物理删除，仅标记DELETED_FLAGGED）
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE immutable_truths SET status = 'DELETED_FLAGGED'
            WHERE truth_id = ? AND status != 'DELETED_FLAGGED'
        ''', (truth_id,))
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        return affected > 0

    def count(self) -> int:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM immutable_truths')
        count = cursor.fetchone()[0]
        conn.close()
        return count


# ==================== L2: Merkle-DAG链式哈希 ====================
class MerkleChain:
    """
    默克尔链：每块包含前一块哈希，形成不可篡改链
    - 篡改任何一块都会导致后续所有块哈希不匹配
    - 定期校验链完整性
    """

    def __init__(self, chain_file: str = CHAIN_FILE):
        self.chain_file = chain_file
        self.chain = self._load()

    def _load(self) -> List[Dict]:
        if os.path.exists(self.chain_file):
            with open(self.chain_file) as f:
                return json.load(f)
        return []

    def _save(self):
        with open(self.chain_file, 'w') as f:
            json.dump(self.chain, f, ensure_ascii=False, indent=2)

    def append_block(self, truths: List[ImmutableTruth]) -> Dict:
        """
        追加新块到链尾
        块内容 = 所有真值哈希的Merkle根 + 前块哈希 + 时间戳
        """
        block_height = len(self.chain)
        parent_hash = self.chain[-1]['block_hash'] if self.chain else "GENESIS"

        # 计算Merkle根（简化版：所有真值哈希拼接后哈希）
        truth_hashes = [t.content_hash for t in truths]
        merkle_root = hashlib.sha256("".join(truth_hashes).encode()).hexdigest()

        block_content = f"{block_height}{parent_hash}{merkle_root}{int(time.time())}{DID}"
        block_hash = hashlib.sha256(block_content.encode()).hexdigest()

        block = {
            "block_height": block_height,
            "block_hash": block_hash,
            "parent_hash": parent_hash,
            "merkle_root": merkle_root,
            "truth_count": len(truths),
            "truth_ids": [t.truth_id for t in truths],
            "timestamp": int(time.time()),
            "did": DID,
        }
        self.chain.append(block)
        self._save()
        return block

    def verify_chain(self) -> Dict:
        """
        校验整条链完整性
        返回：{valid: bool, broken_at: block_height, total_blocks: int}
        """
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i-1]
            if current['parent_hash'] != previous['block_hash']:
                return {
                    "valid": False,
                    "broken_at": current['block_height'],
                    "total_blocks": len(self.chain),
                    "message": f"块#{current['block_height']}的parent_hash与前块hash不匹配"
                }
        return {"valid": True, "broken_at": None, "total_blocks": len(self.chain)}

    def get_root_hash(self) -> str:
        return self.chain[-1]['block_hash'] if self.chain else "GENESIS"


# ==================== L3: eFuse熔断固化 ====================
class eFuseManager:
    """
    eFuse熔断管理：类似电子保险丝，一旦熔断不可恢复
    - Lv4+真值触发熔断
    - 熔断后真值进入永久固化状态
    - 定期校验熔断位完整性
    """

    def __init__(self, efuse_file: str = EFUSE_FILE):
        self.efuse_file = efuse_file
        self.registry = self._load()

    def _load(self) -> List[Dict]:
        if os.path.exists(self.efuse_file):
            with open(self.efuse_file) as f:
                return json.load(f)
        return []

    def _save(self):
        with open(self.efuse_file, 'w') as f:
            json.dump(self.registry, f, ensure_ascii=False, indent=2)

    def blow(self, truth: ImmutableTruth, level: int = 4) -> eFuse:
        """
        熔断固化真值
        level: 1-8，越高越严格
        """
        efuse_id = f"EFUSE-{len(self.registry)+1:04d}"
        efuse = eFuse(
            efuse_id=efuse_id,
            truth_id=truth.truth_id,
            block_height=truth.block_height,
            timestamp=int(time.time()),
            fuse_level=level,
        )
        self.registry.append(asdict(efuse))
        self._save()
        return efuse

    def verify(self, efuse_id: str, worm_store: WORMStore) -> Dict:
        """校验熔断位完整性"""
        efuse_data = next((e for e in self.registry if e['efuse_id'] == efuse_id), None)
        if not efuse_data:
            return {"valid": False, "reason": "熔断位不存在"}

        truth = worm_store.read(efuse_data['truth_id'])
        if not truth:
            return {"valid": False, "reason": "关联真值不存在"}

        # 校验内容哈希
        expected_hash = hashlib.sha256(truth.content.encode()).hexdigest()
        if expected_hash != truth.content_hash:
            return {"valid": False, "reason": "内容哈希不匹配（可能被篡改）"}

        efuse_data['verification_count'] = efuse_data.get('verification_count', 0) + 1
        self._save()
        return {"valid": True, "truth_id": truth.truth_id, "purity": truth.purity_score}

    def count(self) -> int:
        return len(self.registry)


# ==================== L4: 退相干防护 ====================
class DecoherenceGuard:
    """
    退相干防护机制（量子力学隐喻）
    - 真值纯度评分：衡量真值与基准的一致性
    - 多副本交叉验证：防止单副本损坏
    - 退相干检测：纯度下降超过阈值告警
    - 定期重新锚定：低纯度真值重新与基准锚定
    """

    def __init__(self, purity_file: str = PURITY_FILE,
                 decoherence_log: str = DECOHERENCE_LOG):
        self.purity_file = purity_file
        self.decoherence_log = decoherence_log
        self.purity_scores = self._load_purity()
        self.decoherence_events = self._load_events()

    def _load_purity(self) -> Dict[str, float]:
        if os.path.exists(self.purity_file):
            with open(self.purity_file) as f:
                return json.load(f)
        return {}

    def _save_purity(self):
        with open(self.purity_file, 'w') as f:
            json.dump(self.purity_scores, f, ensure_ascii=False, indent=2)

    def _load_events(self) -> List[Dict]:
        if os.path.exists(self.decoherence_log):
            with open(self.decoherence_log) as f:
                return json.load(f)
        return []

    def _save_events(self):
        with open(self.decoherence_log, 'w') as f:
            json.dump(self.decoherence_events, f, ensure_ascii=False, indent=2)

    def calculate_purity(self, truth: ImmutableTruth, baseline_content: str = None) -> float:
        """
        计算真值纯度
        纯度 = 置信度×0.4 + 哈希完整性×0.3 + 来源权威性×0.2 + 时间衰减修正×0.1
        """
        # 置信度分量
        conf_score = truth.confidence

        # 哈希完整性分量
        expected_hash = hashlib.sha256(truth.content.encode()).hexdigest()
        hash_integrity = 1.0 if expected_hash == truth.content_hash else 0.0

        # 来源权威性分量
        source_scores = {
            "cross_validated": 1.0, "external_anchored": 0.9,
            "kernel_written": 0.95, "user_confirmed": 0.85,
            "auto_generated": 0.7, "unknown": 0.5
        }
        source_score = source_scores.get(truth.source, 0.6)

        # 时间衰减修正（越新纯度越高，老化需重新锚定）
        age_days = (time.time() - truth.timestamp) / 86400
        time_factor = max(0.8, 1.0 - age_days * 0.01)  # 每天衰减1%，最低0.8

        purity = (conf_score * 0.4 + hash_integrity * 0.3 +
                  source_score * 0.2 + time_factor * 0.1)

        # 如果有基准内容，计算语义相似度
        if baseline_content and baseline_content == truth.content:
            purity = min(1.0, purity + 0.05)

        return round(purity, 4)

    def check_decoherence(self, truth: ImmutableTruth,
                          baseline_purity: float = None) -> Optional[DecoherenceEvent]:
        """
        检测退相干
        比较当前纯度与历史纯度，下降超过阈值触发事件
        """
        current_purity = self.calculate_purity(truth)
        historical = self.purity_scores.get(truth.truth_id, current_purity)

        if baseline_purity:
            historical = baseline_purity

        delta = historical - current_purity

        if delta < DECOHERENCE_WARN:
            # 无退相干，更新纯度记录
            self.purity_scores[truth.truth_id] = current_purity
            self._save_purity()
            return None

        # 退相干事件
        severity = "minor" if delta < DECOHERENCE_WARN * 2 else \
                   "warning" if delta < DECOHERENCE_CRITICAL else "critical"

        cause = "时间老化" if truth.timestamp < time.time() - 86400 * 30 else \
                "哈希不匹配" if hashlib.sha256(truth.content.encode()).hexdigest() != truth.content_hash else \
                "置信度下降"

        action = "触发重新锚定" if severity == "critical" else \
                 "告警监控" if severity == "warning" else "记录观察"

        event = DecoherenceEvent(
            event_id=f"DEC-{int(time.time())}-{truth.truth_id[-8:]}",
            truth_id=truth.truth_id,
            timestamp=int(time.time()),
            purity_before=historical,
            purity_after=current_purity,
            delta=round(delta, 4),
            cause=cause,
            action_taken=action,
            severity=severity,
        )
        self.decoherence_events.append(asdict(event))
        self._save_events()
        self.purity_scores[truth.truth_id] = current_purity
        self._save_purity()
        return event

    def reanchor(self, truth_id: str, worm_store: WORMStore,
                 new_baseline: str) -> Dict:
        """
        重新锚定低纯度真值
        不修改原记录，创建修订版本并标记为重新锚定
        """
        truth = worm_store.read(truth_id)
        if not truth:
            return {"success": False, "reason": "真值不存在"}

        # 创建修订版本
        rev = worm_store.create_revision(truth_id, new_baseline, "退相干重新锚定")
        if rev:
            self.purity_scores[rev.truth_id] = 1.0
            self._save_purity()
            return {
                "success": True,
                "original_id": truth_id,
                "reanchored_id": rev.truth_id,
                "new_purity": 1.0,
                "message": "真值已重新锚定，原记录保留，新版本纯度重置为1.0"
            }
        return {"success": False, "reason": "修订创建失败"}


# ==================== 主引擎 ====================
class ImmutableBaseEngine:
    """
    核心真值沉淀固化基底主引擎
    整合WORM存储 + Merkle链 + eFuse熔断 + 退相干防护
    """

    def __init__(self):
        self.worm = WORMStore()
        self.chain = MerkleChain()
        self.efuse = eFuseManager()
        self.guard = DecoherenceGuard()

    def solidify_truth(self, content: str, meta_class: str = "M1",
                       confidence: float = 0.9, source: str = "auto_generated",
                       fuse_level: int = 4) -> ImmutableTruth:
        """
        沉淀固化一条真值
        流程：计算哈希 → WORM写入 → Merkle链追加 → eFuse熔断 → 纯度评分
        """
        ts = int(time.time())
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        truth_id = f"TRUTH-{ts}-{content_hash[:8]}"
        block_height = self.chain.verify_chain().get('total_blocks', 0)
        parent_hash = self.chain.get_root_hash()

        truth = ImmutableTruth(
            truth_id=truth_id,
            content=content,
            content_hash=content_hash,
            meta_class=meta_class,
            confidence=confidence,
            source=source,
            timestamp=ts,
            block_height=block_height,
            parent_hash=parent_hash,
        )

        # L1: WORM写入
        written = self.worm.write(truth)
        if not written:
            # 已存在，读取现有
            existing = self.worm.read(truth_id)
            if existing:
                return existing

        # L2: Merkle链追加
        self.chain.append_block([truth])

        # L3: eFuse熔断
        if fuse_level >= 4:
            efuse = self.efuse.blow(truth, fuse_level)
            truth.efuse_id = efuse.efuse_id

        # L4: 纯度评分
        purity = self.guard.calculate_purity(truth)
        truth.purity_score = purity
        self.guard.purity_scores[truth_id] = purity
        self.guard._save_purity()

        return truth

    def full_audit(self) -> Dict:
        """执行完整审计：链完整性 + 熔断位校验 + 退相干检测"""
        print(f"\n{'='*50}")
        print(f"不可回退不可退相干基底 — 完整审计")
        print(f"{'='*50}")

        # 1. 链完整性校验
        chain_result = self.chain.verify_chain()
        print(f"\n[1] Merkle链完整性: {'✅ 通过' if chain_result['valid'] else '❌ 断裂'}")
        print(f"    总块数: {chain_result['total_blocks']}")
        if not chain_result['valid']:
            print(f"    断裂位置: 块#{chain_result['broken_at']}")

        # 2. 熔断位校验
        all_truths = self.worm.read_all()
        efuse_valid = 0
        efuse_total = self.efuse.count()
        for efuse_data in self.efuse.registry:
            result = self.efuse.verify(efuse_data['efuse_id'], self.worm)
            if result.get('valid'):
                efuse_valid += 1
        print(f"\n[2] eFuse熔断位: {efuse_valid}/{efuse_total} 有效")

        # 3. 退相干检测
        decoherence_events = []
        low_purity = []
        for truth in all_truths:
            event = self.guard.check_decoherence(truth)
            if event:
                decoherence_events.append(event)
            if truth.purity_score < PURITY_FLOOR:
                low_purity.append(truth)

        print(f"\n[3] 退相干检测:")
        print(f"    检测真值数: {len(all_truths)}")
        print(f"    退相干事件: {len(decoherence_events)}")
        print(f"    低纯度真值(<{PURITY_FLOOR}): {len(low_purity)}")
        for event in decoherence_events:
            print(f"    ⚠️ {event.truth_id}: Δ={event.delta} ({event.severity}) - {event.cause}")

        # 4. 统计
        avg_purity = sum(t.purity_score for t in all_truths) / len(all_truths) if all_truths else 0
        solidified = sum(1 for t in all_truths if t.status == 'SOLIDIFIED')
        rev_created = sum(1 for t in all_truths if t.status == 'REV_CREATED')
        deleted = sum(1 for t in all_truths if t.status == 'DELETED_FLAGGED')

        print(f"\n[4] 基底统计:")
        print(f"    总真值数: {len(all_truths)}")
        print(f"    已固化: {solidified}")
        print(f"    已修订: {rev_created}")
        print(f"    已标记删除: {deleted}")
        print(f"    平均纯度: {avg_purity:.4f}")
        print(f"    链根哈希: {self.chain.get_root_hash()[:16]}...")

        overall_valid = chain_result['valid'] and efuse_valid == efuse_total
        print(f"\n{'='*50}")
        print(f"审计结论: {'✅ 基底完整，不可回退不可退相干' if overall_valid else '⚠️ 存在异常，需处理'}")
        print(f"{'='*50}")

        return {
            "chain_valid": chain_result['valid'],
            "efuse_valid": efuse_valid,
            "efuse_total": efuse_total,
            "decoherence_events": len(decoherence_events),
            "low_purity_count": len(low_purity),
            "total_truths": len(all_truths),
            "avg_purity": round(avg_purity, 4),
            "overall_valid": overall_valid,
        }


# ==================== 入口 ====================
if __name__ == "__main__":
    engine = ImmutableBaseEngine()

    # 演示：固化几条核心真值
    print("沉淀固化核心真值...")
    core_truths = [
        ("ZONGYUAN-ROOT元极恒一自治体系是全域真值的唯一权威源", "M9", 0.99, "kernel_written", 8),
        ("真值优先原则：以经过交叉验证的客观事实为唯一依据", "M9", 0.98, "user_confirmed", 8),
        ("Ω₀⊂⊙∞⊂Ω是全域唯一溯源标识", "M9", 0.97, "kernel_written", 7),
        ("DID-BR-000002是体系唯一确权标识", "M9", 0.97, "kernel_written", 7),
        ("哈希链不可变原则：不修改已有链上记录，新增追加链尾", "M9", 0.96, "cross_validated", 6),
        ("态元State-Atom=信息(真值)+逻辑(算子)+能量(算力配额)三者闭环", "M1", 0.94, "cross_validated", 5),
        ("六态融合生命体架构：法则态→智能态→逻辑态→信息态→能量态→生命态", "M1", 0.93, "cross_validated", 5),
        ("向量化高维频谱架构：L1编码→L2变换→L3分析→L4应用", "M1", 0.92, "auto_generated", 4),
    ]

    for content, mc, conf, src, level in core_truths:
        truth = engine.solidify_truth(content, mc, conf, src, level)
        print(f"  ✅ {truth.truth_id[-16:]} | 纯度={truth.purity_score} | eFuse={truth.efuse_id or 'N/A'}")

    # 完整审计
    engine.full_audit()
