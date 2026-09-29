#!/usr/bin/env python3
"""
决策审计模块 - ZONGYUAN-ROOT Autonomy Governor
决策快照 + 审计日志 + 事后复盘
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
"""
import json
import os
import uuid
from typing import Dict, List, Optional
from datetime import datetime, timezone, timedelta

AUDIT_DIR = os.path.join(os.path.dirname(__file__), '..', 'logs', 'audit')
SNAPSHOT_DIR = os.path.join(os.path.dirname(__file__), '..', 'logs', 'snapshots')


class DecisionAuditor:
    """决策审计器"""
    
    def __init__(self):
        os.makedirs(AUDIT_DIR, exist_ok=True)
        os.makedirs(SNAPSHOT_DIR, exist_ok=True)
        self.audit_log = os.path.join(AUDIT_DIR, 'decision_audit.jsonl')
    
    def create_snapshot(self, operation: str, level: str, 
                        risk_score: float, params: Dict = None) -> str:
        """
        创建决策前快照
        返回审计ID
        """
        audit_id = str(uuid.uuid4())[:12]
        timestamp = datetime.now(timezone.utc).isoformat()
        
        snapshot = {
            'audit_id': audit_id,
            'operation': operation,
            'level': level,
            'risk_score': risk_score,
            'params': params or {},
            'timestamp': timestamp,
            'status': 'PENDING',
            'did': 'DID-BR-000002',
            'trace_mark': 'Ω₀⊂⊙∞⊂Ω'
        }
        
        # 保存快照
        snapshot_file = os.path.join(SNAPSHOT_DIR, f'{audit_id}.json')
        with open(snapshot_file, 'w') as f:
            json.dump(snapshot, f, ensure_ascii=False, indent=2)
        
        # 追加审计日志
        self._append_log(snapshot)
        
        return audit_id
    
    def record_execution(self, audit_id: str, success: bool, 
                         result: Dict = None, duration_seconds: float = 0,
                         error: str = None):
        """记录执行结果"""
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # 更新快照
        snapshot_file = os.path.join(SNAPSHOT_DIR, f'{audit_id}.json')
        if os.path.exists(snapshot_file):
            with open(snapshot_file) as f:
                snapshot = json.load(f)
            snapshot['status'] = 'SUCCESS' if success else 'FAILED'
            snapshot['result'] = result or {}
            snapshot['duration_seconds'] = duration_seconds
            snapshot['error'] = error
            snapshot['completed_at'] = timestamp
            with open(snapshot_file, 'w') as f:
                json.dump(snapshot, f, ensure_ascii=False, indent=2)
        
        # 追加执行日志
        log_entry = {
            'audit_id': audit_id,
            'event': 'EXECUTION',
            'success': success,
            'duration_seconds': duration_seconds,
            'error': error,
            'timestamp': timestamp
        }
        self._append_log(log_entry)
    
    def record_notification(self, audit_id: str, channel: str, 
                            success: bool, message: str = None):
        """记录通知发送"""
        log_entry = {
            'audit_id': audit_id,
            'event': 'NOTIFICATION',
            'channel': channel,
            'success': success,
            'message': message,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        self._append_log(log_entry)
    
    def record_approval(self, audit_id: str, approved: bool, 
                        approver: str = None, comment: str = None):
        """记录审批结果"""
        log_entry = {
            'audit_id': audit_id,
            'event': 'APPROVAL',
            'approved': approved,
            'approver': approver,
            'comment': comment,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        self._append_log(log_entry)
    
    def record_rollback(self, audit_id: str, reason: str, 
                        success: bool = True):
        """记录回滚"""
        log_entry = {
            'audit_id': audit_id,
            'event': 'ROLLBACK',
            'reason': reason,
            'success': success,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        self._append_log(log_entry)
    
    def get_recent_decisions(self, limit: int = 20, 
                             level: str = None) -> List[Dict]:
        """获取最近的决策记录"""
        decisions = []
        if os.path.exists(self.audit_log):
            with open(self.audit_log) as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        if entry.get('event') == 'DECISION' or 'operation' in entry:
                            if level is None or entry.get('level') == level:
                                decisions.append(entry)
                    except:
                        pass
        return decisions[-limit:]
    
    def get_statistics(self) -> Dict:
        """获取审计统计"""
        stats = {
            'total_decisions': 0,
            'by_level': {'L0': 0, 'L1': 0, 'L2': 0, 'L3': 0, 'L4': 0},
            'success_rate': 0,
            'total_executions': 0,
            'successful_executions': 0,
        }
        
        if os.path.exists(self.audit_log):
            with open(self.audit_log) as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        if 'operation' in entry and 'status' in entry:
                            stats['total_decisions'] += 1
                            level = entry.get('level', 'L0')
                            if level in stats['by_level']:
                                stats['by_level'][level] += 1
                        if entry.get('event') == 'EXECUTION':
                            stats['total_executions'] += 1
                            if entry.get('success'):
                                stats['successful_executions'] += 1
                    except:
                        pass
        
        if stats['total_executions'] > 0:
            stats['success_rate'] = round(
                stats['successful_executions'] / stats['total_executions'] * 100, 1)
        
        return stats
    
    def post_review(self, audit_id: str) -> Dict:
        """事后复盘（L2以上决策24h后自动触发）"""
        snapshot_file = os.path.join(SNAPSHOT_DIR, f'{audit_id}.json')
        if not os.path.exists(snapshot_file):
            return {'error': 'snapshot not found'}
        
        with open(snapshot_file) as f:
            snapshot = json.load(f)
        
        review = {
            'audit_id': audit_id,
            'operation': snapshot.get('operation'),
            'level': snapshot.get('level'),
            'risk_score': snapshot.get('risk_score'),
            'actual_success': snapshot.get('status') == 'SUCCESS',
            'duration_seconds': snapshot.get('duration_seconds', 0),
            'review_time': datetime.now(timezone.utc).isoformat(),
            'lessons_learned': [],
            'recommendation': ''
        }
        
        # 生成复盘建议
        if not review['actual_success']:
            review['lessons_learned'].append('执行失败，需检查失败原因并优化')
            review['recommendation'] = '建议降级该类操作的自治等级或增加预检'
        elif review['duration_seconds'] > 300:
            review['lessons_learned'].append('执行耗时过长，需优化执行效率')
            review['recommendation'] = '建议优化执行流程或增加超时处理'
        else:
            review['lessons_learned'].append('执行成功，可维持当前自治等级')
            review['recommendation'] = '该类操作可继续自动执行'
        
        # 保存复盘
        review_file = os.path.join(SNAPSHOT_DIR, f'{audit_id}_review.json')
        with open(review_file, 'w') as f:
            json.dump(review, f, ensure_ascii=False, indent=2)
        
        return review
    
    def _append_log(self, entry: Dict):
        """追加审计日志"""
        with open(self.audit_log, 'a') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')


def main():
    """测试"""
    auditor = DecisionAuditor()
    
    print("=" * 60)
    print("决策审计模块测试")
    print("=" * 60)
    
    # 创建快照
    audit_id = auditor.create_snapshot(
        operation='测试操作',
        level='L0',
        risk_score=15.0,
        params={'test': True}
    )
    print(f"创建快照: {audit_id}")
    
    # 记录执行
    auditor.record_execution(
        audit_id=audit_id,
        success=True,
        result={'test': 'passed'},
        duration_seconds=1.5
    )
    print("记录执行: 成功")
    
    # 记录通知
    auditor.record_notification(
        audit_id=audit_id,
        channel='feishu',
        success=True,
        message='测试通知'
    )
    print("记录通知: 成功")
    
    # 统计
    stats = auditor.get_statistics()
    print(f"\n统计: {json.dumps(stats, ensure_ascii=False, indent=2)}")
    
    # 复盘
    review = auditor.post_review(audit_id)
    print(f"\n复盘: {json.dumps(review, ensure_ascii=False, indent=2)}")
    
    print("\n" + "=" * 60)
    print("决策审计模块测试完成")
    print("=" * 60)


if __name__ == '__main__':
    main()
