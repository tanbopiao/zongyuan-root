#!/usr/bin/env python3
"""
算子组合引擎 - 5种组合模式（五行运化）
木：串行(SerialPipeline) - 有序生长
火：并行(ParallelExecutor) - 并发爆发
土：条件(ConditionalBranch) - 承载判断
金：循环(LoopIterator) - 收敛循环（手动栈，禁递归）
水：异常(TryCatch) - 降级流通
"""
import threading
import time
from typing import Any, Dict, List, Optional, Callable, Tuple
from dataclasses import dataclass, field
import uuid

from .base_operator import BaseOperator, OperatorInput, OperatorOutput, OperatorStatus


@dataclass
class PipelineResult:
    """流水线执行结果"""
    success: bool
    results: List[OperatorOutput] = field(default_factory=list)
    total_time_ms: float = 0.0
    pipeline_id: str = ""
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "pipeline_id": self.pipeline_id,
            "total_time_ms": round(self.total_time_ms, 2),
            "step_count": len(self.results),
            "results": [r.to_dict() for r in self.results],
            "error": self.error,
        }


class SerialPipeline:
    """
    串行管道 - 木：有序生长，前序生后序
    算子按顺序执行，前一个的输出作为后一个的输入
    """

    def __init__(self, operators: List[BaseOperator], name: str = "serial_pipeline"):
        self.operators = operators
        self.name = name
        self.pipeline_id = f"pipe-{uuid.uuid4().hex[:12]}"

    def execute(self, initial_input: OperatorInput) -> PipelineResult:
        start_time = time.time()
        results = []
        current_input = initial_input

        for i, operator in enumerate(self.operators):
            output = operator.execute(current_input)
            results.append(output)

            if not output.success:
                return PipelineResult(
                    success=False,
                    results=results,
                    total_time_ms=(time.time() - start_time) * 1000,
                    pipeline_id=self.pipeline_id,
                    error=f"第{i+1}个算子({operator.metadata.operator_name})执行失败: {output.error}",
                )

            # 将输出作为下一个算子的输入
            current_input = OperatorInput(
                params=output.data if isinstance(output.data, dict) else {"result": output.data},
                context={"previous_results": [r.to_dict() for r in results]},
            )

        return PipelineResult(
            success=True,
            results=results,
            total_time_ms=(time.time() - start_time) * 1000,
            pipeline_id=self.pipeline_id,
        )


class ParallelExecutor:
    """
    并行执行器 - 火：并发爆发，多路并行
    多个算子同时执行，共享相同输入，结果汇总
    """

    def __init__(self, operators: List[BaseOperator], name: str = "parallel_executor", max_workers: int = 10):
        self.operators = operators
        self.name = name
        self.max_workers = max_workers
        self.executor_id = f"par-{uuid.uuid4().hex[:12]}"

    def execute(self, input_data: OperatorInput) -> PipelineResult:
        start_time = time.time()
        results: List[Optional[OperatorOutput]] = [None] * len(self.operators)

        def run_operator(index: int, op: BaseOperator, inp: OperatorInput):
            results[index] = op.execute(inp)

        threads = []
        for i, op in enumerate(self.operators):
            t = threading.Thread(target=run_operator, args=(i, op, input_data))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        all_success = all(r and r.success for r in results)
        valid_results = [r for r in results if r is not None]

        return PipelineResult(
            success=all_success,
            results=valid_results,
            total_time_ms=(time.time() - start_time) * 1000,
            pipeline_id=self.executor_id,
            error=None if all_success else "部分算子执行失败",
        )


class ConditionalBranch:
    """
    条件分支 - 土：承载判断，路由分发
    根据条件判断结果，选择执行不同的算子分支
    """

    def __init__(
        self,
        condition: Callable[[OperatorInput], bool],
        true_branch: BaseOperator,
        false_branch: Optional[BaseOperator] = None,
        name: str = "conditional_branch",
    ):
        self.condition = condition
        self.true_branch = true_branch
        self.false_branch = false_branch
        self.name = name
        self.branch_id = f"cond-{uuid.uuid4().hex[:12]}"

    def execute(self, input_data: OperatorInput) -> PipelineResult:
        start_time = time.time()

        try:
            condition_result = self.condition(input_data)
        except Exception as e:
            return PipelineResult(
                success=False,
                results=[],
                total_time_ms=(time.time() - start_time) * 1000,
                pipeline_id=self.branch_id,
                error=f"条件判断异常: {str(e)}",
            )

        if condition_result:
            output = self.true_branch.execute(input_data)
            branch_taken = "true"
        elif self.false_branch:
            output = self.false_branch.execute(input_data)
            branch_taken = "false"
        else:
            return PipelineResult(
                success=True,
                results=[],
                total_time_ms=(time.time() - start_time) * 1000,
                pipeline_id=self.branch_id,
                error=None,
            )

        return PipelineResult(
            success=output.success,
            results=[output],
            total_time_ms=(time.time() - start_time) * 1000,
            pipeline_id=self.branch_id,
            error=output.error,
        )


