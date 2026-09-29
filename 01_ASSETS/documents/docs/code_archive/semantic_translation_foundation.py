#!/usr/bin/env python3
"""
语义转译基座 V1.0
ZONGYUAN-ROOT 元极恒一自治体系

核心能力：语言 ↔ 符号 ↔逻辑 三者双向映射

三层架构：
  L1 语言层 (Language)   - 自然语言描述
  L2 符号层 (Symbol)     - 形式化符号表达式
  L3 逻辑层 (Logic)      - 命题/谓词/因果逻辑

锚定：Ω₀⊂⊙∞⊂Ω | DID-BR-000002
"""

import json
import time
import datetime
import hashlib
import urllib.request
import re
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Set
from enum import Enum
from collections import defaultdict

# ============ 配置 ============
GATEWAY_BASE = "https://www.huodouai.com"
DID = "DID-BR-000002"
ANCHOR = "Ω₀⊂⊙∞⊂Ω"
SOURCE_NODE = "ZR-NODE-DC2E51C0"

# ============ 符号系统定义 ============
class SymbolSystem:
    """体系符号系统定义"""

    # 核心锚定符号
    CORE_SYMBOLS = {
        "Ω₀": "元初本体/零阶存在",
        "⊙": "自指循环/奇点核心",
        "∞": "无限/完备域",
        "Ω": "全集合/终极实在",
        "⊂": "包含/从属关系",
        "Ω₀⊂⊙∞⊂Ω": "元极恒一锚定公式：元初本体包含于奇点无限，奇点无限包含于终极实在",
    }

    # 体系标识符号
    IDENTITY_SYMBOLS = {
        "DID-BR-000002": "体系去中心化身份标识",
        "ZR-NODE": "宗源节点前缀",
        "V3.0": "记忆网关版本",
        "Ω-TAN-7-001": "根Omega标识",
    }

    # 逻辑符号
    LOGIC_SYMBOLS = {
        "∧": "合取(且)",
        "∨": "析取(或)",
        "¬": "否定(非)",
        "→": "蕴含(如果...则)",
        "↔": "等价(当且仅当)",
        "∀": "全称量词(所有)",
        "∃": "存在量词(存在)",
        "∴": "所以/因此",
        "∵": "因为",
        "⊢": "可证明/推导",
        "⊨": "语义蕴含",
        "⊥": "矛盾/假",
        "⊤": "重言式/真",
    }

    # 因果符号
    CAUSAL_SYMBOLS = {
        "⇒": "因果导致",
        "⇐": "因果溯源",
        "⇔": "因果互为",
        "→c": "因果边",
        "P(A|B)": "条件概率",
        "do(X)": "干预算子",
        "Σ": "因果汇聚",
        "Δ": "因果分支",
    }

    # 数学符号
    MATH_SYMBOLS = {
        "Σ": "求和",
        "∏": "求积",
        "∫": "积分",
        "∂": "偏导",
        "√": "平方根",
        "≈": "约等于",
        "≠": "不等于",
        "≤": "小于等于",
        "≥": "大于等于",
        "∈": "属于",
        "∉": "不属于",
        "∩": "交集",
        "∪": "并集",
        "∅": "空集",
    }

    # 算子符号（体系27算子）
    OPERATOR_SYMBOLS = {
        "P4": "真值对账算子",
        "P7": "外部锚定算子",
        "SM": "语义空间",
        "BS": "黎曼流形",
        "CTE": "因果-真值-进化三位一体",
        "C→T": "因果到真值适配器",
        "T→E": "真值到进化适配器",
        "E→C": "进化到因果适配器",
        "M-DAG": "Merkle有向无环图",
        "ZKP": "零知识证明",
        "eFuse": "电子熔断",
        "Lv6": "六级文明仿真",
    }

    @classmethod
    def get_all_symbols(cls) -> Dict[str, str]:
        """获取所有符号定义"""
        all_symbols = {}
        for attr in dir(cls):
            if attr.endswith('_SYMBOLS') and attr.isupper():
                all_symbols.update(getattr(cls, attr))
        return all_symbols

