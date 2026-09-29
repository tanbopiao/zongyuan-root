#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT MR-019 长期记忆系统
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | Ω-TAN-7-001

定位：跨会话持久记忆，实现真正的"永恒"。

核心功能：
  1. 三级记忆存储 - 短期记忆(会话内) / 中期记忆(7天) / 长期记忆(永久)
  2. 记忆巩固器 - 重要信息自动从短期升级到中期、长期
  3. 记忆遗忘器 - 不重要信息自动衰减，防止记忆爆炸
  4. 记忆检索器 - 基于关键词+标签+语义相似度的快速检索
  5. 记忆关联器 - 自动建立记忆间的关联网络
  6. 记忆API - HTTP接口供其他组件调用
  7. 跨会话加载 - 新会话自动加载历史记忆摘要

技术设计：
  - 存储：SQLite + JSON元数据
  - 语义检索：TF-IDF简化版（关键词权重+标签匹配）
  - 巩固算法：访问频率×重要性评分×时间衰减
  - 遗忘算法：指数时间衰减 + 访问频率加权
  - 关联算法：共同标签数 + 内容关键词重叠度
"""

import os
import sys
import json
import time
import sqlite3
import logging
import hashlib
import math
import re
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from collections import Counter, defaultdict
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# ============================================================
# 配置
# ============================================================
CONFIG = {
    "memory_db_path": "/opt/ZONGYUAN-ROOT/data/long_term_memory.db",
    "log_file": "/opt/ZONGYUAN-ROOT/ops/mr019_long_term_memory/mr019.log",
    "state_file": "/opt/ZONGYUAN-ROOT/ops/mr019_long_term_memory/state.json",
    "api_port": 9123,
    "consolidation_interval": 3600,      # 巩固间隔（1小时）
    "forgetting_interval": 7200,         # 遗忘间隔（2小时）
    "short_term_ttl": 86400,             # 短期记忆保留时间（1天）
    "mid_term_ttl": 604800,              # 中期记忆保留时间（7天）
    "consolidation_threshold": 0.6,       # 巩固阈值（重要性评分）
    "forgetting_threshold": 0.2,          # 遗忘阈值（低于此值遗忘）
    "max_short_term": 1000,               # 短期记忆最大数量
    "max_search_results": 20,             # 检索最大结果数
    "node_id": "mr019-long-term-memory",
}

# 中文停用词
STOP_WORDS = set("的了是在我有和就不人都一一个上也很到说要去你会着没有看好自己这那他她它们什么怎么为什么这样那样因为所以如果但是然后而且或者虽然可是就是还是不是可以能够应该需要可能大概也许已经正在将要曾经一直总是经常偶尔有时从来永远".split())

# ============================================================
# 日志
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
    return logging.getLogger("mr019")

logger = setup_logging()

# ============================================================
# 工具函数
# ============================================================
def tokenize(text: str) -> List[str]:
    """简单分词（中文按字+英文按词）"""
    # 提取英文单词
    english_words = re.findall(r'[a-zA-Z]+', text.lower())
    # 提取中文（按2-gram）
    chinese_chars = re.findall(r'[\u4e00-\u9fff]', text)
    chinese_bigrams = [''.join(chinese_chars[i:i+2]) for i in range(len(chinese_chars)-1)]
    # 提取数字
    numbers = re.findall(r'\d+', text)

    tokens = english_words + chinese_bigrams + numbers
    # 过滤停用词和短词
    tokens = [t for t in tokens if t not in STOP_WORDS and len(t) >= 2]
    return tokens


def compute_tfidf_similarity(text1: str, text2: str) -> float:
    """计算两个文本的TF-IDF相似度（简化版）"""
    tokens1 = tokenize(text1)
    tokens2 = tokenize(text2)

    if not tokens1 or not tokens2:
        return 0.0

    counter1 = Counter(tokens1)
    counter2 = Counter(tokens2)

    # 计算余弦相似度
    all_tokens = set(counter1.keys()) | set(counter2.keys())
    dot_product = sum(counter1.get(t, 0) * counter2.get(t, 0) for t in all_tokens)
    norm1 = math.sqrt(sum(v**2 for v in counter1.values()))
    norm2 = math.sqrt(sum(v**2 for v in counter2.values()))

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return round(dot_product / (norm1 * norm2), 3)

# ============================================================
# 组件一：记忆存储层
# ============================================================
class MemoryStore:
    """三级记忆存储层"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """初始化数据库"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 记忆主表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                memory_id TEXT PRIMARY KEY,
                content TEXT,
                title TEXT,
                memory_level TEXT,           -- short_term / mid_term / long_term
                category TEXT,
                tags TEXT,                    -- JSON数组
                importance REAL,              -- 0-1重要性评分
                access_count INTEGER DEFAULT 0,
                last_accessed REAL,
                created_at REAL,
                updated_at REAL,
                expires_at REAL,              -- 过期时间（短期/中期记忆）
                keywords TEXT,                -- JSON数组（用于检索）
                source TEXT,
                metadata TEXT                 -- JSON
            )
        """)

        # 记忆关联表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memory_relations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                memory_id_1 TEXT,
                memory_id_2 TEXT,
                relation_type TEXT,           -- similar / related / causal / hierarchical
                strength REAL,                -- 0-1关联强度
                created_at REAL,
                UNIQUE(memory_id_1, memory_id_2, relation_type)
            )
        """)

        # 访问日志表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS access_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                memory_id TEXT,
                action TEXT,                  -- create / access / update / consolidate / forget
                timestamp REAL,
                details TEXT
            )
        """)

        # 索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memories_level ON memories(memory_level)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(importance)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memories_expires ON memories(expires_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_relations_1 ON memory_relations(memory_id_1)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_relations_2 ON memory_relations(memory_id_2)")

        conn.commit()
        conn.close()

    def create_memory(self, content: str, title: str = "", category: str = "general",
                      tags: List[str] = None, importance: float = 0.5,
                      memory_level: str = "short_term", source: str = "",
                      metadata: Dict = None) -> str:
        """创建记忆"""
        memory_id = f"MEM-{int(time.time())}-{hashlib.md5(content.encode()).hexdigest()[:8]}"
        now = time.time()
        keywords = tokenize(content + " " + title)
        keyword_counts = Counter(keywords)
        top_keywords = [k for k, _ in keyword_counts.most_common(20)]

        # 计算过期时间
        if memory_level == "short_term":
            expires_at = now + CONFIG["short_term_ttl"]
        elif memory_level == "mid_term":
            expires_at = now + CONFIG["mid_term_ttl"]
        else:
            expires_at = None  # 长期记忆永不过期

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO memories
            (memory_id, content, title, memory_level, category, tags, importance,
             access_count, last_accessed, created_at, updated_at, expires_at,
             keywords, source, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?, ?)
        """, (
            memory_id, content, title, memory_level, category,
            json.dumps(tags or []), importance, now, now, now, expires_at,
            json.dumps(top_keywords), source, json.dumps(metadata or {})
        ))
        conn.commit()
        conn.close()

        self._log_access(memory_id, "create", {"level": memory_level, "importance": importance})
        logger.info(f"记忆创建: {memory_id} ({title or content[:30]}, {memory_level})")
        return memory_id

    def get_memory(self, memory_id: str) -> Optional[Dict]:
        """获取记忆"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM memories WHERE memory_id = ?", (memory_id,))
        row = cursor.fetchone()

        if row:
            # 更新访问计数
            cursor.execute("""
                UPDATE memories SET access_count = access_count + 1, last_accessed = ?
                WHERE memory_id = ?
            """, (time.time(), memory_id))
            conn.commit()
            self._log_access(memory_id, "access", {})

        conn.close()

        if row:
            memory = dict(row)
            memory["tags"] = json.loads(memory.get("tags", "[]"))
            memory["keywords"] = json.loads(memory.get("keywords", "[]"))
            memory["metadata"] = json.loads(memory.get("metadata", "{}"))
            return memory
        return None

    def update_memory(self, memory_id: str, **kwargs) -> bool:
        """更新记忆"""
        allowed_fields = ["content", "title", "category", "tags", "importance",
                          "memory_level", "metadata", "source"]
        updates = []
        params = []

        for field, value in kwargs.items():
            if field in allowed_fields:
                if field in ["tags", "metadata"]:
                    value = json.dumps(value)
                updates.append(f"{field} = ?")
                params.append(value)

        if not updates:
            return False

        updates.append("updated_at = ?")
        params.append(time.time())

        # 如果更新了内容，重新计算关键词
        if "content" in kwargs or "title" in kwargs:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT content, title FROM memories WHERE memory_id = ?", (memory_id,))
            row = cursor.fetchone()
            conn.close()
            if row:
                content = kwargs.get("content", row[0])
                title = kwargs.get("title", row[1])
                keywords = tokenize(content + " " + title)
                keyword_counts = Counter(keywords)
                top_keywords = [k for k, _ in keyword_counts.most_common(20)]
                updates.append("keywords = ?")
                params.append(json.dumps(top_keywords))

        params.append(memory_id)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(f"UPDATE memories SET {', '.join(updates)} WHERE memory_id = ?", params)
        conn.commit()
        conn.close()

        self._log_access(memory_id, "update", {"fields": list(kwargs.keys())})
        return True

    def delete_memory(self, memory_id: str) -> bool:
        """删除记忆"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM memories WHERE memory_id = ?", (memory_id,))
        cursor.execute("DELETE FROM memory_relations WHERE memory_id_1 = ? OR memory_id_2 = ?", (memory_id, memory_id))
        conn.commit()
        conn.close()
        self._log_access(memory_id, "forget", {"reason": "manual_delete"})
        return True

    def get_all_memories(self, level: str = None, category: str = None,
                          limit: int = 100, offset: int = 0) -> List[Dict]:
        """获取记忆列表"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = "SELECT * FROM memories WHERE 1=1"
        params = []

        if level:
            query += " AND memory_level = ?"
            params.append(level)
        if category:
            query += " AND category = ?"
            params.append(category)

        query += " ORDER BY importance DESC, created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        memories = []
        for row in rows:
            memory = dict(row)
            memory["tags"] = json.loads(memory.get("tags", "[]"))
            memory["keywords"] = json.loads(memory.get("keywords", "[]"))
            memory["metadata"] = json.loads(memory.get("metadata", "{}"))
            memories.append(memory)
        return memories

    def get_stats(self) -> Dict:
        """获取记忆统计"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT memory_level, COUNT(*) FROM memories GROUP BY memory_level")
        level_counts = dict(cursor.fetchall())

        cursor.execute("SELECT category, COUNT(*) FROM memories GROUP BY category ORDER BY COUNT(*) DESC LIMIT 10")
        category_counts = dict(cursor.fetchall())

        cursor.execute("SELECT COUNT(*) FROM memories")
        total = cursor.fetchone()[0]

        cursor.execute("SELECT AVG(importance) FROM memories")
        avg_importance = cursor.fetchone()[0] or 0

        cursor.execute("SELECT COUNT(*) FROM memory_relations")
        total_relations = cursor.fetchone()[0]

        conn.close()

        return {
            "total_memories": total,
            "by_level": level_counts,
            "top_categories": category_counts,
            "avg_importance": round(avg_importance, 2),
            "total_relations": total_relations,
        }

    def _log_access(self, memory_id: str, action: str, details: Dict):
        """记录访问日志"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO access_log (memory_id, action, timestamp, details)
            VALUES (?, ?, ?, ?)
        """, (memory_id, action, time.time(), json.dumps(details)))
        conn.commit()
        conn.close()

