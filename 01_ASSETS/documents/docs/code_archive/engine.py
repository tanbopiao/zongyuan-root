#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
真值自动元秩序化引擎 - 核心引擎
确权: DID-BR-000002 | 溯源: Ω₀⊂⊙∞⊂Ω

全自动流水线：
真值采集 → 四层结构化拆分 → 九大元类归类 → SHA256哈希确权 → Merkle-DAG追加 → 锁档归档 → 上报中枢
"""

import os
import sys
import json
import time
import uuid
import hashlib
import logging
import logging.handlers
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import (
    ENGINE_NAME, ENGINE_VERSION, ENGINE_DID, ENGINE_TRACE_MARK, ENGINE_NODE_ID,
    TRUTH_GATEWAY, STRUCTURE_CONFIG, META_CLASSES, HASH_CONFIG,
    ARCHIVE_CONFIG, REPORT_CONFIG, SCHEDULER_CONFIG, LOG_CONFIG
)


# ============================================================================
# 日志配置
# ============================================================================

def setup_logging():
    """配置日志"""
    log_dir = os.path.dirname(LOG_CONFIG["log_file"])
    if log_dir and not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir, exist_ok=True)
        except Exception:
            pass

    logger = logging.getLogger("MetaOrderEngine")
    logger.setLevel(getattr(logging, LOG_CONFIG["log_level"]))

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(LOG_CONFIG["log_format"]))
    logger.addHandler(console_handler)

    try:
        file_handler = logging.handlers.RotatingFileHandler(
            LOG_CONFIG["log_file"],
            maxBytes=LOG_CONFIG["max_log_size_mb"] * 1024 * 1024,
            backupCount=LOG_CONFIG["backup_count"],
            encoding="utf-8"
        )
        file_handler.setFormatter(logging.Formatter(LOG_CONFIG["log_format"]))
        logger.addHandler(file_handler)
    except Exception as e:
        logger.warning(f"日志文件初始化失败: {e}")

    return logger


logger = setup_logging()


# ============================================================================
# 9120真值网关客户端
# ============================================================================

class TruthGatewayClient:
    """9120真值网关客户端"""

    def __init__(self):
        self.base_url = f"http://{TRUTH_GATEWAY['host']}:{TRUTH_GATEWAY['port']}"
        self.timeout = TRUTH_GATEWAY["timeout"]
        self._online = None

    def is_online(self) -> bool:
        """检查网关是否在线"""
        if self._online is not None:
            return self._online
        try:
            import urllib.request
            # 使用/api/truths端点检查（/api/health不存在）
            req = urllib.request.Request(f"{self.base_url}/api/truths", method="GET")
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                self._online = resp.status == 200
        except Exception:
            self._online = False
        return self._online

    def list_truths(self, prefix: str = "") -> List[str]:
        """列出真值key列表"""
        try:
            import urllib.request
            url = f"{self.base_url}/api/truths"
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                truths = data if isinstance(data, list) else data.get("truths", [])
                if prefix:
                    truths = [t for t in truths if t.startswith(prefix)]
                return truths
        except Exception as e:
            logger.warning(f"列出真值失败: {e}")
            return []

    def get_truth(self, key: str) -> Optional[Dict]:
        """获取单条真值"""
        try:
            import urllib.request
            url = f"{self.base_url}/api/truth/{key}"
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data
        except Exception as e:
            logger.warning(f"获取真值失败 {key}: {e}")
            return None

    def upsert_truth(self, key: str, value: Any, category: str = "meta_order") -> bool:
        """写入/更新真值"""
        try:
            import urllib.request
            data = json.dumps({
                "key": key,
                "value": value if isinstance(value, str) else json.dumps(value, ensure_ascii=False),
                "node_id": ENGINE_NODE_ID,
                "category": category
            }).encode("utf-8")
            req = urllib.request.Request(
                f"{self.base_url}/api/truth/upsert",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result.get("status") == "ok" or result.get("success") is True
        except Exception as e:
            logger.warning(f"写入真值失败 {key}: {e}")
            return False

    def register_node(self) -> bool:
        """注册节点"""
        try:
            import urllib.request
            data = json.dumps({
                "node_id": ENGINE_NODE_ID,
                "node_type": "meta_order_engine",
                "capabilities": ["truth_collection", "structuring", "classification", "hash_anchor", "merkle_dag", "archive"],
                "DID": ENGINE_DID,
                "ROOT_OMEGA": "Ω-TAN-7-001"
            }).encode("utf-8")
            req = urllib.request.Request(
                f"{self.base_url}/api/node/register",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result.get("status") == "ok"
        except Exception as e:
            logger.warning(f"节点注册失败: {e}")
            return False


# ============================================================================
# 增量同步状态管理
# ============================================================================

class SyncState:
    """增量同步状态管理"""

    def __init__(self):
        self.state_file = TRUTH_GATEWAY["state_file"]
        self.state = self._load()

    def _load(self) -> Dict:
        """加载状态"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"加载同步状态失败: {e}")
        return {
            "last_sync_time": 0,
            "last_truth_count": 0,
            "processed_keys": [],
            "total_processed": 0,
            "last_run_id": None,
        }

    def save(self):
        """保存状态"""
        try:
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(self.state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"保存同步状态失败: {e}")

    def is_processed(self, key: str) -> bool:
        """检查是否已处理"""
        return key in self.state.get("processed_keys", [])

    def mark_processed(self, key: str):
        """标记为已处理"""
        if "processed_keys" not in self.state:
            self.state["processed_keys"] = []
        # 只保留最近10000条，防止状态文件过大
        if len(self.state["processed_keys"]) > 10000:
            self.state["processed_keys"] = self.state["processed_keys"][-5000:]
        self.state["processed_keys"].append(key)
        self.state["total_processed"] = self.state.get("total_processed", 0) + 1


