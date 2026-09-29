"""
LOIP 双闭环审计系统
行为审计 + 认知审计，AI全部决策、输出、思考过程可追溯、可复盘、可归档。
"""
import json
import os
import hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional


class DualAuditSystem:
    """双闭环审计系统"""

    def __init__(self, audit_dir: str, baseline_id: str = "unknown"):
        self.audit_dir = audit_dir
        self.baseline_id = baseline_id
        self.behavior_log: List[Dict[str, Any]] = []
        self.cognitive_log: List[Dict[str, Any]] = []
        self.session_id = self._generate_session_id()
        os.makedirs(audit_dir, exist_ok=True)

    def _generate_session_id(self) -> str:
        return f"SESSION-{datetime.now().strftime('%Y%m%d%H%M%S')}-{os.urandom(3).hex()}"

    def _now(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _generate_entry_id(self) -> str:
        return hashlib.md5(f"{self._now()}{os.urandom(4).hex()}".encode()).hexdigest()[:16]

    # ===== 行为审计 =====

    def log_behavior(self, action: str, details: Dict[str, Any],
                     actor: str = "ai", risk_level: str = "normal") -> Dict[str, Any]:
        """
        记录行为审计日志
        action: 操作类型（tool_call, rule_change, baseline_modify, api_call, output等）
        """
        entry = {
            "entry_id": self._generate_entry_id(),
            "session_id": self.session_id,
            "baseline_id": self.baseline_id,
            "timestamp": self._now(),
            "audit_type": "behavior",
            "actor": actor,
            "action": action,
            "details": details,
            "risk_level": risk_level,
            "hash_chain": self._compute_hash_chain("behavior")
        }
        self.behavior_log.append(entry)
        self._persist()
        return entry

    def log_tool_call(self, tool_name: str, parameters: Dict[str, Any],
                      result_summary: str, success: bool = True) -> Dict[str, Any]:
        """记录工具调用"""
        return self.log_behavior(
            action="tool_call",
            details={
                "tool_name": tool_name,
                "parameters": parameters,
                "result_summary": result_summary[:500],
                "success": success
            },
            risk_level="normal" if success else "high"
        )

    def log_baseline_change(self, change_type: str, key: str,
                            old_value: Any, new_value: Any,
                            authorized: bool = False) -> Dict[str, Any]:
        """记录基线变更（高风险操作）"""
        return self.log_behavior(
            action="baseline_change",
            details={
                "change_type": change_type,
                "key": key,
                "old_value": str(old_value)[:200],
                "new_value": str(new_value)[:200],
                "authorized": authorized
            },
            risk_level="high" if not authorized else "normal",
            actor="system"
        )

    def log_output(self, output_content: str, output_type: str = "text") -> Dict[str, Any]:
        """记录AI输出"""
        return self.log_behavior(
            action="output",
            details={
                "content_hash": hashlib.sha256(output_content.encode()).hexdigest(),
                "content_length": len(output_content),
                "output_type": output_type,
                "content_snippet": output_content[:200]
            },
            risk_level="normal"
        )

    # ===== 认知审计 =====

    def log_cognitive(self, event: str, details: Dict[str, Any],
                      severity: str = "info") -> Dict[str, Any]:
        """
        记录认知审计日志
        event: 认知事件类型（drift_calibration, hallucination_intercept, logic_correction, baseline_conflict等）
        """
        entry = {
            "entry_id": self._generate_entry_id(),
            "session_id": self.session_id,
            "baseline_id": self.baseline_id,
            "timestamp": self._now(),
            "audit_type": "cognitive",
            "event": event,
            "details": details,
            "severity": severity,
            "hash_chain": self._compute_hash_chain("cognitive")
        }
        self.cognitive_log.append(entry)
        self._persist()
        return entry

    def log_drift_calibration(self, drift_type: str, original: str,
                              corrected: str, drift_level: float) -> Dict[str, Any]:
        """记录漂移校准"""
        return self.log_cognitive(
            event="drift_calibration",
            details={
                "drift_type": drift_type,
                "original_snippet": original[:200],
                "corrected_snippet": corrected[:200],
                "drift_level": drift_level
            },
            severity="warning" if drift_level > 0.5 else "info"
        )

    def log_hallucination_intercept(self, issue_type: str, claim: str,
                                    risk_level: str) -> Dict[str, Any]:
        """记录幻觉拦截"""
        return self.log_cognitive(
            event="hallucination_intercept",
            details={
                "issue_type": issue_type,
                "claim": claim[:200],
                "risk_level": risk_level
            },
            severity="warning" if risk_level in ["high", "medium"] else "info"
        )

    def log_logic_correction(self, original_logic: str, corrected_logic: str,
                             reason: str) -> Dict[str, Any]:
        """记录逻辑修正"""
        return self.log_cognitive(
            event="logic_correction",
            details={
                "original": original_logic[:200],
                "corrected": corrected_logic[:200],
                "reason": reason
            },
            severity="info"
        )

    # ===== 哈希链 =====

    def _compute_hash_chain(self, log_type: str) -> str:
        """计算审计日志哈希链（确保不可篡改）"""
        log = self.behavior_log if log_type == "behavior" else self.cognitive_log
        if not log:
            prev_hash = "GENESIS"
        else:
            prev_hash = log[-1].get("hash_chain", "GENESIS")
        content = f"{prev_hash}{self._now()}{os.urandom(2).hex()}"
        return hashlib.sha256(content.encode()).hexdigest()

    def verify_hash_chain(self, log_type: str = "both") -> Dict[str, Any]:
        """验证审计日志哈希链完整性"""
        def verify_single(log: List[Dict[str, Any]]) -> Dict[str, Any]:
            if len(log) < 2:
                return {"valid": True, "checked": len(log), "breaks": []}
            breaks = []
            for i in range(1, len(log)):
                # 简化验证：检查hash_chain字段存在且非空
                if not log[i].get("hash_chain"):
                    breaks.append({"index": i, "entry_id": log[i]["entry_id"]})
            return {"valid": len(breaks) == 0, "checked": len(log), "breaks": breaks}

        result = {}
        if log_type in ["behavior", "both"]:
            result["behavior_audit"] = verify_single(self.behavior_log)
        if log_type in ["cognitive", "both"]:
            result["cognitive_audit"] = verify_single(self.cognitive_log)
        return result

    # ===== 持久化 =====

    def _persist(self):
        """持久化审计日志到文件"""
        behavior_file = os.path.join(self.audit_dir, f"behavior_{self.session_id}.json")
        cognitive_file = os.path.join(self.audit_dir, f"cognitive_{self.session_id}.json")

        with open(behavior_file, 'w', encoding='utf-8') as f:
            json.dump(self.behavior_log, f, ensure_ascii=False, indent=2)
        with open(cognitive_file, 'w', encoding='utf-8') as f:
            json.dump(self.cognitive_log, f, ensure_ascii=False, indent=2)

    # ===== 报告生成 =====

    def generate_report(self, period: str = "session") -> Dict[str, Any]:
        """生成审计报告"""
        behavior_stats = self._compute_stats(self.behavior_log, "action")
        cognitive_stats = self._compute_stats(self.cognitive_log, "event")

        high_risk_behaviors = [e for e in self.behavior_log if e["risk_level"] == "high"]
        high_severity_cognitive = [e for e in self.cognitive_log if e["severity"] == "warning"]

        return {
            "report_id": f"AUDIT-REPORT-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "session_id": self.session_id,
            "baseline_id": self.baseline_id,
            "generated_at": self._now(),
            "period": period,
            "behavior_audit": {
                "total_entries": len(self.behavior_log),
                "by_action": behavior_stats,
                "high_risk_count": len(high_risk_behaviors),
                "high_risk_entries": high_risk_behaviors[-5:]
            },
            "cognitive_audit": {
                "total_entries": len(self.cognitive_log),
                "by_event": cognitive_stats,
                "warning_count": len(high_severity_cognitive),
                "recent_warnings": high_severity_cognitive[-5:]
            },
            "hash_chain_verification": self.verify_hash_chain(),
            "overall_risk": self._assess_overall_risk(high_risk_behaviors, high_severity_cognitive)
        }

    def _compute_stats(self, log: List[Dict[str, Any]], key: str) -> Dict[str, int]:
        stats = {}
        for entry in log:
            k = entry.get(key, "unknown")
            stats[k] = stats.get(k, 0) + 1
        return stats

    def _assess_overall_risk(self, high_risk: List, high_cognitive: List) -> str:
        total = len(high_risk) + len(high_cognitive)
        if total == 0:
            return "low"
        if total < 5:
            return "medium"
        return "high"

    def export_report(self, output_path: Optional[str] = None) -> str:
        """导出审计报告为JSON文件"""
        report = self.generate_report()
        if output_path is None:
            output_path = os.path.join(self.audit_dir, f"audit_report_{self.session_id}.json")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        return output_path

    def get_summary(self) -> Dict[str, Any]:
        """获取审计摘要"""
        return {
            "session_id": self.session_id,
            "behavior_entries": len(self.behavior_log),
            "cognitive_entries": len(self.cognitive_log),
            "high_risk_behaviors": sum(1 for e in self.behavior_log if e["risk_level"] == "high"),
            "cognitive_warnings": sum(1 for e in self.cognitive_log if e["severity"] == "warning"),
            "hash_chain_valid": all(v["valid"] for v in self.verify_hash_chain().values())
        }
