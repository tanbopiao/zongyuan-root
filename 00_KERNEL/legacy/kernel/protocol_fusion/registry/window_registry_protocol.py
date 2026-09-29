#!/usr/bin/env python3
"""
多窗口注册协议标准 - 定义窗口注册/发现/通信/协作的标准协议
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from enum import Enum
import hashlib
import time
import json
import uuid


class WindowRole(Enum):
    """窗口角色枚举"""
    KERNEL_ARCHITECT = "kernel_architect"       # 内核架构师（根窗口）
    GOV_AI = "gov_ai"                           # 政务AI
    DRAMA_PRODUCTION = "drama_production"       # 短剧生产
    WEBSITE_EXHIBITION = "website_exhibition"   # 官网展示
    KNOWLEDGE_BASE = "knowledge_base"            # 知识库
    AI_RESEARCH = "ai_research"                  # AI研究
    GENERAL_PURPOSE = "general_purpose"          # 通用窗口


class WindowStatus(Enum):
    """窗口状态枚举"""
    ACTIVE = "active"           # 活跃
    IDLE = "idle"               # 空闲
    BUSY = "busy"               # 忙碌
    SLEEPING = "sleeping"       # 休眠
    ARCHIVED = "archived"       # 已归档
    OFFLINE = "offline"         # 离线


class WindowPriority(Enum):
    """窗口优先级枚举"""
    ROOT = 0                    # 根窗口（最高）
    CORE = 1                    # 核心窗口
    STANDARD = 2                # 标准窗口
    AUXILIARY = 3               # 辅助窗口
    TEMPORARY = 4               # 临时窗口


@dataclass
class WindowRegistration:
    """窗口注册信息 - 标准注册格式"""
    window_id: str
    window_role: WindowRole
    window_name: str
    anchor_protocol: str = "ZONGYUAN-ROOT V2.1.0"
    protocol_version: str = "ZR-PROTO-V1.0"
    status: WindowStatus = WindowStatus.ACTIVE
    priority: WindowPriority = WindowPriority.STANDARD
    is_root_window: bool = False

    # 能力标签
    capabilities: List[str] = field(default_factory=list)

    # 边界约束
    boundary_constraints: List[str] = field(default_factory=list)

    # 服务对象
    service_objects: List[str] = field(default_factory=list)

    # 通信端点
    communication_endpoint: str = ""
    api_endpoint: str = ""

    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)

    # 注册信息
    registration_time: float = field(default_factory=time.time)
    last_heartbeat: float = field(default_factory=time.time)
    registration_hash: str = ""

    def __post_init__(self):
        if not self.registration_hash:
            self.registration_hash = self._compute_hash()

    def _compute_hash(self) -> str:
        """计算注册哈希"""
        content = json.dumps({
            "window_id": self.window_id,
            "window_role": self.window_role.value,
            "window_name": self.window_name,
            "anchor_protocol": self.anchor_protocol,
            "registration_time": self.registration_time,
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest().upper()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "window_id": self.window_id,
            "window_role": self.window_role.value,
            "window_name": self.window_name,
            "anchor_protocol": self.anchor_protocol,
            "protocol_version": self.protocol_version,
            "status": self.status.value,
            "priority": self.priority.value,
            "is_root_window": self.is_root_window,
            "capabilities": self.capabilities,
            "boundary_constraints": self.boundary_constraints,
            "service_objects": self.service_objects,
            "communication_endpoint": self.communication_endpoint,
            "api_endpoint": self.api_endpoint,
            "metadata": self.metadata,
            "registration_time": self.registration_time,
            "last_heartbeat": self.last_heartbeat,
            "registration_hash": self.registration_hash,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WindowRegistration":
        """从字典创建"""
        return cls(
            window_id=data["window_id"],
            window_role=WindowRole(data.get("window_role", "general_purpose")),
            window_name=data["window_name"],
            anchor_protocol=data.get("anchor_protocol", "ZONGYUAN-ROOT V2.1.0"),
            protocol_version=data.get("protocol_version", "ZR-PROTO-V1.0"),
            status=WindowStatus(data.get("status", "active")),
            priority=WindowPriority(data.get("priority", 2)),
            is_root_window=data.get("is_root_window", False),
            capabilities=data.get("capabilities", []),
            boundary_constraints=data.get("boundary_constraints", []),
            service_objects=data.get("service_objects", []),
            communication_endpoint=data.get("communication_endpoint", ""),
            api_endpoint=data.get("api_endpoint", ""),
            metadata=data.get("metadata", {}),
            registration_time=data.get("registration_time", time.time()),
            last_heartbeat=data.get("last_heartbeat", time.time()),
            registration_hash=data.get("registration_hash", ""),
        )


@dataclass
class WindowMessage:
    """窗口间消息标准格式"""
    message_id: str
    from_window: str
    to_window: str
    message_type: str  # request/response/notification/broadcast
    content: Any
    priority: int = 2
    timestamp: float = field(default_factory=time.time)
    requires_ack: bool = False
    correlation_id: str = ""  # 关联请求ID（用于响应匹配）
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.message_id:
            self.message_id = f"msg-{uuid.uuid4().hex[:16]}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "from_window": self.from_window,
            "to_window": self.to_window,
            "message_type": self.message_type,
            "content": self.content,
            "priority": self.priority,
            "timestamp": self.timestamp,
            "requires_ack": self.requires_ack,
            "correlation_id": self.correlation_id,
            "metadata": self.metadata,
        }


@dataclass
class WindowTask:
    """窗口协作任务标准格式"""
    task_id: str
    title: str
    description: str
    assigned_window: str
    assigned_by: str
    status: str = "pending"  # pending/running/completed/failed/cancelled
    priority: int = 2
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    deadline: float = 0
    dependencies: List[str] = field(default_factory=list)
    result: Any = None
    error: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.task_id:
            self.task_id = f"task-{uuid.uuid4().hex[:16]}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "title": self.title,
            "description": self.description,
            "assigned_window": self.assigned_window,
            "assigned_by": self.assigned_by,
            "status": self.status,
            "priority": self.priority,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "deadline": self.deadline,
            "dependencies": self.dependencies,
            "result": self.result,
            "error": self.error,
            "metadata": self.metadata,
        }


# 多窗口协议常量
WINDOW_PROTOCOL_VERSION = "WINDOW-PROTO-V1.0"
WINDOW_PROTOCOL_MAGIC = "ZR-WINDOW"

# 标准能力标签
STANDARD_CAPABILITIES = [
    "architecture_design",      # 架构设计
    "protocol_fusion",          # 协议融合
    "kernel_evolution",         # 内核进化
    "global_locking",           # 全域锁档
    "self_healing",             # 自愈
    "gov_ai_services",          # 政务AI服务
    "drama_production",         # 短剧生产
    "website_exhibition",       # 官网展示
    "knowledge_management",     # 知识管理
    "ai_research",              # AI研究
    "api_gateway",              # API网关
    "compute_scheduling",       # 算力调度
]

# 标准边界约束模板
STANDARD_BOUNDARY_TEMPLATES = {
    "kernel_architect": [
        "不做应用层业务功能开发",
        "不做商业化运营",
        "不做具体内容创作",
    ],
    "gov_ai": [
        "不修改内核核心协议",
        "不操作其他窗口数据",
    ],
    "drama_production": [
        "不修改内核核心协议",
        "不操作政务数据",
    ],
}
