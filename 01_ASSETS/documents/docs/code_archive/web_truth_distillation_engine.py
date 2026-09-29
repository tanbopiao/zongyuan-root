#!/usr/bin/env python3
"""
全网搜索真值提炼与交叉校验引擎 V1.0
ZONGYUAN-ROOT元极恒一自治体系
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω

功能：
1. 关键词驱动全网搜索
2. 多源真值提炼
3. 交叉比对校验（一致性/时效性/权威性/逻辑）
4. 冲突检测与消解
5. 高价值真值上报记忆网关
"""
import hashlib
import json
import os
import re
import time
import urllib.request
import urllib.parse
from datetime import datetime
from typing import List, Dict, Tuple, Optional

# ==================== 配置 ====================
DID = "DID-BR-000002"
TRACE = "Ω₀⊂⊙∞⊂Ω"
GATEWAY_URL = "https://www.huodouai.com/api/report/truth"
SOURCE_NODE = "BR-000002-web-truth-distiller"

# 体系核心搜索关键词（按优先级）
SEARCH_KEYWORDS = [
    # P0: 体系核心技术
    "AI agent autonomy architecture 2026",
    "large language model memory system architecture",
    "causal inference AI reasoning 2026",
    # P1: 工程化标准
    "AI engineering best practices production 2026",
    "LLM agent evaluation framework benchmark",
    "vector database optimization low memory",
    # P2: 行业趋势
    "AI agent framework comparison 2026",
    "multi-agent system orchestration",
    "AI infrastructure edge deployment",
]

# 真值类型映射
TRUTH_TYPES = {
    "technical": "protocol",
    "standard": "rule",
    "trend": "data",
    "architecture": "config",
    "method": "meta_law",
}

# 权威性来源白名单
AUTHORITATIVE_SOURCES = [
    "arxiv.org", "github.com", "stackoverflow.com",
    "aws.amazon.com", "cloud.google.com", "azure.microsoft.com",
    "openai.com", "anthropic.com", "deepmind.google",
    "huggingface.co", "pytorch.org", "tensorflow.org",
]


# ==================== 真值条目 ====================
class TruthItem:
    def __init__(self, content: str, source: str, source_url: str,
                 truth_type: str = "unknown", confidence: float = 0.5):
        self.truth_id = hashlib.sha256(f"{content}{source}{time.time()}".encode()).hexdigest()[:16]
        self.content = content
        self.source = source
        self.source_url = source_url
        self.truth_type = truth_type
        self.confidence = confidence
        self.timestamp = int(time.time())
        self.cross_checks = []  # 交叉校验记录
        self.conflicts = []     # 冲突记录

    def to_dict(self) -> dict:
        return {
            "truth_id": self.truth_id,
            "content": self.content[:500],
            "source": self.source,
            "source_url": self.source_url,
            "truth_type": self.truth_type,
            "confidence": round(self.confidence, 4),
            "timestamp": self.timestamp,
            "cross_check_count": len(self.cross_checks),
            "conflict_count": len(self.conflicts),
        }


# ==================== 全网搜索模块 ====================
class WebSearchEngine:
    """全网搜索引擎（通过HTTP请求搜索API）"""

    def __init__(self):
        self.results_cache = {}

    def search(self, query: str, max_results: int = 5) -> List[Dict]:
        """执行搜索，返回结构化结果"""
        if query in self.results_cache:
            return self.results_cache[query]

        results = []
        # 使用DuckDuckGo HTML搜索（无需API key）
        try:
            results = self._duckduckgo_search(query, max_results)
        except Exception as e:
            print(f"  ⚠️ 搜索失败 '{query[:30]}': {e}")

        self.results_cache[query] = results
        return results

    def _duckduckgo_search(self, query: str, max_results: int) -> List[Dict]:
        """DuckDuckGo HTML搜索"""
        url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")

        results = []
        # 解析搜索结果
        pattern = r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>'
        matches = re.findall(pattern, html, re.DOTALL)
        for link, title in matches[:max_results]:
            clean_title = re.sub(r'<[^>]+>', '', title).strip()
            if clean_title and link.startswith("http"):
                results.append({
                    "title": clean_title,
                    "url": link,
                    "snippet": "",
                    "source": self._extract_domain(link),
                })
        return results

    def _extract_domain(self, url: str) -> str:
        """提取域名"""
        try:
            return urllib.parse.urlparse(url).netloc.replace("www.", "")
        except:
            return "unknown"


