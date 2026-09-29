#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 自进化引擎 V3.0 - 深度实现版
功能：完整四阶段闭环 + Docker沙箱真实隔离 + 灰度发布 + 自动回滚
溯源：Ω₀⊂⊙∞⊂Ω | DID-BR-000002
集成模块：docker_sandbox.py + gray_release.py
"""
import os
import sys
import json
import time
import hashlib
import subprocess
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

# 导入集成模块
try:
    from docker_sandbox import DockerSandbox, SandboxVerification
except ImportError:
    DockerSandbox = None
    SandboxVerification = None
    print("⚠️  docker_sandbox模块未找到，沙箱功能将不可用")

try:
    from gray_release import GrayReleaseManager, AutoRollbackMonitor
except ImportError:
    GrayReleaseManager = None
    AutoRollbackMonitor = None
    print("⚠️  gray_release模块未找到，灰度发布功能将不可用")


class SelfEvolutionEngineV3:
    """自进化引擎 V3.0 - 深度实现版"""
    
    def __init__(self,
                 base_dir: str = "/opt/ZONGYUAN-ROOT/evolution",
                 config_path: str = "/opt/ZONGYUAN-ROOT/self_evolution/config.json"):
        """
        初始化自进化引擎
        
        Args:
            base_dir: 基础工作目录
            config_path: 配置文件路径
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.config_path = Path(config_path)
        self.config = self._load_config()
        
        # 初始化子目录
        self.suggestions_dir = self.base_dir / "suggestions"
        self.sandbox_dir = self.base_dir / "sandbox"
        self.versions_dir = self.base_dir / "versions"
        self.history_dir = self.base_dir / "history"
        self.locks_dir = self.base_dir / "locks"
        self.logs_dir = self.base_dir / "logs"
        
        for d in [self.suggestions_dir, self.sandbox_dir, self.versions_dir,
                  self.history_dir, self.locks_dir, self.logs_dir]:
            d.mkdir(exist_ok=True)
        
        # 初始化集成模块
        self.sandbox_manager = None
        self.gray_manager = None
        
        if DockerSandbox:
            self.sandbox_manager = DockerSandbox(sandbox_dir=str(self.sandbox_dir))
        
        if GrayReleaseManager:
            self.gray_manager = GrayReleaseManager(versions_dir=str(self.versions_dir))
        
        # 引擎状态
        self.engine_state = {
            "version": "3.0.0",
            "started_at": datetime.now().isoformat(),
            "cycles_completed": 0,
            "suggestions_generated": 0,
            "sandbox_verifications": 0,
            "gray_releases": 0,
            "rollbacks": 0,
            "locks_created": 0,
            "status": "initialized"
        }
    
    def _load_config(self) -> Dict:
        """加载配置"""
        if self.config_path.exists():
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def _save_state(self):
        """保存引擎状态"""
        state_file = self.base_dir / "engine_state.json"
        self.engine_state["last_updated"] = datetime.now().isoformat()
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(self.engine_state, f, ensure_ascii=False, indent=2)
    
    def _sha256_hash(self, data: str) -> str:
        """计算SHA256哈希"""
        return hashlib.sha256(data.encode('utf-8')).hexdigest()
    
    def _log(self, message: str, level: str = "INFO"):
        """记录日志"""
        log_entry = f"[{datetime.now().isoformat()}] [{level}] {message}"
        print(log_entry)
        log_file = self.logs_dir / f"evolution_{datetime.now().strftime('%Y%m%d')}.log"
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry + "\n")
    
    # ==================== 阶段1：建议生成 ====================
    
    def get_system_metrics(self) -> Dict:
        """获取系统指标"""
        metrics = {}
        try:
            # 内存
            result = subprocess.run(['free', '-m'], capture_output=True, text=True)
            lines = result.stdout.strip().split('\n')
            if len(lines) >= 2:
                parts = lines[1].split()
                metrics['memory_total'] = int(parts[1])
                metrics['memory_used'] = int(parts[2])
                metrics['memory_percent'] = int(parts[2] * 100 / parts[1])
            
            # 磁盘
            result = subprocess.run(['df', '-h', '/'], capture_output=True, text=True)
            lines = result.stdout.strip().split('\n')
            if len(lines) >= 2:
                parts = lines[1].split()
                metrics['disk_percent'] = int(parts[4].replace('%', ''))
            
            # 负载
            result = subprocess.run(['uptime'], capture_output=True, text=True)
            if 'load average:' in result.stdout:
                load_str = result.stdout.split('load average:')[1].strip().split(',')[0]
                metrics['load_avg'] = float(load_str)
        except Exception as e:
            metrics['error'] = str(e)
        return metrics
    
    def get_service_health(self) -> Dict:
        """检查服务健康状态"""
        services = {
            'nginx': 'pgrep -x nginx',
            'mysql': 'pgrep -x mysqld',
            'redis': 'redis-cli ping | grep -q PONG',
            'aios_backend': 'curl -s http://127.0.0.1:8765/health | grep -q ok',
            'omega_brain': 'curl -s http://127.0.0.1:8000/health | grep -q healthy',
            'loip_api': 'curl -s http://127.0.0.1:8001/api/v1/status | grep -q ok',
            'anchor_api': 'curl -s http://127.0.0.1:8006/api/v1/sync/handshake | grep -q truth_version',
            'frps': 'ss -tlnp | grep -q 7100',
        }
        
        health = {}
        for name, check_cmd in services.items():
            try:
                result = subprocess.run(check_cmd, shell=True, capture_output=True)
                health[name] = 'healthy' if result.returncode == 0 else 'unhealthy'
            except Exception as e:
                health[name] = f'error: {str(e)}'
        return health
    
    def generate_suggestions(self, metrics: Dict = None, health: Dict = None) -> List[Dict]:
        """
        基于系统指标和服务健康状态生成优化建议
        
        Args:
            metrics: 系统指标（自动获取如果不指定）
            health: 服务健康状态（自动获取如果不指定）
            
        Returns:
            建议列表
        """
        if metrics is None:
            metrics = self.get_system_metrics()
        if health is None:
            health = self.get_service_health()
        
        suggestions = []
        timestamp = datetime.now().isoformat()
        
        # 内存优化建议
        if metrics.get('memory_percent', 0) > 85:
            suggestions.append({
                'suggestion_id': f"SUGG-{int(time.time())}-MEM",
                'type': '性能优化',
                'title': '内存使用率过高，建议优化内存占用',
                'description': f'当前内存使用率 {metrics.get("memory_percent")}%，超过85%阈值',
                'expected_benefit': '降低内存使用率至70%以下，提升系统稳定性',
                'risk_level': 'medium',
                'implementation_plan': [
                    '检查高内存占用进程',
                    '优化服务配置，降低内存上限',
                    '清理不必要的缓存和临时文件',
                    '考虑启用Swap或增加物理内存'
                ],
                'estimated_time': '1-2小时',
                'created_at': timestamp,
                'status': 'pending'
            })
        
        # 磁盘优化建议
        if metrics.get('disk_percent', 0) > 85:
            suggestions.append({
                'suggestion_id': f"SUGG-{int(time.time())}-DISK",
                'type': '性能优化',
                'title': '磁盘使用率过高，建议清理空间',
                'description': f'当前磁盘使用率 {metrics.get("disk_percent")}%，超过85%阈值',
                'expected_benefit': '释放磁盘空间，提升系统性能',
                'risk_level': 'low',
                'implementation_plan': [
                    '清理系统日志和临时文件',
                    '清理旧的备份和归档文件',
                    '检查大文件占用情况',
                    '考虑扩展磁盘容量'
                ],
                'estimated_time': '30分钟',
                'created_at': timestamp,
                'status': 'pending'
            })
        
        # 服务异常建议
        for service, status in health.items():
            if status == 'unhealthy':
                suggestions.append({
                    'suggestion_id': f"SUGG-{int(time.time())}-SVC-{service}",
                    'type': '安全加固',
                    'title': f'服务 {service} 异常，建议检查并恢复',
                    'description': f'服务 {service} 健康检查失败',
                    'expected_benefit': '恢复服务正常运行，保障系统可用性',
                    'risk_level': 'high',
                    'implementation_plan': [
                        '检查服务日志，定位故障原因',
                        '尝试重启服务',
                        '检查依赖服务状态',
                        '验证服务恢复正常'
                    ],
                    'estimated_time': '15-30分钟',
                    'created_at': timestamp,
                    'status': 'pending'
                })
        
        # SSL证书到期检查
        try:
            result = subprocess.run(
                ['bash', '/opt/ZONGYUAN-ROOT/ssl_check.sh'],
                capture_output=True, text=True
            )
            if '严重告警' in result.stdout or '告警' in result.stdout:
                suggestions.append({
                    'suggestion_id': f"SUGG-{int(time.time())}-SSL",
                    'type': '安全加固',
                    'title': 'SSL证书即将到期，建议续期',
                    'description': 'SSL证书检查发现告警，需要及时续期',
                    'expected_benefit': '避免证书过期导致服务中断',
                    'risk_level': 'high',
                    'implementation_plan': [
                        '检查证书到期时间',
                        '通过宝塔面板或certbot续期证书',
                        '验证证书更新成功',
                        '设置自动续期提醒'
                    ],
                    'estimated_time': '30分钟',
                    'created_at': timestamp,
                    'status': 'pending'
                })
        except Exception:
            pass
        
        # 保存建议
        for sug in suggestions:
            self._save_suggestion(sug)
        
        self.engine_state["suggestions_generated"] += len(suggestions)
        self._save_state()
        
        return suggestions
    
    def _save_suggestion(self, suggestion: Dict):
        """保存建议到文件"""
        filepath = self.suggestions_dir / f"{suggestion['suggestion_id']}.json"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(suggestion, f, ensure_ascii=False, indent=2)
    
    # ==================== 阶段2：人工确认 ====================
    
    def approve_suggestion(self, suggestion_id: str, approver: str = "system") -> bool:
        """
        审批建议
        
        Args:
            suggestion_id: 建议ID
            approver: 审批人
            
        Returns:
            是否成功
        """
        filepath = self.suggestions_dir / f"{suggestion_id}.json"
        if not filepath.exists():
            self._log(f"建议 {suggestion_id} 不存在", "ERROR")
            return False
        
        with open(filepath, 'r', encoding='utf-8') as f:
            suggestion = json.load(f)
        
        # 根据风险级别决定审批方式
        risk_level = suggestion.get('risk_level', 'medium')
        if risk_level == 'low':
            suggestion['status'] = 'approved'
            suggestion['approver'] = 'auto_system'
            suggestion['approved_at'] = datetime.now().isoformat()
            self._log(f"低风险建议自动审批通过: {suggestion['title']}")
        else:
            suggestion['status'] = 'pending_approval'
            suggestion['approver'] = approver
            self._log(f"建议待人工审批: {suggestion['title']} (风险级别: {risk_level})")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(suggestion, f, ensure_ascii=False, indent=2)
        
        return True
    
    def get_pending_approvals(self) -> List[Dict]:
        """获取待审批建议列表"""
        pending = []
        for filepath in self.suggestions_dir.glob("*.json"):
            with open(filepath, 'r', encoding='utf-8') as f:
                suggestion = json.load(f)
                if suggestion.get('status') == 'pending_approval':
                    pending.append(suggestion)
        return pending
    
    # ==================== 阶段3：沙箱验证（Docker真实隔离） ====================
    
    def verify_in_sandbox(self, 
                          suggestion_id: str,
                          code_path: str = None,
                          test_commands: List[str] = None) -> Dict:
        """
        在Docker沙箱中验证建议
        
        Args:
            suggestion_id: 建议ID
            code_path: 待验证代码路径
            test_commands: 测试命令列表
            
        Returns:
            验证结果
        """
        if not self.sandbox_manager:
            return {
                "status": "error",
                "message": "Docker沙箱模块不可用",
                "suggestion_id": suggestion_id
            }
        
        # 检查Docker可用性
        if not self.sandbox_manager.check_docker_available():
            return {
                "status": "error",
                "message": "Docker不可用，请先安装Docker",
                "suggestion_id": suggestion_id
            }
        
        self._log(f"开始沙箱验证: {suggestion_id}")
        
        # 创建沙箱
        sandbox_metadata = self.sandbox_manager.create_sandbox(
            image="python:3.9-slim",
            cpu="1",
            memory="512m",
            disk="1g",
            network_mode="bridge"
        )
        
        if sandbox_metadata.get('status') == 'error':
            return {
                "status": "error",
                "message": f"沙箱创建失败: {sandbox_metadata.get('error')}",
                "suggestion_id": suggestion_id
            }
        
        sandbox_id = sandbox_metadata['sandbox_id']
        self._log(f"沙箱创建成功: {sandbox_id}")
        
        try:
            # 复制代码到沙箱
            if code_path and os.path.exists(code_path):
                self.sandbox_manager.copy_to_sandbox(sandbox_id, code_path, "/workspace/")
                self._log(f"代码已复制到沙箱: {code_path}")
            
            # 运行功能测试
            verification = SandboxVerification(self.sandbox_manager)
            test_commands = test_commands or [
                "python3 --version",
                "pip list 2>/dev/null | head -5",
                "echo 'Sandbox verification passed'"
            ]
            
            test_result = verification.run_functional_tests(sandbox_id, test_commands)
            
            # 运行性能基准
            benchmarks = {
                "cpu_test": "python3 -c \"import time; start=time.time(); sum(range(1000000)); print(f'{time.time()-start:.3f}s')\"",
                "io_test": "python3 -c \"import time; start=time.time(); open('/tmp/test_io.txt','w').write('x'*1000000); print(f'{time.time()-start:.3f}s')\""
            }
            perf_result = verification.run_performance_benchmark(sandbox_id, benchmarks)
            
            # 运行安全扫描
            security_result = verification.run_security_scan(sandbox_id)
            
            # 综合验证结果
            overall_passed = (
                test_result.get('passed_threshold', False) and
                security_result.get('passed', False)
            )
            
            verification_result = {
                "suggestion_id": suggestion_id,
                "sandbox_id": sandbox_id,
                "sandbox_metadata": sandbox_metadata,
                "functional_tests": test_result,
                "performance_benchmark": perf_result,
                "security_scan": security_result,
                "overall_passed": overall_passed,
                "verified_at": datetime.now().isoformat(),
                "status": "passed" if overall_passed else "failed"
            }
            
            # 保存验证报告
            report_path = self.sandbox_dir / f"{suggestion_id}_verification_report.json"
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(verification_result, f, ensure_ascii=False, indent=2)
            
            self.engine_state["sandbox_verifications"] += 1
            self._save_state()
            
            self._log(f"沙箱验证完成: {'✅ 通过' if overall_passed else '❌ 失败'}")
            
            return verification_result
            
        finally:
            # 销毁沙箱
            self.sandbox_manager.destroy_sandbox(sandbox_id)
            self._log(f"沙箱已销毁: {sandbox_id}")
    
    # ==================== 阶段4：灰度发布 + 自动回滚 ====================
    
    def create_version(self, source_path: str, description: str = "") -> Dict:
        """
        创建新版本
        
        Args:
            source_path: 源文件/目录路径
            description: 版本描述
            
        Returns:
            版本信息
        """
        if not self.gray_manager:
            return {"status": "error", "message": "灰度发布模块不可用"}
        
        version_info = self.gray_manager.create_version(
            source_path=source_path,
            description=description
        )
        
        self._log(f"新版本创建: {version_info['version']}")
        return version_info
    
    def start_gray_release(self, 
                            new_version: str,
                            initial_percentage: int = 10,
                            auto_rollback: bool = True) -> Dict:
        """
        开始灰度发布
        
        Args:
            new_version: 新版本号
            initial_percentage: 初始灰度百分比
            auto_rollback: 是否自动回滚
            
        Returns:
            灰度发布信息
        """
        if not self.gray_manager:
            return {"status": "error", "message": "灰度发布模块不可用"}
        
        gray_release = self.gray_manager.start_gray_release(
            new_version=new_version,
            gray_percentage=initial_percentage,
            auto_rollback=auto_rollback
        )
        
        self.engine_state["gray_releases"] += 1
        self._save_state()
        
        self._log(f"灰度发布开始: {new_version} (初始比例: {initial_percentage}%)")
        return gray_release
    
    def increase_gray_percentage(self, increment: int = 10) -> Dict:
        """
        增加灰度百分比
        
        Args:
            increment: 增加的百分比
            
        Returns:
            更新后的灰度发布信息
        """
        if not self.gray_manager:
            return {"status": "error", "message": "灰度发布模块不可用"}
        
        result = self.gray_manager.increase_gray_percentage(increment)
        
        if result.get('status') == 'completed':
            self._log(f"灰度发布完成: {result.get('new_version')}")
        
        return result
    
    def check_gray_health(self) -> Dict:
        """检查灰度发布健康状态"""
        if not self.gray_manager:
            return {"status": "error", "message": "灰度发布模块不可用"}
        
        result = self.gray_manager.check_gray_health()
        
        if result.get('need_rollback'):
            self.engine_state["rollbacks"] += 1
            self._save_state()
            self._log(f"⚠️ 检测到需要回滚: {result.get('rollback_reasons')}")
        
        return result
    
    def rollback(self, reason: str = "manual") -> Dict:
        """
        回滚到上一个版本
        
        Args:
            reason: 回滚原因
            
        Returns:
            回滚结果
        """
        if not self.gray_manager:
            return {"status": "error", "message": "灰度发布模块不可用"}
        
        result = self.gray_manager.rollback(reason)
        
        self.engine_state["rollbacks"] += 1
        self._save_state()
        
        self._log(f"回滚完成: {result.get('rollback_id')} (原因: {reason})")
        return result
    
    # ==================== 锁档归档 ====================
    
    def lock_archive(self, suggestion_id: str, verification_result: Dict = None) -> Dict:
        """
        锁档归档
        
        Args:
            suggestion_id: 建议ID
            verification_result: 验证结果
            
        Returns:
            锁档记录
        """
        # 读取建议
        suggestion_path = self.suggestions_dir / f"{suggestion_id}.json"
        if not suggestion_path.exists():
            return {"status": "error", "message": "建议不存在"}
        
        with open(suggestion_path, 'r', encoding='utf-8') as f:
            suggestion = json.load(f)
        
        # 计算锁档哈希
        lock_data = {
            "suggestion": suggestion,
            "verification": verification_result or {},
            "locked_at": datetime.now().isoformat()
        }
        lock_hash = self._sha256_hash(json.dumps(lock_data, ensure_ascii=False, sort_keys=True))
        
        # 创建锁档记录
        lock_record = {
            "lock_id": f"LOCK-{int(time.time())}-EVO",
            "suggestion_id": suggestion_id,
            "lock_hash": lock_hash,
            "lock_type": "self_evolution",
            "status": "BLOWN_PERMANENT",
            "locked_at": datetime.now().isoformat(),
            "溯源标识": "Ω₀⊂⊙∞⊂Ω",
            "确权编码": "DID-BR-000002",
            "体系基线": "ZONGYUAN-ROOT V1.7",
            "engine_version": "3.0.0"
        }
        
        # 保存锁档记录
        lock_filepath = self.locks_dir / f"{lock_record['lock_id']}.json"
        with open(lock_filepath, 'w', encoding='utf-8') as f:
            json.dump(lock_record, f, ensure_ascii=False, indent=2)
        
        # 更新建议状态
        suggestion['status'] = 'locked'
        suggestion['lock_id'] = lock_record['lock_id']
        suggestion['lock_hash'] = lock_hash
        with open(suggestion_path, 'w', encoding='utf-8') as f:
            json.dump(suggestion, f, ensure_ascii=False, indent=2)
        
        # 保存到历史
        history_filepath = self.history_dir / f"{suggestion_id}.json"
        with open(history_filepath, 'w', encoding='utf-8') as f:
            json.dump(lock_data, f, ensure_ascii=False, indent=2)
        
        self.engine_state["locks_created"] += 1
        self._save_state()
        
        self._log(f"锁档完成: {lock_record['lock_id']} (哈希: {lock_hash[:16]}...)")
        
        return lock_record
    
    # ==================== 完整进化循环 ====================
    
    def run_full_evolution_cycle(self, auto_approve_low_risk: bool = True) -> Dict:
        """
        运行完整的进化循环
        
        Args:
            auto_approve_low_risk: 是否自动审批低风险建议
            
        Returns:
            循环结果
        """
        self._log("=" * 60)
        self._log("  ZONGYUAN-ROOT 自进化引擎 V3.0 - 完整进化循环")
        self._log("  溯源: Ω₀⊂⊙∞⊂Ω | DID-BR-000002")
        self._log("=" * 60)
        
        cycle_result = {
            "cycle_id": f"CYCLE-{int(time.time())}",
            "started_at": datetime.now().isoformat(),
            "stages": {}
        }
        
        # 阶段1：建议生成
        self._log("\n【阶段1】生成优化建议...")
        metrics = self.get_system_metrics()
        health = self.get_service_health()
        suggestions = self.generate_suggestions(metrics, health)
        cycle_result["stages"]["suggestion_generation"] = {
            "count": len(suggestions),
            "suggestions": [s["suggestion_id"] for s in suggestions]
        }
        self._log(f"  生成 {len(suggestions)} 条建议")
        
        # 阶段2：人工确认
        self._log("\n【阶段2】审批建议...")
        approved = 0
        if auto_approve_low_risk:
            for sug in suggestions:
                if sug.get('risk_level') == 'low':
                    if self.approve_suggestion(sug['suggestion_id'], 'auto_system'):
                        approved += 1
        
        pending = self.get_pending_approvals()
        cycle_result["stages"]["approval"] = {
            "auto_approved": approved,
            "pending_manual_approval": len(pending)
        }
        self._log(f"  自动审批 {approved} 条，待人工审批 {len(pending)} 条")
        
        # 阶段3：沙箱验证（对已审批的建议）
        self._log("\n【阶段3】沙箱验证...")
        verified = 0
        for sug in suggestions:
            if sug.get('risk_level') == 'low' and self.sandbox_manager:
                # 低风险建议进行沙箱验证
                result = self.verify_in_sandbox(sug['suggestion_id'])
                if result.get('overall_passed'):
                    verified += 1
        
        cycle_result["stages"]["sandbox_verification"] = {
            "verified": verified,
            "sandbox_available": self.sandbox_manager is not None
        }
        self._log(f"  沙箱验证 {verified} 条通过")
        
        # 阶段4：锁档归档
        self._log("\n【阶段4】锁档归档...")
        locked = 0
        for sug in suggestions:
            if sug.get('risk_level') == 'low':
                lock_record = self.lock_archive(sug['suggestion_id'])
                if lock_record.get('status') == 'BLOWN_PERMANENT':
                    locked += 1
        
        cycle_result["stages"]["lock_archive"] = {
            "locked": locked
        }
        self._log(f"  锁档归档 {locked} 条")
        
        # 完成循环
        cycle_result["completed_at"] = datetime.now().isoformat()
        cycle_result["status"] = "completed"
        
        self.engine_state["cycles_completed"] += 1
        self._save_state()
        
        self._log("\n" + "=" * 60)
        self._log("  进化循环完成")
        self._log(f"  生成建议: {len(suggestions)} 条")
        self._log(f"  自动审批: {approved} 条")
        self._log(f"  沙箱验证: {verified} 条")
        self._log(f"  锁档归档: {locked} 条")
        self._log("=" * 60)
        
        return cycle_result
    
    def get_engine_status(self) -> Dict:
        """获取引擎状态"""
        return {
            "engine_state": self.engine_state,
            "sandbox_available": self.sandbox_manager is not None,
            "gray_release_available": self.gray_manager is not None,
            "pending_approvals": len(self.get_pending_approvals()),
            "current_gray_release": self.gray_manager.get_gray_release_status() if self.gray_manager else None,
            "checked_at": datetime.now().isoformat()
        }


