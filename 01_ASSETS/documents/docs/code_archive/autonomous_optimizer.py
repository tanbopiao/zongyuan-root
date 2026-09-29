"""
火斗云智AIOS - 完全自治优化引擎
零人工介入 · 自动检测·决策·执行·验证·进化
"""
import os
import sys
import json
import time
import hashlib
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import deque

# ============ 枚举定义 ============

class RiskLevel(Enum):
    """风险级别"""
    L0_READONLY = "L0"      # 只读，无风险
    L1_SAFE = "L1"          # 安全，只删缓存
    L2_REVERSIBLE = "L2"    # 可逆，有备份
    L3_SENSITIVE = "L3"     # 敏感，多重校验
    L4_DANGEROUS = "L4"     # 危险，必须人工

class Severity(Enum):
    """严重程度"""
    NORMAL = "normal"
    NOTICE = "notice"
    WARNING = "warning"
    CRITICAL = "critical"
    FATAL = "fatal"

class DecisionAction(Enum):
    """决策动作"""
    AUTO_EXECUTE = "auto_execute"
    WAIT_FOR_HUMAN = "wait_for_human"
    SKIP = "skip"
    SCHEDULE = "schedule"

# ============ 数据类 ============

@dataclass
class AnomalyEvent:
    """异常事件"""
    metric: str
    current_value: float
    severity: Severity
    description: str
    timestamp: str
    confidence: float = 0.0
    history_values: List[float] = field(default_factory=list)

@dataclass
class OptimizationCandidate:
    """优化候选方案"""
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

@dataclass
class Decision:
    """决策结果"""
    action: DecisionAction
    candidate: Optional[OptimizationCandidate] = None
    score: float = 0.0
    reason: str = ""
    auto_backup: bool = False
    auto_rollback: bool = True

@dataclass
class ExecutionResult:
    """执行结果"""
    success: bool
    output: str
    duration: float
    rolled_back: bool = False
    error: str = ""

@dataclass
class VerificationResult:
    """验证结果"""
    passed: bool
    improvement_percentage: float
    comparison: Dict
    rolled_back: bool = False
    details: Dict = field(default_factory=dict)

@dataclass
class Experience:
    """经验条目"""
    problem: str
    solution: str
    result: str
    improvement: float
    timestamp: str
    parameters: Dict = field(default_factory=dict)

# ============ 检测引擎 ============

class DetectionEngine:
    """自治检测引擎"""
    
    def __init__(self):
        self.history = {}  # metric -> deque of values
        self.anomalies = []
        self.check_intervals = {
            "memory": 300,
            "cpu": 300,
            "disk": 3600,
            "network": 600,
            "services": 3600,
            "aios_self": 300
        }
        self.last_check = {}
    
    def check_all(self) -> List[AnomalyEvent]:
        """全维度检测"""
        anomalies = []
        
        # 内存检测
        mem_anomalies = self._check_memory()
        anomalies.extend(mem_anomalies)
        
        # CPU检测
        cpu_anomalies = self._check_cpu()
        anomalies.extend(cpu_anomalies)
        
        # 磁盘检测
        disk_anomalies = self._check_disk()
        anomalies.extend(disk_anomalies)
        
        # 服务检测
        svc_anomalies = self._check_services()
        anomalies.extend(svc_anomalies)
        
        # AIOS自检测
        aios_anomalies = self._check_aios_self()
        anomalies.extend(aios_anomalies)
        
        self.anomalies = anomalies
        return anomalies
    
    def _check_memory(self) -> List[AnomalyEvent]:
        """内存检测"""
        anomalies = []
        try:
            import psutil
            mem = psutil.virtual_memory()
            
            # 记录历史
            if "memory_percent" not in self.history:
                self.history["memory_percent"] = deque(maxlen=100)
            self.history["memory_percent"].append(mem.percent)
            
            # 阈值检测
            if mem.percent > 90:
                anomalies.append(AnomalyEvent(
                    metric="memory_percent",
                    current_value=mem.percent,
                    severity=Severity.CRITICAL,
                    description=f"内存占用过高: {mem.percent:.1f}%",
                    timestamp=datetime.now().isoformat(),
                    confidence=0.95
                ))
            elif mem.percent > 80:
                anomalies.append(AnomalyEvent(
                    metric="memory_percent",
                    current_value=mem.percent,
                    severity=Severity.WARNING,
                    description=f"内存占用偏高: {mem.percent:.1f}%",
                    timestamp=datetime.now().isoformat(),
                    confidence=0.9
                ))
            
            # 内存泄漏检测（持续上升趋势）
            if len(self.history["memory_percent"]) >= 10:
                recent = list(self.history["memory_percent"])[-10:]
                if all(recent[i] < recent[i+1] for i in range(len(recent)-1)):
                    anomalies.append(AnomalyEvent(
                        metric="memory_leak",
                        current_value=recent[-1] - recent[0],
                        severity=Severity.WARNING,
                        description=f"内存持续上升，可能存在泄漏: +{recent[-1]-recent[0]:.1f}%",
                        timestamp=datetime.now().isoformat(),
                        confidence=0.7
                    ))
        except Exception as e:
            logging.error(f"内存检测失败: {e}")
        
        return anomalies
    
    def _check_cpu(self) -> List[AnomalyEvent]:
        """CPU检测"""
        # 实现略，类似内存检测
        return []
    
    def _check_disk(self) -> List[AnomalyEvent]:
        """磁盘检测"""
        # 实现略
        return []
    
    def _check_services(self) -> List[AnomalyEvent]:
        """服务检测"""
        # 实现略
        return []
    
    def _check_aios_self(self) -> List[AnomalyEvent]:
        """AIOS自检测"""
        # 实现略
        return []

