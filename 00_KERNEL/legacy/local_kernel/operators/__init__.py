"""
ZONGYUAN-ROOT 算子化架构
从"代码堆叠"升级到"算子组合"

标准算子库（6个标准算子，可复用可锁档）：
├── hash_lock            哈希锁档算子
├── auto_check           自动检查算子
├── deploy               部署算子
├── api_call             API调用算子
├── merkle_dag_walk      Merkle-DAG遍历算子（手动栈，禁递归）
└── file_operation       文件操作算子

组合引擎（5种组合模式）：
├── SerialPipeline       串行管道
├── ParallelExecutor     并行执行
├── ConditionalBranch    条件分支
├── LoopIterator         循环迭代（手动栈，禁递归）
└── TryCatch             异常捕获+fallback

元规则：
- KD-STACK-0001: 所有遍历必须使用手动栈，禁止递归调用
- 算子接口统一: result = operator(inputs_dict)
- 每个算子有哈希、版本、元数据，可锁档确权

溯源标识：Ω₀⊂⊙∞⊂Ω
确权编码：DID-BR-000002
根挂载：ZONGYUAN-ROOT V1.7
版本：V1.0
"""

from operator_base import BaseOperator, OperatorResult, OperatorMetadata
from composition_engine import (
    SerialPipeline,
    ParallelExecutor,
    ConditionalBranch,
    LoopIterator,
    TryCatch,
)
from operator_registry import OperatorRegistry, get_registry, register_default_operators

# 版本信息
__version__ = "V1.0"
__author__ = "ZONGYUAN-ROOT"
__did__ = "DID-BR-000002"
__trace_symbol__ = "Ω₀⊂⊙∞⊂Ω"

# 便捷函数
def create_pipeline(operators, name="pipeline"):
    """创建串行管道"""
    return SerialPipeline(operators, name)

def create_try_catch(primary, fallback=None, name="try_catch"):
    """创建try-catch-fallback"""
    return TryCatch(primary, fallback, name)

def create_loop(operator, max_iterations=10, continue_condition=None, name="loop"):
    """创建循环迭代器"""
    return LoopIterator(operator, max_iterations, continue_condition, name)

def create_conditional(condition, true_op, false_op=None, name="conditional"):
    """创建条件分支"""
    return ConditionalBranch(condition, true_op, false_op, name)

# 自动注册默认算子（延迟导入，避免循环依赖）
def init_operators():
    """初始化并注册所有默认算子"""
    registry = register_default_operators()
    return registry

__all__ = [
    # 基类
    "BaseOperator",
    "OperatorResult",
    "OperatorMetadata",
    # 组合引擎
    "SerialPipeline",
    "ParallelExecutor",
    "ConditionalBranch",
    "LoopIterator",
    "TryCatch",
    # 注册表
    "OperatorRegistry",
    "get_registry",
    "register_default_operators",
    # 便捷函数
    "create_pipeline",
    "create_try_catch",
    "create_loop",
    "create_conditional",
    "init_operators",
    # 版本
    "__version__",
]
