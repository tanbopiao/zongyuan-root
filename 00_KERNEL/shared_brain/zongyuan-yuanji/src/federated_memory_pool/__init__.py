"""Federated Memory Pool L2

ZONGYUAN-ROOT 元极恒一自治体系 · 联邦记忆池
Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | L2 网关真值库 (append_only)

五阶段治理: propose → validate → vote → archive → confirm
生命周期:  proposed → validated → reinforced → decayed → soft_forgotten | confirmed
"""

__version__ = "2.0.0"
__all__ = [
    "MemoryRecord",
    "MemoryNode",
    "FederatedMemoryPool",
    "MemoryBank",
    "STATE_PROPOSED", "STATE_VALIDATED", "STATE_REINFORCED",
    "STATE_DECAYED", "STATE_SOFT_FORGOTTEN", "STATE_CONFIRMED",
]

from .core import (
    MemoryRecord, MemoryNode, FederatedMemoryPool, MemoryBank,
    STATE_PROPOSED, STATE_VALIDATED, STATE_REINFORCED,
    STATE_DECAYED, STATE_SOFT_FORGOTTEN, STATE_CONFIRMED,
)