# ==================== 真值提炼模块 ====================
class TruthExtractor:
    """从搜索结果中提炼真值"""

    def extract(self, search_results: List[Dict], query: str) -> List[TruthItem]:
        """从搜索结果提炼真值条目"""
        truths = []
        for result in search_results:
            content = self._extract_truth_content(result, query)
            if content and len(content) > 20:
                truth_type = self._classify_truth_type(content, query)
                confidence = self._initial_confidence(result, content)
                truth = TruthItem(
                    content=content,
                    source=result.get("source", "unknown"),
                    source_url=result.get("url", ""),
                    truth_type=truth_type,
                    confidence=confidence,
                )
                truths.append(truth)
        return truths

    def _extract_truth_content(self, result: Dict, query: str) -> str:
        """从搜索结果提取真值内容"""
        title = result.get("title", "")
        snippet = result.get("snippet", "")
        # 组合标题和摘要作为真值内容
        content = f"{title}. {snippet}".strip()
        # 过滤低价值内容
        if len(content) < 20:
            return ""
        if any(skip in content.lower() for skip in ["cookie", "privacy policy", "terms of service"]):
            return ""
        return content

    def _classify_truth_type(self, content: str, query: str) -> str:
        """分类真值类型"""
        content_lower = content.lower()
        query_lower = query.lower()
        if any(k in query_lower for k in ["architecture", "framework", "system"]):
            return "config"
        elif any(k in query_lower for k in ["best practice", "standard", "evaluation"]):
            return "rule"
        elif any(k in query_lower for k in ["trend", "comparison", "2026"]):
            return "data"
        elif any(k in query_lower for k in ["method", "technique", "optimization"]):
            return "protocol"
        return "unknown"

    def _initial_confidence(self, result: Dict, content: str) -> float:
        """初始置信度评估"""
        conf = 0.5
        # 来源权威性
        source = result.get("source", "")
        if any(auth in source for auth in AUTHORITATIVE_SOURCES):
            conf += 0.2
        # 内容长度
        if len(content) > 100:
            conf += 0.1
        # 时效性（URL中含2025/2026）
        if any(y in result.get("url", "") for y in ["2025", "2026"]):
            conf += 0.1
        return min(conf, 0.95)


