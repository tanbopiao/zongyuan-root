"""
引擎二：自治决策引擎
三维稳态评估 + 风险分级 + 知识库检索 + 自动选最优
"""
import os
import sys
import json
import time
import logging
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engines.detection_engine import AnomalyEvent, Severity
from circuit_breaker.circuit_breaker import get_circuit_breaker

logger = logging.getLogger(__name__)

class RiskLevel(Enum):
    """风险级别"""
    L0_READONLY = "L0"      # 只读，无风险
    L1_SAFE = "L1"          # 安全，只删缓存
    L2_REVERSIBLE = "L2"    # 可逆，有备份
    L3_SENSITIVE = "L3"     # 敏感，多重校验
    L4_DANGEROUS = "L4"     # 危险，必须人工

class DecisionAction(Enum):
    """决策动作"""
    AUTO_EXECUTE = "auto_execute"
    SCHEDULE = "schedule"
    WAIT_FOR_HUMAN = "wait_for_human"
    SKIP = "skip"
    NOTIFY_ONLY = "notify_only"

@dataclass
class OptimizationCandidate:
    """优化候选方案"""
    candidate_id: str
    name: str
    description: str
    operation_type: str
    command: str
    risk_level: RiskLevel
    estimated_benefit: float  # 0-1
    estimated_risk: float     # 0-1
    estimated_cost: float     # 0-1
    targets: List[str] = field(default_factory=list)
    parameters: Dict = field(default_factory=dict)
    timeout: int = 300
    stabilization_time: int = 60
    score: float = 0.0
    source: str = "rule_based"  # rule_based/knowledge_base/historical

@dataclass
class Decision:
    """决策结果"""
    decision_id: str
    action: DecisionAction
    anomaly: Optional[AnomalyEvent] = None
    candidate: Optional[OptimizationCandidate] = None
    score: float = 0.0
    reason: str = ""
    auto_backup: bool = False
    auto_rollback: bool = True
    candidates_evaluated: int = 0
    timestamp: str = ""
    confidence: float = 0.0

