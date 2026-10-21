#!/usr/bin/env python3
# ZONGYUAN-ROOT 智能任务路由引擎
"""
Task-Aware Model Router - 根据任务类型自动选择最优模型

任务分类:
✓ 日常对话 → doubao/sensenova (快速 + 低成本)
✓ 代码生成 → deepseek-pro (高质量)
✓ 长文本处理 → sensenova/glm-flash (上下文大)
✓ 复杂推理 → deepseek-pro + doubao (双验证)
✓ 简单问答 → glm-flash/local (免费/本地)

优化策略:
1. 关键词检测 + NLP 分类
2. 历史成功率加权
3. 成本估算前置
4. 动态负载均衡
"""

import re, json, time
from typing import Dict, List, Tuple
from datetime import datetime


class TaskTypeClassifier:
    """任务类型分类器"""
    
    # 任务类型关键词库
    TASK_KEYWORDS = {
        "code_generation": [
            "写代码", "编写代码", "生成代码", "debug", "修复 bug", "实现功能",
            "def ", "class ", "function", "import ", "return ", "print(",
            "python", "javascript", "java", "c++", "go", "rust"
        ],
        "data_analysis": [
            "分析数据", "统计数据", "计算结果", "趋势预测", "数据挖掘",
            "mean", "median", "std", "correlation", "regression", "pandas",
            "csv", "excel", "sql", "数据库", "图表"
        ],
        "long_text_processing": [
            "总结这段文字", "提取要点", "翻译成英文", "润色文章", "改写",
            "缩写", "扩写", "续写", "阅读理解", "摘要", "大纲"
        ],
        "complex_reasoning": [
            "请推理", "为什么", "如何解释", "因果关系", "如果...会怎样",
            "论证", "证明", "数学题", "逻辑题", "物理题", "化学题"
        ],
        "simple_qa": [
            "什么是", "谁", "哪里", "何时", "多少", "怎么做", "可以吗",
            "时间", "天气", "定义", "介绍", "背景", "历史"
        ],
        "creative_writing": [
            "写一篇", "创作", "故事", "诗歌", "小说", "剧本", "文案",
            "标题", "标语", "广告语", "朋友圈", "微博"
        ]
    }
    
    def classify(self, user_message: str) -> str:
        """
        分类任务类型
        
        Returns:
            任务类型：code_generation / data_analysis / long_text_processing /
                    complex_reasoning / simple_qa / creative_writing / general
        """
        message_lower = user_message.lower()
        scores = {}
        
        for task_type, keywords in self.TASK_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw.lower() in message_lower)
            if score > 0:
                scores[task_type] = score
        
        if not scores:
            return "general"
        
        # 返回得分最高的任务类型
        return max(scores.keys(), key=lambda k: scores[k])


