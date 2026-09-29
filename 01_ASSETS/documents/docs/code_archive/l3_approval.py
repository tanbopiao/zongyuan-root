#!/usr/bin/env python3
"""
L3 人工审批执行器 - ZONGYUAN-ROOT Autonomy Governor
风险70-85%，必须飞书审批通过后才能执行
典型场景：重大架构变更/高风险部署/安全策略调整/大额成本支出
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
"""
import json
import os
import sys
import subprocess
from typing import Dict, List, Optional
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from audit.decision_audit import DecisionAuditor

CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'config', 'autonomy_config.json')
LOG_DIR = os.path.join(os.path.dirname(__file__), '..', 'logs')
L3_PENDING_DIR = os.path.join(os.path.dirname(__file__), '..', 'logs', 'l3_pending')


class L3ApprovalExecutor:
    """L3人工审批执行器"""

    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = CONFIG_PATH
        with open(config_path) as f:
            self.config = json.load(f)
        self.auditor = DecisionAuditor()
        os.makedirs(LOG_DIR, exist_ok=True)
        os.makedirs(L3_PENDING_DIR, exist_ok=True)
        self.approval_code = self.config.get('feishu', {}).get('approval_code', '')

    def submit(self, operation: str, params: Dict = None,
               risk_score: float = 75) -> Dict:
        """提交L3审批：生成审批单，等待飞书审批通过"""
        if params is None:
            params = {}

        audit_id = self.auditor.create_snapshot(
            operation=operation, level='L3',
            risk_score=risk_score, params=params
        )

        approval = self._generate_approval(operation, params, risk_score)

        pending = {
            'audit_id': audit_id,
            'operation': operation,
            'params': params,
            'risk_score': risk_score,
            'approval': approval,
            'status': 'PENDING_APPROVAL',
            'submitted_at': datetime.now(timezone.utc).isoformat(),
            'approval_instance_code': None,
            'approved': None,
            'approved_by': None,
            'approved_at': None,
            'reject_reason': None
        }

        pending_file = os.path.join(L3_PENDING_DIR, f'{audit_id}.json')
        with open(pending_file, 'w') as f:
            json.dump(pending, f, ensure_ascii=False, indent=2)

        # 尝试发起飞书审批（有lark-cli时）
        instance_code = self._create_feishu_approval(pending)
        if instance_code:
            pending['approval_instance_code'] = instance_code
            with open(pending_file, 'w') as f:
                json.dump(pending, f, ensure_ascii=False, indent=2)

        return {
            'audit_id': audit_id,
            'operation': operation,
            'level': 'L3',
            'status': 'PENDING_APPROVAL',
            'risk_score': risk_score,
            'approval_code': self.approval_code,
            'approval_instance_code': instance_code,
            'approval': approval,
            'message': 'L3级操作必须飞书审批通过后才能执行。审批单已生成。'
        }

    def approve(self, audit_id: str, approver: str = 'human',
                comment: str = '') -> Dict:
        """审批通过，执行操作"""
        pending_file = os.path.join(L3_PENDING_DIR, f'{audit_id}.json')
        if not os.path.exists(pending_file):
            return {'success': False, 'error': 'pending task not found'}

        with open(pending_file) as f:
            pending = json.load(f)

        pending['approved'] = True
        pending['approved_by'] = approver
        pending['approved_at'] = datetime.now(timezone.utc).isoformat()
        pending['status'] = 'APPROVED_EXECUTING'

        with open(pending_file, 'w') as f:
            json.dump(pending, f, ensure_ascii=False, indent=2)

        self.auditor.record_approval(audit_id, True, approver, comment)

        # 灰度执行
        return self._execute_with_canary(pending)

    def reject(self, audit_id: str, reason: str = '') -> Dict:
        """审批拒绝"""
        pending_file = os.path.join(L3_PENDING_DIR, f'{audit_id}.json')
        if not os.path.exists(pending_file):
            return {'success': False, 'error': 'pending task not found'}

        with open(pending_file) as f:
            pending = json.load(f)

        pending['approved'] = False
        pending['status'] = 'REJECTED'
        pending['reject_reason'] = reason

        with open(pending_file, 'w') as f:
            json.dump(pending, f, ensure_ascii=False, indent=2)

        self.auditor.record_approval(audit_id, False, 'human', reason)
        return {'success': True, 'audit_id': audit_id, 'status': 'REJECTED', 'reason': reason}

    def _execute_with_canary(self, pending: Dict) -> Dict:
        """灰度执行：10%→50%→100%，每阶段观察错误率"""
        operation = pending['operation']
        audit_id = pending['audit_id']
        start_time = datetime.now(timezone.utc)

        canary_stages = [
            {'stage': 'canary_10pct', 'traffic': '10%', 'observe_seconds': 5},
            {'stage': 'canary_50pct', 'traffic': '50%', 'observe_seconds': 5},
            {'stage': 'full_rollout', 'traffic': '100%', 'observe_seconds': 0},
        ]

        execution_log = []
        success = True
        rollback_triggered = False

        for stage in canary_stages:
            stage_result = {
                'stage': stage['stage'],
                'traffic': stage['traffic'],
                'status': 'EXECUTED',
                'error_rate': 0.0,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            execution_log.append(stage_result)

            # 仿真：每阶段都成功
            if stage['observe_seconds'] > 0:
                pass  # 仿真模式不实际等待

        duration = (datetime.now(timezone.utc) - start_time).total_seconds()

        result = {
            'success': success,
            'operation': operation,
            'canary_stages': execution_log,
            'rollback_triggered': rollback_triggered,
            'message': f'{operation}灰度执行完成（仿真）'
        }

        self.auditor.record_execution(
            audit_id=audit_id, success=success,
            result=result, duration_seconds=duration
        )

        pending['status'] = 'EXECUTED' if success else 'FAILED'
        pending['execution_result'] = result
        with open(os.path.join(L3_PENDING_DIR, f'{audit_id}.json'), 'w') as f:
            json.dump(pending, f, ensure_ascii=False, indent=2)

        return {
            'audit_id': audit_id,
            'operation': operation,
            'level': 'L3',
            'success': success,
            'duration_seconds': round(duration, 2),
            'canary_stages': len(execution_log),
            'rollback_triggered': rollback_triggered,
            'approved_by': pending.get('approved_by')
        }

    def _generate_approval(self, operation: str, params: Dict,
                           risk_score: float) -> Dict:
        """生成审批单内容"""
        return {
            'title': f'[L3审批] {operation}',
            'risk_score': risk_score,
            'risk_level': '高风险',
            'impact_scope': '系统级/多模块',
            'rollback_plan': '快照回滚，预计2分钟',
            'estimated_duration': '10-30分钟',
            'requires_approval': True,
            'auto_execute_on_approval': True,
            'approval_deadline': (datetime.now(timezone.utc) + timedelta(hours=48)).isoformat()
        }

    def _create_feishu_approval(self, pending: Dict) -> Optional[str]:
        """尝试通过lark-cli创建飞书审批实例"""
        try:
            if not self.approval_code:
                return None
            # 仿真模式：不实际调用lark-cli
            return f'SIM-APPROVAL-{pending["audit_id"][:8]}'
        except Exception:
            return None

    def list_pending(self) -> List[Dict]:
        """列出待审批任务"""
        pending_list = []
        for filename in os.listdir(L3_PENDING_DIR):
            if not filename.endswith('.json'):
                continue
            with open(os.path.join(L3_PENDING_DIR, filename)) as f:
                pending = json.load(f)
            if pending['status'] == 'PENDING_APPROVAL':
                pending_list.append({
                    'audit_id': pending['audit_id'],
                    'operation': pending['operation'],
                    'risk_score': pending['risk_score'],
                    'submitted_at': pending['submitted_at'],
                    'approval_instance': pending.get('approval_instance_code')
                })
        return pending_list


def main():
    executor = L3ApprovalExecutor()
    print("=" * 60)
    print("L3人工审批执行器测试")
    print("=" * 60)

    print("\n1. 提交L3审批:")
    result = executor.submit('重大架构变更', {'scope': 'core'}, risk_score=78)
    print(f"   审计ID: {result['audit_id']}")
    print(f"   状态: {result['status']}")
    print(f"   审批实例: {result['approval_instance_code']}")

    audit_id = result['audit_id']

    print("\n2. 待审批列表:")
    for p in executor.list_pending():
        print(f"   {p['audit_id']}: {p['operation']} (风险{p['risk_score']}%)")

    print("\n3. 审批通过+灰度执行:")
    exec_result = executor.approve(audit_id, approver='admin', comment='同意灰度发布')
    print(f"   成功: {exec_result['success']}")
    print(f"   灰度阶段: {exec_result['canary_stages']}")
    print(f"   耗时: {exec_result['duration_seconds']}s")
    print(f"   回滚触发: {exec_result['rollback_triggered']}")

    print("\n" + "=" * 60)
    print("L3执行器测试完成 | 审批→灰度10%→50%→100%")
    print("=" * 60)


if __name__ == '__main__':
    main()
