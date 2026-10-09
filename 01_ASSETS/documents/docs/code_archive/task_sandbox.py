"""
任务沙箱模拟模块
模拟工作任务模式的行为：接收上下文、执行任务、访问资产、发送状态
"""
import json
import uuid
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field

from ..handshake import HandshakeClient, perform_full_handshake, PERMISSION_WRITE
from ..truth_bus import (
    ContextFrame, AssetIndexFrame, StateSnapshotFrame, TaskFrame,
    create_header, FrameHeader,
    FRAME_TYPE_CONTEXT, FRAME_TYPE_ASSET_INDEX, FRAME_TYPE_STATE_SNAPSHOT,
    FRAME_TYPE_TASK,
    MODE_DIALOG, MODE_TASK, parse_frame, BaseFrame
)


@dataclass
class TaskSandboxState:
    """任务沙箱状态"""
    node_id: str = ""
    session_id: str = ""
    mode: str = MODE_TASK
    is_active: bool = False
    handshake_completed: bool = False
    session_token: str = ""
    received_assets: list = field(default_factory=list)
    received_contexts: list = field(default_factory=list)
    task_list: list = field(default_factory=list)
    sequence_counter: int = 0


class TaskSandbox:
    """
    任务沙箱模拟
    模拟工作任务模式的核心行为：
    1. 与总线代理完成同源协议握手
    2. 接收对话沙箱的上下文帧
    3. 接收对话沙箱的资产索引帧
    4. 通过资产索引访问已固化资产
    5. 执行任务并发送状态快照帧
    """
    
    def __init__(self, node_id: str = "node-task-001",
                 did: str = "DID-BR-000002",
                 trace_symbol: str = "Ω₀⊂⊙∞⊂Ω",
                 merkle_proof: str = "ROOT-OMEGA:Ω-TAN-7-001"):
        self.state = TaskSandboxState(
            node_id=node_id,
            session_id=str(uuid.uuid4()),
            mode=MODE_TASK
        )
        self.did = did
        self.trace_symbol = trace_symbol
        self.merkle_proof = merkle_proof
        self.handshake_client = HandshakeClient(
            did=did,
            trace_symbol=trace_symbol,
            node_id=node_id,
            mode=MODE_TASK,
            merkle_proof=merkle_proof
        )
        self.bus_queue = None  # 由桥接网关注入
        self.storage = None  # 本地存储（由桥接网关注入）
    
    def connect_to_bus(self, bus_queue):
        """连接到真值总线"""
        self.bus_queue = bus_queue
        bus_queue.register_node(self.state.node_id)
        self.state.is_active = True
        print(f"[任务沙箱] 已连接到总线，节点ID: {self.state.node_id}")
    
    def set_storage(self, storage):
        """设置本地存储引用"""
        self.storage = storage
    
    def perform_handshake(self, handshake_server) -> bool:
        """执行同源协议握手"""
        print(f"[任务沙箱] 开始同源协议握手...")
        success, token, message = perform_full_handshake(self.handshake_client, handshake_server)
        
        if success and token:
            self.state.handshake_completed = True
            self.state.session_token = token.session_token
            print(f"[任务沙箱] 握手成功，令牌: {token.session_token[:16]}...")
            return True
        else:
            print(f"[任务沙箱] 握手失败: {message}")
            return False
    
    def receive_frames(self) -> list[BaseFrame]:
        """接收发送到本节点的帧"""
        if not self.bus_queue:
            return []
        
        frames = []
        while True:
            frame = self.bus_queue.receive(self.state.node_id)
            if frame is None:
                break
            frames.append(frame)
            self._process_frame(frame)
        
        return frames
    
    def _process_frame(self, frame: BaseFrame):
        """处理收到的帧"""
        frame_type = frame.get_frame_type()
        
        if frame_type == FRAME_TYPE_CONTEXT:
            context_summary = frame.body.get("context_summary", "")
            dialog_history = frame.body.get("dialog_history", [])
            self.state.received_contexts.append({
                "frame_id": frame.get_frame_id(),
                "summary": context_summary,
                "message_count": len(dialog_history),
                "received_at": datetime.now().isoformat()
            })
            print(f"[任务沙箱] 处理上下文帧: {context_summary[:50]}... ({len(dialog_history)}条消息)")
        
        elif frame_type == FRAME_TYPE_ASSET_INDEX:
            assets = frame.body.get("assets", [])
            for asset in assets:
                self.state.received_assets.append(asset)
            print(f"[任务沙箱] 处理资产索引帧: {len(assets)}个资产")
            for asset in assets:
                print(f"  - {asset['asset_name']} (SHA256: {asset['sha256'][:16]}...)")
        
        elif frame_type == FRAME_TYPE_TASK:
            tasks = frame.body.get("task_list", [])
            self.state.task_list.extend(tasks)
            print(f"[任务沙箱] 处理任务帧: {len(tasks)}个任务")
    
    def access_asset_by_sha256(self, sha256: str) -> Optional[dict]:
        """
        通过SHA256访问已固化资产
        这是桥接架构的核心优势：任务模式不需要原始CDN链接，
        只需要资产索引中的SHA256和存储路径即可访问资产
        """
        # 先在已接收的资产索引中查找
        for asset in self.state.received_assets:
            if asset.get("sha256", "").upper() == sha256.upper():
                storage_path = asset.get("storage_path", "")
                
                # 如果有本地存储，验证文件是否存在
                if self.storage and storage_path:
                    file_path = self.storage.file_exists(sha256)
                    if file_path:
                        return {
                            "found": True,
                            "asset": asset,
                            "local_path": file_path,
                            "access_method": "local_storage"
                        }
                
                return {
                    "found": True,
                    "asset": asset,
                    "local_path": storage_path,
                    "access_method": "index_path"
                }
        
        # 如果有本地存储，直接通过SHA256查找
        if self.storage:
            file_path = self.storage.file_exists(sha256)
            if file_path:
                return {
                    "found": True,
                    "asset": {"sha256": sha256, "storage_path": file_path},
                    "local_path": file_path,
                    "access_method": "sha256_lookup"
                }
        
        return {"found": False, "sha256": sha256}
    
    def add_task(self, task_name: str, description: str = "",
                 priority: str = "P2", depends_on: list = None):
        """添加任务"""
        task = {
            "task_id": f"TASK-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4]}",
            "task_name": task_name,
            "description": description,
            "priority": priority,
            "status": "pending",
            "depends_on": depends_on or [],
            "created_at": datetime.now().isoformat()
        }
        self.state.task_list.append(task)
        print(f"[任务沙箱] 添加任务: {task_name} (ID: {task['task_id']})")
        return task
    
    def send_state_snapshot(self, target_node: str) -> Optional[BaseFrame]:
        """发送状态快照帧到目标节点"""
        if not self.bus_queue:
            print("[任务沙箱] 错误：未连接到总线")
            return None
        
        self.state.sequence_counter += 1
        
        header = create_header(
            frame_type=FRAME_TYPE_STATE_SNAPSHOT,
            source_node=self.state.node_id,
            source_mode=MODE_TASK,
            target_node=target_node,
            target_mode=MODE_DIALOG,
            session_id=self.state.session_id,
            did=self.did,
            trace_symbol=self.trace_symbol,
            merkle_proof=self.merkle_proof,
            session_token=self.state.session_token,
            sequence=self.state.sequence_counter
        )
        
        frame = StateSnapshotFrame(header=header)
        frame.set_system_state(
            kernel_status="ACTIVATED",
            ledger_root_hash=self.merkle_proof,
            active_sessions=1,
            pending_tasks=len([t for t in self.state.task_list if t["status"] == "pending"]),
            archived_assets=len(self.state.received_assets)
        )
        frame.set_session_state(
            current_mode=MODE_TASK,
            mode_duration="N/A",
            last_switch_at=datetime.now().isoformat(),
            switch_count=0
        )
        for task in self.state.task_list[-5:]:
            frame.add_todo(f"[{task['priority']}] {task['task_name']} - {task['status']}")
        frame.update_snapshot_hash()
        frame.update_hash()
        
        success, error = self.bus_queue.send(frame)
        if success:
            print(f"[任务沙箱] 发送状态快照到 {target_node} (seq={self.state.sequence_counter})")
            return frame
        else:
            print(f"[任务沙箱] 发送状态快照失败: {error}")
            return None
    
    def get_state(self) -> TaskSandboxState:
        """获取沙箱状态"""
        return self.state
    
    def get_state_snapshot(self) -> dict:
        """获取状态快照"""
        return {
            "node_id": self.state.node_id,
            "session_id": self.state.session_id,
            "mode": self.state.mode,
            "is_active": self.state.is_active,
            "handshake_completed": self.state.handshake_completed,
            "received_assets_count": len(self.state.received_assets),
            "received_contexts_count": len(self.state.received_contexts),
            "task_count": len(self.state.task_list),
            "pending_tasks": len([t for t in self.state.task_list if t["status"] == "pending"]),
            "sequence_counter": self.state.sequence_counter
        }