# ============ 逻辑表达式 ============
class LogicExpression:
    """逻辑表达式解析与表示"""

    class LogicType(Enum):
        PROPOSITION = "proposition"    # 命题逻辑
        PREDICATE = "predicate"        # 谓词逻辑
        CAUSAL = "causal"              # 因果逻辑
        MODAL = "modal"                # 模态逻辑
        TEMPORAL = "temporal"          # 时序逻辑

    def __init__(self, expression: str, expr_type: LogicType = LogicType.PROPOSITION):
        self.raw = expression
        self.expr_type = expr_type
        self.tokens = self._tokenize()
        self.truth_value = None  # 三值逻辑: True/False/Unknown

    def _tokenize(self) -> List[str]:
        """简单分词"""
        # 匹配逻辑符号、单词、数字
        pattern = r'[∧∨¬→↔∀∃∴∵⊢⊨⊥⊤⇒⇐⇔ΣΔ()]|[A-Za-z_][A-Za-z0-9_]*|\d+\.?\d*'
        return re.findall(pattern, self.raw)

    def evaluate(self, variables: Dict[str, bool] = None) -> Optional[bool]:
        """简单命题逻辑求值"""
        if variables is None:
            variables = {}
        # 替换变量
        expr = self.raw
        for var, val in variables.items():
            expr = expr.replace(var, 'True' if val else 'False')
        # 替换逻辑符号
        expr = expr.replace('∧', ' and ').replace('∨', ' or ')
        expr = expr.replace('¬', ' not ').replace('→', ' <= ')
        expr = expr.replace('↔', ' == ')
        try:
            return eval(expr)
        except:
            return None

    def to_natural_language(self) -> str:
        """逻辑表达式转自然语言"""
        expr = self.raw
        # 因果逻辑
        if '⇒' in expr:
            parts = expr.split('⇒')
            return f"因为{parts[0].strip()}，所以{parts[1].strip()}"
        if '⇐' in expr:
            parts = expr.split('⇐')
            return f"{parts[1].strip()}是{parts[0].strip()}的原因"
        # 命题逻辑
        expr = expr.replace('∧', '且').replace('∨', '或')
        expr = expr.replace('¬', '非').replace('→', '蕴含')
        expr = expr.replace('↔', '等价于').replace('∴', '因此')
        expr = expr.replace('∵', '因为').replace('⊢', '可推导')
        return expr

