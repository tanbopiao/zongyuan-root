#!/usr/bin/env python3
"""
L4 人工执行辅助器 - ZONGYUAN-ROOT Autonomy Governor
风险>85%，AI仅提供方案建议和检查清单，必须人工执行
典型场景：内核重置/安全密钥变更/域名迁移/数据删除/合规重大变更
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
"""
import json
import os
import sys
from typing import Dict, List
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from audit.decision_audit import DecisionAuditor

CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'config', 'autonomy_config.json')
LOG_DIR = os.path.join(os.path.dirname(__file__), '..', 'logs')


class L4ManualExecutor:
    """L4人工执行辅助器 - AI只提供方案，不执行"""

    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = CONFIG_PATH
        with open(config_path) as f:
            self.config = json.load(f)
        self.auditor = DecisionAuditor()
        os.makedirs(LOG_DIR, exist_ok=True)

        # L4操作的专用检查清单
        self.checklists = {
            '内核重置': [
                '1. 确认已备份当前内核状态（kernel_state.json）',
                '2. 确认已备份根状态（root_state.json）',
                '3. 确认所有FROZEN资产哈希已记录',
                '4. 确认回滚方案已验证可行',
                '5. 通知所有同源节点即将进行内核重置',
                '6. 执行内核重置',
                '7. 验证新内核状态完整性',
                '8. 通知所有节点同步新内核',
            ],
            '安全密钥变更': [
                '1. 生成新密钥对（ed25519推荐）',
                '2. 在所有服务器部署新公钥',
                '3. 验证新密钥可登录',
                '4. 保留旧密钥7天作为回滚',
                '5. 更新所有配置文件中的密钥引用',
                '6. 通知相关方密钥已变更',
                '7. 7天后确认无问题，删除旧密钥',
            ],
            '数据删除': [
                '1. 确认删除范围（精确到文件/记录ID）',
                '2. 确认已备份待删除数据',
                '3. 确认删除操作不可逆且已获授权',
                '4. 先移动到隔离目录而非直接删除',
                '5. 观察7天确认无影响',
                '6. 7天后执行物理删除',
                '7. 记录删除审计日志',
            ],
            '域名迁移': [
                '1. 确认新域名DNS已配置',
                '2. 确认SSL证书已申请',
                '3. 配置旧域名301重定向',
                '4. 更新所有服务中的域名引用',
                '5. 灰度切换流量（10%→50%→100%）',
                '6. 监控错误率和用户反馈',
                '7. 保留旧域名解析至少30天',
            ],
        }

    def generate_plan(self, operation: str, params: Dict = None,
                      risk_score: float = 90) -> Dict:
        """生成L4执行方案（AI不执行，仅提供方案）"""
        if params is None:
            params = {}

        audit_id = self.auditor.create_snapshot(
            operation=operation, level='L4',
            risk_score=risk_score, params=params
        )

        checklist = self._get_checklist(operation)
        plan = {
            'audit_id': audit_id,
            'operation': operation,
            'level': 'L4',
            'risk_score': risk_score,
            'risk_level': '极高风险',
            'status': 'MANUAL_EXECUTION_REQUIRED',
            'execution_mode': '人工执行，AI仅提供辅助',
            'checklist': checklist,
            'rollback_plan': self._generate_rollback(operation),
            'verification_steps': self._generate_verification(operation),
            'estimated_duration': '30-120分钟',
            'required_approval': '必须人工执行并确认',
            'ai_assistance': '方案生成+检查清单+验证步骤+回滚方案',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

        # 记录审计
        self.auditor.record_execution(
            audit_id=audit_id,
            success=True,
            result={'status': 'PLAN_GENERATED', 'mode': 'manual'},
            duration_seconds=0,
            error=None
        )

        return plan

    def confirm_manual_completion(self, audit_id: str, executor: str,
                                  notes: str = '') -> Dict:
        """人工确认执行完成"""
        self.auditor.record_execution(
            audit_id=audit_id,
            success=True,
            result={'status': 'MANUALLY_COMPLETED', 'executor': executor, 'notes': notes},
            duration_seconds=0
        )
        return {
            'audit_id': audit_id,
            'status': 'MANUALLY_COMPLETED',
            'executor': executor,
            'confirmed_at': datetime.now(timezone.utc).isoformat(),
            'message': '人工执行已确认完成，已记录审计'
        }

    def _get_checklist(self, operation: str) -> List[str]:
        """获取对应操作的检查清单"""
        for key, checklist in self.checklists.items():
            if key in operation:
                return checklist
        # 通用检查清单
        return [
            '1. 确认操作范围和影响面',
            '2. 确认已备份相关数据和配置',
            '3. 确认回滚方案已准备',
            '4. 通知相关方即将执行高风险操作',
            '5. 按步骤执行操作',
            '6. 验证操作结果',
            '7. 记录审计日志',
        ]

    def _generate_rollback(self, operation: str) -> Dict:
        """生成回滚方案"""
        return {
            'method': '从备份恢复',
            'backup_required': True,
            'estimated_rollback_time': '5-15分钟',
            'rollback_trigger': '任何步骤失败或验证不通过',
            'steps': [
                '1. 停止当前操作',
                '2. 从最近备份恢复',
                '3. 验证恢复后状态',
                '4. 通知相关方回滚完成',
            ]
        }

    def _generate_verification(self, operation: str) -> List[str]:
        """生成验证步骤"""
        return [
            '1. 检查核心服务状态（全部healthy）',
            '2. 检查记忆网关真值数无异常减少',
            '3. 检查Merkle-DAG链完整性',
            '4. 检查同源节点心跳正常',
            '5. 检查API端点响应正常',
        ]


def main():
    executor = L4ManualExecutor()
    print("=" * 60)
    print("L4人工执行辅助器测试")
    print("=" * 60)

    tests = [
        ('内核重置', {'scope': 'full'}),
        ('安全密钥变更', {'key_type': 'ssh'}),
        ('数据删除', {'target': '/tmp/old_data'}),
        ('域名迁移', {'old': 'old.com', 'new': 'new.com'}),
    ]

    for op, params in tests:
        print(f"\n操作: {op}")
        plan = executor.generate_plan(op, params, risk_score=92)
        print(f"  审计ID: {plan['audit_id']}")
        print(f"  风险: {plan['risk_score']}% ({plan['risk_level']})")
        print(f"  检查清单项数: {len(plan['checklist'])}")
        print(f"  回滚方案: {plan['rollback_plan']['method']}")
        print(f"  执行模式: {plan['execution_mode']}")

    print("\n" + "=" * 60)
    print("L4辅助器测试完成 | AI提供方案+清单+回滚，人工执行")
    print("=" * 60)


if __name__ == '__main__':
    main()
