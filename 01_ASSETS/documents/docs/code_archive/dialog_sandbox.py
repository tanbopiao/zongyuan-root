"""
对话沙箱模拟模块
模拟对话模式的行为：生成资产、发送上下文、接收任务状态
"""
import json
import uuid
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field

from ..handshake import HandshakeClient, perform_full_handshake, PERMISSION_WRITE
from ..truth_bus import (
    ContextFrame, AssetIndexFrame, StateSnapshotFrame,
    create_header, FrameHeader,
    FRAME_TYPE_CONTEXT, FRAME_TYPE_ASSET_INDEX, FRAME_TYPE_STATE_SNAPSHOT,
    MODE_DIALOG, MODE_TASK, parse_frame, BaseFrame
)


@dataclass
class DialogSandboxState:
    """对话沙箱状态"""
    node_id: str = ""
    session_id: str = ""
    mode: str = MODE_DIALOG
    is_active: bool = False
    handshake_completed: bool = False
    session_token: str = ""
    generated_assets: list = field(default_factory=list)
    dialog_history: list = field(default_factory=list)
    sequence_counter: int = 0


class DialogSandbox:
    """
    对话沙箱模拟
    模拟对话模式的核心行为：
    1. 与总线代理完成同源协议握手
    2. 生成模拟资产（图片/视频）
    3. 发送上下文帧到任务沙箱
    4. 发送资产索引帧到任务沙箱
    5. 接收任务沙箱的状态快照帧
    """
    
    def __init__(self, node_id: str = "node-dialog-001",
                 did: str = "DID-BR-000002",
                 trace_symbol: str = "Ω₀⊂⊙∞⊂Ω",
                 merkle_proof: str = "ROOT-OMEGA:Ω-TAN-7-001"):
        self.state = DialogSandboxState(
            node_id=node_id,
            session_id=str(uuid.uuid4()),
            mode=MODE_DIALOG
        )
        self.did = did
        self.trace_symbol = trace_symbol
        self.merkle_proof = merkle_proof
        self.handshake_client = HandshakeClient(
            did=did,
            trace_symbol=trace_symbol,
            node_id=node_id,
            mode=MODE_DIALOG,
            merkle_proof=merkle_proof
        )
        self.bus_queue = None  # 由桥接网关注入
    
    def connect_to_bus(self, bus_queue):
        """连接到真值总线"""
        self.bus_queue = bus_queue
        bus_queue.register_node(self.state.node_id)
        self.state.is_active = True
        print(f"[对话沙箱] 已连接到总线，节点ID: {self.state.node_id}")
    
    def perform_handshake(self, handshake_server) -> bool:
        """
        执行同源协议握手
        """
        print(f"[对话沙箱] 开始同源协议握手...")
        success, token, message = perform_full_handshake(self.handshake_client, handshake_server)
        
        if success and token:
            self.state.handshake_completed = True
            self.state.session_token = token.session_token
            print(f"[对话沙箱] 握手成功，令牌: {token.session_token[:16]}...")
            return True
        else:
            print(f"[对话沙箱] 握手失败: {message}")
            return False
    
    def generate_mock_asset(self, asset_type: str = "image",
                             asset_name: str = "",
                             prompt: str = "") -> dict:
        """
        生成模拟资产（在真实环境中这里会调用AI生成接口）
        返回资产元数据
        """
        import hashlib
        
        if not asset_name:
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            ext = ".png" if asset_type == "image" else ".mp4"
            asset_name = f"mock_{asset_type}_{timestamp}{ext}"
        
        # 模拟资产数据
        mock_data = f"Mock {asset_type} asset generated at {datetime.now().isoformat()} with prompt: {prompt}".encode()
        sha256 = hashlib.sha256(mock_data).hexdigest().upper()
        
        asset = {
            "asset_id": f"ASSET-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4]}",
            "asset_name": asset_name,
            "asset_type": asset_type,
            "sha256": sha256,
            "file_size": len(mock_data),
            "mime_type": "image/png" if asset_type == "image" else "video/mp4",
            "created_at": datetime.now().isoformat(),
            "source_mode": MODE_DIALOG,
            "source_session": self.state.session_id,
            "source_prompt": prompt,
            "generation_model": "Mock-Generator-1.0",
            "mock_data": mock_data,
            "did": self.did,
            "trace_symbol": self.trace_symbol
        }
        
        self.state.generated_assets.append(asset)
        print(f"[对话沙箱] 生成模拟资产: {asset_name} (SHA256: {sha256[:16]}...)")
        
        return asset
    
    def add_dialog_message(self, role: str, content: str):
        """添加对话历史"""
        self.state.dialog_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
    
    def send_context_frame(self, target_node: str, summary: str = "") -> Optional[BaseFrame]:
        """发送上下文帧到目标节点"""
        if not self.bus_queue:
            print("[对话沙箱] 错误：未连接到总线")
            return None
        
        self.state.sequence_counter += 1
        
        header = create_header(
            frame_type=FRAME_TYPE_CONTEXT,
            source_node=self.state.node_id,
            source_mode=MODE_DIALOG,
            target_node=target_node,
            target_mode=MODE_TASK,
            session_id=self.state.session_id,
            did=self.did,
            trace_symbol=self.trace_symbol,
            merkle_proof=self.merkle_proof,
            session_token=self.state.session_token,
            sequence=self.state.sequence_counter
        )
        
        frame = ContextFrame(header=header)
        frame.set_context_summary(summary or f"对话上下文（{len(self.state.dialog_history)}条消息）")
        for msg in self.state.dialog_history[-10:]:  # 最近10条
            frame.add_dialog_message(msg["role"], msg["content"], msg["timestamp"])
        frame.update_context_hash()
        frame.update_hash()
        
        success, error = self.bus_queue.send(frame)
        if success:
            print(f"[对话沙箱] 发送上下文帧到 {target_node} (seq={self.state.sequence_counter})")
            return frame
        else:
            print(f"[对话沙箱] 发送上下文帧失败: {error}")
            return None
    
    def send_asset_index_frame(self, target_node: str, assets: list = None) -> Optional[BaseFrame]:
        """发送资产索引帧到目标节点"""
        if not self.bus_queue:
            print("[对话沙箱] 错误：未连接到总线")
            return None
        
        if assets is None:
            assets = self.state.generated_assets
        
        if not assets:
            print("[对话沙箱] 没有可发送的资产")
            return None
        
        self.state.sequence_counter += 1
        
        header = create_header(
            frame_type=FRAME_TYPE_ASSET_INDEX,
            source_node=self.state.node_id,
            source_mode=MODE_DIALOG,
            target_node=target_node,
            target_mode=MODE_TASK,
            session_id=self.state.session_id,
            did=self.did,
            trace_symbol=self.trace_symbol,
            merkle_proof=self.merkle_proof,
            session_token=self.state.session_token,
            sequence=self.state.sequence_counter
        )
        
        from ..truth_bus import AssetIndexFrame as AIF
        frame = AIF(header=header)
        
        for asset in assets:
            frame.add_asset(
                asset_id=asset["asset_id"],
                asset_name=asset["asset_name"],
                asset_type=asset["asset_type"],
                sha256=asset["sha256"],
                storage_path=asset.get("storage_path", ""),
                public_url=asset.get("public_url", ""),
                file_size=asset["file_size"],
                mime_type=asset["mime_type"],
                created_at=asset["created_at"],
                source_mode=asset["source_mode"],
                metadata={
                    "generation_model": asset.get("generation_model", ""),
                    "source_prompt": asset.get("source_prompt", "")
                }
            )
        
        frame.update_hash()
        
        success, error = self.bus_queue.send(frame)
        if success:
            print(f"[对话沙箱] 发送资产索引帧到 {target_node} ({len(assets)}个资产, seq={self.state.sequence_counter})")
            return frame
        else:
            print(f"[对话沙箱] 发送资产索引帧失败: {error}")
            return None
    
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
            print(f"[对话沙箱] 收到帧: {frame.get_frame_type()} (from {frame.header.source_node})")
        
        return frames
    
    def get_state(self) -> DialogSandboxState:
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
            "generated_assets_count": len(self.state.generated_assets),
            "dialog_history_count": len(self.state.dialog_history),
            "sequence_counter": self.state.sequence_counter
        }