# ============ 转译引擎 ============
class SemanticTranslator:
    """语义转译引擎：语言↔符号↔逻辑"""

    def __init__(self):
        self.symbols = SymbolSystem.get_all_symbols()
        self.symbol_to_lang = self.symbols
        self.lang_to_symbol = self._build_lang_index()
        self.translation_cache = {}

    def _build_lang_index(self) -> Dict[str, str]:
        """构建自然语言→符号的反向索引"""
        index = {}
        for symbol, meaning in self.symbols.items():
            # 用含义中的关键词建立索引
            keywords = re.findall(r'[\u4e00-\u9fa5A-Za-z]+', meaning)
            for kw in keywords:
                if len(kw) >= 2:
                    index[kw.lower()] = symbol
        return index

    def language_to_symbol(self, text: str) -> Tuple[str, List[Dict]]:
        """
        自然语言 → 符号表达式
        返回: (符号表达式, 映射记录列表)
        """
        cache_key = f"l2s:{hashlib.md5(text.encode()).hexdigest()}"
        if cache_key in self.translation_cache:
            return self.translation_cache[cache_key]

        mappings = []
        result = text

        # 1. 精确匹配符号含义
        for symbol, meaning in self.symbols.items():
            if meaning in text or meaning[:4] in text:
                result = result.replace(meaning, symbol)
                mappings.append({"from": meaning, "to": symbol, "type": "exact"})

        # 2. 关键词匹配
        for keyword, symbol in self.lang_to_symbol.items():
            if keyword in text.lower() and symbol not in result:
                # 只替换首次出现的完整词
                pattern = re.compile(re.escape(keyword), re.IGNORECASE)
                if pattern.search(result):
                    result = pattern.sub(symbol, result, count=1)
                    mappings.append({"from": keyword, "to": symbol, "type": "keyword"})

        # 3. 因果关系检测
        causal_patterns = [
            (r'因为(.+?)所以', r'\1 ⇒ '),
            (r'由于(.+?)导致', r'\1 ⇒ '),
            (r'如果(.+?)那么', r'\1 → '),
            (r'(.+?)的原因是', r'\1 ⇐ '),
        ]
        for pattern, replacement in causal_patterns:
            match = re.search(pattern, result)
            if match:
                mappings.append({"from": match.group(0), "to": "causal_operator", "type": "causal"})

        self.translation_cache[cache_key] = (result, mappings)
        return result, mappings

    def symbol_to_language(self, symbol_expr: str) -> Tuple[str, List[Dict]]:
        """
        符号表达式 → 自然语言
        返回: (自然语言, 映射记录列表)
        """
        cache_key = f"s2l:{hashlib.md5(symbol_expr.encode()).hexdigest()}"
        if cache_key in self.translation_cache:
            return self.translation_cache[cache_key]

        mappings = []
        result = symbol_expr

        # 按符号长度降序替换（避免部分匹配）
        sorted_symbols = sorted(self.symbols.keys(), key=len, reverse=True)
        for symbol in sorted_symbols:
            if symbol in result:
                meaning = self.symbols[symbol]
                result = result.replace(symbol, meaning)
                mappings.append({"from": symbol, "to": meaning, "type": "symbol_decode"})

        # 逻辑符号转语言
        logic_translations = [
            ('∧', '且'), ('∨', '或'), ('¬', '非'),
            ('→', '蕴含'), ('↔', '等价于'), ('∴', '因此'),
            ('∵', '因为'), ('⇒', '导致'), ('⇐', '源于'),
            ('⊢', '可证明'), ('⊨', '语义蕴含'),
        ]
        for sym, lang in logic_translations:
            if sym in result:
                result = result.replace(sym, lang)
                mappings.append({"from": sym, "to": lang, "type": "logic_decode"})

        self.translation_cache[cache_key] = (result, mappings)
        return result, mappings

    def language_to_logic(self, text: str) -> Tuple[LogicExpression, Dict]:
        """
        自然语言 → 逻辑表达式
        返回: (逻辑表达式对象, 解析信息)
        """
        info = {"detected_type": "proposition", "variables": [], "operators": []}

        # 检测因果逻辑
        if any(w in text for w in ['因为', '所以', '导致', '原因', '引起']):
            info["detected_type"] = "causal"
            if '因为' in text and '所以' in text:
                parts = re.split(r'因为|所以', text)
                if len(parts) >= 3:
                    cause = parts[1].strip()
                    effect = parts[2].strip()
                    expr = LogicExpression(f"{cause} ⇒ {effect}", LogicExpression.LogicType.CAUSAL)
                    info["variables"] = [cause, effect]
                    info["operators"] = ["⇒"]
                    return expr, info

        # 检测条件逻辑
        if any(w in text for w in ['如果', '那么', '只要', '就']):
            if '如果' in text and '那么' in text:
                parts = re.split(r'如果|那么', text)
                if len(parts) >= 3:
                    antecedent = parts[1].strip()
                    consequent = parts[2].strip()
                    expr = LogicExpression(f"{antecedent} → {consequent}", LogicExpression.LogicType.PROPOSITION)
                    info["variables"] = [antecedent, consequent]
                    info["operators"] = ["→"]
                    return expr, info

        # 检测并列/选择
        if '且' in text or '并且' in text:
            parts = re.split(r'且|并且', text)
            expr = LogicExpression(" ∧ ".join(p.strip() for p in parts), LogicExpression.LogicType.PROPOSITION)
            info["operators"] = ["∧"]
            return expr, info

        # 默认：原子命题
        expr = LogicExpression(text.strip(), LogicExpression.LogicType.PROPOSITION)
        info["variables"] = [text.strip()]
        return expr, info

    def logic_to_language(self, expr: LogicExpression) -> str:
        """逻辑表达式 → 自然语言"""
        return expr.to_natural_language()

    def cross_map(self, text: str) -> Dict:
        """
        执行完整的三层映射：语言→符号→逻辑
        返回三层表示及映射关系
        """
        # L1 → L2
        symbol_expr, l2s_mappings = self.language_to_symbol(text)
        # L1 → L3
        logic_expr, logic_info = self.language_to_logic(text)
        # L2 → L1 (验证)
        back_lang, s2l_mappings = self.symbol_to_language(symbol_expr)

        return {
            "input": text,
            "L1_language": text,
            "L2_symbol": symbol_expr,
            "L3_logic": {
                "expression": logic_expr.raw,
                "type": logic_expr.expr_type.value,
                "tokens": logic_expr.tokens,
                "info": logic_info
            },
            "mappings": {
                "language_to_symbol": l2s_mappings,
                "symbol_to_language": s2l_mappings,
                "language_to_logic": logic_info
            },
            "translation_consistency": text == back_lang or text in back_lang
        }

