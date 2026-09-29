"""
火斗云智AIOS - 完全自治优化器 V2.0
五大引擎集成：检测→决策→执行→验证→反馈进化
零人工介入的完全自治优化系统
"""
import os
import sys
import json
import time
import logging
import threading
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engines.detection_engine import get_detection_engine, AnomalyEvent, Severity
from engines.decision_engine import get_decision_engine, Decision, DecisionAction, RiskLevel
from engines.execution_engine import get_execution_engine, ExecutionResult
from engines.verification_engine import get_verification_engine, VerificationResult
from engines.feedback_engine import get_feedback_engine, Experience
from circuit_breaker.circuit_breaker import get_circuit_breaker

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(__file__), 'logs', 'autonomous_optimizer.log'), encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('AutonomousOptimizer')

@dataclass
class OptimizationCycle:
    """优化周期记录"""
    cycle_id: str
    start_time: str
    end_time: str = ""
    duration: float = 0
    anomalies_detected: int = 0
    decisions_made: int = 0
    executions: int = 0
    successes: int = 0
    failures: int = 0
    rollbacks: int = 0
    total_improvement: float = 0
    status: str = "running"  # running/completed/failed
    details: List[Dict] = field(default_factory=list)

class AutonomousOptimizer:
    """完全自治优化器 - 主入口"""
    
    def __init__(self, config: Dict = None):
        self.config = config or self._default_config()
        
        # 初始化五大引擎
        self.detector = get_detection_engine()
        self.decider = get_decision_engine()
        self.executor = get_execution_engine()
        self.verifier = get_verification_engine()
        self.feedback = get_feedback_engine()
        self.circuit_breaker = get_circuit_breaker()
        
        # 状态
        self.running = False
        self.main_thread = None
        self.cycle_count = 0
        self.cycle_history = []
        self.paused = False
        
        # 确保目录存在
        os.makedirs(os.path.join(os.path.dirname(__file__), 'logs'), exist_ok=True)
        os.makedirs(os.path.join(os.path.dirname(__file__), 'config'), exist_ok=True)
        os.makedirs(os.path.join(os.path.dirname(__file__), 'backups'), exist_ok=True)
        
        logger.info("=" * 60)
        logger.info("火斗云智AIOS - 完全自治优化器 V2.0 初始化完成")
        logger.info(f"五大引擎: 检测/决策/执行/验证/反馈进化")
        logger.info(f"配置: 检查间隔={self.config['check_interval']}秒, "
                    f"最大并发优化={self.config['max_concurrent_optimizations']}")
        logger.info("=" * 60)
    
    def _default_config(self) -> Dict:
        return {
            "check_interval": 300,  # 主循环检查间隔（秒）
            "max_concurrent_optimizations": 3,  # 最大并发优化数
            "min_severity_for_auto": "warning",  # 自动执行的最低严重程度
            "schedule_hours": {"start": 2, "end": 6},  # 深度优化时间窗口（凌晨2-6点）
            "notification_enabled": True,  # 异常通知
            "memory_gateway_report": True,  # 记忆网关上报告
            "auto_backup": True,  # 自动备份
            "auto_rollback": True,  # 自动回滚
            "evolution_enabled": True  # 进化学习启用
        }
    
    def run_cycle(self) -> OptimizationCycle:
        """运行一个完整的自治优化周期"""
        cycle_id = f"cycle_{self.cycle_count}_{int(time.time())}"
        start_time = datetime.now()
        
        cycle = OptimizationCycle(
            cycle_id=cycle_id,
            start_time=start_time.isoformat()
        )
        
        logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info(f"优化周期开始: {cycle_id}")
        logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        try:
            # ========== 阶段1：检测 ==========
            logger.info("【阶段1/5】检测引擎 - 全维度异常检测")
            anomalies = self.detector.check_all()
            cycle.anomalies_detected = len(anomalies)
            
            if not anomalies:
                logger.info("✅ 未检测到异常，系统状态良好")
                cycle.status = "completed"
                cycle.end_time = datetime.now().isoformat()
                cycle.duration = (datetime.now() - start_time).total_seconds()
                self.cycle_history.append(cycle)
                return cycle
            
            logger.info(f"⚠️  检测到 {len(anomalies)} 个异常:")
            for anomaly in anomalies:
                logger.info(f"  [{anomaly.severity.value}] {anomaly.description}")
            
            # 按严重程度排序，优先处理严重异常
            severity_order = {
                Severity.FATAL: 0,
                Severity.CRITICAL: 1,
                Severity.WARNING: 2,
                Severity.NOTICE: 3,
                Severity.NORMAL: 4
            }
            anomalies.sort(key=lambda a: severity_order.get(a.severity, 99))
            
            # ========== 阶段2-5：对每个异常执行完整闭环 ==========
            active_optimizations = 0
            
            for anomaly in anomalies:
                # 检查熔断
                if not self.circuit_breaker.can_execute():
                    logger.warning("🔒 熔断已触发，跳过剩余优化")
                    break
                
                # 检查并发限制
                if active_optimizations >= self.config['max_concurrent_optimizations']:
                    logger.info(f"⏳ 达到最大并发优化数({self.config['max_concurrent_optimizations']})，等待下一轮")
                    break
                
                # 低严重程度的异常可能只记录不执行
                min_severity = self.config['min_severity_for_auto']
                severity_levels = ['normal', 'notice', 'warning', 'critical', 'fatal']
                if severity_levels.index(anomaly.severity.value) < severity_levels.index(min_severity):
                    logger.info(f"📝 异常严重程度({anomaly.severity.value})低于自动执行阈值({min_severity})，仅记录")
                    continue
                
                active_optimizations += 1
                
                try:
                    # 阶段2：决策
                    logger.info(f"【阶段2/5】决策引擎 - 分析异常: {anomaly.metric}")
                    decision = self.decider.decide(anomaly)
                    cycle.decisions_made += 1
                    
                    if decision.action == DecisionAction.SKIP:
                        logger.info(f"⏭️  决策跳过: {decision.reason}")
                        active_optimizations -= 1
                        continue
                    elif decision.action == DecisionAction.WAIT_FOR_HUMAN:
                        logger.info(f"👤 需要人工介入: {decision.reason}")
                        # 记录待人工处理的决策
                        cycle.details.append({
                            "anomaly": anomaly.metric,
                            "action": "wait_for_human",
                            "reason": decision.reason,
                            "candidate": decision.candidate.name if decision.candidate else ""
                        })
                        active_optimizations -= 1
                        continue
                    elif decision.action == DecisionAction.SCHEDULE:
                        logger.info(f"📅 已调度执行: {decision.reason}")
                        active_optimizations -= 1
                        continue
                    
                    # 阶段3：执行
                    logger.info(f"【阶段3/5】执行引擎 - 执行优化: {decision.candidate.name}")
                    logger.info(f"  风险级别: {decision.candidate.risk_level.value}")
                    logger.info(f"  预计收益: {decision.candidate.estimated_benefit:.0%}")
                    logger.info(f"  命令: {decision.candidate.command[:100]}...")
                    
                    execution_result = self.executor.execute(decision)
                    cycle.executions += 1
                    
                    if not execution_result.success:
                        logger.error(f"❌ 执行失败: {execution_result.error}")
                        if execution_result.rolled_back:
                            logger.info("🔄 已自动回滚")
                            cycle.rollbacks += 1
                        cycle.failures += 1
                        
                        # 记录失败结果
                        self.decider.record_result(decision, False, reason=execution_result.error)
                        active_optimizations -= 1
                        continue
                    
                    logger.info(f"✅ 执行成功，耗时: {execution_result.duration:.1f}秒")
                    
                    # 阶段4：验证
                    logger.info(f"【阶段4/5】验证引擎 - 验证优化效果")
                    verification_result = self.verifier.verify(decision, execution_result)
                    
                    if not verification_result.passed:
                        logger.warning(f"⚠️  验证未通过: {verification_result.verification_report}")
                        if verification_result.rolled_back:
                            logger.info("🔄 已自动回滚")
                            cycle.rollbacks += 1
                        cycle.failures += 1
                        
                        # 记录验证失败结果
                        self.decider.record_result(decision, False, reason="验证未通过")
                        active_optimizations -= 1
                        continue
                    
                    logger.info(f"✅ 验证通过，改善幅度: {verification_result.improvement_percentage:.2f}%")
                    cycle.successes += 1
                    cycle.total_improvement += verification_result.improvement_percentage
                    
                    # 阶段5：反馈进化
                    logger.info(f"【阶段5/5】反馈进化引擎 - 沉淀经验")
                    experience = self.feedback.process(decision, execution_result, verification_result)
                    
                    logger.info(f"📚 经验已沉淀: {experience.experience_id}")
                    logger.info(f"  结果: {experience.result}")
                    logger.info(f"  教训: {experience.lessons_learned}")
                    
                    # 记录成功结果
                    self.decider.record_result(decision, True, improvement=verification_result.improvement_percentage)
                    
                    cycle.details.append({
                        "anomaly": anomaly.metric,
                        "candidate": decision.candidate.name,
                        "risk_level": decision.candidate.risk_level.value,
                        "improvement": verification_result.improvement_percentage,
                        "duration": execution_result.duration,
                        "experience_id": experience.experience_id
                    })
                    
                    active_optimizations -= 1
                    
                except Exception as e:
                    logger.error(f"💥 优化异常: {str(e)}", exc_info=True)
                    cycle.failures += 1
                    active_optimizations -= 1
                    continue
            
            # 周期完成
            cycle.status = "completed"
            cycle.end_time = datetime.now().isoformat()
            cycle.duration = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            logger.info(f"优化周期完成: {cycle_id}")
            logger.info(f"  检测异常: {cycle.anomalies_detected}")
            logger.info(f"  决策数量: {cycle.decisions_made}")
            logger.info(f"  执行优化: {cycle.executions}")
            logger.info(f"  成功: {cycle.successes}, 失败: {cycle.failures}, 回滚: {cycle.rollbacks}")
            logger.info(f"  总改善: {cycle.total_improvement:.2f}%")
            logger.info(f"  耗时: {cycle.duration:.1f}秒")
            logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            
        except Exception as e:
            logger.error(f"💥 优化周期异常: {str(e)}", exc_info=True)
            cycle.status = "failed"
            cycle.end_time = datetime.now().isoformat()
            cycle.duration = (datetime.now() - start_time).total_seconds()
        
        self.cycle_history.append(cycle)
        if len(self.cycle_history) > 1000:
            self.cycle_history = self.cycle_history[-1000:]
        
        self.cycle_count += 1
        
        # 保存周期记录
        self._save_cycle_record(cycle)
        
        return cycle
    
    def _save_cycle_record(self, cycle: OptimizationCycle):
        """保存周期记录"""
        try:
            record_path = os.path.join(
                os.path.dirname(__file__), 'logs', 
                f'cycle_{cycle.cycle_id}.json'
            )
            with open(record_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "cycle_id": cycle.cycle_id,
                    "start_time": cycle.start_time,
                    "end_time": cycle.end_time,
                    "duration": cycle.duration,
                    "anomalies_detected": cycle.anomalies_detected,
                    "decisions_made": cycle.decisions_made,
                    "executions": cycle.executions,
                    "successes": cycle.successes,
                    "failures": cycle.failures,
                    "rollbacks": cycle.rollbacks,
                    "total_improvement": cycle.total_improvement,
                    "status": cycle.status,
                    "details": cycle.details
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存周期记录失败: {e}")
    
    def start(self, interval: int = None):
        """启动自治优化循环"""
        if self.running:
            logger.warning("自治优化器已在运行中")
            return
        
        if interval:
            self.config['check_interval'] = interval
        
        self.running = True
        self.paused = False
        
        self.main_thread = threading.Thread(target=self._main_loop, daemon=True)
        self.main_thread.start()
        
        logger.info(f"🚀 自治优化循环已启动，检查间隔: {self.config['check_interval']}秒")
    
    def stop(self):
        """停止自治优化循环"""
        self.running = False
        if self.main_thread:
            self.main_thread.join(timeout=10)
        logger.info("⏹️  自治优化循环已停止")
    
    def pause(self):
        """暂停自治优化"""
        self.paused = True
        logger.info("⏸️  自治优化已暂停")
    
    def resume(self):
        """恢复自治优化"""
        self.paused = False
        logger.info("▶️  自治优化已恢复")
    
    def _main_loop(self):
        """主循环"""
        while self.running:
            try:
                if not self.paused:
                    self.run_cycle()
                else:
                    logger.info("⏸️  自治优化暂停中...")
            except Exception as e:
                logger.error(f"💥 主循环异常: {str(e)}", exc_info=True)
            
            # 等待下一个周期
            time.sleep(self.config['check_interval'])
    
    def get_status(self) -> Dict:
        """获取自治优化器状态"""
        total_cycles = len(self.cycle_history)
        total_successes = sum(c.successes for c in self.cycle_history)
        total_failures = sum(c.failures for c in self.cycle_history)
        total_rollbacks = sum(c.rollbacks for c in self.cycle_history)
        total_improvement = sum(c.total_improvement for c in self.cycle_history)
        
        return {
            "running": self.running,
            "paused": self.paused,
            "cycle_count": self.cycle_count,
            "check_interval": self.config['check_interval'],
            "total_cycles": total_cycles,
            "total_successes": total_successes,
            "total_failures": total_failures,
            "total_rollbacks": total_rollbacks,
            "total_improvement": total_improvement,
            "success_rate": (total_successes / (total_successes + total_failures) * 100) 
                           if (total_successes + total_failures) > 0 else 0,
            "engines": {
                "detection": self.detector.get_status(),
                "decision": self.decider.get_status(),
                "execution": self.executor.get_status(),
                "verification": self.verifier.get_status(),
                "feedback": self.feedback.get_status()
            },
            "circuit_breaker": self.circuit_breaker.get_status(),
            "recent_cycles": [
                {
                    "cycle_id": c.cycle_id,
                    "status": c.status,
                    "anomalies": c.anomalies_detected,
                    "successes": c.successes,
                    "failures": c.failures,
                    "improvement": c.total_improvement,
                    "duration": c.duration
                }
                for c in self.cycle_history[-5:]
            ]
        }

# 单例
_optimizer = None

def get_autonomous_optimizer() -> AutonomousOptimizer:
    """获取自治优化器单例"""
    global _optimizer
    if _optimizer is None:
        _optimizer = AutonomousOptimizer()
    return _optimizer

if __name__ == "__main__":
    print("=" * 60)
    print("  火斗云智AIOS - 完全自治优化器 V2.0")
    print("  五大引擎集成：检测→决策→执行→验证→反馈进化")
    print("=" * 60)
    
    optimizer = get_autonomous_optimizer()
    
    # 运行单次测试
    print("\n▶️  运行单次优化周期测试...")
    cycle = optimizer.run_cycle()
    
    print(f"\n📊 测试结果:")
    print(f"  周期ID: {cycle.cycle_id}")
    print(f"  状态: {cycle.status}")
    print(f"  检测异常: {cycle.anomalies_detected}")
    print(f"  决策数量: {cycle.decisions_made}")
    print(f"  执行优化: {cycle.executions}")
    print(f"  成功: {cycle.successes}")
    print(f"  失败: {cycle.failures}")
    print(f"  回滚: {cycle.rollbacks}")
    print(f"  总改善: {cycle.total_improvement:.2f}%")
    print(f"  耗时: {cycle.duration:.1f}秒")
    
    # 状态
    status = optimizer.get_status()
    print(f"\n📈 系统状态:")
    print(f"  总周期数: {status['total_cycles']}")
    print(f"  总成功: {status['total_successes']}")
    print(f"  总失败: {status['total_failures']}")
    print(f"  成功率: {status['success_rate']:.1f}%")
    print(f"  总改善: {status['total_improvement']:.2f}%")
    
    print("\n✅ 完全自治优化器测试完成！")
