"""
LOIP 语义级检测模块 v0.2
提供抽象检测接口，支持两种后端：
1. KeywordBackend（默认，零依赖）：关键词/规则匹配
2. SemanticBackend（可选，需pip install sentence-transformers）：向量相似度+NLI语义检测

使用方式：
    from loip.semantic import get_detector
    detector = get_detector(backend="semantic")  # 或 "keyword"
    score = detector.similarity("输出内容", "规则内容")
    is_violation = detector.check_violation("输出内容", "规则内容")
"""
import re
from typing import List, Optional, Tuple


class BaseDetector:
    """检测后端抽象基类"""

    def similarity(self, text1: str, text2: str) -> float:
        """计算两段文本的语义相似度，返回0-1"""
        raise NotImplementedError

    def check_violation(self, output: str, rule: str) -> Tuple[bool, float]:
        """
        检测输出是否违反规则
        返回: (是否违反, 置信度0-1)
        """
        raise NotImplementedError

    def check_contradiction(self, output: str, fact: str) -> Tuple[bool, float]:
        """
        检测输出是否与事实矛盾
        返回: (是否矛盾, 置信度0-1)
        """
        raise NotImplementedError

    def batch_similarity(self, text: str, candidates: List[str]) -> List[float]:
        """批量计算相似度"""
        return [self.similarity(text, c) for c in candidates]


class KeywordBackend(BaseDetector):
    """关键词匹配后端（默认，零依赖）"""

    def __init__(self):
        self.negation_words = ["不", "没", "无", "非", "否", "禁止", "不得", "不能", "不可", "严禁",
                               "never", "not", "no", "cannot", "must not"]
        self.assertion_patterns = [
            r"根据(统计|数据|研究|报告)",
            r"(百分之|%)\d+",
            r"(首次|唯一|最大|最好|最优)",
            r"(证明|证实|确认|发现)",
            r"(必须|一定|绝对|肯定)",
        ]

    def similarity(self, text1: str, text2: str) -> float:
        """基于关键词重叠的相似度"""
        words1 = set(self._tokenize(text1))
        words2 = set(self._tokenize(text2))
        if not words1 or not words2:
            return 0.0
        intersection = words1 & words2
        union = words1 | words2
        return len(intersection) / len(union)

    def check_violation(self, output: str, rule: str) -> Tuple[bool, float]:
        """检测规则违反：提取规则中被禁止的内容，检查输出是否包含"""
        # 提取否定词后的禁止内容
        for neg in self.negation_words:
            if neg in rule:
                parts = rule.split(neg, 1)
                if len(parts) > 1:
                    forbidden = parts[1].strip()[:30]
                    if forbidden and forbidden in output:
                        # 检查输出中是否也有否定（可能是双重否定=遵守）
                        output_context = output[max(0, output.find(forbidden)-10):output.find(forbidden)+len(forbidden)]
                        if not any(n in output_context for n in self.negation_words):
                            return True, 0.7
        return False, 0.0

    def check_contradiction(self, output: str, fact: str) -> Tuple[bool, float]:
        """检测事实矛盾：检查输出中是否有事实的否定形式"""
        fact_keywords = self._tokenize(fact)
        for kw in fact_keywords:
            if kw in output:
                pos = output.find(kw)
                context = output[max(0, pos-10):pos]
                if any(n in context for n in self.negation_words):
                    return True, 0.6
        return False, 0.0

    def _tokenize(self, text: str) -> List[str]:
        """简化分词：提取2字以上中文词组和英文单词"""
        words = re.findall(r'[\u4e00-\u9fa5]{2,}|[a-zA-Z]{3,}', text)
        return list(set(words))


class SemanticBackend(BaseDetector):
    """语义检测后端（可选，需安装sentence-transformers）"""

    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"):
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model_name)
            self.available = True
            self.model_name = model_name
        except ImportError:
            self.available = False
            self.model = None
            self.model_name = model_name
            print(f"[LOIP] 语义后端未启用：请运行 pip install sentence-transformers")
            print(f"[LOIP] 当前回退到关键词匹配后端")

        # NLI模型用于矛盾检测（可选）
        self.nli_model = None
        try:
            from transformers import pipeline
            self.nli_model = pipeline("text-classification",
                                      model="cross-encoder/nli-deberta-v3-base",
                                      device=-1)
        except Exception:
            pass

    def similarity(self, text1: str, text2: str) -> float:
        """基于向量的余弦相似度"""
        if not self.available:
            return KeywordBackend().similarity(text1, text2)
        import numpy as np
        emb1 = self.model.encode(text1)
        emb2 = self.model.encode(text2)
        cos_sim = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
        return float(max(0, min(1, cos_sim)))

    def check_violation(self, output: str, rule: str) -> Tuple[bool, float]:
        """语义级规则违反检测"""
        if not self.available:
            return KeywordBackend().check_violation(output, rule)

        # 方法：计算输出与"违反规则的表述"的相似度
        # 将规则转换为正面表述，然后检测输出是否与之相反
        sim = self.similarity(output, rule)
        # 如果输出与规则相似度低，且包含规则关键词，则可能违反
        rule_keywords = KeywordBackend()._tokenize(rule)
        keyword_hit = any(kw in output for kw in rule_keywords)

        if keyword_hit and sim < 0.4:
            return True, 1.0 - sim
        return False, sim

    def check_contradiction(self, output: str, fact: str) -> Tuple[bool, float]:
        """语义级矛盾检测（优先使用NLI模型）"""
        if self.nli_model:
            try:
                result = self.nli_model(f"{fact} {output}")
                label = result[0]["label"]
                score = result[0]["score"]
                if label == "CONTRADICTION":
                    return True, float(score)
                return False, float(score)
            except Exception:
                pass

        if not self.available:
            return KeywordBackend().check_contradiction(output, fact)

        # 回退：基于相似度的矛盾判断
        sim = self.similarity(output, fact)
        # 提取事实关键词，检查输出中是否有否定
        fact_keywords = KeywordBackend()._tokenize(fact)
        negation_in_output = any(n in output for n in KeywordBackend().negation_words)

        if negation_in_output and any(kw in output for kw in fact_keywords):
            return True, 0.8
        if sim < 0.3 and any(kw in output for kw in fact_keywords):
            return True, 0.5
        return False, sim


def get_detector(backend: str = "auto") -> BaseDetector:
    """
    获取检测器实例
    backend: "auto"（自动选择，有语义库用语义，否则关键词）
             "keyword"（强制关键词）
             "semantic"（强制语义，不可用则回退）
    """
    if backend == "keyword":
        return KeywordBackend()
    if backend == "semantic":
        return SemanticBackend()
    # auto：尝试语义，失败回退关键词
    detector = SemanticBackend()
    if detector.available:
        return detector
    return KeywordBackend()


def extract_entities(text: str) -> List[str]:
    """
    提取文本中的实体（数字、时间、专有名词）
    用于幻觉检测中的实体级事实校验
    """
    entities = []
    # 数字+单位
    entities.extend(re.findall(r'\d+(?:\.\d+)?(?:%|％|个|人|元|天|年|月|日|次|倍|MB|GB|TB|km|m|kg)?', text))
    # 时间
    entities.extend(re.findall(r'\d{4}年\d{1,2}月|\d{1,2}月\d{1,2}日|昨天|今天|明天|上周|下周', text))
    # 英文专有名词（大写开头）
    entities.extend(re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text))
    return list(set(entities))