# ============================================================================
# 四层结构化拆分器
# ============================================================================

class FourLayerStructurer:
    """四层结构化拆分器
    L1元数据层 / L2内容层 / L3关系层 / L4真值层
    """

    def __init__(self):
        self.config = STRUCTURE_CONFIG

    def structure(self, truth_key: str, truth_value: str, truth_meta: Dict = None) -> Dict:
        """执行四层结构化拆分"""
        truth_meta = truth_meta or {}

        # L1 元数据层
        l1 = self._extract_l1_metadata(truth_key, truth_meta)

        # L2 内容层
        l2 = self._extract_l2_content(truth_value)

        # L3 关系层
        l3 = self._extract_l3_relations(truth_key, truth_value)

        # L4 真值层
        l4 = self._extract_l4_truth(truth_key, truth_value, truth_meta)

        return {
            "l1_metadata": l1,
            "l2_content": l2,
            "l3_relation": l3,
            "l4_truth": l4,
        }

    def _extract_l1_metadata(self, key: str, meta: Dict) -> Dict:
        """L1 元数据层提取"""
        timestamp = meta.get("timestamp", time.time())
        root_id = f"ROOT-{hashlib.sha256(key.encode()).hexdigest()[:16]}"
        snap_id = f"SNAP-{datetime.fromtimestamp(timestamp).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
        content_hash = hashlib.sha256(str(meta.get("value", "")).encode()).hexdigest()

        return {
            "root_id": root_id,
            "snap_id": snap_id,
            "merkle_hash": content_hash,
            "timestamp": timestamp,
            "source": meta.get("source", "9120_truth_gateway"),
            "version": meta.get("version", "v1.0"),
            "original_key": key,
        }

    def _extract_l2_content(self, value: str) -> Dict:
        """L2 内容层分离"""
        result = {
            "text": [],
            "code": [],
            "table": [],
            "image_ref": [],
            "citation": [],
            "raw_length": len(value) if value else 0,
        }

        if not value:
            return result

        # 简单分离：检测代码块
        lines = value.split("\n")
        in_code = False
        code_block = []

        for line in lines:
            if line.strip().startswith("```"):
                if in_code:
                    result["code"].append("\n".join(code_block))
                    code_block = []
                    in_code = False
                else:
                    in_code = True
                continue
            if in_code:
                code_block.append(line)
            else:
                # 检测引用
                if line.strip().startswith(">") or "引用" in line or "来源" in line:
                    result["citation"].append(line.strip())
                # 检测表格（markdown格式）
                elif "|" in line and ("---" in line or line.strip().startswith("|")):
                    result["table"].append(line.strip())
                # 检测图片引用
                elif "![" in line or "<img" in line:
                    result["image_ref"].append(line.strip())
                elif line.strip():
                    result["text"].append(line.strip())

        return result

    def _extract_l3_relations(self, key: str, value: str) -> Dict:
        """L3 关系层提取"""
        relations = {
            "entities": [],
            "causal": [],
            "temporal": [],
            "dependency": [],
            "similarity": [],
        }

        if not value:
            return relations

        # 实体提取（简单关键词匹配）
        entity_keywords = ["元极恒一", "ZONGYUAN-ROOT", "火斗云智", "9120", "记忆网关",
                          "贝叶斯", "五行", "算子", "元规则", "元法则", "元公理",
                          "中枢大脑", "智能体", "闭环", "熵减", "稳态"]
        for kw in entity_keywords:
            if kw in key or kw in value:
                relations["entities"].append(kw)

        # 因果关系检测
        causal_words = ["因为", "所以", "导致", "引起", "使得", "因此", "由于", "从而"]
        for word in causal_words:
            if word in value:
                relations["causal"].append(word)
                break

        # 时序关系检测
        temporal_words = ["首先", "然后", "接着", "最后", "之前", "之后", "同时", "逐步"]
        for word in temporal_words:
            if word in value:
                relations["temporal"].append(word)
                break

        # 依赖关系检测
        dep_words = ["依赖", "基于", "需要", "调用", "接入", "集成"]
        for word in dep_words:
            if word in value:
                relations["dependency"].append(word)
                break

        return relations

    def _extract_l4_truth(self, key: str, value: str, meta: Dict) -> Dict:
        """L4 真值层提取"""
        # 置信度评估
        confidence = self._assess_confidence(key, value, meta)

        # 冲突标记
        conflict_mark = self._detect_conflict(key, value)

        # 验证状态
        verification_status = "verified" if confidence >= 0.8 else ("pending" if confidence >= 0.5 else "low_confidence")

        return {
            "confidence": confidence,
            "source": meta.get("source", "9120"),
            "version": meta.get("version", "v1.0"),
            "conflict_mark": conflict_mark,
            "verification_status": verification_status,
            "truth_purity_score": confidence,
        }

    def _assess_confidence(self, key: str, value: str, meta: Dict) -> float:
        """评估真值置信度"""
        score = 0.7  # 默认置信度

        # 来源权重
        source = meta.get("source", "")
        if "verified" in source or "official" in source:
            score += 0.15
        elif "auto" in source or "generated" in source:
            score -= 0.1

        # 内容长度（过短可能低价值）
        if value and len(value) < 20:
            score -= 0.1
        elif value and len(value) > 200:
            score += 0.05

        # key前缀权重
        high_value_prefixes = ["METALAW", "META", "PROTOCOL", "DECISION", "TRUTH"]
        if any(key.startswith(p) for p in high_value_prefixes):
            score += 0.1

        return max(0.1, min(0.99, score))

    def _detect_conflict(self, key: str, value: str) -> str:
        """检测冲突标记"""
        conflict_words = ["冲突", "矛盾", "不一致", "错误", "失败", "告警", "异常"]
        for word in conflict_words:
            if word in key or (value and word in value):
                return f"conflict_detected:{word}"
        return "none"


