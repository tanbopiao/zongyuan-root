"""
真值总线错误码定义
基于KERNEL-ENTRY-0199规范：E1001-E1010标准错误码
"""

# 错误码字典
ERROR_CODES = {
    "E1001": {
        "type": "auth",
        "message": "会话令牌无效或过期",
        "recoverable": True,
        "retry_after": 0,
        "suggestion": "重新执行同源协议握手获取新的会话令牌"
    },
    "E1002": {
        "type": "auth",
        "message": "DID/溯源标识校验失败",
        "recoverable": False,
        "retry_after": 0,
        "suggestion": "检查DID和溯源标识是否正确，确认节点已加入同源白名单"
    },
    "E1003": {
        "type": "validation",
        "message": "帧哈希校验失败",
        "recoverable": True,
        "retry_after": 0,
        "suggestion": "帧体可能在传输中被篡改，重新构造并发送帧"
    },
    "E1004": {
        "type": "validation",
        "message": "帧结构字段缺失或类型错误",
        "recoverable": False,
        "retry_after": 0,
        "suggestion": "检查帧结构是否符合真值总线帧标准V1.0，通用帧头16字段必须完整"
    },
    "E1005": {
        "type": "validation",
        "message": "Merkle凭证校验失败",
        "recoverable": True,
        "retry_after": 5,
        "suggestion": "Merkle根哈希可能已更新，获取最新的全局账本根哈希后重试"
    },
    "E1006": {
        "type": "timeout",
        "message": "握手挑战超时",
        "recoverable": True,
        "retry_after": 0,
        "suggestion": "挑战有效期30秒，在有效期内完成响应计算，或重新发起握手"
    },
    "E1007": {
        "type": "timeout",
        "message": "帧传输超时",
        "recoverable": True,
        "retry_after": 3,
        "suggestion": "总线队列可能已满或网络延迟，等待后重试"
    },
    "E1008": {
        "type": "network",
        "message": "总线连接中断",
        "recoverable": True,
        "retry_after": 5,
        "suggestion": "检查总线代理是否运行，重新建立连接后重试"
    },
    "E1009": {
        "type": "internal",
        "message": "总线内部错误",
        "recoverable": True,
        "retry_after": 10,
        "suggestion": "总线代理内部异常，查看日志后重试"
    },
    "E1010": {
        "type": "other",
        "message": "其他未分类错误",
        "recoverable": True,
        "retry_after": 0,
        "suggestion": "查看详细错误信息后处理"
    }
}


class TruthBusError(Exception):
    """真值总线异常基类"""
    
    def __init__(self, error_code: str, detail: str = ""):
        self.error_code = error_code
        self.detail = detail
        error_info = ERROR_CODES.get(error_code, ERROR_CODES["E1010"])
        self.error_type = error_info["type"]
        self.message = error_info["message"]
        self.recoverable = error_info["recoverable"]
        self.retry_after = error_info["retry_after"]
        self.suggestion = error_info["suggestion"]
        
        full_message = f"[{error_code}] {self.message}"
        if detail:
            full_message += f" - {detail}"
        super().__init__(full_message)
    
    def to_dict(self) -> dict:
        return {
            "error_code": self.error_code,
            "error_type": self.error_type,
            "message": self.message,
            "detail": self.detail,
            "recoverable": self.recoverable,
            "retry_after": self.retry_after,
            "suggestion": self.suggestion
        }


def get_error_info(error_code: str) -> dict:
    """获取错误码信息"""
    return ERROR_CODES.get(error_code, ERROR_CODES["E1010"])
