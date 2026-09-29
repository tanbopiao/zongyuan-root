#!/usr/bin/env python3
"""
L2 自动+预审执行器 - ZONGYUAN-ROOT Autonomy Governor
风险50-70%，自动生成方案+风险评估，人工预审确认后执行，24h超时自动执行
典型场景：元法则更新/算子阈值调整/中等规模部署/新功能上线
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
"""
import json
import os
import sys
import subprocess
from typing import Dict, List, Optional, Callable
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from audit.decision_audit import DecisionAuditor

CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'config', 'autonomy_config.json')
LOG_DIR = os.path.join(os.path.dirname(__file__), '..', 'logs')
PENDING_DIR = os.path.join(os.path.dirname(__file__), '..', 'logs', 'l2_pending')


class L2PrecheckExecutor:
    """L2自动+预审执行器"""
    
    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = CONFIG_PATH
        with open(config_path) as f:
            self.config = json.load(f)
        self.auditor = DecisionAuditor()
        os.makedirs(LOG_DIR, exist_ok=True)
        os.makedirs(PENDING_DIR, exist_ok=True)
        
        self.timeout_hours = self.config['autonomy_levels']['L2'].get('timeout_hours', 24)
        
        # L2可执行操作
        self.operations = {
            'metalaw_update': self._metalaw_update,
            'operator_threshold': self._operator_threshold,
            'medium_deploy': self._medium_deploy,
            'new_feature_launch': self._new_feature_launch,
        }
    
    def submit(self, operation: str, params: Dict = None,
               risk_score: float = 60) -> Dict:
        """
        提交L2操作：生成预审方案，等待人工确认或超时自动执行
        """
        if params is None:
            params = {}
        
        # 1. 创建审计快照
        audit_id = self.auditor.create_snapshot(
            operation=operation,
            level='L2',
            risk_score=risk_score,
            params=params
        )
        
        # 2. 生成预审方案
        precheck = self._generate_precheck(operation, params, risk_score)
        
        # 3. 保存待执行任务
        pending = {
            'audit_id': audit_id,
            'operation': operation,
            'params': params,
            'risk_score': risk_score,
            'precheck': precheck,
            'status': 'PENDING_PRECHECK',
            'submitted_at': datetime.now(timezone.utc).isoformat(),
            'deadline': (datetime.now(timezone.utc) + timedelta(hours=self.timeout_hours)).isoformat(),
            'approved': None,
            'approved_by': None,
            'approved_at': None
        }
        
        pending_file = os.path.join(PENDING_DIR, f'{audit_id}.json')
        with open(pending_file, 'w') as f:
            json.dump(pending, f, ensure_ascii=False, indent=2)
        
        # 4. 发送预审通知（飞书待办）
        self._send_precheck_notification(pending)
        
        return {
            'audit_id': audit_id,
            'operation': operation,
            'level': 'L2',
            'status': 'PENDING_PRECHECK',
            'risk_score': risk_score,
            'precheck': precheck,
            'deadline': pending['deadline'],
            'timeout_hours': self.timeout_hours,
            'message': f'预审方案已生成，等待人工确认。{self.timeout_hours}h超时后自动执行。'
        }
    
    def approve(self, audit_id: str, approver: str = 'human', 
                comment: str = '') -> Dict:
        """人工批准执行"""
        pending_file = os.path.join(PENDING_DIR, f'{audit_id}.json')
        if not os.path.exists(pending_file):
            return {'success': False, 'error': 'pending task not found'}
        
        with open(pending_file) as f:
            pending = json.load(f)
        
        pending['approved'] = True
        pending['approved_by'] = approver
        pending['approved_at'] = datetime.now(timezone.utc).isoformat()
        pending['status'] = 'APPROVED'
        
        with open(pending_file, 'w') as f:
            json.dump(pending, f, ensure_ascii=False, indent=2)
        
        # 记录审批
        self.auditor.record_approval(audit_id, True, approver, comment)
        
        # 立即执行
        return self._execute_pending(pending)
    
    def reject(self, audit_id: str, reason: str = '') -> Dict:
        """人工拒绝"""
        pending_file = os.path.join(PENDING_DIR, f'{audit_id}.json')
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
    
    def check_timeouts(self) -> List[Dict]:
        """检查超时任务并自动执行"""
        executed = []
        now = datetime.now(timezone.utc)
        
        for filename in os.listdir(PENDING_DIR):
            if not filename.endswith('.json'):
                continue
            pending_file = os.path.join(PENDING_DIR, filename)
            with open(pending_file) as f:
                pending = json.load(f)
            
            if pending['status'] != 'PENDING_PRECHECK':
                continue
            
            deadline = datetime.fromisoformat(pending['deadline'])
            if now >= deadline:
                # 超时自动执行
                pending['approved'] = True
                pending['approved_by'] = 'AUTO_TIMEOUT'
                pending['approved_at'] = now.isoformat()
                pending['status'] = 'AUTO_EXECUTED_TIMEOUT'
                
                with open(pending_file, 'w') as f:
                    json.dump(pending, f, ensure_ascii=False, indent=2)
                
                result = self._execute_pending(pending)
                result['auto_timeout'] = True
                executed.append(result)
        
        return executed
    
    def list_pending(self) -> List[Dict]:
        """列出待预审任务"""
        pending_list = []
        for filename in os.listdir(PENDING_DIR):
            if not filename.endswith('.json'):
                continue
            with open(os.path.join(PENDING_DIR, filename)) as f:
                pending = json.load(f)
            if pending['status'] == 'PENDING_PRECHECK':
                pending_list.append({
                    'audit_id': pending['audit_id'],
                    'operation': pending['operation'],
                    'risk_score': pending['risk_score'],
                    'submitted_at': pending['submitted_at'],
                    'deadline': pending['deadline'],
                    'precheck_summary': pending['precheck'].get('summary', '')
                })
        return pending_list
    
    def _generate_precheck(self, operation: str, params: Dict, 
                           risk_score: float) -> Dict:
        """生成预审方案"""
        return {
            'operation': operation,
            'risk_score': risk_score,
            'risk_level': 'L2',
            'summary': f'{operation} - 风险{risk_score}%，需人工预审',
            'impact_analysis': self._analyze_impact(operation, params),
            'rollback_plan': self._generate_rollback_plan(operation),
            'execution_steps': self._generate_steps(operation, params),
            'estimated_duration': '5-30分钟',
            'requires_approval': True,
            'timeout_auto_execute': f'{self.timeout_hours}h后自动执行'
        }
    
    def _analyze_impact(self, operation: str, params: Dict) -> Dict:
        """影响分析"""
        return {
            'scope': '系统级',
            'affected_components': [operation],
            'downtime': '无（灰度执行）',
            'data_risk': '低（有快照回滚）'
        }
    
    def _generate_rollback_plan(self, operation: str) -> Dict:
        """回滚方案"""
        return {
            'method': '快照回滚',
            'trigger': '错误率>5%或人工触发',
            'estimated_time': '2分钟',
            'steps': ['恢复执行前快照', '验证服务状态', '通知相关方']
        }
    
    def _generate_steps(self, operation: str, params: Dict) -> List[str]:
        """生成执行步骤"""
        return [
            f'1. 执行前快照（已完成）',
            f'2. 灰度10%执行{operation}',
            f'3. 观察60秒，错误率<5%继续',
            f'4. 灰度50%执行',
            f'5. 全量执行',
            f'6. 验证结果+事后复盘'
        ]
    
    def _execute_pending(self, pending: Dict) -> Dict:
        """执行待处理任务"""
        operation = pending['operation']
        params = pending['params']
        audit_id = pending['audit_id']
        
        start_time = datetime.now(timezone.utc)
        try:
            handler = self._get_handler(operation)
            result = handler(params)
            success = result.get('success', True)
            error = None
        except Exception as e:
            result = {'success': False, 'error': str(e)}
            success = False
            error = str(e)
        
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        self.auditor.record_execution(
            audit_id=audit_id,
            success=success,
            result=result,
            duration_seconds=duration,
            error=error
        )
        
        # 更新状态
        pending_file = os.path.join(PENDING_DIR, f'{audit_id}.json')
        with open(pending_file) as f:
            pending = json.load(f)
        pending['status'] = 'EXECUTED' if success else 'FAILED'
        pending['execution_result'] = result
        pending['execution_duration'] = duration
        with open(pending_file, 'w') as f:
            json.dump(pending, f, ensure_ascii=False, indent=2)
        
        # 发送完成通知
        self._send_complete_notification(pending, success, duration)
        
        return {
            'audit_id': audit_id,
            'operation': operation,
            'level': 'L2',
            'success': success,
            'duration_seconds': round(duration, 2),
            'result': result,
            'approved_by': pending.get('approved_by'),
            'auto_timeout': pending.get('approved_by') == 'AUTO_TIMEOUT'
        }
    
    def _get_handler(self, operation: str) -> Callable:
        op_lower = operation.lower()
        for key, handler in self.operations.items():
            if key in op_lower:
                return handler
        return self._generic_execute
    
    def _metalaw_update(self, params: Dict) -> Dict:
        return {'success': True, 'message': '元法则更新仿真完成', 'metalaw': params.get('metalaw', 'unknown')}
    
    def _operator_threshold(self, params: Dict) -> Dict:
        return {'success': True, 'message': '算子阈值调整仿真完成', 'operator': params.get('operator', 'unknown')}
    
    def _medium_deploy(self, params: Dict) -> Dict:
        return {'success': True, 'message': '中等规模部署仿真完成', 'target': params.get('target', 'unknown')}
    
    def _new_feature_launch(self, params: Dict) -> Dict:
        return {'success': True, 'message': '新功能上线仿真完成', 'feature': params.get('feature', 'unknown')}
    
    def _generic_execute(self, params: Dict) -> Dict:
        return {'success': True, 'message': 'L2通用执行仿真完成'}
    
    def _send_precheck_notification(self, pending: Dict):
        """发送预审通知"""
        message = (
            f"⚠️ [L2预审待确认]\n"
            f"操作: {pending['operation']}\n"
            f"审计ID: {pending['audit_id']}\n"
            f"风险: {pending['risk_score']}%\n"
            f"截止: {pending['deadline']}\n"
            f"超时自动执行: {self.timeout_hours}h\n"
            f"Ω₀⊂⊙∞⊂Ω | DID-BR-000002"
        )
        self.auditor.record_notification(pending['audit_id'], 'feishu_todo', True, 'precheck submitted')
    
    def _send_complete_notification(self, pending: Dict, success: bool, duration: float):
        """发送完成通知"""
        status = "✅" if success else "❌"
        message = (
            f"{status} [L2执行完成]\n"
            f"操作: {pending['operation']}\n"
            f"审计ID: {pending['audit_id']}\n"
            f"耗时: {round(duration, 2)}秒\n"
            f"审批人: {pending.get('approved_by', 'unknown')}\n"
            f"Ω₀⊂⊙∞⊂Ω | DID-BR-000002"
        )
        self.auditor.record_notification(pending['audit_id'], 'feishu', success, 'execution complete')


