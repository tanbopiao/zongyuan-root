"""
帧基类与7种帧类型定义
基于KERNEL-ENTRY-0199规范：真值总线帧标准V1.0
"""
import json
import hashlib
from dataclasses import dataclass, field
from typing import Optional, Any

from .frame_header import (
    FrameHeader, create_header,
    FRAME_TYPE_CONTEXT, FRAME_TYPE_TASK, FRAME_TYPE_ASSET_INDEX,
    FRAME_TYPE_STATE_SNAPSHOT, FRAME_TYPE_HANDSHAKE,
    FRAME_TYPE_AUDIT, FRAME_TYPE_ERROR,
    MODE_DIALOG, MODE_TASK
)


@dataclass
class BaseFrame:
    """
    帧基类
    所有真值总线帧的基类，包含通用帧头和帧体
    """
    header: FrameHeader
    body: dict
    
    def compute_hash(self) -> str:
        """计算帧体SHA256哈希"""
        body_json = json.dumps(self.body, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(body_json.encode()).hexdigest().upper()
    
    def update_hash(self):
        """更新帧头中的帧哈希"""
        self.header.frame_hash = self.compute_hash()
    
    def verify_hash(self) -> bool:
        """校验帧哈希是否匹配"""
        computed = self.compute_hash()
        return computed == self.header.frame_hash.upper()
    
    def to_json(self) -> str:
        """序列化为JSON字符串"""
        return json.dumps({
            "header": self.header.to_dict(),
            "body": self.body
        }, ensure_ascii=False, indent=2)
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "header": self.header.to_dict(),
            "body": self.body
        }
    
    @classmethod
    def from_json(cls, json_str: str) -> 'BaseFrame':
        """从JSON字符串反序列化"""
        data = json.loads(json_str)
        header = FrameHeader.from_dict(data["header"])
        return cls(header=header, body=data.get("body", {}))
    
    @classmethod
    def from_dict(cls, data: dict) -> 'BaseFrame':
        """从字典创建"""
        header = FrameHeader.from_dict(data["header"])
        return cls(header=header, body=data.get("body", {}))
    
    def get_frame_type(self) -> str:
        """获取帧类型"""
        return self.header.frame_type
    
    def get_frame_id(self) -> str:
        """获取帧ID"""
        return self.header.frame_id


# ========== 7种具体帧类型 ==========

class ContextFrame(BaseFrame):
    """
    上下文帧（context_frame）
    传递会话上下文、对话历史、推理中间结果
    方向：双向
    """
    
    def __init__(self, header: FrameHeader, body: Optional[dict] = None):
        if body is None:
            body = {
                "context_summary": "",
                "dialog_history": [],
                "intermediate_results": [],
                "active_variables": {},
                "context_hash": ""
            }
        super().__init__(header=header, body=body)
        self.header.frame_type = FRAME_TYPE_CONTEXT
    
    def set_context_summary(self, summary: str):
        self.body["context_summary"] = summary
    
    def add_dialog_message(self, role: str, content: str, timestamp: str = ""):
        self.body["dialog_history"].append({
            "role": role,
            "content": content,
            "timestamp": timestamp
        })
    
    def add_intermediate_result(self, name: str, value: Any, result_type: str = "text"):
        self.body["intermediate_results"].append({
            "name": name,
            "value": value,
            "type": result_type
        })
    
    def update_context_hash(self):
        ctx_json = json.dumps(self.body, sort_keys=True, ensure_ascii=False)
        self.body["context_hash"] = hashlib.sha256(ctx_json.encode()).hexdigest().upper()


class TaskFrame(BaseFrame):
    """
    任务帧（task_frame）
    传递结构化任务清单、优先级、依赖关系
    方向：对话→任务
    """
    
    def __init__(self, header: FrameHeader, body: Optional[dict] = None):
        if body is None:
            body = {
                "task_list": [],
                "task_dag": {},
                "overall_progress": 0
            }
        super().__init__(header=header, body=body)
        self.header.frame_type = FRAME_TYPE_TASK
    
    def add_task(self, task_id: str, task_name: str, description: str = "",
                 priority: str = "P2", status: str = "pending",
                 depends_on: list = None, estimated_effort: str = "",
                 acceptance_criteria: str = "", assigned_to: str = ""):
        self.body["task_list"].append({
            "task_id": task_id,
            "task_name": task_name,
            "description": description,
            "priority": priority,
            "status": status,
            "depends_on": depends_on or [],
            "estimated_effort": estimated_effort,
            "acceptance_criteria": acceptance_criteria,
            "assigned_to": assigned_to
        })
    
    def set_overall_progress(self, progress: int):
        self.body["overall_progress"] = progress


