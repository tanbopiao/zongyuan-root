"""
引擎五：反馈进化引擎
自动经验沉淀 + 记忆网关上报告 + 决策模型更新 + 知识库进化
"""
import os
import sys
import json
import time
import logging
import requests
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engines.decision_engine import Decision, OptimizationCandidate
from engines.execution_engine import ExecutionResult
from engines.verification_engine import VerificationResult

logger = logging.getLogger(__name__)

@dataclass
class Experience:
    """经验条目"""
    experience_id: str
    problem: str
    solution: str
    result: str  # success/failed/rolled_back
    improvement: float
    risk_level: str
    operation_type: str
    duration: float
    timestamp: str
    parameters: Dict = field(default_factory=dict)
    lessons_learned: List[str] = field(default_factory=list)

class FeedbackEngine:
    """反馈进化引擎"""
    
    def __init__(self, config: Dict = None):
        self.config = config or self._default_config()
        self.experiences = deque(maxlen=1000)
        self.pending_reports = deque(maxlen=100)
        self.decision_model = self._load_decision_model()
        self.memory_gateway_url = self.config.get('memory_gateway_url', 
            'https://www.huodouai.com/api/report/truth')
        self.source_node = self.config.get('source_node', 'local-windows-001')
        self.did = self.config.get('did', 'DID-BR-000002')
        self.trace_mark = self.config.get('trace_mark', 'Ω₀⊂⊙∞⊂Ω')
    
    def _default_config(self) -> Dict:
        return {
            "memory_gateway_url": "https://www.huodouai.com/api/report/truth",
            "source_node": "local-windows-001",
            "did": "DID-BR-000002",
            "trace_mark": "Ω₀⊂⊙∞⊂Ω",
            "auto_report": True,
            "report_batch_size": 5,
            "max_retries": 3,
            "knowledge_base_path": "./config/optimization_knowledge.json",
            "decision_model_path": "./config/decision_model.json"
        }
    
    def _load_decision_model(self) -> Dict:
        """加载决策模型"""
        model_path = self.config.get('decision_model_path', './config/decision_model.json')
        if os.path.exists(model_path):
            try:
                with open(model_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {
            "version": "1.0.0",
            "weights": {"benefit": 0.40, "risk": 0.35, "cost": 0.25},
            "risk_adjustments": {},
            "success_patterns": {},
            "failure_patterns": {},
            "total_experiences": 0,
            "success_rate": 0.0,
            "last_updated": datetime.now().isoformat()
        }
    
    def _save_decision_model(self):
        """保存决策模型"""
        model_path = self.config.get('decision_model_path', './config/decision_model.json')
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        self.decision_model['last_updated'] = datetime.now().isoformat()
        with open(model_path, 'w', encoding='utf-8') as f:
            json.dump(self.decision_model, f, ensure_ascii=False, indent=2)
    
    def process(self, decision: Decision, execution_result: ExecutionResult, 
                verification_result: VerificationResult) -> Experience:
        """处理优化结果，沉淀经验"""
        
        # 1. 生成经验条目
        experience = self._create_experience(decision, execution_result, verification_result)
        
        # 2. 存入本地经验库
        self.experiences.append(experience)
        
        # 3. 更新决策模型
        self._update_decision_model(experience)
        
        # 4. 上报记忆网关
        if self.config['auto_report']:
            self._report_to_memory_gateway(experience)
        
        # 5. 提取教训
        lessons = self._extract_lessons(experience)
        experience.lessons_learned = lessons
        
        logger.info(f"经验沉淀完成: {experience.experience_id}, 结果: {experience.result}")
        
        return experience
    
    def _create_experience(self, decision: Decision, execution_result: ExecutionResult,
                           verification_result: VerificationResult) -> Experience:
        """创建经验条目"""
        if verification_result.passed:
            result = "success"
        elif verification_result.rolled_back:
            result = "rolled_back"
        else:
            result = "failed"
        
        problem = decision.anomaly.description if decision.anomaly else "unknown"
        solution = decision.candidate.name if decision.candidate else "unknown"
        risk_level = decision.candidate.risk_level.value if decision.candidate else "unknown"
        operation_type = decision.candidate.operation_type if decision.candidate else "unknown"
        
        return Experience(
            experience_id=f"exp_{int(time.time())}_{decision.decision_id}",
            problem=problem,
            solution=solution,
            result=result,
            improvement=verification_result.improvement_percentage,
            risk_level=risk_level,
            operation_type=operation_type,
            duration=execution_result.duration,
            timestamp=datetime.now().isoformat(),
            parameters={
                "decision_id": decision.decision_id,
                "score": decision.score,
                "confidence": decision.confidence,
                "retry_count": execution_result.retry_count,
                "verification_details": verification_result.details
            }
        )
    
    def _update_decision_model(self, experience: Experience):
        """更新决策模型"""
        model = self.decision_model
        
        # 更新统计
        model['total_experiences'] += 1
        
        # 更新成功率
        successes = sum(1 for e in self.experiences if e.result == 'success')
        model['success_rate'] = successes / len(self.experiences) if self.experiences else 0
        
        # 更新风险调整
        key = f"{experience.operation_type}_{experience.solution}"
        if key not in model['risk_adjustments']:
            model['risk_adjustments'][key] = {'success': 0, 'failure': 0, 'rolled_back': 0}
        
        if experience.result == 'success':
            model['risk_adjustments'][key]['success'] += 1
        elif experience.result == 'rolled_back':
            model['risk_adjustments'][key]['rolled_back'] += 1
        else:
            model['risk_adjustments'][key]['failure'] += 1
        
        # 更新成功/失败模式
        if experience.result == 'success' and experience.improvement > 5:
            if key not in model['success_patterns']:
                model['success_patterns'][key] = 0
            model['success_patterns'][key] += 1
        elif experience.result in ['failed', 'rolled_back']:
            if key not in model['failure_patterns']:
                model['failure_patterns'][key] = 0
            model['failure_patterns'][key] += 1
        
        # 保存模型
        self._save_decision_model()
    
    def _report_to_memory_gateway(self, experience: Experience) -> bool:
        """上报到记忆网关"""
        truth_key = f"LOCAL.AUTONOMOUS.OPT.{experience.experience_id}"
        truth_value = json.dumps({
            "problem": experience.problem,
            "solution": experience.solution,
            "result": experience.result,
            "improvement": experience.improvement,
            "risk_level": experience.risk_level,
            "operation_type": experience.operation_type,
            "duration": experience.duration,
            "timestamp": experience.timestamp,
            "lessons_learned": experience.lessons_learned
        }, ensure_ascii=False)
        
        try:
            response = requests.post(
                self.memory_gateway_url,
                json={
                    "truth_key": truth_key,
                    "truth_value": truth_value,
                    "source_node": self.source_node,
                    "truth_type": "decision",
                    "category": "autonomous_optimization",
                    "did": self.did,
                    "trace_mark": self.trace_mark
                },
                timeout=30
            )
            result = response.json()
            if result.get('success') or result.get('status') == 'reported':
                logger.info(f"记忆网关上报告成功: {truth_key}")
                return True
            else:
                logger.warning(f"记忆网关上报告失败: {result}")
                self.pending_reports.append(experience)
                return False
        except Exception as e:
            logger.error(f"记忆网关上报告异常: {e}")
            self.pending_reports.append(experience)
            return False
    
    def retry_pending_reports(self) -> int:
        """重试待上报的经验"""
        retry_count = 0
        while self.pending_reports:
            experience = self.pending_reports.popleft()
            if self._report_to_memory_gateway(experience):
                retry_count += 1
            else:
                self.pending_reports.append(experience)
                break  # 连续失败则停止重试
        return retry_count
    
    def _extract_lessons(self, experience: Experience) -> List[str]:
        """提取教训"""
        lessons = []
        
        if experience.result == 'success':
            if experience.improvement > 10:
                lessons.append(f"方案 '{experience.solution}' 效果显著(+{experience.improvement:.1f}%)，推荐优先使用")
            elif experience.improvement > 5:
                lessons.append(f"方案 '{experience.solution}' 效果良好(+{experience.improvement:.1f}%)")
            else:
                lessons.append(f"方案 '{experience.solution}' 效果一般(+{experience.improvement:.1f}%)，考虑优化参数")
        
        elif experience.result == 'rolled_back':
            lessons.append(f"方案 '{experience.solution}' 验证未通过已回滚，需要检查风险评估")
            lessons.append(f"建议降低 '{experience.operation_type}' 类型操作的风险评级")
        
        else:  # failed
            lessons.append(f"方案 '{experience.solution}' 执行失败，需要排查根因")
            if experience.duration > 120:
                lessons.append(f"执行耗时过长({experience.duration:.0f}秒)，考虑增加超时时间或优化命令")
        
        return lessons
    
    def get_evolution_summary(self) -> Dict:
        """获取进化总结"""
        total = len(self.experiences)
        successes = sum(1 for e in self.experiences if e.result == 'success')
        failures = sum(1 for e in self.experiences if e.result == 'failed')
        rollbacks = sum(1 for e in self.experiences if e.result == 'rolled_back')
        
        avg_improvement = 0
        if successes > 0:
            avg_improvement = sum(e.improvement for e in self.experiences if e.result == 'success') / successes
        
        # 最成功的方案
        top_solutions = {}
        for e in self.experiences:
            if e.result == 'success':
                key = e.solution
                if key not in top_solutions:
                    top_solutions[key] = {'count': 0, 'total_improvement': 0}
                top_solutions[key]['count'] += 1
                top_solutions[key]['total_improvement'] += e.improvement
        
        top_solutions_sorted = sorted(
            top_solutions.items(),
            key=lambda x: x[1]['total_improvement'] / x[1]['count'],
            reverse=True
        )[:5]
        
        return {
            "total_experiences": total,
            "success_count": successes,
            "failure_count": failures,
            "rollback_count": rollbacks,
            "success_rate": (successes / total * 100) if total > 0 else 0,
            "average_improvement": avg_improvement,
            "pending_reports": len(self.pending_reports),
            "top_solutions": [
                {
                    "solution": sol,
                    "count": data['count'],
                    "avg_improvement": data['total_improvement'] / data['count']
                }
                for sol, data in top_solutions_sorted
            ],
            "decision_model_version": self.decision_model.get('version', 'unknown'),
            "model_last_updated": self.decision_model.get('last_updated', '')
        }
    
    def get_status(self) -> Dict:
        """获取反馈引擎状态"""
        return {
            "experiences_stored": len(self.experiences),
            "pending_reports": len(self.pending_reports),
            "memory_gateway_url": self.memory_gateway_url,
            "auto_report": self.config['auto_report'],
            "evolution_summary": self.get_evolution_summary()
        }

# 单例
_feedback_engine = None

def get_feedback_engine() -> FeedbackEngine:
    """获取反馈引擎单例"""
    global _feedback_engine
    if _feedback_engine is None:
        _feedback_engine = FeedbackEngine()
    return _feedback_engine

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    engine = get_feedback_engine()
    print("=" * 50)
    print("反馈进化引擎测试")
    print("=" * 50)
    
    status = engine.get_status()
    print(f"\n引擎状态: {json.dumps(status, indent=2, ensure_ascii=False)}")
