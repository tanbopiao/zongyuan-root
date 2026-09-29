"""
真值总线帧模块
基于KERNEL-ENTRY-0199规范：7种帧类型 + 通用帧头16字段 + 5重校验 + 总线队列
"""
from .frame_header import (
    FrameHeader, create_header,
    FRAME_TYPE_CONTEXT, FRAME_TYPE_TASK, FRAME_TYPE_ASSET_INDEX,
    FRAME_TYPE_STATE_SNAPSHOT, FRAME_TYPE_HANDSHAKE,
    FRAME_TYPE_AUDIT, FRAME_TYPE_ERROR,
    VALID_FRAME_TYPES, MODE_DIALOG, MODE_TASK, VALID_MODES
)
from .frame import (
    BaseFrame, ContextFrame, TaskFrame, AssetIndexFrame,
    StateSnapshotFrame, HandshakeFrame, AuditFrame, ErrorFrame,
    FRAME_TYPE_MAP, create_frame_by_type, parse_frame
)
from .frame_validator import FrameValidator, ValidationResult
from .bus_queue import TruthBusQueue, BusStats
from .error_codes import ERROR_CODES, TruthBusError, get_error_info

__all__ = [
    "FrameHeader", "create_header",
    "FRAME_TYPE_CONTEXT", "FRAME_TYPE_TASK", "FRAME_TYPE_ASSET_INDEX",
    "FRAME_TYPE_STATE_SNAPSHOT", "FRAME_TYPE_HANDSHAKE",
    "FRAME_TYPE_AUDIT", "FRAME_TYPE_ERROR",
    "VALID_FRAME_TYPES", "MODE_DIALOG", "MODE_TASK", "VALID_MODES",
    "BaseFrame", "ContextFrame", "TaskFrame", "AssetIndexFrame",
    "StateSnapshotFrame", "HandshakeFrame", "AuditFrame", "ErrorFrame",
    "FRAME_TYPE_MAP", "create_frame_by_type", "parse_frame",
    "FrameValidator", "ValidationResult",
    "TruthBusQueue", "BusStats",
    "ERROR_CODES", "TruthBusError", "get_error_info"
]
