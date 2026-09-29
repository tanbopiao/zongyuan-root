#!/usr/bin/env python3
"""
五级自治分级器 - ZONGYUAN-ROOT Autonomy Governor
L0全自动 → L1自动+通知 → L2自动+预审 → L3人工审批 → L4人工执行
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
"""
import json
import os
import sys
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from risk_engine.risk_scorer import RiskEngine, RiskAssessment

CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'config', 'autonomy_config.json')


class LevelClassifier:
    """五级自治分级器"""
    
    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = CONFIG_PATH
        with open(config_path) as f:
            self.config = json.load(f)
        self.levels = self.config['autonomy_levels']
        self.risk_engine = RiskEngine(config_path)
        
        # 操作类型到等级的硬映射（高风险操作强制升级）
        self.force_level_map = {
            '内核重置': 'L4',
            '安全密钥变更': 'L4',
            '密钥变更': 'L4',
            '域名迁移': 'L4',
            '数据删除': 'L4',
            '删除数据': 'L4',
            '合规重大变更': 'L4',
            '重大架构变更': 'L3',
            '高风险部署': 'L3',
            '安全策略调整': 'L3',
            '大额成本支出': 'L3',
        }
    
    def classify(self, operation: str, 
                 explicit_risk: float = None,
                 context: Dict = None) -> Tuple[str, RiskAssessment]:
        """
        对操作进行自治分级
        返回: (level, risk_assessment)
        """
        # 1. 先检查硬映射（高风险操作强制升级）
        forced = self._check_force_level(operation)
        if forced:
            # 仍然执行风险评估，但等级用强制的
            assessment = self.risk_engine.assess(operation, context=context)
            assessment.risk_level = forced
            assessment.recommendation = f"【强制{forced}】{self.levels[forced]['description']}"
            return forced, assessment
        
        # 2. 风险评估
        if explicit_risk is not None:
            # 使用显式风险分数
            assessment = self.risk_engine.assess(operation, context=context)
            assessment.total_risk = explicit_risk
            assessment.risk_level = self.risk_engine._classify_level(explicit_risk)
            assessment.recommendation = self.risk_engine._generate_recommendation(
                assessment.risk_level, explicit_risk)
        else:
            assessment = self.risk_engine.assess(operation, context=context)
        
        return assessment.risk_level, assessment
    
    def _check_force_level(self, operation: str) -> Optional[str]:
        """检查是否有强制等级映射"""
        op_lower = operation.lower()
        for keyword, level in self.force_level_map.items():
            if keyword.lower() in op_lower:
                return level
        return None
    
    def get_execution_strategy(self, level: str) -> Dict:
        """获取指定等级的执行策略"""
        if level not in self.levels:
            return self.levels['L4']
        return self.levels[level]
    
    def can_auto_execute(self, level: str) -> bool:
        """判断是否可以自动执行"""
        strategy = self.get_execution_strategy(level)
        return strategy['execution'] in ['auto', 'precheck_then_auto']
    
    def needs_approval(self, level: str) -> bool:
        """判断是否需要审批"""
        strategy = self.get_execution_strategy(level)
        return strategy['execution'] in ['approval_required', 'manual_only']
    
    def batch_classify(self, operations: List[str]) -> List[Tuple[str, RiskAssessment]]:
        """批量分级"""
        return [self.classify(op) for op in operations]
    
    def get_level_summary(self) -> str:
        """获取分级体系摘要"""
        lines = ["五级自治分级体系："]
        for key in ['L0', 'L1', 'L2', 'L3', 'L4']:
            lv = self.levels[key]
            lines.append(f"  {key} {lv['name']}: 风险{lv['risk_min']}-{lv['risk_max']}% | {lv['description']}")
            lines.append(f"       典型: {', '.join(lv['examples'][:4])}")
        return '\n'.join(lines)


def main():
    """命令行测试"""
    classifier = LevelClassifier()
    
    print("=" * 70)
    print("五级自治分级器测试")
    print("=" * 70)
    print(classifier.get_level_summary())
    
    test_ops = [
        "日志清理",
        "缓存释放",
        "真值上报",
        "资产扫描",
        "常规巡检",
        "服务重启",
        "产线调度",
        "参数微调",
        "低风险部署",
        "元法则更新",
        "算子阈值调整",
        "新功能上线",
        "重大架构变更",
        "高风险部署",
        "安全策略调整",
        "内核重置",
        "安全密钥变更",
        "数据删除",
    ]
    
    print(f"\n{'操作':<16} {'风险':<8} {'等级':<6} {'自动?':<6} {'需审批?':<8} 建议")
    print("-" * 90)
    
    for op in test_ops:
        level, assessment = classifier.classify(op)
        auto = "✅" if classifier.can_auto_execute(level) else "❌"
        approval = "✅" if classifier.needs_approval(level) else "❌"
        print(f"{op:<16} {assessment.total_risk:<8} {level:<6} {auto:<6} {approval:<8} "
              f"{assessment.recommendation[:40]}")
    
    print("\n" + "=" * 70)
    print("分级完成。L0/L1可自动执行，L2需预审，L3需审批，L4只能人工。")
    print("=" * 70)


if __name__ == '__main__':
    main()
