#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
贝叶斯五行闭环引擎 - 9120真值网关集成
负责与记忆网关的所有交互：读写真值、节点注册、心跳
"""

import json
import time
import logging
import urllib.request
import urllib.error
from typing import Optional, Dict, List, Any

from config import (
    TRUTH_GATEWAY_BASE_URL, TRUTH_GATEWAY_TIMEOUT,
    TRUTH_GATEWAY_NODE_ID, ENGINE_DID, ENGINE_ROOT_OMEGA
)

logger = logging.getLogger("BayesianLoop.TruthGateway")


class TruthGateway:
    """9120真值网关客户端"""

    def __init__(self, base_url: str = None, timeout: int = None):
        self.base_url = base_url or TRUTH_GATEWAY_BASE_URL
        self.timeout = timeout or TRUTH_GATEWAY_TIMEOUT
        self.node_id = TRUTH_GATEWAY_NODE_ID
        self._registered = False

    def _request(self, method: str, path: str, data: dict = None) -> Optional[dict]:
        """发送HTTP请求到真值网关"""
        url = f"{self.base_url}{path}"
        try:
            req = urllib.request.Request(url, method=method)
            req.add_header("Content-Type", "application/json")
            if data:
                req.data = json.dumps(data, ensure_ascii=False).encode("utf-8")
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as e:
            logger.error(f"真值网关请求失败 {method} {path}: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"真值网关响应解析失败: {e}")
            return None
        except Exception as e:
            logger.error(f"真值网关未知错误: {e}")
            return None

    # ============ 真值操作 ============

    def upsert_truth(self, key: str, value: Any, category: str = "general",
                     node_id: str = None) -> bool:
        """写入/更新真值"""
        if isinstance(value, (dict, list)):
            value_str = json.dumps(value, ensure_ascii=False)
        else:
            value_str = str(value)
        data = {
            "key": key,
            "value": value_str,
            "node_id": node_id or self.node_id,
            "category": category
        }
        result = self._request("POST", "/api/truth/upsert", data)
        if result and (result.get("status") == "ok" or result.get("success") is True):
            logger.debug(f"真值写入成功: {key}")
            return True
        logger.warning(f"真值写入失败: {key}, 响应: {result}")
        return False

    def get_truth(self, key: str) -> Optional[dict]:
        """读取单条真值"""
        result = self._request("GET", f"/api/truth/{key}")
        if result and result.get("status") == "ok":
            return result.get("truth", result)
        return None

    def list_truths(self, prefix: str = None, category: str = None) -> List[str]:
        """列出真值key列表"""
        result = self._request("GET", "/api/truths")
        if not result:
            return []
        truths = result if isinstance(result, list) else result.get("truths", [])
        if prefix:
            truths = [t for t in truths if t.startswith(prefix)]
        return truths

    def search_truths(self, keyword: str) -> List[str]:
        """搜索包含关键词的真值"""
        all_truths = self.list_truths()
        return [t for t in all_truths if keyword.lower() in t.lower()]

    # ============ 节点操作 ============

    def register_node(self, capabilities: List[str] = None) -> bool:
        """注册节点（需要同源认证）"""
        data = {
            "node_id": self.node_id,
            "node_type": "bayesian_engine",
            "capabilities": capabilities or ["bayesian_update", "divergence", "convergence", "iteration", "entropy_reduction"],
            "DID": ENGINE_DID,
            "ROOT_OMEGA": ENGINE_ROOT_OMEGA
        }
        result = self._request("POST", "/api/node/register", data)
        if result and result.get("status") == "ok":
            self._registered = True
            logger.info(f"节点注册成功: {self.node_id}")
            return True
        logger.warning(f"节点注册失败: {result}")
        return False

    def send_heartbeat(self) -> bool:
        """发送节点心跳"""
        data = {
            "node_id": self.node_id,
            "DID": ENGINE_DID,
            "ROOT_OMEGA": ENGINE_ROOT_OMEGA
        }
        result = self._request("POST", "/api/node/heartbeat", data)
        return result is not None and result.get("status") == "ok"

    def get_nodes(self) -> dict:
        """获取所有节点状态"""
        result = self._request("GET", "/api/nodes")
        return result or {}

    # ============ 状态查询 ============

    def get_status(self) -> dict:
        """获取网关状态"""
        result = self._request("GET", "/api/status")
        return result or {}

    def is_online(self) -> bool:
        """检查网关是否在线"""
        try:
            req = urllib.request.Request(f"{self.base_url}/api/status", method="GET")
            with urllib.request.urlopen(req, timeout=3) as resp:
                return resp.status == 200
        except Exception:
            return False

    # ============ 批量操作 ============

    def batch_upsert(self, truths: List[Dict[str, Any]], category: str = "batch") -> int:
        """批量写入真值，返回成功数量"""
        success = 0
        for t in truths:
            if self.upsert_truth(t["key"], t["value"], t.get("category", category)):
                success += 1
            time.sleep(0.01)  # 避免请求过快
        return success

    def get_truths_batch(self, keys: List[str]) -> Dict[str, dict]:
        """批量读取真值"""
        result = {}
        for key in keys:
            truth = self.get_truth(key)
            if truth:
                result[key] = truth
        return result
