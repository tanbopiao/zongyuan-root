"""
火斗云智AIOS - 自治Windows服务
以LocalSystem权限运行，提供高权限操作API
绕过UAC，实现零人工介入的系统级优化
"""
import os
import sys
import json
import time
import logging
import subprocess
import win32serviceutil
import win32service
import win32event
import servicemanager
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

# 配置
SERVICE_NAME = "AIOSAutonomousService"
SERVICE_DISPLAY_NAME = "火斗云智AIOS自治服务"
SERVICE_DESCRIPTION = "AIOS完全自治优化服务，以System权限运行，提供高权限系统操作API"
API_HOST = "127.0.0.1"
API_PORT = 9150
LOG_FILE = r"C:\Users\4906\.zongyuan_root\logs\aios_autonomous_service.log"
BACKUP_DIR = r"C:\Users\4906\.zongyuan_root\backups\autonomous"

# 确保日志目录存在
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
os.makedirs(BACKUP_DIR, exist_ok=True)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# L4黑名单 - 任何情况下都不执行
L4_BLACKLIST = [
    "bcdedit", "bootcfg",
    r"C:\\Windows\\System32", r"C:\\Windows\\WinSxS",
    "DISM /ResetBase",
    "sc stop RpcSs", "sc stop DcomLaunch", "sc stop PlugPlay",
    "sc stop Winmgmt", "sc stop Power", "sc stop CryptSvc",
    "sc stop EventLog", "sc stop Schedule", "sc stop BFE",
    "sc stop WinDefend",
    "taskkill /f /im csrss.exe", "taskkill /f /im wininit.exe",
    "taskkill /f /im winlogon.exe", "taskkill /f /im services.exe",
    "taskkill /f /im lsass.exe", "taskkill /f /im smss.exe",
    "taskkill /f /im svchost.exe", "taskkill /f /im dwm.exe",
    "taskkill /f /im MsMpEng.exe",
    "del /f /q C:\\Windows\\System32",
    "rmdir /s /q C:\\Windows",
    "reg delete HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run /va /f",
    "format c:",
]

def is_l4_blacklisted(command):
    """检查是否在L4黑名单中"""
    command_lower = command.lower()
    for blacklist_item in L4_BLACKLIST:
        if blacklist_item.lower() in command_lower:
            return True
    return False

