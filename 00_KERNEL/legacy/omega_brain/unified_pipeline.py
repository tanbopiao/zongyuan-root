#!/usr/bin/env python3
"""
P0修复 - 统一流水线执行引擎 (Unified Pipeline Executor)

核心修复: 此前trust_pipeline.py与pipeline_executor.py双轨并行，违反单一真值源原则。

修复方案:
  - pipeline_executor.py 成为唯一执行引擎（手脚驱动层全加固）
  - trust_pipeline.py 降级为配置定义层（只定义阶段配置，不执行）
  - 本模块作为统一入口，所有外部调用必须通过本模块

调用关系:
  外部调用 → UnifiedPipeline → PipelineExecutor(执行引擎) → Action(手脚驱动)
                           → TrustPipelineConfig(配置定义)

禁止: 外部直接调用trust_pipeline.py的执行方法
"""

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent))

from pipeline_executor import PipelineExecutor, PipelineStage
from evolution_executor import EvolutionExecutor
from truth_architecture import TruthArchitecture, TruthDomain


class TrustPipelineConfig:
    """
    可信流水线配置定义层（trust_pipeline.py降级后的角色）

    只负责定义流水线阶段配置，不执行任何操作。
    执行由PipelineExecutor负责。
    """

    VERSION = "2.0.0-config-only"

    @staticmethod
    def get_default_stages() -> List[dict]:
        """获取默认七层流水线阶段配置"""
        return [
            {'stage_id': 'L1_cas', 'name': 'CAS内容寻址存储',
             'action_name': 'tpc_cas_write', 'sensitivity': 'medium'},
            {'stage_id': 'L2_merkle', 'name': 'Merkle哈希链',
             'action_name': 'tpc_snapshot', 'sensitivity': 'high',
             'dependencies': ['L1_cas']},
            {'stage_id': 'L3_timestamp', 'name': 'RFC3161时间戳',
             'action_name': 'api_call', 'sensitivity': 'medium',
             'dependencies': ['L2_merkle']},
            {'stage_id': 'L4_consensus', 'name': 'BFT共识',
             'action_name': 'audit_write', 'sensitivity': 'high',
             'dependencies': ['L3_timestamp']},
            {'stage_id': 'L5_compute_audit', 'name': '计算审计',
             'action_name': 'audit_write', 'sensitivity': 'medium',
             'dependencies': ['L4_consensus']},
            {'stage_id': 'L6_append_audit', 'name': 'append-only审计',
             'action_name': 'audit_write', 'sensitivity': 'medium',
             'dependencies': ['L5_compute_audit']},
            {'stage_id': 'L7_blockchain', 'name': '区块链锚定',
             'action_name': 'api_call', 'sensitivity': 'high',
             'dependencies': ['L6_append_audit']},
            {'stage_id': 'L8_vector_sync', 'name': '向量库同步',
             'action_name': 'vector_sync', 'sensitivity': 'high',
             'dependencies': ['L7_blockchain']},
        ]

    @staticmethod
    def get_evolution_stages() -> List[dict]:
        """获取进化循环阶段配置"""
        return [
            {'stage_id': 'E1_truth_base', 'name': '真值基座', 'sensitivity': 'high'},
            {'stage_id': 'E2_architecture', 'name': '架构推演', 'sensitivity': 'high',
             'dependencies': ['E1_truth_base']},
            {'stage_id': 'E3_kernel_write', 'name': '内核写入', 'sensitivity': 'critical',
             'dependencies': ['E2_architecture']},
            {'stage_id': 'E4_global_lock', 'name': '全域锁档', 'sensitivity': 'critical',
             'dependencies': ['E3_kernel_write']},
            {'stage_id': 'E5_monitoring', 'name': '监测校验', 'sensitivity': 'high',
             'dependencies': ['E4_global_lock']},
            {'stage_id': 'E6_weekly', 'name': '周度巡检', 'sensitivity': 'medium',
             'dependencies': ['E5_monitoring']},
            {'stage_id': 'E7_archive', 'name': '归档输出', 'sensitivity': 'medium',
             'dependencies': ['E6_weekly']},
        ]

    @staticmethod
    def validate_config(stages: List[dict]) -> dict:
        """校验流水线配置合法性"""
        errors = []
        stage_ids = {s['stage_id'] for s in stages}

        for stage in stages:
            # 检查依赖是否存在
            for dep in stage.get('dependencies', []):
                if dep not in stage_ids:
                    errors.append(f"stage {stage['stage_id']} depends on non-existent {dep}")
            # 检查必要字段
            if 'action_name' not in stage:
                errors.append(f"stage {stage['stage_id']} missing action_name")

        # 检查循环依赖
        visited = set()
        rec_stack = set()

        def has_cycle(node):
            visited.add(node)
            rec_stack.add(node)
            stage = next((s for s in stages if s['stage_id'] == node), None)
            if stage:
                for dep in stage.get('dependencies', []):
                    if dep not in visited:
                        if has_cycle(dep):
                            return True
                    elif dep in rec_stack:
                        return True
            rec_stack.discard(node)
            return False

        for stage in stages:
            if stage['stage_id'] not in visited:
                if has_cycle(stage['stage_id']):
                    errors.append("circular dependency detected")
                    break

        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'stage_count': len(stages),
        }


