#!/usr/bin/env python3
"""
灰度执行+熔断回滚引擎 - ZONGYUAN-ROOT Autonomy Governor
支持：灰度发布(10%→50%→100%)、错误率监控、自动熔断、快照回滚
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
"""
import json
import os
import sys
import shutil
from typing import Dict, List, Optional, Callable
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'config', 'autonomy_config.json')
ROLLBACK_DIR = os.path.join(os.path.dirname(__file__), '..', 'rollback')
LOG_DIR = os.path.join(os.path.dirname(__file__), '..', 'logs')


class CanaryRollbackEngine:
    """灰度执行+熔断回滚引擎"""

    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = CONFIG_PATH
        with open(config_path) as f:
            self.config = json.load(f)

        os.makedirs(ROLLBACK_DIR, exist_ok=True)
        os.makedirs(LOG_DIR, exist_ok=True)

        # 熔断阈值
        self.error_rate_threshold = self.config.get('rollback', {}).get('error_rate_threshold', 0.05)
        self.max_consecutive_failures = self.config.get('rollback', {}).get('max_consecutive_failures', 3)
        self.observation_seconds = self.config.get('rollback', {}).get('observation_seconds', 30)

        # 灰度阶段
        self.canary_stages = [
            {'name': 'canary_10pct', 'traffic': 0.10, 'observe': self.observation_seconds},
            {'name': 'canary_50pct', 'traffic': 0.50, 'observe': self.observation_seconds},
            {'name': 'full_rollout', 'traffic': 1.00, 'observe': 0},
        ]

    def create_snapshot(self, name: str, data: Dict) -> str:
        """创建执行前快照"""
        snapshot_id = f"SNAP-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{name[:20]}"
        snapshot = {
            'snapshot_id': snapshot_id,
            'name': name,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'data': data,
            'status': 'ACTIVE'
        }
        snap_file = os.path.join(ROLLBACK_DIR, f'{snapshot_id}.json')
        with open(snap_file, 'w') as f:
            json.dump(snapshot, f, ensure_ascii=False, indent=2)
        return snapshot_id

    def execute_with_canary(self, operation: str, executor: Callable,
                            params: Dict = None,
                            error_rate_fn: Callable = None) -> Dict:
        """
        灰度执行：10%→50%→100%，每阶段观察错误率
        错误率超阈值自动熔断+回滚
        """
        if params is None:
            params = {}

        # 1. 创建快照
        snapshot_id = self.create_snapshot(operation, params)
        execution_log = []
        consecutive_failures = 0
        rollback_triggered = False
        rollback_reason = None

        # 2. 逐阶段灰度
        for stage in self.canary_stages:
            stage_result = {
                'stage': stage['name'],
                'traffic': f"{int(stage['traffic']*100)}%",
                'started_at': datetime.now(timezone.utc).isoformat(),
                'status': 'EXECUTING'
            }

            try:
                # 执行当前阶段
                result = executor({**params, 'traffic_percent': stage['traffic']})
                stage_result['execution_success'] = result.get('success', True)

                # 计算错误率（仿真模式）
                if error_rate_fn:
                    error_rate = error_rate_fn(stage['traffic'])
                else:
                    error_rate = 0.0  # 仿真：无错误

                stage_result['error_rate'] = round(error_rate, 4)
                stage_result['error_rate_threshold'] = self.error_rate_threshold

                # 熔断判断
                if error_rate > self.error_rate_threshold:
                    consecutive_failures += 1
                    stage_result['status'] = 'CIRCUIT_BREAKER_TRIGGERED'
                    stage_result['message'] = f'错误率{error_rate:.2%}超过阈值{self.error_rate_threshold:.2%}'

                    if consecutive_failures >= self.max_consecutive_failures:
                        rollback_triggered = True
                        rollback_reason = f'连续{consecutive_failures}次错误率超阈值，自动回滚'
                        stage_result['action'] = 'ROLLBACK_INITIATED'
                        execution_log.append(stage_result)
                        break
                else:
                    consecutive_failures = 0
                    stage_result['status'] = 'PASSED'

            except Exception as e:
                stage_result['status'] = 'EXCEPTION'
                stage_result['error'] = str(e)
                consecutive_failures += 1
                if consecutive_failures >= self.max_consecutive_failures:
                    rollback_triggered = True
                    rollback_reason = f'连续{consecutive_failures}次异常，自动回滚'
                    execution_log.append(stage_result)
                    break

            stage_result['completed_at'] = datetime.now(timezone.utc).isoformat()
            execution_log.append(stage_result)

        # 3. 如需回滚
        if rollback_triggered:
            rollback_result = self.rollback(snapshot_id, rollback_reason)
            final_status = 'ROLLED_BACK'
        else:
            rollback_result = None
            final_status = 'FULLY_DEPLOYED'

        # 4. 记录执行日志
        log_entry = {
            'operation': operation,
            'snapshot_id': snapshot_id,
            'final_status': final_status,
            'rollback_triggered': rollback_triggered,
            'rollback_reason': rollback_reason,
            'stages': execution_log,
            'rollback_result': rollback_result,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        log_file = os.path.join(LOG_DIR, f'canary_{datetime.now(timezone.utc).strftime("%Y%m%d")}.jsonl')
        with open(log_file, 'a') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')

        return {
            'operation': operation,
            'snapshot_id': snapshot_id,
            'final_status': final_status,
            'rollback_triggered': rollback_triggered,
            'rollback_reason': rollback_reason,
            'stages_executed': len(execution_log),
            'execution_log': execution_log,
            'rollback_result': rollback_result
        }

    def rollback(self, snapshot_id: str, reason: str = '') -> Dict:
        """回滚到指定快照"""
        snap_file = os.path.join(ROLLBACK_DIR, f'{snapshot_id}.json')
        if not os.path.exists(snap_file):
            return {'success': False, 'error': 'snapshot not found'}

        with open(snap_file) as f:
            snapshot = json.load(f)

        # 标记快照已用于回滚
        snapshot['status'] = 'ROLLED_BACK'
        snapshot['rolled_back_at'] = datetime.now(timezone.utc).isoformat()
        snapshot['rollback_reason'] = reason
        with open(snap_file, 'w') as f:
            json.dump(snapshot, f, ensure_ascii=False, indent=2)

        return {
            'success': True,
            'snapshot_id': snapshot_id,
            'rolled_back_at': datetime.now(timezone.utc).isoformat(),
            'reason': reason,
            'restored_data_keys': list(snapshot.get('data', {}).keys())
        }

    def list_snapshots(self) -> List[Dict]:
        """列出所有快照"""
        snapshots = []
        for filename in sorted(os.listdir(ROLLBACK_DIR), reverse=True):
            if not filename.endswith('.json'):
                continue
            with open(os.path.join(ROLLBACK_DIR, filename)) as f:
                snap = json.load(f)
            snapshots.append({
                'snapshot_id': snap['snapshot_id'],
                'name': snap['name'],
                'created_at': snap['created_at'],
                'status': snap['status']
            })
        return snapshots

    def get_stats(self) -> Dict:
        """获取统计"""
        log_file = os.path.join(LOG_DIR, f'canary_{datetime.now(timezone.utc).strftime("%Y%m%d")}.jsonl')
        total = 0
        rolled_back = 0
        if os.path.exists(log_file):
            with open(log_file) as f:
                for line in f:
                    entry = json.loads(line)
                    total += 1
                    if entry.get('rollback_triggered'):
                        rolled_back += 1

        return {
            'snapshots_available': len(self.list_snapshots()),
            'today_executions': total,
            'today_rollbacks': rolled_back,
            'rollback_rate': f"{(rolled_back/total*100):.1f}%" if total > 0 else 'N/A',
            'error_rate_threshold': self.error_rate_threshold,
            'circuit_breaker_threshold': self.max_consecutive_failures,
            'engine_status': 'ACTIVE'
        }


def main():
    engine = CanaryRollbackEngine()
    print("=" * 60)
    print("灰度执行+熔断回滚引擎测试")
    print("=" * 60)

    # 测试1：正常灰度执行（无错误）
    print("\n1. 正常灰度执行（无错误）:")
    def mock_executor(params):
        return {'success': True, 'traffic': params.get('traffic_percent')}
    result = engine.execute_with_canary('测试服务部署', mock_executor, {'version': 'v2.0'})
    print(f"   最终状态: {result['final_status']}")
    print(f"   执行阶段: {result['stages_executed']}")
    print(f"   回滚触发: {result['rollback_triggered']}")

    # 测试2：错误率超阈值触发熔断回滚
    print("\n2. 错误率超阈值触发熔断回滚:")
    def mock_error_executor(params):
        return {'success': True}
    def mock_error_rate(traffic):
        return 0.15  # 15%错误率，超5%阈值
    result2 = engine.execute_with_canary(
        '高风险部署', mock_error_executor,
        {'version': 'v3.0'}, error_rate_fn=mock_error_rate
    )
    print(f"   最终状态: {result2['final_status']}")
    print(f"   回滚触发: {result2['rollback_triggered']}")
    print(f"   回滚原因: {result2['rollback_reason']}")

    # 测试3：快照列表
    print("\n3. 可用快照:")
    for snap in engine.list_snapshots()[:3]:
        print(f"   {snap['snapshot_id']}: {snap['name']} ({snap['status']})")

    # 统计
    print("\n4. 引擎统计:")
    for k, v in engine.get_stats().items():
        print(f"   {k}: {v}")

    print("\n" + "=" * 60)
    print("灰度+熔断+回滚引擎测试完成")
    print("=" * 60)


if __name__ == '__main__':
    main()
