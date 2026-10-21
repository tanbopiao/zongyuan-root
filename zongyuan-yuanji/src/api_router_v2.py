#!/usr/bin/env python3
"""
智能多模型降级路由引擎 (V2.0)
解决限流问题的核心组件

特性:
  ✅ 429 限流自动检测和记录
  ✅ 熔断器模式 (Circuit Breaker)
  ✅ 指数退避重试策略
  ✅ 健康状态缓存池
  ✅ 优先级 + 健康度综合路由
"""

import requests, time, json, os, re, datetime
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

# ============ 配置参数 ============
CONFIG = {
    # 熔断器设置
    "circuit_breaker": {
        "failure_threshold": 3,      # 失败次数阈值 → 熔断
        "success_threshold": 2,      # 成功次数恢复 → 闭合
        "timeout": 60,               # 熔断超时 (秒)
        "half_open_requests": 2,     # 半开状态尝试数
    },
    
    # 限流处理
    "rate_limit": {
        "max_retry_attempts": 3,     # 最大重试次数
        "base_delay": 5,             # 基础退避时间 (秒)
        "max_delay": 120,            # 最大退避时间 (秒)
        "randomize_factor": 0.3,     # 随机化因子 (避免雪崩)
    },
    
    # 健康检查
    "health_check": {
        "cache_ttl": 30,             # 健康状态缓存 TTL(秒)
        "check_interval": 60,        # 主动健康检查间隔 (秒)
    }
}

# ============ 全局状态管理器 ============
class ModelState:
    """单个模型的状态跟踪"""
    def __init__(self):
        self.failures = 0              # 连续失败次数
        self.successes = 0             # 连续成功次数
        self.circuit_state = "CLOSED"  # CLOSED / OPEN / HALF_OPEN
        self.circuit_opened_at = None  # 熔断开启时间
        self.last_error = None         # 最后一次错误
        self.rate_limited = False      # 是否被限流
        self.rate_limited_at = None    # 限流时间
        self.health_score = 100        # 健康度评分 (0-100)
        self.avg_latency = 0           # 平均延迟 (毫秒)
        self.total_requests = 0        # 总请求数
        self.total_failures = 0        # 总失败数
    
    def record_success(self, latency_ms: float):
        self.failures = 0
        self.successes += 1
        self.total_requests += 1
        
        # 更新平均延迟 (平滑移动平均)
        alpha = 0.3
        if self.avg_latency == 0:
            self.avg_latency = latency_ms
        else:
            self.avg_latency = alpha * latency_ms + (1 - alpha) * self.avg_latency
        
        # 更新健康度
        self.health_score = min(100, self.health_score + 5)
        
        # 检查是否应该恢复
        if self.circuit_state == "HALF_OPEN" and self.successes >= CONFIG["circuit_breaker"]["success_threshold"]:
            self._close_circuit()
    
    def record_failure(self, error: str, is_rate_limit: bool = False):
        self.failures += 1
        self.successes = 0
        self.total_failures += 1
        self.last_error = error
        
        # 更新健康度
        self.health_score = max(0, self.health_score - 10)
        if is_rate_limit:
            self.rate_limited = True
            self.rate_limited_at = time.time()
        
        # 检查是否应该熔断
        if self.circuit_state == "CLOSED" and self.failures >= CONFIG["circuit_breaker"]["failure_threshold"]:
            self._open_circuit()
    
    def _open_circuit(self):
        self.circuit_state = "OPEN"
        self.circuit_opened_at = time.time()
        print(f"[CircuitBreaker] 🔴 模型熔断：{self}")
    
    def _close_circuit(self):
        self.circuit_state = "CLOSED"
        self.circuit_opened_at = None
        self.failures = 0
        print(f"[CircuitBreaker] 🟢 模型恢复：{self}")
    
    def can_execute(self) -> bool:
        """检查是否可以执行请求"""
        if self.circuit_state == "CLOSED":
            return not self.is_expired_rate_limit()
        
        if self.circuit_state == "OPEN":
            # 检查是否过了熔断超时时间
            if time.time() - self.circuit_opened_at > CONFIG["circuit_breaker"]["timeout"]:
                self.circuit_state = "HALF_OPEN"
                self.successes = 0
                return True
            return False
        
        # HALF_OPEN 状态允许有限请求
        return not self.is_expired_rate_limit()
    
    def is_expired_rate_limit(self) -> bool:
        """检查限流是否已过期 (2 分钟后自动解除)"""
        if not self.rate_limited:
            return False
        return time.time() - self.rate_limited_at < 120
    
    def get_priority_score(self, base_priority: float) -> float:
        """计算综合优先级分数 (越低越优先)"""
        # 综合评分 = 基础优先级 * 健康度系数 * 延迟惩罚
        health_factor = self.health_score / 100
        latency_penalty = 1 + (self.avg_latency / 1000)  # 每 1000ms 增加 1.0
        return base_priority * health_factor * latency_penalty
    
    def __str__(self):
        return f"{self.circuit_state}(failures={self.failures}, health={self.health_score}, latency={self.avg_latency:.0f}ms)"


