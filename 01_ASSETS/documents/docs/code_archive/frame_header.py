"""
通用帧头构造模块
基于KERNEL-ENTRY-0199规范：通用帧头16字段
"""
import uuid
from datetime import datetime
from dataclasses import dataclass, asdict, field
from typing import Optional


# 帧类型枚举
FRAME_TYPE_CONTEXT = "context_frame"
FRAME_TYPE_TASK = "task_frame"
FRAME_TYPE_ASSET_INDEX = "asset_index_frame"
FRAME_TYPE_STATE_SNAPSHOT = "state_snapshot_frame"
FRAME_TYPE_HANDSHAKE = "handshake_frame"
FRAME_TYPE_AUDIT = "audit_frame"
FRAME_TYPE_ERROR = "error_frame"

VALID_FRAME_TYPES = [
    FRAME_TYPE_CONTEXT, FRAME_TYPE_TASK, FRAME_TYPE_ASSET_INDEX,
    FRAME_TYPE_STATE_SNAPSHOT, FRAME_TYPE_HANDSHAKE,
    FRAME_TYPE_AUDIT, FRAME_TYPE_ERROR
]

# 模式枚举
MODE_DIALOG = "dialog"
MODE_TASK = "task"
VALID_MODES = [MODE_DIALOG, MODE_TASK]


@dataclass
class FrameHeader:
    """
    通用帧头（16字段）
    所有真值总线帧必须包含完整的通用帧头
    """
    # 1. 帧版本
    frame_version: str = "1.0"
    
    # 2. 帧唯一标识（UUID）
    frame_id: str = ""
    
    # 3. 帧类型
    frame_type: str = ""
    
    # 4. DID标识
    did: str = "DID-BR-000002"
    
    # 5. 溯源标识
    trace_symbol: str = "Ω₀⊂⊙∞⊂Ω"
    
    # 6. 发送方节点ID
    source_node: str = ""
    
    # 7. 发送方模式
    source_mode: str = ""
    
    # 8. 接收方节点ID
    target_node: str = ""
    
    # 9. 接收方模式
    target_mode: str = ""
    
    # 10. 关联会话ID
    session_id: str = ""
    
    # 11. 时间戳（ISO8601）
    timestamp: str = ""
    
    # 12. 帧序列号（同会话内递增）
    sequence: int = 0
    
    # 13. Merkle根凭证
    merkle_proof: str = ""
    
    # 14. 帧体SHA256哈希
    frame_hash: str = ""
    
    # 15. 会话令牌
    session_token: str = ""
    
    # 16. 扩展字段（预留）
    extensions: dict = field(default_factory=dict)
    
    def __post_init__(self):
        """初始化后自动填充默认值"""
        if not self.frame_id:
            self.frame_id = str(uuid.uuid4())
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'FrameHeader':
        """从字典创建"""
        # 只提取已知字段，忽略额外字段
        known_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered)
    
    def validate(self) -> tuple[bool, list[str]]:
        """
        校验帧头完整性
        返回：(是否有效, 错误列表)
        """
        errors = []
        
        # 必需字段校验
        required_fields = [
            "frame_version", "frame_id", "frame_type", "did",
            "trace_symbol", "source_node", "source_mode",
            "target_node", "target_mode", "session_id",
            "timestamp", "sequence", "merkle_proof",
            "frame_hash", "session_token"
        ]
        
        for field_name in required_fields:
            value = getattr(self, field_name, None)
            if value is None or value == "":
                # sequence=0是合法的，不需要报错
                if field_name == "sequence" and value == 0:
                    continue
                errors.append(f"帧头字段缺失: {field_name}")
        
        # 帧类型校验
        if self.frame_type and self.frame_type not in VALID_FRAME_TYPES:
            errors.append(f"无效帧类型: {self.frame_type}，有效类型: {VALID_FRAME_TYPES}")
        
        # 模式校验
        if self.source_mode and self.source_mode not in VALID_MODES:
            errors.append(f"无效源模式: {self.source_mode}")
        if self.target_mode and self.target_mode not in VALID_MODES:
            errors.append(f"无效目标模式: {self.target_mode}")
        
        return (len(errors) == 0, errors)


def create_header(frame_type: str, source_node: str, source_mode: str,
                  target_node: str, target_mode: str, session_id: str,
                  did: str = "DID-BR-000002",
                  trace_symbol: str = "Ω₀⊂⊙∞⊂Ω",
                  merkle_proof: str = "",
                  session_token: str = "",
                  sequence: int = 0) -> FrameHeader:
    """
    快捷创建帧头
    """
    return FrameHeader(
        frame_type=frame_type,
        did=did,
        trace_symbol=trace_symbol,
        source_node=source_node,
        source_mode=source_mode,
        target_node=target_node,
        target_mode=target_mode,
        session_id=session_id,
        sequence=sequence,
        merkle_proof=merkle_proof,
        session_token=session_token
    )