# ============================================================================
# 九大元类分类器
# ============================================================================

class MetaClassClassifier:
    """九大元类分类器"""

    def __init__(self):
        self.classes = META_CLASSES

    def classify(self, truth_key: str, truth_value: str, structured: Dict) -> Dict:
        """执行九大元类分类"""
        scores = {}

        for class_id, class_info in self.classes.items():
            score = self._calculate_class_score(class_id, class_info, truth_key, truth_value, structured)
            scores[class_id] = score

        # 找出最高分的元类
        best_class = max(scores, key=scores.get)
        best_score = scores[best_class]

        return {
            "primary_class": best_class,
            "primary_class_name": self.classes[best_class]["name"],
            "primary_score": best_score,
            "all_scores": scores,
            "confidence": best_score / sum(scores.values()) if sum(scores.values()) > 0 else 0,
        }

    def _calculate_class_score(self, class_id: str, class_info: Dict,
                                 key: str, value: str, structured: Dict) -> float:
        """计算某个元类的匹配分数"""
        score = 0.0
        keywords = class_info["keywords"]
        weight = class_info["weight"]

        # 关键词匹配（key和value中）
        key_lower = key.lower()
        value_lower = (value or "").lower()

        for kw in keywords:
            kw_lower = kw.lower()
            if kw_lower in key_lower:
                score += 2.0  # key中匹配权重更高
            if kw_lower in value_lower:
                score += 1.0

        # L4真值层验证状态加成
        verification = structured.get("l4_truth", {}).get("verification_status", "")
        if verification == "verified" and class_id in ["M1", "M2", "M9"]:
            score += 0.5

        # L3关系层类型加成
        relations = structured.get("l3_relation", {})
        if relations.get("causal") and class_id == "M6":
            score += 0.5
        if relations.get("temporal") and class_id == "M3":
            score += 0.3

        return score * weight