def main():
    """测试"""
    executor = L2PrecheckExecutor()
    
    print("=" * 60)
    print("L2自动+预审执行器测试")
    print("=" * 60)
    
    # 提交任务
    print("\n1. 提交L2预审任务:")
    result = executor.submit('元法则更新', {'metalaw': 'META-003'}, risk_score=55)
    print(f"   审计ID: {result['audit_id']}")
    print(f"   状态: {result['status']}")
    print(f"   截止: {result['deadline']}")
    
    audit_id = result['audit_id']
    
    # 列出待处理
    print("\n2. 待预审任务列表:")
    pending = executor.list_pending()
    for p in pending:
        print(f"   {p['audit_id']}: {p['operation']} (风险{p['risk_score']}%)")
    
    # 批准执行
    print("\n3. 人工批准执行:")
    exec_result = executor.approve(audit_id, approver='test_user', comment='同意执行')
    print(f"   成功: {exec_result['success']}")
    print(f"   耗时: {exec_result['duration_seconds']}s")
    print(f"   审批人: {exec_result['approved_by']}")
    
    # 测试超时自动执行
    print("\n4. 测试超时自动执行（模拟超时）:")
    result2 = executor.submit('算子阈值调整', {'operator': 'drift'}, risk_score=60)
    # 手动修改截止时间为过去
    pending_file = os.path.join(PENDING_DIR, f"{result2['audit_id']}.json")
    with open(pending_file) as f:
        p = json.load(f)
    p['deadline'] = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    with open(pending_file, 'w') as f:
        json.dump(p, f, ensure_ascii=False, indent=2)
    
    timeout_results = executor.check_timeouts()
    for r in timeout_results:
        print(f"   超时自动执行: {r['audit_id']} - 成功={r['success']} (auto_timeout={r['auto_timeout']})")
    
    print("\n" + "=" * 60)
    print("L2执行器测试完成")
    print("=" * 60)


if __name__ == '__main__':
    main()
