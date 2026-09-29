#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
火斗云智AIOS - 远程执行Worker
监听记忆网关指令，自动执行部署和优化任务
后台静默运行，无需人工干预
"""

import os
import sys
import json
import time
import logging
import subprocess
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

# 配置
WORKER_VERSION = "1.0.0"
WORKER_ID = "local-windows-001"
DID = "DID-BR-000002"
TRACE_MARK = "Ω₀⊂⊙∞⊂Ω"

# 记忆网关配置
MEMORY_GATEWAY_URL = "https://www.huodouai.com/api"
COMMAND_POLL_INTERVAL = 30  # 轮询指令间隔（秒）
HEARTBEAT_INTERVAL = 60    # 心跳间隔（秒）

# 工作目录
BASE_DIR = Path(__file__).parent.parent
CONFIG_DIR = BASE_DIR / "config"
LOG_DIR = BASE_DIR / "logs"
STATE_DIR = BASE_DIR / "state"
SCRIPT_DIR = BASE_DIR / "scripts"

# 确保目录存在
for d in [LOG_DIR, STATE_DIR, CONFIG_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "worker.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('RemoteWorker')


class RemoteWorker:
    """远程执行Worker"""
    
    def __init__(self):
        self.worker_id = WORKER_ID
        self.version = WORKER_VERSION
        self.running = False
        self.last_heartbeat = 0
        self.last_command_poll = 0
        self.command_queue: List[Dict] = []
        self.executing = False
        self.state_file = STATE_DIR / "worker_state.json"
        self.config_file = CONFIG_DIR / "worker_config.json"
        self.load_config()
        self.load_state()
        
    def load_config(self):
        """加载配置"""
        default_config = {
            "worker_id": WORKER_ID,
            "version": WORKER_VERSION,
            "did": DID,
            "trace_mark": TRACE_MARK,
            "memory_gateway_url": MEMORY_GATEWAY_URL,
            "command_poll_interval": COMMAND_POLL_INTERVAL,
            "heartbeat_interval": HEARTBEAT_INTERVAL,
            "auto_deploy": True,
            "auto_optimize": True,
            "allowed_commands": [
                "deploy_all",
                "install_service",
                "start_optimizer",
                "stop_optimizer",
                "verify_deployment",
                "uninstall_service",
                "run_optimization",
                "system_scan",
                "status_report",
                "restart_worker",
                "shutdown_worker"
            ],
            "l4_blacklist": [
                "format",
                "del C:\\Windows",
                "bcdedit",
                "shutdown /s",
                "restart /f"
            ]
        }
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config = {**default_config, **json.load(f)}
                logger.info("配置已加载")
            except Exception as e:
                logger.error(f"配置加载失败，使用默认配置: {e}")
                self.config = default_config
        else:
            self.config = default_config
            self.save_config()
            
    def save_config(self):
        """保存配置"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"配置保存失败: {e}")
            
    def load_state(self):
        """加载状态"""
        default_state = {
            "worker_id": self.worker_id,
            "status": "idle",
            "started_at": None,
            "last_heartbeat": None,
            "last_command": None,
            "commands_executed": 0,
            "commands_failed": 0,
            "current_task": None
        }
        
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    self.state = {**default_state, **json.load(f)}
            except Exception as e:
                logger.error(f"状态加载失败: {e}")
                self.state = default_state
        else:
            self.state = default_state
            
    def save_state(self):
        """保存状态"""
        try:
            self.state['last_heartbeat'] = datetime.now().isoformat()
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"状态保存失败: {e}")
            
    def send_heartbeat(self):
        """发送心跳到记忆网关"""
        try:
            heartbeat_data = {
                "worker_id": self.worker_id,
                "version": self.version,
                "did": self.config['did'],
                "trace_mark": self.config['trace_mark'],
                "status": self.state['status'],
                "timestamp": datetime.now().isoformat(),
                "system_info": self.get_system_info()
            }
            
            # 尝试发送心跳（网络可能不通时静默失败）
            try:
                import requests
                url = f"{self.config['memory_gateway_url']}/worker/heartbeat"
                response = requests.post(url, json=heartbeat_data, timeout=10)
                if response.status_code == 200:
                    logger.debug("心跳发送成功")
                else:
                    logger.debug(f"心跳发送失败: {response.status_code}")
            except Exception as e:
                logger.debug(f"心跳发送失败（网络可能不通）: {e}")
                
            self.last_heartbeat = time.time()
            self.save_state()
            
        except Exception as e:
            logger.error(f"心跳处理失败: {e}")
            
    def get_system_info(self) -> Dict:
        """获取系统信息"""
        try:
            import platform
            import psutil
            
            return {
                "os": platform.system(),
                "os_version": platform.version(),
                "hostname": platform.node(),
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_percent": psutil.virtual_memory().percent,
                "memory_available": psutil.virtual_memory().available // (1024*1024),
                "disk_usage": psutil.disk_usage('/').percent if os.path.exists('/') else 0
            }
        except Exception as e:
            return {"error": str(e)}
            
    def poll_commands(self) -> List[Dict]:
        """轮询记忆网关获取指令"""
        commands = []
        
        try:
            # 尝试从记忆网关获取指令
            try:
                import requests
                url = f"{self.config['memory_gateway_url']}/worker/commands"
                params = {
                    "worker_id": self.worker_id,
                    "did": self.config['did']
                }
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if 'commands' in data:
                        commands = data['commands']
                        logger.info(f"获取到 {len(commands)} 条指令")
            except Exception as e:
                logger.debug(f"指令获取失败（网络可能不通）: {e}")
                
            # 检查本地指令文件（备用通道）
            local_command_file = STATE_DIR / "pending_commands.json"
            if local_command_file.exists():
                try:
                    with open(local_command_file, 'r', encoding='utf-8') as f:
                        local_commands = json.load(f)
                        if isinstance(local_commands, list):
                            commands.extend(local_commands)
                            # 清空本地指令文件
                            local_command_file.unlink()
                            logger.info(f"从本地文件获取 {len(local_commands)} 条指令")
                except Exception as e:
                    logger.error(f"本地指令文件读取失败: {e}")
                    
        except Exception as e:
            logger.error(f"指令轮询失败: {e}")
            
        return commands
        
    def validate_command(self, command: Dict) -> bool:
        """验证指令合法性"""
        try:
            # 检查指令类型
            cmd_type = command.get('type', '')
            if cmd_type not in self.config['allowed_commands']:
                logger.warning(f"指令类型不在允许列表: {cmd_type}")
                return False
                
            # 检查L4黑名单
            cmd_content = json.dumps(command).lower()
            for blocked in self.config['l4_blacklist']:
                if blocked.lower() in cmd_content:
                    logger.warning(f"指令包含黑名单内容: {blocked}")
                    return False
                    
            # 检查指令签名（可选）
            if 'signature' in command:
                # TODO: 验证签名
                pass
                
            return True
            
        except Exception as e:
            logger.error(f"指令验证失败: {e}")
            return False
            
    def execute_command(self, command: Dict) -> Dict:
        """执行指令"""
        result = {
            "command_id": command.get('id', 'unknown'),
            "type": command.get('type', ''),
            "status": "pending",
            "started_at": datetime.now().isoformat(),
            "finished_at": None,
            "output": "",
            "error": "",
            "success": False
        }
        
        try:
            cmd_type = command.get('type', '')
            logger.info(f"开始执行指令: {cmd_type} (ID: {command.get('id')})")
            
            self.state['status'] = 'executing'
            self.state['current_task'] = command
            self.save_state()
            
            # 根据指令类型执行
            if cmd_type == 'deploy_all':
                result = self._execute_deploy_all(command, result)
            elif cmd_type == 'install_service':
                result = self._execute_install_service(command, result)
            elif cmd_type == 'start_optimizer':
                result = self._execute_start_optimizer(command, result)
            elif cmd_type == 'stop_optimizer':
                result = self._execute_stop_optimizer(command, result)
            elif cmd_type == 'verify_deployment':
                result = self._execute_verify_deployment(command, result)
            elif cmd_type == 'run_optimization':
                result = self._execute_run_optimization(command, result)
            elif cmd_type == 'system_scan':
                result = self._execute_system_scan(command, result)
            elif cmd_type == 'status_report':
                result = self._execute_status_report(command, result)
            elif cmd_type == 'restart_worker':
                result = self._execute_restart_worker(command, result)
            elif cmd_type == 'shutdown_worker':
                result = self._execute_shutdown_worker(command, result)
            else:
                result['error'] = f"未知指令类型: {cmd_type}"
                result['status'] = 'failed'
                
            result['finished_at'] = datetime.now().isoformat()
            result['success'] = result['status'] == 'success'
            
            # 更新统计
            if result['success']:
                self.state['commands_executed'] += 1
            else:
                self.state['commands_failed'] += 1
                
            self.state['status'] = 'idle'
            self.state['current_task'] = None
            self.state['last_command'] = command
            self.save_state()
            
            # 上报执行结果
            self._report_result(result)
            
            logger.info(f"指令执行完成: {cmd_type} - 成功: {result['success']}")
            
        except Exception as e:
            result['error'] = str(e)
            result['status'] = 'failed'
            result['finished_at'] = datetime.now().isoformat()
            logger.error(f"指令执行异常: {e}")
            
        return result
        
    def _run_script(self, script_name: str, timeout: int = 300) -> tuple:
        """运行脚本"""
        script_path = SCRIPT_DIR / script_name
        if not script_path.exists():
            return False, f"脚本不存在: {script_path}", ""
            
        try:
            # 使用cmd运行批处理脚本
            result = subprocess.run(
                ['cmd', '/c', str(script_path)],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(SCRIPT_DIR)
            )
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", "执行超时"
        except Exception as e:
            return False, "", str(e)
            
    def _execute_deploy_all(self, command: Dict, result: Dict) -> Dict:
        """执行一键部署"""
        result['status'] = 'running'
        success, output, error = self._run_script('deploy_all.bat', timeout=600)
        result['output'] = output
        result['error'] = error
        result['status'] = 'success' if success else 'failed'
        return result
        
    def _execute_install_service(self, command: Dict, result: Dict) -> Dict:
        """执行安装服务"""
        result['status'] = 'running'
        success, output, error = self._run_script('install_service.bat', timeout=300)
        result['output'] = output
        result['error'] = error
        result['status'] = 'success' if success else 'failed'
        return result
        
    def _execute_start_optimizer(self, command: Dict, result: Dict) -> Dict:
        """执行启动优化器"""
        result['status'] = 'running'
        success, output, error = self._run_script('start_optimizer.bat', timeout=120)
        result['output'] = output
        result['error'] = error
        result['status'] = 'success' if success else 'failed'
        return result
        
    def _execute_stop_optimizer(self, command: Dict, result: Dict) -> Dict:
        """执行停止优化器"""
        result['status'] = 'running'
        success, output, error = self._run_script('stop_optimizer.bat', timeout=120)
        result['output'] = output
        result['error'] = error
        result['status'] = 'success' if success else 'failed'
        return result
        
    def _execute_verify_deployment(self, command: Dict, result: Dict) -> Dict:
        """执行验证部署"""
        result['status'] = 'running'
        success, output, error = self._run_script('verify_deployment.bat', timeout=120)
        result['output'] = output
        result['error'] = error
        result['status'] = 'success' if success else 'failed'
        return result
        
    def _execute_run_optimization(self, command: Dict, result: Dict) -> Dict:
        """执行运行优化"""
        result['status'] = 'running'
        # 调用自治优化器执行一次优化
        try:
            optimizer_path = SCRIPT_DIR.parent / "aios_autonomous" / "autonomous_optimizer_v2.py"
            if optimizer_path.exists():
                proc = subprocess.run(
                    ['python', str(optimizer_path), '--mode', 'single'],
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                result['output'] = proc.stdout
                result['error'] = proc.stderr
                result['status'] = 'success' if proc.returncode == 0 else 'failed'
            else:
                result['error'] = "优化器程序不存在"
                result['status'] = 'failed'
        except Exception as e:
            result['error'] = str(e)
            result['status'] = 'failed'
        return result
        
    def _execute_system_scan(self, command: Dict, result: Dict) -> Dict:
        """执行系统扫描"""
        result['status'] = 'running'
        result['output'] = json.dumps(self.get_system_info(), ensure_ascii=False, indent=2)
        result['status'] = 'success'
        return result
        
    def _execute_status_report(self, command: Dict, result: Dict) -> Dict:
        """执行状态报告"""
        result['status'] = 'running'
        status = {
            "worker_id": self.worker_id,
            "version": self.version,
            "status": self.state['status'],
            "started_at": self.state['started_at'],
            "last_heartbeat": self.state['last_heartbeat'],
            "commands_executed": self.state['commands_executed'],
            "commands_failed": self.state['commands_failed'],
            "system_info": self.get_system_info()
        }
        result['output'] = json.dumps(status, ensure_ascii=False, indent=2)
        result['status'] = 'success'
        return result
        
    def _execute_restart_worker(self, command: Dict, result: Dict) -> Dict:
        """执行重启Worker"""
        result['status'] = 'success'
        result['output'] = "Worker将在3秒后重启"
        # 延迟重启
        threading.Timer(3, self._restart).start()
        return result
        
    def _execute_shutdown_worker(self, command: Dict, result: Dict) -> Dict:
        """执行关闭Worker"""
        result['status'] = 'success'
        result['output'] = "Worker将在3秒后关闭"
        threading.Timer(3, self._shutdown).start()
        return result
        
    def _restart(self):
        """重启Worker"""
        logger.info("Worker重启中...")
        python = sys.executable
        os.execl(python, python, *sys.argv)
        
    def _shutdown(self):
        """关闭Worker"""
        logger.info("Worker关闭中...")
        self.running = False
        
    def _report_result(self, result: Dict):
        """上报执行结果到记忆网关"""
        try:
            report_data = {
                "worker_id": self.worker_id,
                "did": self.config['did'],
                "trace_mark": self.config['trace_mark'],
                "result": result,
                "timestamp": datetime.now().isoformat()
            }
            
            try:
                import requests
                url = f"{self.config['memory_gateway_url']}/worker/result"
                response = requests.post(url, json=report_data, timeout=10)
                if response.status_code == 200:
                    logger.debug("结果上报成功")
                else:
                    logger.debug(f"结果上报失败: {response.status_code}")
            except Exception as e:
                logger.debug(f"结果上报失败（网络可能不通）: {e}")
                
            # 保存到本地结果文件（备用）
            result_file = STATE_DIR / f"result_{result['command_id']}_{int(time.time())}.json"
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"结果上报处理失败: {e}")
            
    def run(self):
        """运行Worker主循环"""
        logger.info("=" * 60)
        logger.info(f"火斗云智AIOS - 远程执行Worker v{WORKER_VERSION}")
        logger.info(f"Worker ID: {self.worker_id}")
        logger.info(f"DID: {DID}")
        logger.info(f"溯源: {TRACE_MARK}")
        logger.info("=" * 60)
        
        self.running = True
        self.state['started_at'] = datetime.now().isoformat()
        self.state['status'] = 'running'
        self.save_state()
        
        # 启动时发送一次心跳
        self.send_heartbeat()
        
        logger.info("Worker已启动，进入主循环")
        logger.info(f"指令轮询间隔: {self.config['command_poll_interval']}秒")
        logger.info(f"心跳间隔: {self.config['heartbeat_interval']}秒")
        
        try:
            while self.running:
                current_time = time.time()
                
                # 心跳
                if current_time - self.last_heartbeat >= self.config['heartbeat_interval']:
                    self.send_heartbeat()
                    
                # 轮询指令
                if current_time - self.last_command_poll >= self.config['command_poll_interval']:
                    if not self.executing:
                        commands = self.poll_commands()
                        for cmd in commands:
                            if self.validate_command(cmd):
                                self.executing = True
                                result = self.execute_command(cmd)
                                self.executing = False
                            else:
                                logger.warning(f"指令验证失败，已拒绝: {cmd.get('id')}")
                    self.last_command_poll = current_time
                    
                # 休眠
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("收到中断信号，Worker停止中...")
        except Exception as e:
            logger.error(f"Worker主循环异常: {e}")
        finally:
            self.state['status'] = 'stopped'
            self.save_state()
            logger.info("Worker已停止")


def main():
    """主函数"""
    worker = RemoteWorker()
    worker.run()


if __name__ == "__main__":
    main()
