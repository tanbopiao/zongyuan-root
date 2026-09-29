"""
HRM-SDK 配置模块
"""
import os

# 内核端点（默认本地调度内核，可通过环境变量覆盖）
KERNEL_BASE_ENDPOINT = os.getenv(
    "ZKROOT_API_ENDPOINT", "http://127.0.0.1:8032/kernel-api"
)

# 确权身份
DID_SUBJECT = os.getenv("ZKROOT_DID", "DID-BR-000002")
TRACE_SYMBOL = os.getenv("ZKROOT_TRACE_SYMBOL", "Ω₀⊂⊙∞⊂Ω")
SDK_VERSION = "HRM-SDK-V1.0"

# 内核调度密钥（HMAC签名用，环境变量注入，禁止硬编码提交）
SCHEDULER_SECRET = os.getenv("ZONGYUAN_ROOT_SCHEDULER_SECRET", "")

# 离线队列
LOCAL_QUEUE_STORE_PATH = os.getenv(
    "HRM_SDK_QUEUE_PATH", os.path.join(os.path.dirname(__file__), "hrm_sdk_local_queue.dat")
)
LOCAL_QUEUE_MAX = int(os.getenv("HRM_SDK_QUEUE_MAX", "500"))

# 网络
REQUEST_TIMEOUT = int(os.getenv("HRM_SDK_TIMEOUT", "12"))
RETRY_MAX = int(os.getenv("HRM_SDK_RETRY", "3"))
