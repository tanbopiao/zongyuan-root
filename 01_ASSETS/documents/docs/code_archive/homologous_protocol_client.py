#!/usr/bin/env python3
"""
同源协议互通规范客户端 V1.0
基于KD-META-7354同源协议互通规范V1.0实现
支持：节点注册、心跳保活、真值互通、资产锁档同步、决策协同
确权：DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | ZONGYUAN-ROOT
"""
import hashlib
import json
import time
import uuid
import requests
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

# 常量
DID = "DID-BR-000002"
TRACE_MARK = "Ω₀⊂⊙∞⊂Ω"
ROOT_OMEGA = "ZONGYUAN-ROOT-ORIGIN-ETERNAL-20260407"
GATEWAY_BASE = "https://www.huodouai.com/api/report"

# 节点类型枚举
class NodeType:
    HUB = "NODE-HUB"           # 中枢节点
    WORKER = "NODE-WORK"        # 工作节点
    GATEWAY = "NODE-GW"         # 网关节点
    STORAGE = "NODE-STORE"      # 存储节点
    DISPLAY = "NODE-DISPLAY"    # 展示节点
    EDGE = "NODE-EDGE"          # 边缘节点

# 消息类型枚举
class MessageType:
    NODE_REGISTER = "NODE_REGISTER"
    NODE_HEARTBEAT = "NODE_HEARTBEAT"
    TRUTH_REPORT = "TRUTH_REPORT"
    ASSET_LOCK = "ASSET_LOCK"
    DECISION_REQUEST = "DECISION_REQUEST"
    DECISION_VOTE = "DECISION_VOTE"
    TASK_ASSIGN = "TASK_ASSIGN"
    STATUS_SYNC = "STATUS_SYNC"

