"""
多模型能力提炼集成引擎 V1.0
横向基础能力组件，支持多模型API接入、高阶能力提炼、能力融合对齐、短板检测补齐。

确权：DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
"""

import json
import time
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field, asdict

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    import urllib.request
    import urllib.error


@dataclass
class ModelConfig:
    """模型配置"""
    model_id: str
    model_name: str
    provider: str  # zhipu/doubao/deepseek/qwen/volcengine
    api_base: str
    api_key: str = ""
    api_key_env: str = ""  # 从环境变量读取的key名
    model_name_api: str = ""  # API调用时的模型名
    max_tokens: int = 4096
    temperature: float = 0.7
    capabilities: List[str] = field(default_factory=list)  # 支持的能力
    cost_per_1k_tokens: float = 0.0  # 每千token成本
    rate_limit: int = 60  # 每分钟请求数
    enabled: bool = True


@dataclass
class Capability:
    """能力条目"""
    capability_id: str
    capability_name: str
    capability_type: str  # reasoning/creative/analysis/planning/coding/multimodal/domain/meta
    source_model: str
    description: str
    confidence: float = 0.8
    extracted_at: str = field(default_factory=lambda: datetime.now().isoformat())
    test_results: Dict = field(default_factory=dict)
    metadata: Dict = field(default_factory=dict)


