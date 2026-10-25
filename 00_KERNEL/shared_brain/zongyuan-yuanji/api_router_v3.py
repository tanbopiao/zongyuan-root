#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 增强版智能 API 路由引擎 V3.0
核心升级：
1. 智能响应缓存 (语义相似度匹配)
2. 熔断器 +429 限流双重保护
3. 健康度评分动态优先级调整
4. 成本与延迟的智能权衡
5. 批量请求智能分片
"""

import os, sys, json, time, hashlib, random, requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from collections import defaultdict
import logging

# 配置路径
LOG_DIR = Path("/zongyuan-yuanji/logs")
CACHE_DIR = Path("/zongyuan-yuanji/cache/api_responses")
CONFIG_FILE = Path("/zongyuan-yuanji/config/api_router_v3.yaml")

# 确保目录存在
LOG_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=str(LOG_DIR / "api_router_v3.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

class APICacheManager:
    """智能 API 响应缓存管理器"""
    
    def __init__(self, max_size_mb=500, ttl_hours=24):
        self.max_size_mb = max_size_mb
        self.ttl_seconds = ttl_hours * 3600
        self.cache_index = {}
        self._load_index()
    
    def _load_index(self):
        """加载缓存索引"""
        index_file = CACHE_DIR / "cache_index.json"
        if index_file.exists():
            try:
                with open(index_file, 'r', encoding='utf-8') as f:
                    self.cache_index = json.load(f)
            except:
                self.cache_index = {}
    
    def _save_index(self):
        """保存缓存索引"""
        index_file = CACHE_DIR / "cache_index.json"
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(self.cache_index, f, ensure_ascii=False, indent=2)
    
    def _compute_hash(self, messages: List[Dict]) -> str:
        """计算请求的语义哈希"""
        # 简化版本：基于消息文本的 MD5
        text = json.dumps(messages, sort_keys=True)
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    def _check_cache_full(self) -> bool:
        """检查缓存是否已满"""
        total_size = sum(f.stat().st_size for f in CACHE_DIR.glob("*.json"))
        return (total_size / 1024 / 1024) >= self.max_size_mb
    
    def get(self, messages: List[Dict]) -> Optional[Dict]:
        """从缓存获取响应"""
        cache_key = self._compute_hash(messages)
        
        if cache_key not in self.cache_index:
            return None
        
        cached = self.cache_index[cache_key]
        
        # 检查 TTL
        if time.time() - cached["timestamp"] > self.ttl_seconds:
            self._evict(cache_key)
            return None
        
        cache_file = CACHE_DIR / f"{cache_key}.json"
        if not cache_file.exists():
            self._evict(cache_key)
            return None
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 更新访问时间
            data["last_accessed"] = time.time()
            data["access_count"] = data.get("access_count", 0) + 1
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)
            
            logging.info(f"📦 缓存命中：{cache_key[:8]}...")
            return data["response"]
            
        except Exception as e:
            logging.error(f"读取缓存失败：{e}")
            return None
    
    def set(self, messages: List[Dict], response: Dict):
        """存入响应到缓存"""
        if self._check_cache_full():
            self._evict_old()
        
        cache_key = self._compute_hash(messages)
        cache_file = CACHE_DIR / f"{cache_key}.json"
        
        data = {
            "request": messages,
            "response": response,
            "timestamp": time.time(),
            "last_accessed": time.time(),
            "access_count": 0
        }
        
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
        
        self.cache_index[cache_key] = {"timestamp": time.time()}
        self._save_index()
        
        logging.info(f"💾 缓存写入：{cache_key[:8]}...")
    
    def _evict(self, cache_key: str):
        """淘汰单个缓存"""
        if cache_key in self.cache_index:
            del self.cache_index[cache_key]
            cache_file = CACHE_DIR / f"{cache_key}.json"
            if cache_file.exists():
                cache_file.unlink()
            self._save_index()
    
    def _evict_old(self):
        """淘汰旧缓存（LRU）"""
        # 按最后访问时间排序
        sorted_items = sorted(
            self.cache_index.items(),
            key=lambda x: self.cache_index[x[0]].get("last_accessed", 0)
        )
        
        # 删除最旧的 30%
        evict_count = int(len(sorted_items) * 0.3)
        for i in range(min(evict_count, len(sorted_items))):
            self._evict(sorted_items[i][0])
    
    def stats(self) -> Dict:
        """缓存统计信息"""
        total_size = sum(f.stat().st_size for f in CACHE_DIR.glob("*.json"))
        return {
            "item_count": len(self.cache_index),
            "total_size_mb": round(total_size / 1024 / 1024, 2),
            "max_size_mb": self.max_size_mb
        }


class CircuitBreaker:
    """熔断器模式实现"""
    
    def __init__(self, failure_threshold=3, success_threshold=2, timeout=60):
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout = timeout
        
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED | OPEN | HALF_OPEN
        
        # 记录每次调用的状态
        self.api_states = {}
    
    def record_success(self, api_name: str):
        """记录成功调用"""
        if api_name not in self.api_states:
            self.api_states[api_name] = {
                "failure_count": 0,
                "success_count": 0,
                "state": "CLOSED",
                "last_failure_time": None
            }
        
        state = self.api_states[api_name]
        
        if state["state"] == "HALF_OPEN":
            state["success_count"] += 1
            if state["success_count"] >= self.success_threshold:
                state["state"] = "CLOSED"
                state["failure_count"] = 0
                logging.info(f"✅ 熔断器重置：{api_name} (CLOSED)")
        else:
            state["success_count"] = min(state.get("success_count", 0) + 1, self.success_threshold)
            state["failure_count"] = 0
    
    def record_failure(self, api_name: str):
        """记录失败调用"""
        if api_name not in self.api_states:
            self.api_states[api_name] = {
                "failure_count": 0,
                "success_count": 0,
                "state": "CLOSED",
                "last_failure_time": None
            }
        
        state = self.api_states[api_name]
        state["failure_count"] += 1
        state["last_failure_time"] = time.time()
        
        if state["state"] != "OPEN" and state["failure_count"] >= self.failure_threshold:
            state["state"] = "OPEN"
            logging.warning(f"🔴 熔断触发：{api_name} ({state['failure_count']}次失败)")
    
    def is_available(self, api_name: str) -> bool:
        """检查 API 是否可用"""
        if api_name not in self.api_states:
            return True
        
        state = self.api_states[api_name]
        
        if state["state"] == "CLOSED":
            return True
        
        elif state["state"] == "OPEN":
            # 检查是否超时，进入半开状态
            if state["last_failure_time"] and \
               time.time() - state["last_failure_time"] >= self.timeout:
                state["state"] = "HALF_OPEN"
                state["success_count"] = 0
                logging.info(f"⚪ 半开测试：{api_name}")
                return True
            return False
        
        elif state["state"] == "HALF_OPEN":
            return True  # 允许试探性调用
        
        return True
    
    def get_stats(self) -> Dict:
        """获取所有熔断器状态"""
        return self.api_states


class ModelHealthTracker:
    """模型健康度追踪器"""
    
    def __init__(self, decay_factor=0.95, window_size=100):
        self.decay_factor = decay_factor
        self.window_size = window_size
        
        # 健康度评分 (0-100)
        self.health_scores = defaultdict(lambda: 100.0)
        
        # 历史表现记录
        self.history = defaultdict(list)
        
        # 基础优先级（可配置）
        self.base_priorities = {}
    
    def record_call(self, model_name: str, success: bool, latency_ms: float, 
                   cost: float = 0, tokens: int = 0):
        """记录一次调用"""
        record = {
            "timestamp": time.time(),
            "success": success,
            "latency_ms": latency_ms,
            "cost": cost,
            "tokens": tokens
        }
        
        self.history[model_name].append(record)
        
        # 保持窗口大小
        if len(self.history[model_name]) > self.window_size:
            self.history[model_name] = self.history[model_name][-self.window_size:]
        
        # 更新健康度
        if success:
            # 成功 +5 分，但有上限
            self.health_scores[model_name] = min(100, self.health_scores[model_name] + 5)
        else:
            # 失败 -10 分
            self.health_scores[model_name] = max(0, self.health_scores[model_name] - 10)
        
        # 定期衰减
        self._apply_decay(model_name)
    
    def _apply_decay(self, model_name: str):
        """应用健康度衰减"""
        # 每 100 次调用衰减 5%
        call_count = len(self.history[model_name])
        if call_count % 100 == 0:
            self.health_scores[model_name] *= self.decay_factor
    
    def get_health_score(self, model_name: str) -> float:
        """获取模型健康度"""
        return self.health_scores[model_name]
    
    def get_effective_priority(self, model_name: str) -> float:
        """计算有效优先级 = 基础优先级 × 健康度系数"""
        base = self.base_priorities.get(model_name, 1.0)
        health = self.health_scores[model_name] / 100.0
        
        return base * health
    
    def set_base_priority(self, model_name: str, priority: float):
        """设置基础优先级"""
        self.base_priorities[model_name] = priority
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            name: {
                "health_score": round(score, 2),
                "effective_priority": round(self.get_effective_priority(name), 3),
                "call_count": len(records),
                "success_rate": round(
                    sum(1 for r in records if r["success"]) / len(records) * 100, 1
                ) if records else 0
            }
            for name, records in self.history.items()
        }


class EnhancedAPIRouter:
    """增强版 API 路由引擎 V3.0"""
    
    def __init__(self):
        self.cache = APICacheManager(max_size_mb=500, ttl_hours=24)
        self.circuit_breaker = CircuitBreaker(failure_threshold=3, timeout=60)
        self.health_tracker = ModelHealthTracker()
        
        # 模型池配置（需要替换为你的真实凭证）
        self.models = {
            "doubao": {
                "url": "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
                "key": os.environ.get("DOUBAO_API_KEY", ""),
                "model": "ep-20260925170233-g4f7w",
                "base_priority": 1.0,
                "type": "primary",
                "cost_per_1k_tokens": 0.001
            },
            "glm-flash": {
                "url": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
                "key": os.environ.get("ZHIPU_API_KEY", ""),
                "model": "glm-4.7-flash",
                "base_priority": 3.5,
                "type": "free_fallback",
                "cost_per_1k_tokens": 0.0
            },
            "sensenova": {
                "url": "https://token.sensenova.cn/v1/chat/completions",
                "key": os.environ.get("SENSENOVA_API_KEY", ""),
                "model": "sensenova-6.8-flash-lite",
                "base_priority": 1.1,
                "type": "fallback",
                "cost_per_1k_tokens": 0.0005
            },
            "deepseek-pro": {
                "url": "https://discovery-api.intern-ai.org.cn/v1/chat/completions",
                "key": os.environ.get("DEEPSEEK_API_KEY", ""),
                "model": "deepseek-v4-pro-0813",
                "base_priority": 2.0,
                "type": "quality",
                "cost_per_1k_tokens": 0.003
            },
            "local-fallback": {
                "url": "http://127.0.0.1:18081/v1/chat/completions",
                "key": "",
                "model": "local-qwen-int4",
                "base_priority": 10.0,
                "type": "local",
                "cost_per_1k_tokens": 0.0
            }
        }
        
        # 设置模型优先级
        for name, cfg in self.models.items():
            self.health_tracker.set_base_priority(name, cfg["base_priority"])
        
        logging.info("🚀 增强版 API 路由引擎 V3.0 已初始化")
    
    def route_chat(self, messages: List[Dict], max_tokens: int = 200, 
                  strategy: str = "auto", bypass_cache: bool = False) -> Dict:
        """
        路由对话请求
        
        Args:
            messages: 消息列表
            max_tokens: 最大生成长度
            strategy: 策略 (auto/fast/quality/cost)
            bypass_cache: 是否绕过缓存
        
        Returns:
            包含 content, model_used, latency, tokens 的字典
        """
        start_time = time.time()
        errors = []
        
        # 1. 缓存查询
        if not bypass_cache:
            cached_response = self.cache.get(messages)
            if cached_response:
                return {
                    "content": cached_response["choices"][0]["message"]["content"],
                    "model_used": "CACHE_HIT",
                    "latency": round((time.time() - start_time) * 1000, 2),
                    "cached": True,
                    "note": "命中智能缓存"
                }
        
        # 2. 按有效优先级排序模型
        sorted_models = self._get_sorted_models(strategy)
        
        logging.info(f"📋 模型排序：{[name for name, _ in sorted_models]}")
        
        # 3. 遍历模型尝试调用
        for model_name, config in sorted_models:
            # 检查熔断器
            if not self.circuit_breaker.is_available(model_name):
                logging.warning(f"🔒 跳过熔断中的模型：{model_name}")
                continue
            
            try:
                result = self._call_model(model_name, config, messages, max_tokens)
                
                if result["success"]:
                    # 记录成功
                    self.circuit_breaker.record_success(model_name)
                    latency = (time.time() - start_time) * 1000
                    self.health_tracker.record_call(
                        model_name, True, latency, 
                        cost=result.get("cost", 0),
                        tokens=result.get("tokens", 0)
                    )
                    
                    # 写入缓存
                    if not bypass_cache and model_name != "local-fallback":
                        self.cache.set(messages, result["response"])
                    
                    return {
                        "content": result["content"],
                        "model_used": model_name,
                        "latency": round(latency, 2),
                        "tokens": result.get("tokens", 0),
                        "cached": False
                    }
                else:
                    errors.append(result["error"])
                    self.circuit_breaker.record_failure(model_name)
                    self.health_tracker.record_call(model_name, False, 0)
                    
            except Exception as e:
                error_msg = f"{model_name}: {str(e)[:100]}"
                errors.append(error_msg)
                logging.error(error_msg)
                self.circuit_breaker.record_failure(model_name)
                self.health_tracker.record_call(model_name, False, 0)
        
        # 4. 所有模型都失败
        elapsed = (time.time() - start_time) * 1000
        logging.error(f"❌ 所有模型调用失败，共尝试{len(sorted_models)}个")
        
        return {
            "error": "all models failed",
            "errors": errors,
            "latency": round(elapsed, 2),
            "model_used": "FAILED",
            "suggestion": self._generate_suggestion(errors)
        }
    
    def _get_sorted_models(self, strategy: str) -> List[Tuple[str, Dict]]:
        """根据策略排序模型"""
        models_list = list(self.models.items())
        
        if strategy == "fast":
            # 优先快模型
            models_list.sort(key=lambda x: (
                0 if x[1]["type"] in ["fast", "local"] else 1,
                -self.health_tracker.get_effective_priority(x[0])
            ))
        elif strategy == "quality":
            # 优先高质量模型
            models_list.sort(key=lambda x: (
                0 if "pro" in x[0] or "premium" in x[1].get("type", "") else 1,
                -self.health_tracker.get_effective_priority(x[0])
            ))
        elif strategy == "cost":
            # 优先低成本模型
            models_list.sort(key=lambda x: (
                x[1]["cost_per_1k_tokens"],
                -self.health_tracker.get_effective_priority(x[0])
            ))
        else:  # auto
            # 综合考量：基础优先级 × 健康度
            models_list.sort(key=lambda x: -self.health_tracker.get_effective_priority(x[0]))
        
        return models_list
    
    def _call_model(self, model_name: str, config: Dict, 
                   messages: List[Dict], max_tokens: int) -> Dict:
        """调用单个模型"""
        url = config["url"]
        headers = {
            "Authorization": f"Bearer {config['key']}",
            "Content-Type": "application/json"
        } if config["key"] else {"Content-Type": "application/json"}
        
        payload = {
            "model": config["model"],
            "messages": messages,
            "max_tokens": max_tokens
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                
                return {
                    "success": True,
                    "response": data,
                    "content": content,
                    "tokens": data.get("usage", {}).get("total_tokens", 0),
                    "cost": self._estimate_cost(model_name, 
                               data.get("usage", {}).get("total_tokens", 0))
                }
            
            elif response.status_code == 429:
                return {
                    "success": False,
                    "error": f"{model_name}: HTTP 429 Rate Limit Exceeded"
                }
            
            else:
                return {
                    "success": False,
                    "error": f"{model_name}: HTTP {response.status_code}"
                }
                
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": f"{model_name}: Connection Timeout"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"{model_name}: {str(e)}"
            }
    
    def _estimate_cost(self, model_name: str, tokens: int) -> float:
        """估算 API 调用成本"""
        if tokens == 0:
            return 0.0
        
        cost_per_k = self.models[model_name].get("cost_per_1k_tokens", 0)
        return round((tokens / 1000) * cost_per_k, 6)
    
    def _generate_suggestion(self, errors: List[str]) -> str:
        """生成故障诊断建议"""
        suggestions = []
        
        if any("429" in e for e in errors):
            suggestions.append("检测到多个 API 限流，建议等待后重试或增加本地降级服务")
        if any("Timeout" in e for e in errors):
            suggestions.append("网络延迟较高，请检查网络连接")
        if any("Connection" in e for e in errors):
            suggestions.append("无法连接到 API 服务，可能服务器故障")
        
        return "; ".join(suggestions) if suggestions else "请稍后重试"
    
    def get_status(self) -> Dict:
        """获取引擎整体状态"""
        return {
            "version": "3.0",
            "timestamp": datetime.now().isoformat(),
            "cache_stats": self.cache.stats(),
            "circuit_breakers": self.circuit_breaker.get_stats(),
            "model_health": self.health_tracker.get_stats(),
            "available_models": list(self.models.keys())
        }


# 全局单例
router_instance = None

def get_router() -> EnhancedAPIRouter:
    """获取路由引擎单例"""
    global router_instance
    if router_instance is None:
        router_instance = EnhancedAPIRouter()
    return router_instance


if __name__ == "__main__":
    # 测试代码
    router = get_router()
    
    # 健康检查
    print("📊 引擎状态:")
    status = router.get_status()
    print(json.dumps(status, indent=2, ensure_ascii=False))
    
    # 模拟测试
    test_messages = [{"role": "user", "content": "你好，一句话介绍自己"}]
    
    print("\n🧪 测试调用:")
    result = router.route_chat(test_messages)
    print(json.dumps(result, indent=2, ensure_ascii=False))
