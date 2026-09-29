"""
帧校验器模块
基于KERNEL-ENTRY-0199规范：5重校验规则
1. 完整性校验（帧哈希）
2. 时序校验（sequence）
3. 令牌校验（session_token）
4. Merkle校验（merkle_proof）
5. 大小校验（单帧最大1MB）
"""
import json
from dataclasses import dataclass, field
from typing import Optional, Callable
from collections import defaultdict

from .frame import BaseFrame
from .frame_header import FrameHeader
from .error_codes import TruthBusError, get_error_info


@dataclass
class ValidationResult:
    """校验结果"""
    passed: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    details: dict = field(default_factory=dict)
    
    def add_error(self, error: str):
        self.errors.append(error)
        self.passed = False
    
    def add_warning(self, warning: str):
        self.warnings.append(warning)
    
    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "errors": self.errors,
            "warnings": self.warnings,
            "details": self.details
        }


class FrameValidator:
    """
    帧校验器（5重校验）
    """
    
    MAX_FRAME_SIZE_BYTES = 1048576  # 1MB
    SEQUENCE_GAP_THRESHOLD = 10
    
    def __init__(self, token_validator: Optional[Callable[[str], bool]] = None,
                 merkle_validator: Optional[Callable[[str], bool]] = None):
        """
        初始化校验器
        token_validator: 外部令牌校验函数（接收token字符串，返回bool）
        merkle_validator: 外部Merkle校验函数（接收merkle_proof字符串，返回bool）
        """
        self.token_validator = token_validator
        self.merkle_validator = merkle_validator
        # 按session_id记录最后一个sequence
        self._last_sequence: dict[str, int] = defaultdict(int)
    
    def validate(self, frame: BaseFrame) -> ValidationResult:
        """
        执行全部5重校验
        """
        result = ValidationResult(passed=True)
        
        # 校验1：完整性校验（帧哈希）
        self._validate_hash(frame, result)
        
        # 校验2：时序校验（sequence）
        self._validate_sequence(frame, result)
        
        # 校验3：令牌校验（session_token）
        self._validate_token(frame, result)
        
        # 校验4：Merkle校验（merkle_proof）
        self._validate_merkle(frame, result)
        
        # 校验5：大小校验
        self._validate_size(frame, result)
        
        # 额外：帧头完整性校验
        header_valid, header_errors = frame.header.validate()
        if not header_valid:
            for err in header_errors:
                result.add_error(f"帧头校验失败: {err}")
        
        return result
    
    def _validate_hash(self, frame: BaseFrame, result: ValidationResult):
        """校验1：完整性校验（帧体SHA256与帧头frame_hash比对）"""
        if not frame.header.frame_hash:
            result.add_error("E1003: 帧哈希缺失（frame_hash为空）")
            return
        
        computed = frame.compute_hash()
        if computed != frame.header.frame_hash.upper():
            result.add_error(
                f"E1003: 帧哈希校验失败，期望={frame.header.frame_hash[:16]}...，"
                f"实际={computed[:16]}..."
            )
        else:
            result.details["hash_valid"] = True
    
    def _validate_sequence(self, frame: BaseFrame, result: ValidationResult):
        """校验2：时序校验（同会话sequence严格递增）"""
        session_id = frame.header.session_id
        sequence = frame.header.sequence
        
        if not session_id:
            result.add_warning("session_id为空，无法进行时序校验")
            return
        
        last_seq = self._last_sequence.get(session_id, -1)
        
        if sequence <= last_seq:
            result.add_error(
                f"时序校验失败：sequence={sequence} 不大于上次的sequence={last_seq}"
            )
        elif sequence - last_seq > self.SEQUENCE_GAP_THRESHOLD:
            result.add_warning(
                f"时序跳号过大：sequence={sequence}，上次={last_seq}，"
                f"跳号={sequence - last_seq}（阈值={self.SEQUENCE_GAP_THRESHOLD}）"
            )
        else:
            # 更新最后一个sequence
            self._last_sequence[session_id] = sequence
            result.details["sequence_valid"] = True
    
    def _validate_token(self, frame: BaseFrame, result: ValidationResult):
        """校验3：会话令牌有效性校验"""
        token = frame.header.session_token
        
        if not token:
            result.add_error("E1001: 会话令牌缺失（session_token为空）")
            return
        
        if self.token_validator:
            if not self.token_validator(token):
                result.add_error("E1001: 会话令牌无效或过期")
            else:
                result.details["token_valid"] = True
        else:
            # 没有外部校验器时，只检查格式（64位十六进制）
            if len(token) != 64 or not all(c in '0123456789abcdefABCDEF' for c in token):
                result.add_warning("会话令牌格式异常（期望64位十六进制），但未配置外部校验器")
            else:
                result.details["token_format_valid"] = True
    
    def _validate_merkle(self, frame: BaseFrame, result: ValidationResult):
        """校验4：Merkle凭证校验"""
        merkle_proof = frame.header.merkle_proof
        
        if not merkle_proof:
            result.add_warning("Merkle凭证为空（merkle_proof为空）")
            return
        
        if self.merkle_validator:
            if not self.merkle_validator(merkle_proof):
                result.add_error("E1005: Merkle凭证校验失败")
            else:
                result.details["merkle_valid"] = True
        else:
            # 没有外部校验器时，只做格式检查
            result.details["merkle_present"] = True
    
    def _validate_size(self, frame: BaseFrame, result: ValidationResult):
        """校验5：大小校验（单帧最大1MB）"""
        try:
            frame_json = frame.to_json()
            size_bytes = len(frame_json.encode('utf-8'))
            
            if size_bytes > self.MAX_FRAME_SIZE_BYTES:
                result.add_error(
                    f"帧大小超限：{size_bytes}字节 > {self.MAX_FRAME_SIZE_BYTES}字节（1MB），"
                    f"需要分片传输"
                )
            else:
                result.details["frame_size_bytes"] = size_bytes
                result.details["size_valid"] = True
        except Exception as e:
            result.add_error(f"帧大小计算失败: {e}")
    
    def reset_sequence(self, session_id: str):
        """重置指定会话的sequence计数器"""
        if session_id in self._last_sequence:
            del self._last_sequence[session_id]
    
    def reset_all(self):
        """重置所有状态"""
        self._last_sequence.clear()
