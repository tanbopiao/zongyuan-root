"""
算子库 - 标准化、可复用、可组合、可锁档的算子生态
算子即太极：阴阳具足（输入/输出）、四象完备（状态机）、五行可运（5种组合模式）
"""
from .base_operator import (
    BaseOperator, OperatorInput, OperatorOutput,
    OperatorMetadata, OperatorStatus, OperatorQuality
)
from .core_operators import (
    HashLockOperator, TruthExtractOperator, DriftDetectOperator,
    SelfHealingOperator, DeployOperator, APICallOperator,
    MerkleDAGWalkOperator, FileOperationOperator, AutoCheckOperator,
    HealthCheckOperator, CORE_OPERATORS, get_operator, list_operators
)
from .composition_engine import (
    SerialPipeline, ParallelExecutor, ConditionalBranch,
    LoopIterator, TryCatch, OperatorCompositionEngine, PipelineResult
)
from .operator_registry import OperatorRegistry, OperatorRegistration

__all__ = [
    "BaseOperator", "OperatorInput", "OperatorOutput",
    "OperatorMetadata", "OperatorStatus", "OperatorQuality",
    "HashLockOperator", "TruthExtractOperator", "DriftDetectOperator",
    "SelfHealingOperator", "DeployOperator", "APICallOperator",
    "MerkleDAGWalkOperator", "FileOperationOperator", "AutoCheckOperator",
    "HealthCheckOperator", "CORE_OPERATORS", "get_operator", "list_operators",
    "SerialPipeline", "ParallelExecutor", "ConditionalBranch",
    "LoopIterator", "TryCatch", "OperatorCompositionEngine", "PipelineResult",
    "OperatorRegistry", "OperatorRegistration",
]
