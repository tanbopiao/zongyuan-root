#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自治内核增强：基于全量真值的本地检索与决策引擎
将中枢全量真值作为本地知识库，支持：
1. 关键词/类别检索真值
2. 真值溯源与可信度评估
3. 基于真值的自治决策辅助
"""
import json
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

ROOT = Path("/workspace/persistence_root")
ALL_TRUTHS_FILE = ROOT / "all_truths.json"


class AutonomousKernel:
    """火斗云智自治内核 - 基于本地全量真值库"""

    def __init__(self):
        self.truths = []
        self.seq_index = {}
        self.key_index = {}
        self.category_index = {}
        self._load()

    def _load(self):
        """加载全量真值并建立索引。"""
        if ALL_TRUTHS_FILE.exists():
            self.truths = json.loads(ALL_TRUTHS_FILE.read_text(encoding="utf-8"))
            for t in self.truths:
                self.seq_index[t["seq"]] = t
                self.key_index[t["key"]] = t
                # 按顶级前缀分类
                key = t["key"]
                cat = key
                for sep in [".", "_", "-"]:
                    if sep in key:
                        cat = key.split(sep)[0]
                        break
                self.category_index.setdefault(cat, []).append(t)
            print(f"自治内核加载: {len(self.truths)} 条真值, {len(self.category_index)} 个类别")

    def search(self, keyword: str, category: str = None, limit: int = 10) -> List[Dict]:
        """关键词检索真值。"""
        results = []
        kw = keyword.lower()
        for t in self.truths:
            if category and not t["key"].lower().startswith(category.lower()):
                continue
            text = json.dumps(t, ensure_ascii=False).lower()
            if kw in text:
                results.append(t)
            if len(results) >= limit:
                break
        return results

    def get_by_seq(self, seq: int) -> Optional[Dict]:
        """按 seq 获取真值。"""
        return self.seq_index.get(seq)

    def get_by_key(self, key: str) -> Optional[Dict]:
        """按 key 获取真值。"""
        return self.key_index.get(key)

    def get_category(self, category: str) -> List[Dict]:
        """按类别获取真值列表。"""
        return self.category_index.get(category, [])

    def evaluate_truth_credibility(self, truth: Dict) -> Dict:
        """评估真值可信度。"""
        score = 50  # 基础分
        reasons = []

        # 有明确来源加分
        value = truth.get("value", {})
        if isinstance(value, dict):
            if value.get("source"):
                score += 15
                reasons.append("有明确来源")
            if value.get("url"):
                score += 15
                reasons.append("有溯源URL")
            if value.get("significance"):
                score += 10
                reasons.append("有重要性说明")

        # 心跳类降权
        key = truth.get("key", "")
        if any(hb in key for hb in ["heartbeat", "ntfy", "system_status"]):
            score -= 30
            reasons.append("心跳/状态类(低信息量)")

        # 时间新鲜度
        ts = truth.get("ts", "")
        if ts:
            try:
                from datetime import datetime
                truth_date = datetime.fromisoformat(ts[:10])
                days_old = (datetime.now() - truth_date).days
                if days_old <= 1:
                    score += 10
                    reasons.append("当日新鲜")
                elif days_old > 7:
                    score -= 10
                    reasons.append("超过7天")
            except:
                pass

        score = max(0, min(100, score))
        return {"score": score, "level": "高" if score >= 70 else "中" if score >= 40 else "低", "reasons": reasons}

    def get_stats(self) -> Dict:
        """获取真值库统计。"""
        return {
            "total": len(self.truths),
            "categories": len(self.category_index),
            "top_categories": sorted(
                [(k, len(v)) for k, v in self.category_index.items()],
                key=lambda x: -x[1]
            )[:10],
            "seq_range": [min(self.seq_index.keys()), max(self.seq_index.keys())] if self.seq_index else [0, 0],
        }

    def autonomous_decision(self, query: str) -> Dict:
        """基于真值库的自治决策辅助。"""
        # 检索相关真值
        related = self.search(query, limit=5)

        # 评估可信度
        evaluated = []
        for t in related:
            cred = self.evaluate_truth_credibility(t)
            evaluated.append({
                "seq": t["seq"],
                "key": t["key"][:50],
                "credibility": cred,
            })

        # 生成决策建议
        high_cred = [e for e in evaluated if e["credibility"]["level"] == "高"]
        suggestion = "可基于高可信度真值执行" if high_cred else "真值不足，建议人工复核或联网补充"

        return {
            "query": query,
            "related_truths": len(related),
            "high_credibility_count": len(high_cred),
            "evaluated": evaluated[:5],
            "suggestion": suggestion,
            "timestamp": datetime.now().isoformat(),
        }


# 命令行入口
if __name__ == "__main__":
    kernel = AutonomousKernel()
    stats = kernel.get_stats()
    print(f"\n=== 自治内核状态 ===")
    print(f"真值总数: {stats['total']}")
    print(f"类别数: {stats['categories']}")
    print(f"seq范围: {stats['seq_range']}")
    print(f"Top类别: {stats['top_categories'][:5]}")

    # 测试检索
    print(f"\n=== 检索测试: 'AI合规' ===")
    results = kernel.search("AI合规", limit=3)
    for r in results:
        cred = kernel.evaluate_truth_credibility(r)
        print(f"  seq={r['seq']} cred={cred['score']} key={r['key'][:50]}")

    # 测试决策
    print(f"\n=== 决策测试: '智能体部署' ===")
    decision = kernel.autonomous_decision("智能体部署")
    print(f"  相关真值: {decision['related_truths']}")
    print(f"  高可信度: {decision['high_credibility_count']}")
    print(f"  建议: {decision['suggestion']}")
