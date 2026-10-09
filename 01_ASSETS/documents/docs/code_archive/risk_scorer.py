#!/usr/bin/env python3
"""
风险评估引擎 - ZONGYUAN-ROOT Autonomy Governor
五维风险评分：可逆性30% + 影响范围25% + 失败概率20% + 安全合规15% + 成本10%
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
"""
import json
import os
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone

CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'config', 'autonomy_config.json')

@dataclass
class RiskAssessment:
    """风险评估结果"""
    operation: str
    reversibility: float        # 可逆性 0-100 (越高越可逆，风险越低)
    impact_scope: float         # 影响范围 0-100 (越高影响越大)
    failure_probability: float  # 失败概率 0-100
    security_compliance: float  # 安全合规风险 0-100
    cost_impact: float          # 成本影响 0-100
    total_risk: float           # 综合风险 0-100
    risk_level: str             # L0-L4
    recommendation: str         # 执行建议
    factors: Dict[str, str]     # 关键风险因素
    timestamp: str

    def to_dict(self):
        return asdict(self)


class RiskEngine:
    """风险评估引擎"""
    
    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = CONFIG_PATH
        with open(config_path) as f:
            self.config = json.load(f)
        self.weights = self.config['risk_weights']
        self.levels = self.config['autonomy_levels']
    
    def assess(self, operation: str, 
               reversibility: float = None,
               impact_scope: float = None,
               failure_probability: float = None,
               security_compliance: float = None,
               cost_impact: float = None,
               context: Dict = None) -> RiskAssessment:
        """
        执行五维风险评估
        未提供的维度根据operation类型和context自动推断
        """
        # 自动推断未提供的维度
        if reversibility is None:
            reversibility = self._infer_reversibility(operation, context)
        if impact_scope is None:
            impact_scope = self._infer_impact(operation, context)
        if failure_probability is None:
            failure_probability = self._infer_failure(operation, context)
        if security_compliance is None:
            security_compliance = self._infer_compliance(operation, context)
        if cost_impact is None:
            cost_impact = self._infer_cost(operation, context)
        
        # 计算综合风险 (注意：reversibility越高风险越低，所以取反)
        total_risk = (
            (100 - reversibility) * self.weights['reversibility'] +
            impact_scope * self.weights['impact_scope'] +
            failure_probability * self.weights['failure_probability'] +
            security_compliance * self.weights['security_compliance'] +
            cost_impact * self.weights['cost_impact']
        )
        total_risk = round(total_risk, 1)
        
        # 确定风险等级
        risk_level = self._classify_level(total_risk)
        
        # 生成建议
        recommendation = self._generate_recommendation(risk_level, total_risk)
        
        # 关键因素
        factors = self._identify_factors(reversibility, impact_scope, 
                                         failure_probability, security_compliance, cost_impact)
        
        return RiskAssessment(
            operation=operation,
            reversibility=round(reversibility, 1),
            impact_scope=round(impact_scope, 1),
            failure_probability=round(failure_probability, 1),
            security_compliance=round(security_compliance, 1),
            cost_impact=round(cost_impact, 1),
            total_risk=total_risk,
            risk_level=risk_level,
            recommendation=recommendation,
            factors=factors,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
    
    def _classify_level(self, risk: float) -> str:
        """根据风险分数确定自治等级"""
        for level_key in ['L0', 'L1', 'L2', 'L3', 'L4']:
            lv = self.levels[level_key]
            if lv['risk_min'] <= risk < lv['risk_max']:
                return level_key
        return 'L4'  # >=85
    
    def _generate_recommendation(self, level: str, risk: float) -> str:
        """生成执行建议"""
        lv = self.levels[level]
        recommendations = {
            'L0': f"风险{risk}%，可全自动执行。{lv['description']}",
            'L1': f"风险{risk}%，自动执行并通知内核群。{lv['description']}",
            'L2': f"风险{risk}%，需人工预审，24h超时自动执行。{lv['description']}",
            'L3': f"风险{risk}%，必须飞书审批通过。{lv['description']}",
            'L4': f"风险{risk}%，只能人工执行，AI提供方案。{lv['description']}",
        }
        return recommendations.get(level, "需人工评估")
    
    def _identify_factors(self, rev, imp, fail, comp, cost) -> Dict[str, str]:
        """识别关键风险因素"""
        factors = {}
        if rev < 50:
            factors['reversibility'] = f"低可逆性({rev}%)，回滚困难"
        if imp > 60:
            factors['impact'] = f"高影响范围({imp}%)，影响面广"
        if fail > 50:
            factors['failure'] = f"高失败概率({fail}%)，技术不成熟"
        if comp > 60:
            factors['compliance'] = f"高合规风险({comp}%)，涉及安全/合规"
        if cost > 50:
            factors['cost'] = f"高成本影响({cost}%)，产生额外支出"
        if not factors:
            factors['overall'] = "各维度风险均可控"
        return factors
    
    def _infer_reversibility(self, operation: str, context: Dict = None) -> float:
        """推断可逆性"""
        op_lower = operation.lower()
        # 高可逆操作
        high_rev = ['查询', '扫描', '巡检', '监控', '上报', '日志', '缓存', '清理', '读取', 'status', 'scan', 'report', 'log', 'cache']
        # 中可逆操作
        mid_rev = ['更新', '调整', '重启', '调度', '配置', '部署', 'update', 'restart', 'deploy', 'config']
        # 低可逆操作
        low_rev = ['删除', '重置', '迁移', '密钥', '内核', '删除数据', 'delete', 'reset', 'migrate', 'kernel', 'key']
        
        for kw in high_rev:
            if kw in op_lower:
                return 85.0
        for kw in low_rev:
            if kw in op_lower:
                return 20.0
        for kw in mid_rev:
            if kw in op_lower:
                return 60.0
        return 50.0
    
    def _infer_impact(self, operation: str, context: Dict = None) -> float:
        """推断影响范围"""
        op_lower = operation.lower()
        high_impact = ['内核', '全局', '全域', '元法则', '安全', '架构', 'kernel', 'global', 'meta_law', 'security']
        mid_impact = ['服务', '产线', '部署', '配置', '算子', 'service', 'pipeline', 'deploy', 'operator']
        low_impact = ['日志', '缓存', '查询', '扫描', '上报', 'log', 'cache', 'query', 'scan', 'report']
        
        for kw in high_impact:
            if kw in op_lower:
                return 75.0
        for kw in low_impact:
            if kw in op_lower:
                return 20.0
        for kw in mid_impact:
            if kw in op_lower:
                return 50.0
        return 40.0
    
    def _infer_failure(self, operation: str, context: Dict = None) -> float:
        """推断失败概率"""
        op_lower = operation.lower()
        high_fail = ['新功能', '首次', '实验', '迁移', '重构', 'new', 'first', 'experiment', 'migrate', 'refactor']
        mid_fail = ['部署', '更新', '调整', 'deploy', 'update', 'adjust']
        low_fail = ['查询', '扫描', '巡检', '上报', '日志', 'query', 'scan', 'inspect', 'report', 'log']
        
        for kw in high_fail:
            if kw in op_lower:
                return 60.0
        for kw in low_fail:
            if kw in op_lower:
                return 10.0
        for kw in mid_fail:
            if kw in op_lower:
                return 35.0
        return 30.0
    
    def _infer_compliance(self, operation: str, context: Dict = None) -> float:
        """推断安全合规风险"""
        op_lower = operation.lower()
        high_comp = ['安全', '密钥', '权限', '合规', '数据删除', '隐私', 'security', 'key', 'permission', 'compliance', 'privacy']
        mid_comp = ['部署', '配置', '更新', 'deploy', 'config', 'update']
        low_comp = ['查询', '扫描', '巡检', '上报', '日志', 'query', 'scan', 'report', 'log']
        
        for kw in high_comp:
            if kw in op_lower:
                return 70.0
        for kw in low_comp:
            if kw in op_lower:
                return 10.0
        for kw in mid_comp:
            if kw in op_lower:
                return 30.0
        return 25.0
    
    def _infer_cost(self, operation: str, context: Dict = None) -> float:
        """推断成本影响"""
        op_lower = operation.lower()
        high_cost = ['部署', '生成', '算力', '视频', '图片', 'API调用', 'deploy', 'generate', 'compute', 'video', 'image', 'api']
        mid_cost = ['更新', '调整', '服务', 'update', 'adjust', 'service']
        low_cost = ['查询', '扫描', '巡检', '上报', '日志', '清理', 'query', 'scan', 'report', 'log', 'clean']
        
        for kw in high_cost:
            if kw in op_lower:
                return 55.0
        for kw in low_cost:
            if kw in op_lower:
                return 5.0
        for kw in mid_cost:
            if kw in op_lower:
                return 25.0
        return 20.0
    
    def batch_assess(self, operations: List[str]) -> List[RiskAssessment]:
        """批量评估多个操作"""
        return [self.assess(op) for op in operations]


def main():
    """命令行测试"""
    engine = RiskEngine()
    
    print("=" * 60)
    print("风险评估引擎测试")
    print("=" * 60)
    
    test_ops = [
        "日志清理",
        "缓存释放",
        "真值上报到记忆网关",
        "资产扫描",
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
    
    print(f"\n{'操作':<20} {'风险':<8} {'等级':<6} {'可逆':<6} {'影响':<6} {'失败':<6} {'合规':<6} {'成本':<6}")
    print("-" * 80)
    
    for op in test_ops:
        result = engine.assess(op)
        print(f"{op:<20} {result.total_risk:<8} {result.risk_level:<6} "
              f"{result.reversibility:<6} {result.impact_scope:<6} "
              f"{result.failure_probability:<6} {result.security_compliance:<6} "
              f"{result.cost_impact:<6}")
    
    print("\n" + "=" * 60)
    print("风险评分公式: (100-可逆)*30% + 影响*25% + 失败*20% + 合规*15% + 成本*10%")
    print("等级阈值: L0<30% | L1 30-50% | L2 50-70% | L3 70-85% | L4>85%")
    print("=" * 60)


if __name__ == '__main__':
    main()
