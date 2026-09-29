"""
资产索引帧构造与总线同步模块
基于KERNEL-ENTRY-0199规范：跨模式资产自动中转阶段4-总线索引同步
"""
import json
from datetime import datetime
from typing import Optional
from dataclasses import dataclass

from .metadata import AssetMetadata
from ..truth_bus import (
    AssetIndexFrame, FrameHeader, create_header,
    FRAME_TYPE_ASSET_INDEX, MODE_DIALOG, MODE_TASK
)


@dataclass
class IndexSyncResult:
    """索引同步结果"""
    success: bool
    frame_id: str = ""
    frame_type: str = FRAME_TYPE_ASSET_INDEX
    assets_count: int = 0
    total_size: int = 0
    error_message: str = ""
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "frame_id": self.frame_id,
            "frame_type": self.frame_type,
            "assets_count": self.assets_count,
            "total_size": self.total_size,
            "error_message": self.error_message
        }


class IndexSyncer:
    """
    资产索引帧构造与总线同步器
    阶段4：构造asset_index_frame，通过同源协议握手认证，发送到真值总线
    """
    
    def __init__(self, did: str = "DID-BR-000002",
                 trace_symbol: str = "Ω₀⊂⊙∞⊂Ω",
                 source_node: str = "node-dialog-001",
                 target_node: str = "node-task-001",
                 merkle_proof: str = ""):
        self.did = did
        self.trace_symbol = trace_symbol
        self.source_node = source_node
        self.target_node = target_node
        self.merkle_proof = merkle_proof
    
    def build_asset_index_frame(self, metadata_list: list[AssetMetadata],
                                  session_id: str = "",
                                  session_token: str = "",
                                  sequence: int = 0) -> AssetIndexFrame:
        """
        构造资产索引帧
        """
        header = create_header(
            frame_type=FRAME_TYPE_ASSET_INDEX,
            source_node=self.source_node,
            source_mode=MODE_DIALOG,
            target_node=self.target_node,
            target_mode=MODE_TASK,
            session_id=session_id,
            did=self.did,
            trace_symbol=self.trace_symbol,
            merkle_proof=self.merkle_proof,
            session_token=session_token,
            sequence=sequence
        )
        
        frame = AssetIndexFrame(header=header)
        
        # 添加资产索引
        for meta in metadata_list:
            frame.add_asset(
                asset_id=meta.asset_id,
                asset_name=meta.asset_name,
                asset_type=meta.asset_type,
                sha256=meta.sha256,
                storage_path=meta.storage_path,
                public_url=meta.public_url,
                file_size=meta.file_size,
                mime_type=meta.mime_type,
                created_at=meta.created_at,
                source_mode=meta.source_mode,
                archive_batch=meta.archive_batch,
                metadata={
                    "sub_type": meta.sub_type,
                    "width": meta.width,
                    "height": meta.height,
                    "duration": meta.duration,
                    "generation_model": meta.generation_model,
                    "feishu_drive_url": meta.feishu_drive_url,
                    "feishu_base_record": meta.feishu_base_record,
                    "did": meta.did,
                    "trace_symbol": meta.trace_symbol
                }
            )
        
        # 更新帧哈希
        frame.update_hash()
        
        return frame
    
    def build_single_asset_frame(self, metadata: AssetMetadata,
                                   session_id: str = "",
                                   session_token: str = "",
                                   sequence: int = 0) -> AssetIndexFrame:
        """构造单个资产的索引帧"""
        return self.build_asset_index_frame([metadata], session_id, session_token, sequence)
    
    def sync_to_bus(self, frame: AssetIndexFrame, bus_queue) -> IndexSyncResult:
        """
        同步资产索引帧到真值总线
        bus_queue: TruthBusQueue实例
        """
        try:
            success, error = bus_queue.send(frame)
            
            if success:
                return IndexSyncResult(
                    success=True,
                    frame_id=frame.get_frame_id(),
                    assets_count=frame.body.get("total_assets", 0),
                    total_size=frame.body.get("total_size", 0)
                )
            else:
                return IndexSyncResult(
                    success=False,
                    frame_id=frame.get_frame_id(),
                    error_message=error or "发送到总线失败"
                )
        except Exception as e:
            return IndexSyncResult(
                success=False,
                error_message=f"同步异常: {str(e)}"
            )
    
    def receive_from_bus(self, bus_queue, target_node: str = "") -> Optional[AssetIndexFrame]:
        """
        从总线接收资产索引帧
        """
        target = target_node or self.target_node
        frame = bus_queue.receive(target)
        
        if frame and frame.get_frame_type() == FRAME_TYPE_ASSET_INDEX:
            return frame
        return None
    
    def extract_assets_from_frame(self, frame: AssetIndexFrame) -> list[dict]:
        """从资产索引帧中提取资产列表"""
        return frame.body.get("assets", [])
    
    def verify_frame_integrity(self, frame: AssetIndexFrame) -> bool:
        """校验帧完整性（哈希校验）"""
        return frame.verify_hash()