# 全局模型状态字典
MODEL_STATES: Dict[str, ModelState] = {}


# ============ 路由引擎 ============
def smart_route_chat(messages: List[Dict], max_tokens: int = 200, strategy: str = "auto") -> Dict:
    """
    智能路由对话请求
    
    Args:
        messages: 对话消息列表
        max_tokens: 最大生成 token 数
        strategy: 路由策略 (auto/fast/quality/fallback)
    
    Returns:
        响应结果或错误信息
    """
    
    # === 模型池配置 ===
    MODELS = {
        "doubao": {
            "url": "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
            "key": "ark-800a6f28-5c7f-4ec5-9766-4b7da1a58f1d-50a70",
            "model": "ep-20260925170233-g4f7w",
            "priority": 1.0,
            "type": "main"
        },
        "zhipu-glm-flash": {
            "url": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
            "key": "d63c880c0e1b424d8ad242f686e83451.vhHr5d5OQUY5UHNp",
            "model": "glm-4.7-flash",
            "priority": 3.5,
            "type": "free"
        },
        "sensenova": {
            "url": "https://token.sensenova.cn/v1/chat/completions",
            "key": os.environ.get("SENSENOVA_API_KEY", ""),
            "model": "sensenova-6.8-flash-lite",
            "priority": 1.1,
            "type": "fallback"
        },
        "deepseek-pro": {
            "url": "https://discovery-api.intern-ai.org.cn/v1/chat/completions",
            "key": "",
            "model": "deepseek-v4-pro-0813",
            "priority": 2.0,
            "type": "fallback"
        },
        "deepseek-flash": {
            "url": "https://discovery-api.intern-ai.org.cn/v1/chat/completions",
            "key": "",
            "model": "deepseek-v4-flash-0731",
            "priority": 3.0,
            "type": "fast"
        },
        "intern-s2": {
            "url": "https://discovery-api.intern-ai.org.cn/v1/chat/completions",
            "key": "",
            "model": "intern-s2",
            "priority": 1.3,
            "type": "free"
        },
        "agents-a1": {
            "url": "https://discovery-api.intern-ai.org.cn/v1/chat/completions",
            "key": "",
            "model": "Agents-A1",
            "priority": 1.4,
            "type": "free"
        },
    }
    
    # === 按综合优先级排序 ===
    def get_model_sort_key(item):
        name, cfg = item
        state = MODEL_STATES.get(name, ModelState())
        if name not in MODEL_STATES:
            MODEL_STATES[name] = state
        
        base_pri = cfg["priority"]
        if strategy == "fast":
            base_pri *= 0.7 if cfg["type"] == "fast" else 1.5
        elif strategy == "quality":
            base_pri *= 0.7 if "pro" in name else 1.5
        
        return state.get_priority_score(base_pri)
    
    sorted_models = sorted(MODELS.items(), key=get_model_sort_key)
    
    # === 依次尝试 ===
    errors = []
    for name, cfg in sorted_models:
        # 确保状态对象存在
        if name not in MODEL_STATES:
            MODEL_STATES[name] = ModelState()
        state = MODEL_STATES[name]
        
        # 检查是否可以执行
        if not state.can_execute():
            errors.append(f"{name}: Circuit {'Open' if state.circuit_state == 'OPEN' else 'Rate-Limited'}")
            continue
        
        # 指数退避重试
        for attempt in range(CONFIG["rate_limit"]["max_retry_attempts"]):
            try:
                t0 = time.time()
                
                headers = {
                    "Authorization": f"Bearer {cfg['key']}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": cfg["model"],
                    "messages": messages,
                    "max_tokens": max_tokens
                }
                
                r = requests.post(cfg["url"], json=payload, headers=headers, timeout=30)
                elapsed_ms = (time.time() - t0) * 1000
                
                if r.status_code == 200:
                    data = r.json()
                    msg = data["choices"][0]["message"]
                    content = msg.get("content") or msg.get("reasoning_content", "") or ""
                    
                    state.record_success(elapsed_ms)
                    
                    return {
                        "content": content,
                        "model_used": name,
                        "latency_ms": round(elapsed_ms, 2),
                        "tokens": data.get("usage", {}).get("total_tokens", 0),
                        "status": "success"
                    }
                
                elif r.status_code == 429:
                    # 429 限流！标记并退避
                    state.record_failure("HTTP 429 Rate Limit", is_rate_limit=True)
                    errors.append(f"{name}: 限流 (429)")
                    
                    # 指数退避 + 随机化
                    delay = min(
                        CONFIG["rate_limit"]["max_delay"],
                        CONFIG["rate_limit"]["base_delay"] * (2 ** attempt)
                    )
                    random_factor = 1 + (os.urandom(1)[0] % 100) / 100 * CONFIG["rate_limit"]["randomize_factor"]
                    sleep_time = delay * random_factor
                    
                    print(f"[RateLimit] ⏳ {name} 限流，退避 {sleep_time:.1f}s...")
                    time.sleep(sleep_time)
                    continue
                
                else:
                    state.record_failure(f"HTTP {r.status_code}")
                    errors.append(f"{name}: HTTP {r.status_code}")
                    
            except requests.exceptions.Timeout:
                state.record_failure("Timeout")
                errors.append(f"{name}: Timeout")
            
            except Exception as e:
                state.record_failure(str(e)[:100])
                errors.append(f"{name}: {str(e)[:50]}")
            
            # 如果不是最后一次的，等待后重试
            if attempt < CONFIG["rate_limit"]["max_retry_attempts"] - 1:
                time.sleep(1)
    
    # === 所有外部 API 都失败 → 本地兜底 ===
    print("[Fallback] 🔄 尝试本地兜底模型...")
    result = try_local_fallback(messages, max_tokens)
    if result.get("content"):
        return result
    
    # === 全部失败 ===
    return {
        "error": "All models failed",
        "errors": errors[:5],  # 只保留前 5 个错误
        "circuit_states": {k: str(v) for k, v in list(MODEL_STATES.items())[:5]}
    }


