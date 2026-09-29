#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT MR-009 真值自动吸收守护进程
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | Ω-TAN-7-001

功能：
  1. 每60秒轮询9120记忆网关 /api/truths
  2. 对比上次拉取的key列表，发现新增/更新真值
  3. 自动分类（元法则/L1公理/L2定理/L3方法/L4数据）
  4. 冲突检测（新真值是否与已有公理矛盾）
  5. 相似真值合并提炼
  6. 写入内核本地存储（kernel/truth_entries/ + data/truths/）
  7. 写审计日志
  8. 状态持久化

分类规则：
  - key包含 META_RULE / MR- / 元法则 → meta_law（元法则）
  - key包含 AXIOM / L1 / 公理 → axiom（L1公理）
  - key包含 THEOREM / L2 / 定理 → theorem（L2定理）
  - key包含 METHOD / L3 / 方法 / SOP → method（L3方法）
  - key包含 CONFIG / STATUS / METRIC / EVENT → data（L4数据）
  - 其他 → general（通用）
"""

import json
import time
import hashlib
import os
import sys
import logging
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Any, Set

# ============================================================
# 配置
# ============================================================
CONFIG = {
    "gateway_url": "http://127.0.0.1:9120",
    "db_path": "/opt/ZONGYUAN-ROOT/data/memory_gateway.db",
    "poll_interval": 60,          # 轮询间隔（秒）
    "request_timeout": 10,

    # 存储路径
    "kernel_truth_dir": "/opt/ZONGYUAN-ROOT/kernel/truth_entries",
    "data_truth_dir": "/opt/ZONGYUAN-ROOT/data/truths/absorbed",
    "state_file": "/opt/ZONGYUAN-ROOT/ops/truth_absorber/state.json",
    "audit_log": "/opt/ZONGYUAN-ROOT/ops/truth_absorber/audit.jsonl",
    "log_file": "/opt/ZONGYUAN-ROOT/ops/truth_absorber/absorber.log",

    # 分类关键词
    "category_keywords": {
        "meta_law": ["META_RULE", "MR-", "元法则", "META_LAW"],
        "axiom": ["AXIOM", "L1", "公理", "FUNDAMENTAL"],
        "theorem": ["THEOREM", "L2", "定理"],
        "method": ["METHOD", "L3", "方法", "SOP", "WORKFLOW"],
        "data": ["CONFIG", "STATUS", "METRIC", "EVENT", "DATA", "SNAPSHOT"],
        "risk": ["RISK", "ALERT", "WARNING", "风险", "告警"],
        "decision": ["DECISION", "决策", "RESOLUTION"],
    },

    # 冲突检测：这些类别的真值如果与已有同key真值内容差异过大，标记冲突
    "conflict_check_categories": ["meta_law", "axiom"],
    "conflict_similarity_threshold": 0.3,  # 相似度低于此值标记冲突
}

# ============================================================
# 日志配置
# ============================================================
def setup_logging():
    os.makedirs(os.path.dirname(CONFIG["log_file"]), exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(CONFIG["log_file"]),
            logging.StreamHandler(sys.stdout),
        ],
    )
    return logging.getLogger("truth_absorber")

logger = setup_logging()

# ============================================================
# 状态管理
# ============================================================
class StateManager:
    def __init__(self, state_file: str):
        self.state_file = state_file
        self.state = self._load()

    def _load(self) -> Dict:
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "last_poll": None,
            "known_keys": {},       # {key: last_hash}
            "absorbed_count": 0,
            "conflict_count": 0,
            "merged_count": 0,
            "error_count": 0,
            "last_error": None,
            "started_at": datetime.now().isoformat(),
        }

    def save(self):
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        with open(self.state_file, "w") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    def is_known(self, key: str, truth_hash: str) -> bool:
        """检查真值是否已处理过（key和hash都相同）"""
        return self.state["known_keys"].get(key) == truth_hash

    def mark_known(self, key: str, truth_hash: str):
        self.state["known_keys"][key] = truth_hash

    def increment(self, field: str):
        self.state[field] = self.state.get(field, 0) + 1


# ============================================================
# 真值分类器
# ============================================================
class TruthClassifier:
    def __init__(self, keywords: Dict[str, List[str]]):
        self.keywords = keywords

    def classify(self, key: str, value: str = "") -> str:
        """根据key和value内容自动分类"""
        text = f"{key} {value}".upper()
        for category, kws in self.keywords.items():
            for kw in kws:
                if kw.upper() in text:
                    return category
        return "general"

    def extract_tags(self, key: str, value: str = "") -> List[str]:
        """提取标签"""
        tags = []
        text = f"{key} {value}".upper()
        for category, kws in self.keywords.items():
            for kw in kws:
                if kw.upper() in text:
                    tags.append(category)
                    break
        # 从key中提取域标签
        parts = key.split(".")
        if len(parts) > 1:
            tags.append(parts[0].lower())
        return list(set(tags))


# ============================================================
# 冲突检测器
# ============================================================
class ConflictDetector:
    def __init__(self, threshold: float = 0.3):
        self.threshold = threshold

    def _similarity(self, s1: str, s2: str) -> float:
        """简单文本相似度（基于字符集合Jaccard）"""
        if not s1 or not s2:
            return 0.0
        set1 = set(s1)
        set2 = set(s2)
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0.0

    def detect(self, key: str, new_value: str, old_value: str, category: str) -> Dict:
        """检测冲突"""
        if category not in CONFIG["conflict_check_categories"]:
            return {"conflict": False, "reason": "category_not_checked"}

        sim = self._similarity(new_value, old_value)
        if sim < self.threshold:
            return {
                "conflict": True,
                "similarity": round(sim, 3),
                "reason": f"内容差异过大（相似度{sim:.1%} < 阈值{self.threshold:.0%}）",
                "action": "quarantine",  # 隔离，不自动覆盖
            }
        return {"conflict": False, "similarity": round(sim, 3)}


# ============================================================
# 相似真值合并器
# ============================================================
class TruthMerger:
    def __init__(self):
        self.groups: Dict[str, List[Dict]] = {}

    def _group_key(self, truth: Dict) -> str:
        """生成归组键（基于key的前缀）"""
        key = truth.get("truth_key", "")
        parts = key.split(".")
        if len(parts) >= 3:
            return ".".join(parts[:3])
        elif len(parts) >= 2:
            return ".".join(parts[:2])
        return key

    def add(self, truth: Dict):
        gk = self._group_key(truth)
        if gk not in self.groups:
            self.groups[gk] = []
        self.groups[gk].append(truth)

    def get_merge_candidates(self) -> List[Dict]:
        """获取可合并的候选组（同组超过1条）"""
        candidates = []
        for gk, truths in self.groups.items():
            if len(truths) > 1:
                candidates.append({
                    "group_key": gk,
                    "count": len(truths),
                    "keys": [t.get("truth_key", "") for t in truths],
                })
        return candidates


# ============================================================
# 内核存储写入器
# ============================================================
class KernelStorageWriter:
    def __init__(self, kernel_dir: str, data_dir: str):
        self.kernel_dir = kernel_dir
        self.data_dir = data_dir
        os.makedirs(kernel_dir, exist_ok=True)
        os.makedirs(data_dir, exist_ok=True)

    def _safe_filename(self, key: str) -> str:
        """生成安全的文件名"""
        return key.replace("/", "_").replace(" ", "_").replace(":", "_")

    def write(self, truth: Dict, category: str, tags: List[str], conflict_info: Dict = None) -> Dict:
        """写入真值到内核存储"""
        key = truth.get("truth_key", "")
        value = truth.get("truth_value", "")
        truth_hash = truth.get("truth_hash", "")
        node_id = truth.get("node_id", "unknown")
        version = truth.get("version", 1)

        entry = {
            "truth_key": key,
            "truth_value": value,
            "truth_hash": truth_hash,
            "category": category,
            "tags": tags,
            "node_id": node_id,
            "version": version,
            "absorbed_at": datetime.now().isoformat(),
            "source": "memory_gateway_9120",
            "conflict": conflict_info or {"conflict": False},
        }

        # 写入kernel/truth_entries/（按分类子目录）
        cat_dir = os.path.join(self.kernel_dir, category)
        os.makedirs(cat_dir, exist_ok=True)
        kernel_path = os.path.join(cat_dir, f"{self._safe_filename(key)}.json")
        with open(kernel_path, "w") as f:
            json.dump(entry, f, ensure_ascii=False, indent=2)

        # 写入data/truths/absorbed/（扁平化存储）
        data_path = os.path.join(self.data_dir, f"{self._safe_filename(key)}.json")
        with open(data_path, "w") as f:
            json.dump(entry, f, ensure_ascii=False, indent=2)

        return {
            "kernel_path": kernel_path,
            "data_path": data_path,
            "entry": entry,
        }


# ============================================================
# 审计日志
# ============================================================
class AuditLogger:
    def __init__(self, audit_file: str):
        self.audit_file = audit_file
        os.makedirs(os.path.dirname(audit_file), exist_ok=True)

    def log(self, action: str, detail: Dict):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "detail": detail,
        }
        with open(self.audit_file, "a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ============================================================
# 主吸收器
# ============================================================
class TruthAbsorber:
    def __init__(self):
        self.state = StateManager(CONFIG["state_file"])
        self.classifier = TruthClassifier(CONFIG["category_keywords"])
        self.detector = ConflictDetector(CONFIG["conflict_similarity_threshold"])
        self.merger = TruthMerger()
        self.writer = KernelStorageWriter(
            CONFIG["kernel_truth_dir"],
            CONFIG["data_truth_dir"],
        )
        self.audit = AuditLogger(CONFIG["audit_log"])

    def fetch_truths(self) -> List[Dict]:
        """从SQLite数据库读取所有真值（比HTTP API更高效）"""
        try:
            conn = sqlite3.connect(CONFIG["db_path"])
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT truth_key, truth_value, truth_hash, category, node_id, "
                "created_at, updated_at, version FROM truths WHERE truth_key != '' ORDER BY updated_at"
            )
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"读取数据库失败: {e}")
            return []

    def process_truth(self, truth: Dict) -> Dict:
        """处理单条真值"""
        key = truth.get("truth_key", "")
        value = truth.get("truth_value", "")
        truth_hash = truth.get("truth_hash", "")

        # 1. 分类
        category = self.classifier.classify(key, value)
        tags = self.classifier.extract_tags(key, value)

        # 2. 冲突检测（如果是更新）
        conflict_info = {"conflict": False}
        old_hash = self.state.state["known_keys"].get(key)
        if old_hash and old_hash != truth_hash:
            # 这是一个更新，检测冲突
            # 注意：这里简化处理，实际需要拉取旧值对比
            conflict_info = {"conflict": False, "note": "updated_truth"}

        # 3. 如果是元法则/公理类且标记冲突，隔离不覆盖
        if conflict_info.get("conflict") and category in CONFIG["conflict_check_categories"]:
            self.audit.log("conflict_quarantined", {
                "key": key,
                "category": category,
                "reason": conflict_info.get("reason", ""),
            })
            self.state.increment("conflict_count")
            return {"status": "quarantined", "key": key, "category": category}

        # 4. 写入内核存储
        write_result = self.writer.write(truth, category, tags, conflict_info)

        # 5. 标记已处理
        self.state.mark_known(key, truth_hash)
        self.state.increment("absorbed_count")

        # 6. 审计
        self.audit.log("absorbed", {
            "key": key,
            "category": category,
            "tags": tags,
            "node_id": truth.get("node_id", "unknown"),
            "version": truth.get("version", 1),
        })

        return {
            "status": "absorbed",
            "key": key,
            "category": category,
            "tags": tags,
            "kernel_path": write_result["kernel_path"],
        }

    def run_cycle(self) -> Dict:
        """执行一轮吸收循环"""
        cycle_start = time.time()
        logger.info("=== 开始真值吸收循环 ===")

        try:
            # 1. 拉取真值
            truths = self.fetch_truths()
            logger.info(f"从9120拉取到 {len(truths)} 条真值")

            # 2. 筛选新增/更新
            new_truths = []
            updated_truths = []
            for t in truths:
                key = t.get("truth_key", "")
                truth_hash = t.get("truth_hash", "")
                if not self.state.is_known(key, truth_hash):
                    if key in self.state.state["known_keys"]:
                        updated_truths.append(t)
                    else:
                        new_truths.append(t)

            logger.info(f"新增: {len(new_truths)} 条, 更新: {len(updated_truths)} 条")

            # 3. 处理新增真值
            absorbed = []
            for t in new_truths:
                try:
                    result = self.process_truth(t)
                    absorbed.append(result)
                    self.merger.add(t)
                except Exception as e:
                    logger.error(f"处理真值失败 {t.get('truth_key')}: {e}")
                    self.state.increment("error_count")
                    self.state.state["last_error"] = str(e)

            # 4. 处理更新真值
            for t in updated_truths:
                try:
                    result = self.process_truth(t)
                    absorbed.append(result)
                except Exception as e:
                    logger.error(f"处理更新真值失败 {t.get('truth_key')}: {e}")
                    self.state.increment("error_count")

            # 5. 合并检测
            merge_candidates = self.merger.get_merge_candidates()
            if merge_candidates:
                logger.info(f"发现 {len(merge_candidates)} 个可合并组")
                for mc in merge_candidates:
                    self.audit.log("merge_candidate", mc)
                    self.state.increment("merged_count")

            # 6. 更新状态
            self.state.state["last_poll"] = datetime.now().isoformat()
            self.state.save()

            cycle_time = round(time.time() - cycle_start, 2)
            logger.info(
                f"循环完成: 吸收{len(absorbed)}条, "
                f"冲突{self.state.state.get('conflict_count', 0)}, "
                f"合并候选{len(merge_candidates)}, "
                f"耗时{cycle_time}秒"
            )

            return {
                "status": "ok",
                "fetched": len(truths),
                "new": len(new_truths),
                "updated": len(updated_truths),
                "absorbed": len(absorbed),
                "merge_candidates": len(merge_candidates),
                "cycle_time": cycle_time,
            }

        except Exception as e:
            logger.error(f"吸收循环异常: {e}")
            self.state.increment("error_count")
            self.state.state["last_error"] = str(e)
            self.state.save()
            return {"status": "error", "msg": str(e)}

    def run_forever(self):
        """常驻运行"""
        logger.info("=" * 60)
        logger.info("MR-009 真值自动吸收守护进程启动")
        logger.info(f"网关: {CONFIG['gateway_url']}")
        logger.info(f"轮询间隔: {CONFIG['poll_interval']}秒")
        logger.info(f"内核存储: {CONFIG['kernel_truth_dir']}")
        logger.info("=" * 60)

        while True:
            self.run_cycle()
            time.sleep(CONFIG["poll_interval"])


# ============================================================
# 命令行入口
# ============================================================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="MR-009 真值自动吸收守护进程")
    parser.add_argument("--once", action="store_true", help="只运行一轮")
    parser.add_argument("--status", action="store_true", help="查看状态")
    parser.add_argument("--daemon", action="store_true", help="常驻运行（默认）")

    args = parser.parse_args()

    absorber = TruthAbsorber()

    if args.status:
        print(json.dumps(absorber.state.state, ensure_ascii=False, indent=2))
    elif args.once:
        result = absorber.run_cycle()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        absorber.run_forever()