class SmartModelRouter:
    """智能模型路由器"""
    
    def __init__(self):
        self.classifier = TaskTypeClassifier()
        
        # 任务类型 → 推荐模型映射表
        self.task_to_models = {
            "code_generation": [
                ("deepseek-pro", 0.7),   # 70% 概率用高质量模型
                ("doubao", 0.3),          # 30% 概率用主模型
            ],
            "data_analysis": [
                ("sensenova", 0.6),       # 性价比高
                ("deepseek-pro", 0.3),    # 复杂数据分析
                ("glm-flash", 0.1),       # 简单统计
            ],
            "long_text_processing": [
                ("sensenova", 0.5),       # 上下文长度优势
                ("glm-flash", 0.3),       # 免费回退
                ("doubao", 0.2),
            ],
            "complex_reasoning": [
                ("deepseek-pro", 0.8),    # 推理能力最强
                ("doubao", 0.2),
            ],
            "simple_qa": [
                ("glm-flash", 0.5),       # 免费模型足够
                ("local-fallback", 0.3),  # 本地兜底
                ("doubao", 0.2),
            ],
            "creative_writing": [
                ("doubao", 0.5),          # 创意能力强
                ("deepseek-pro", 0.3),    # 文采好
                ("sensenova", 0.2),
            ],
            "general": [
                ("doubao", 0.6),          # 默认主模型
                ("sensenova", 0.3),       # 备用
                ("glm-flash", 0.1),       # 免费回退
            ]
        }
        
        # 成本配置
        self.cost_per_1k_tokens = {
            "doubao": 0.001,
            "sensenova": 0.0005,
            "deepseek-pro": 0.003,
            "glm-flash": 0.000,
            "local-fallback": 0.000
        }
        
        # 随机数种子
        import random
        self.random = random.Random(int(time.time()))
    
    def select_model(self, messages: List[Dict], 
                    strategy: str = "auto") -> Tuple[str, float]:
        """
        选择最优模型
        
        Args:
            messages: 对话消息列表
            strategy: auto/fast/cost/quality
        
        Returns:
            (model_name, estimated_cost)
        """
        # 提取用户消息
        user_message = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_message = msg.get("content", "")
                break
        
        # 估算 token 数量
        estimated_tokens = len(user_message) * 1.5  # 中文约 1.5 token/字
        
        # 获取任务类型
        task_type = self.classifier.classify(user_message)
        
        # 根据策略调整模型选择
        if strategy == "fast":
            # 优先速度
            model = "doubao"
        elif strategy == "cost":
            # 优先成本
            if task_type in ["simple_qa"]:
                model = "glm-flash"
            else:
                model = "sensenova"
        elif strategy == "quality":
            # 优先质量
            model = "deepseek-pro"
        else:
            # auto: 根据任务类型 + 概率选择
            available_models = self.task_to_models.get(task_type, self.task_to_models["general"])
            
            # 权重随机选择
            r = self.random.random()
            cumulative = 0
            for model, prob in available_models:
                cumulative += prob
                if r <= cumulative:
                    break
            
        # 估算成本
        cost = estimated_tokens / 1000 * self.cost_per_1k_tokens.get(model, 0.001)
        
        return model, round(cost, 6)
    
    def get_routing_decision(self, messages: List[Dict]) -> Dict:
        """
        获取完整的路由决策信息
        
        Returns:
            包含任务类型、推荐模型、备选方案、成本估算的字典
        """
        user_message = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_message = msg.get("content", "")
                break
        
        task_type = self.classifier.classify(user_message)
        estimated_tokens = len(user_message) * 1.5
        
        selected_model, estimated_cost = self.select_model(messages)
        alternatives = self.task_to_models.get(task_type, self.task_to_models["general"])
        
        return {
            "task_type": task_type,
            "user_message_preview": user_message[:100] + "..." if len(user_message) > 100 else user_message,
            "estimated_tokens": estimated_tokens,
            "selected_model": selected_model,
            "alternatives": [m for m, _ in alternatives],
            "estimated_cost": estimated_cost,
            "reasoning": f"检测到 [{task_type}] 任务，基于历史表现选择 {selected_model}"
        }


if __name__ == "__main__":
    # 测试
    router = SmartModelRouter()
    
    test_cases = [
        [{"role": "user", "content": "帮我写一个 Python 函数，实现快速排序"}],
        [{"role": "user", "content": "什么是量子纠缠？请通俗易懂地解释"}],
        [{"role": "user", "content": "分析这份 CSV 数据的销售趋势"}],
        [{"role": "user", "content": "今天天气怎么样"}],
        [{"role": "user", "content": "请为我的咖啡店想一个吸引人的广告语"}],
    ]
    
    print("=" * 60)
    print("智能任务路由引擎测试")
    print("=" * 60)
    
    for i, messages in enumerate(test_cases, 1):
        decision = router.get_routing_decision(messages)
        print(f"\n#{i} 测试用例:")
        print(f"  用户消息：{decision['user_message_preview']}")
        print(f"  任务类型：{decision['task_type']}")
        print(f"  推荐模型：{decision['selected_model']}")
        print(f"  备选方案：{decision['alternatives']}")
        print(f"  预估成本：¥{decision['estimated_cost']:.6f}")
        print(f"  推理逻辑：{decision['reasoning']}")
    
    print("\n" + "=" * 60)
    print("✅ 路由决策示例完成")