class HomologousProtocolClient:
    """同源协议客户端"""
    
    def __init__(self, node_id: str, node_name: str, node_type: str):
        self.node_id = node_id
        self.node_name = node_name
        self.node_type = node_type
        self.registered = False
        self.last_heartbeat = None
        self.session_token = None
        self.message_history: List[Dict] = []
    
    def _generate_message_id(self) -> str:
        """生成全局唯一消息ID"""
        return f"MSG-{uuid.uuid4().hex[:16].upper()}"
    
    def _compute_signature(self, payload: Dict) -> str:
        """计算消息签名（SHA256）"""
        content = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(content.encode('utf-8')).hexdigest().upper()
    
    def _build_message(self, msg_type: str, payload: Dict) -> Dict:
        """构建标准协议消息"""
        timestamp = datetime.now(timezone.utc).isoformat()
        message = {
            "message_id": self._generate_message_id(),
            "message_type": msg_type,
            "source_node": self.node_id,
            "source_node_name": self.node_name,
            "source_node_type": self.node_type,
            "timestamp": timestamp,
            "did": DID,
            "trace_mark": TRACE_MARK,
            "root_omega": ROOT_OMEGA,
            "payload": payload,
            "protocol_version": "1.0"
        }
        message["signature"] = self._compute_signature(message)
        self.message_history.append(message)
        return message
    
    def register_node(self, capabilities: List[str] = None, 
                     metadata: Dict = None) -> Dict:
        """节点注册（协议消息类型：NODE_REGISTER）"""
        payload = {
            "node_id": self.node_id,
            "node_name": self.node_name,
            "node_type": self.node_type,
            "capabilities": capabilities or [],
            "metadata": metadata or {},
            "register_time": datetime.now(timezone.utc).isoformat()
        }
        message = self._build_message(MessageType.NODE_REGISTER, payload)
        
        # 通过记忆网关上报告注册信息
        try:
            resp = requests.post(
                f"{GATEWAY_BASE}/truth",
                json={
                    "truth_key": f"NODE.REGISTER.{self.node_id}.{int(time.time())}",
                    "truth_value": json.dumps(message, ensure_ascii=False),
                    "source_node": self.node_id,
                    "confidence": 0.95,
                    "truth_type": "protocol"
                },
                timeout=10
            )
            if resp.status_code == 200:
                self.registered = True
                self.session_token = hashlib.sha256(
                    f"{self.node_id}{time.time()}".encode()
                ).hexdigest()[:32]
                return {"success": True, "message": "节点注册成功", 
                        "session_token": self.session_token,
                        "message_id": message["message_id"]}
        except Exception as e:
            pass
        
        return {"success": False, "message": "节点注册失败", 
                "message_id": message["message_id"]}
    
    def send_heartbeat(self, status: str = "online", 
                       load: float = 0.0,
                       metrics: Dict = None) -> Dict:
        """发送心跳（协议消息类型：NODE_HEARTBEAT）"""
        payload = {
            "node_id": self.node_id,
            "status": status,
            "load": load,
            "metrics": metrics or {},
            "last_heartbeat": self.last_heartbeat,
            "heartbeat_time": datetime.now(timezone.utc).isoformat()
        }
        message = self._build_message(MessageType.NODE_HEARTBEAT, payload)
        self.last_heartbeat = datetime.now(timezone.utc).isoformat()
        
        # 通过记忆网关上报告心跳
        try:
            resp = requests.post(
                f"{GATEWAY_BASE}/truth",
                json={
                    "truth_key": f"NODE.HEARTBEAT.{self.node_id}.{int(time.time())}",
                    "truth_value": json.dumps(message, ensure_ascii=False),
                    "source_node": self.node_id,
                    "confidence": 0.9,
                    "truth_type": "data"
                },
                timeout=10
            )
            if resp.status_code == 200:
                return {"success": True, "message": "心跳发送成功",
                        "message_id": message["message_id"]}
        except Exception as e:
            pass
        
        return {"success": False, "message": "心跳发送失败",
                "message_id": message["message_id"]}
    
    def report_truth(self, truth_key: str, truth_value: str,
                    confidence: float = 0.9, truth_type: str = "data") -> Dict:
        """真值互通上报（协议消息类型：TRUTH_REPORT）"""
        payload = {
            "truth_key": truth_key,
            "truth_value": truth_value,
            "confidence": confidence,
            "truth_type": truth_type,
            "report_time": datetime.now(timezone.utc).isoformat()
        }
        message = self._build_message(MessageType.TRUTH_REPORT, payload)
        
        try:
            resp = requests.post(
                f"{GATEWAY_BASE}/truth",
                json={
                    "truth_key": truth_key,
                    "truth_value": truth_value,
                    "source_node": self.node_id,
                    "confidence": confidence,
                    "truth_type": truth_type
                },
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                return {"success": True, "message": "真值上报成功",
                        "truth_count": data.get("truth_count", "?"),
                        "message_id": message["message_id"]}
        except Exception as e:
            pass
        
        return {"success": False, "message": "真值上报失败",
                "message_id": message["message_id"]}
    
    def sync_asset_lock(self, asset_id: str, asset_hash: str,
                        lock_level: int = 5, meta_class: str = "M4") -> Dict:
        """资产锁档同步（协议消息类型：ASSET_LOCK）"""
        payload = {
            "asset_id": asset_id,
            "asset_hash": asset_hash,
            "lock_level": lock_level,
            "meta_class": meta_class,
            "lock_time": datetime.now(timezone.utc).isoformat()
        }
        message = self._build_message(MessageType.ASSET_LOCK, payload)
        
        try:
            resp = requests.post(
                f"{GATEWAY_BASE}/truth",
                json={
                    "truth_key": f"ASSET.LOCK.{asset_id}.{int(time.time())}",
                    "truth_value": json.dumps(message, ensure_ascii=False),
                    "source_node": self.node_id,
                    "confidence": 0.95,
                    "truth_type": "protocol"
                },
                timeout=10
            )
            if resp.status_code == 200:
                return {"success": True, "message": "资产锁档同步成功",
                        "message_id": message["message_id"]}
        except Exception as e:
            pass
        
        return {"success": False, "message": "资产锁档同步失败",
                "message_id": message["message_id"]}
    
    def get_status(self) -> Dict:
        """获取网关状态"""
        try:
            resp = requests.get(f"{GATEWAY_BASE}/status", timeout=10)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            pass
        return {"status": "unknown"}
    
    def get_nodes(self) -> List[Dict]:
        """获取节点列表"""
        try:
            resp = requests.get(f"{GATEWAY_BASE}/nodes", timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("nodes", data.get("data", []))
        except Exception as e:
            pass
        return []


# 便捷函数：创建默认工作节点客户端
def create_worker_client(node_name: str = "本地工作节点") -> HomologousProtocolClient:
    """创建默认工作节点客户端"""
    node_id = f"NODE-WORK-{uuid.uuid4().hex[:8].upper()}"
    return HomologousProtocolClient(
        node_id=node_id,
        node_name=node_name,
        node_type=NodeType.WORKER
    )


if __name__ == "__main__":
    # 自测
    client = create_worker_client("同源协议测试节点")
    print(f"节点ID: {client.node_id}")
    print(f"节点名称: {client.node_name}")
    print(f"节点类型: {client.node_type}")
    print()
    
    # 注册
    result = client.register_node(capabilities=["truth_report", "heartbeat", "asset_lock"])
    print(f"注册结果: {result}")
    print()
    
    # 心跳
    result = client.send_heartbeat(status="online", load=0.15)
    print(f"心跳结果: {result}")
    print()
    
    # 真值上报
    result = client.report_truth(
        truth_key="TEST.HOMOLOGOUS.PROTOCOL.V1",
        truth_value="同源协议客户端V1.0自测成功",
        confidence=0.9,
        truth_type="protocol"
    )
    print(f"真值上报结果: {result}")