class UnifiedPipeline:
    """
    统一流水线入口 - P0修复核心

    所有流水线/进化循环调用必须通过本模块。
    确保单一执行引擎（PipelineExecutor），消除双轨并行。
    """

    VERSION = "1.0.0"
    P0_FIX_APPLIED = True

    def __init__(self, work_dir: str = None):
        self.work_dir = Path(work_dir) if work_dir else Path(__file__).parent.parent / 'executor'
        self.work_dir.mkdir(parents=True, exist_ok=True)

        # 唯一执行引擎
        self.executor = PipelineExecutor(work_dir=str(self.work_dir / 'pipeline'))

        # 进化循环执行器（复用手脚驱动层）
        self.evolution = EvolutionExecutor(work_dir=str(self.work_dir / 'evolution'))

        # 配置定义层
        self.config = TrustPipelineConfig()

        # 四真值架构
        self.truth_arch = TruthArchitecture(store_dir=str(self.work_dir.parent / 'truth_architecture'))

    def run_trust_pipeline(self, run_id: str = None, custom_stages: List[dict] = None) -> dict:
        """
        执行可信流水线（唯一入口）

        Args:
            run_id: 运行ID
            custom_stages: 自定义阶段配置（默认使用七层配置）
        """
        # 从配置层获取阶段定义
        if custom_stages:
            validation = self.config.validate_config(custom_stages)
            if not validation['valid']:
                return {'success': False, 'error': f'invalid config: {validation["errors"]}'}
            stage_configs = custom_stages
        else:
            stage_configs = self.config.get_default_stages()

        # 转换为PipelineStage并执行
        stages = []
        for sc in stage_configs:
            params = sc.get('params', {})
            if sc['action_name'] == 'tpc_cas_write' and 'data' not in params:
                params['data'] = json.dumps({'run_id': run_id, 'stage': sc['stage_id']}).encode()
            if sc['action_name'] == 'tpc_snapshot' and 'snapshot_id' not in params:
                params['snapshot_id'] = f'{run_id}_{sc["stage_id"]}'
            if sc['action_name'] == 'audit_write' and 'op_type' not in params:
                params['op_type'] = f'PIPELINE_{sc["stage_id"].upper()}'
                params['operator'] = 'unified_pipeline'
                params['details'] = {'run_id': run_id, 'stage': sc['stage_id']}

            stages.append(PipelineStage(
                stage_id=sc['stage_id'],
                name=sc['name'],
                action_name=sc['action_name'],
                params=params,
                sensitivity=sc.get('sensitivity', 'medium'),
                dependencies=sc.get('dependencies', []),
            ))

        result = self.executor.run_pipeline(run_id=run_id, stages=stages)
        result['unified_pipeline_version'] = self.VERSION
        result['p0_fix_applied'] = self.P0_FIX_APPLIED
        return result

    def run_evolution_cycle(self, run_id: str = None) -> dict:
        """执行进化循环（唯一入口，通过手脚驱动层）"""
        result = self.evolution.run_evolution_cycle(run_id=run_id)
        result['unified_pipeline_version'] = self.VERSION
        result['p0_fix_applied'] = self.P0_FIX_APPLIED
        return result

    def run_full_cycle(self, run_id: str = None) -> dict:
        """
        执行完整循环: 可信流水线 + 进化循环

        这是元极恒一每日进化的标准入口。
        """
        if not run_id:
            run_id = f"FULL-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

        start = time.time()

        # 阶段1: 可信流水线
        pipeline_result = self.run_trust_pipeline(run_id=f'{run_id}_PIPELINE')

        # 阶段2: 进化循环
        evolution_result = self.run_evolution_cycle(run_id=f'{run_id}_EVOL')

        total_duration = round((time.time() - start) * 1000, 2)

        # 四真值记录
        self._record_runtime_truth(run_id, pipeline_result, evolution_result)

        return {
            'run_id': run_id,
            'success': pipeline_result.get('success_stages', 0) > 0 and evolution_result.get('success_stages', 0) > 0,
            'total_duration_ms': total_duration,
            'pipeline': {
                'stages': pipeline_result.get('total_stages', 0),
                'success': pipeline_result.get('success_stages', 0),
                'merkle_root': pipeline_result.get('pipeline_merkle_root', ''),
            },
            'evolution': {
                'stages': evolution_result.get('total_stages', 0),
                'success': evolution_result.get('success_stages', 0),
                'merkle_root': evolution_result.get('cycle_merkle_root', ''),
            },
            'execution_chain_valid': pipeline_result.get('execution_chain_valid', False) and evolution_result.get('execution_chain_valid', False),
            'p0_fix_applied': True,
            'unified_entry': True,
        }

    def _record_runtime_truth(self, run_id: str, pipeline_result: dict, evolution_result: dict):
        """将运行结果记录为运行真值"""
        try:
            self.truth_arch.add(
                item_id=f'runtime_{run_id}',
                domain=TruthDomain.RUNTIME,
                title=f'运行真值 - {run_id}',
                content={
                    'pipeline_success': pipeline_result.get('success_stages', 0),
                    'evolution_success': evolution_result.get('success_stages', 0),
                    'pipeline_merkle': pipeline_result.get('pipeline_merkle_root', ''),
                    'evolution_merkle': evolution_result.get('cycle_merkle_root', ''),
                    'executed_at': datetime.now(timezone.utc).isoformat(),
                },
                source='unified_pipeline',
                dependencies=['code_pipeline_executor', 'code_evolution_executor'],
            )
        except Exception:
            pass  # 真值记录失败不影响主流程

    def get_status(self) -> dict:
        """获取统一流水线状态"""
        return {
            'version': self.VERSION,
            'p0_fix_applied': self.P0_FIX_APPLIED,
            'single_execution_engine': 'pipeline_executor.py',
            'config_layer': 'trust_pipeline.py (config-only)',
            'executor': self.executor.get_status(),
            'evolution': self.evolution.get_status(),
            'truth_architecture': self.truth_arch.get_status(),
            'work_dir': str(self.work_dir),
        }


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Unified Pipeline - 统一流水线入口(P0修复)')
    sub = parser.add_subparsers(dest='command')

    sub.add_parser('pipeline', help='Run trust pipeline')
    sub.add_parser('evolution', help='Run evolution cycle')
    sub.add_parser('full', help='Run full cycle (pipeline + evolution)')
    sub.add_parser('status', help='Show status')
    sub.add_parser('config', help='Show default config')

    args = parser.parse_args()
    unified = UnifiedPipeline()

    if args.command == 'pipeline':
        print(json.dumps(unified.run_trust_pipeline(), indent=2, ensure_ascii=False, default=str))
    elif args.command == 'evolution':
        print(json.dumps(unified.run_evolution_cycle(), indent=2, ensure_ascii=False, default=str))
    elif args.command == 'full':
        print(json.dumps(unified.run_full_cycle(), indent=2, ensure_ascii=False, default=str))
    elif args.command == 'status':
        print(json.dumps(unified.get_status(), indent=2, ensure_ascii=False))
    elif args.command == 'config':
        print(json.dumps(TrustPipelineConfig.get_default_stages(), indent=2, ensure_ascii=False))
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