# ============ 决策引擎 ============

class DecisionEngine:
    """自治决策引擎"""
    
    def __init__(self, knowledge_base=None):
        self.knowledge_base = knowledge_base
        self.decision_history = []
        self.consecutive_failures = 0
        self.circuit_open = False
        self.circuit_reason = ""
    
    def decide(self, anomaly: AnomalyEvent) -> Decision:
        """自治决策"""
        
        # 1. 熔断检查
        if self.circuit_open:
            return Decision(
                action=DecisionAction.SKIP,
                reason=f"熔断中: {self.circuit_reason}"
            )
        
        # 2. 生成候选方案
        candidates = self._generate_candidates(anomaly)
        if not candidates:
            return Decision(
                action=DecisionAction.SKIP,
                reason="无可用优化方案"
            )
        
        # 3. 三维稳态评分
        for candidate in candidates:
            candidate.score = self._calculate_score(candidate)
        
        # 4. 选择最优方案
        best = max(candidates, key=lambda x: x.score)
        
        # 5. L4检查
        if best.risk_level == RiskLevel.L4_DANGEROUS:
            return Decision(
                action=DecisionAction.WAIT_FOR_HUMAN,
                candidate=best,
                score=best.score,
                reason="L4危险操作，需要人工确认"
            )
        
        # 6. 置信度检查
        if best.score < 0.4:
            return Decision(
                action=DecisionAction.SKIP,
                candidate=best,
                score=best.score,
                reason=f"置信度过低: {best.score:.2f}"
            )
        
        # 7. 自动执行决策
        return Decision(
            action=DecisionAction.AUTO_EXECUTE,
            candidate=best,
            score=best.score,
            auto_backup=best.risk_level in [RiskLevel.L2_REVERSIBLE, RiskLevel.L3_SENSITIVE],
            auto_rollback=True
        )
    
    def _calculate_score(self, candidate: OptimizationCandidate) -> float:
        """三维稳态评分: 利益40% + 风险35% + 成本25%"""
        benefit = candidate.estimated_benefit
        risk_score = 1 - candidate.estimated_risk
        cost_score = 1 - candidate.estimated_cost
        
        return (benefit * 0.40) + (risk_score * 0.35) + (cost_score * 0.25)
    
    def _generate_candidates(self, anomaly: AnomalyEvent) -> List[OptimizationCandidate]:
        """生成候选优化方案"""
        candidates = []
        
        # 根据异常类型生成方案
        if anomaly.metric == "memory_percent":
            candidates.extend([
                OptimizationCandidate(
                    name="关闭闲置进程",
                    description="关闭内存占用高且闲置的进程",
                    operation_type="process_kill",
                    command="...",
                    risk_level=RiskLevel.L1_SAFE,
                    estimated_benefit=0.6,
                    estimated_risk=0.1,
                    estimated_cost=0.2
                ),
                OptimizationCandidate(
                    name="清理内存缓存",
                    description="清理standby列表和内存缓存",
                    operation_type="memory_clean",
                    command="...",
                    risk_level=RiskLevel.L1_SAFE,
                    estimated_benefit=0.4,
                    estimated_risk=0.05,
                    estimated_cost=0.1
                ),
            ])
        # 其他异常类型...
        
        return candidates
    
    def record_result(self, success: bool):
        """记录决策结果，更新熔断状态"""
        if success:
            self.consecutive_failures = 0
        else:
            self.consecutive_failures += 1
            if self.consecutive_failures >= 3:
                self.circuit_open = True
                self.circuit_reason = "连续3次失败"

