#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT 统一LLM API调用层
支持多API并行调用、自动故障转移、本地兜底
从云端中枢提取的免费API配置
"""
import requests
import json
import time
import random
from typing import List, Dict, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

# 从云端中枢提取的免费API配置
API_CONFIGS = {
    "siliconflow": {
        "provider": "硅基流动",
        "base_url": "https://api.siliconflow.cn/v1",
        "api_key": "sk-koocoafgyjwbieclpmdlgdycijohbjzgdbkgkxkpmxlbznhw",
        "models": ["Qwen/Qwen2.5-7B-Instruct", "Qwen/Qwen2.5-14B-Instruct", "deepseek-ai/DeepSeek-V2.5"],
        "default_model": "Qwen/Qwen2.5-7B-Instruct",
        "free_tier": True,
        "priority": 1,
        "status": "verified"
    },
    "zhipu_glm": {
        "provider": "智谱AI",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "api_key": "d63c880c0e1b424d8ad242f686e83451.vhHr5d5OQUY5UHNp",
        "models": ["glm-4-flash", "glm-4-plus", "glm-3-turbo"],
        "default_model": "glm-4-flash",
        "free_tier": True,
        "priority": 2,
        "status": "verified"
    },
    "kimi": {
        "provider": "KIMI/Moonshot",
        "base_url": "https://api.moonshot.cn/v1",
        "api_key": "sk-SYGqDrdFHCvk1pN7wxRCUcM2rISny8cFErTDGilcgpFDNiP9",
        "models": ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"],
        "default_model": "moonshot-v1-8k",
        "free_tier": False,
        "priority": 3,
        "status": "verified"
    },
    "agnes": {
        "provider": "Agnes AI",
        "base_url": "https://apihub.agnes-ai.com/v1",
        "api_key": "sk-c15ub0rOGZXa33elApicuNCvyLXXqzRYQY8U7nlzjxSrzywv",
        "models": ["agnes-chat-2.0", "agnes-image-2.1-flash"],
        "default_model": "agnes-chat-2.0",
        "free_tier": True,
        "priority": 4,
        "status": "verified"
    },
}

# 本地7B兜底（GPU大脑）
LOCAL_FALLBACK = {
    "provider": "本地7B兜底",
    "base_url": "http://127.0.0.1:7861",
    "model": "Qwen2.5-7B-Instruct",
    "priority": 100,
    "status": "local"
}

class UnifiedLLMAPI:
    """统一LLM API调用类"""
    
    def __init__(self, primary_api: str = "siliconflow", enable_failover: bool = True):
        self.primary_api = primary_api
        self.enable_failover = enable_failover
        self.api_status = {name: "online" for name in API_CONFIGS.keys()}
        self.call_history = []
    
    def _call_openai_compatible(self, config: Dict, messages: List[Dict], 
                                  model: Optional[str] = None, 
                                  temperature: float = 0.7,
                                  max_tokens: int = 1024,
                                  timeout: int = 60) -> str:
        """调用OpenAI兼容API"""
        url = f"{config['base_url']}/chat/completions"
        headers = {
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model or config["default_model"],
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False
        }
        
        resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    
    def _call_local_fallback(self, messages: List[Dict], 
                               temperature: float = 0.7,
                               max_tokens: int = 1024) -> str:
        """调用本地7B兜底"""
        # 本地GPU大脑用decide接口
        context = messages[-1]["content"] if messages else ""
        resp = requests.post(
            f"{LOCAL_FALLBACK['base_url']}/decide",
            json={"context": context},
            timeout=120
        )
        resp.raise_for_status()
        return resp.json().get("decision", "")
    
    def chat(self, messages: List[Dict], 
             model: Optional[str] = None,
             temperature: float = 0.7,
             max_tokens: int = 1024,
             use_primary_only: bool = False) -> Dict:
        """
        统一聊天接口，支持自动故障转移
        返回: {"content": str, "provider": str, "model": str, "latency": float, "fallback_used": bool}
        """
        start_time = time.time()
        fallback_used = False
        
        # 确定调用顺序
        if use_primary_only:
            api_order = [self.primary_api]
        else:
            # 按优先级排序，主API优先
            api_order = sorted(
                [name for name, cfg in API_CONFIGS.items() if self.api_status.get(name) == "online"],
                key=lambda x: API_CONFIGS[x]["priority"]
            )
            if self.primary_api in api_order:
                api_order.remove(self.primary_api)
                api_order.insert(0, self.primary_api)
        
        last_error = None
        for api_name in api_order:
            config = API_CONFIGS[api_name]
            try:
                content = self._call_openai_compatible(
                    config, messages, model, temperature, max_tokens
                )
                latency = time.time() - start_time
                result = {
                    "content": content,
                    "provider": config["provider"],
                    "api_name": api_name,
                    "model": model or config["default_model"],
                    "latency": latency,
                    "fallback_used": fallback_used
                }
                self.call_history.append(result)
                return result
            except Exception as e:
                last_error = e
                self.api_status[api_name] = "error"
                print(f"  [WARN] {config['provider']} 调用失败: {e}，尝试下一个API...")
                continue
        
        # 所有外部API失败，尝试本地兜底
        if self.enable_failover:
            try:
                print(f"  [INFO] 所有外部API失败，使用本地7B兜底...")
                fallback_used = True
                content = self._call_local_fallback(messages, temperature, max_tokens)
                latency = time.time() - start_time
                result = {
                    "content": content,
                    "provider": LOCAL_FALLBACK["provider"],
                    "api_name": "local_fallback",
                    "model": LOCAL_FALLBACK["model"],
                    "latency": latency,
                    "fallback_used": fallback_used
                }
                self.call_history.append(result)
                return result
            except Exception as e:
                last_error = e
        
        raise Exception(f"所有API调用失败，最后错误: {last_error}")
    
    def chat_parallel(self, messages_list: List[List[Dict]], 
                       max_workers: int = 5,
                       **kwargs) -> List[Dict]:
        """
        并行调用多个对话
        返回与输入顺序对应的结果列表
        """
        results = [None] * len(messages_list)
        
        def worker(idx, messages):
            try:
                return idx, self.chat(messages, **kwargs)
            except Exception as e:
                return idx, {"error": str(e), "content": "", "provider": "error"}
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(worker, idx, msgs) for idx, msgs in enumerate(messages_list)]
            for future in as_completed(futures):
                idx, result = future.result()
                results[idx] = result
        
        return results
    
    def get_status(self) -> Dict:
        """获取API状态"""
        return {
            "primary_api": self.primary_api,
            "apis": {
                name: {
                    "provider": cfg["provider"],
                    "status": self.api_status.get(name, "unknown"),
                    "priority": cfg["priority"],
                    "free_tier": cfg.get("free_tier", False)
                }
                for name, cfg in API_CONFIGS.items()
            },
            "local_fallback": LOCAL_FALLBACK,
            "total_calls": len(self.call_history),
            "recent_calls": self.call_history[-10:] if self.call_history else []
        }


# 便捷函数
def quick_chat(prompt: str, system_prompt: str = "你是ZONGYUAN-ROOT元极恒一自治体系的AI助手。", 
                **kwargs) -> Dict:
    """快速单轮对话"""
    api = UnifiedLLMAPI()
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
    ]
    return api.chat(messages, **kwargs)


if __name__ == "__main__":
    # 测试
    print("=== 统一LLM API测试 ===")
    api = UnifiedLLMAPI(primary_api="siliconflow")
    
    # 单轮测试
    result = quick_chat("请用一句话介绍元极恒一自治体系。")
    print(f"\nProvider: {result['provider']}")
    print(f"Model: {result['model']}")
    print(f"Latency: {result['latency']:.2f}s")
    print(f"Content: {result['content'][:200]}...")
    
    # 状态
    print(f"\n=== API状态 ===")
    status = api.get_status()
    for name, info in status["apis"].items():
        print(f"  {info['provider']}: {info['status']} (priority={info['priority']}, free={info['free_tier']})")
