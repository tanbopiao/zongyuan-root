#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
火斗云智 AIOS — 合规审校引擎（最小实现）
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω

为 compliance_api.py（EVO-P0-003）补齐缺失依赖：
  - BANNED_WORDS      基础禁用词库
  - RISK_SCENARIOS    风险场景库
  - ComplianceChecker 检测 / 统计 / 复核队列

轻量化约束：
  - 仅标准库依赖，不引入第三方包
  - 落点与运行期一致（compliance_api 的 sys.path 含 /workspace/scripts/services）
  - level 仅取 high / medium，避免 merge_rules() 的等级统计越界
"""
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

WORKSPACE = Path("/workspace")
STORE_DIR = WORKSPACE / "evolution" / "compliance"
STORE_FILE = STORE_DIR / "checks.jsonl"

DID_TAG = "DID-BR-000002"

# ============ 基础禁用词库（level 仅 high / medium） ============
BANNED_WORDS: Dict[str, Dict[str, str]] = {
    # 违禁内容
    "赌博": {"level": "high", "suggest": ""},
    "博彩": {"level": "high", "suggest": ""},
    "传销": {"level": "high", "suggest": ""},
    "诈骗": {"level": "high", "suggest": ""},
    "洗钱": {"level": "high", "suggest": ""},
    "色情": {"level": "high", "suggest": ""},
    "毒品": {"level": "high", "suggest": ""},
    "枪支": {"level": "high", "suggest": ""},
    "走私": {"level": "high", "suggest": ""},
    "暴力": {"level": "high", "suggest": ""},
    # 违规经营
    "非法集资": {"level": "high", "suggest": "合规融资"},
    "高利贷": {"level": "high", "suggest": "合规借贷"},
    "虚假宣传": {"level": "high", "suggest": "如实描述"},
    "欺骗消费者": {"level": "high", "suggest": "诚信经营"},
    # 广告绝对化用语
    "国家级": {"level": "medium", "suggest": "高标准"},
    "最高级": {"level": "medium", "suggest": "高水准"},
    "第一品牌": {"level": "medium", "suggest": "知名品牌"},
    "绝对": {"level": "medium", "suggest": "较为"},
    "100%": {"level": "medium", "suggest": "高比例"},
    # 诱导表达
    "点击领取": {"level": "medium", "suggest": "了解详情"},
    "限时抢购": {"level": "medium", "suggest": "限时优惠"},
    "免费送": {"level": "medium", "suggest": "赠品"},
}

# ============ 风险场景库 ============
RISK_SCENARIOS: Dict[str, Dict[str, Any]] = {
    "违禁内容": {"desc": "涉赌博/色情/毒品/暴力等违法违规表达", "level": "high"},
    "金融风险": {"desc": "承诺收益、保本保息、荐股等金融违规", "level": "high"},
    "医疗风险": {"desc": "疗效承诺、根治、无副作用等医疗违规", "level": "high"},
    "法律风险": {"desc": "包赢、胜诉率承诺等法律服务违规", "level": "high"},
    "教育风险": {"desc": "保过、包拿证、命题人等教育违规", "level": "high"},
    "广告绝对化": {"desc": "国家级/最高级/第一等绝对化用语", "level": "medium"},
    "诱导消费": {"desc": "诱导点击、免费送、限时抢购等", "level": "medium"},
}


class ComplianceChecker:
    """合规检测器（最小可用实现）。"""

    def __init__(self, store_file: Path = STORE_FILE):
        self.store_file = Path(store_file)
        self.store_file.parent.mkdir(parents=True, exist_ok=True)

    # ---- 内部：落盘 / 读取 ----
    def _record(self, record: Dict[str, Any]):
        try:
            with open(self.store_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except OSError:
            pass

    def _load(self) -> List[Dict[str, Any]]:
        if not self.store_file.exists():
            return []
        rows = []
        for line in self.store_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return rows

    # ---- 对外能力 ----
    def check(self, text: str) -> Dict[str, Any]:
        """检测单条文本：命中禁用词则给出等级与替换建议。"""
        text = text or ""
        hits = []
        for word, info in BANNED_WORDS.items():
            if word in text:
                hits.append({
                    "word": word,
                    "level": info.get("level", "medium"),
                    "suggest": info.get("suggest", ""),
                })
        if any(h["level"] == "high" for h in hits):
            level = "high"
        elif hits:
            level = "medium"
        else:
            level = "none"
        result = {
            "text": text,
            "passed": level == "none",
            "level": level,
            "hits": hits,
            "hit_count": len(hits),
            "scenarios": [k for k, v in RISK_SCENARIOS.items() if v.get("level") == level] if hits else [],
            "checked_at": datetime.now().isoformat(),
            "did_tag": DID_TAG,
        }
        self._record(result)
        return result

    def stats(self) -> Dict[str, Any]:
        """检测统计。"""
        rows = self._load()
        return {
            "total_checks": len(rows),
            "high_risk": sum(1 for r in rows if r.get("level") == "high"),
            "medium_risk": sum(1 for r in rows if r.get("level") == "medium"),
            "passed": sum(1 for r in rows if r.get("passed")),
            "base_rules": len(BANNED_WORDS),
            "risk_scenarios": len(RISK_SCENARIOS),
            "did_tag": DID_TAG,
        }

    def get_review_queue(self) -> List[Dict[str, Any]]:
        """待复核队列：未通过（high）的检测记录，最近 50 条。"""
        return [r for r in self._load() if r.get("level") == "high"][-50:]


__all__ = ["BANNED_WORDS", "RISK_SCENARIOS", "ComplianceChecker"]
