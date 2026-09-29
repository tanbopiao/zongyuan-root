#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT MR-014 元认知引擎
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | Ω-TAN-7-001

定位：体系的"自我意识"核心，能审视自身思维过程、识别认知偏差。

核心功能：
  1. 思维日志记录器 - 记录LLM调用输入/输出/推理路径
  2. 认知偏差识别器 - 识别确认偏差/锚定效应/过度概括等8种偏差
  3. 推理质量评估器 - 评估逻辑严密性/证据充分性/结论可靠性
  4. 自我质疑机制   - 对高置信度结论自动生成反方观点
  5. 认知修正策略器 - 生成修正策略并应用到后续推理

技术设计：
  - 思维日志：/opt/ZONGYUAN-ROOT/kernel/cognition/thought_log.jsonl
  - 偏差识别：规则引擎(60%) + LLM辅助(40%) 混合方法
  - 质量评分：四维评分(逻辑/证据/时效/置信度)
  - 自我质疑：对置信度>0.8的结论触发反方论证
  - 常驻服务：每2小时分析一次思维日志
"""

import os
import sys
import json
import time
import sqlite3
import logging
import hashlib
import requests
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

# ============================================================
# 配置
# ============================================================
CONFIG = {
    "db_path": "/opt/ZONGYUAN-ROOT/data/memory_gateway.db",
    "thought_log": "/opt/ZONGYUAN-ROOT/kernel/cognition/thought_log.jsonl",
    "cognition_state": "/opt/ZONGYUAN-ROOT/kernel/cognition/cognition_state.json",
    "log_file": "/opt/ZONGYUAN-ROOT/ops/mr014_metacognition/mr014.log",
    "audit_log": "/opt/ZONGYUAN-ROOT/ops/mr014_metacognition/audit.jsonl",
    "local_llm_url": "http://127.0.0.1:8081/v1/chat/completions",
    "external_llm_url": "http://127.0.0.1:8021/v1/chat/completions",
    "analysis_interval": 7200,  # 分析间隔（2小时）
    "node_id": "mr014-metacognition",
}

# ============================================================
# 8种认知偏差定义
# ============================================================
COGNITIVE_BIASES = {
    "confirmation_bias": {
        "name": "确认偏差",
        "name_en": "Confirmation Bias",
        "description": "倾向于寻找、解释和记忆能够证实自己先入为主观念的信息",
        "indicators": [
            "只引用支持性证据，忽略反面证据",
            "结论与输入假设高度一致，缺乏质疑",
            "对反面观点缺乏回应",
        ],
        "severity": "high",
    },
    "anchoring_effect": {
        "name": "锚定效应",
        "name_en": "Anchoring Effect",
        "description": "过度依赖最初获得的信息（锚点）进行判断",
        "indicators": [
            "结论高度依赖第一个数据点或初始假设",
            "后续信息未能充分调整初始判断",
            "数值估计围绕某个固定值波动",
        ],
        "severity": "medium",
    },
    "overgeneralization": {
        "name": "过度概括",
        "name_en": "Overgeneralization",
        "description": "基于有限的样本或个别案例得出普遍性结论",
        "indicators": [
            "从单个案例推导出普遍规律",
            "样本量过小但结论范围过大",
            "使用'总是''从不''所有'等绝对化表述",
        ],
        "severity": "high",
    },
    "availability_heuristic": {
        "name": "可得性启发",
        "name_en": "Availability Heuristic",
        "description": "根据信息在记忆中的可得性来判断事件发生的概率",
        "indicators": [
            "高估近期或印象深刻事件的概率",
            "判断基于记忆中的例子而非统计数据",
            "对罕见但生动的事件过度担忧",
        ],
        "severity": "medium",
    },
    "halo_effect": {
        "name": "晕轮效应",
        "name_en": "Halo Effect",
        "description": "对某人或某事的整体印象影响对其具体特质的评价",
        "indicators": [
            "对整体印象好的对象，各维度评分都偏高",
            "缺乏对具体维度的独立评估",
            "正面/负面评价扩散到无关维度",
        ],
        "severity": "low",
    },
    "dunning_kruger_effect": {
        "name": "邓宁-克鲁格效应",
        "name_en": "Dunning-Kruger Effect",
        "description": "能力不足的人高估自己的能力，而能力强的人倾向于低估自己",
        "indicators": [
            "对复杂问题给出过于自信的简单答案",
            "承认不确定性的程度与问题复杂度不匹配",
            "缺乏对自身知识边界的认知",
        ],
        "severity": "medium",
    },
    "bandwagon_effect": {
        "name": "从众效应",
        "name_en": "Bandwagon Effect",
        "description": "倾向于做或相信很多其他人也在做或相信的事情",
        "indicators": [
            "结论基于'大家都这么认为'而非独立证据",
            "引用流行观点作为主要论据",
            "缺乏对主流观点的批判性审视",
        ],
        "severity": "low",
    },
    "sunk_cost_fallacy": {
        "name": "沉没成本谬误",
        "name_en": "Sunk Cost Fallacy",
        "description": "因为已经投入了资源而继续进行不合理的决策",
        "indicators": [
            "决策基于已投入的资源而非未来收益",
            "对失败的项目继续投入",
            "难以承认之前的决策错误",
        ],
        "severity": "medium",
    },
}

# ============================================================
# 日志
# ============================================================
def setup_logging():
    os.makedirs(os.path.dirname(CONFIG["log_file"]), exist_ok=True)
    os.makedirs(os.path.dirname(CONFIG["thought_log"]), exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(CONFIG["log_file"]),
            logging.StreamHandler(sys.stdout),
        ],
    )
    return logging.getLogger("mr014")

logger = setup_logging()

# ============================================================
# 工具函数
# ============================================================
def append_jsonl(filepath: str, data: Any):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "a") as f:
        f.write(json.dumps(data, ensure_ascii=False) + "\n")


def call_llm(prompt: str, system_prompt: str = "你是一个元认知分析专家，擅长识别思维中的认知偏差和逻辑问题。",
              use_external: bool = False, max_tokens: int = 500) -> Optional[str]:
    """调用LLM"""
    url = CONFIG["external_llm_url"] if use_external else CONFIG["local_llm_url"]
    model = "doubao" if use_external else "qwen"
    try:
        resp = requests.post(
            url,
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": max_tokens,
                "temperature": 0.3,
            },
            timeout=60 if use_external else 30,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.error(f"LLM调用失败: {e}")
        return None

# ============================================================
# 组件一：思维日志记录器
# ============================================================
class ThoughtLogger:
    """思维日志记录器"""

    def __init__(self, log_path: str):
        self.log_path = log_path

    def log_thought(self, thought_type: str, input_data: Any, output_data: Any,
                     metadata: Dict = None, confidence: float = None) -> str:
        """记录一次思维过程"""
        thought_id = f"THOUGHT-{int(time.time())}-{hashlib.md5(str(time.time()).encode()).hexdigest()[:8]}"
        entry = {
            "thought_id": thought_id,
            "timestamp": datetime.now().isoformat(),
            "thought_type": thought_type,
            "input": self._truncate(input_data),
            "output": self._truncate(output_data),
            "confidence": confidence,
            "metadata": metadata or {},
            "quality_score": None,  # 待评估
            "biases_detected": [],  # 待识别
        }
        append_jsonl(self.log_path, entry)
        return thought_id

    def _truncate(self, data: Any, max_len: int = 2000) -> Any:
        """截断过长的数据"""
        if isinstance(data, str) and len(data) > max_len:
            return data[:max_len] + "...[truncated]"
        if isinstance(data, (dict, list)):
            s = json.dumps(data, ensure_ascii=False)
            if len(s) > max_len:
                return s[:max_len] + "...[truncated]"
        return data

    def get_recent_thoughts(self, limit: int = 20) -> List[Dict]:
        """获取最近的思维记录"""
        thoughts = []
        try:
            with open(self.log_path, "r") as f:
                lines = f.readlines()
                for line in lines[-limit:]:
                    try:
                        thoughts.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        except FileNotFoundError:
            pass
        return thoughts

    def get_thought_count(self) -> int:
        """获取思维记录总数"""
        try:
            with open(self.log_path, "r") as f:
                return sum(1 for _ in f)
        except FileNotFoundError:
            return 0


# ============================================================
# 组件二：认知偏差识别器
# ============================================================
class BiasDetector:
    """认知偏差识别器"""

    def __init__(self):
        self.biases = COGNITIVE_BIASES

    def detect_rules(self, thought: Dict) -> List[Dict]:
        """基于规则的偏差识别（快速初筛）"""
        detected = []
        output = str(thought.get("output", ""))
        input_text = str(thought.get("input", ""))
        combined = input_text + " " + output

        # 1. 过度概括：绝对化表述
        absolute_words = ["总是", "从不", "所有", "全部", "永远", "不可能", "一定", "绝对", "always", "never", "all"]
        abs_count = sum(1 for w in absolute_words if w in combined)
        if abs_count >= 2:
            detected.append({
                "bias_type": "overgeneralization",
                "bias_name": self.biases["overgeneralization"]["name"],
                "confidence": min(0.9, 0.5 + abs_count * 0.1),
                "evidence": f"发现{abs_count}个绝对化表述",
                "detection_method": "rule",
            })

        # 2. 确认偏差：只引用支持性证据
        if "但是" not in combined and "然而" not in combined and "不过" not in combined and len(combined) > 200:
            if "因此" in combined or "所以" in combined:
                detected.append({
                    "bias_type": "confirmation_bias",
                    "bias_name": self.biases["confirmation_bias"]["name"],
                    "confidence": 0.6,
                    "evidence": "有结论但缺乏反面观点讨论",
                    "detection_method": "rule",
                })

        # 3. 邓宁-克鲁格效应：对复杂问题过于自信
        confidence = thought.get("confidence")
        if confidence and confidence > 0.9 and len(combined) < 300:
            detected.append({
                "bias_type": "dunning_kruger_effect",
                "bias_name": self.biases["dunning_kruger_effect"]["name"],
                "confidence": 0.5,
                "evidence": f"置信度{confidence}但内容较短({len(combined)}字符)",
                "detection_method": "rule",
            })

        # 4. 从众效应：引用主流观点
        bandwagon_words = ["大家都", "普遍认为", "众所周知", "主流观点", "一般来说"]
        bw_count = sum(1 for w in bandwagon_words if w in combined)
        if bw_count >= 1 and len(combined) > 100:
            detected.append({
                "bias_type": "bandwagon_effect",
                "bias_name": self.biases["bandwagon_effect"]["name"],
                "confidence": 0.5,
                "evidence": f"引用{bw_count}处主流观点表述",
                "detection_method": "rule",
            })

        return detected

    def detect_llm(self, thought: Dict) -> List[Dict]:
        """基于LLM的深度偏差识别"""
        output = str(thought.get("output", ""))
        if len(output) < 50:
            return []

        prompt = f"""请分析以下思维输出，识别其中可能存在的认知偏差。