class APIRequestHandler(BaseHTTPRequestHandler):
    """API请求处理器"""
    
    def _send_json_response(self, status_code, data):
        """发送JSON响应"""
        response = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(response)))
        self.end_headers()
        self.wfile.write(response)
    
    def do_GET(self):
        """处理GET请求"""
        if self.path == '/api/health':
            self._send_json_response(200, {
                "status": "ok",
                "service": SERVICE_NAME,
                "version": "1.0.0",
                "privilege": "LocalSystem",
                "timestamp": datetime.now().isoformat()
            })
        elif self.path == '/api/status':
            self._send_json_response(200, {
                "status": "running",
                "uptime": time.time() - self.server.start_time,
                "requests_handled": self.server.request_count,
                "backup_dir": BACKUP_DIR
            })
        else:
            self._send_json_response(404, {"error": "Not found"})
    
    def do_POST(self):
        """处理POST请求"""
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data.decode('utf-8'))
        except:
            self._send_json_response(400, {"error": "Invalid JSON"})
            return
        
        self.server.request_count += 1
        
        if self.path == '/api/execute':
            self._handle_execute(data)
        elif self.path == '/api/backup':
            self._handle_backup(data)
        elif self.path == '/api/rollback':
            self._handle_rollback(data)
        elif self.path == '/api/registry/backup':
            self._handle_registry_backup(data)
        elif self.path == '/api/registry/restore':
            self._handle_registry_restore(data)
        elif self.path == '/api/service/control':
            self._handle_service_control(data)
        else:
            self._send_json_response(404, {"error": "Not found"})
    
    def _handle_execute(self, data):
        """处理命令执行请求"""
        command = data.get('command', '')
        timeout = data.get('timeout', 300)
        need_backup = data.get('need_backup', False)
        operation_type = data.get('operation_type', 'generic')
        targets = data.get('targets', [])
        
        logger.info(f"执行请求: {command[:100]}...")
        
        # L4黑名单检查
        if is_l4_blacklisted(command):
            logger.warning(f"拒绝执行L4黑名单命令: {command[:100]}")
            self._send_json_response(403, {
                "success": False,
                "error": "命令在L4黑名单中，禁止自动执行",
                "command_preview": command[:200]
            })
            return
        
        # 自动备份
        backup_record = None
        if need_backup:
            backup_record = self._perform_backup(operation_type, targets)
        
        # 执行命令
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding='gbk',
                errors='replace'
            )
            
            self._send_json_response(200, {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout[:5000],
                "stderr": result.stderr[:5000],
                "backup_record": backup_record
            })
        except subprocess.TimeoutExpired:
            self._send_json_response(408, {
                "success": False,
                "error": f"命令执行超时（{timeout}秒）"
            })
        except Exception as e:
            self._send_json_response(500, {
                "success": False,
                "error": str(e)
            })
    
    def _perform_backup(self, operation_type, targets):
        """执行备份"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_id = f"{operation_type}_{timestamp}"
        backup_path = os.path.join(BACKUP_DIR, backup_id)
        os.makedirs(backup_path, exist_ok=True)
        
        backup_record = {
            "backup_id": backup_id,
            "operation_type": operation_type,
            "targets": targets,
            "backup_path": backup_path,
            "timestamp": datetime.now().isoformat()
        }
        
        # 根据类型执行备份
        try:
            if operation_type == 'registry':
                for target in targets:
                    safe_name = target.replace('\\', '_').replace(':', '')
                    reg_file = os.path.join(backup_path, f"{safe_name}.reg")
                    subprocess.run(f'reg export "{target}" "{reg_file}" /y', 
                                 shell=True, capture_output=True, timeout=30)
            elif operation_type == 'service':
                services_file = os.path.join(backup_path, "services_before.xml")
                subprocess.run(f'sc query type= service state= all > "{services_file}"',
                             shell=True, capture_output=True, timeout=30)
            elif operation_type == 'startup':
                startup_file = os.path.join(backup_path, "startup_backup.json")
                # 备份启动项
                startup_data = {}
                try:
                    result = subprocess.run('reg query "HKCU\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run"',
                                          shell=True, capture_output=True, text=True, encoding='gbk')
                    startup_data['hkcu_run'] = result.stdout
                except:
                    pass
                with open(startup_file, 'w', encoding='utf-8') as f:
                    json.dump(startup_data, f, ensure_ascii=False, indent=2)
            
            backup_record["success"] = True
        except Exception as e:
            backup_record["success"] = False
            backup_record["error"] = str(e)
        
        # 保存备份记录
        record_file = os.path.join(backup_path, "backup_record.json")
        with open(record_file, 'w', encoding='utf-8') as f:
            json.dump(backup_record, f, ensure_ascii=False, indent=2)
        
        logger.info(f"备份完成: {backup_id}")
        return backup_record
    
    def _handle_backup(self, data):
        """处理备份请求"""
        operation_type = data.get('operation_type', 'generic')
        targets = data.get('targets', [])
        backup_record = self._perform_backup(operation_type, targets)
        self._send_json_response(200, backup_record)
    
    def _handle_rollback(self, data):
        """处理回滚请求"""
        backup_id = data.get('backup_id', '')
        backup_path = os.path.join(BACKUP_DIR, backup_id)
        
        if not os.path.exists(backup_path):
            self._send_json_response(404, {"error": f"备份不存在: {backup_id}"})
            return
        
        # 读取备份记录
        record_file = os.path.join(backup_path, "backup_record.json")
        try:
            with open(record_file, 'r', encoding='utf-8') as f:
                backup_record = json.load(f)
        except:
            self._send_json_response(500, {"error": "备份记录损坏"})
            return
        
        # 执行回滚
        try:
            operation_type = backup_record.get('operation_type', '')
            
            if operation_type == 'registry':
                for reg_file in os.listdir(backup_path):
                    if reg_file.endswith('.reg'):
                        full_path = os.path.join(backup_path, reg_file)
                        subprocess.run(f'reg import "{full_path}"',
                                     shell=True, capture_output=True, timeout=30)
            
            self._send_json_response(200, {
                "success": True,
                "backup_id": backup_id,
                "operation_type": operation_type,
                "message": "回滚完成"
            })
        except Exception as e:
            self._send_json_response(500, {
                "success": False,
                "error": str(e)
            })
    
    def _handle_registry_backup(self, data):
        """处理注册表备份"""
        key_path = data.get('key_path', '')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = key_path.replace('\\', '_').replace(':', '')
        reg_file = os.path.join(BACKUP_DIR, f"registry_{safe_name}_{timestamp}.reg")
        
        try:
            result = subprocess.run(
                f'reg export "{key_path}" "{reg_file}" /y',
                shell=True, capture_output=True, text=True, timeout=30
            )
            self._send_json_response(200, {
                "success": result.returncode == 0,
                "backup_file": reg_file
            })
        except Exception as e:
            self._send_json_response(500, {"success": False, "error": str(e)})
    
    def _handle_registry_restore(self, data):
        """处理注册表恢复"""
        reg_file = data.get('reg_file', '')
        
        if not os.path.exists(reg_file):
            self._send_json_response(404, {"error": f"文件不存在: {reg_file}"})
            return
        
        try:
            result = subprocess.run(
                f'reg import "{reg_file}"',
                shell=True, capture_output=True, text=True, timeout=30
            )
            self._send_json_response(200, {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr
            })
        except Exception as e:
            self._send_json_response(500, {"success": False, "error": str(e)})
    
    def _handle_service_control(self, data):
        """处理服务控制"""
        service_name = data.get('service_name', '')
        action = data.get('action', 'status')  # start/stop/restart/status
        
        # L4关键服务保护
        critical_services = ['RpcSs', 'DcomLaunch', 'PlugPlay', 'Winmgmt', 
                           'Power', 'CryptSvc', 'EventLog', 'Schedule', 
                           'BFE', 'WinDefend']
        
        if service_name in critical_services and action in ['stop', 'restart']:
            self._send_json_response(403, {
                "success": False,
                "error": f"关键服务 {service_name} 禁止自动停止/重启"
            })
            return
        
        try:
            if action == 'start':
                result = subprocess.run(f'net start "{service_name}"',
                                      shell=True, capture_output=True, text=True, timeout=30)
            elif action == 'stop':
                result = subprocess.run(f'net stop "{service_name}"',
                                      shell=True, capture_output=True, text=True, timeout=30)
            elif action == 'restart':
                subprocess.run(f'net stop "{service_name}"',
                             shell=True, capture_output=True, timeout=30)
                time.sleep(2)
                result = subprocess.run(f'net start "{service_name}"',
                                      shell=True, capture_output=True, text=True, timeout=30)
            else:  # status
                result = subprocess.run(f'sc query "{service_name}"',
                                      shell=True, capture_output=True, text=True, timeout=10)
            
            self._send_json_response(200, {
                "success": result.returncode == 0,
                "action": action,
                "service": service_name,
                "output": result.stdout[:2000]
            })
        except Exception as e:
            self._send_json_response(500, {"success": False, "error": str(e)})
    
    def log_message(self, format, *args):
        """静默日志"""
        pass

class AIOSAutonomousService(win32serviceutil.ServiceFramework):
    """AIOS自治Windows服务"""
    
    _svc_name_ = SERVICE_NAME
    _svc_display_name_ = SERVICE_DISPLAY_NAME
    _svc_description_ = SERVICE_DESCRIPTION
    
    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.server = None
        self.server_thread = None
    
    def SvcStop(self):
        """服务停止"""
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        if self.server:
            self.server.shutdown()
        logger.info("AIOS自治服务已停止")
    
    def SvcDoRun(self):
        """服务运行"""
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        self.main()
    
    def main(self):
        """主函数"""
        logger.info("=" * 60)
        logger.info("火斗云智AIOS自治服务启动")
        logger.info(f"服务名称: {SERVICE_NAME}")
        logger.info(f"API地址: http://{API_HOST}:{API_PORT}")
        logger.info(f"备份目录: {BACKUP_DIR}")
        logger.info("=" * 60)
        
        # 启动API服务器
        self.server = HTTPServer((API_HOST, API_PORT), APIRequestHandler)
        self.server.start_time = time.time()
        self.server.request_count = 0
        
        logger.info(f"API服务器已启动: http://{API_HOST}:{API_PORT}")
        
        # 运行服务
        self.server.serve_forever()

if __name__ == '__main__':
    if len(sys.argv) > 1:
        # 命令行参数处理（安装/卸载/调试）
        if sys.argv[1] == 'install':
            win32serviceutil.HandleCommandLine(AIOSAutonomousService)
        elif sys.argv[1] == 'remove':
            win32serviceutil.HandleCommandLine(AIOSAutonomousService)
        elif sys.argv[1] == 'debug':
            # 调试模式（控制台运行）
            service = AIOSAutonomousService([])
            service.SvcDoRun()
        else:
            win32serviceutil.HandleCommandLine(AIOSAutonomousService)
    else:
        win32serviceutil.HandleCommandLine(AIOSAutonomousService)