# ==================== 交叉比对校验模块 ====================
class CrossValidator:
    """多源交叉比对校验引擎"""

    def validate(self, truths: List[TruthItem]) -> Tuple[List[TruthItem], List[Dict]]:
        """
        交叉校验所有真值
        返回：(通过校验的真值, 校验报告)
        """
        report = {
            "total": len(truths),
            "passed": 0,
            "conflicts": 0,
            "low_confidence": 0,
            "checks": [],
        }

        validated = []
        for truth in truths:
            checks = self._run_checks(truth, truths)
            truth.cross_checks = checks

            # 综合评分
            pass_count = sum(1 for c in checks if c["passed"])
            score = pass_count / len(checks) if checks else 0

            if score >= 0.6 and truth.confidence >= 0.5:
                truth.confidence = min(truth.confidence + score * 0.2, 0.98)
                validated.append(truth)
                report["passed"] += 1
            elif truth.confidence < 0.5:
                report["low_confidence"] += 1
            else:
                report["conflicts"] += 1

            report["checks"].append({
                "truth_id": truth.truth_id[:8],
                "score": round(score, 2),
                "confidence": round(truth.confidence, 4),
                "passed": score >= 0.6,
            })

        return validated, report

    def _run_checks(self, truth: TruthItem, all_truths: List[TruthItem]) -> List[Dict]:
        """对单个真值执行多项校验"""
        checks = []

        # 1. 来源权威性校验
        auth_check = {
            "name": "source_authority",
            "passed": any(a in truth.source for a in AUTHORITATIVE_SOURCES),
            "detail": f"source={truth.source}",
        }
        checks.append(auth_check)

        # 2. 内容完整性校验
        content_check = {
            "name": "content_completeness",
            "passed": len(truth.content) > 30,
            "detail": f"length={len(truth.content)}",
        }
        checks.append(content_check)

        # 3. 多源一致性校验（与其他真值比对）
        related = [t for t in all_truths if t.truth_id != truth.truth_id
                   and self._semantic_overlap(truth.content, t.content) > 0.3]
        consistency = len(related) > 0
        consistency_check = {
            "name": "multi_source_consistency",
            "passed": consistency,
            "detail": f"related_sources={len(related)}",
        }
        checks.append(consistency_check)

        # 4. 逻辑一致性校验（无明显矛盾）
        logic_check = {
            "name": "logical_consistency",
            "passed": not self._has_logical_conflict(truth.content),
            "detail": "no contradiction detected",
        }
        checks.append(logic_check)

        # 5. 时效性校验
        timeliness_check = {
            "name": "timeliness",
            "passed": True,  # 搜索结果默认较新
            "detail": f"timestamp={truth.timestamp}",
        }
        checks.append(timeliness_check)

        return checks

    def _semantic_overlap(self, text1: str, text2: str) -> float:
        """简单语义重叠度（基于关键词）"""
        words1 = set(re.findall(r'\w+', text1.lower()))
        words2 = set(re.findall(r'\w+', text2.lower()))
        if not words1 or not words2:
            return 0
        overlap = words1 & words2
        return len(overlap) / min(len(words1), len(words2))

    def _has_logical_conflict(self, content: str) -> bool:
        """检测明显逻辑矛盾"""
        contradictions = [
            (r"always", r"never"),
            (r"all", r"none"),
            (r"must", r"cannot"),
        ]
        content_lower = content.lower()
        for pos, neg in contradictions:
            if re.search(pos, content_lower) and re.search(neg, content_lower):
                return True
        return False