思维输出：
{output[:1500]}

请从以下8种偏差中识别（可多选）：
1. confirmation_bias 确认偏差 - 只寻找支持性证据
2. anchoring_effect 锚定效应 - 过度依赖初始信息
3. overgeneralization 过度概括 - 从有限样本得出普遍结论
4. availability_heuristic 可得性启发 - 基于记忆可得性判断概率
5. halo_effect 晕轮效应 - 整体印象影响具体评价
6. dunning_kruger_effect 邓宁-克鲁格效应 - 能力不足却高估自己
7. bandwagon_effect 从众效应 - 跟随主流观点
8. sunk_cost_fallacy 沉没成本谬误 - 因已投入而继续不合理决策

只输出JSON格式：
{{"biases": [{{"bias_type": "...", "confidence": 0.0-1.0, "evidence": "具体证据"}}], "summary": "简要分析"}}
"""
        result = call_llm(prompt, use_external=True, max_tokens=400)
        if not result:
            return []

        try:
            # 提取JSON
            json_start = result.find("{")
            json_end = result.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                parsed = json.loads(result[json_start:json_end])
                biases = parsed.get("biases", [])
                for b in biases:
                    b["detection_method"] = "llm"
                    b["bias_name"] = self.biases.get(b["bias_type"], {}).get("name", b["bias_type"])
                return biases
        except Exception as e:
            logger.error(f"LLM偏差识别结果解析失败: {e}")
        return []

    def detect(self, thought: Dict) -> List[Dict]:
        """综合偏差识别（规则+LLM）"""
        # 规则初筛
        rule_biases = self.detect_rules(thought)
        # LLM深度识别（只对有一定长度的思维）
        llm_biases = self.detect_llm(thought) if len(str(thought.get("output", ""))) > 100 else []

        # 合并去重
        all_biases = rule_biases + llm_biases
        seen = set()
        unique = []
        for b in all_biases:
            key = b["bias_type"]
            if key not in seen:
                seen.add(key)
                unique.append(b)
            else:
                # 更新置信度（取较高的）
                for existing in unique:
                    if existing["bias_type"] == key:
                        existing["confidence"] = max(existing["confidence"], b["confidence"])
                        existing["detection_method"] = "rule+llm"
                        break
        return unique


# ============================================================
# 组件三：推理质量评估器
# ============================================================
class QualityEvaluator:
    """推理质量评估器"""

    def evaluate(self, thought: Dict) -> Dict:
        """评估思维质量（四维评分）"""
        output = str(thought.get("output", ""))
        input_text = str(thought.get("input", ""))
        combined = input_text + " " + output

        # 1. 逻辑严密性 (25分)
        logic_score = self._evaluate_logic(combined)

        # 2. 证据充分性 (25分)
        evidence_score = self._evaluate_evidence(combined)

        # 3. 时效性 (25分)
        timeliness_score = self._evaluate_timeliness(thought)

        # 4. 置信度合理性 (25分)
        confidence_score = self._evaluate_confidence(thought, combined)

        total = logic_score + evidence_score + timeliness_score + confidence_score

        if total >= 90:
            grade = "A"
        elif total >= 75:
            grade = "B"
        elif total >= 60:
            grade = "C"
        elif total >= 40:
            grade = "D"
        else:
            grade = "E"

        return {
            "total_score": round(total, 1),
            "grade": grade,
            "dimensions": {
                "logic": {"score": logic_score, "max": 25, "name": "逻辑严密性"},
                "evidence": {"score": evidence_score, "max": 25, "name": "证据充分性"},
                "timeliness": {"score": timeliness_score, "max": 25, "name": "时效性"},
                "confidence": {"score": confidence_score, "max": 25, "name": "置信度合理性"},
            },
        }

    def _evaluate_logic(self, text: str) -> float:
        """评估逻辑严密性"""
        score = 15.0  # 基础分

        # 有逻辑连接词
        logic_words = ["因此", "所以", "因为", "由于", "由此可见", "综上所述", "然而", "但是", "不过", "虽然", "尽管"]
        logic_count = sum(1 for w in logic_words if w in text)
        score += min(5, logic_count * 0.5)

        # 有结构（分段/编号）
        if "\n" in text or "1." in text or "第一" in text:
            score += 3

        # 长度适中（太短可能逻辑不完整）
        if len(text) > 100:
            score += 2
        elif len(text) < 30:
            score -= 3

        return max(0, min(25, score))

    def _evaluate_evidence(self, text: str) -> float:
        """评估证据充分性"""
        score = 10.0  # 基础分

        # 有数据/数字
        import re
        numbers = re.findall(r'\d+\.?\d*', text)
        if len(numbers) >= 3:
            score += 5
        elif len(numbers) >= 1:
            score += 2

        # 有引用/来源
        source_words = ["根据", "据", "数据显示", "研究表明", "统计", "报告", "文献"]
        source_count = sum(1 for w in source_words if w in text)
        score += min(5, source_count * 2)

        # 有具体案例
        case_words = ["例如", "比如", "案例", "实例", "具体来说"]
        if any(w in text for w in case_words):
            score += 3

        # 长度
        if len(text) > 200:
            score += 2

        return max(0, min(25, score))

    def _evaluate_timeliness(self, thought: Dict) -> float:
        """评估时效性"""
        score = 20.0  # 基础分
        timestamp = thought.get("timestamp")
        if timestamp:
            try:
                thought_time = datetime.fromisoformat(timestamp)
                age_hours = (datetime.now() - thought_time).total_seconds() / 3600
                if age_hours < 1:
                    score = 25
                elif age_hours < 6:
                    score = 22
                elif age_hours < 24:
                    score = 18
                elif age_hours < 72:
                    score = 12
                else:
                    score = 8
            except Exception:
                pass
        return score

    def _evaluate_confidence(self, thought: Dict, text: str) -> float:
        """评估置信度合理性"""
        score = 15.0
        confidence = thought.get("confidence")

        if confidence is None:
            return 15.0  # 无置信度给中等分

        # 高置信度需要有充分的内容和证据
        if confidence > 0.9:
            if len(text) > 200:
                score = 25
            elif len(text) > 100:
                score = 20
            else:
                score = 10  # 高置信度但内容少，不合理
        elif confidence > 0.7:
            score = 20 if len(text) > 100 else 15
        elif confidence > 0.5:
            score = 18
        else:
            score = 22  # 低置信度是诚实的表现

        return max(0, min(25, score))


# ============================================================
# 组件四：自我质疑机制
# ============================================================
class SelfQuestioner:
    """自我质疑机制"""

    def __init__(self, threshold: float = 0.8):
        self.threshold = threshold

    def should_question(self, thought: Dict) -> bool:
        """判断是否需要自我质疑"""
        confidence = thought.get("confidence")
        output = str(thought.get("output", ""))
        # 高置信度且有明确结论的需要质疑
        if confidence and confidence >= self.threshold and len(output) > 50:
            return True
        # 包含绝对化结论的需要质疑
        absolute_words = ["因此", "所以", "由此可见", "综上所述", "结论是"]
        if any(w in output for w in absolute_words):
            return True
        return False

    def generate_counterargument(self, thought: Dict) -> Optional[Dict]:
        """生成反方观点"""
        output = str(thought.get("output", ""))
        if len(output) < 50:
            return None

        prompt = f"""请对以下结论进行自我质疑，生成反方观点和潜在问题。

