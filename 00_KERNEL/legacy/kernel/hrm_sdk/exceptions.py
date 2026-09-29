"""
HRM-SDK 异常定义
"""
class HRMSDKError(Exception):
    """SDK 基础异常"""
    pass


class KernelUnreachableError(HRMSDKError):
    """内核服务不可访问"""
    pass


class ReceiptVerifyError(HRMSDKError):
    """锁档回执哈希校验不通过"""
    pass


class LocalPendingError(HRMSDKError):
    """请求已进入本地离线队列，等待网络恢复补提交"""
    pass


class SteadyRejectError(HRMSDKError):
    """稳态算子判定拒绝业务操作"""
    pass