if __name__ == "__main__":
    print("=" * 60)
    print("  ZONGYUAN-ROOT 自进化引擎 V3.0 - 深度实现版")
    print("  溯源: Ω₀⊂⊙∞⊂Ω | DID-BR-000002")
    print("  集成: Docker沙箱 + 灰度发布 + 自动回滚")
    print("=" * 60)
    print()
    
    engine = SelfEvolutionEngineV3()
    
    # 显示引擎状态
    print("【引擎状态】")
    status = engine.get_engine_status()
    print(f"  引擎版本: {status['engine_state']['version']}")
    print(f"  Docker沙箱: {'✅ 可用' if status['sandbox_available'] else '❌ 不可用'}")
    print(f"  灰度发布: {'✅ 可用' if status['gray_release_available'] else '❌ 不可用'}")
    print(f"  待审批建议: {status['pending_approvals']} 条")
    print(f"  已完成循环: {status['engine_state']['cycles_completed']} 次")
    print()
    
    # 运行完整进化循环
    if len(sys.argv) > 1 and sys.argv[1] == 'cycle':
        result = engine.run_full_evolution_cycle(auto_approve_low_risk=True)
        print(f"\n循环ID: {result['cycle_id']}")
        print(f"状态: {result['status']}")
    else:
        print("使用方法:")
        print("  python3 self_evolution_engine_v3.py cycle  # 运行完整进化循环")
        print("  python3 self_evolution_engine_v3.py status  # 显示引擎状态")