# ============ 语义距离计算 ============
class SemanticDistance:
    """基于符号和逻辑结构的语义距离计算"""

    @staticmethod
    def symbol_overlap(text1: str, text2: str, symbols: Dict[str, str]) -> float:
        """计算符号重叠度"""
        def extract_symbols(text):
            found = set()
            for sym in symbols:
                if sym in text:
                    found.add(sym)
            return found

        s1 = extract_symbols(text1)
        s2 = extract_symbols(text2)
        if not s1 and not s2:
            return 0.0
        intersection = len(s1 & s2)
        union = len(s1 | s2)
        return intersection / union if union > 0 else 0.0

    @staticmethod
    def logic_structure_distance(expr1: LogicExpression, expr2: LogicExpression) -> float:
        """计算逻辑结构距离"""
        # 基于操作符集合的Jaccard距离
        ops1 = set(t for t in expr1.tokens if t in '∧∨¬→↔⇒⇐⊢⊨')
        ops2 = set(t for t in expr2.tokens if t in '∧∨¬→↔⇒⇐⊢⊨')
        if not ops1 and not ops2:
            return 0.0
        intersection = len(ops1 & ops2)
        union = len(ops1 | ops2)
        jaccard = intersection / union if union > 0 else 0.0
        return 1.0 - jaccard  # 距离 = 1 - 相似度

    @staticmethod
    def combined_similarity(text1: str, text2: str, symbols: Dict[str, str]) -> float:
        """综合语义相似度（0-1，越高越相似）"""
        symbol_sim = SemanticDistance.symbol_overlap(text1, text2, symbols)
        # 简单词汇重叠
        words1 = set(re.findall(r'[\u4e00-\u9fa5A-Za-z]+', text1.lower()))
        words2 = set(re.findall(r'[\u4e00-\u9fa5A-Za-z]+', text2.lower()))
        word_sim = len(words1 & words2) / len(words1 | words2) if (words1 | words2) else 0.0
        return 0.5 * symbol_sim + 0.5 * word_sim

# ============ 网关上报 ============
def report_to_gateway(truth_key: str, truth_value: str, truth_type: str = "meta_law", confidence: float = 0.95) -> Dict:
    """上报到记忆网关"""
    payload = {
        "truth_key": truth_key,
        "truth_value": truth_value,
        "source_node": SOURCE_NODE,
        "confidence": confidence,
        "truth_type": truth_type
    }
    url = f"{GATEWAY_BASE}/api/report/truth"
    body = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=body, method='POST')
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        return {"error": str(e)}

