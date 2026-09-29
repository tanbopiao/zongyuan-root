"""
HRM-SDK V1.0 桥接适配层
火斗云智HRM业务 ↔ ZONGYUAN-ROOT云内核 唯一桥接层

确权: DID-BR-000002 | 溯源: Ω₀⊂⊙∞⊂Ω | 协议: ZONGYUAN-ROOT
版本: V1.0
"""
from .config import (
    KERNEL_BASE_ENDPOINT,
    DID_SUBJECT,
    TRACE_SYMBOL,
    SDK_VERSION,
    LOCAL_QUEUE_STORE_PATH,
    REQUEST_TIMEOUT,
    RETRY_MAX,
)
from .signer import sign_request, verify_receipt
from .asset_submit import submit_asset, query_asset
from .steady_client import steady_judge
from .event_reporter import report_evolution_event
from .local_queue import LocalQueue
from .exceptions import (
    KernelUnreachableError,
    ReceiptVerifyError,
    LocalPendingError,
    SteadyRejectError,
)

__all__ = [
    "KERNEL_BASE_ENDPOINT", "DID_SUBJECT", "TRACE_SYMBOL", "SDK_VERSION",
    "LOCAL_QUEUE_STORE_PATH", "REQUEST_TIMEOUT", "RETRY_MAX",
    "sign_request", "verify_receipt",
    "submit_asset", "query_asset",
    "steady_judge", "report_evolution_event", "LocalQueue",
    "KernelUnreachableError", "ReceiptVerifyError", "LocalPendingError", "SteadyRejectError",
]
