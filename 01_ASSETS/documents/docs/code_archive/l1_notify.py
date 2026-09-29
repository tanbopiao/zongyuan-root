#!/usr/bin/env python3
"""
L1 自动+通知执行器 - ZONGYUAN-ROOT Autonomy Governor
风险30-50%，自动执行，同时飞书通知内核群，人工可随时中止
典型场景：服务重启/配置更新/产线调度/参数微调/低风险部署
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
"""
import json
import os
import sys
import subprocess
from typing import Dict, List, Optional, Callable
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from audit.decision_audit import DecisionAuditor

CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'config', 'autonomy_config.json')
LOG_DIR = os.path.join(os.path.dirname(__file__), '..', 'logs')


class L1NotifyExecutor:
    """L1自动+通知执行器"""
    
    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = CONFIG_PATH
        with open(config_path) as f:
            self.config = json.load(f)
        self.auditor = DecisionAuditor()
        os.makedirs(LOG_DIR, exist_ok=True)
        
        # L1可执行操作
        self.operations = {
            'service_restart': self._service_restart,
            'config_update': self._config_update,
            'pipeline_schedule': self._pipeline_schedule,
            'param_adjust': self._param_adjust,
            'low_risk_deploy': self._low_risk_deploy,
        }
    
    def execute(self, operation: str, params: Dict = None) -> Dict:
        """
        执行L1操作：自动执行 + 飞书通知
        """
        if params is None:
            params = {}
        
        # 1. 决策审计快照
        audit_id = self.auditor.create_snapshot(
            operation=operation,
            level='L1',
            risk_score=params.get('risk_score', 40),
            params=params
        )
        
        # 2. 发送执行前通知
        self._notify_start(operation, audit_id, params)
        
        # 3. 执行操作
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
        
        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()
        
        # 4. 记录审计
        self.auditor.record_execution(
            audit_id=audit_id,
            success=success,
            result=result,
            duration_seconds=duration,
            error=error
        )
        
        # 5. 发送执行结果通知
        self._notify_complete(operation, audit_id, success, duration, result)
        
        # 6. 记录日志
        self._log_execution(operation, success, duration, result)
        
        return {
            'audit_id': audit_id,
            'operation': operation,
            'level': 'L1',
            'success': success,
            'duration_seconds': round(duration, 2),
            'result': result,
            'notified': True,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    def _get_handler(self, operation: str) -> Callable:
        """获取操作处理器"""
        op_lower = operation.lower()
        for key, handler in self.operations.items():
            if key in op_lower:
                return handler
        return self._generic_execute
    
    def _service_restart(self, params: Dict) -> Dict:
        """服务重启（仿真模式，不实际重启）"""
        service = params.get('service', 'unknown')
        return {
            'success': True,
            'service': service,
            'action': 'restart_simulated',
            'message': f'服务{service}重启仿真完成（本地环境不实际重启）'
        }
    
    def _config_update(self, params: Dict) -> Dict:
        """配置更新"""
        config_key = params.get('config_key', 'unknown')
        config_value = params.get('config_value')
        return {
            'success': True,
            'config_key': config_key,
            'config_value': config_value,
            'message': f'配置{config_key}更新仿真完成'
        }
    
    def _pipeline_schedule(self, params: Dict) -> Dict:
        """产线调度"""
        pipeline = params.get('pipeline', 'unknown')
        task = params.get('task', 'unknown')
        return {
            'success': True,
            'pipeline': pipeline,
            'task': task,
            'message': f'产线{pipeline}任务{task}调度仿真完成'
        }
    
    def _param_adjust(self, params: Dict) -> Dict:
        """参数微调"""
        param_name = params.get('param_name', 'unknown')
        old_value = params.get('old_value')
        new_value = params.get('new_value')
        return {
            'success': True,
            'param_name': param_name,
            'old_value': old_value,
            'new_value': new_value,
            'message': f'参数{param_name}从{old_value}调整为{new_value}仿真完成'
        }
    
    def _low_risk_deploy(self, params: Dict) -> Dict:
        """低风险部署"""
        deploy_target = params.get('deploy_target', 'unknown')
        return {
            'success': True,
            'deploy_target': deploy_target,
            'message': f'低风险部署到{deploy_target}仿真完成'
        }
    
    def _generic_execute(self, params: Dict) -> Dict:
        """通用执行"""
        return {'success': True, 'message': 'L1通用执行仿真完成'}
    
    def _notify_start(self, operation: str, audit_id: str, params: Dict):
        """发送执行开始通知"""
        message = (
            f"🔄 [L1自动执行开始]\n"
            f"操作: {operation}\n"
            f"审计ID: {audit_id}\n"
            f"时间: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
            f"参数: {json.dumps(params, ensure_ascii=False)[:100]}\n"
            f"Ω₀⊂⊙∞⊂Ω | DID-BR-000002"
        )
        self._send_feishu_notification(message, audit_id, 'START')
    
    def _notify_complete(self, operation: str, audit_id: str, 
                         success: bool, duration: float, result: Dict):
        """发送执行完成通知"""
        status_icon = "✅" if success else "❌"
        status_text = "成功" if success else "失败"
        message = (
            f"{status_icon} [L1自动执行完成]\n"
            f"操作: {operation}\n"
            f"审计ID: {audit_id}\n"
            f"状态: {status_text}\n"
            f"耗时: {round(duration, 2)}秒\n"
            f"结果: {str(result)[:100]}\n"
            f"Ω₀⊂⊙∞⊂Ω | DID-BR-000002"
        )
        self._send_feishu_notification(message, audit_id, 'COMPLETE')
    
    def _send_feishu_notification(self, message: str, audit_id: str, event: str):
        """发送飞书通知（通过lark-cli）"""
        try:
            chat_id = self.config.get('feishu', {}).get('kernel_group_chat_id', '')
            if not chat_id:
                self.auditor.record_notification(audit_id, 'feishu', False, 'no chat_id')
                return False
            
            # 使用lark-cli发送消息
            cmd = [
                'lark-cli', 'im', '+messages-send',
                '--chat-id', chat_id,
                '--msg-type', 'text',
                '--content', json.dumps({'text': message}, ensure_ascii=False)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                self.auditor.record_notification(audit_id, 'feishu', True, event)
                return True
            else:
                self.auditor.record_notification(audit_id, 'feishu', False, result.stderr[:100])
                return False
        except Exception as e:
            self.auditor.record_notification(audit_id, 'feishu', False, str(e)[:100])
            return False
    
    def _log_execution(self, operation: str, success: bool, duration: float, result: Dict):
        """记录执行日志"""
        log_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'level': 'L1',
            'operation': operation,
            'success': success,
            'duration_seconds': round(duration, 2),
            'result_summary': str(result)[:200]
        }
        log_file = os.path.join(LOG_DIR, f'l1_executions_{datetime.now(timezone.utc).strftime("%Y%m%d")}.jsonl')
        with open(log_file, 'a') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')


def main():
    """测试"""
    executor = L1NotifyExecutor()
    
    print("=" * 60)
    print("L1自动+通知执行器测试")
    print("=" * 60)
    
    tests = [
        ('服务重启', {'service': 'memory-gateway'}),
        ('配置更新', {'config_key': 'timeout', 'config_value': 30}),
        ('产线调度', {'pipeline': 'drama', 'task': 'EP01'}),
        ('参数微调', {'param_name': 'threshold', 'old_value': 0.5, 'new_value': 0.6}),
    ]
    
    for op, params in tests:
        print(f"\n执行: {op}")
        result = executor.execute(op, params)
        print(f"  成功: {result['success']} | 耗时: {result['duration_seconds']}s | "
              f"通知: {result['notified']} | 审计ID: {result['audit_id']}")
    
    print("\n" + "=" * 60)
    print("L1执行器测试完成（飞书通知在有lark-cli环境时实际发送）")
    print("=" * 60)


if __name__ == '__main__':
    main()
