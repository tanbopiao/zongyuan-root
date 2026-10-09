#!/usr/bin/env python3
"""
ZONGYUAN-ROOT Autonomy Governor - 自治分级引擎主入口
五级自治分级：L0全自动 → L1自动+通知 → L2自动+预审 → L3人工审批 → L4人工执行
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | 火斗云智AIOS
"""
import json
import os
import sys
import argparse
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone

# 添加模块路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from risk_engine.risk_scorer import RiskEngine, RiskAssessment
from level_classifier.classifier import LevelClassifier
from executor.l0_auto import L0AutoExecutor
from executor.l1_notify import L1NotifyExecutor
from audit.decision_audit import DecisionAuditor

CONFIG_PATH = os.path.join(BASE_DIR, 'config', 'autonomy_config.json')


class AutonomyGovernor:
    """自治分级引擎主控"""
    
    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = CONFIG_PATH
        with open(config_path) as f:
            self.config = json.load(f)
        
        self.risk_engine = RiskEngine(config_path)
        self.classifier = LevelClassifier(config_path)
        self.l0_executor = L0AutoExecutor(config_path)
        self.l1_executor = L1NotifyExecutor(config_path)
        self.auditor = DecisionAuditor()
    
    def process(self, operation: str, params: Dict = None,
                explicit_risk: float = None, dry_run: bool = False) -> Dict:
        """
        处理一个操作：评估风险 → 分级 → 执行
        """
        if params is None:
            params = {}
        
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # 1. 风险评估 + 分级
        level, assessment = self.classifier.classify(
            operation, explicit_risk=explicit_risk, context=params)
        
        result = {
            'operation': operation,
            'params': params,
            'risk_assessment': assessment.to_dict(),
            'autonomy_level': level,
            'level_name': self.config['autonomy_levels'][level]['name'],
            'can_auto_execute': self.classifier.can_auto_execute(level),
            'needs_approval': self.classifier.needs_approval(level),
            'timestamp': timestamp,
            'did': 'DID-BR-000002',
            'trace_mark': 'Ω₀⊂⊙∞⊂Ω'
        }
        
        # 2. 根据等级执行
        if dry_run:
            result['execution'] = {'status': 'DRY_RUN', 'message': '仅评估不执行'}
            return result
        
        if level == 'L0':
            exec_result = self.l0_executor.execute(operation, {**params, 'risk_score': assessment.total_risk})
            result['execution'] = exec_result
        elif level == 'L1':
            exec_result = self.l1_executor.execute(operation, {**params, 'risk_score': assessment.total_risk})
            result['execution'] = exec_result
        elif level == 'L2':
            result['execution'] = {
                'status': 'PENDING_PRECHECK',
                'message': 'L2级操作需人工预审，24h超时自动执行。已生成预审方案。',
                'precheck_deadline': '24h',
                'action_required': '人工确认或等待超时自动执行'
            }
        elif level == 'L3':
            result['execution'] = {
                'status': 'APPROVAL_REQUIRED',
                'message': 'L3级操作必须飞书审批通过后才能执行。',
                'approval_code': self.config['feishu']['approval_code'],
                'action_required': '发起飞书审批'
            }
        elif level == 'L4':
            result['execution'] = {
                'status': 'MANUAL_ONLY',
                'message': 'L4级操作只能人工执行，AI仅提供方案建议和检查清单。',
                'action_required': '人工执行'
            }
        
        return result
    
    def batch_process(self, operations: List[str], dry_run: bool = False) -> List[Dict]:
        """批量处理"""
        return [self.process(op, dry_run=dry_run) for op in operations]
    
    def get_status(self) -> Dict:
        """获取引擎状态"""
        stats = self.auditor.get_statistics()
        return {
            'engine': 'ZONGYUAN-ROOT Autonomy Governor',
            'version': self.config['version'],
            'did': self.config['did'],
            'levels': {k: v['name'] for k, v in self.config['autonomy_levels'].items()},
            'audit_stats': stats,
            'gateway': self.config['gateway']['report_url'],
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    def get_level_summary(self) -> str:
        """获取分级摘要"""
        return self.classifier.get_level_summary()


def main():
    parser = argparse.ArgumentParser(description='ZONGYUAN-ROOT Autonomy Governor')
    parser.add_argument('operation', nargs='?', help='要执行的操作')
    parser.add_argument('--risk', type=float, help='显式风险分数(0-100)')
    parser.add_argument('--dry-run', action='store_true', help='仅评估不执行')
    parser.add_argument('--status', action='store_true', help='查看引擎状态')
    parser.add_argument('--levels', action='store_true', help='查看分级体系')
    parser.add_argument('--test', action='store_true', help='运行测试')
    
    args = parser.parse_args()
    
    governor = AutonomyGovernor()
    
    if args.status:
        print(json.dumps(governor.get_status(), ensure_ascii=False, indent=2))
        return
    
    if args.levels:
        print(governor.get_level_summary())
        return
    
    if args.test:
        print("=" * 70)
        print("ZONGYUAN-ROOT Autonomy Governor 集成测试")
        print("=" * 70)
        
        test_ops = [
            "日志清理",
            "缓存释放",
            "真值上报",
            "资产扫描",
            "常规巡检",
            "服务重启",
            "产线调度",
            "参数微调",
            "元法则更新",
            "新功能上线",
            "重大架构变更",
            "安全策略调整",
            "内核重置",
            "安全密钥变更",
            "数据删除",
        ]
        
        print(f"\n{'操作':<14} {'风险':<7} {'等级':<5} {'自动?':<6} {'审批?':<6} 执行状态")
        print("-" * 80)
        
        for op in test_ops:
            result = governor.process(op, dry_run=True)
            auto = "✅" if result['can_auto_execute'] else "❌"
            approval = "✅" if result['needs_approval'] else "❌"
            exec_status = result['execution']['status']
            print(f"{op:<14} {result['risk_assessment']['total_risk']:<7} "
                  f"{result['autonomy_level']:<5} {auto:<6} {approval:<6} {exec_status}")
        
        print("\n" + "=" * 70)
        print("实际执行测试（L0操作）:")
        print("-" * 80)
        
        for op in ["状态查询", "常规巡检"]:
            result = governor.process(op)
            print(f"  {op}: 成功={result['execution']['success']}, "
                  f"耗时={result['execution']['duration_seconds']}s, "
                  f"审计ID={result['execution']['audit_id']}")
        
        print("\n" + "=" * 70)
        print("引擎状态:")
        print(json.dumps(governor.get_status(), ensure_ascii=False, indent=2))
        print("=" * 70)
        return
    
    if args.operation:
        result = governor.process(
            args.operation,
            explicit_risk=args.risk,
            dry_run=args.dry_run
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    
    parser.print_help()


if __name__ == '__main__':
    main()