class LoopIterator:
    """
    循环迭代器 - 金：收敛循环，手动栈禁递归
    重复执行算子直到满足终止条件，使用手动栈管理迭代状态
    遵循KD-STACK-0001元规则：禁止递归，强制手动栈
    """

    def __init__(
        self,
        operator: BaseOperator,
        max_iterations: int = 100,
        stop_condition: Optional[Callable[[OperatorOutput, int], bool]] = None,
        name: str = "loop_iterator",
    ):
        self.operator = operator
        self.max_iterations = max_iterations
        self.stop_condition = stop_condition
        self.name = name
        self.loop_id = f"loop-{uuid.uuid4().hex[:12]}"

    def execute(self, initial_input: OperatorInput) -> PipelineResult:
        start_time = time.time()
        results = []

        # 手动栈管理迭代状态（禁递归 - KD-STACK-0001）
        stack = [{"input": initial_input, "iteration": 0}]
        current_input = initial_input

        while stack:
            state = stack.pop()
            iteration = state["iteration"]

            if iteration >= self.max_iterations:
                break

            output = self.operator.execute(current_input)
            results.append(output)

            # 检查终止条件
            should_stop = False
            if self.stop_condition:
                try:
                    should_stop = self.stop_condition(output, iteration)
                except Exception:
                    should_stop = False

            if should_stop or not output.success:
                break

            # 更新输入，压入下一次迭代
            current_input = OperatorInput(
                params=output.data if isinstance(output.data, dict) else {"result": output.data, "iteration": iteration + 1},
                context={"iteration": iteration + 1, "previous_results": [r.to_dict() for r in results]},
            )
            stack.append({"input": current_input, "iteration": iteration + 1})

        all_success = all(r.success for r in results)

        return PipelineResult(
            success=all_success,
            results=results,
            total_time_ms=(time.time() - start_time) * 1000,
            pipeline_id=self.loop_id,
            error=None if all_success else "循环中存在失败执行",
        )


class TryCatch:
    """
    异常捕获 - 水：降级流通，主路径失败则润下到fallback
    尝试执行主算子，失败则执行fallback算子
    """

    def __init__(
        self,
        primary: BaseOperator,
        fallback: Optional[BaseOperator] = None,
        max_retries: int = 1,
        name: str = "try_catch",
    ):
        self.primary = primary
        self.fallback = fallback
        self.max_retries = max_retries
        self.name = name
        self.trycatch_id = f"tc-{uuid.uuid4().hex[:12]}"

    def execute(self, input_data: OperatorInput) -> PipelineResult:
        start_time = time.time()
        results = []

        # 尝试主算子（支持重试）
        for attempt in range(self.max_retries + 1):
            output = self.primary.execute(input_data)
            results.append(output)

            if output.success:
                return PipelineResult(
                    success=True,
                    results=results,
                    total_time_ms=(time.time() - start_time) * 1000,
                    pipeline_id=self.trycatch_id,
                )

        # 主算子失败，尝试fallback
        if self.fallback:
            fallback_output = self.fallback.execute(input_data)
            results.append(fallback_output)

            return PipelineResult(
                success=fallback_output.success,
                results=results,
                total_time_ms=(time.time() - start_time) * 1000,
                pipeline_id=self.trycatch_id,
                error=fallback_output.error,
            )

        return PipelineResult(
            success=False,
            results=results,
            total_time_ms=(time.time() - start_time) * 1000,
            pipeline_id=self.trycatch_id,
            error=f"主算子执行失败且无fallback: {results[-1].error if results else 'unknown'}",
        )


class OperatorCompositionEngine:
    """
    算子组合引擎 - 五行运化的统一入口
    支持5种组合模式的创建和执行
    """

    def __init__(self):
        self.compositions: Dict[str, Any] = {}
        self.execution_count = 0

    def create_serial(self, operators: List[BaseOperator], name: str = "") -> SerialPipeline:
        """创建串行管道"""
        pipeline = SerialPipeline(operators, name or f"serial_{len(self.compositions)}")
        self.compositions[pipeline.pipeline_id] = pipeline
        return pipeline

    def create_parallel(self, operators: List[BaseOperator], name: str = "", max_workers: int = 10) -> ParallelExecutor:
        """创建并行执行器"""
        executor = ParallelExecutor(operators, name or f"parallel_{len(self.compositions)}", max_workers)
        self.compositions[executor.executor_id] = executor
        return executor

    def create_conditional(
        self,
        condition: Callable[[OperatorInput], bool],
        true_branch: BaseOperator,
        false_branch: Optional[BaseOperator] = None,
        name: str = "",
    ) -> ConditionalBranch:
        """创建条件分支"""
        branch = ConditionalBranch(condition, true_branch, false_branch, name or f"cond_{len(self.compositions)}")
        self.compositions[branch.branch_id] = branch
        return branch

    def create_loop(
        self,
        operator: BaseOperator,
        max_iterations: int = 100,
        stop_condition: Optional[Callable[[OperatorOutput, int], bool]] = None,
        name: str = "",
    ) -> LoopIterator:
        """创建循环迭代器"""
        loop = LoopIterator(operator, max_iterations, stop_condition, name or f"loop_{len(self.compositions)}")
        self.compositions[loop.loop_id] = loop
        return loop

    def create_trycatch(
        self,
        primary: BaseOperator,
        fallback: Optional[BaseOperator] = None,
        max_retries: int = 1,
        name: str = "",
    ) -> TryCatch:
        """创建异常捕获"""
        tc = TryCatch(primary, fallback, max_retries, name or f"trycatch_{len(self.compositions)}")
        self.compositions[tc.trycatch_id] = tc
        return tc

    def get_stats(self) -> Dict[str, Any]:
        """获取组合引擎统计"""
        return {
            "total_compositions": len(self.compositions),
            "execution_count": self.execution_count,
            "composition_ids": list(self.compositions.keys()),
        }