class KnowledgeBase:
    """优化知识库 - 存储历史成功的优化方案"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "config", "optimization_knowledge.json"
        )
        self.knowledge = self._load()
    
    def _load(self) -> Dict:
        """加载知识库"""
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {
            "patterns": {},
            "successful_optimizations": [],
            "failed_optimizations": [],
            "risk_adjustments": {}
        }
    
    def save(self):
        """保存知识库"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with open(self.db_path, 'w', encoding='utf-8') as f:
            json.dump(self.knowledge, f, ensure_ascii=False, indent=2)
    
    def search(self, anomaly: AnomalyEvent) -> List[OptimizationCandidate]:
        """根据异常搜索历史成功方案"""
        candidates = []
        metric = anomaly.metric
        
        # 搜索匹配的模式
        if metric in self.knowledge.get('patterns', {}):
            pattern = self.knowledge['patterns'][metric]
            for opt in pattern.get('successful_optimizations', []):
                candidate = OptimizationCandidate(
                    candidate_id=f"kb_{opt.get('id', int(time.time()))}",
                    name=opt.get('name', '知识库方案'),
                    description=opt.get('description', ''),
                    operation_type=opt.get('operation_type', 'generic'),
                    command=opt.get('command', ''),
                    risk_level=RiskLevel(opt.get('risk_level', 'L2')),
                    estimated_benefit=opt.get('benefit', 0.5),
                    estimated_risk=opt.get('risk', 0.2),
                    estimated_cost=opt.get('cost', 0.3),
                    targets=opt.get('targets', []),
                    source="knowledge_base"
                )
                candidates.append(candidate)
        
        return candidates
    
    def record_success(self, anomaly: AnomalyEvent, candidate: OptimizationCandidate, improvement: float):
        """记录成功优化"""
        metric = anomaly.metric
        if metric not in self.knowledge['patterns']:
            self.knowledge['patterns'][metric] = {'successful_optimizations': [], 'failed_optimizations': []}
        
        self.knowledge['patterns'][metric]['successful_optimizations'].append({
            'id': candidate.candidate_id,
            'name': candidate.name,
            'command': candidate.command,
            'operation_type': candidate.operation_type,
            'risk_level': candidate.risk_level.value,
            'benefit': candidate.estimated_benefit,
            'risk': candidate.estimated_risk,
            'cost': candidate.estimated_cost,
            'actual_improvement': improvement,
            'timestamp': datetime.now().isoformat()
        })
        
        # 调整风险评级（成功则降低风险评估）
        key = f"{candidate.operation_type}_{candidate.name}"
        if key not in self.knowledge['risk_adjustments']:
            self.knowledge['risk_adjustments'][key] = {'success': 0, 'failure': 0}
        self.knowledge['risk_adjustments'][key]['success'] += 1
        
        self.save()
    
    def record_failure(self, anomaly: AnomalyEvent, candidate: OptimizationCandidate, reason: str):
        """记录失败优化"""
        metric = anomaly.metric
        if metric not in self.knowledge['patterns']:
            self.knowledge['patterns'][metric] = {'successful_optimizations': [], 'failed_optimizations': []}
        
        self.knowledge['patterns'][metric]['failed_optimizations'].append({
            'id': candidate.candidate_id,
            'name': candidate.name,
            'reason': reason,
            'timestamp': datetime.now().isoformat()
        })
        
        # 调整风险评级（失败则提高风险评估）
        key = f"{candidate.operation_type}_{candidate.name}"
        if key not in self.knowledge['risk_adjustments']:
            self.knowledge['risk_adjustments'][key] = {'success': 0, 'failure': 0}
        self.knowledge['risk_adjustments'][key]['failure'] += 1
        
        self.save()
    
    def get_risk_adjustment(self, operation_type: str, name: str) -> float:
        """获取风险调整系数（基于历史成功率）"""
        key = f"{operation_type}_{name}"
        if key in self.knowledge['risk_adjustments']:
            adj = self.knowledge['risk_adjustments'][key]
            total = adj['success'] + adj['failure']
            if total > 0:
                success_rate = adj['success'] / total
                # 成功率高则降低风险，成功率低则提高风险
                return 1.0 - (success_rate - 0.5) * 0.3  # 0.85-1.15
        return 1.0