# ============================================================================
# SHA256哈希确权 + Merkle-DAG
# ============================================================================

class HashAnchorMerkleDAG:
    """SHA256哈希确权 + Merkle-DAG主链追加"""

    def __init__(self):
        self.config = HASH_CONFIG
        self.chain_file = self.config["merkle_dag"]["chain_file"]
        self.chain = self._load_chain()

    def _load_chain(self) -> Dict:
        """加载Merkle-DAG链"""
        try:
            if os.path.exists(self.chain_file):
                with open(self.chain_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"加载Merkle-DAG链失败: {e}")
        return {
            "chain_id": f"MERKLE-DAG-{uuid.uuid4().hex[:8]}",
            "blocks": [],
            "root_hash": None,
            "total_assets": 0,
            "created_at": time.time(),
        }

    def _save_chain(self):
        """保存Merkle-DAG链"""
        try:
            os.makedirs(os.path.dirname(self.chain_file), exist_ok=True)
            with open(self.chain_file, "w", encoding="utf-8") as f:
                json.dump(self.chain, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"保存Merkle-DAG链失败: {e}")

    def anchor(self, structured: Dict, classification: Dict) -> Dict:
        """执行SHA256哈希确权"""
        # 构建确权数据
        anchor_data = {
            "root_id": structured["l1_metadata"]["root_id"],
            "original_key": structured["l1_metadata"]["original_key"],
            "content_hash": structured["l1_metadata"]["merkle_hash"],
            "meta_class": classification["primary_class"],
            "meta_class_name": classification["primary_class_name"],
            "confidence": structured["l4_truth"]["confidence"],
            "timestamp": structured["l1_metadata"]["timestamp"],
            "did": ENGINE_DID,
            "trace_mark": ENGINE_TRACE_MARK,
        }

        # 计算SHA256哈希
        hash_input = json.dumps(anchor_data, sort_keys=True, ensure_ascii=False)
        sha256_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()

        anchor_result = {
            "sha256": sha256_hash,
            "anchor_data": anchor_data,
            "anchor_time": time.time(),
            "algorithm": self.config["algorithm"],
        }

        return anchor_result

    def append_to_dag(self, anchor_results: List[Dict]) -> Dict:
        """批量追加到Merkle-DAG主链"""
        if not anchor_results:
            return {"status": "skipped", "reason": "no_anchors"}

        block_size = self.config["merkle_dag"]["block_size"]

        # 分批构建Merkle块
        for i in range(0, len(anchor_results), block_size):
            batch = anchor_results[i:i + block_size]
            block = self._build_merkle_block(batch)
            self.chain["blocks"].append(block)
            self.chain["total_assets"] += len(batch)

        # 更新根哈希
        self._update_root_hash()
        self._save_chain()

        return {
            "status": "success",
            "blocks_added": len(self.chain["blocks"]),
            "total_assets": self.chain["total_assets"],
            "root_hash": self.chain["root_hash"],
        }

    def _build_merkle_block(self, anchors: List[Dict]) -> Dict:
        """构建Merkle块"""
        # 计算每个叶子节点的哈希
        leaf_hashes = [a["sha256"] for a in anchors]

        # 构建Merkle树（简化版：两两哈希）
        merkle_root = self._compute_merkle_root(leaf_hashes)

        prev_hash = self.chain["blocks"][-1]["block_hash"] if self.chain["blocks"] else "GENESIS"

        block = {
            "block_index": len(self.chain["blocks"]),
            "block_hash": hashlib.sha256(f"{prev_hash}{merkle_root}{time.time()}".encode()).hexdigest(),
            "prev_hash": prev_hash,
            "merkle_root": merkle_root,
            "leaf_count": len(anchors),
            "leaf_hashes": leaf_hashes,
            "timestamp": time.time(),
        }

        return block

    def _compute_merkle_root(self, hashes: List[str]) -> str:
        """计算Merkle根哈希"""
        if not hashes:
            return hashlib.sha256(b"empty").hexdigest()
        if len(hashes) == 1:
            return hashes[0]

        # 两两配对哈希
        while len(hashes) > 1:
            new_level = []
            for i in range(0, len(hashes), 2):
                if i + 1 < len(hashes):
                    combined = hashes[i] + hashes[i + 1]
                else:
                    combined = hashes[i] + hashes[i]  # 奇数个时复制最后一个
                new_level.append(hashlib.sha256(combined.encode()).hexdigest())
            hashes = new_level

        return hashes[0]

    def _update_root_hash(self):
        """更新链根哈希"""
        if self.chain["blocks"]:
            all_block_hashes = [b["block_hash"] for b in self.chain["blocks"]]
            self.chain["root_hash"] = self._compute_merkle_root(all_block_hashes)