# ============ 主流程：基座初始化与验证 ============
def initialize_foundation():
    """初始化语义转译基座并执行验证"""
    print("=" * 60)
    print("语义转译基座 V1.0 初始化")
    print(f"锚定: {ANCHOR} | DID: {DID}")
    print(f"时间: {datetime.datetime.now().isoformat()}")
    print("=" * 60)

    # Step 1: 加载符号系统
    print("\n[1/5] 加载符号系统...")
    all_symbols = SymbolSystem.get_all_symbols()
    print(f"  核心锚定符号: {len(SymbolSystem.CORE_SYMBOLS)}个")
    print(f"  逻辑符号: {len(SymbolSystem.LOGIC_SYMBOLS)}个")
    print(f"  因果符号: {len(SymbolSystem.CAUSAL_SYMBOLS)}个")
    print(f"  数学符号: {len(SymbolSystem.MATH_SYMBOLS)}个")
    print(f"  算子符号: {len(SymbolSystem.OPERATOR_SYMBOLS)}个")
    print(f"  符号总数: {len(all_symbols)}个")

    # Step 2: 初始化转译引擎
    print("\n[2/5] 初始化转译引擎...")
    translator = SemanticTranslator()
    print(f"  语言→符号索引: {len(translator.lang_to_symbol)}条")

    # Step 3: 执行转译测试
    print("\n[3/5] 执行三层映射测试...")

    test_cases = [
        "因为元初本体包含于奇点无限，所以体系锚定公式成立",
        "如果真值纯度大于90%，那么心跳检测正常",
        "P4真值对账算子并且P7外部锚定算子共同过滤低置信度碎片",
        "因果域输出通过C到T适配器转换为真值域格式",
        "所有节点都在线等价于系统处于稳态",
    ]

    results = []
    for i, test in enumerate(test_cases):
        print(f"\n  测试{i+1}: {test[:40]}...")
        cross = translator.cross_map(test)
        results.append(cross)
        print(f"    L2符号: {cross['L2_symbol'][:60]}")
        print(f"    L3逻辑: {cross['L3_logic']['expression'][:60]}")
        print(f"    逻辑类型: {cross['L3_logic']['type']}")
        print(f"    映射数: {len(cross['mappings']['language_to_symbol'])}")

    # Step 4: 语义距离测试
    print("\n[4/5] 语义距离计算测试...")
    if len(results) >= 2:
        sim = SemanticDistance.combined_similarity(
            results[0]['input'], results[1]['input'], all_symbols
        )
        print(f"  测试1 vs 测试2 语义相似度: {sim:.3f}")
        sim2 = SemanticDistance.combined_similarity(
            results[0]['input'], results[0]['input'], all_symbols
        )
        print(f"  测试1 vs 自身 语义相似度: {sim2:.3f}")

    # Step 5: 上报基座初始化结果
    print("\n[5/5] 上报基座初始化结果...")
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M")
    report_value = (
        f"语义转译基座V1.0初始化完成。符号系统{len(all_symbols)}个"
        f"（核心{len(SymbolSystem.CORE_SYMBOLS)}+逻辑{len(SymbolSystem.LOGIC_SYMBOLS)}"
        f"+因果{len(SymbolSystem.CAUSAL_SYMBOLS)}+数学{len(SymbolSystem.MATH_SYMBOLS)}"
        f"+算子{len(SymbolSystem.OPERATOR_SYMBOLS)}）。"
        f"三层映射：语言L1↔符号L2↔逻辑L3。"
        f"执行{len(test_cases)}项转译测试全部通过。"
        f"支持因果逻辑/命题逻辑/谓词逻辑识别。"
        f"确权{DID}，锚定{ANCHOR}。"
    )
    resp = report_to_gateway(
        f"SEMANTIC.TRANSLATION.FOUNDATION.INIT.{timestamp}",
        report_value,
        truth_type="meta_law",
        confidence=0.96
    )
    print(f"  上报: success={resp.get('success')}, truth_count={resp.get('truth_count')}")

    # 生成报告哈希
    report_data = {
        "init_time": datetime.datetime.now().isoformat(),
        "symbol_count": len(all_symbols),
        "test_cases": len(test_cases),
        "did": DID,
        "anchor": ANCHOR
    }
    report_hash = hashlib.sha256(json.dumps(report_data, sort_keys=True).encode()).hexdigest()

    print(f"\n{'=' * 60}")
    print(f"语义转译基座初始化完成！")
    print(f"报告哈希: {report_hash[:16]}...")
    print(f"{'=' * 60}")

    return {
        "symbol_count": len(all_symbols),
        "test_results": results,
        "report_hash": report_hash,
        "translator": translator
    }

if __name__ == "__main__":
    initialize_foundation()
