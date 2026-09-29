"""
组合引擎 - ZONGYUAN-ROOT 算子化架构
实现5种算子组合模式，支持复杂工作流编排

组合模式：
1. SerialPipeline      串行管道
2. ParallelExecutor    并行执行
3. ConditionalBranch   条件分支
4. LoopIterator        循环迭代（手动栈，禁递归）
5. TryCatch            异常捕获+fallback

溯源标识：Ω₀⊂⊙∞⊂Ω
确权编码：DID-BR-000002
根挂载：ZONGYUAN-ROOT V1.7
"""

import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from operator_base import BaseOperator, OperatorResult


class SerialPipeline:
    """
    串行管道 - 算子按顺序执行，前一个输出作为后一个输入

    适用场景：部署闭环（检查→部署→验证→锁档）
    """

    def __init__(self, operators: List[BaseOperator], name: str = "serial_pipeline"):
        self.operators = operators
        self.name = name

    def execute(self, initial_inputs: Optional[Dict[str, Any]] = None) -> OperatorResult:
        """执行串行管道"""
        if initial_inputs is None:
            initial_inputs = {}

        start_time = time.time()
        current_inputs = dict(initial_inputs)
        results = []
        pipeline_data = {"initial_inputs": initial_inputs, "steps": []}

        for i, operator in enumerate(self.operators):
            step_start = time.time()
            result = operator(current_inputs)
            step_time = (time.time() - step_start) * 1000

            step_info = {
                "step": i + 1,
                "operator": operator.metadata.operator_name,
                "success": result.success,
                "execution_time_ms": round(step_time, 2),
            }
            pipeline_data["steps"].append(step_info)
            results.append(result)

            if not result.success:
                pipeline_data["failed_at_step"] = i + 1
                pipeline_data["error"] = result.error
                return OperatorResult(
                    success=False,
                    data=pipeline_data,
                    error=f"步骤{i+1}({operator.metadata.operator_name})失败: {result.error}",
                    operator_name=self.name,
                    execution_time_ms=round((time.time() - start_time) * 1000, 2),
                    timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
                )

            # 将当前算子输出合并到下一个算子的输入
            current_inputs.update(result.data)

        pipeline_data["final_output"] = current_inputs
        pipeline_data["total_steps"] = len(self.operators)

        return OperatorResult(
            success=True,
            data=pipeline_data,
            operator_name=self.name,
            execution_time_ms=round((time.time() - start_time) * 1000, 2),
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
        )

    def __call__(self, inputs: Optional[Dict[str, Any]] = None) -> OperatorResult:
        return self.execute(inputs)


class ParallelExecutor:
    """
    并行执行 - 多个算子同时执行，输入相同，输出合并

    适用场景：多源数据采集、多模型同时调用
    注意：Python GIL限制，实际并行通过concurrent.futures实现
    """

    def __init__(self, operators: List[BaseOperator], name: str = "parallel_executor"):
        self.operators = operators
        self.name = name

    def execute(self, inputs: Optional[Dict[str, Any]] = None) -> OperatorResult:
        """执行并行算子（简化版：顺序执行但模拟并行语义）"""
        if inputs is None:
            inputs = {}

        start_time = time.time()
        results = {}
        all_success = True

        for operator in self.operators:
            result = operator(dict(inputs))
            results[operator.metadata.operator_id] = result.to_dict()
            if not result.success:
                all_success = False

        return OperatorResult(
            success=all_success,
            data={
                "inputs": inputs,
                "results": results,
                "operator_count": len(self.operators),
            },
            operator_name=self.name,
            execution_time_ms=round((time.time() - start_time) * 1000, 2),
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
        )

    def __call__(self, inputs: Optional[Dict[str, Any]] = None) -> OperatorResult:
        return self.execute(inputs)


class ConditionalBranch:
    """
    条件分支 - 根据条件选择执行不同算子

    适用场景：根据检查结果选择修复方案、根据状态选择路径
    """

    def __init__(
        self,
        condition: Callable[[Dict[str, Any]], bool],
        true_operator: BaseOperator,
        false_operator: Optional[BaseOperator] = None,
        name: str = "conditional_branch",
    ):
        self.condition = condition
        self.true_operator = true_operator
        self.false_operator = false_operator
        self.name = name

    def execute(self, inputs: Optional[Dict[str, Any]] = None) -> OperatorResult:
        """执行条件分支"""
        if inputs is None:
            inputs = {}

        start_time = time.time()
        condition_result = self.condition(inputs)

        branch_data = {
            "inputs": inputs,
            "condition_result": condition_result,
            "branch_taken": "true" if condition_result else "false",
        }

        if condition_result:
            result = self.true_operator(inputs)
            branch_data["executed_operator"] = self.true_operator.metadata.operator_name
        else:
            if self.false_operator:
                result = self.false_operator(inputs)
                branch_data["executed_operator"] = self.false_operator.metadata.operator_name
            else:
                result = OperatorResult(
                    success=True,
                    data={"message": "条件为假，无false分支，跳过执行"},
                    operator_name=self.name,
                )
                branch_data["executed_operator"] = "none (skipped)"

        branch_data["result"] = result.to_dict()

        return OperatorResult(
            success=result.success,
            data=branch_data,
            error=result.error,
            operator_name=self.name,
            execution_time_ms=round((time.time() - start_time) * 1000, 2),
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
        )

    def __call__(self, inputs: Optional[Dict[str, Any]] = None) -> OperatorResult:
        return self.execute(inputs)


