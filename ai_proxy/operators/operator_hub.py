#!/usr/bin/env python3
"""V2.0.0: 算子底座统一调度层（Operator Hub）
多窗口协同核心：政务/短剧/云运维共享同一套算子底座，统一注册、调度、监控、缓存"""
import json, os, sys, time, hashlib, threading
from collections import OrderedDict

sys.path.insert(0, "/opt/ZONGYUAN-ROOT/ai_proxy")
WINDOWS_REGISTRY_FILE = "/opt/ZONGYUAN-ROOT/operator_hub_windows.json"
from operators import get_registry

class OperatorHub:
    """算子底座统一调度层 - 多窗口共享"""
    
    def __init__(self):
        self.registry = get_registry()
        self.window_registry = {}  # 窗口ID → 窗口信息
        self.call_stats = {}  # 算子调用统计
        self.lock = threading.Lock()
        self._load_windows()
        self.hub_cache = OrderedDict()  # 跨窗口共享缓存
        self.max_cache = 200
        self.cache_ttl = 600  # 10分钟
    
    def _load_windows(self):
        """从文件加载已注册窗口"""
        if os.path.exists(WINDOWS_REGISTRY_FILE):
            try:
                with open(WINDOWS_REGISTRY_FILE) as f:
                    self.window_registry = json.load(f)
            except:
                pass
    
    def _save_windows(self):
        """保存窗口注册信息到文件"""
        with open(WINDOWS_REGISTRY_FILE, "w") as f:
            json.dump(self.window_registry, f, ensure_ascii=False, indent=2)
    
    def register_window(self, window_id, window_name, domain, capabilities):
        """注册专业窗口到算子底座"""
        with self.lock:
            self.window_registry[window_id] = {
                "window_id": window_id,
                "window_name": window_name,
                "domain": domain,
                "capabilities": capabilities,
                "registered_at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
                "last_active": time.strftime("%Y-%m-%dT%H:%M:%S+08:00")
            }
        self._save_windows()
        return {"success": True, "window_id": window_id}
    
    def call(self, window_id, group, operator, params=None, **kwargs):
        """窗口调用算子（带权限检查和统计）"""
        # 窗口权限检查
        with self.lock:
            win = self.window_registry.get(window_id)
            if not win:
                return {"success": False, "error": "window_not_registered", "window_id": window_id}
            win["last_active"] = time.strftime("%Y-%m-%dT%H:%M:%S+08:00")
            
            # 展开params字典
            if isinstance(params, dict):
                kwargs.update(params)
            # 统计
            key = "%s.%s" % (group, operator)
            self.call_stats[key] = self.call_stats.get(key, 0) + 1
            
            # 跨窗口缓存检查
            cache_key = hashlib.md5(("%s:%s:%s" % (group, operator, json.dumps(kwargs, sort_keys=True, default=str))).encode()).hexdigest()
            if cache_key in self.hub_cache:
                entry = self.hub_cache[cache_key]
                if time.time() - entry["time"] < self.cache_ttl:
                    self.hub_cache.move_to_end(cache_key)
                    return entry["result"]
                else:
                    del self.hub_cache[cache_key]
        
        # 执行算子
        result = self.registry.call(group, operator, **kwargs)
        
        # 成功结果入缓存
        if result.get("success"):
            with self.lock:
                self.hub_cache[cache_key] = {"result": result, "time": time.time()}
                self.hub_cache.move_to_end(cache_key)
                while len(self.hub_cache) > self.max_cache:
                    self.hub_cache.popitem(last=False)
        
        return result
    
    def list_windows(self):
        """列出所有注册窗口"""
        with self.lock:
            return list(self.window_registry.values())
    
    def get_stats(self):
        """获取算子底座统计"""
        with self.lock:
            return {
                "registered_windows": len(self.window_registry),
                "total_calls": sum(self.call_stats.values()),
                "call_stats": dict(self.call_stats),
                "cache_size": len(self.hub_cache),
                "cache_max": self.max_cache,
                "operator_groups": self.registry.list_all()
            }

# 全局单例
operator_hub = OperatorHub()

# 预注册短剧母机窗口
operator_hub.register_window(
    "window-drama-machine",
    "昆仑洞天短剧生产工业母机",
    "drama_production",
    ["script_generation", "storyboard", "keyframe", "video_generation", "tts", "merge", "storage"]
)

if __name__ == "__main__":
    print(json.dumps(operator_hub.get_stats(), ensure_ascii=False, indent=2))
