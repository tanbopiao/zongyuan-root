"""
引擎三：自治执行引擎
集成高权限服务 + 自动备份 + 自动重试 + 失败回滚
"""
import os
import sys
import json
import time
import logging
import hashlib
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engines.decision_engine import Decision, OptimizationCandidate, RiskLevel
from api.aios_service_client import AISOServiceClient, get_service_client

logger = logging.getLogger(__name__)

@dataclass
class ExecutionResult:
    """执行结果"""
    success: bool
    output: str
    duration: float
    rolled_back: bool = False
    error: str = ""
    backup_record: Dict = field(default_factory=dict)
    retry_count: int = 0
    before_snapshot: Dict = field(default_factory=dict)
    after_snapshot: Dict = field(default_factory=dict)

class ExecutionEngine:
    """自治执行引擎"""
    
    def __init__(self, config: Dict = None):
        self.config = config or self._default_config()
        self.service_client = get_service_client()
        self.execution_history = []
        self.backup_dir = self.config.get('backup_dir', 
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backups'))
        os.makedirs(self.backup_dir, exist_ok=True)
    
    def _default_config(self) -> Dict:
        return {
            "max_retries": 3,
            "retry_delay_base": 2,  # 指数退避基数
            "default_timeout": 300,
            "stabilization_time": 60,
            "auto_backup_risk_levels": ["L2", "L3"],
            "backup_dir": "./backups"
        }
    
    def execute(self, decision: Decision) -> ExecutionResult:
        """执行决策"""
        start_time = time.time()
        
        if decision.action.value != "auto_execute" or not decision.candidate:
            return ExecutionResult(
                success=False,
                output="",
                duration=0,
                error="非自动执行决策或无候选方案"
            )
        
        candidate = decision.candidate
        
        # 1. 执行前快照
        before_snapshot = self._take_snapshot()
        
        # 2. 自动备份
        backup_record = {}
        if decision.auto_backup or candidate.risk_level.value in self.config['auto_backup_risk_levels']:
            backup_record = self._perform_backup(candidate)
        
        # 3. 执行命令（带自动重试）
        result = self._execute_with_retry(candidate)
        
        # 4. 执行后快照
        after_snapshot = self._take_snapshot()
        
        # 5. 失败自动回滚
        rolled_back = False
        if not result.success and decision.auto_rollback and backup_record:
            rollback_result = self._rollback(backup_record)
            rolled_back = rollback_result.success
            result.output += f"\n[自动回滚] {'成功' if rolled_back else '失败'}"
        
        duration = time.time() - start_time
        
        execution_result = ExecutionResult(
            success=result.success,
            output=result.output,
            duration=duration,
            rolled_back=rolled_back,
            error=result.error,
            backup_record=backup_record,
            retry_count=result.retry_count,
            before_snapshot=before_snapshot,
            after_snapshot=after_snapshot
        )
        
        # 记录执行历史
        self.execution_history.append({
            "decision_id": decision.decision_id,
            "candidate": candidate.name,
            "success": result.success,
            "duration": duration,
            "rolled_back": rolled_back,
            "timestamp": datetime.now().isoformat()
        })
        
        return execution_result
    
    def _execute_with_retry(self, candidate: OptimizationCandidate) -> ExecutionResult:
        """带自动重试的命令执行"""
        max_retries = self.config['max_retries']
        retry_delay_base = self.config['retry_delay_base']
        
        last_error = ""
        last_output = ""
        
        for attempt in range(max_retries):
            try:
                # 通过高权限服务执行
                result = self.service_client.execute_command(
                    command=candidate.command,
                    timeout=candidate.timeout,
                    need_backup=False,  # 备份已在外部完成
                    operation_type=candidate.operation_type,
                    targets=candidate.targets
                )
                
                if result.get('success'):
                    return ExecutionResult(
                        success=True,
                        output=result.get('stdout', ''),
                        duration=0,
                        retry_count=attempt,
                        error=""
                    )
                else:
                    last_error = result.get('error', '执行失败')
                    last_output = result.get('stdout', '') + result.get('stderr', '')
                    
                    # L4黑名单拒绝，不重试
                    if 'L4黑名单' in last_error:
                        break
                        
            except Exception as e:
                last_error = str(e)
                last_output = ""
            
            # 重试前等待（指数退避）
            if attempt < max_retries - 1:
                delay = retry_delay_base ** (attempt + 1)
                logger.warning(f"执行失败（第{attempt+1}次），{delay}秒后重试: {last_error}")
                time.sleep(delay)
        
        return ExecutionResult(
            success=False,
            output=last_output,
            duration=0,
            retry_count=max_retries,
            error=last_error
        )
    
    def _perform_backup(self, candidate: OptimizationCandidate) -> Dict:
        """执行自动备份"""
        try:
            result = self.service_client.backup(
                operation_type=candidate.operation_type,
                targets=candidate.targets
            )
            return result
        except Exception as e:
            logger.error(f"备份失败: {e}")
            return {"success": False, "error": str(e)}
    
    def _rollback(self, backup_record: Dict) -> ExecutionResult:
        """执行回滚"""
        try:
            backup_id = backup_record.get('backup_id', '')
            if not backup_id:
                return ExecutionResult(success=False, output="", duration=0, error="无备份ID")
            
            result = self.service_client.rollback(backup_id)
            return ExecutionResult(
                success=result.get('success', False),
                output=str(result),
                duration=0,
                error=result.get('error', '')
            )
        except Exception as e:
            logger.error(f"回滚失败: {e}")
            return ExecutionResult(success=False, output="", duration=0, error=str(e))
    
    def _take_snapshot(self) -> Dict:
        """采集系统快照"""
        snapshot = {}
        try:
            import psutil
            snapshot['memory_percent'] = psutil.virtual_memory().percent
            snapshot['cpu_percent'] = psutil.cpu_percent(interval=0.5)
            snapshot['process_count'] = len(psutil.pids())
            
            # 磁盘
            for partition in psutil.disk_partitions():
                if 'C:' in partition.mountpoint:
                    usage = psutil.disk_usage(partition.mountpoint)
                    snapshot['disk_c_percent'] = usage.percent
                    break
        except Exception as e:
            logger.error(f"快照采集失败: {e}")
        
        snapshot['timestamp'] = datetime.now().isoformat()
        return snapshot
    
    def get_status(self) -> Dict:
        """获取执行引擎状态"""
        return {
            "total_executions": len(self.execution_history),
            "success_rate": (
                sum(1 for e in self.execution_history if e['success']) / len(self.execution_history) * 100
                if self.execution_history else 0
            ),
            "rollback_count": sum(1 for e in self.execution_history if e.get('rolled_back')),
            "recent_executions": self.execution_history[-10:],
            "service_available": self.service_client.health_check().get('success', False)
        }

# 单例
_execution_engine = None

def get_execution_engine() -> ExecutionEngine:
    """获取执行引擎单例"""
    global _execution_engine
    if _execution_engine is None:
        _execution_engine = ExecutionEngine()
    return _execution_engine

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    engine = get_execution_engine()
    print("=" * 50)
    print("自治执行引擎测试")
    print("=" * 50)
    
    # 服务可用性检查
    health = engine.service_client.health_check()
    print(f"\n高权限服务状态: {health}")
    
    # 引擎状态
    status = engine.get_status()
    print(f"\n引擎状态: {json.dumps(status, indent=2, ensure_ascii=False)}")