原结论：
{output[:1500]}

请从以下角度质疑：
1. 这个结论的前提假设是否可靠？
2. 有哪些反面证据或例外情况？
3. 结论的适用范围是否被过度扩大？
4. 长期来看可能有什么 unintended consequences？

只输出JSON格式：
{{"counterarguments": ["反方观点1", "反方观点2", ...], "weaknesses": ["弱点1", "弱点2", ...], "caveats": ["注意事项1", ...], "overall_assessment": "对原结论的整体评估"}}
"""
        result = call_llm(prompt, use_external=True, max_tokens=500)
        if not result:
            return None

        try:
            json_start = result.find("{")
            json_end = result.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                parsed = json.loads(result[json_start:json_end])
                return {
                    "thought_id": thought.get("thought_id"),
                    "counterarguments": parsed.get("counterarguments", []),
                    "weaknesses": parsed.get("weaknesses", []),
                    "caveats": parsed.get("caveats", []),
                    "overall_assessment": parsed.get("overall_assessment", ""),
                    "timestamp": datetime.now().isoformat(),
                }
        except Exception as e:
            logger.error(f"自我质疑结果解析失败: {e}")
        return None


# ============================================================
# 组件五：认知修正策略器
# ============================================================
class CorrectionStrategy:
    """认知修正策略生成器"""

    def generate_strategy(self, biases: List[Dict], quality: Dict) -> Dict:
        """根据识别的偏差和质量评估生成修正策略"""
        strategies = []

        for bias in biases:
            bias_type = bias.get("bias_type")
            confidence = bias.get("confidence", 0)
            if confidence < 0.5:
                continue  # 低置信度偏差不生成策略

            strategy = self._get_bias_correction(bias_type)
            if strategy:
                strategies.append({
                    "bias_type": bias_type,
                    "bias_name": bias.get("bias_name"),
                    "confidence": confidence,
                    "strategy": strategy,
                })

        # 基于质量评估的通用策略
        total_score = quality.get("total_score", 0)
        if total_score < 60:
            strategies.append({
                "bias_type": "low_quality",
                "bias_name": "低质量推理",
                "confidence": 1.0,
                "strategy": "加强证据收集，增加逻辑结构，明确前提假设，降低结论置信度",
            })

        # 生成system prompt级别的修正指令
        correction_prompt = self._build_correction_prompt(strategies)

        return {
            "strategies": strategies,
            "correction_prompt": correction_prompt,
            "strategy_count": len(strategies),
            "timestamp": datetime.now().isoformat(),
        }

    def _get_bias_correction(self, bias_type: str) -> str:
        """获取特定偏差的修正策略"""
        corrections = {
            "confirmation_bias": "主动寻找反面证据，列出支持和反对两方面论据，对结论进行辩证检验",
            "anchoring_effect": "从多个独立来源获取初始数据，进行区间估计而非点估计，定期重新评估锚点",
            "overgeneralization": "明确结论的适用范围和边界条件，使用限定词（在某些情况下/通常），提供反例",
            "availability_heuristic": "基于统计数据而非记忆中的例子进行判断，查询基础概率，区分生动案例和普遍规律",
            "halo_effect": "对每个维度进行独立评估，使用评分量表，避免整体印象扩散",
            "dunning_kruger_effect": "承认知识边界，列出不确定的方面，寻求外部验证，对复杂问题保持谦逊",
            "bandwagon_effect": "独立评估证据，质疑主流观点的前提，考虑少数派观点，避免以流行度作为论据",
            "sunk_cost_fallacy": "决策时只考虑未来成本和收益，忽略已投入的资源，设定止损点，定期重新评估",
        }
        return corrections.get(bias_type, "加强批判性思维，多角度审视结论")

    def _build_correction_prompt(self, strategies: List[Dict]) -> str:
        """构建修正用的system prompt"""
        if not strategies:
            return "保持当前推理方式。"

        prompt_parts = ["在后续推理中，请注意以下认知修正："]
        for s in strategies:
            prompt_parts.append(f"- {s['bias_name']}: {s['strategy']}")
        prompt_parts.append("\n请在推理过程中主动应用以上修正策略。")
        return "\n".join(prompt_parts)


# ============================================================
# 元认知引擎主类
# ============================================================
class MetacognitionEngine:
    """元认知引擎主类"""

    def __init__(self):
        self.thought_logger = ThoughtLogger(CONFIG["thought_log"])
        self.bias_detector = BiasDetector()
        self.quality_evaluator = QualityEvaluator()
        self.self_questioner = SelfQuestioner(threshold=0.8)
        self.correction_strategy = CorrectionStrategy()
        self.state = self._load_state()

    def _load_state(self) -> Dict:
        """加载状态"""
        if os.path.exists(CONFIG["cognition_state"]):
            try:
                with open(CONFIG["cognition_state"], "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "total_thoughts_analyzed": 0,
            "biases_detected": 0,
            "self_questions_generated": 0,
            "correction_strategies_generated": 0,
            "avg_quality_score": 0,
            "quality_distribution": {"A": 0, "B": 0, "C": 0, "D": 0, "E": 0},
            "bias_distribution": {},
            "last_analysis": None,
            "started_at": datetime.now().isoformat(),
        }

    def _save_state(self):
        """保存状态"""
        os.makedirs(os.path.dirname(CONFIG["cognition_state"]), exist_ok=True)
        with open(CONFIG["cognition_state"], "w") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    def analyze_thought(self, thought: Dict) -> Dict:
        """分析单条思维记录"""
        # 1. 偏差识别
        biases = self.bias_detector.detect(thought)

        # 2. 质量评估
        quality = self.quality_evaluator.evaluate(thought)

        # 3. 自我质疑（对高置信度结论）
        counterargument = None
        if self.self_questioner.should_question(thought):
            counterargument = self.self_questioner.generate_counterargument(thought)

        # 4. 修正策略
        correction = self.correction_strategy.generate_strategy(biases, quality)

        # 5. 更新状态
        self.state["total_thoughts_analyzed"] += 1
        self.state["biases_detected"] += len(biases)
        if counterargument:
            self.state["self_questions_generated"] += 1
        if correction["strategy_count"] > 0:
            self.state["correction_strategies_generated"] += 1

        # 更新质量分布
        grade = quality["grade"]
        self.state["quality_distribution"][grade] = self.state["quality_distribution"].get(grade, 0) + 1

        # 更新平均质量分
        total = self.state["total_thoughts_analyzed"]
        old_avg = self.state["avg_quality_score"]
        self.state["avg_quality_score"] = round((old_avg * (total - 1) + quality["total_score"]) / total, 1)

        # 更新偏差分布
        for b in biases:
            bt = b["bias_type"]
            self.state["bias_distribution"][bt] = self.state["bias_distribution"].get(bt, 0) + 1

        self.state["last_analysis"] = datetime.now().isoformat()
        self._save_state()

        result = {
            "thought_id": thought.get("thought_id"),
            "biases": biases,
            "quality": quality,
            "counterargument": counterargument,
            "correction": correction,
        }

        # 写入9120真值
        self._write_to_gateway(result)

        return result

    def analyze_recent_thoughts(self, limit: int = 10) -> List[Dict]:
        """分析最近的思维记录"""
        thoughts = self.thought_logger.get_recent_thoughts(limit)
        results = []
        for thought in thoughts:
            # 跳过已分析的
            if thought.get("quality_score"):
                continue
            result = self.analyze_thought(thought)
            results.append(result)
        return results

    def analyze_truths_from_gateway(self, limit: int = 20) -> List[Dict]:
        """分析9120中的真值（作为思维产物）"""
        conn = sqlite3.connect(CONFIG["db_path"])
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT truth_key, truth_value, category, node_id, updated_at
            FROM truths
            WHERE node_id IN ('mr010-dual-compute-scheduler', 'mr011-stability-evolution')
               OR truth_key LIKE '%SELF_REFLECTION%'
               OR truth_key LIKE '%ANOMALY_DETECT%'
               OR truth_key LIKE '%LOG_SUMMARY%'
            ORDER BY updated_at DESC
            LIMIT ?
        """, (limit,))
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()

        results = []
        for row in rows:
            thought = {
                "thought_id": f"TRUTH-{row['truth_key']}",
                "timestamp": datetime.fromtimestamp(row["updated_at"]).isoformat() if row.get("updated_at") else datetime.now().isoformat(),
                "thought_type": f"truth_{row.get('category', 'unknown')}",
                "input": row["truth_key"],
                "output": row["truth_value"],
                "confidence": None,
                "metadata": {"source": "9120_gateway", "category": row.get("category"), "node_id": row.get("node_id")},
            }
            result = self.analyze_thought(thought)
            results.append(result)
        return results

    def _write_to_gateway(self, result: Dict):
        """将分析结果写入9120"""
        try:
            conn = sqlite3.connect(CONFIG["db_path"])
            cursor = conn.cursor()
            key = f"METACOGNITION.{datetime.now().strftime('%Y%m%d_%H%M%S')}.{hashlib.md5(str(time.time()).encode()).hexdigest()[:6]}"
            value = json.dumps(result, ensure_ascii=False)
            truth_hash = hashlib.sha256(value.encode()).hexdigest()
            now = time.time()
            cursor.execute(
                "INSERT INTO truths (truth_key, truth_value, truth_hash, category, node_id, created_at, updated_at, version) VALUES (?,?,?,?,?,?,?,1)",
                (key, value, truth_hash, "method", CONFIG["node_id"], now, now)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"写入9120失败: {e}")

    def get_status(self) -> Dict:
        """获取引擎状态"""
        return {
            "thought_log_count": self.thought_logger.get_thought_count(),
            "state": self.state,
        }

    def run_analysis_cycle(self):
        """执行一轮分析循环"""
        logger.info("=" * 60)
        logger.info("MR-014 元认知分析循环")
        logger.info("=" * 60)

        # 分析9120中的思维产物
        logger.info("分析9120中的思维产物...")
        results = self.analyze_truths_from_gateway(limit=15)
        logger.info(f"分析了{len(results)}条思维产物")

        # 统计
        total_biases = sum(len(r["biases"]) for r in results)
        avg_quality = sum(r["quality"]["total_score"] for r in results) / len(results) if results else 0
        counter_count = sum(1 for r in results if r["counterargument"])
        correction_count = sum(1 for r in results if r["correction"]["strategy_count"] > 0)

        logger.info(f"偏差识别: {total_biases}个")
        logger.info(f"平均质量分: {avg_quality:.1f}")
        logger.info(f"自我质疑: {counter_count}次")
        logger.info(f"修正策略: {correction_count}个")

        logger.info("=" * 60)
        return results

    def run_forever(self):
        """常驻运行"""
        logger.info("")
        logger.info("╔══════════════════════════════════════════════════════╗")
        logger.info("║  MR-014 元认知引擎启动                               ║")
        logger.info("║  思维日志: {}       ║".format(CONFIG["thought_log"]))
        logger.info("║  偏差识别: 规则+LLM混合 (8种认知偏差)               ║")
        logger.info("║  质量评估: 四维评分 (逻辑/证据/时效/置信度)         ║")
        logger.info("║  自我质疑: 高置信度结论自动反方论证                  ║")
        logger.info("║  分析间隔: 每2小时                                    ║")
        logger.info("╚══════════════════════════════════════════════════════╝")
        logger.info("")

        # 启动时立即执行一轮
        self.run_analysis_cycle()

        while True:
            time.sleep(CONFIG["analysis_interval"])
            try:
                self.run_analysis_cycle()
            except Exception as e:
                logger.error(f"分析循环异常: {e}")
                time.sleep(60)


# ============================================================
# 命令行入口
# ============================================================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="MR-014 元认知引擎")
    parser.add_argument("command", choices=["analyze", "status", "daemon"],
                        help="analyze=执行一轮分析, status=查看状态, daemon=常驻运行")
    parser.add_argument("--limit", type=int, default=10, help="分析数量（默认10）")
    args = parser.parse_args()

    engine = MetacognitionEngine()

    if args.command == "analyze":
        results = engine.analyze_truths_from_gateway(limit=args.limit)
        print(f"分析完成: {len(results)}条思维产物")
        for r in results[:3]:
            print(f"\n--- {r['thought_id']} ---")
            print(f"  质量: {r['quality']['total_score']}/100 ({r['quality']['grade']})")
            print(f"  偏差: {len(r['biases'])}个")
            for b in r['biases']:
                print(f"    - {b['bias_name']} (置信度{b['confidence']:.2f})")
            if r['counterargument']:
                print(f"  自我质疑: 已生成")
            if r['correction']['strategy_count'] > 0:
                print(f"  修正策略: {r['correction']['strategy_count']}个")
    elif args.command == "status":
        status = engine.get_status()
        print(json.dumps(status, ensure_ascii=False, indent=2))
    elif args.command == "daemon":
        engine.run_forever()