class LoopIterator:
    """
    循环迭代 - 手动栈实现，禁止递归

    适用场景：批量处理、重试循环、遍历集合
    元规则：禁止递归，必须使用手动栈/迭代
    """

    def __init__(
        self,
        operator: BaseOperator,
        max_iterations: int = 10,
        continue_condition: Optional[Callable[[Dict[str, Any], int], bool]] = None,
        name: str = "loop_iterator",
    ):
        self.operator = operator
        self.max_iterations = max_iterations
        self.continue_condition = continue_condition
        self.name = name

    def execute(self, initial_inputs: Optional[Dict[str, Any]] = None) -> OperatorResult:
        """执行循环迭代（手动栈实现，禁递归）"""
        if initial_inputs is None:
            initial_inputs = {}

        start_time = time.time()
        current_inputs = dict(initial_inputs)
        iterations = []
        all_success = True

        # 手动栈循环 - 禁止递归
        iteration = 0
        while iteration < self.max_iterations:
            # 检查继续条件
            if self.continue_condition and not self.continue_condition(current_inputs, iteration):
                break

            iter_start = time.time()
            result = self.operator(dict(current_inputs))
            iter_time = (time.time() - iter_start) * 1000

            iter_info = {
                "iteration": iteration + 1,
                "success": result.success,
                "execution_time_ms": round(iter_time, 2),
                "data": result.data,
                "error": result.error,
            }
            iterations.append(iter_info)

            if not result.success:
                all_success = False
                # 失败时可以选择继续或停止，这里继续但记录失败
                current_inputs.update({"last_error": result.error})
            else:
                current_inputs.update(result.data)

            iteration += 1

        return OperatorResult(
            success=all_success,
            data={
                "initial_inputs": initial_inputs,
                "iterations": iterations,
                "total_iterations": iteration,
                "max_iterations": self.max_iterations,
                "final_state": current_inputs,
            },
            operator_name=self.name,
            execution_time_ms=round((time.time() - start_time) * 1000, 2),
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
        )

    def __call__(self, inputs: Optional[Dict[str, Any]] = None) -> OperatorResult:
        return self.execute(inputs)


class TryCatch:
    """
    异常捕获+fallback - 主算子失败时执行备用算子

    适用场景：API调用失败切换备用模型、主方案失败执行兜底方案
    """

    def __init__(
        self,
        primary_operator: BaseOperator,
        fallback_operator: Optional[BaseOperator] = None,
        name: str = "try_catch",
    ):
        self.primary_operator = primary_operator
        self.fallback_operator = fallback_operator
        self.name = name

    def execute(self, inputs: Optional[Dict[str, Any]] = None) -> OperatorResult:
        """执行try-catch-fallback"""
        if inputs is None:
            inputs = {}

        start_time = time.time()
        result_data = {
            "inputs": inputs,
            "primary_executed": True,
            "primary_success": False,
            "fallback_executed": False,
        }

        # 尝试主算子
        primary_result = self.primary_operator(dict(inputs))
        result_data["primary_result"] = primary_result.to_dict()
        result_data["primary_success"] = primary_result.success

        if primary_result.success:
            result_data["final_result"] = primary_result.to_dict()
            return OperatorResult(
                success=True,
                data=result_data,
                operator_name=self.name,
                execution_time_ms=round((time.time() - start_time) * 1000, 2),
                timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            )

        # 主算子失败，执行fallback
        result_data["primary_error"] = primary_result.error

        if self.fallback_operator:
            result_data["fallback_executed"] = True
            fallback_result = self.fallback_operator(dict(inputs))
            result_data["fallback_result"] = fallback_result.to_dict()
            result_data["final_result"] = fallback_result.to_dict()

            return OperatorResult(
                success=fallback_result.success,
                data=result_data,
                error=fallback_result.error,
                operator_name=self.name,
                execution_time_ms=round((time.time() - start_time) * 1000, 2),
                timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            )
        else:
            result_data["final_result"] = primary_result.to_dict()
            return OperatorResult(
                success=False,
                data=result_data,
                error=f"主算子失败且无fallback: {primary_result.error}",
                operator_name=self.name,
                execution_time_ms=round((time.time() - start_time) * 1000, 2),
                timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            )

    def __call__(self, inputs: Optional[Dict[str, Any]] = None) -> OperatorResult:
        return self.execute(inputs)