class AssetIndexFrame(BaseFrame):
    """
    资产索引帧（asset_index_frame）
    传递已固化资产的SHA256列表与存储路径
    方向：双向
    """
    
    def __init__(self, header: FrameHeader, body: Optional[dict] = None):
        if body is None:
            body = {
                "assets": [],
                "total_assets": 0,
                "total_size": 0
            }
        super().__init__(header=header, body=body)
        self.header.frame_type = FRAME_TYPE_ASSET_INDEX
    
    def add_asset(self, asset_id: str, asset_name: str, asset_type: str,
                  sha256: str, storage_path: str, public_url: str = "",
                  file_size: int = 0, mime_type: str = "",
                  created_at: str = "", source_mode: str = "",
                  archive_batch: str = "", metadata: dict = None):
        self.body["assets"].append({
            "asset_id": asset_id,
            "asset_name": asset_name,
            "asset_type": asset_type,
            "sha256": sha256,
            "storage_path": storage_path,
            "public_url": public_url,
            "file_size": file_size,
            "mime_type": mime_type,
            "created_at": created_at,
            "source_mode": source_mode,
            "archive_batch": archive_batch,
            "metadata": metadata or {}
        })
        self.body["total_assets"] = len(self.body["assets"])
        self.body["total_size"] = sum(a.get("file_size", 0) for a in self.body["assets"])


class StateSnapshotFrame(BaseFrame):
    """
    状态快照帧（state_snapshot_frame）
    传递系统状态、变量值、待办栈快照
    方向：双向
    """
    
    def __init__(self, header: FrameHeader, body: Optional[dict] = None):
        if body is None:
            body = {
                "system_state": {},
                "session_state": {},
                "todo_stack": [],
                "snapshot_hash": ""
            }
        super().__init__(header=header, body=body)
        self.header.frame_type = FRAME_TYPE_STATE_SNAPSHOT
    
    def set_system_state(self, kernel_status: str = "", ledger_root_hash: str = "",
                         active_sessions: int = 0, pending_tasks: int = 0,
                         archived_assets: int = 0):
        self.body["system_state"] = {
            "kernel_status": kernel_status,
            "ledger_root_hash": ledger_root_hash,
            "active_sessions": active_sessions,
            "pending_tasks": pending_tasks,
            "archived_assets": archived_assets
        }
    
    def set_session_state(self, current_mode: str = "", mode_duration: str = "",
                          last_switch_at: str = "", switch_count: int = 0):
        self.body["session_state"] = {
            "current_mode": current_mode,
            "mode_duration": mode_duration,
            "last_switch_at": last_switch_at,
            "switch_count": switch_count
        }
    
    def add_todo(self, todo: str):
        self.body["todo_stack"].insert(0, todo)
    
    def update_snapshot_hash(self):
        snap_json = json.dumps(self.body, sort_keys=True, ensure_ascii=False)
        self.body["snapshot_hash"] = hashlib.sha256(snap_json.encode()).hexdigest().upper()


class HandshakeFrame(BaseFrame):
    """
    握手帧（handshake_frame）
    同源协议握手专用帧
    方向：双向
    """
    
    def __init__(self, header: FrameHeader, body: Optional[dict] = None):
        if body is None:
            body = {
                "handshake_step": "init",  # init | challenge | response | ack
                "nonce": "",
                "challenge": "",
                "response": "",
                "session_token": "",
                "permission": "",
                "error_code": "",
                "error_message": ""
            }
        super().__init__(header=header, body=body)
        self.header.frame_type = FRAME_TYPE_HANDSHAKE


class AuditFrame(BaseFrame):
    """
    审计帧（audit_frame）
    传递操作审计记录
    方向：总线→双方
    """
    
    def __init__(self, header: FrameHeader, body: Optional[dict] = None):
        if body is None:
            body = {
                "audit_id": "",
                "operation": "",
                "operator": "",
                "target": "",
                "result": "",
                "details": {},
                "audit_timestamp": ""
            }
        super().__init__(header=header, body=body)
        self.header.frame_type = FRAME_TYPE_AUDIT


class ErrorFrame(BaseFrame):
    """
    错误帧（error_frame）
    传递错误信息与恢复建议
    方向：总线→请求方
    """
    
    def __init__(self, header: FrameHeader, body: Optional[dict] = None):
        if body is None:
            body = {
                "error_code": "E1010",
                "error_message": "",
                "error_type": "other",
                "recoverable": True,
                "recovery_suggestion": "",
                "retry_after": 0,
                "context": {}
            }
        super().__init__(header=header, body=body)
        self.header.frame_type = FRAME_TYPE_ERROR


# 帧类型映射
FRAME_TYPE_MAP = {
    FRAME_TYPE_CONTEXT: ContextFrame,
    FRAME_TYPE_TASK: TaskFrame,
    FRAME_TYPE_ASSET_INDEX: AssetIndexFrame,
    FRAME_TYPE_STATE_SNAPSHOT: StateSnapshotFrame,
    FRAME_TYPE_HANDSHAKE: HandshakeFrame,
    FRAME_TYPE_AUDIT: AuditFrame,
    FRAME_TYPE_ERROR: ErrorFrame
}


def create_frame_by_type(frame_type: str, header: FrameHeader, 
                          body: Optional[dict] = None) -> BaseFrame:
    """根据帧类型创建对应帧对象"""
    frame_class = FRAME_TYPE_MAP.get(frame_type, BaseFrame)
    return frame_class(header=header, body=body)


def parse_frame(json_str: str) -> BaseFrame:
    """
    解析JSON字符串为对应帧类型对象
    自动根据header.frame_type创建具体帧类
    """
    data = json.loads(json_str)
    header = FrameHeader.from_dict(data["header"])
    frame_type = header.frame_type
    frame_class = FRAME_TYPE_MAP.get(frame_type, BaseFrame)
    return frame_class(header=header, body=data.get("body", {}))