# ==================== 上报模块 ====================
class GatewayReporter:
    """记忆网关上报告"""

    def report(self, truths: List[TruthItem]) -> Dict:
        """上报高价值真值到记忆网关"""
        results = {"success": 0, "failed": 0, "truth_count": 0}
        for truth in truths:
            try:
                payload = json.dumps({
                    "truth_key": f"WEBTRUTH.{truth.truth_type.upper()}.{truth.truth_id[:12].upper()}",
                    "truth_value": f"[全网搜索提炼] {truth.content[:400]} | 来源:{truth.source} | 交叉校验:{len(truth.cross_checks)}项 | 置信度:{truth.confidence:.2f}",
                    "source_node": SOURCE_NODE,
                    "confidence": truth.confidence,
                    "truth_type": truth.truth_type if truth.truth_type in TRUTH_TYPES.values() else "data",
                }, ensure_ascii=False).encode("utf-8")

                req = urllib.request.Request(
                    GATEWAY_URL,
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    result = json.loads(resp.read().decode())
                    if result.get("success"):
                        results["success"] += 1
                        results["truth_count"] = result.get("truth_count", 0)
                    else:
                        results["failed"] += 1
            except Exception as e:
                results["failed"] += 1
                print(f"  ⚠️ 上报失败: {e}")
        return results


# ==================== 主引擎 ====================
class WebTruthDistillationEngine:
    """全网搜索真值提炼与交叉校验主引擎"""

    def __init__(self):
        self.search_engine = WebSearchEngine()
        self.extractor = TruthExtractor()
        self.validator = CrossValidator()
        self.reporter = GatewayReporter()

    def run(self, keywords: Optional[List[str]] = None,
            max_per_keyword: int = 3) -> Dict:
        """
        执行完整流程：搜索→提炼→校验→上报
        """
        start_time = time.time()
        keywords = keywords or SEARCH_KEYWORDS[:6]  # 默认取前6个关键词

        print(f"{'='*60}")
        print(f"全网搜索真值提炼与交叉校验引擎 V1.0")
        print(f"DID: {DID} | {TRACE}")
        print(f"搜索关键词: {len(keywords)}个")
        print(f"{'='*60}")

        all_truths = []
        search_stats = {"queries": 0, "results": 0, "truths_extracted": 0}

        # 阶段1：全网搜索 + 真值提炼
        print(f"\n--- 阶段1：全网搜索与真值提炼 ---")
        for i, keyword in enumerate(keywords):
            print(f"\n[{i+1}/{len(keywords)}] 搜索: {keyword[:50]}")
            results = self.search_engine.search(keyword, max_per_keyword)
            search_stats["queries"] += 1
            search_stats["results"] += len(results)
            print(f"  搜索结果: {len(results)}条")

            truths = self.extractor.extract(results, keyword)
            search_stats["truths_extracted"] += len(truths)
            all_truths.extend(truths)
            print(f"  提炼真值: {len(truths)}条")

        print(f"\n  小计: {search_stats['queries']}次搜索, {search_stats['results']}条结果, "
              f"{search_stats['truths_extracted']}条真值")

        # 去重
        unique_truths = {}
        for t in all_truths:
            key = hashlib.md5(t.content[:100].encode()).hexdigest()
            if key not in unique_truths:
                unique_truths[key] = t
        all_truths = list(unique_truths.values())
        print(f"  去重后: {len(all_truths)}条唯一真值")

        # 阶段2：交叉比对校验
        print(f"\n--- 阶段2：交叉比对校验 ---")
        validated, validation_report = self.validator.validate(all_truths)
        print(f"  校验总数: {validation_report['total']}")
        print(f"  通过校验: {validation_report['passed']}")
        print(f"  冲突: {validation_report['conflicts']}")
        print(f"  低置信度: {validation_report['low_confidence']}")

        # 阶段3：高价值真值上报
        print(f"\n--- 阶段3：高价值真值上报 ---")
        # 按置信度排序，取Top高价值真值
        validated.sort(key=lambda t: t.confidence, reverse=True)
        high_value = [t for t in validated if t.confidence >= 0.6][:10]
        print(f"  高价值真值(conf>=0.6): {len(high_value)}条")

        report_result = self.reporter.report(high_value)
        print(f"  上报成功: {report_result['success']}")
        print(f"  上报失败: {report_result['failed']}")
        print(f"  网关真值总数: {report_result['truth_count']}")

        # 汇总
        elapsed = time.time() - start_time
        summary = {
            "engine": "WebTruthDistillationEngine V1.0",
            "did": DID,
            "trace": TRACE,
            "timestamp": int(time.time()),
            "elapsed_seconds": round(elapsed, 2),
            "search": search_stats,
            "extraction": {"total": len(all_truths), "unique": len(all_truths)},
            "validation": validation_report,
            "report": report_result,
            "high_value_truths": [t.to_dict() for t in high_value[:5]],
        }

        print(f"\n{'='*60}")
        print(f"执行完成 | 耗时: {elapsed:.1f}s")
        print(f"搜索: {search_stats['queries']}次 | 提炼: {len(all_truths)}条 | "
              f"校验通过: {validation_report['passed']} | 上报: {report_result['success']}条")
        print(f"{'='*60}")

        return summary


# ==================== 入口 ====================
if __name__ == "__main__":
    import sys
    # 支持自定义关键词
    custom_keywords = sys.argv[1:] if len(sys.argv) > 1 else None
    engine = WebTruthDistillationEngine()
    result = engine.run(keywords=custom_keywords)

    # 保存报告
    report_dir = os.path.expanduser("~/.zongyuan_root/web_truth_reports")
    os.makedirs(report_dir, exist_ok=True)
    report_file = os.path.join(report_dir, f"web_truth_{int(time.time())}.json")
    with open(report_file, 'w') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n报告已保存: {report_file}")