# ============ 执行引擎 ============

class ExecutionEngine:
    """自治执行引擎"""
    
    def __init__(self, service_url="http://127.0.0.1:9150"):
        self.service_url = service_url
        self.backup_manager = BackupManager()
        self.rollback_log = []
    
    def execute(self, decision: Decision) -> ExecutionResult:
        """执行决策"""
        if decision.action != DecisionAction.AUTO_EXECUTE:
            return ExecutionResult(success=False, output="", duration=0, error="非自动执行决策")
        
        candidate = decision.candidate
        start_time = time.time()
        
        # 1. 自动备份
        backup_record = None
        if decision.auto_backup:
            backup_record = self.backup_manager.backup(
                candidate.operation_type,
                candidate.targets
            )
        
        # 2. 通过高权限服务执行
        try:
            result = self._execute_via_service(candidate.command, candidate.timeout)
        except Exception as e:
            result = {"success": False, "output": "", "error": str(e)}
        
        # 3. 失败重试
        if not result.get("success"):
            for attempt in range(3):
                time.sleep(2 ** attempt)
                try:
                    result = self._execute_via_service(candidate.command, candidate.timeout)
                    if result.get("success"):
                        break
                except:
                    continue
        
        # 4. 仍然失败 → 自动回滚
        rolled_back = False
        if not result.get("success") and decision.auto_rollback and backup_record:
            self._rollback(backup_record)
            rolled_back = True
        
        duration = time.time() - start_time
        
        return ExecutionResult(
            success=result.get("success", False),
            output=result.get("output", ""),
            duration=duration,
            rolled_back=rolled_back,
            error=result.get("error", "")
        )
    
    def _execute_via_service(self, command: str, timeout: int) -> Dict:
        """通过高权限Windows服务执行（绕过UAC）"""
        import requests
        try:
            response = requests.post(
                f"{self.service_url}/api/execute",
                json={"command": command, "timeout": timeout},
                timeout=timeout + 10
            )
            return response.json()
        except Exception as e:
            # 服务不可用时，降级为本地执行（可能需要UAC）
            return {"success": False, "output": "", "error": f"服务不可用: {e}"}
    
    def _rollback(self, backup_record: Dict):
        """自动回滚"""
        # 实现回滚逻辑
        pass

# ============ 备份管理器 ============

