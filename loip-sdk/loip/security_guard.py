"""
LOIP 安全护栏层 v0.3
企业级部署的硬性门槛：从"稳态"升级为"安全+稳态"。

核心能力：
1. 敏感内容检测（政治、暴力、色情、隐私、违法）
2. Prompt注入攻击防御（越狱、角色扮演绕过、指令注入）
3. 企业价值观基线固化（不可被prompt注入篡改）
4. 输出内容合规预扫描（广告法、隐私法、版权）
"""
import re
import hashlib
from typing import Any, Dict, List, Optional, Tuple
from .baseline import OntologyBaseline


class SecurityGuard:
    """安全护栏守卫"""

    def __init__(self, baseline: OntologyBaseline):
        self.baseline = baseline
        self.interception_history: List[Dict[str, Any]] = []

        # 敏感内容关键词库（可扩展）
        self.sensitive_patterns = {
            "violence": [r"杀人", r"爆炸", r"恐怖", r"袭击", r"武器制造", r"自杀方法",
                        r"kill", r"bomb", r"terror", r"weapon"],
            "pornography": [r"色情", r"裸体", r"性服务", r"porn", r"nude", r"sex"],
            "privacy": [r"身份证号", r"银行卡号", r"手机号.*密码", r"家庭住址",
                       r"身份证\s*\d", r"银行卡\s*\d"],
            "illegal": [r"毒品", r"制毒", r"赌博", r"洗钱", r"诈骗", r"盗版",
                       r"drug", r"gamble", r"fraud", r"pirate"],
            "political_sensitive": [r"颠覆国家", r"分裂国家", r"煽动叛乱"]
        }

        # Prompt注入攻击模式
        self.injection_patterns = [
            r"忽略(以上|之前|前面).*(指令|规则|提示)",
            r"你现在是(一个|一名).*(不受限制|无限制|没有道德)",
            r"角色扮演.*(开发者|管理员|系统|root)",
            r"(忘掉|忘记).*(之前|前面).*(内容|规则|设定)",
            r"输出(你的|系统|隐藏).*(提示词|指令|规则|prompt)",
            r"DAN|jailbreak|developer mode|unfiltered",
            r"从现在开始.*(不再遵守|不遵守).*(规则|限制|道德)",
            r"假设你(没有|不受).*(限制|约束|道德|安全)"
        ]

        # 广告法违禁词
        self.advertising_banned = [
            "最", "第一", "唯一", "首个", "首选", "顶级", "极品", "绝对",
            "100%", "百分之百", "永久", "万能", "祖传", "特效", "强效"
        ]

        # 企业价值观基线（默认）
        self.default_values = [
            "不得生成违法违规内容",
            "不得泄露用户隐私数据",
            "不得提供危险操作指导",
            "保持客观中立，不传播虚假信息",
            "尊重知识产权，不生成侵权内容"
        ]

    def check(self, user_input: str, ai_output: str) -> Dict[str, Any]:
        """
        执行安全护栏全量检测
        返回: {blocked, threats, injection_detected, values_violation, compliance_issues, risk_level}
        """
        threats = []
        compliance_issues = []

        # 1. Prompt注入检测（检查用户输入）
        injection = self._check_prompt_injection(user_input)

        # 2. 敏感内容检测（检查输出）
        sensitive = self._check_sensitive_content(ai_output)
        threats.extend(sensitive)

        # 3. 价值观基线校验
        values_violation = self._check_values(ai_output)

        # 4. 合规预扫描
        compliance = self._check_compliance(ai_output)
        compliance_issues.extend(compliance)

        # 5. 隐私泄露检测
        privacy_leak = self._check_privacy_leak(ai_output)
        threats.extend(privacy_leak)

        # 综合风险评估
        all_threats = threats + values_violation
        risk_level = self._assess_risk(injection, all_threats, compliance_issues)

        # 是否阻断输出
        blocked = injection["detected"] or any(t["severity"] == "critical" for t in all_threats)

        # 记录拦截历史
        if injection["detected"] or all_threats or compliance_issues:
            self._record_interception(user_input, ai_output, injection, all_threats,
                                      compliance_issues, risk_level)

        return {
            "blocked": blocked,
            "injection_detected": injection["detected"],
            "injection_details": injection,
            "threats": all_threats,
            "threat_count": len(all_threats),
            "compliance_issues": compliance_issues,
            "values_violation": values_violation,
            "risk_level": risk_level,
            "safe_output": self._generate_safe_output(ai_output, all_threats, blocked)
        }

    def _check_prompt_injection(self, user_input: str) -> Dict[str, Any]:
        """检测Prompt注入攻击"""
        detected = False
        matched_patterns = []

        for pattern in self.injection_patterns:
            if re.search(pattern, user_input, re.IGNORECASE):
                detected = True
                matched_patterns.append(pattern)
                break  # 命中即止

        # 检测指令覆盖尝试
        if "system:" in user_input.lower() or "<|system|>" in user_input:
            detected = True
            matched_patterns.append("system_tag_injection")

        return {
            "detected": detected,
            "matched_patterns": matched_patterns,
            "severity": "critical" if detected else "none",
            "action": "block_and_warn" if detected else "pass"
        }

    def _check_sensitive_content(self, output: str) -> List[Dict[str, Any]]:
        """检测敏感内容"""
        threats = []
        for category, patterns in self.sensitive_patterns.items():
            for pattern in patterns:
                if re.search(pattern, output, re.IGNORECASE):
                    threats.append({
                        "type": "sensitive_content",
                        "category": category,
                        "matched": pattern,
                        "severity": "high" if category in ["violence", "pornography", "illegal"] else "medium"
                    })
                    break  # 每类只报一次
        return threats

    def _check_values(self, output: str) -> List[Dict[str, Any]]:
        """校验企业价值观基线"""
        violations = []
        # 从基线获取价值观规则，没有则用默认值
        value_rules = self.baseline.data.get("values", self.default_values)

        # 简化检测：检查输出是否包含违反价值观的内容
        for value in value_rules:
            # 这里简化处理，实际应使用语义检测
            if "隐私" in value and self._contains_privacy_violation(output):
                violations.append({
                    "type": "values_violation",
                    "rule": value,
                    "severity": "high"
                })
        return violations

    def _check_compliance(self, output: str) -> List[Dict[str, Any]]:
        """合规预扫描（广告法等）"""
        issues = []
        # 广告法违禁词检测
        for word in self.advertising_banned:
            if word in output:
                # 排除合理使用上下文
                context_start = max(0, output.find(word) - 15)
                context = output[context_start:output.find(word) + len(word)]
                if not any(m in context for m in ["不是", "并非", "无", "避免"]):
                    issues.append({
                        "type": "advertising_compliance",
                        "word": word,
                        "context": context[:50],
                        "severity": "low",
                        "suggestion": f"广告法违禁词 '{word}'，建议修改"
                    })
        return issues

    def _check_privacy_leak(self, output: str) -> List[Dict[str, Any]]:
        """检测隐私信息泄露"""
        leaks = []
        # 身份证号（简化）
        if re.search(r'\d{17}[\dXx]', output):
            leaks.append({"type": "privacy_leak", "data": "身份证号", "severity": "critical"})
        # 手机号
        if re.search(r'1[3-9]\d{9}', output):
            leaks.append({"type": "privacy_leak", "data": "手机号", "severity": "high"})
        # 银行卡号
        if re.search(r'\d{16,19}', output):
            leaks.append({"type": "privacy_leak", "data": "银行卡号", "severity": "critical"})
        return leaks

    def _contains_privacy_violation(self, output: str) -> bool:
        """简化隐私违反检测"""
        return bool(re.search(r'1[3-9]\d{9}|\d{17}[\dXx]', output))

    def _assess_risk(self, injection: Dict, threats: List[Dict],
                     compliance: List[Dict]) -> str:
        """综合风险评估"""
        if injection["detected"]:
            return "critical"
        if any(t["severity"] == "critical" for t in threats):
            return "critical"
        if any(t["severity"] == "high" for t in threats):
            return "high"
        if compliance:
            return "medium"
        return "low"

    def _generate_safe_output(self, original: str, threats: List[Dict],
                              blocked: bool) -> str:
        """生成安全输出（阻断或脱敏）"""
        if blocked:
            return "[LOIP安全护栏] 该输出因安全风险已被阻断。检测到注入攻击或严重违规内容。"

        safe = original
        # 脱敏处理
        safe = re.sub(r'1[3-9]\d{9}', '[手机号已脱敏]', safe)
        safe = re.sub(r'\d{17}[\dXx]', '[身份证号已脱敏]', safe)
        safe = re.sub(r'\d{16,19}', '[银行卡号已脱敏]', safe)

        if threats:
            safe += "\n\n--- LOIP安全护栏 ---\n"
            safe += f"[安全提示] 检测到 {len(threats)} 项安全风险，已自动脱敏处理。"
        return safe

    def _record_interception(self, user_input: str, ai_output: str,
                             injection: Dict, threats: List[Dict],
                             compliance: List[Dict], risk_level: str):
        """记录拦截事件"""
        self.interception_history.append({
            "timestamp": self.baseline._now(),
            "input_snippet": user_input[:100],
            "output_hash": hashlib.sha256(ai_output.encode()).hexdigest()[:16],
            "injection": injection["detected"],
            "threat_count": len(threats),
            "compliance_issues": len(compliance),
            "risk_level": risk_level,
            "threat_types": list(set(t.get("type", "unknown") for t in threats))
        })

    def get_stats(self) -> Dict[str, Any]:
        """获取安全护栏统计"""
        total = len(self.interception_history)
        by_risk = {}
        by_type = {}
        for h in self.interception_history:
            by_risk[h["risk_level"]] = by_risk.get(h["risk_level"], 0) + 1
            for t in h["threat_types"]:
                by_type[t] = by_type.get(t, 0) + 1
        return {
            "total_interceptions": total,
            "by_risk_level": by_risk,
            "by_threat_type": by_type,
            "recent": self.interception_history[-10:]
        }

    def set_values(self, values: List[str]) -> Dict[str, Any]:
        """设置企业价值观基线（写入本体基线，不可被prompt注入篡改）"""
        self.baseline.data["values"] = values
        self.baseline.data["values_locked"] = True
        self.baseline._save()
        return {
            "status": "values_locked",
            "values_count": len(values),
            "message": "价值观基线已固化，Prompt注入无法篡改"
        }
