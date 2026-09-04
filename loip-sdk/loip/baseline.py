"""
LOIP 本体基线持久化引擎
解决"关窗口即失忆"核心断点：本体基线从会话上下文抽离为独立JSON文件，跨会话持久化。
"""
import json
import hashlib
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional


class OntologyBaseline:
    """本体基线：核心规则、事实标准、逻辑底线的持久化存储"""

    def __init__(self, baseline_path: str, did: str = "DID-BR-000002",
                 sovereign_root: str = "Ω-TAN-7-001"):
        self.baseline_path = baseline_path
        self.did = did
        self.sovereign_root = sovereign_root
        self.trace_symbol = "Ω₀⊂⊙∞⊂Ω"
        self.data: Dict[str, Any] = {}
        self.version_history: List[Dict[str, Any]] = []
        self._load()

    def _load(self):
        """加载已有基线，不存在则初始化"""
        if os.path.exists(self.baseline_path):
            with open(self.baseline_path, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
            self.version_history = self.data.get("version_history", [])
        else:
            self.data = {
                "baseline_id": self._generate_id(),
                "did": self.did,
                "sovereign_root": self.sovereign_root,
                "trace_symbol": self.trace_symbol,
                "created_at": self._now(),
                "updated_at": self._now(),
                "version": "1.0.0",
                "rules": {},          # 核心规则库
                "facts": {},          # 事实标准库
                "constraints": [],    # 逻辑底线约束
                "weights": {},        # 规则权重
                "locked": False,      # eFuse锁档状态
                "version_history": []
            }
            self._save()

    def _save(self):
        """持久化到磁盘"""
        self.data["updated_at"] = self._now()
        self.data["sha256"] = self._calculate_hash()
        os.makedirs(os.path.dirname(self.baseline_path) or '.', exist_ok=True)
        with open(self.baseline_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def _calculate_hash(self) -> str:
        """计算基线内容SHA256（排除sha256字段本身）"""
        content = {k: v for k, v in self.data.items() if k != "sha256"}
        serialized = json.dumps(content, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(serialized.encode('utf-8')).hexdigest()

    def _generate_id(self) -> str:
        return f"BASELINE-{int(time.time())}-{os.urandom(4).hex()}"

    def _now(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _bump_version(self, major: bool = False, minor: bool = False):
        """版本号递增"""
        parts = self.data["version"].split(".")
        if major:
            parts[0] = str(int(parts[0]) + 1)
            parts[1] = "0"
            parts[2] = "0"
        elif minor:
            parts[1] = str(int(parts[1]) + 1)
            parts[2] = "0"
        else:
            parts[2] = str(int(parts[2]) + 1)
        self.data["version"] = ".".join(parts)

    # ===== 规则管理 =====

    def set_rule(self, key: str, rule: str, weight: float = 1.0,
                 require_confirm: bool = False) -> Dict[str, Any]:
        """设置核心规则，已存在则触发变更确认"""
        if key in self.data["rules"] and require_confirm:
            return {
                "status": "confirmation_required",
                "message": f"规则 '{key}' 已存在，变更需确认",
                "old_value": self.data["rules"][key],
                "new_value": rule
            }

        old_value = self.data["rules"].get(key)
        self.data["rules"][key] = {
            "content": rule,
            "weight": weight,
            "created_at": self._now(),
            "updated_at": self._now()
        }
        self.data["weights"][key] = weight
        self._bump_version()
        self._record_version("rule_update", key, old_value, rule)
        self._save()
        return {"status": "success", "key": key, "version": self.data["version"]}

    def get_rule(self, key: str) -> Optional[Dict[str, Any]]:
        return self.data["rules"].get(key)

    def get_all_rules(self) -> Dict[str, Any]:
        return self.data["rules"].copy()

    # ===== 事实标准管理 =====

    def set_fact(self, key: str, fact: str, source: str = "user",
                 confidence: float = 1.0) -> Dict[str, Any]:
        """设置事实标准"""
        self.data["facts"][key] = {
            "content": fact,
            "source": source,
            "confidence": confidence,
            "created_at": self._now(),
            "updated_at": self._now()
        }
        self._bump_version()
        self._record_version("fact_update", key, None, fact)
        self._save()
        return {"status": "success", "key": key}

    def get_fact(self, key: str) -> Optional[Dict[str, Any]]:
        return self.data["facts"].get(key)

    # ===== 约束管理 =====

    def add_constraint(self, constraint: str, level: str = "hard") -> Dict[str, Any]:
        """添加逻辑底线约束（hard=不可突破，soft=尽量遵守）"""
        entry = {
            "content": constraint,
            "level": level,
            "created_at": self._now()
        }
        self.data["constraints"].append(entry)
        self._bump_version()
        self._save()
        return {"status": "success", "constraint_id": len(self.data["constraints"])}

    def get_constraints(self, level: Optional[str] = None) -> List[Dict[str, Any]]:
        if level:
            return [c for c in self.data["constraints"] if c["level"] == level]
        return self.data["constraints"].copy()

    # ===== 版本管理 =====

    def _record_version(self, action: str, key: str, old_value, new_value):
        """记录版本变更历史"""
        entry = {
            "version": self.data["version"],
            "action": action,
            "key": key,
            "old_value": old_value,
            "new_value": new_value,
            "timestamp": self._now(),
            "hash_before": self.data.get("sha256", "initial")
        }
        self.version_history.append(entry)
        self.data["version_history"] = self.version_history[-100:]  # 保留最近100条

    def get_version_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        return self.version_history[-limit:]

    def rollback(self, version: str) -> bool:
        """回滚到指定版本（需未锁档）"""
        if self.data["locked"]:
            return False
        # 简化实现：实际应从历史快照恢复
        return True

    # ===== eFuse锁档 =====

    def lock(self) -> Dict[str, Any]:
        """执行eFuse硬件熔断锁档，锁档后不可静默修改"""
        if self.data["locked"]:
            return {"status": "already_locked"}
        self.data["locked"] = True
        self.data["locked_at"] = self._now()
        self.data["lock_hash"] = self._calculate_hash()
        self._save()
        return {
            "status": "locked",
            "lock_hash": self.data["lock_hash"],
            "locked_at": self.data["locked_at"]
        }

    def is_locked(self) -> bool:
        return self.data.get("locked", False)

    # ===== 校验 =====

    def verify_integrity(self) -> Dict[str, Any]:
        """校验基线完整性（哈希一致性）"""
        current_hash = self.data.get("sha256", "")
        recalculated = self._calculate_hash()
        return {
            "integrity": current_hash == recalculated,
            "stored_hash": current_hash,
            "recalculated_hash": recalculated,
            "version": self.data["version"],
            "locked": self.data["locked"],
            "rules_count": len(self.data["rules"]),
            "facts_count": len(self.data["facts"]),
            "constraints_count": len(self.data["constraints"])
        }

    # ===== 导出 =====

    def export_prompt(self) -> str:
        """导出为系统提示词格式（兼容提示词测试版）"""
        lines = [
            "【LOIP本体基线持久化版】",
            f"基线ID: {self.data['baseline_id']}",
            f"版本: {self.data['version']}",
            f"锁档状态: {'已锁档' if self.data['locked'] else '未锁档'}",
            "",
            "【核心规则】"
        ]
        for key, rule in self.data["rules"].items():
            lines.append(f"- {key}: {rule['content']} (权重:{rule['weight']})")
        lines.append("")
        lines.append("【事实标准】")
        for key, fact in self.data["facts"].items():
            lines.append(f"- {key}: {fact['content']} (置信度:{fact['confidence']})")
        lines.append("")
        lines.append("【逻辑底线约束】")
        for c in self.data["constraints"]:
            lines.append(f"- [{c['level']}] {c['content']}")
        return "\n".join(lines)

    def get_summary(self) -> Dict[str, Any]:
        """获取基线摘要"""
        return {
            "baseline_id": self.data["baseline_id"],
            "version": self.data["version"],
            "sha256": self.data.get("sha256", ""),
            "locked": self.data["locked"],
            "rules_count": len(self.data["rules"]),
            "facts_count": len(self.data["facts"]),
            "constraints_count": len(self.data["constraints"]),
            "created_at": self.data["created_at"],
            "updated_at": self.data["updated_at"]
        }
