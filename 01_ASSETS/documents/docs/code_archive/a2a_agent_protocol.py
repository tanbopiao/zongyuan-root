#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
火斗云智 · A2A智能体通讯协议 V1.0
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
标准化消息信封 + DID签名 + ACK回执 + 任务分发 + 幂等校验
"""
import json, hashlib, time, uuid, threading
from typing import Dict, List, Optional, Callable
from enum import Enum

class MessageType(Enum):
    TASK_DISPATCH = "task_dispatch"      # 任务下发
    TASK_PROGRESS = "task_progress"      # 进度上报
    TASK_RESULT = "task_result"          # 结果回执
    HEARTBEAT = "heartbeat"              # 心跳
    REGISTER = "register"                # 注册
    ACK = "ack"                          # 确认
    ERROR = "error"                      # 错误
    BROADCAST = "broadcast"              # 广播

class AgentRole(Enum):
    ORCHESTRATOR = "orchestrator"    # 编排者
    WORKER = "worker"               # 工作者
    MONITOR = "monitor"             # 监控者
    GATEWAY = "gateway"             # 网关

class MessageEnvelope:
    """标准化消息信封"""
    
    def __init__(self, msg_type: MessageType, sender_did: str, receiver_did: str, 
                 payload: dict, sender_role: AgentRole = AgentRole.WORKER):
        self.msg_id = str(uuid.uuid4())
        self.msg_type = msg_type.value
        self.sender_did = sender_did
        self.receiver_did = receiver_did
        self.sender_role = sender_role.value
        self.payload = payload
        self.timestamp = time.time()
        self.signature = self._sign()
        self.ack_required = msg_type in [MessageType.TASK_DISPATCH, MessageType.TASK_RESULT]

    def _sign(self) -> str:
        """DID签名"""
        sign_raw = f"{self.msg_id}{self.msg_type}{self.sender_did}{self.receiver_did}{json.dumps(self.payload, sort_keys=True)}{self.timestamp}"
        return hashlib.sha256(sign_raw.encode("utf-8")).hexdigest()

    def verify(self) -> bool:
        """验签"""
        new_sign = self._sign()
        return new_sign == self.signature

    def to_dict(self) -> dict:
        return {
            "msg_id": self.msg_id,
            "msg_type": self.msg_type,
            "sender_did": self.sender_did,
            "receiver_did": self.receiver_did,
            "sender_role": self.sender_role,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "datetime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.timestamp)),
            "signature": self.signature,
            "ack_required": self.ack_required
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'MessageEnvelope':
        msg = cls.__new__(cls)
        msg.msg_id = data["msg_id"]
        msg.msg_type = data["msg_type"]
        msg.sender_did = data["sender_did"]
        msg.receiver_did = data["receiver_did"]
        msg.sender_role = data["sender_role"]
        msg.payload = data["payload"]
        msg.timestamp = data["timestamp"]
        msg.signature = data["signature"]
        msg.ack_required = data.get("ack_required", False)
        return msg

class AgentRegistry:
    """智能体注册中心"""
    
    def __init__(self):
        self.agents: Dict[str, dict] = {}
        self._lock = threading.Lock()

    def register(self, agent_id: str, did: str, role: AgentRole, 
                 capabilities: List[str], endpoint: str = None) -> dict:
        """注册智能体"""
        with self._lock:
            self.agents[agent_id] = {
                "agent_id": agent_id,
                "did": did,
                "role": role.value,
                "capabilities": capabilities,
                "endpoint": endpoint,
                "registered_at": time.time(),
                "last_heartbeat": time.time(),
                "status": "active",
                "tasks_completed": 0,
                "tasks_failed": 0
            }
            return self.agents[agent_id]

    def unregister(self, agent_id: str):
        with self._lock:
            if agent_id in self.agents:
                self.agents[agent_id]["status"] = "inactive"

    def heartbeat(self, agent_id: str) -> bool:
        with self._lock:
            if agent_id in self.agents:
                self.agents[agent_id]["last_heartbeat"] = time.time()
                self.agents[agent_id]["status"] = "active"
                return True
            return False

    def get_available_agents(self, capability: str = None) -> List[dict]:
        """获取可用智能体"""
        now = time.time()
        agents = []
        for a in self.agents.values():
            if a["status"] == "active" and (now - a["last_heartbeat"]) < 60:
                if capability is None or capability in a["capabilities"]:
                    agents.append(a)
        return agents

    def get_all(self) -> List[dict]:
        return list(self.agents.values())

class TaskDispatcher:
    """任务分发器（负载均衡）"""
    
    def __init__(self, registry: AgentRegistry):
        self.registry = registry
        self.task_queue: List[dict] = []
        self.processed_tasks: Dict[str, dict] = {}
        self._lock = threading.Lock()
        self._idempotency_keys = set()

    def dispatch(self, task: dict, capability: str = None) -> Optional[dict]:
        """分发任务到合适的智能体"""
        # 幂等校验
        idem_key = hashlib.md5(json.dumps(task, sort_keys=True).encode()).hexdigest()
        if idem_key in self._idempotency_keys:
            return {"status": "duplicate", "task_id": task.get("task_id")}
        self._idempotency_keys.add(idem_key)

        agents = self.registry.get_available_agents(capability)
        if not agents:
            with self._lock:
                self.task_queue.append(task)
            return {"status": "queued", "reason": "no_available_agent"}

        # 轮询负载均衡
        agent = agents[len(self.processed_tasks) % len(agents)]
        task["assigned_to"] = agent["agent_id"]
        task["dispatched_at"] = time.time()
        task["status"] = "dispatched"
        
        with self._lock:
            self.processed_tasks[task["task_id"]] = task
        
        return {
            "status": "dispatched",
            "task_id": task["task_id"],
            "assigned_to": agent["agent_id"],
            "agent_did": agent["did"]
        }

    def complete_task(self, task_id: str, result: dict, agent_id: str):
        """任务完成"""
        with self._lock:
            if task_id in self.processed_tasks:
                self.processed_tasks[task_id]["status"] = "completed"
                self.processed_tasks[task_id]["result"] = result
                self.processed_tasks[task_id]["completed_at"] = time.time()
                if agent_id in self.registry.agents:
                    self.registry.agents[agent_id]["tasks_completed"] += 1

    def fail_task(self, task_id: str, error: str, agent_id: str):
        with self._lock:
            if task_id in self.processed_tasks:
                self.processed_tasks[task_id]["status"] = "failed"
                self.processed_tasks[task_id]["error"] = error
                if agent_id in self.registry.agents:
                    self.registry.agents[agent_id]["tasks_failed"] += 1

class A2AProtocol:
    """A2A协议主类"""
    
    def __init__(self, agent_id: str, did: str, role: AgentRole):
        self.agent_id = agent_id
        self.did = did
        self.role = role
        self.registry = AgentRegistry()
        self.dispatcher = TaskDispatcher(self.registry)
        self.message_log: List[dict] = []
        self.handlers: Dict[str, Callable] = {}
        self._lock = threading.Lock()

    def register_handler(self, msg_type: str, handler: Callable):
        """注册消息处理器"""
        self.handlers[msg_type] = handler

    def send_message(self, receiver_did: str, msg_type: MessageType, 
                     payload: dict) -> MessageEnvelope:
        """发送消息"""
        msg = MessageEnvelope(msg_type, self.did, receiver_did, payload, self.role)
        with self._lock:
            self.message_log.append(msg.to_dict())
        return msg

    def receive_message(self, msg_data: dict) -> dict:
        """接收并处理消息"""
        msg = MessageEnvelope.from_dict(msg_data)
        
        # 验签
        if not msg.verify():
            return {"status": "error", "reason": "signature_invalid"}

        # 幂等校验
        if msg.msg_id in [m["msg_id"] for m in self.message_log[-100:]]:
            return {"status": "duplicate", "msg_id": msg.msg_id}

        # ACK
        if msg.ack_required:
            ack = self.send_message(msg.sender_did, MessageType.ACK, 
                                    {"ack_msg_id": msg.msg_id, "status": "received"})

        # 路由到处理器
        handler = self.handlers.get(msg.msg_type)
        if handler:
            try:
                result = handler(msg)
                return {"status": "processed", "result": result, "msg_id": msg.msg_id}
            except Exception as e:
                return {"status": "error", "reason": str(e), "msg_id": msg.msg_id}
        
        return {"status": "received", "msg_id": msg.msg_id}

    def get_status(self) -> dict:
        """获取协议状态"""
        return {
            "agent_id": self.agent_id,
            "did": self.did,
            "role": self.role.value,
            "registered_agents": len(self.registry.get_all()),
            "active_agents": len(self.registry.get_available_agents()),
            "messages_processed": len(self.message_log),
            "tasks_in_queue": len(self.dispatcher.task_queue),
            "tasks_completed": sum(1 for t in self.dispatcher.processed_tasks.values() if t["status"] == "completed"),
            "did": "DID-BR-000002",
            "trace": "Ω₀⊂⊙∞⊂Ω"
        }


# 标准智能体能力定义
STANDARD_CAPABILITIES = {
    "drama_production": "短剧生产",
    "gov_operations": "政务运算",
    "decision_making": "决策推理",
    "research": "研究调研",
    "monitoring": "监控运维",
    "data_processing": "数据处理",
    "content_generation": "内容生成",
    "code_development": "代码开发",
    "legal_review": "法律审查",
    "archive_lock": "归档锁档"
}

if __name__ == "__main__":
    print("=== 火斗云智 A2A智能体通讯协议 V1.0 ===")
    print(f"DID: DID-BR-000002 | 溯源: Ω₀⊂⊙∞⊂Ω")
    print()

    # 创建编排者
    orchestrator = A2AProtocol("orch-001", "DID-BR-000002", AgentRole.ORCHESTRATOR)
    
    # 注册工作者智能体
    orchestrator.registry.register("worker-001", "DID-BR-000003", AgentRole.WORKER, 
                                    ["drama_production", "content_generation"])
    orchestrator.registry.register("worker-002", "DID-BR-000004", AgentRole.WORKER,
                                    ["gov_operations", "data_processing"])
    orchestrator.registry.register("worker-003", "DID-BR-000005", AgentRole.WORKER,
                                    ["decision_making", "research"])
    
    print(f"已注册智能体: {len(orchestrator.registry.get_all())} 个")
    for a in orchestrator.registry.get_all():
        print(f"  - {a['agent_id']}: {a['role']} | 能力: {a['capabilities']}")
    
    # 测试消息
    print("\n消息测试:")
    msg = orchestrator.send_message("DID-BR-000003", MessageType.TASK_DISPATCH,
                                     {"task_id": "T-001", "type": "drama_production", 
                                      "content": "生成短剧分镜表"})
    print(f"  消息ID: {msg.msg_id}")
    print(f"  签名有效: {msg.verify()}")
    print(f"  需ACK: {msg.ack_required}")
    
    # 测试任务分发
    print("\n任务分发测试:")
    result = orchestrator.dispatcher.dispatch(
        {"task_id": "T-001", "type": "drama", "content": "测试"},
        capability="drama_production"
    )
    print(f"  分发结果: {result['status']}")
    print(f"  分配给: {result.get('assigned_to', 'N/A')}")
    
    # 幂等测试
    result2 = orchestrator.dispatcher.dispatch(
        {"task_id": "T-001", "type": "drama", "content": "测试"},
        capability="drama_production"
    )
    print(f"  重复任务: {result2['status']}")
    
    # 状态
    print(f"\n协议状态: {json.dumps(orchestrator.get_status(), indent=2, ensure_ascii=False)}")