# ============================================================
# 组件二：记忆巩固器
# ============================================================
class MemoryConsolidator:
    """记忆巩固器（自动升级重要记忆）"""

    def __init__(self, store: MemoryStore):
        self.store = store

    def consolidate(self) -> Dict:
        """执行记忆巩固"""
        logger.info("=== 执行记忆巩固 ===")
        now = time.time()
        consolidated = []

        # 获取所有短期和中期记忆
        for level in ["short_term", "mid_term"]:
            memories = self.store.get_all_memories(level=level, limit=500)

            for memory in memories:
                # 计算巩固评分
                score = self._calculate_consolidation_score(memory, now)

                # 如果评分超过阈值，升级记忆
                if score >= CONFIG["consolidation_threshold"]:
                    new_level = "mid_term" if level == "short_term" else "long_term"
                    self.store.update_memory(memory["memory_id"], memory_level=new_level)

                    # 更新过期时间
                    conn = sqlite3.connect(self.store.db_path)
                    cursor = conn.cursor()
                    if new_level == "mid_term":
                        expires_at = now + CONFIG["mid_term_ttl"]
                    else:
                        expires_at = None
                    cursor.execute("UPDATE memories SET expires_at = ? WHERE memory_id = ?",
                                   (expires_at, memory["memory_id"]))
                    conn.commit()
                    conn.close()

                    consolidated.append({
                        "memory_id": memory["memory_id"],
                        "title": memory["title"],
                        "from_level": level,
                        "to_level": new_level,
                        "score": score,
                    })
                    logger.info(f"  巩固: {memory['memory_id']} {level} → {new_level} (评分{score:.2f})")

        result = {
            "timestamp": datetime.now().isoformat(),
            "consolidated_count": len(consolidated),
            "consolidated": consolidated,
        }
        logger.info(f"巩固完成: {len(consolidated)}条记忆升级")
        return result

    def _calculate_consolidation_score(self, memory: Dict, now: float) -> float:
        """计算巩固评分"""
        # 1. 重要性评分（权重40%）
        importance = memory.get("importance", 0.5)

        # 2. 访问频率（权重30%）
        access_count = memory.get("access_count", 0)
        age_days = max(1, (now - memory.get("created_at", now)) / 86400)
        access_freq = min(1.0, access_count / age_days / 5)  # 每天5次访问满分

        # 3. 内容长度/质量（权重15%）
        content_length = len(memory.get("content", ""))
        length_score = min(1.0, content_length / 500)

        # 4. 标签丰富度（权重15%）
        tags = memory.get("tags", [])
        tag_score = min(1.0, len(tags) / 5)

        score = importance * 0.4 + access_freq * 0.3 + length_score * 0.15 + tag_score * 0.15
        return round(score, 3)