class DecisionEngine:
    """自治决策引擎"""
    
    def __init__(self, config: Dict = None):
        self.config = config or self._default_config()
        self.knowledge_base = KnowledgeBase()
        self.circuit_breaker = get_circuit_breaker()
        self.decision_history = []
        self.consecutive_failures = 0
    
    def _default_config(self) -> Dict:
        return {
            "weights": {
                "benefit": 0.40,
                "risk": 0.35,
                "cost": 0.25
            },
            "thresholds": {
                "auto_execute": 0.60,
                "schedule": 0.40,
                "skip": 0.30
            },
            "max_candidates": 5,
            "use_knowledge_base": True,
            "use_historical_adjustment": True
        }
    
    def decide(self, anomaly: AnomalyEvent) -> Decision:
        """自治决策主流程"""
        decision_id = f"decision_{int(time.time())}_{anomaly.anomaly_id}"
        timestamp = datetime.now().isoformat()
        
        # 1. 熔断检查
        if not self.circuit_breaker.can_execute():
            return Decision(
                decision_id=decision_id,
                action=DecisionAction.SKIP,
                anomaly=anomaly,
                reason="熔断中，暂停自治优化",
                timestamp=timestamp
            )
        
        # 2. 生成候选方案
        candidates = self._generate_candidates(anomaly)
        
        if not candidates:
            return Decision(
                decision_id=decision_id,
                action=DecisionAction.NOTIFY_ONLY,
                anomaly=anomaly,
                reason="无可用优化方案，仅通知",
                timestamp=timestamp
            )
        
        # 3. 三维稳态评分
        for candidate in candidates:
            candidate.score = self._calculate_score(candidate)
        
        # 4. 按得分排序
        candidates.sort(key=lambda x: x.score, reverse=True)
        best = candidates[0]
        
        # 5. L4检查
        if best.risk_level == RiskLevel.L4_DANGEROUS:
            return Decision(
                decision_id=decision_id,
                action=DecisionAction.WAIT_FOR_HUMAN,
                anomaly=anomaly,
                candidate=best,
                score=best.score,
                reason="L4危险操作，需要人工确认",
                candidates_evaluated=len(candidates),
                timestamp=timestamp,
                confidence=0.9
            )
        
        # 6. 严重程度检查（FATAL级别即使L3也自动执行）
        if anomaly.severity == Severity.FATAL and best.risk_level in [RiskLevel.L2_REVERSIBLE, RiskLevel.L3_SENSITIVE]:
            return Decision(
                decision_id=decision_id,
                action=DecisionAction.AUTO_EXECUTE,
                anomaly=anomaly,
                candidate=best,
                score=best.score,
                reason=f"致命异常({anomaly.severity.value})，紧急自动执行",
                auto_backup=True,
                auto_rollback=True,
                candidates_evaluated=len(candidates),
                timestamp=timestamp,
                confidence=0.95
            )
        
        # 7. 置信度阈值判断
        if best.score >= self.config['thresholds']['auto_execute']:
            action = DecisionAction.AUTO_EXECUTE
            reason = f"评分{best.score:.2f}超过自动执行阈值{self.config['thresholds']['auto_execute']}"
        elif best.score >= self.config['thresholds']['schedule']:
            action = DecisionAction.SCHEDULE
            reason = f"评分{best.score:.2f}，建议调度执行"
        else:
            action = DecisionAction.SKIP
            reason = f"评分{best.score:.2f}过低，跳过"
        
        # 8. 生成决策
        decision = Decision(
            decision_id=decision_id,
            action=action,
            anomaly=anomaly,
            candidate=best,
            score=best.score,
            reason=reason,
            auto_backup=best.risk_level in [RiskLevel.L2_REVERSIBLE, RiskLevel.L3_SENSITIVE],
            auto_rollback=True,
            candidates_evaluated=len(candidates),
            timestamp=timestamp,
            confidence=min(best.score, 0.95)
        )
        
        # 记录决策历史
        self.decision_history.append(decision)
        if len(self.decision_history) > 1000:
            self.decision_history = self.decision_history[-1000:]
        
        return decision
    
    def _generate_candidates(self, anomaly: AnomalyEvent) -> List[OptimizationCandidate]:
        """生成候选优化方案"""
        candidates = []
        
        # 1. 基于规则生成
        rule_candidates = self._generate_rule_based_candidates(anomaly)
        candidates.extend(rule_candidates)
        
        # 2. 从知识库检索
        if self.config['use_knowledge_base']:
            kb_candidates = self.knowledge_base.search(anomaly)
            candidates.extend(kb_candidates)
        
        # 3. 去重和限制数量
        seen = set()
        unique_candidates = []
        for c in candidates:
            key = f"{c.operation_type}_{c.name}"
            if key not in seen:
                seen.add(key)
                unique_candidates.append(c)
        
        return unique_candidates[:self.config['max_candidates']]
    
    def _generate_rule_based_candidates(self, anomaly: AnomalyEvent) -> List[OptimizationCandidate]:
        """基于规则生成候选方案"""
        candidates = []
        metric = anomaly.metric
        
        # 内存相关
        if metric in ['memory_percent', 'memory_used_mb', 'top_process_memory_mb']:
            candidates.extend([
                OptimizationCandidate(
                    candidate_id=f"rule_mem_kill_{int(time.time())}",
                    name="关闭高内存闲置进程",
                    description="识别并关闭内存占用高且闲置的用户进程",
                    operation_type="process_kill",
                    command="powershell -Command \"Get-Process | Where-Object {$_.WorkingSet64 -gt 500MB -and $_.CPU -lt 10} | Select-Object Name, Id, WorkingSet64\"",
                    risk_level=RiskLevel.L1_SAFE,
                    estimated_benefit=0.6,
                    estimated_risk=0.1,
                    estimated_cost=0.2,
                    timeout=60
                ),
                OptimizationCandidate(
                    candidate_id=f"rule_mem_clean_{int(time.time())}",
                    name="清理内存缓存",
                    description="清理Standby列表和内存缓存，释放可用内存",
                    operation_type="memory_clean",
                    command="powershell -Command \"[System.GC]::Collect(); [System.GC]::WaitForPendingFinalizers()\"",
                    risk_level=RiskLevel.L0_READONLY,
                    estimated_benefit=0.4,
                    estimated_risk=0.05,
                    estimated_cost=0.1,
                    timeout=30
                ),
            ])
        
        # CPU相关
        elif metric in ['cpu_percent', 'cpu_top_process_percent']:
            candidates.extend([
                OptimizationCandidate(
                    candidate_id=f"rule_cpu_priority_{int(time.time())}",
                    name="降低高CPU进程优先级",
                    description="将高CPU占用进程优先级降低为BelowNormal",
                    operation_type="process_priority",
                    command="powershell -Command \"Get-Process | Where-Object {$_.CPU -gt 50} | ForEach-Object { $_.PriorityClass = 'BelowNormal' }\"",
                    risk_level=RiskLevel.L1_SAFE,
                    estimated_benefit=0.5,
                    estimated_risk=0.15,
                    estimated_cost=0.2,
                    timeout=60
                ),
            ])
        
        # 磁盘相关
        elif metric in ['disk_c_percent', 'temp_files_gb']:
            candidates.extend([
                OptimizationCandidate(
                    candidate_id=f"rule_disk_temp_{int(time.time())}",
                    name="清理临时文件",
                    description="清理用户临时文件和系统临时文件",
                    operation_type="file_clean",
                    command="powershell -Command \"Remove-Item -Path '$env:TEMP\\*' -Recurse -Force -ErrorAction SilentlyContinue; Remove-Item -Path 'C:\\Windows\\Temp\\*' -Recurse -Force -ErrorAction SilentlyContinue\"",
                    risk_level=RiskLevel.L1_SAFE,
                    estimated_benefit=0.7,
                    estimated_risk=0.1,
                    estimated_cost=0.15,
                    timeout=120
                ),
                OptimizationCandidate(
                    candidate_id=f"rule_disk_update_{int(time.time())}",
                    name="清理Windows更新缓存",
                    description="清理SoftwareDistribution更新缓存",
                    operation_type="file_clean",
                    command="powershell -Command \"Stop-Service wuauserv; Remove-Item -Path 'C:\\Windows\\SoftwareDistribution\\Download\\*' -Recurse -Force; Start-Service wuauserv\"",
                    risk_level=RiskLevel.L2_REVERSIBLE,
                    estimated_benefit=0.5,
                    estimated_risk=0.2,
                    estimated_cost=0.3,
                    timeout=180
                ),
            ])
        
        # 启动相关
        elif metric in ['startup_items_count', 'boot_time_seconds']:
            candidates.extend([
                OptimizationCandidate(
                    candidate_id=f"rule_startup_disable_{int(time.time())}",
                    name="禁用不必要启动项",
                    description="识别并禁用非必要的开机启动项",
                    operation_type="startup_optimize",
                    command="powershell -Command \"Get-CimInstance Win32_StartupCommand | Select-Object Name, Command, Location\"",
                    risk_level=RiskLevel.L2_REVERSIBLE,
                    estimated_benefit=0.6,
                    estimated_risk=0.2,
                    estimated_cost=0.25,
                    timeout=60
                ),
            ])
        
        # AIOS自检相关
        elif metric in ['aios_error_count', 'memory_gateway_sync']:
            candidates.extend([
                OptimizationCandidate(
                    candidate_id=f"rule_aios_restart_{int(time.time())}",
                    name="重启AIOS异常组件",
                    description="检查并重启异常的AIOS服务组件",
                    operation_type="service_restart",
                    command="powershell -Command \"Restart-Service -Name 'AIOS*' -ErrorAction SilentlyContinue\"",
                    risk_level=RiskLevel.L2_REVERSIBLE,
                    estimated_benefit=0.8,
                    estimated_risk=0.15,
                    estimated_cost=0.2,
                    timeout=120
                ),
            ])
        
        return candidates
    
    def _calculate_score(self, candidate: OptimizationCandidate) -> float:
        """三维稳态评分: 利益40% + 风险35% + 成本25%"""
        weights = self.config['weights']
        
        benefit = candidate.estimated_benefit
        risk_score = 1 - candidate.estimated_risk
        cost_score = 1 - candidate.estimated_cost
        
        # 应用历史风险调整
        if self.config['use_historical_adjustment']:
            adjustment = self.knowledge_base.get_risk_adjustment(
                candidate.operation_type, candidate.name
            )
            risk_score *= adjustment
        
        score = (benefit * weights['benefit']) + \
                (risk_score * weights['risk']) + \
                (cost_score * weights['cost'])
        
        return round(min(max(score, 0), 1), 4)
    
    def record_result(self, decision: Decision, success: bool, improvement: float = 0, reason: str = ""):
        """记录决策结果，更新知识库和熔断状态"""
        if decision.candidate and decision.anomaly:
            if success:
                self.knowledge_base.record_success(
                    decision.anomaly, decision.candidate, improvement
                )
                self.consecutive_failures = 0
            else:
                self.knowledge_base.record_failure(
                    decision.anomaly, decision.candidate, reason
                )
                self.consecutive_failures += 1
        
        self.circuit_breaker.record_result(success)
    
    def get_status(self) -> Dict:
        """获取决策引擎状态"""
        return {
            "decisions_made": len(self.decision_history),
            "consecutive_failures": self.consecutive_failures,
            "knowledge_base_patterns": len(self.knowledge_base.knowledge.get('patterns', {})),
            "circuit_breaker": self.circuit_breaker.get_status(),
            "recent_decisions": [
                {
                    "id": d.decision_id,
                    "action": d.action.value,
                    "score": d.score,
                    "reason": d.reason,
                    "timestamp": d.timestamp
                }
                for d in self.decision_history[-10:]
            ]
        }

# 单例
_decision_engine = None

def get_decision_engine() -> DecisionEngine:
    """获取决策引擎单例"""
    global _decision_engine
    if _decision_engine is None:
        _decision_engine = DecisionEngine()
    return _decision_engine

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    engine = get_decision_engine()
    print("=" * 50)
    print("自治决策引擎测试")
    print("=" * 50)
    
    # 模拟异常
    anomaly = AnomalyEvent(
        anomaly_id="test_001",
        metric="memory_percent",
        current_value=88.5,
        severity=Severity.CRITICAL,
        description="内存使用率过高: 88.5%",
        timestamp=datetime.now().isoformat(),
        confidence=0.95
    )
    
    # 决策
    decision = engine.decide(anomaly)
    print(f"\n决策结果:")
    print(f"  动作: {decision.action.value}")
    print(f"  评分: {decision.score}")
    print(f"  原因: {decision.reason}")
    if decision.candidate:
        print(f"  方案: {decision.candidate.name}")
        print(f"  风险级别: {decision.candidate.risk_level.value}")
        print(f"  评估方案数: {decision.candidates_evaluated}")
    
    # 状态
    status = engine.get_status()
    print(f"\n引擎状态: {json.dumps(status, indent=2, ensure_ascii=False)}")
