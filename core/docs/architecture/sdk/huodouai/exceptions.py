"""
同源协议异常定义
"""

class HomoError(Exception):
    """SDK基础异常"""
    def __init__(self, message, code=None):
        self.code = code
        super().__init__(message)

class AuthError(HomoError):
    """鉴权失败"""
    pass

class TimeoutError(HomoError):
    """请求超时"""
    pass

class TaskFailedError(HomoError):
    """任务执行失败"""
    pass

class NotFoundError(HomoError):
    """资源不存在"""
    pass
