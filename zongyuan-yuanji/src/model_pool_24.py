# ZONGYUAN-ROOT - 24 模型智能调度配置
# 基于实际云内核配置的全面优化方案

"""
┌─────────────────────────────────────────────────────────────┐
│                    Octop 模型资产全景图                       │
├─────────────────────────────────────────────────────────────┤
│  Zhipu (6)     │ SHUSHENG(12)   │ ModelScope(2)            │
│  GLM-4.7/5系列 │ deepseek/kimi   │ Qwen3.5/GLM-5            │
│  ↓推理主力      │ ↓日常主力       │ ↓超大参数                 │
├─────────────────────────────────────────────────────────────┤
│  st(2)         │ 办公专用 (2)                                │
│  sensenova/DS  │ N1PRO 系列                                  │
│  ↓低成本        │ ↓垂直场景                                  │
└─────────────────────────────────────────────────────────────┘
"""

import os, json, time, hashlib
from datetime import datetime
from typing import Dict, List, Tuple, Optional


class AdvancedModelPool:
    """24 模型高级池配置"""
    
    def __init__(self):
        # ========== L1: 智谱主力队列 ==========
        self.zhipu_models = {
            "glm-4-flash": {
                "url": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
                "key": os.environ.get("ZHIPU_API_KEY", "1dfa...quIk"),  # 替换为环境变量
                "model": "GLM-4.7-Flash",
                "provider": "zhipu",
                "base_priority": 1.0,
                "type": "primary",
                "context_length": 200000,
                "strengths": ["推理", "通用问答"],
                "cost_per_1k_tokens": 0.0005,
                "rate_limit_rpm": 100  # 每分钟请求数
            },
            "glm-5": {
                "url": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
                "key": os.environ.get("ZHIPU_API_KEY"),
                "model": "GLM-5",
                "provider": "zhipu",
                "base_priority": 1.2,
                "type": "quality",
                "context_length": 200000,
                "strengths": ["复杂推理", "代码生成"],
                "cost_per_1k_tokens": 0.001,
                "rate_limit_rpm": 60
            },
            "glm-5.1": {
                "url": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
                "key": os.environ.get("ZHIPU_API_KEY"),
                "model": "GLM-5.1",
                "provider": "zhipu",
                "base_priority": 1.1,
                "type": "quality",
                "context_length": 200000,
                "strengths": ["多轮对话", "逻辑推理"],
                "cost_per_1k_tokens": 0.001,
                "rate_limit_rpm": 60
            },
            "glm-5.2-long": {
                "url": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
                "key": os.environ.get("ZHIPU_API_KEY"),
                "model": "GLM-5.2",
                "provider": "zhipu",
                "base_priority": 1.3,
                "type": "long_context",
                "context_length": 1000000,  # 1M!
                "strengths": ["超长文本", "文档分析"],
                "cost_per_1k_tokens": 0.002,
                "rate_limit_rpm": 30
            },
            "glm-5-turbo": {
                "url": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
                "key": os.environ.get("ZHIPU_API_KEY"),
                "model": "GLM-5 Turbo",
                "provider": "zhipu",
                "base_priority": 0.9,
                "type": "fast",
                "context_length": 200000,
                "strengths": ["快速响应", "简单问答"],
                "cost_per_1k_tokens": 0.0005,
                "rate_limit_rpm": 120
            },
            "glm-5v-turbo": {
                "url": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
                "key": os.environ.get("ZHIPU_API_KEY"),
                "model": "GLM-5V Turbo",
                "provider": "zhipu",
                "base_priority": 1.5,
                "type": "multimodal",
                "context_length": 200000,
                "supports_vision": True,
                "strengths": ["图像理解", "图文混合"],
                "cost_per_1k_tokens": 0.001,
                "rate_limit_rpm": 80
            }
        }
        
        # ========== L2: SHUSHENG 深思考备用队列 ==========
        self.shusheng_models = {
            "deepseek-pro": {
                "url": "https://discovery-api.intern-ai.org.cn/v1/chat/completions",
                "key": os.environ.get("DEEPSEEK_API_KEY", "sk-e...f4c4"),
                "model": "deepseek-v4-pro-0813",
                "provider": "shusheng",
                "base_priority": 2.0,
                "type": "quality",
                "strengths": ["深度推理", "专业问答"],
                "cost_per_1k_tokens": 0.003,
                "rate_limit_rpm": 50
            },
            "deepseek-vision": {
                "url": "https://discovery-api.intern-ai.org.cn/v1/chat/completions",
                "key": os.environ.get("DEEPSEEK_API_KEY"),
                "model": "deepseek-v4-flash-vision",
                "provider": "shusheng",
                "base_priority": 2.2,
                "type": "multimodal",
                "supports_vision": True,
                "strengths": ["视觉理解", "图表分析"],
                "cost_per_1k_tokens": 0.002,
                "rate_limit_rpm": 60
            },
            "deepseek-flash": {
                "url": "https://discovery-api.intern-ai.org.cn/v1/chat/completions",
                "key": os.environ.get("DEEPSEEK_API_KEY"),
                "model": "deepseek-v4-flash-0731",
                "provider": "shusheng",
                "base_priority": 1.5,
                "type": "fast",
                "strengths": ["快速响应", "通用问答"],
                "cost_per_1k_tokens": 0.001,
                "rate_limit_rpm": 100
            },
            "kimi-k2.6": {
                "url": "https://discovery-api.intern-ai.org.cn/v1/chat/completions",
                "key": os.environ.get("DEEPSEEK_API_KEY"),
                "model": "kimi-k2.6",
                "provider": "shusheng",
                "base_priority": 1.8,
                "type": "high_concurrency",
                "strengths": ["高并发稳定", "长对话"],
                "cost_per_1k_tokens": 0.0015,
                "rate_limit_rpm": 80
            },
            "intern-s2": {
                "url": "https://discovery-api.intern-ai.org.cn/v1/chat/completions",
                "key": os.environ.get("DEEPSEEK_API_KEY"),
                "model": "intern-s2",
                "provider": "shusheng",
                "base_priority": 1.3,
                "type": "fallback",
                "strengths": ["免费额度", "基础问答"],
                "cost_per_1k_tokens": 0.000,
                "rate_limit_rpm": 100
            },
            "minimax-m3": {
                "url": "https://discovery-api.intern-ai.org.cn/v1/chat/completions",
                "key": os.environ.get("DEEPSEEK_API_KEY"),
                "model": "minimax-m3",
                "provider": "shusheng",
                "base_priority": 1.6,
                "type": "creative",
                "strengths": ["创意写作", "文案生成"],
                "cost_per_1k_tokens": 0.0012,
                "rate_limit_rpm": 70
            },
            "qwen3.8-27b": {
                "url": "https://discovery-api.intern-ai.org.cn/v1/chat/completions",
                "key": os.environ.get("DEEPSEEK_API_KEY"),
                "model": "qwen3.8-27b",
                "provider": "shusheng",
                "base_priority": 1.4,
                "type": "general",
                "strengths": ["通用能力", "平衡性能"],
                "cost_per_1k_tokens": 0.0008,
                "rate_limit_rpm": 90
            },
            "glm-5.3": {
                "url": "https://discovery-api.intern-ai.org.cn/v1/chat/completions",
                "key": os.environ.get("DEEPSEEK_API_KEY"),
                "model": "glm-5.3",
                "provider": "shusheng",
                "base_priority": 1.5,
                "type": "balanced",
                "strengths": ["速度质量平衡"],
                "cost_per_1k_tokens": 0.001,
                "rate_limit_rpm": 80
            },
            "atrian-dawn": {
                "url": "https://discovery-api.intern-ai.org.cn/v1/chat/completions",
                "key": os.environ.get("DEEPSEEK_API_KEY"),
                "model": "Atria-Dawn",
                "provider": "shusheng",
                "base_priority": 1.7,
                "type": "advanced",
                "strengths": ["前沿模型", "实验功能"],
                "cost_per_1k_tokens": 0.002,
                "rate_limit_rpm": 50
            },
            "atrian-dawn-preview": {
                "url": "https://discovery-api.intern-ai.org.cn/v1/chat/completions",
                "key": os.environ.get("DEEPSEEK_API_KEY"),
                "model": "Atria-Dawn-Preview",
                "provider": "shusheng",
                "base_priority": 2.5,
                "type": "preview",
                "strengths": ["预览功能", "测试新特性"],
                "cost_per_1k_tokens": 0.003,
                "rate_limit_rpm": 30
            },
            "agents-a1": {
                "url": "https://discovery-api.intern-ai.org.cn/v1/chat/completions",
                "key": os.environ.get("DEEPSEEK_API_KEY"),
                "model": "Agents-A1",
                "provider": "shusheng",
                "base_priority": 2.8,
                "type": "agent",
                "strengths": ["Agent 协同", "工具调用"],
                "cost_per_1k_tokens": 0.0025,
                "rate_limit_rpm": 40
            },
            "decision-4b": {
                "url": "https://discovery-api.intern-ai.org.cn/v1/chat/completions",
                "key": os.environ.get("DEEPSEEK_API_KEY"),
                "model": "intern-decision-4b",
                "provider": "shusheng",
                "base_priority": 2.3,
                "type": "decision",
                "strengths": ["决策支持", "方案评估"],
                "cost_per_1k_tokens": 0.0018,
                "rate_limit_rpm": 50
            }
        }
        
        # ========== L3: ModelScope 超大参数队列 ==========
        self.modelscope_models = {
            "qwen3.5-122b": {
                "url": "https://api-inference.modelscope.cn/v1/chat/completions",
                "key": os.environ.get("MODELSCOPE_API_KEY", "ms-6...3ce7"),
                "model": "Qwen3.5-122B-A10B",
                "provider": "modelscope",
                "base_priority": 3.5,
                "type": "ultra_large",
                "strengths": ["超大参数", "知识渊博"],
                "cost_per_1k_tokens": 0.005,
                "rate_limit_rpm": 20
            },
            "glm-5-ms": {
                "url": "https://api-inference.modelscope.cn/v1/chat/completions",
                "key": os.environ.get("MODELSCOPE_API_KEY"),
                "model": "GLM-5",
                "provider": "modelscope",
                "base_priority": 2.5,
                "type": "backup",
                "strengths": ["兜底备份"],
                "cost_per_1k_tokens": 0.001,
                "rate_limit_rpm": 40
            }
        }
        
        # ========== L4: st (SenseNova) 低成本队列 ==========
        self.sensenova_models = {
            "sensenova-flash": {
                "url": "https://token.sensenova.cn/v1/responses",
                "key": os.environ.get("SENSENOVA_API_KEY", "sk-w...aXmi"),
                "model": "sensenova-6.8-flash-lite",
                "provider": "st",
                "base_priority": 1.2,
                "type": "low_cost",
                "strengths": ["极致性价比", "轻量任务"],
                "cost_per_1k_tokens": 0.0003,
                "rate_limit_rpm": 150
            },
            "ds-flash-st": {
                "url": "https://token.sensenova.cn/v1/responses",
                "key": os.environ.get("SENSENOVA_API_KEY"),
                "model": "DeepSeek V4 Flash",
                "provider": "st",
                "base_priority": 1.4,
                "type": "balanced",
                "strengths": ["DeepSeek 能力", "低成本"],
                "cost_per_1k_tokens": 0.001,
                "rate_limit_rpm": 100
            }
        }
        
        # ========== L5: 办公专用垂直场景 ==========
        self.office_models = {
            "n1promax": {
                "url": "https://www.wwlib.cn/index.php/v1/chat/completions",
                "key": os.environ.get("OFFICE_API_KEY", "sk-6...9c52"),
                "model": "N1PROMAX",
                "provider": "office",
                "base_priority": 2.0,
                "type": "vertical",
                "strengths": ["办公场景", "文档处理"],
                "cost_per_1k_tokens": 0.002,
                "rate_limit_rpm": 60
            },
            "n1proflash": {
                "url": "https://www.wwlib.cn/index.php/v1/chat/completions",
                "key": os.environ.get("OFFICE_API_KEY"),
                "model": "N1PROFLASH",
                "provider": "office",
                "base_priority": 1.5,
                "type": "vertical_fast",
                "strengths": ["办公场景", "快速响应"],
                "cost_per_1k_tokens": 0.001,
                "rate_limit_rpm": 100
            }
        }
        
        # 合并所有模型
        self.all_models = {}
        self.all_models.update(self.zhipu_models)
        self.all_models.update(self.shusheng_models)
        self.all_models.update(self.modelscope_models)
        self.all_models.update(self.sensenova_models)
        self.all_models.update(self.office_models)
        
        print(f"✅ 已加载 {len(self.all_models)} 个模型配置")
    
    def get_model_by_type(self, model_type: str) -> List[str]:
        """根据类型获取可用模型列表"""
        return [name for name, cfg in self.all_models.items() 
                if cfg["type"] == model_type]
    
    def get_strongest_models(self, count: int = 3) -> List[Tuple[str, Dict]]:
        """获取最强的 N 个模型"""
        sorted_models = sorted(
            self.all_models.items(),
            key=lambda x: x[1]["base_priority"],
            reverse=True
        )
        return sorted_models[:count]
    
    def get_cheapest_models(self, count: int = 3) -> List[Tuple[str, Dict]]:
        """获取最便宜的 N 个模型（不含免费）"""
        paid_models = [(n, c) for n, c in self.all_models.items() 
                      if c["cost_per_1k_tokens"] > 0]
        sorted_models = sorted(paid_models, key=lambda x: x[1]["cost_per_1k_tokens"])
        return sorted_models[:count]
    
    def get_free_models(self) -> List[str]:
        """获取免费模型"""
        return [name for name, cfg in self.all_models.items() 
                if cfg["cost_per_1k_tokens"] == 0]


if __name__ == "__main__":
    pool = AdvancedModelPool()
    
    print("\n" + "=" * 60)
    print("📊 24 模型资产统计")
    print("=" * 60)
    
    print(f"\n总模型数：{len(pool.all_models)}")
    
    print("\n🏆 最强模型 Top 3:")
    for name, cfg in pool.get_strongest_models(3):
        print(f"  {name}: 优先级={cfg['base_priority']}, 擅长={[s for s in cfg['strengths']]}")
    
    print("\n💰 最便宜模型 Top 3 (非免费):")
    for name, cfg in pool.get_cheapest_models(3):
        print(f"  {name}: ¥{cfg['cost_per_1k_tokens']:.4f}/千 token")
    
    print("\n🎁 免费模型:")
    for name in pool.get_free_models():
        print(f"  ✓ {name}")
    
    print("\n" + "=" * 60)
    print("✅ 模型池初始化完成")
    print("=" * 60)