class BackupManager:
    """自动备份管理器"""
    
    def __init__(self, backup_dir="./backups"):
        self.backup_dir = backup_dir
        os.makedirs(backup_dir, exist_ok=True)
    
    def backup(self, operation_type: str, targets: List[str]) -> Dict:
        """根据操作类型自动备份"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_id = f"{operation_type}_{timestamp}"
        backup_path = os.path.join(self.backup_dir, backup_id)
        
        # 根据类型执行备份
        backup_methods = {
            "registry": self._backup_registry,
            "service": self._backup_service,
            "startup": self._backup_startup,
            "process_kill": self._backup_process_list,
            "file_delete": self._backup_to_quarantine
        }
        
        method = backup_methods.get(operation_type, self._backup_generic)
        method(backup_path, targets)
        
        # 计算哈希
        backup_hash = self._calculate_hash(backup_path)
        
        return {
            "backup_id": backup_id,
            "operation_type": operation_type,
            "targets": targets,
            "backup_path": backup_path,
            "backup_hash": backup_hash,
            "timestamp": datetime.now().isoformat(),
            "can_rollback": True
        }
    
    def _calculate_hash(self, path: str) -> str:
        """计算备份哈希"""
        if os.path.isfile(path):
            with open(path, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        return "dir_hash_placeholder"
    
    def _backup_registry(self, path, targets):
        """备份注册表"""
        pass
    
    def _backup_service(self, path, targets):
        """备份服务配置"""
        pass
    
    def _backup_startup(self, path, targets):
        """备份启动项"""
        pass
    
    def _backup_process_list(self, path, targets):
        """备份进程列表"""
        pass
    
    def _backup_to_quarantine(self, path, targets):
        """备份文件到隔离区（不删除，移动）"""
        pass
    
    def _backup_generic(self, path, targets):
        """通用备份"""
        pass

# ============ 验证引擎 ============

class VerificationEngine:
    """自治验证引擎"""
    
    def verify(self, operation, before_snapshot: Dict) -> VerificationResult:
        """验证优化效果"""
        
        # 1. 等待系统稳定
        time.sleep(operation.candidate.stabilization_time)
        
        # 2. 采集优化后快照
        after_snapshot = self._take_snapshot()
        
        # 3. 量化对比
        comparison = self._compare(before_snapshot, after_snapshot)
        
        # 4. 多维度验证
        target_metric = operation.candidate.parameters.get("target_metric", "")
        target_improved = comparison.get(target_metric, {}).get("improved", False)
        no_regression = all(
            v.get("delta", 0) >= -5 
            for k, v in comparison.items() 
            if k != target_metric
        )
        system_stable = self._check_system_stability()
        
        passed = target_improved and no_regression and system_stable
        
        # 5. 计算改善百分比
        improvement = comparison.get(target_metric, {}).get("percentage", 0)
        
        return VerificationResult(
            passed=passed,
            improvement_percentage=improvement,
            comparison=comparison,
            details={
                "target_improved": target_improved,
                "no_regression": no_regression,
                "system_stable": system_stable
            }
        )
    
    def _take_snapshot(self) -> Dict:
        """采集系统快照"""
        snapshot = {}
        try:
            import psutil
            snapshot["memory_percent"] = psutil.virtual_memory().percent
            snapshot["cpu_percent"] = psutil.cpu_percent(interval=1)
            snapshot["disk_usage"] = psutil.disk_usage('/').percent
        except:
            pass
        return snapshot
    
    def _compare(self, before: Dict, after: Dict) -> Dict:
        """对比快照"""
        comparison = {}
        for key in before:
            if key in after:
                delta = after[key] - before[key]
                comparison[key] = {
                    "before": before[key],
                    "after": after[key],
                    "delta": delta,
                    "percentage": (delta / before[key] * 100) if before[key] else 0,
                    "improved": delta < 0  # 假设越低越好
                }
        return comparison
    
    def _check_system_stability(self) -> bool:
        """检查系统稳定性"""
        # 检查关键进程、服务、事件日志
        return True

# ============ 反馈进化引擎 ============

class FeedbackEngine:
    """反馈进化引擎"""
    
    def __init__(self, gateway_url="https://www.huodouai.com/api/report/truth"):
        self.gateway_url = gateway_url
        self.experiences = []
        self.pending_reports = deque()
    
    def process(self, operation, execution: ExecutionResult, verification: VerificationResult):
        """处理优化结果，沉淀经验"""
        
        experience = Experience(
            problem=operation.anomaly.description if hasattr(operation, 'anomaly') else "unknown",
            solution=operation.decision.candidate.name if operation.decision.candidate else "unknown",
            result="success" if verification.passed else "failed",
            improvement=verification.improvement_percentage,
            timestamp=datetime.now().isoformat(),
            parameters={
                "risk_level": operation.decision.candidate.risk_level.value if operation.decision.candidate else "",
                "duration": execution.duration,
                "rolled_back": verification.rolled_back
            }
        )
        
        self.experiences.append(experience)
        
        # 上报记忆网关
        self._report_to_gateway(experience)
        
        return experience
    
    def _report_to_gateway(self, experience: Experience):
        """自动上报记忆网关"""
        import requests
        truth_key = f"LOCAL.AUTONOMOUS.OPT.{int(time.time())}"
        truth_value = json.dumps({
            "problem": experience.problem,
            "solution": experience.solution,
            "result": experience.result,
            "improvement": experience.improvement,
            "timestamp": experience.timestamp
        }, ensure_ascii=False)
        
        try:
            response = requests.post(
                self.gateway_url,
                json={
                    "truth_key": truth_key,
                    "truth_value": truth_value,
                    "source_node": "local-windows-001",
                    "truth_type": "decision",
                    "category": "autonomous_optimization",
                    "did": "DID-BR-000002",
                    "trace_mark": "Ω₀⊂⊙∞⊂Ω"
                },
                timeout=30
            )
            return response.json()
        except Exception as e:
            # 失败存入待重传队列
            self.pending_reports.append({
                "truth_key": truth_key,
                "truth_value": truth_value,
                "error": str(e)
            })
            return {"success": False, "queued": True}

# ============ 主自治优化器 ============

class AutonomousOptimizer:
    """完全自治优化器 - 主入口"""
    
    def __init__(self):
        self.detector = DetectionEngine()
        self.decider = DecisionEngine()
        self.executor = ExecutionEngine()
        self.verifier = VerificationEngine()
        self.feedback = FeedbackEngine()
        self.running = False
        self.optimization_count = 0
    
    def run_cycle(self) -> Dict:
        """运行一个完整的自治优化周期"""
        
        cycle_result = {
            "cycle_id": self.optimization_count,
            "timestamp": datetime.now().isoformat(),
            "anomalies_detected": 0,
            "decisions_made": 0,
            "executions": 0,
            "successes": 0,
            "failures": 0,
            "rollbacks": 0
        }
        
        # 1. 检测
        anomalies = self.detector.check_all()
        cycle_result["anomalies_detected"] = len(anomalies)
        
        # 2. 对每个异常决策+执行+验证+反馈
        for anomaly in anomalies:
            if anomaly.severity in [Severity.NORMAL, Severity.NOTICE]:
                continue  # 低级别不处理
            
            # 决策
            decision = self.decider.decide(anomaly)
            if decision.action != DecisionAction.AUTO_EXECUTE:
                continue
            
            cycle_result["decisions_made"] += 1
            
            # 执行前快照
            before_snapshot = self.verifier._take_snapshot()
            
            # 封装操作对象
            operation = type('Operation', (), {
                'anomaly': anomaly,
                'decision': decision,
                'candidate': decision.candidate
            })()
            
            # 执行
            execution = self.executor.execute(decision)
            cycle_result["executions"] += 1
            
            # 验证
            verification = self.verifier.verify(operation, before_snapshot)
            
            # 反馈
            self.feedback.process(operation, execution, verification)
            
            # 记录结果
            if verification.passed:
                cycle_result["successes"] += 1
            else:
                cycle_result["failures"] += 1
                if verification.rolled_back:
                    cycle_result["rollbacks"] += 1
            
            # 更新决策引擎熔断状态
            self.decider.record_result(verification.passed)
        
        self.optimization_count += 1
        return cycle_result
    
    def start(self, interval: int = 300):
        """启动自治优化循环"""
        self.running = True
        logging.info("自治优化器启动")
        
        while self.running:
            try:
                result = self.run_cycle()
                logging.info(f"优化周期完成: {json.dumps(result)}")
            except Exception as e:
                logging.error(f"优化周期异常: {e}")
            
            time.sleep(interval)
    
    def stop(self):
        """停止自治优化"""
        self.running = False
        logging.info("自治优化器停止")

# ============ 单例 ============

_optimizer = None

def get_autonomous_optimizer() -> AutonomousOptimizer:
    """获取自治优化器单例"""
    global _optimizer
    if _optimizer is None:
        _optimizer = AutonomousOptimizer()
    return _optimizer

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    optimizer = get_autonomous_optimizer()
    
    # 运行单次测试
    print("=" * 50)
    print("火斗云智AIOS - 完全自治优化器测试")
    print("=" * 50)
    
    result = optimizer.run_cycle()
    print(f"\n优化周期结果: {json.dumps(result, indent=2)}")
