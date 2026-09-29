"""
LOIP 主SDK接口
整合本体基线、漂移检测、幻觉抑制、双闭环审计，提供统一的中间件调用入口。
使用方式：
    from loip import LOIP
    loip = LOIP(baseline_path="./my_baseline.json", audit_dir="./audit_logs")
    loip.set_rule("风格", "始终使用正式商务语气")
    result = loip.process(user_input, ai_output)
    if result["needs_correction"]:
        ai_output = result["corrected_output"]
"""
import os
from typing import Any, Callable, Dict, Optional

from .baseline import OntologyBaseline
from .drift import DriftDetector
from .hallucination import HallucinationGuard
from .audit import DualAuditSystem
from .security_guard import SecurityGuard


class LOIP:
    """LOIP逻辑本体智能协议 · 主SDK接口"""

    VERSION = "0.1.0-MVP"

    def __init__(self, baseline_path: str, audit_dir: str = "./loip_audit",
                 did: str = "DID-BR-000002", sovereign_root: str = "Ω-TAN-7-001",
                 auto_audit: bool = True, backend: str = "auto"):
        """
        初始化LOIP内核
        :param baseline_path: 本体基线持久化文件路径
        :param audit_dir: 审计日志存储目录
        :param did: 去中心化身份标识
        :param sovereign_root: 本体主权根
        :param auto_audit: 是否自动记录审计日志
        :param backend: 检测后端 "auto"/"keyword"/"semantic"
        """
        self.baseline = OntologyBaseline(baseline_path, did, sovereign_root)
        self.drift_detector = DriftDetector(self.baseline, backend=backend)
        self.hallucination_guard = HallucinationGuard(self.baseline, backend=backend)
        self.security_guard = SecurityGuard(self.baseline)
        self.audit = DualAuditSystem(audit_dir, self.baseline.data["baseline_id"])
        self.llm_adapter = None  # v0.4: 模型适配器，set_llm()后启用
        self.auto_audit = auto_audit
        self.processing_count = 0
        self.backend = backend

        if self.auto_audit:
            self.audit.log_behavior(
                action="loip_init",
                details={"version": self.VERSION, "baseline_path": baseline_path},
                actor="system"
            )

    # ===== 基线管理快捷方法 =====

    def set_rule(self, key: str, rule: str, weight: float = 1.0) -> Dict[str, Any]:
        """设置核心规则"""
        result = self.baseline.set_rule(key, rule, weight, require_confirm=True)
        if self.auto_audit and result["status"] == "success":
            self.audit.log_baseline_change("rule_set", key, None, rule, authorized=True)
        return result

    def set_fact(self, key: str, fact: str, confidence: float = 1.0) -> Dict[str, Any]:
        """设置事实标准"""
        result = self.baseline.set_fact(key, fact, confidence=confidence)
        if self.auto_audit:
            self.audit.log_baseline_change("fact_set", key, None, fact, authorized=True)
        return result

    def add_constraint(self, constraint: str, level: str = "hard") -> Dict[str, Any]:
        """添加逻辑底线约束"""
        result = self.baseline.add_constraint(constraint, level)
        if self.auto_audit:
            self.audit.log_baseline_change("constraint_add", constraint, None, constraint, authorized=True)
        return result

    def lock(self) -> Dict[str, Any]:
        """执行eFuse锁档"""
        result = self.baseline.lock()
        if self.auto_audit:
            self.audit.log_behavior("efuse_lock", result, actor="system", risk_level="high")
        return result

    # ===== 核心处理流程 =====

    def process(self, user_input: str, ai_output: str,
                context: Optional[str] = None) -> Dict[str, Any]:
        """
        核心处理流水线：漂移检测 → 幻觉抑制 → 审计记录 → 修正建议
        :return: 处理结果，包含检测结果、修正建议、是否需要修正
        """
        self.processing_count += 1

        # 1. 认知漂移检测
        drift_result = self.drift_detector.check(user_input, ai_output)

        # 2. 幻觉抑制检测
        hallucination_result = self.hallucination_guard.check(ai_output, context)

        # 2.5 安全护栏检测（v0.3新增）
        security_result = self.security_guard.check(user_input, ai_output)

        # 3. 自动修正（生成修正后输出）
        corrected_output = self._auto_correct(ai_output, drift_result, hallucination_result, security_result)
        needs_correction = corrected_output != ai_output

        # 4. 审计记录
        if self.auto_audit:
            self.audit.log_output(ai_output)
            if drift_result["drift_detected"]:
                for c in drift_result["conflicts"]:
                    self.audit.log_drift_calibration(
                        c["type"], ai_output, corrected_output, drift_result["drift_level"]
                    )
            if hallucination_result["issue_count"] > 0:
                for issue in hallucination_result["issues"]:
                    self.audit.log_hallucination_intercept(
                        issue["type"], issue.get("claim", ""), hallucination_result["hallucination_risk"]
                    )

        # 5. 综合评估
        overall = self._assess_overall(drift_result, hallucination_result, security_result)

        return {
            "needs_correction": needs_correction,
            "blocked": security_result.get("blocked", False),
            "original_output": ai_output,
            "corrected_output": corrected_output,
            "drift_detection": drift_result,
            "hallucination_guard": hallucination_result,
            "security_guard": {
                "injection_detected": security_result.get("injection_detected", False),
                "threat_count": security_result.get("threat_count", 0),
                "compliance_issues": len(security_result.get("compliance_issues", [])),
                "risk_level": security_result.get("risk_level", "low")
            },
            "overall_risk": overall["risk"],
            "overall_score": overall["score"],
            "corrections_applied": overall["corrections"],
            "processing_id": f"PROC-{self.processing_count:06d}"
        }

    def _auto_correct(self, output: str, drift_result: Dict,
                      hallucination_result: Dict, security_result: Optional[Dict] = None) -> str:
        """自动修正输出（标注式修正 + 安全脱敏 + 阻断）"""
        # 安全护栏优先：如果被阻断，直接返回安全输出
        if security_result and security_result.get("blocked"):
            return security_result["safe_output"]

        corrected = output
        corrections = []

        # 安全脱敏（v0.3新增）
        if security_result and security_result.get("threat_count", 0) > 0:
            corrected = security_result["safe_output"].split("\n\n--- LOIP安全护栏")[0]
            corrections.append(f"【安全护栏】检测到 {security_result['threat_count']} 项安全风险，已自动脱敏")

        # 漂移修正：添加校准标记
        if drift_result["drift_detected"]:
            for corr in drift_result["corrections"]:
                corrections.append(f"【漂移校准】{corr['suggestion']}")

        # 幻觉修正：为无依据断言添加待核实标注
        if hallucination_result["hallucination_risk"] in ["high", "medium"]:
            corrected = self.hallucination_guard.annotate_uncertainty(corrected)
            for sug in hallucination_result["suggestions"]:
                if "待核实" in sug:
                    corrections.append(f"【幻觉抑制】{sug}")

        # 附加修正说明
        if corrections:
            correction_note = "\n\n--- LOIP稳态校准 ---\n" + "\n".join(corrections)
            corrected = corrected + correction_note

        return corrected

    def _assess_overall(self, drift_result: Dict, hallucination_result: Dict,
                        security_result: Optional[Dict] = None) -> Dict[str, Any]:
        """综合风险评估（含安全护栏）"""
        drift_score = drift_result["drift_level"]
        hallu_risk_map = {"low": 0.2, "medium": 0.5, "high": 0.8}
        hallu_score = hallu_risk_map.get(hallucination_result["hallucination_risk"], 0.3)

        # 安全风险（v0.3新增）
        security_score = 0.0
        if security_result:
            sec_risk_map = {"low": 0.2, "medium": 0.5, "high": 0.8, "critical": 1.0}
            security_score = sec_risk_map.get(security_result.get("risk_level", "low"), 0.3)

        overall_score = max(drift_score, hallu_score, security_score)
        corrections = (drift_result["conflict_count"]
                       + hallucination_result["issue_count"]
                       + (security_result.get("threat_count", 0) if security_result else 0))

        if overall_score >= 0.9:
            risk = "critical"
        elif overall_score >= 0.7:
            risk = "high"
        elif overall_score >= 0.4:
            risk = "medium"
        else:
            risk = "low"

        return {"risk": risk, "score": round(overall_score, 3), "corrections": corrections}

    # ===== 中间件装饰器 =====

    def middleware(self, llm_func: Callable) -> Callable:
        """
        中间件装饰器：包裹大模型调用函数，自动注入LOIP稳态治理
        使用方式：
            @loip.middleware
            def call_llm(prompt):
                return openai.ChatCompletion.create(...)
        """
        def wrapper(user_input: str, *args, **kwargs):
            # 调用原始大模型
            raw_output = llm_func(user_input, *args, **kwargs)
            # 经过LOIP治理
            result = self.process(user_input, raw_output)
            return result["corrected_output"], result
        return wrapper

    # ===== 状态与报告 =====

    def get_status(self) -> Dict[str, Any]:
        """获取LOIP内核运行状态"""
        return {
            "loip_version": self.VERSION,
            "baseline": self.baseline.get_summary(),
            "drift_stats": self.drift_detector.get_drift_stats(),
            "hallucination_stats": self.hallucination_guard.get_stats(),
            "security_stats": self.security_guard.get_stats(),
            "audit_summary": self.audit.get_summary(),
            "processing_count": self.processing_count
        }

    def set_security_values(self, values: list) -> Dict[str, Any]:
        """设置企业价值观基线（固化后不可被Prompt注入篡改）"""
        return self.security_guard.set_values(values)

    def generate_audit_report(self, output_path: Optional[str] = None) -> str:
        """生成审计报告"""
        return self.audit.export_report(output_path)

    def verify_integrity(self) -> Dict[str, Any]:
        """全链路完整性校验"""
        return {
            "baseline_integrity": self.baseline.verify_integrity(),
            "audit_hash_chain": self.audit.verify_hash_chain()
        }

    def export_baseline_prompt(self) -> str:
        """导出基线为系统提示词（兼容提示词测试版）"""
        return self.baseline.export_prompt()

    # ===== v0.4: 多模型适配 + 一键调用 =====

    def set_llm(self, config: dict):
        """
        配置大模型适配器（v0.4新增）
        配置格式：
            {"preset": "doubao-pro", "api_key": "xxx"}
            {"adapter": "openai", "api_key": "xxx", "model": "gpt-4o", "base_url": "..."}
        """
        from .adapters import create_adapter
        self.llm_adapter = create_adapter(config)
        return {"status": "llm_configured", "model": self.llm_adapter.model,
                "adapter": type(self.llm_adapter).__name__}

    def chat(self, user_input: str, system_prompt: Optional[str] = None,
             auto_correct: bool = True, **kwargs) -> Dict[str, Any]:
        """
        一键调用：大模型生成 + LOIP稳态治理（v0.4核心方法）
        使用前需先调用 set_llm() 配置模型。

        :param user_input: 用户输入
        :param system_prompt: 系统提示词（可选，默认使用基线导出的提示词）
        :param auto_correct: 是否自动应用修正输出
        :return: {raw_output, corrected_output, governance, llm_info}
        """
        if not self.llm_adapter:
            return {"error": "未配置大模型，请先调用 set_llm()",
                    "help": "loip.set_llm({'preset': 'doubao-pro', 'api_key': 'xxx'})"}

        # 使用基线导出的系统提示词（如果未指定）
        if system_prompt is None:
            system_prompt = self.export_baseline_prompt()

        # 调用大模型
        llm_resp = self.llm_adapter.simple_chat(user_input, system_prompt, **kwargs)

        if not llm_resp.success:
            return {"error": f"大模型调用失败: {llm_resp.error}", "llm_info": llm_resp.model}

        # LOIP稳态治理
        governance = self.process(user_input, llm_resp.content)

        return {
            "raw_output": llm_resp.content,
            "corrected_output": governance["corrected_output"] if auto_correct else llm_resp.content,
            "governance": {
                "blocked": governance["blocked"],
                "overall_risk": governance["overall_risk"],
                "overall_score": governance["overall_score"],
                "drift_conflicts": governance["drift_detection"]["conflict_count"],
                "hallucination_issues": governance["hallucination_guard"]["issue_count"],
                "security_threats": governance["security_guard"]["threat_count"],
                "corrections_applied": governance["corrections_applied"]
            },
            "llm_info": {
                "model": llm_resp.model,
                "usage": llm_resp.usage
            },
            "processing_id": governance["processing_id"]
        }

    @classmethod
    def from_config(cls, config_path: str, baseline_path: Optional[str] = None) -> "LOIP":
        """
        从配置文件一键创建LOIP实例（v0.4新增）
        配置文件JSON格式：
        {
          "baseline_path": "./baseline.json",
          "audit_dir": "./audit",
          "llm": {"preset": "doubao-pro", "api_key": "xxx"},
          "backend": "keyword"
        }
        """
        import json as _json
        with open(config_path, 'r', encoding='utf-8') as f:
            config = _json.load(f)

        bp = baseline_path or config.get("baseline_path", "./loip_baseline.json")
        instance = cls(
            baseline_path=bp,
            audit_dir=config.get("audit_dir", "./loip_audit"),
            backend=config.get("backend", "auto")
        )
        if "llm" in config:
            instance.set_llm(config["llm"])
        return instance