@dataclass
class CapabilityFusion:
    """能力融合结果"""
    fusion_id: str
    fusion_name: str
    fusion_strategy: str  # weighted/specialty_routing/cascade/complementary/consensus
    source_capabilities: List[str]
    description: str
    confidence: float = 0.85
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class MultiModelCapabilityEngine:
    """多模型能力提炼集成引擎"""

    # 八大高阶能力类型
    CAPABILITY_TYPES = {
        "reasoning": "推理能力",
        "creative": "创作能力",
        "analysis": "分析能力",
        "planning": "规划能力",
        "coding": "编码能力",
        "multimodal": "多模态能力",
        "domain": "领域能力",
        "meta": "元能力",
    }

    # 能力探针测试提示词
    CAPABILITY_PROBES = {
        "reasoning": "请解决以下逻辑推理问题：有A、B、C三人，A说B在说谎，B说C在说谎，C说A和B都在说谎。请问谁在说真话？请给出推理过程。",
        "creative": "请以\"量子花园\"为题，写一首现代诗，要求包含至少3个科学意象和2个情感意象。",
        "analysis": "请分析以下数据趋势：某产品1月销量100，2月150，3月120，4月200，5月180，6月250。请分析增长趋势、波动原因和未来预测。",
        "planning": "请为一个从零开始的个人博客项目制定3个月的详细计划，包括技术选型、功能开发、内容运营和推广策略。",
        "coding": "请用Python实现一个快速排序算法，并给出时间复杂度分析和测试用例。",
        "multimodal": "请描述如何将一张风景图片转换为文字描述，再将文字描述转换为音乐，需要哪些技术步骤。",
        "domain": "请解释机器学习中的过拟合现象，包括原因、检测方法和5种解决方案。",
        "meta": "请反思你自己的回答过程：你是如何理解问题、组织答案、检查错误的？请给出元认知分析。",
    }

    def __init__(self, config: Dict = None):
        """
        初始化多模型能力引擎

        Args:
            config: 配置字典
        """
        self.config = config or {}
        self.models: Dict[str, ModelConfig] = {}
        self.capabilities: Dict[str, Capability] = {}
        self.fusions: Dict[str, CapabilityFusion] = {}
        self._call_count = 0
        self._extract_count = 0
        self._fusion_count = 0

        # 注册默认模型配置
        self._register_default_models()

    def _register_default_models(self):
        """注册默认模型配置"""
        default_models = [
            ModelConfig(
                model_id="zhipu-glm",
                model_name="智谱GLM",
                provider="zhipu",
                api_base="https://open.bigmodel.cn/api/paas/v4",
                api_key_env="ZHIPU_API_KEY",
                model_name_api="glm-4",
                capabilities=["reasoning", "creative", "analysis", "coding", "domain"],
                cost_per_1k_tokens=0.01,
            ),
            ModelConfig(
                model_id="doubao",
                model_name="豆包",
                provider="doubao",
                api_base="https://ark.cn-beijing.volces.com/api/v3",
                api_key_env="DOUBAO_API_KEY",
                model_name_api="doubao-pro",
                capabilities=["reasoning", "creative", "analysis", "coding", "multimodal"],
                cost_per_1k_tokens=0.008,
            ),
            ModelConfig(
                model_id="deepseek",
                model_name="DeepSeek",
                provider="deepseek",
                api_base="https://api.deepseek.com",
                api_key_env="DEEPSEEK_API_KEY",
                model_name_api="deepseek-chat",
                capabilities=["reasoning", "coding", "analysis"],
                cost_per_1k_tokens=0.001,
            ),
            ModelConfig(
                model_id="qwen",
                model_name="通义千问",
                provider="qwen",
                api_base="https://dashscope.aliyuncs.com/compatible-mode/v1",
                api_key_env="QWEN_API_KEY",
                model_name_api="qwen-plus",
                capabilities=["reasoning", "creative", "analysis", "coding", "multimodal", "domain"],
                cost_per_1k_tokens=0.004,
            ),
        ]

        for model in default_models:
            self.models[model.model_id] = model

    def register_model(self, model_config: ModelConfig) -> bool:
        """
        注册新模型

        Args:
            model_config: 模型配置

        Returns:
            是否注册成功
        """
        if model_config.model_id in self.models:
            return False
        self.models[model_config.model_id] = model_config
        return True

    def get_model(self, model_id: str) -> Optional[ModelConfig]:
        """获取模型配置"""
        return self.models.get(model_id)

    def list_models(self, enabled_only: bool = True) -> List[Dict]:
        """列出所有模型"""
        models = []
        for model in self.models.values():
            if enabled_only and not model.enabled:
                continue
            models.append({
                "model_id": model.model_id,
                "model_name": model.model_name,
                "provider": model.provider,
                "capabilities": model.capabilities,
                "enabled": model.enabled,
                "api_key_configured": bool(model.api_key or self._get_api_key(model)),
            })
        return models

    def call_model(self, model_id: str, prompt: str,
                   system_prompt: str = None, **kwargs) -> Dict:
        """
        调用指定模型

        Args:
            model_id: 模型ID
            prompt: 用户提示词
            system_prompt: 系统提示词
            **kwargs: 其他参数

        Returns:
            调用结果字典
        """
        model = self.get_model(model_id)
        if not model:
            return {"success": False, "error": f"模型不存在: {model_id}"}

        if not model.enabled:
            return {"success": False, "error": f"模型未启用: {model_id}"}

        api_key = self._get_api_key(model)
        if not api_key:
            return {
                "success": False,
                "error": f"API Key未配置: {model_id} (环境变量: {model.api_key_env})",
            }

        start_time = time.time()
        try:
            # 构建请求
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            payload = {
                "model": model.model_name_api or model.model_id,
                "messages": messages,
                "max_tokens": kwargs.get("max_tokens", model.max_tokens),
                "temperature": kwargs.get("temperature", model.temperature),
            }

            # 发送请求
            response = self._http_post(
                f"{model.api_base}/chat/completions",
                payload,
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=kwargs.get("timeout", 30),
            )

            # 解析响应
            content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
            usage = response.get("usage", {})

            self._call_count += 1

            return {
                "success": True,
                "model_id": model_id,
                "content": content,
                "usage": usage,
                "elapsed_ms": (time.time() - start_time) * 1000,
                "raw_response": response,
            }

        except Exception as e:
            return {
                "success": False,
                "model_id": model_id,
                "error": str(e),
                "elapsed_ms": (time.time() - start_time) * 1000,
            }

    def extract_capability(self, model_id: str,
                           capability_type: str) -> Dict:
        """
        提炼指定模型的高阶能力

        Args:
            model_id: 模型ID
            capability_type: 能力类型

        Returns:
            能力提炼结果
        """
        if capability_type not in self.CAPABILITY_TYPES:
            return {"success": False, "error": f"未知能力类型: {capability_type}"}

        model = self.get_model(model_id)
        if not model:
            return {"success": False, "error": f"模型不存在: {model_id}"}

        # 检查模型是否支持该能力
        if capability_type not in model.capabilities:
            return {
                "success": False,
                "error": f"模型 {model_id} 不支持能力 {capability_type}",
            }

        # 使用能力探针测试
        probe_prompt = self.CAPABILITY_PROBES.get(capability_type, "请展示你的能力。")
        system_prompt = f"你是{model.model_name}，请展示你在{self.CAPABILITY_TYPES[capability_type]}方面的能力。"

        result = self.call_model(model_id, probe_prompt, system_prompt)

        if not result.get("success"):
            return {
                "success": False,
                "error": f"能力探针测试失败: {result.get('error')}",
            }

        # 评估能力表现
        content = result.get("content", "")
        capability_score = self._evaluate_capability_response(content, capability_type)

        # 创建能力条目
        capability_id = f"CAP-{model_id}-{capability_type}-{datetime.now().strftime('%Y%m%d')}"
        capability = Capability(
            capability_id=capability_id,
            capability_name=f"{model.model_name}的{self.CAPABILITY_TYPES[capability_type]}",
            capability_type=capability_type,
            source_model=model_id,
            description=f"从{model.model_name}提炼的{self.CAPABILITY_TYPES[capability_type]}，探针测试得分{capability_score}/100",
            confidence=capability_score / 100,
            test_results={
                "probe_score": capability_score,
                "probe_response_length": len(content),
                "elapsed_ms": result.get("elapsed_ms", 0),
            },
        )

        self.capabilities[capability_id] = capability
        self._extract_count += 1

        return {
            "success": True,
            "capability": asdict(capability),
            "probe_response": content[:500],
            "score": capability_score,
        }

    def extract_all_capabilities(self, model_id: str) -> Dict:
        """提炼模型的所有支持能力"""
        model = self.get_model(model_id)
        if not model:
            return {"success": False, "error": f"模型不存在: {model_id}"}

        results = []
        for cap_type in model.capabilities:
            result = self.extract_capability(model_id, cap_type)
            results.append({
                "capability_type": cap_type,
                "success": result.get("success"),
                "score": result.get("score", 0),
                "error": result.get("error"),
            })

        return {
            "success": True,
            "model_id": model_id,
            "results": results,
            "total_extracted": sum(1 for r in results if r["success"]),
        }

    def fuse_capabilities(self, capability_ids: List[str],
                           strategy: str = "weighted",
                           fusion_name: str = None) -> Dict:
        """
        融合多个能力

        Args:
            capability_ids: 能力ID列表
            strategy: 融合策略（weighted/specialty_routing/cascade/complementary/consensus）
            fusion_name: 融合名称

        Returns:
            融合结果
        """
        if len(capability_ids) < 2:
            return {"success": False, "error": "至少需要2个能力进行融合"}

        # 验证能力存在
        capabilities = []
        for cid in capability_ids:
            cap = self.capabilities.get(cid)
            if not cap:
                return {"success": False, "error": f"能力不存在: {cid}"}
            capabilities.append(cap)

        # 计算融合置信度（加权平均）
        total_confidence = sum(c.confidence for c in capabilities)
        avg_confidence = total_confidence / len(capabilities)

        # 创建融合结果
        fusion_id = f"FUSION-{strategy}-{hashlib.md5(','.join(capability_ids).encode()).hexdigest()[:8]}"
        fusion = CapabilityFusion(
            fusion_id=fusion_id,
            fusion_name=fusion_name or f"{strategy}融合-{len(capabilities)}能力",
            fusion_strategy=strategy,
            source_capabilities=capability_ids,
            description=f"使用{strategy}策略融合{len(capabilities)}个能力，平均置信度{avg_confidence:.2f}",
            confidence=min(avg_confidence * 1.1, 1.0),  # 融合后置信度略有提升
        )

        self.fusions[fusion_id] = fusion
        self._fusion_count += 1

        return {
            "success": True,
            "fusion": asdict(fusion),
            "strategy_description": self._get_strategy_description(strategy),
        }

    def detect_shortages(self) -> Dict:
        """
        检测能力短板

        Returns:
            短板检测结果
        """
        # 统计各能力类型的覆盖情况
        type_coverage = {}
        for cap_type in self.CAPABILITY_TYPES:
            type_coverage[cap_type] = {
                "name": self.CAPABILITY_TYPES[cap_type],
                "capability_count": 0,
                "model_count": set(),
                "avg_confidence": 0.0,
                "max_confidence": 0.0,
            }

        for cap in self.capabilities.values():
            if cap.capability_type in type_coverage:
                coverage = type_coverage[cap.capability_type]
                coverage["capability_count"] += 1
                coverage["model_count"].add(cap.source_model)
                coverage["avg_confidence"] += cap.confidence
                coverage["max_confidence"] = max(coverage["max_confidence"], cap.confidence)

        # 计算平均值和识别短板
        shortages = []
        for cap_type, coverage in type_coverage.items():
            if coverage["capability_count"] > 0:
                coverage["avg_confidence"] /= coverage["capability_count"]
                coverage["model_count"] = len(coverage["model_count"])
            else:
                coverage["model_count"] = 0

            # 判断是否为短板
            is_shortage = False
            shortage_reason = ""

            if coverage["capability_count"] == 0:
                is_shortage = True
                shortage_reason = "无任何能力覆盖"
            elif coverage["model_count"] < 2:
                is_shortage = True
                shortage_reason = "仅1个模型覆盖，缺乏冗余"
            elif coverage["avg_confidence"] < 0.6:
                is_shortage = True
                shortage_reason = f"平均置信度低（{coverage['avg_confidence']:.2f}）"

            if is_shortage:
                shortages.append({
                    "capability_type": cap_type,
                    "name": coverage["name"],
                    "reason": shortage_reason,
                    "current_state": {
                        "capability_count": coverage["capability_count"],
                        "model_count": coverage["model_count"],
                        "avg_confidence": round(coverage["avg_confidence"], 2),
                    },
                    "suggestion": self._get_shortage_suggestion(cap_type),
                })

        return {
            "success": True,
            "coverage": type_coverage,
            "shortages": shortages,
            "shortage_count": len(shortages),
            "total_capabilities": len(self.capabilities),
            "total_fusions": len(self.fusions),
        }

    def _evaluate_capability_response(self, content: str,
                                       capability_type: str) -> float:
        """评估能力探针响应质量（简单评分）"""
        score = 50.0  # 基础分

        # 长度评分（200-2000字最佳）
        length = len(content)
        if 200 <= length <= 2000:
            score += 20
        elif 100 <= length < 200 or 2000 < length <= 5000:
            score += 10

        # 结构评分（包含列表/编号/分段）
        if any(marker in content for marker in ['1.', '2.', '3.', '•', '- ', '步骤', '首先', '其次']):
            score += 15

        # 内容深度评分（包含具体数字/代码/公式）
        if any(marker in content for marker in ['%', '代码', '公式', '算法', '具体', '例如']):
            score += 15

        return min(score, 100.0)

    def _get_strategy_description(self, strategy: str) -> str:
        """获取融合策略描述"""
        descriptions = {
            "weighted": "加权融合：按各能力置信度加权，置信度高的能力贡献更大",
            "specialty_routing": "专长路由：根据任务类型自动路由到最擅长的模型",
            "cascade": "级联推理：简单模型先处理，复杂问题升级到更强模型",
            "complementary": "互补协作：各模型处理自己擅长的部分，结果合并",
            "consensus": "共识达成：多模型独立回答，取多数一致的结果",
        }
        return descriptions.get(strategy, "未知策略")

    def _get_shortage_suggestion(self, capability_type: str) -> str:
        """获取短板补齐建议"""
        suggestions = {
            "reasoning": "接入更多推理能力强的模型（如DeepSeek-R1），或使用思维链提示增强",
            "creative": "接入创作能力强的模型，或使用风格提示词增强创作能力",
            "analysis": "接入数据分析工具，或使用分析框架提示词增强",
            "planning": "使用规划框架（如ReAct）增强，或接入专门的规划模型",
            "coding": "接入代码生成模型（如CodeLlama），或使用代码审查工具增强",
            "multimodal": "接入多模态模型（如GPT-4V），或使用图像理解工具",
            "domain": "接入领域专用模型，或使用领域知识库检索增强",
            "meta": "使用元认知提示词增强，或接入反思能力强的模型",
        }
        return suggestions.get(capability_type, "建议接入更多模型或使用提示工程增强")

    def _get_api_key(self, model: ModelConfig) -> str:
        """获取模型API Key（优先直接配置，其次环境变量）"""
        if model.api_key:
            return model.api_key
        if model.api_key_env:
            return os.environ.get(model.api_key_env, "")
        return ""

    def _http_post(self, url: str, payload: Dict,
                    headers: Dict = None, timeout: int = 30) -> Dict:
        """HTTP POST请求"""
        if headers is None:
            headers = {}
        headers["Content-Type"] = "application/json"

        if HAS_REQUESTS:
            response = requests.post(url, json=payload, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response.json()
        else:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))

    def get_stats(self) -> Dict:
        """获取引擎统计"""
        return {
            "registered_models": len(self.models),
            "enabled_models": sum(1 for m in self.models.values() if m.enabled),
            "api_key_configured": sum(1 for m in self.models.values() if self._get_api_key(m)),
            "extracted_capabilities": len(self.capabilities),
            "fusions": len(self.fusions),
            "total_calls": self._call_count,
            "total_extractions": self._extract_count,
            "total_fusions": self._fusion_count,
            "status": "running",
        }


# 导入os（用于环境变量）
import os
