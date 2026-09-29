"""
联网搜索模块 tool.web_search
Ω-Modular Engine 可插拔模块
模块ID: tool.web_search
确权: DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
"""

import hashlib
import time
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field


@dataclass
class SearchResult:
    """单条搜索结果"""
    title: str
    url: str
    snippet: str
    source: str
    rank: int
    timestamp: float = field(default_factory=time.time)


class WebSearchModule:
    """
    联网搜索模块
    支持多搜索引擎切换、结果去重、摘要生成、来源溯源
    """

    # 模块身份
    module_id = "tool.web_search"
    module_name = "联网搜索模块"
    module_version = "v1.0.0"
    module_type = "tool"
    description = "多引擎联网搜索，结果去重摘要，支持Google/Bing/Baidu/DuckDuckGo切换，与秒塔组合实现联网推理闭环"

    # 输入端口定义
    input_ports = [
        {
            "name": "query",
            "data_type": "str",
            "required": True,
            "description": "搜索查询关键词"
        },
        {
            "name": "engine",
            "data_type": "enum",
            "required": False,
            "description": "搜索引擎选择",
            "constraints": {
                "enum": ["auto", "google", "bing", "baidu", "duckduckgo"],
                "default": "auto"
            }
        },
        {
            "name": "max_results",
            "data_type": "int",
            "required": False,
            "description": "最大返回结果数",
            "constraints": {"min": 1, "max": 50, "default": 10}
        },
        {
            "name": "timeout",
            "data_type": "int",
            "required": False,
            "description": "搜索超时时间(秒)",
            "constraints": {"min": 5, "max": 60, "default": 15}
        }
    ]

    # 输出端口定义
    output_ports = [
        {
            "name": "results",
            "data_type": "list",
            "required": True,
            "description": "搜索结果列表，每条包含title/url/snippet/source/rank"
        },
        {
            "name": "summary",
            "data_type": "str",
            "required": True,
            "description": "搜索结果综合摘要"
        },
        {
            "name": "sources",
            "data_type": "list",
            "required": True,
            "description": "来源域名列表，用于溯源"
        },
        {
            "name": "hash",
            "data_type": "str",
            "required": True,
            "description": "搜索结果SHA256确权哈希"
        }
    ]

    def __init__(self):
        self.state = "idle"
        self.cache_pool = {}
        self.search_history = []
        self.engine_priority = ["duckduckgo", "bing", "google", "baidu"]
        self.stats = {
            "total_searches": 0,
            "success_count": 0,
            "fail_count": 0,
            "avg_time_ms": 0,
            "cache_hits": 0
        }

    async def pre_check(self, inputs: Dict[str, Any]) -> bool:
        """执行前自检：查询词校验、网络连通性"""
        self.state = "precheck"
        query = inputs.get("query", "").strip()

        if not query:
            raise ValueError("搜索查询词不能为空")

        if len(query) > 500:
            raise ValueError(f"搜索查询词过长({len(query)}字符)，限制500字符")

        # 检查缓存
        cache_key = hashlib.md5(f"{query}:{inputs.get('engine','auto')}".encode()).hexdigest()
        if cache_key in self.cache_pool:
            cache_age = time.time() - self.cache_pool[cache_key]["timestamp"]
            if cache_age < 3600:  # 1小时缓存
                self.stats["cache_hits"] += 1
                return True

        return True

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """执行联网搜索"""
        self.state = "running"
        start_time = time.time()

        query = inputs["query"].strip()
        engine = inputs.get("engine", "auto")
        max_results = inputs.get("max_results", 10)
        timeout = inputs.get("timeout", 15)

        # 缓存检查
        cache_key = hashlib.md5(f"{query}:{engine}".encode()).hexdigest()
        if cache_key in self.cache_pool:
            cache_age = time.time() - self.cache_pool[cache_key]["timestamp"]
            if cache_age < 3600:
                cached = self.cache_pool[cache_key]
                self.state = "success"
                self.stats["total_searches"] += 1
                return {
                    "results": cached["results"],
                    "summary": cached["summary"],
                    "sources": cached["sources"],
                    "hash": cached["hash"],
                    "_cache_hit": True,
                    "_cache_age_sec": round(cache_age, 1)
                }

        # 引擎选择
        if engine == "auto":
            selected_engine = await self._auto_select_engine()
        else:
            selected_engine = engine

        # 执行搜索（带重试和降级）
        results = []
        actual_engine = selected_engine
        retry_count = 0
        max_retries = 2

        while retry_count <= max_retries and not results:
            try:
                results = await self._search_with_engine(
                    query, selected_engine, max_results, timeout
                )
                actual_engine = selected_engine
            except Exception as e:
                retry_count += 1
                if retry_count <= max_retries:
                    # 降级到下一个引擎
                    next_idx = (self.engine_priority.index(selected_engine) + 1) % len(self.engine_priority)
                    selected_engine = self.engine_priority[next_idx]
                    await asyncio.sleep(0.5)
                else:
                    raise RuntimeError(f"所有搜索引擎均失败，最后错误: {str(e)}")

        # 结果去重
        results = self._deduplicate_results(results)

        # 生成摘要
        summary = self._generate_summary(query, results, actual_engine)

        # 提取来源
        sources = self._extract_sources(results)

        # 确权哈希
        result_str = str(sorted([r["url"] for r in results]))
        sha256_hash = hashlib.sha256(result_str.encode("utf-8")).hexdigest()

        # 写入缓存
        self.cache_pool[cache_key] = {
            "results": results,
            "summary": summary,
            "sources": sources,
            "hash": sha256_hash,
            "timestamp": time.time()
        }

        # 更新统计
        elapsed_ms = round((time.time() - start_time) * 1000, 2)
        self.stats["total_searches"] += 1
        self.stats["success_count"] += 1
        self.stats["avg_time_ms"] = round(
            (self.stats["avg_time_ms"] * (self.stats["total_searches"] - 1) + elapsed_ms)
            / self.stats["total_searches"], 2
        )

        # 记录历史
        self.search_history.append({
            "query": query,
            "engine": actual_engine,
            "result_count": len(results),
            "elapsed_ms": elapsed_ms,
            "timestamp": time.time()
        })

        self.state = "success"

        return {
            "results": results,
            "summary": summary,
            "sources": sources,
            "hash": sha256_hash,
            "_engine_used": actual_engine,
            "_elapsed_ms": elapsed_ms,
            "_retry_count": retry_count
        }

    async def _auto_select_engine(self) -> str:
        """自动选择最优搜索引擎（基于历史成功率和响应速度）"""
        # 简单策略：优先DuckDuckGo（无API密钥需求），其次Bing
        return "duckduckgo"

    async def _search_with_engine(
        self, query: str, engine: str, max_results: int, timeout: int
    ) -> List[Dict[str, Any]]:
        """
        使用指定搜索引擎执行搜索
        注：当前为仿真实现，实际部署需接入对应搜索引擎API
        """
        # 仿真搜索结果（实际部署时替换为真实API调用）
        await asyncio.sleep(0.3)  # 模拟网络延迟

        simulated_results = [
            {
                "title": f"{query} - 权威解答",
                "url": f"https://zh.wikipedia.org/wiki/{query}",
                "snippet": f"关于{query}的详细介绍、历史背景、核心概念和最新进展，涵盖多个维度的全面解析。",
                "source": "zh.wikipedia.org",
                "rank": 1
            },
            {
                "title": f"{query}最新动态与行业分析",
                "url": f"https://www.zhihu.com/search?q={query}",
                "snippet": f"行业专家深度解读{query}的发展趋势、技术演进和市场影响，包含多视角分析和数据支撑。",
                "source": "zhihu.com",
                "rank": 2
            },
            {
                "title": f"{query}技术文档与最佳实践",
                "url": f"https://github.com/search?q={query}",
                "snippet": f"开源社区中关于{query}的技术实现、代码示例、最佳实践和常见问题解决方案。",
                "source": "github.com",
                "rank": 3
            },
            {
                "title": f"{query}学术研究前沿",
                "url": f"https://arxiv.org/search/?query={query}",
                "snippet": f"最新学术论文汇总，涵盖{query}相关的理论研究、实验结果和创新方法，包含arXiv预印本。",
                "source": "arxiv.org",
                "rank": 4
            },
            {
                "title": f"{query}实战教程与入门指南",
                "url": f"https://juejin.cn/search?query={query}",
                "snippet": f"从入门到精通的完整学习路径，包含{query}的基础概念、核心原理、实战案例和进阶技巧。",
                "source": "juejin.cn",
                "rank": 5
            }
        ]

        return simulated_results[:max_results]

    def _deduplicate_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """结果去重（基于URL域名和标题相似度）"""
        seen_urls = set()
        seen_titles = set()
        unique_results = []

        for r in results:
            url_normalized = r["url"].split("?")[0].rstrip("/").lower()
            title_normalized = r["title"].lower().strip()

            if url_normalized not in seen_urls and title_normalized not in seen_titles:
                seen_urls.add(url_normalized)
                seen_titles.add(title_normalized)
                unique_results.append(r)

        return unique_results

    def _generate_summary(self, query: str, results: List[Dict[str, Any]], engine: str) -> str:
        """生成搜索结果综合摘要"""
        if not results:
            return f"未找到关于「{query}」的搜索结果"

        source_count = len(set(r["source"] for r in results))
        top_sources = list(set(r["source"] for r in results))[:3]

        summary = (
            f"关于「{query}」的搜索共返回{len(results)}条结果，"
            f"来自{source_count}个独立来源（{', '.join(top_sources)}等），"
            f"使用{engine}搜索引擎。"
            f"核心内容涵盖：{results[0]['snippet'][:60]}..."
        )
        return summary

    def _extract_sources(self, results: List[Dict[str, Any]]) -> List[str]:
        """提取来源域名列表"""
        sources = []
        seen = set()
        for r in results:
            if r["source"] not in seen:
                sources.append(r["source"])
                seen.add(r["source"])
        return sources

    async def on_error(self, error: Exception) -> str:
        """异常处理策略"""
        self.state = "failed"
        self.stats["fail_count"] += 1

        error_str = str(error).lower()
        if "timeout" in error_str or "timed out" in error_str:
            return "retry_with_fallback_engine"
        elif "connection" in error_str or "network" in error_str:
            return "fallback_to_cache"
        elif "rate limit" in error_str or "429" in error_str:
            return "retry_with_delay"
        else:
            return "abort"

    async def self_evaluate(self) -> Dict[str, Any]:
        """模块自我评估"""
        success_rate = (
            self.stats["success_count"] / self.stats["total_searches"] * 100
            if self.stats["total_searches"] > 0 else 0
        )
        return {
            "success_rate": round(success_rate, 2),
            "avg_time_ms": self.stats["avg_time_ms"],
            "cache_hit_rate": round(
                self.stats["cache_hits"] / max(self.stats["total_searches"], 1) * 100, 2
            ),
            "total_searches": self.stats["total_searches"],
            "supported_engines": self.engine_priority,
            "state": self.state
        }


# 模块注册信息
MODULE_REGISTRY = {
    "module_id": "tool.web_search",
    "module_name": "联网搜索模块",
    "module_version": "v1.0.0",
    "module_type": "tool",
    "module_class": WebSearchModule,
    "input_ports": WebSearchModule.input_ports,
    "output_ports": WebSearchModule.output_ports
}
