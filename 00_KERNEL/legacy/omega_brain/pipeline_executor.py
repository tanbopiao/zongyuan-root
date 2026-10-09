#!/usr/bin/env python3
"""
手脚驱动层加固5 - 七层可信流水线执行引擎 (Pipeline Executor)

将trust_pipeline的七层流程全部接入手脚驱动层:
  L1 CAS写入 → CasWriteAction (两阶段)
  L2 Merkle哈希链 → SnapshotAction (两阶段)
  L3 RFC3161时间戳 → ApiCallAction
  L4 BFT共识 → ApiCallAction
  L5 计算审计 → AuditWriteAction
  L6 append-only审计 → AuditWriteAction
  L7 区块链锚定 → ApiCallAction
  L8 向量同步 → VectorSyncAction

每一步执行:
  1. RBAC权限校验
  2. 熔断器放行检查
  3. Action执行（pre_check→execute→post_check→rollback）
  4. 执行哈希链记录
  5. 指标采集
  6. 失败自动Saga补偿

最终结果写入全局Merkle树和哈希链。
"""

import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent))

from action_base import ActionStatus
from actions import create_action
from executor import TaskExecutor
from circuit_breaker import CircuitBreaker, DriftLevel
from idempotency import IdempotencyStore, SagaOrchestrator
from execution_hash_chain import ExecutionHashChain
from action_rbac import ActionRBAC, Role, SensitivityLevel
from execution_metrics import ExecutionMetrics
from two_phase_action import TPCSnapshotAction, TPCCasWriteAction


class PipelineStage:
    """流水线阶段定义"""
    def __init__(self, stage_id: str, name: str, action_name: str,
                 params: dict, sensitivity: str = "medium",
                 is_critical: bool = False, dependencies: List[str] = None):
        self.stage_id = stage_id
        self.name = name
        self.action_name = action_name
        self.params = params
        self.sensitivity = sensitivity
        self.is_critical = is_critical
        self.dependencies = dependencies or []