def try_local_fallback(messages: List[Dict], max_tokens: int) -> Dict:
    """尝试本地兜底模型"""
    try:
        # 检查服务是否运行
        r = requests.get("http://127.0.0.1:18081/health", timeout=2)
        if r.status_code != 200:
            raise Exception("Service not healthy")
        
        t0 = time.time()
        payload = {"messages": messages, "max_tokens": max_tokens}
        r = requests.post("http://127.0.0.1:18081/v1/chat/completions", json=payload, timeout=60)
        
        if r.status_code == 200:
            data = r.json()
            return {
                "content": data["choices"][0]["message"]["content"],
                "model_used": "local-qwen-int4",
                "latency_ms": round((time.time() - t0) * 1000, 2),
                "tokens": 0,
                "status": "fallback-success",
                "note": "Local fallback (CPU inference)"
            }
    except Exception as e:
        pass
    
    return {"error": "Local fallback failed"}


# ============ 监控接口 ============
def get_model_status() -> Dict:
    """获取所有模型的健康状态"""
    return {
        name: {
            "state": state.circuit_state,
            "health": state.health_score,
            "avg_latency_ms": state.avg_latency,
            "total_requests": state.total_requests,
            "total_failures": state.total_failures,
            "rate_limited": state.rate_limited,
            "last_error": state.last_error
        }
        for name, state in MODEL_STATES.items()
    }


def reset_circuit(model_name: str):
    """手动重置模型电路状态 (用于调试)"""
    if model_name in MODEL_STATES:
        state = MODEL_STATES[model_name]
        state.failures = 0
        state.successes = 0
        state.circuit_state = "CLOSED"
        state.circuit_opened_at = None
        state.rate_limited = False
        print(f"[ManualReset] 🔁 重置模型：{model_name}")


# ============ CLI 测试 ============
if __name__ == "__main__":
    import sys
    
    # 简单的命令行测试
    test_message = [{"role": "user", "content": "你好，一句话介绍你自己"}]
    
    print("🚀 开始测试智能路由...")
    result = smart_route_chat(test_message, max_tokens=50)
    
    print("\n📊 测试结果:")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    print("\n🔍 模型状态:")
    status = get_model_status()
    print(json.dumps(status, ensure_ascii=False, indent=2))