# ============================================================
# 组件三：记忆遗忘器
# ============================================================
class MemoryForgetting:
    """记忆遗忘器（自动衰减不重要记忆）"""

    def __init__(self, store: MemoryStore):
        self.store = store

    def forget(self) -> Dict:
        """执行记忆遗忘"""
        logger.info("=== 执行记忆遗忘 ===")
        now = time.time()
        forgotten = []
        decayed = []

        # 1. 删除过期的短期和中期记忆
        conn = sqlite3.connect(self.store.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT memory_id, title, memory_level, importance, expires_at
            FROM memories
            WHERE expires_at IS NOT NULL AND expires_at < ?
        """, (now,))
        expired = cursor.fetchall()

        for row in expired:
            memory_id, title, level, importance, expires_at = row
            # 重要的记忆不删除，降级为长期（但降低重要性）
            if importance >= 0.7:
                cursor.execute("""
                    UPDATE memories SET memory_level = 'long_term', expires_at = NULL,
                    importance = importance * 0.8, updated_at = ?
                    WHERE memory_id = ?
                """, (now, memory_id))
                decayed.append({"memory_id": memory_id, "action": "downgraded_to_long_term"})
                logger.info(f"  降级: {memory_id} 过期但重要，转为长期记忆")
            else:
                cursor.execute("DELETE FROM memories WHERE memory_id = ?", (memory_id,))
                cursor.execute("DELETE FROM memory_relations WHERE memory_id_1 = ? OR memory_id_2 = ?",
                               (memory_id, memory_id))
                forgotten.append({"memory_id": memory_id, "title": title, "level": level})
                logger.info(f"  遗忘: {memory_id} ({title})")

        conn.commit()
        conn.close()

        # 2. 衰减长期未访问记忆的重要性
        conn = sqlite3.connect(self.store.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT memory_id, title, importance, last_accessed
            FROM memories
            WHERE last_accessed < ? AND importance > 0.3
        """, (now - 30 * 86400,))  # 30天未访问
        stale = cursor.fetchall()

        for row in stale:
            memory_id, title, importance, last_accessed = row
            new_importance = max(0.1, importance * 0.95)  # 每次衰减5%
            cursor.execute("UPDATE memories SET importance = ?, updated_at = ? WHERE memory_id = ?",
                           (new_importance, now, memory_id))
            decayed.append({"memory_id": memory_id, "action": "importance_decayed",
                           "from": importance, "to": new_importance})

        conn.commit()
        conn.close()

        # 3. 如果短期记忆超过上限，删除最不重要的
        conn = sqlite3.connect(self.store.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM memories WHERE memory_level = 'short_term'")
        short_count = cursor.fetchone()[0]

        if short_count > CONFIG["max_short_term"]:
            excess = short_count - CONFIG["max_short_term"]
            cursor.execute("""
                SELECT memory_id, title FROM memories
                WHERE memory_level = 'short_term'
                ORDER BY importance ASC, access_count ASC, created_at ASC
                LIMIT ?
            """, (excess,))
            to_remove = cursor.fetchall()

            for row in to_remove:
                memory_id, title = row
                cursor.execute("DELETE FROM memories WHERE memory_id = ?", (memory_id,))
                forgotten.append({"memory_id": memory_id, "title": title, "level": "short_term", "reason": "overflow"})

        conn.commit()
        conn.close()

        result = {
            "timestamp": datetime.now().isoformat(),
            "forgotten_count": len(forgotten),
            "decayed_count": len(decayed),
            "forgotten": forgotten[:20],  # 只记录前20条
            "decayed": decayed[:20],
        }
        logger.info(f"遗忘完成: 删除{len(forgotten)}条, 衰减{len(decayed)}条")
        return result

# ============================================================
# 组件四：记忆检索器
# ============================================================
class MemoryRetriever:
    """记忆检索器（语义+标签+时间）"""

    def __init__(self, store: MemoryStore):
        self.store = store

    def search(self, query: str, category: str = None, tags: List[str] = None,
               level: str = None, limit: int = 10) -> List[Dict]:
        """语义检索"""
        # 获取候选记忆
        candidates = self.store.get_all_memories(level=level, category=category, limit=200)

        # 计算相似度
        scored = []
        query_tokens = set(tokenize(query))

        for memory in candidates:
            # 1. 内容相似度（TF-IDF）
            content_sim = compute_tfidf_similarity(query, memory.get("content", "") + " " + memory.get("title", ""))

            # 2. 关键词匹配
            memory_keywords = set(memory.get("keywords", []))
            keyword_overlap = len(query_tokens & memory_keywords) / max(1, len(query_tokens))

            # 3. 标签匹配
            tag_score = 0.0
            if tags:
                memory_tags = set(memory.get("tags", []))
                tag_score = len(set(tags) & memory_tags) / len(tags)

            # 4. 重要性加权
            importance = memory.get("importance", 0.5)

            # 综合评分
            total_score = content_sim * 0.4 + keyword_overlap * 0.3 + tag_score * 0.2 + importance * 0.1
            scored.append((memory, round(total_score, 3)))

        # 排序并返回
        scored.sort(key=lambda x: x[1], reverse=True)
        results = []
        for memory, score in scored[:limit]:
            memory["search_score"] = score
            results.append(memory)
        return results

    def get_related(self, memory_id: str, limit: int = 5) -> List[Dict]:
        """获取相关记忆"""
        conn = sqlite3.connect(self.store.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT m.*, r.strength, r.relation_type
            FROM memory_relations r
            JOIN memories m ON (m.memory_id = r.memory_id_1 OR m.memory_id = r.memory_id_2)
            WHERE (r.memory_id_1 = ? OR r.memory_id_2 = ?)
              AND m.memory_id != ?
            ORDER BY r.strength DESC
            LIMIT ?
        """, (memory_id, memory_id, memory_id, limit))

        rows = cursor.fetchall()
        conn.close()

        related = []
        for row in rows:
            memory = dict(row)
            memory["tags"] = json.loads(memory.get("tags", "[]"))
            related.append(memory)
        return related

    def get_session_summary(self, max_items: int = 10) -> Dict:
        """获取会话启动时的记忆摘要"""
        # 获取最重要的长期记忆
        long_term = self.store.get_all_memories(level="long_term", limit=max_items)

        # 获取最近的中期记忆
        mid_term = self.store.get_all_memories(level="mid_term", limit=max_items)

        # 获取统计信息
        stats = self.store.get_stats()

        return {
            "summary": "ZONGYUAN-ROOT 长期记忆系统会话摘要",
            "timestamp": datetime.now().isoformat(),
            "stats": stats,
            "key_long_term_memories": [
                {"id": m["memory_id"], "title": m["title"], "importance": m["importance"]}
                for m in long_term[:5]
            ],
            "recent_mid_term_memories": [
                {"id": m["memory_id"], "title": m["title"], "created": datetime.fromtimestamp(m["created_at"]).isoformat()}
                for m in mid_term[:5]
            ],
        }

# ============================================================
# 组件五：记忆关联器
# ============================================================
class MemoryRelator:
    """记忆关联器（自动建立记忆间关联）"""

    def __init__(self, store: MemoryStore):
        self.store = store

    def build_relations(self) -> Dict:
        """构建记忆关联"""
        logger.info("=== 构建记忆关联 ===")
        memories = self.store.get_all_memories(limit=100)

        if len(memories) < 2:
            return {"built": 0, "message": "记忆数量不足"}

        new_relations = 0
        conn = sqlite3.connect(self.store.db_path)
        cursor = conn.cursor()

        # 对每对记忆计算关联度
        for i in range(len(memories)):
            for j in range(i + 1, len(memories)):
                m1 = memories[i]
                m2 = memories[j]

                # 1. 标签重叠
                tags1 = set(m1.get("tags", []))
                tags2 = set(m2.get("tags", []))
                tag_overlap = len(tags1 & tags2) / max(1, len(tags1 | tags2))

                # 2. 内容相似度
                content_sim = compute_tfidf_similarity(
                    m1.get("content", "") + m1.get("title", ""),
                    m2.get("content", "") + m2.get("title", "")
                )

                # 3. 同类别
                same_category = 1.0 if m1.get("category") == m2.get("category") else 0.0

                # 综合关联强度
                strength = tag_overlap * 0.4 + content_sim * 0.4 + same_category * 0.2

                if strength >= 0.3:  # 关联阈值
                    relation_type = "similar" if content_sim > 0.5 else "related"
                    try:
                        cursor.execute("""
                            INSERT OR IGNORE INTO memory_relations
                            (memory_id_1, memory_id_2, relation_type, strength, created_at)
                            VALUES (?, ?, ?, ?, ?)
                        """, (m1["memory_id"], m2["memory_id"], relation_type, strength, time.time()))
                        if cursor.rowcount > 0:
                            new_relations += 1
                    except Exception:
                        pass

        conn.commit()
        conn.close()

        logger.info(f"关联构建完成: 新增{new_relations}条关联")
        return {"built": new_relations, "total_memories": len(memories)}

# ============================================================
# HTTP API 处理器
# ============================================================
class MemoryAPIHandler(BaseHTTPRequestHandler):
    """记忆系统HTTP API"""

    def log_message(self, format, *args):
        pass  # 静默日志

    def _send_json(self, data: Dict, status: int = 200):
        response = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        try:
            if path == "/api/health":
                self._send_json({"status": "healthy", "service": "MR-019 Long Term Memory"})

            elif path == "/api/memory/get":
                memory_id = params.get("id", [""])[0]
                if not memory_id:
                    self._send_json({"error": "missing id"}, 400)
                    return
                memory = self.server.memory_store.get_memory(memory_id)
                self._send_json({"memory": memory} if memory else {"error": "not found"}, 200 if memory else 404)

            elif path == "/api/memory/search":
                query = params.get("q", [""])[0]
                category = params.get("category", [None])[0]
                tags = params.get("tags", [None])[0]
                tags_list = tags.split(",") if tags else None
                level = params.get("level", [None])[0]
                limit = int(params.get("limit", ["10"])[0])

                results = self.server.retriever.search(query, category=category, tags=tags_list, level=level, limit=limit)
                self._send_json({"results": results, "count": len(results)})

            elif path == "/api/memory/list":
                level = params.get("level", [None])[0]
                category = params.get("category", [None])[0]
                limit = int(params.get("limit", ["50"])[0])
                offset = int(params.get("offset", ["0"])[0])
                memories = self.server.memory_store.get_all_memories(level=level, category=category, limit=limit, offset=offset)
                self._send_json({"memories": memories, "count": len(memories)})

            elif path == "/api/memory/related":
                memory_id = params.get("id", [""])[0]
                limit = int(params.get("limit", ["5"])[0])
                related = self.server.retriever.get_related(memory_id, limit=limit)
                self._send_json({"related": related, "count": len(related)})

            elif path == "/api/memory/stats":
                stats = self.server.memory_store.get_stats()
                self._send_json(stats)

            elif path == "/api/memory/session-summary":
                summary = self.server.retriever.get_session_summary()
                self._send_json(summary)

            else:
                self._send_json({"error": "unknown endpoint"}, 404)

        except Exception as e:
            logger.error(f"API错误: {e}")
            self._send_json({"error": str(e)}, 500)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length) if content_length > 0 else b"{}"
            data = json.loads(body.decode("utf-8")) if body else {}

            if path == "/api/memory/create":
                memory_id = self.server.memory_store.create_memory(
                    content=data.get("content", ""),
                    title=data.get("title", ""),
                    category=data.get("category", "general"),
                    tags=data.get("tags", []),
                    importance=data.get("importance", 0.5),
                    memory_level=data.get("memory_level", "short_term"),
                    source=data.get("source", ""),
                    metadata=data.get("metadata", {}),
                )
                self._send_json({"memory_id": memory_id, "status": "created"})

            elif path == "/api/memory/update":
                memory_id = data.get("memory_id", "")
                if not memory_id:
                    self._send_json({"error": "missing memory_id"}, 400)
                    return
                success = self.server.memory_store.update_memory(memory_id, **data)
                self._send_json({"success": success})

            elif path == "/api/memory/delete":
                memory_id = data.get("memory_id", "")
                success = self.server.memory_store.delete_memory(memory_id)
                self._send_json({"success": success})

            elif path == "/api/memory/consolidate":
                result = self.server.consolidator.consolidate()
                self._send_json(result)

            elif path == "/api/memory/forget":
                result = self.server.forgetting.forget()
                self._send_json(result)

            elif path == "/api/memory/build-relations":
                result = self.server.relator.build_relations()
                self._send_json(result)

            else:
                self._send_json({"error": "unknown endpoint"}, 404)

        except Exception as e:
            logger.error(f"API错误: {e}")
            self._send_json({"error": str(e)}, 500)

# ============================================================
# 长期记忆系统主类
# ============================================================
class LongTermMemorySystem:
    """长期记忆系统主类"""

    def __init__(self):
        self.store = MemoryStore(CONFIG["memory_db_path"])
        self.consolidator = MemoryConsolidator(self.store)
        self.forgetting = MemoryForgetting(self.store)
        self.retriever = MemoryRetriever(self.store)
        self.relator = MemoryRelator(self.store)
        self.state = self._load_state()
        self.api_server = None

    def _load_state(self) -> Dict:
        if os.path.exists(CONFIG["state_file"]):
            try:
                with open(CONFIG["state_file"], "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "total_consolidations": 0,
            "total_forgetting_cycles": 0,
            "total_relations_built": 0,
            "last_consolidation": None,
            "last_forgetting": None,
            "started_at": datetime.now().isoformat(),
        }

    def _save_state(self):
        os.makedirs(os.path.dirname(CONFIG["state_file"]), exist_ok=True)
        with open(CONFIG["state_file"], "w") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    def start_api(self):
        """启动HTTP API服务器"""
        server = HTTPServer(("127.0.0.1", CONFIG["api_port"]), MemoryAPIHandler)
        server.memory_store = self.store
        server.retriever = self.retriever
        server.consolidator = self.consolidator
        server.forgetting = self.forgetting
        server.relator = self.relator
        self.api_server = server

        api_thread = threading.Thread(target=server.serve_forever, daemon=True)
        api_thread.start()
        logger.info(f"记忆API启动: http://127.0.0.1:{CONFIG['api_port']}")

    def run_maintenance_cycle(self):
        """执行维护周期（巩固+遗忘+关联）"""
        # 巩固
        cons_result = self.consolidator.consolidate()
        self.state["total_consolidations"] += 1
        self.state["last_consolidation"] = datetime.now().isoformat()

        # 遗忘
        forget_result = self.forgetting.forget()
        self.state["total_forgetting_cycles"] += 1
        self.state["last_forgetting"] = datetime.now().isoformat()

        # 构建关联（每3次维护执行一次）
        if self.state["total_consolidations"] % 3 == 0:
            rel_result = self.relator.build_relations()
            self.state["total_relations_built"] += rel_result.get("built", 0)

        self._save_state()

        return {
            "consolidation": cons_result,
            "forgetting": forget_result,
        }

    def get_status(self) -> Dict:
        """获取系统状态"""
        return {
            "state": self.state,
            "stats": self.store.get_stats(),
            "api_port": CONFIG["api_port"],
            "config": {
                "short_term_ttl": f"{CONFIG['short_term_ttl']//86400}天",
                "mid_term_ttl": f"{CONFIG['mid_term_ttl']//86400}天",
                "consolidation_threshold": CONFIG["consolidation_threshold"],
                "max_short_term": CONFIG["max_short_term"],
            },
        }

    def run_forever(self):
        """常驻运行"""
        logger.info("")
        logger.info("╔══════════════════════════════════════════════════════╗")
        logger.info("║  MR-019 长期记忆系统启动                             ║")
        logger.info("║  三级记忆: 短期(1天) / 中期(7天) / 长期(永久)       ║")
        logger.info("║  巩固: 重要记忆自动升级                               ║")
        logger.info("║  遗忘: 不重要记忆自动衰减                             ║")
        logger.info("║  检索: 语义+标签+时间多维检索                         ║")
        logger.info("║  API端口: {}                                        ║".format(CONFIG["api_port"]))
        logger.info("╚══════════════════════════════════════════════════════╝")
        logger.info("")

        # 启动API
        self.start_api()

        # 初始化一些核心记忆
        self._initialize_core_memories()

        # 主循环
        last_maintenance = 0
        while True:
            now = time.time()

            # 每小时执行维护
            if now - last_maintenance >= CONFIG["consolidation_interval"]:
                self.run_maintenance_cycle()
                last_maintenance = now

            time.sleep(60)

    def _initialize_core_memories(self):
        """初始化核心记忆（如果不存在）"""
        stats = self.store.get_stats()
        if stats["total_memories"] == 0:
            logger.info("初始化核心记忆...")

            # 体系身份记忆
            self.store.create_memory(
                content="ZONGYUAN-ROOT元极恒一自治体系，DID-BR-000002，Ω₀⊂⊙∞⊂Ω，Ω-TAN-7-001。对外品牌：火斗云智AIOS/火斗云智系统。",
                title="体系身份与确权标识",
                category="identity",
                tags=["身份", "确权", "DID", "品牌"],
                importance=1.0,
                memory_level="long_term",
                source="system_init",
            )

            # 核心架构记忆
            self.store.create_memory(
                content="体系采用四阶段进化路径：阶段一元极统一(MR-012/013)、阶段二超认知觉醒(MR-014/015/016)、阶段三永恒自治(MR-017/018/019)、阶段四超认知永恒(MR-020)。",
                title="进化计划与架构路径",
                category="architecture",
                tags=["架构", "进化", "MR组件", "四阶段"],
                importance=0.95,
                memory_level="long_term",
                source="system_init",
            )

            # 核心原则记忆
            self.store.create_memory(
                content="三大铁律：唯一握手点9120端口、云端权威源、真值优先。SOP七步：意图校准→拉记忆→全域对比→三维稳态裁决→执行容错→人工审核部署→沉淀上报。",
                title="核心原则与标准作业流程",
                category="protocol",
                tags=["原则", "SOP", "铁律", "9120"],
                importance=0.9,
                memory_level="long_term",
                source="system_init",
            )

            # 算力架构记忆
            self.store.create_memory(
                content="双轮算力调度：简单任务→本地Qwen2.5-0.5B(8081端口)，复杂任务→外部ai-proxy(8021端口)，失败自动降级。免费额度优先，付费需人工审核。",
                title="算力架构与调度策略",
                category="infrastructure",
                tags=["算力", "LLM", "调度", "双轮"],
                importance=0.85,
                memory_level="long_term",
                source="system_init",
            )

            logger.info("核心记忆初始化完成（4条）")


# ============================================================
# 命令行入口
# ============================================================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="MR-019 长期记忆系统")
    parser.add_argument("command", choices=["init", "stats", "consolidate", "forget", "relations", "search", "status", "daemon"],
                        help="init=初始化核心记忆, stats=查看统计, consolidate=执行巩固, forget=执行遗忘, relations=构建关联, search=测试检索, status=查看状态, daemon=常驻运行")
    parser.add_argument("--query", help="检索查询词")
    args = parser.parse_args()

    system = LongTermMemorySystem()

    if args.command == "init":
        system._initialize_core_memories()
        print("核心记忆初始化完成")
    elif args.command == "stats":
        stats = system.store.get_stats()
        print(json.dumps(stats, ensure_ascii=False, indent=2))
    elif args.command == "consolidate":
        result = system.consolidator.consolidate()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "forget":
        result = system.forgetting.forget()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "relations":
        result = system.relator.build_relations()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "search":
        if not args.query:
            print("请使用 --query 指定检索词")
        else:
            results = system.retriever.search(args.query, limit=5)
            print(f"检索结果: {len(results)}条")
            for r in results:
                print(f"  [{r['search_score']:.3f}] {r['memory_id']}: {r['title']} ({r['memory_level']})")
    elif args.command == "status":
        status = system.get_status()
        print(json.dumps(status, ensure_ascii=False, indent=2))
    elif args.command == "daemon":
        system.run_forever()
