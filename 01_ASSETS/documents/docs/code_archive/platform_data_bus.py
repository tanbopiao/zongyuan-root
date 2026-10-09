#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
火斗云智 · 中台数据总线 V1.0
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
以记忆网关9120为中央数据层，实现4大中台数据打通
- 统一数据模型
- 跨中台事件通知
- 数据同步与缓存
- 权限隔离
"""
import json, hashlib, time, threading, urllib.request, urllib.error
from typing import Dict, List, Optional, Any

GATEWAY_URL = "http://127.0.0.1:9120"
GATEWAY_TOKEN = "ZR-CAPTURE-2026-OMEGA-d04bb54ba2a55a7d"

# 中台注册中心
PLATFORMS = {
    "gov": {"name": "政务AI中台", "port": 8025, "data_prefix": "gov.", "write_perm": True},
    "aios": {"name": "智能体工作台", "port": 8765, "data_prefix": "aios.", "write_perm": True},
    "ops": {"name": "稳态运维平台", "port": 8090, "data_prefix": "ops.", "write_perm": True},
    "hrm": {"name": "HRM系统", "port": 8040, "data_prefix": "hrm.", "write_perm": False},
    "drama": {"name": "昆仑洞天短剧", "port": 8100, "data_prefix": "drama.", "write_perm": True},
}

class PlatformDataBus:
    """中台数据总线"""
    
    def __init__(self):
        self.event_handlers: Dict[str, List] = {}
        self.local_cache: Dict[str, Any] = {}
        self.cache_ttl = 300  # 5分钟缓存
    
    def _gateway_request(self, path: str, method: str = "GET", data: dict = None) -> dict:
        """请求记忆网关"""
        url = f"{GATEWAY_URL}{path}"
        headers = {"Content-Type": "application/json", "X-Capture-Token": GATEWAY_TOKEN}
        try:
            req = urllib.request.Request(url, data=json.dumps(data).encode() if data else None,
                                         headers=headers, method=method)
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            return {"error": str(e)}
    
    def write_truth(self, platform: str, key: str, content: str, meta: dict = None) -> dict:
        """中台写入真值到中央数据层"""
        if platform not in PLATFORMS:
            return {"error": f"未知中台: {platform}"}
        if not PLATFORMS[platform]["write_perm"]:
            return {"error": f"{platform} 无写入权限"}
        
        full_key = f"{PLATFORMS[platform]['data_prefix']}{key}"
        payload = {
            "node_id": f"platform-{platform}",
            "DID": "DID-BR-000002",
            "truth_type": "platform_data",
            "truth_content": content,
            "meta": meta or {}
        }
        result = self._gateway_request("/api/gateway/report", "POST", payload)
        # 触发事件
        self._emit_event("data_written", {"platform": platform, "key": full_key})
        return result
    
    def read_truth(self, platform: str, key: str) -> dict:
        """中台读取真值（可跨中台读取）"""
        full_key = f"{PLATFORMS.get(platform, {}).get('data_prefix', '')}{key}"
        cache_key = f"read:{full_key}"
        if cache_key in self.local_cache:
            cached = self.local_cache[cache_key]
            if time.time() - cached["ts"] < self.cache_ttl:
                return cached["data"]
        result = self._gateway_request(f"/api/truth/get?key={full_key}")
        self.local_cache[cache_key] = {"ts": time.time(), "data": result}
        return result
    
    def query_platform_data(self, platform: str, limit: int = 50) -> dict:
        """查询某中台的全部数据"""
        prefix = PLATFORMS.get(platform, {}).get("data_prefix", "")
        return self._gateway_request(f"/api/truth/list?prefix={prefix}&limit={limit}")
    
    def cross_platform_query(self, source_platform: str, target_platform: str, key: str) -> dict:
        """跨中台数据查询（带权限校验）"""
        source = PLATFORMS.get(source_platform)
        target = PLATFORMS.get(target_platform)
        if not source or not target:
            return {"error": "未知中台"}
        # 权限规则：政务数据仅内部可读，运维数据全平台可读
        if target_platform == "gov" and source_platform not in ["gov", "ops"]:
            return {"error": f"{source_platform} 无权读取政务数据"}
        return self.read_truth(target_platform, key)
    
    def register_event_handler(self, event: str, handler) -> None:
        """注册事件处理器"""
        if event not in self.event_handlers:
            self.event_handlers[event] = []
        self.event_handlers[event].append(handler)
    
    def _emit_event(self, event: str, data: dict) -> None:
        """触发事件"""
        for handler in self.event_handlers.get(event, []):
            try:
                threading.Thread(target=handler, args=(data,), daemon=True).start()
            except Exception:
                pass
    
    def get_platform_status(self) -> dict:
        """获取所有中台数据状态"""
        status = {}
        for pid, pinfo in PLATFORMS.items():
            data = self.query_platform_data(pid, limit=1)
            status[pid] = {
                "name": pinfo["name"],
                "port": pinfo["port"],
                "write_perm": pinfo["write_perm"],
                "data_prefix": pinfo["data_prefix"],
                "gateway_reachable": "error" not in data
            }
        return status
    
    def sync_all_platforms(self) -> dict:
        """全量同步所有中台数据到中央层"""
        results = {}
        for pid in PLATFORMS:
            results[pid] = self._sync_platform(pid)
        return results
    
    def _sync_platform(self, platform: str) -> dict:
        """同步单个中台数据"""
        pinfo = PLATFORMS[platform]
        try:
            # 从中台API拉取数据写入网关
            url = f"http://127.0.0.1:{pinfo['port']}/api/export"
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
            count = 0
            for item in data.get("items", []):
                self.write_truth(platform, item["key"], item["content"], item.get("meta"))
                count += 1
            return {"synced": count, "status": "ok"}
        except Exception as e:
            return {"synced": 0, "status": "skip", "reason": str(e)[:100]}


# 标准数据模型
STANDARD_DATA_MODEL = {
    "task": {"fields": ["task_id", "platform", "type", "status", "created_at", "updated_at", "result"], "index": ["task_id", "status"]},
    "alert": {"fields": ["alert_id", "level", "source", "message", "timestamp", "acknowledged"], "index": ["level", "timestamp"]},
    "metric": {"fields": ["metric_name", "platform", "value", "unit", "timestamp"], "index": ["metric_name", "platform"]},
    "config": {"fields": ["config_key", "platform", "value", "version", "updated_at"], "index": ["config_key", "platform"]},
    "audit": {"fields": ["audit_id", "action", "operator", "target", "result", "timestamp"], "index": ["action", "timestamp"]},
}

if __name__ == "__main__":
    bus = PlatformDataBus()
    print("=== 火斗云智中台数据总线 V1.0 ===")
    print("中央数据层: 记忆网关 9120")
    print(f"已注册中台: {len(PLATFORMS)} 个")
    for pid, p in PLATFORMS.items():
        print(f"  - {pid}: {p['name']} (端口{p['port']}, 前缀{p['data_prefix']})")
    print(f"\n标准数据模型: {len(STANDARD_DATA_MODEL)} 类")
    for model in STANDARD_DATA_MODEL:
        print(f"  - {model}: {len(STANDARD_DATA_MODEL[model]['fields'])} 字段")
