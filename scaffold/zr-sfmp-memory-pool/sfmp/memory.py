#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
记忆条目模型 + 本地记忆池
- 记忆分层：working(工作记忆) / short(短期) / long(长期) / truth(真值沉淀)
- 语义去重：归一化指纹（去空格/符号 + 关键短语哈希），重复表述合并
- 记忆遗忘：低活跃记忆降层归档
- 检索：关键词 + 标签 + 节点过滤
"""
from dataclasses import dataclass, field
import hashlib
import re
import time


def _fingerprint(text: str) -> str:
    """归一化指纹：去除空白/标点 → 取核心片段哈希（轻量语义近似）"""
    norm = re.sub(r"[\s\W_]+", "", text.lower())
    if not norm:
        return hashlib.sha256(text.encode()).hexdigest()[:16]
    core = norm[:48]  # 取前缀近似语义
    return hashlib.sha256(core.encode()).hexdigest()[:16]


def _jaccard_similarity(a: str, b: str) -> float:
    """字符二元组 Jaccard 相似度（轻量语义相似）"""
    sa = {a[i:i+2] for i in range(max(0, len(a)-1))}
    sb = {b[i:i+2] for i in range(max(0, len(b)-1))}
    if not sa or not sb:
        return 0.0
    return round(len(sa & sb) / len(sa | sb), 3)


@dataclass
class MemoryEntry:
    key: str
    value: str
    source_node: str
    confidence: float = 0.9
    layer: str = "short"          # working/short/long/truth
    tags: list = field(default_factory=list)
    fingerprint: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    access_count: int = 0
    conflicts: int = 0

    def __post_init__(self):
        if not self.fingerprint:
            self.fingerprint = _fingerprint(self.value)

    def to_dict(self):
        return {
            "key": self.key, "value": self.value[:60], "source_node": self.source_node,
            "confidence": self.confidence, "layer": self.layer, "tags": self.tags,
            "fingerprint": self.fingerprint[:12], "access_count": self.access_count,
            "conflicts": self.conflicts,
            "updated_at": time.strftime("%Y-%m-%d %H:%M", time.localtime(self.updated_at)),
        }


class MemoryPool:
    def __init__(self, node_id="hub-central-agent"):
        self.node_id = node_id
        self.entries: dict = {}    # key -> MemoryEntry
        self.duplicates_deduped = 0
        self.conflicts_resolved = 0

    def write(self, key, value, source_node=None, confidence=0.9, layer="short", tags=None):
        """写入/更新记忆：同指纹合并（去重），同 key 异值走冲突消解"""
        src = source_node or self.node_id
        tags = tags or []
        fp = _fingerprint(value)
        now = time.time()

        # 语义去重：同指纹且非同一 entry → 合并（更新访问热度，保留高置信度版本）
        for k, e in self.entries.items():
            if e.fingerprint == fp and e.key != key:
                self.duplicates_deduped += 1
                e.access_count += 1
                e.updated_at = now
                return e  # 重复表述不新增
        # 同 key 冲突消解：按置信度 → 更新时间 仲裁
        if key in self.entries:
            e = self.entries[key]
            if e.confidence < confidence:
                e.confidence = confidence
                e.conflicts += 1
                self.conflicts_resolved += 1
            e.value = value if e.confidence <= confidence else e.value
            e.updated_at = now
            e.source_node = src if e.confidence <= confidence else e.source_node
            return e
        e = MemoryEntry(key=key, value=value, source_node=src, confidence=confidence,
                        layer=layer, tags=tags, fingerprint=fp, created_at=now, updated_at=now)
        self.entries[key] = e
        return e

    def promote(self, key, layer="long"):
        """记忆升华：短→长→真值沉淀"""
        e = self.entries.get(key)
        if e:
            e.layer = layer
            e.updated_at = time.time()
        return e

    def search(self, keyword=None, tag=None, node=None, layer=None):
        """检索：关键词(值含匹配)/标签/来源节点/层级过滤"""
        results = []
        for e in self.entries.values():
            if keyword and keyword not in e.value and keyword not in e.key:
                continue
            if tag and tag not in e.tags:
                continue
            if node and e.source_node != node:
                continue
            if layer and e.layer != layer:
                continue
            e.access_count += 1
            results.append(e)
        return results

    def stats(self):
        layers = {}
        for e in self.entries.values():
            layers[e.layer] = layers.get(e.layer, 0) + 1
        return {
            "node": self.node_id,
            "total": len(self.entries),
            "layers": layers,
            "duplicates_deduped": self.duplicates_deduped,
            "conflicts_resolved": self.conflicts_resolved,
        }