# ============================================================================
# 锁档归档器
# ============================================================================

class Archiver:
    """三层锁档归档器"""

    def __init__(self):
        self.config = ARCHIVE_CONFIG
        self.archive_dir = self.config["archive_dir"]

    def archive(self, run_id: str, processed_truths: List[Dict],
                anchor_results: List[Dict], dag_result: Dict) -> Dict:
        """执行锁档归档"""
        os.makedirs(self.archive_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot_file = os.path.join(self.archive_dir, f"meta_order_snapshot_{timestamp}.json")

        # 构建归档快照
        snapshot = {
            "snapshot_id": f"META-ORDER-{run_id}",
            "timestamp": time.time(),
            "datetime": datetime.now().isoformat(),
            "did": ENGINE_DID,
            "trace_mark": ENGINE_TRACE_MARK,
            "lock_level": self.config["lock_level"],
            "processed_count": len(processed_truths),
            "processed_truths": processed_truths,
            "anchor_count": len(anchor_results),
            "dag_result": dag_result,
            "archive_levels": {},
        }

        # L3 内核快照（本地JSON）
        if self.config["levels"]["L3_kernel"]["enabled"]:
            try:
                with open(snapshot_file, "w", encoding="utf-8") as f:
                    json.dump(snapshot, f, ensure_ascii=False, indent=2)
                snapshot["archive_levels"]["L3_kernel"] = {
                    "status": "success",
                    "file": snapshot_file,
                    "size_bytes": os.path.getsize(snapshot_file),
                }
            except Exception as e:
                snapshot["archive_levels"]["L3_kernel"] = {"status": "failed", "error": str(e)}

        # L1 云盘归档（需飞书API，暂跳过）
        snapshot["archive_levels"]["L1_cloud"] = {"status": "skipped", "reason": "requires_feishu_api"}

        # L2 知识库节点（需飞书wiki API，暂跳过）
        snapshot["archive_levels"]["L2_knowledge"] = {"status": "skipped", "reason": "requires_feishu_wiki_api"}

        return snapshot


# ============================================================================
# 上报中枢
# ============================================================================

class Reporter:
    """上报中枢（9120 + 飞书）"""

    def __init__(self, gateway: TruthGatewayClient):
        self.gateway = gateway
        self.config = REPORT_CONFIG

    def report(self, run_id: str, summary: Dict, snapshot: Dict) -> Dict:
        """上报执行结果"""
        result = {"to_9120": False, "to_feishu": False}

        # 上报到9120
        if self.config["to_9120"] and self.gateway.is_online():
            report_key = f"{self.config['report_prefix']}RUN.{run_id}"
            report_value = {
                "run_id": run_id,
                "summary": summary,
                "snapshot_id": snapshot.get("snapshot_id"),
                "dag_root_hash": snapshot.get("dag_result", {}).get("root_hash"),
                "timestamp": time.time(),
            }
            success = self.gateway.upsert_truth(report_key, report_value, category="meta_order_report")
            result["to_9120"] = success
            result["9120_key"] = report_key

        # 上报到飞书（需webhook）
        if self.config["to_feishu"] and self.config["feishu_webhook"]:
            # 飞书webhook上报逻辑
            result["to_feishu"] = "pending_implementation"

        return result


# ============================================================================
# 主引擎
# ============================================================================

class TruthMetaOrderEngine:
    """真值自动元秩序化主引擎"""

    def __init__(self):
        self.name = ENGINE_NAME
        self.version = ENGINE_VERSION
        self.gateway = TruthGatewayClient()
        self.sync_state = SyncState()
        self.structurer = FourLayerStructurer()
        self.classifier = MetaClassClassifier()
        self.hasher = HashAnchorMerkleDAG()
        self.archiver = Archiver()
        self.reporter = Reporter(self.gateway)

    def initialize(self) -> bool:
        """初始化引擎"""
        logger.info("=" * 60)
        logger.info(f"{self.name} v{self.version} 初始化")
        logger.info(f"确权: {ENGINE_DID} | 溯源: {ENGINE_TRACE_MARK}")
        logger.info("=" * 60)

        # 检查9120连通性
        if self.gateway.is_online():
            logger.info("9120真值网关: 在线 ✓")
            # 注册节点
            self.gateway.register_node()
        else:
            logger.warning("9120真值网关: 不在线 ✗")

        logger.info("引擎初始化完成 ✓")
        return True

    def run(self) -> Dict:
        """执行一次完整的元秩序化流水线"""
        run_id = f"{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
        logger.info(f"\n{'='*60}")
        logger.info(f"【元秩序化运行启动】{run_id}")
        logger.info(f"{'='*60}")

        start_time = time.time()
        processed_truths = []
        anchor_results = []

        try:
            # ===== 第一步：真值采集（增量同步）=====
            logger.info("\n--- 第一步：真值采集（增量同步）---")
            new_truths = self._collect_new_truths()
            logger.info(f"采集到新增真值: {len(new_truths)} 条")

            if not new_truths:
                logger.info("无新增真值，跳过本次运行")
                return self._build_result(run_id, 0, [], [], {}, start_time, "no_new_truths")

            # 限制每次处理数量
            max_per_run = SCHEDULER_CONFIG["max_truths_per_run"]
            if len(new_truths) > max_per_run:
                logger.info(f"超过单次处理上限({max_per_run})，截取前{max_per_run}条")
                new_truths = new_truths[:max_per_run]

            # ===== 第二步：四层结构化拆分 =====
            logger.info("\n--- 第二步：四层结构化拆分 ---")
            structured_results = []
            for truth_key, truth_value in new_truths:
                structured = self.structurer.structure(truth_key, truth_value)
                structured_results.append((truth_key, truth_value, structured))
            logger.info(f"四层结构化完成: {len(structured_results)} 条")

            # ===== 第三步：九大元类归类 =====
            logger.info("\n--- 第三步：九大元类归类 ---")
            classification_results = []
            class_distribution = {}
            for truth_key, truth_value, structured in structured_results:
                classification = self.classifier.classify(truth_key, truth_value, structured)
                classification_results.append((truth_key, truth_value, structured, classification))
                cls_name = classification["primary_class_name"]
                class_distribution[cls_name] = class_distribution.get(cls_name, 0) + 1
            logger.info(f"九大元类归类完成: {class_distribution}")

            # ===== 第四步：SHA256哈希确权 =====
            logger.info("\n--- 第四步：SHA256哈希确权 ---")
            for truth_key, truth_value, structured, classification in classification_results:
                anchor = self.hasher.anchor(structured, classification)
                anchor_results.append(anchor)

                # 构建处理后的真值记录
                processed_truths.append({
                    "original_key": truth_key,
                    "root_id": structured["l1_metadata"]["root_id"],
                    "meta_class": classification["primary_class"],
                    "meta_class_name": classification["primary_class_name"],
                    "confidence": structured["l4_truth"]["confidence"],
                    "sha256": anchor["sha256"],
                    "verification_status": structured["l4_truth"]["verification_status"],
                })

                # 标记为已处理
                self.sync_state.mark_processed(truth_key)

            logger.info(f"SHA256哈希确权完成: {len(anchor_results)} 条")

            # ===== 第五步：Merkle-DAG主链追加 =====
            logger.info("\n--- 第五步：Merkle-DAG主链追加 ---")
            dag_result = self.hasher.append_to_dag(anchor_results)
            logger.info(f"Merkle-DAG追加完成: 块{dag_result.get('blocks_added')}, "
                       f"总资产{dag_result.get('total_assets')}, "
                       f"根哈希{dag_result.get('root_hash', 'N/A')[:16]}...")

            # ===== 第六步：锁档归档 =====
            logger.info("\n--- 第六步：锁档归档 ---")
            snapshot = self.archiver.archive(run_id, processed_truths, anchor_results, dag_result)
            logger.info(f"锁档归档完成: {snapshot.get('snapshot_id')}")

            # ===== 第七步：上报中枢 =====
            logger.info("\n--- 第七步：上报中枢 ---")
            summary = {
                "run_id": run_id,
                "processed_count": len(processed_truths),
                "class_distribution": class_distribution,
                "dag_root_hash": dag_result.get("root_hash"),
                "duration_seconds": time.time() - start_time,
            }
            report_result = self.reporter.report(run_id, summary, snapshot)
            logger.info(f"上报中枢完成: 9120={report_result.get('to_9120')}")

            # 保存同步状态
            self.sync_state.state["last_sync_time"] = time.time()
            self.sync_state.state["last_run_id"] = run_id
            self.sync_state.save()

            return self._build_result(run_id, len(processed_truths), processed_truths,
                                       class_distribution, dag_result, start_time, "success")

        except Exception as e:
            logger.error(f"运行失败: {e}", exc_info=True)
            return self._build_result(run_id, 0, [], [], {}, start_time, f"failed:{e}")

    def _collect_new_truths(self) -> List[Tuple[str, str]]:
        """采集新增真值（增量同步）"""
        if not self.gateway.is_online():
            return []

        all_keys = self.gateway.list_truths()
        new_truths = []

        for key in all_keys:
            # 跳过已处理的
            if self.sync_state.is_processed(key):
                continue
            # 跳过引擎自身上报的（避免循环）
            if key.startswith("METAORDER."):
                continue

            # 获取真值内容
            truth = self.gateway.get_truth(key)
            if truth:
                value = truth.get("truth", {}).get("value", "") or truth.get("value", "")
                if isinstance(value, dict):
                    value = json.dumps(value, ensure_ascii=False)
                new_truths.append((key, str(value)))

        return new_truths

    def _build_result(self, run_id: str, processed_count: int,
                       processed_truths: List[Dict], class_distribution: Dict,
                       dag_result: Dict, start_time: float, status: str) -> Dict:
        """构建运行结果"""
        return {
            "run_id": run_id,
            "status": status,
            "processed_count": processed_count,
            "class_distribution": class_distribution,
            "dag_root_hash": dag_result.get("root_hash"),
            "dag_total_assets": dag_result.get("total_assets"),
            "duration_seconds": round(time.time() - start_time, 2),
            "processed_truths_sample": processed_truths[:5],  # 只返回前5条作为样本
        }

    def get_status(self) -> Dict:
        """获取引擎状态"""
        return {
            "engine": {
                "name": self.name,
                "version": self.version,
                "did": ENGINE_DID,
                "trace_mark": ENGINE_TRACE_MARK,
            },
            "gateway": {
                "online": self.gateway.is_online(),
                "base_url": self.gateway.base_url,
            },
            "sync_state": {
                "last_sync_time": self.sync_state.state.get("last_sync_time"),
                "total_processed": self.sync_state.state.get("total_processed", 0),
                "last_run_id": self.sync_state.state.get("last_run_id"),
            },
            "merkle_dag": {
                "chain_id": self.hasher.chain.get("chain_id"),
                "blocks": len(self.hasher.chain.get("blocks", [])),
                "total_assets": self.hasher.chain.get("total_assets", 0),
                "root_hash": self.hasher.chain.get("root_hash"),
            },
        }
