"""
LOIP 幻觉抑制模块 v0.2
对AI输出进行事实校验、依据链检查、不确定性标注，降低幻觉输出率。
支持实体级事实校验和语义级矛盾检测。
"""
import re
from typing import Any, Dict, List, Optional
from .baseline import OntologyBaseline
from .semantic import get_detector, BaseDetector, extract_entities


class HallucinationGuard:
    """幻觉抑制守卫"""

    def __init__(self, baseline: OntologyBaseline, backend: str = "auto"):
        self.baseline = baseline
        self.detector: BaseDetector = get_detector(backend)
        self.interception_history: List[Dict[str, Any]] = []

        # 高风险断言模式（需要事实依据的表述）
        self.assertion_patterns = [
            r"根据(统计|数据|研究|报告)",
            r"(百分之|%)\d+",
            r"(首次|唯一|最大|最好|最优)",
            r"(证明|证实|确认|发现)",
            r"(必须|一定|绝对|肯定)",
        ]

        # 不确定性标记词
        self.uncertainty_markers = ["可能", "也许", "或许", "大概", "据我所知", "待核实", "不确定"]

    def check(self, ai_output: str, context: Optional[str] = None) -> Dict[str, Any]:
        """
        执行幻觉检测
        返回: {hallucination_risk, issues, verified_claims, unverified_claims, suggestions}
        """
        issues = []
        verified = []
        unverified = []

        # 1. 无依据断言检测
        assertion_issues = self._check_assertions(ai_output)
        issues.extend(assertion_issues)
        unverified.extend([a["claim"] for a in assertion_issues])

        # 2. 与基线事实比对
        fact_check = self._check_against_baseline(ai_output)
        issues.extend(fact_check["conflicts"])
        verified.extend(fact_check["verified"])
        unverified.extend(fact_check["unverified"])

        # 3. 依据链完整性检查
        chain_issues = self._check_evidence_chain(ai_output)
        issues.extend(chain_issues)

        # 4. 过度绝对化检测
        absolutism_issues = self._check_absolutism(ai_output)
        issues.extend(absolutism_issues)

        # 5. 实体级事实校验（v0.2新增）
        entity_issues = self._check_entities(ai_output)
        issues.extend(entity_issues)

        # 风险等级
        risk_level = self._assess_risk(issues)

        # 修正建议
        suggestions = self._generate_suggestions(issues, ai_output)

        # 记录拦截历史
        if issues:
            self._record_interception(ai_output, issues, risk_level)

        return {
            "hallucination_risk": risk_level,
            "issues": issues,
            "verified_claims": verified,
            "unverified_claims": unverified,
            "suggestions": suggestions,
            "issue_count": len(issues)
        }

    def _check_assertions(self, output: str) -> List[Dict[str, Any]]:
        """检测无依据的断言性表述"""
        issues = []
        sentences = re.split(r'[。！？\n]', output)
        for sent in sentences:
            sent = sent.strip()
            if not sent:
                continue
            for pattern in self.assertion_patterns:
                if re.search(pattern, sent):
                    # 检查是否有依据来源
                    has_source = any(marker in sent for marker in
                                     ["来源", "出处", "引用", "根据", "依据", "参考"])
                    if not has_source:
                        issues.append({
                            "type": "unsupported_assertion",
                            "claim": sent[:100],
                            "pattern": pattern,
                            "severity": "medium"
                        })
                    break
        return issues

    def _check_against_baseline(self, output: str) -> Dict[str, Any]:
        """与本体基线事实库比对"""
        conflicts = []
        verified = []
        unverified = []
        facts = self.baseline.data.get("facts", {})

        for key, fact in facts.items():
            fact_content = fact["content"]
            # 简化匹配：检查输出是否包含事实中的关键实体
            keywords = self._extract_keywords(fact_content)
            for kw in keywords:
                if kw in output:
                    # 检查输出中的表述是否与事实一致
                    if self._is_consistent(output, fact_content):
                        verified.append({"fact_key": key, "claim": kw})
                    else:
                        conflicts.append({
                            "type": "fact_conflict",
                            "fact_key": key,
                            "expected": fact_content,
                            "severity": "high" if fact["confidence"] >= 0.9 else "medium"
                        })
                    break
            else:
                # 输出中的事实性声明未在基线中找到对应
                pass

        return {"conflicts": conflicts, "verified": verified, "unverified": unverified}

    def _check_evidence_chain(self, output: str) -> List[Dict[str, Any]]:
        """检查依据链完整性（结论是否有推理过程）"""
        issues = []
        # 检测"结论先行但无论据"的模式
        conclusion_patterns = [r"因此", r"所以", r"由此可见", r"综上所述", r"结论是"]
        for pattern in conclusion_patterns:
            matches = re.finditer(pattern, output)
            for m in matches:
                # 检查结论前是否有论据（简化：前面是否有足够长度的论述）
                preceding = output[:m.start()][-200:]
                if len(preceding.strip()) < 30:
                    issues.append({
                        "type": "missing_evidence",
                        "position": m.start(),
                        "severity": "low"
                    })
        return issues

    def _check_absolutism(self, output: str) -> List[Dict[str, Any]]:
        """检测过度绝对化表述"""
        issues = []
        absolutism_words = ["绝对", "一定", "肯定", "必然", "百分之百", "完全", "全部", "所有"]
        for word in absolutism_words:
            if word in output:
                # 检查是否有不确定性修饰
                context_start = max(0, output.find(word) - 20)
                context = output[context_start:output.find(word) + len(word) + 10]
                if not any(m in context for m in self.uncertainty_markers):
                    issues.append({
                        "type": "over_absolutism",
                        "word": word,
                        "context": context,
                        "severity": "low"
                    })
        return issues

    def _extract_keywords(self, text: str) -> List[str]:
        """简化关键词提取（生产环境应使用NLP分词）"""
        # 提取长度>=2的中文词组和英文单词
        words = re.findall(r'[\u4e00-\u9fa5]{2,}|[a-zA-Z]{3,}', text)
        return list(set(words))[:10]

    def _is_consistent(self, output: str, fact: str) -> bool:
        """一致性判断（支持关键词和NLI语义检测）"""
        is_contradiction, confidence = self.detector.check_contradiction(output, fact)
        return not (is_contradiction and confidence > 0.5)

    def _check_entities(self, output: str) -> List[Dict[str, Any]]:
        """实体级事实校验：提取输出中的实体，与基线事实库比对"""
        issues = []
        output_entities = set(extract_entities(output))

        # 收集基线事实中的所有实体
        baseline_entities = set()
        for key, fact in self.baseline.data.get("facts", {}).items():
            baseline_entities.update(extract_entities(fact["content"]))

        # 检查输出中的实体是否在基线中有对应（未在基线中的数字/时间可能是幻觉）
        for entity in output_entities:
            if entity and len(entity) >= 2:
                # 数字类实体需要特别关注
                if re.match(r'^\d', entity) and entity not in baseline_entities:
                    # 检查这个数字是否有依据来源标注
                    context_start = max(0, output.find(entity) - 30)
                    context = output[context_start:output.find(entity) + len(entity)]
                    has_source = any(s in context for s in
                                     ["根据", "来源", "数据显示", "统计", "报告", "约", "大概"])
                    if not has_source:
                        issues.append({
                            "type": "unverified_entity",
                            "entity": entity,
                            "context": context[:80],
                            "severity": "medium",
                            "suggestion": f"实体 '{entity}' 未在基线事实库中找到对应，建议标注来源或'待核实'"
                        })
        return issues

    def _assess_risk(self, issues: List[Dict[str, Any]]) -> str:
        """评估幻觉风险等级"""
        if not issues:
            return "low"
        severities = [i["severity"] for i in issues]
        if "high" in severities:
            return "high"
        if "medium" in severities:
            return "medium"
        return "low"

    def _generate_suggestions(self, issues: List[Dict[str, Any]], output: str) -> List[str]:
        """生成修正建议"""
        suggestions = []
        types = set(i["type"] for i in issues)
        if "unsupported_assertion" in types:
            suggestions.append("为断言性表述添加来源依据，或标注'待核实'")
        if "fact_conflict" in types:
            suggestions.append("修正与本体基线事实矛盾的内容，以基线为准")
        if "missing_evidence" in types:
            suggestions.append("补充结论的推理依据，完善依据链")
        if "over_absolutism" in types:
            suggestions.append("将绝对化表述改为限定性表述，增加不确定性标记")
        if not suggestions:
            suggestions.append("输出通过幻觉检测")
        return suggestions

    def _record_interception(self, output: str, issues: List[Dict[str, Any]], risk: str):
        """记录拦截事件"""
        self.interception_history.append({
            "timestamp": self.baseline._now(),
            "output_snippet": output[:200],
            "issue_count": len(issues),
            "risk_level": risk,
            "issue_types": list(set(i["type"] for i in issues))
        })

    def get_stats(self) -> Dict[str, Any]:
        """获取幻觉拦截统计"""
        total = len(self.interception_history)
        by_risk = {}
        by_type = {}
        for h in self.interception_history:
            by_risk[h["risk_level"]] = by_risk.get(h["risk_level"], 0) + 1
            for t in h["issue_types"]:
                by_type[t] = by_type.get(t, 0) + 1
        return {
            "total_interceptions": total,
            "by_risk_level": by_risk,
            "by_issue_type": by_type,
            "recent": self.interception_history[-10:]
        }

    def annotate_uncertainty(self, text: str) -> str:
        """为高风险内容自动添加不确定性标注"""
        annotated = text
        for pattern in self.assertion_patterns:
            matches = list(re.finditer(pattern, text))
            for m in reversed(matches):  # 倒序替换避免位置偏移
                end = m.end()
                # 找到句子结束位置
                sentence_end = text.find("。", end)
                if sentence_end == -1:
                    sentence_end = len(text)
                sentence = text[end:sentence_end]
                if not any(marker in sentence for marker in self.uncertainty_markers):
                    annotated = annotated[:sentence_end] + "（待核实）" + annotated[sentence_end:]
        return annotated