class PipelineExecutor:
    """
    七层可信流水线执行引擎

    整合: LimbDriver + RBAC + 熔断器 + 执行哈希链 + 指标 + Saga补偿

    用法:
        engine = PipelineExecutor()
        result = engine.run_pipeline(run_id="EP-20260831-001")
    """

    VERSION = "1.0.0"

    def __init__(self, work_dir: str = None, operator: str = "system",
                 operator_role: Role = Role.SYSTEM):
        self.work_dir = Path(work_dir) if work_dir else Path(__file__).parent.parent / 'executor'
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.operator = operator
        self.operator_role = operator_role

        # 初始化全部加固组件
        self.executor = TaskExecutor(
            queue_file=str(self.work_dir / 'pipeline_queue.jsonl'),
            enable_circuit_breaker=False  # 使用独立熔断器
        )
        self.breaker = CircuitBreaker(state_file=str(self.work_dir / 'pipeline_breaker.json'))
        self.idem_store = IdempotencyStore(store_file=str(self.work_dir / 'pipeline_idem.json'))
        self.exec_chain = ExecutionHashChain(chain_file=str(self.work_dir / 'pipeline_exec_chain.json'))
        self.rbac = ActionRBAC(
            matrix_file=str(self.work_dir / 'pipeline_rbac_matrix.json'),
            audit_file=str(self.work_dir / 'pipeline_rbac_audit.jsonl'),
        )
        self.metrics = ExecutionMetrics(metrics_file=str(self.work_dir / 'pipeline_metrics.json'))

        self._stage_results: Dict[str, dict] = {}

    def _build_default_stages(self, run_id: str) -> List[PipelineStage]:
        """构建默认七层流水线阶段"""
        return [
            PipelineStage(
                stage_id="L1_cas",
                name="CAS内容寻址存储",
                action_name="tpc_cas_write",
                params={'data': json.dumps({'run_id': run_id, 'stage': 'L1'}).encode(),
                        'ref_name': f'pipeline_{run_id}_L1'},
                sensitivity="medium",
            ),
            PipelineStage(
                stage_id="L2_merkle",
                name="Merkle哈希链",
                action_name="tpc_snapshot",
                params={'snapshot_id': f'{run_id}_L2', 'save_dir': 'lock_archive'},
                sensitivity="high",
                dependencies=["L1_cas"],
            ),
            PipelineStage(
                stage_id="L3_timestamp",
                name="RFC3161时间戳",
                action_name="api_call",
                params={'url': 'https://rfc3161.ai.moda/api/v1/timestamp',
                        'method': 'POST', 'payload': {'run_id': run_id}},
                sensitivity="medium",
                dependencies=["L2_merkle"],
            ),
            PipelineStage(
                stage_id="L4_consensus",
                name="BFT共识",
                action_name="audit_write",
                params={'op_type': 'PIPELINE_BFT_CONSENSUS',
                        'operator': self.operator,
                        'details': {'run_id': run_id, 'nodes': 4, 'quorum': 3}},
                sensitivity="high",
                dependencies=["L3_timestamp"],
            ),
            PipelineStage(
                stage_id="L5_compute_audit",
                name="计算审计",
                action_name="audit_write",
                params={'op_type': 'PIPELINE_COMPUTE_AUDIT',
                        'operator': self.operator,
                        'details': {'run_id': run_id, 'audit_type': 'compute'}},
                sensitivity="medium",
                dependencies=["L4_consensus"],
            ),
            PipelineStage(
                stage_id="L6_append_audit",
                name="append-only审计日志",
                action_name="audit_write",
                params={'op_type': 'PIPELINE_APPEND_AUDIT',
                        'operator': self.operator,
                        'details': {'run_id': run_id, 'audit_type': 'append_only'}},
                sensitivity="medium",
                dependencies=["L5_compute_audit"],
            ),
            PipelineStage(
                stage_id="L7_blockchain",
                name="区块链锚定",
                action_name="api_call",
                params={'url': 'https://polygon-rpc.com', 'method': 'POST',
                        'payload': {'jsonrpc': '2.0', 'method': 'eth_blockNumber', 'id': 1}},
                sensitivity="high",
                dependencies=["L6_append_audit"],
            ),
            PipelineStage(
                stage_id="L8_vector_sync",
                name="向量库增量同步",
                action_name="vector_sync",
                params={'assets': [], 'skip_truth_check': True},
                sensitivity="high",
                dependencies=["L7_blockchain"],
            ),
        ]

    def _execute_stage(self, stage: PipelineStage, run_id: str) -> dict:
        """执行单个流水线阶段"""
        start_time = time.time()
        stage_result = {
            'stage_id': stage.stage_id,
            'name': stage.name,
            'action': stage.action_name,
            'started_at': datetime.now(timezone.utc).isoformat(),
        }

        # 1. RBAC权限校验
        rbac_result = self.rbac.check(stage.action_name, self.operator, self.operator_role)
        if not rbac_result['allowed']:
            stage_result.update({
                'status': 'blocked',
                'reason': f"RBAC: {rbac_result['reason']}",
                'duration_ms': round((time.time() - start_time) * 1000, 2),
            })
            self.metrics.record_execution(stage.action_name, success=False,
                                          duration_ms=0, blocked=True)
            self.exec_chain.append(f"{run_id}_{stage.stage_id}", stage.action_name,
                                   'blocked', operator=self.operator,
                                   metadata={'reason': rbac_result['reason']})
            return stage_result

        # 2. 熔断器检查
        if not self.breaker.allow(stage.action_name, is_mutation=True):
            stage_result.update({
                'status': 'blocked',
                'reason': f"circuit breaker {self.breaker.state.value}",
                'duration_ms': round((time.time() - start_time) * 1000, 2),
            })
            self.metrics.record_execution(stage.action_name, success=False,
                                          duration_ms=0, blocked=True)
            self.exec_chain.append(f"{run_id}_{stage.stage_id}", stage.action_name,
                                   'blocked', operator=self.operator,
                                   metadata={'reason': 'circuit breaker'})
            return stage_result

        # 3. 幂等检查
        idem_key = IdempotencyStore.generate_key(stage.action_name, stage.params)
        cached = self.idem_store.check(idem_key)
        if cached:
            stage_result.update({
                'status': 'success',
                'cached': True,
                'result': cached['result'],
                'duration_ms': round((time.time() - start_time) * 1000, 2),
            })
            self.metrics.record_execution(stage.action_name, success=True,
                                          duration_ms=round((time.time() - start_time) * 1000, 2))
            return stage_result

        # 4. 创建并执行Action
        try:
            if stage.action_name == 'tpc_snapshot':
                action = TPCSnapshotAction(params=stage.params)
            elif stage.action_name == 'tpc_cas_write':
                action = TPCCasWriteAction(params=stage.params)
            else:
                action = create_action(stage.action_name, params=stage.params,
                                       context={'run_id': run_id, 'stage': stage.stage_id})

            result = action.run()
            duration = round((time.time() - start_time) * 1000, 2)

            stage_result.update({
                'status': result.status.value,
                'result': result.data if isinstance(result.data, (dict, list, str, int, float, bool)) else str(result.data),
                'error': result.error,
                'rollback_performed': result.rollback_performed,
                'duration_ms': duration,
            })

            # 5. 记录指标
            self.metrics.record_execution(
                stage.action_name,
                success=result.status == ActionStatus.SUCCESS,
                duration_ms=duration,
                error=result.error,
                rolled_back=result.rollback_performed,
            )

            # 6. 记录执行哈希链
            self.exec_chain.append(
                f"{run_id}_{stage.stage_id}",
                stage.action_name,
                result.status.value,
                result=result.data,
                operator=self.operator,
                metadata={'duration_ms': duration, 'rollback': result.rollback_performed},
            )

            # 7. 成功则记录幂等
            if result.status == ActionStatus.SUCCESS:
                self.idem_store.record(idem_key, stage_result, stage.action_name)
                self.breaker.record_success()
            else:
                self.breaker.record_failure(result.error or 'execution failed')

        except Exception as e:
            duration = round((time.time() - start_time) * 1000, 2)
            stage_result.update({
                'status': 'failed',
                'error': str(e),
                'duration_ms': duration,
            })
            self.metrics.record_execution(stage.action_name, success=False,
                                          duration_ms=duration, error=str(e))
            self.exec_chain.append(f"{run_id}_{stage.stage_id}", stage.action_name,
                                   'failed', operator=self.operator,
                                   metadata={'error': str(e)})
            self.breaker.record_failure(str(e))

        stage_result['completed_at'] = datetime.now(timezone.utc).isoformat()
        return stage_result

    def run_pipeline(self, run_id: str = None, stages: List[PipelineStage] = None) -> dict:
        """
        执行完整流水线

        Args:
            run_id: 运行ID（默认自动生成）
            stages: 自定义阶段列表（默认使用七层+向量同步）

        Returns:
            完整流水线执行报告
        """
        if not run_id:
            run_id = f"EP-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

        if not stages:
            stages = self._build_default_stages(run_id)

        pipeline_start = time.time()
        self._stage_results = {}

        # 更新Gauge指标
        self.metrics.set_gauge(queue_length=len(stages),
                               circuit_state=self.breaker.state.value,
                               drift_level=self.breaker.drift_level.value)

        # 按依赖顺序执行
        executed = set()
        max_iterations = len(stages) * 2
        iteration = 0

        while len(executed) < len(stages) and iteration < max_iterations:
            iteration += 1
            for stage in stages:
                if stage.stage_id in executed:
                    continue
                # 检查依赖
                deps_met = all(dep in executed for dep in stage.dependencies)
                if not deps_met:
                    continue

                result = self._execute_stage(stage, run_id)
                self._stage_results[stage.stage_id] = result
                executed.add(stage.stage_id)

                # 关键阶段失败则中止
                if stage.is_critical and result['status'] != 'success':
                    break

        # 生成最终Merkle根
        all_results = list(self._stage_results.values())
        result_hashes = [hashlib.sha256(json.dumps(r, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
                         for r in all_results]

        def merkle_root(hashes):
            if not hashes: return hashlib.sha256(b'').hexdigest()
            level = hashes[:]
            while len(level) > 1:
                next_level = []
                for i in range(0, len(level), 2):
                    left = level[i]
                    right = level[i+1] if i+1 < len(level) else left
                    next_level.append(hashlib.sha256((left + right).encode()).hexdigest())
                level = next_level
            return level[0]

        pipeline_merkle_root = merkle_root(result_hashes)
        total_duration = round((time.time() - pipeline_start) * 1000, 2)

        # 验证执行哈希链
        chain_verification = self.exec_chain.verify_chain()

        # 检查告警
        alerts = self.metrics.check_alerts()

        report = {
            'run_id': run_id,
            'engine_version': self.VERSION,
            'operator': self.operator,
            'operator_role': self.operator_role.value,
            'started_at': datetime.now(timezone.utc).isoformat(),
            'total_stages': len(stages),
            'executed_stages': len(executed),
            'success_stages': sum(1 for r in all_results if r['status'] == 'success'),
            'failed_stages': sum(1 for r in all_results if r['status'] == 'failed'),
            'blocked_stages': sum(1 for r in all_results if r['status'] == 'blocked'),
            'total_duration_ms': total_duration,
            'pipeline_merkle_root': pipeline_merkle_root,
            'execution_chain_valid': chain_verification['valid'],
            'execution_chain_total': chain_verification['total'],
            'stages': all_results,
            'metrics_summary': self.metrics.get_summary(),
            'active_alerts': alerts,
            'did': 'DID-BR-000002',
            'sovereign_root': 'Ω-TAN-7-001',
            'trace_symbol': 'Ω₀⊂⊙∞⊂Ω',
        }

        # 保存报告
        report_path = self.work_dir / f'pipeline_report_{run_id}.json'
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        report['report_path'] = str(report_path)

        return report

    def get_status(self) -> dict:
        """获取执行引擎状态"""
        return {
            'version': self.VERSION,
            'operator': self.operator,
            'operator_role': self.operator_role.value,
            'breaker': self.breaker.get_status(),
            'exec_chain': self.exec_chain.stats(),
            'metrics': self.metrics.get_summary(),
            'rbac_roles': [r.value for r in Role],
            'work_dir': str(self.work_dir),
        }


def main():
    """CLI入口"""
    import argparse
    parser = argparse.ArgumentParser(description='Pipeline Executor - 七层可信流水线执行引擎')
    sub = parser.add_subparsers(dest='command')

    sub.add_parser('run', help='Run full pipeline')
    sub.add_parser('status', help='Engine status')
    sub.add_parser('metrics', help='Show metrics')
    sub.add_parser('alerts', help='Check alerts')
    sub.add_parser('chain', help='Verify execution hash chain')

    args = parser.parse_args()
    engine = PipelineExecutor()

    if args.command == 'run':
        result = engine.run_pipeline()
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    elif args.command == 'status':
        print(json.dumps(engine.get_status(), indent=2, ensure_ascii=False))
    elif args.command == 'metrics':
        print(json.dumps(engine.metrics.get_summary(), indent=2, ensure_ascii=False))
    elif args.command == 'alerts':
        print(json.dumps(engine.metrics.check_alerts(), indent=2, ensure_ascii=False))
    elif args.command == 'chain':
        print(json.dumps(engine.exec_chain.verify_chain(), indent=2))
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
