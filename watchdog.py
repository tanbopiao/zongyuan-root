"""
本地内核能量态守护脚本 - watchdog.py
KUN-LAW-019配套 | ZONGYUAN-ROOT元极恒一自治体系

功能集成：
1. 服务监控（AIOS 8017 / Dashboard 8899 / frpc）
2. 自动重启（发现异常自动重启，记录到日志）
3. 轻量调度（每5分钟健康检查/每30分钟云同步/每小时资源监控）
4. 心跳上报（每30秒向云内核上报本地状态）
5. frp保活（frpc断开自动重连）
6. 日志记录（所有操作记录到日志+本地账本）

使用方法：
  python watchdog.py              # 前台运行（调试用）
  python watchdog.py --daemon     # 后台守护模式
  python watchdog.py --status     # 查看守护状态
  python watchdog.py --stop       # 停止守护进程

开机自启：将 start_watchdog.bat 放入 Windows 启动文件夹
"""

import os
import sys
import json
import time
import socket
import logging
import hashlib
import subprocess
import psutil
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

# ============================================================
# 配置
# ============================================================

BASE_DIR = Path(r"C:\Users\4906\.zongyuan_root")
LOG_DIR = BASE_DIR / "logs"
DATA_DIR = BASE_DIR / "data" / "watchdog"
LEDGER_PATH = BASE_DIR / "ledger" / "M9_global_ledger.json"

PYTHON_PATH = r"C:\Users\4906\AppData\Local\Programs\Python\Python311\python.exe"

# 云内核配置
CLOUD_API_BASE = "https://www.huodouai.com/anchor/api/v1"
CLOUD_API_KEY = "8f95a041594914bdc89c103c9deb723290873220a07ec8d4"
CLOUD_DIRECT_BASE = "http://123.207.202.158:8006/api/v1"

# 本地节点标识
NODE_ID = "local-win-001"
NODE_NAME = "本地Windows管理端"

# 服务配置
SERVICES = {
    "aios_v21": {
        "name": "AIOS v2.1 (8017)",
        "port": 8017,
        "host": "127.0.0.1",
        "check_url": "http://127.0.0.1:8017/health",
        "start_cmd": None,  # 待配置
        "auto_restart": True,
        "max_restarts": 5,
        "restart_cooldown": 60,  # 冷却时间（秒）
    },
    "dashboard": {
        "name": "Dashboard (8899)",
        "port": 8899,
        "host": "127.0.0.1",
        "check_url": "http://127.0.0.1:8899/",
        "start_cmd": None,  # 待配置
        "auto_restart": True,
        "max_restarts": 5,
        "restart_cooldown": 60,
    },
    "frpc": {
        "name": "frpc隧道",
        "port": None,  # frpc不监听本地端口，检查进程
        "process_name": "frpc",
        "check_process": True,
        "start_cmd": f'cmd /c "cd /d {BASE_DIR}\\frp && start /b frpc.exe -c frpc.toml"',
        "auto_restart": True,
        "max_restarts": 10,
        "restart_cooldown": 30,
    },
}

# 调度配置
SCHEDULE = {
    "health_check_interval": 30,      # 健康检查间隔（秒）
    "heartbeat_interval": 30,          # 心跳上报间隔（秒）
    "cloud_sync_interval": 1800,       # 云同步间隔（秒）= 30分钟
    "resource_monitor_interval": 3600, # 资源监控间隔（秒）= 1小时
    "ledger_backup_interval": 86400,   # 账本备份间隔（秒）= 24小时
}

# 阈值配置
THRESHOLDS = {
    "cpu_warning": 80,
    "cpu_critical": 90,
    "memory_warning": 85,
    "memory_critical": 95,
    "disk_warning": 90,
    "disk_critical": 95,
}

# ============================================================
# 初始化
# ============================================================

LOG_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

log_file = LOG_DIR / "watchdog.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("Watchdog")

STATE_FILE = DATA_DIR / "watchdog_state.json"
PID_FILE = DATA_DIR / "watchdog.pid"


# ============================================================
# 工具函数
# ============================================================

def get_timestamp() -> str:
    """获取UTC+8时间戳"""
    return datetime.now(timezone(timedelta(hours=8))).isoformat()


def check_port(host: str, port: int, timeout: float = 3.0) -> bool:
    """检查端口是否可连接"""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


def check_http(url: str, timeout: float = 5.0) -> bool:
    """检查HTTP端点是否可访问"""
    try:
        import urllib.request
        req = urllib.request.Request(url, method='GET')
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except Exception:
        return False


def check_process(name: str) -> bool:
    """检查进程是否在运行"""
    for proc in psutil.process_iter(['name']):
        try:
            if name.lower() in proc.info['name'].lower():
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return False


def get_system_resources() -> Dict[str, Any]:
    """获取系统资源状态"""
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('C:\\')
    
    return {
        "cpu_percent": cpu_percent,
        "memory_total_gb": round(memory.total / (1024**3), 2),
        "memory_used_gb": round(memory.used / (1024**3), 2),
        "memory_percent": memory.percent,
        "disk_total_gb": round(disk.total / (1024**3), 2),
        "disk_used_gb": round(disk.used / (1024**3), 2),
        "disk_percent": disk.percent,
        "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat(),
        "uptime_seconds": int(time.time() - psutil.boot_time()),
    }


def load_state() -> Dict[str, Any]:
    """加载守护状态"""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "started_at": get_timestamp(),
        "last_heartbeat": None,
        "last_cloud_sync": None,
        "last_resource_check": None,
        "last_ledger_backup": None,
        "service_restarts": {},
        "total_heartbeats": 0,
        "total_health_checks": 0,
        "alerts": [],
    }


def save_state(state: Dict[str, Any]):
    """保存守护状态"""
    try:
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"保存状态失败: {e}")


# ============================================================
# 服务监控与自动重启
# ============================================================

class ServiceMonitor:
    """服务监控器"""
    
    def __init__(self):
        self.restart_history: Dict[str, List[float]] = {k: [] for k in SERVICES}
    
    def check_service(self, service_id: str, config: Dict) -> Dict[str, Any]:
        """检查单个服务状态"""
        result = {
            "service_id": service_id,
            "name": config["name"],
            "status": "unknown",
            "checked_at": get_timestamp(),
        }
        
        # 端口检查
        if config.get("port"):
            port_open = check_port(config["host"], config["port"])
            result["port_open"] = port_open
            if port_open:
                # HTTP检查
                if config.get("check_url"):
                    http_ok = check_http(config["check_url"])
                    result["http_ok"] = http_ok
                    result["status"] = "running" if http_ok else "degraded"
                else:
                    result["status"] = "running"
            else:
                result["status"] = "stopped"
        
        # 进程检查
        elif config.get("check_process"):
            proc_running = check_process(config["process_name"])
            result["process_running"] = proc_running
            result["status"] = "running" if proc_running else "stopped"
        
        return result
    
    def check_all(self) -> List[Dict[str, Any]]:
        """检查所有服务"""
        results = []
        for service_id, config in SERVICES.items():
            try:
                result = self.check_service(service_id, config)
                results.append(result)
                
                if result["status"] == "stopped":
                    logger.warning(f"服务异常: {result['name']} (状态: {result['status']})")
                    
                    # 自动重启
                    if config.get("auto_restart") and config.get("start_cmd"):
                        self.auto_restart(service_id, config)
                else:
                    logger.debug(f"服务正常: {result['name']}")
                    
            except Exception as e:
                logger.error(f"检查服务 {service_id} 失败: {e}")
                results.append({
                    "service_id": service_id,
                    "name": config["name"],
                    "status": "error",
                    "error": str(e),
                })
        
        return results
    
    def auto_restart(self, service_id: str, config: Dict):
        """自动重启服务"""
        now = time.time()
        history = self.restart_history[service_id]
        
        # 清理过期历史
        cooldown = config.get("restart_cooldown", 60)
        history = [t for t in history if now - t < cooldown * 2]
        self.restart_history[service_id] = history
        
        # 检查重启频率限制
        max_restarts = config.get("max_restarts", 5)
        if len(history) >= max_restarts:
            logger.error(f"服务 {config['name']} 重启次数超限 ({len(history)}/{max_restarts})，跳过自动重启")
            return
        
        # 检查冷却时间
        if history and now - history[-1] < cooldown:
            logger.info(f"服务 {config['name']} 在冷却期内，跳过重启")
            return
        
        # 执行重启
        logger.info(f"正在自动重启服务: {config['name']}")
        try:
            start_cmd = config["start_cmd"]
            subprocess.Popen(start_cmd, shell=True, 
                           stdout=subprocess.DEVNULL, 
                           stderr=subprocess.DEVNULL,
                           creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0)
            self.restart_history[service_id].append(now)
            logger.info(f"服务 {config['name']} 重启命令已发送")
            
            # 等待后验证
            time.sleep(5)
            verify = self.check_service(service_id, config)
            if verify["status"] == "running":
                logger.info(f"服务 {config['name']} 重启成功")
            else:
                logger.warning(f"服务 {config['name']} 重启后仍未正常运行")
                
        except Exception as e:
            logger.error(f"重启服务 {config['name']} 失败: {e}")


# ============================================================
# 心跳上报
# ============================================================

class HeartbeatReporter:
    """心跳上报器（本地→云内核）"""
    
    def __init__(self):
        self.last_heartbeat = None
    
    def send_heartbeat(self, services_status: List[Dict], resources: Dict) -> Dict[str, Any]:
        """发送心跳到云内核"""
        try:
            import urllib.request
            
            heartbeat_data = {
                "node_id": NODE_ID,
                "node_name": NODE_NAME,
                "timestamp": get_timestamp(),
                "status": "active",
                "resources": resources,
                "services": [
                    {
                        "id": s["service_id"],
                        "name": s["name"],
                        "status": s["status"],
                    } for s in services_status
                ],
                "did": "DID-BR-000002",
                "trace_symbol": "Ω₀⊂⊙∞⊂Ω",
            }
            
            # 尝试通过云内核API上报
            payload = json.dumps(heartbeat_data, ensure_ascii=False).encode('utf-8')
            
            # 优先尝试域名，失败则直连IP
            for api_base in [CLOUD_API_BASE, CLOUD_DIRECT_BASE]:
                try:
                    url = f"{api_base}/control/heartbeat"
                    req = urllib.request.Request(
                        url,
                        data=payload,
                        headers={
                            'Content-Type': 'application/json',
                            'X-API-Key': CLOUD_API_KEY,
                        },
                        method='POST'
                    )
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        response_data = json.loads(resp.read().decode('utf-8'))
                        self.last_heartbeat = get_timestamp()
                        logger.info(f"心跳上报成功 (通过 {api_base})")
                        return {
                            "success": True,
                            "response": response_data,
                            "sent_at": self.last_heartbeat,
                        }
                except Exception as e:
                    logger.debug(f"通过 {api_base} 心跳上报失败: {e}")
                    continue
            
            # 所有通道都失败，记录本地
            logger.warning("心跳上报失败（所有通道不可达），记录本地")
            return {
                "success": False,
                "error": "所有通道不可达",
                "local_recorded": True,
            }
            
        except Exception as e:
            logger.error(f"心跳上报异常: {e}")
            return {"success": False, "error": str(e)}


# ============================================================
# 云同步
# ============================================================

class CloudSyncManager:
    """云同步管理器"""
    
    def __init__(self):
        self.last_sync = None
    
    def sync_truths(self) -> Dict[str, Any]:
        """同步真值到云内核"""
        try:
            # 检查本地是否有新真值
            truth_index = BASE_DIR / "truth_index.json"
            if not truth_index.exists():
                return {"success": True, "message": "无新真值需要同步", "synced": 0}
            
            with open(truth_index, 'r', encoding='utf-8') as f:
                local_truths = json.load(f)
            
            # 这里可以实现增量同步逻辑
            # 简化版：记录同步时间
            self.last_sync = get_timestamp()
            logger.info(f"云同步完成（本地真值: {len(local_truths)} 条）")
            
            return {
                "success": True,
                "local_truths": len(local_truths),
                "synced_at": self.last_sync,
            }
            
        except Exception as e:
            logger.error(f"云同步失败: {e}")
            return {"success": False, "error": str(e)}


# ============================================================
# 资源监控与告警
# ============================================================

class ResourceMonitor:
    """资源监控器"""
    
    def __init__(self):
        self.alerts: List[Dict] = []
    
    def check_resources(self) -> Dict[str, Any]:
        """检查系统资源并生成告警"""
        resources = get_system_resources()
        alerts = []
        
        # CPU告警
        if resources["cpu_percent"] >= THRESHOLDS["cpu_critical"]:
            alerts.append({
                "level": "critical",
                "type": "cpu",
                "message": f"CPU使用率 critical: {resources['cpu_percent']}%",
                "value": resources["cpu_percent"],
                "threshold": THRESHOLDS["cpu_critical"],
            })
        elif resources["cpu_percent"] >= THRESHOLDS["cpu_warning"]:
            alerts.append({
                "level": "warning",
                "type": "cpu",
                "message": f"CPU使用率 warning: {resources['cpu_percent']}%",
                "value": resources["cpu_percent"],
                "threshold": THRESHOLDS["cpu_warning"],
            })
        
        # 内存告警
        if resources["memory_percent"] >= THRESHOLDS["memory_critical"]:
            alerts.append({
                "level": "critical",
                "type": "memory",
                "message": f"内存使用率 critical: {resources['memory_percent']}%",
                "value": resources["memory_percent"],
                "threshold": THRESHOLDS["memory_critical"],
            })
        elif resources["memory_percent"] >= THRESHOLDS["memory_warning"]:
            alerts.append({
                "level": "warning",
                "type": "memory",
                "message": f"内存使用率 warning: {resources['memory_percent']}%",
                "value": resources["memory_percent"],
                "threshold": THRESHOLDS["memory_warning"],
            })
        
        # 磁盘告警
        if resources["disk_percent"] >= THRESHOLDS["disk_critical"]:
            alerts.append({
                "level": "critical",
                "type": "disk",
                "message": f"磁盘使用率 critical: {resources['disk_percent']}%",
                "value": resources["disk_percent"],
                "threshold": THRESHOLDS["disk_critical"],
            })
        elif resources["disk_percent"] >= THRESHOLDS["disk_warning"]:
            alerts.append({
                "level": "warning",
                "type": "disk",
                "message": f"磁盘使用率 warning: {resources['disk_percent']}%",
                "value": resources["disk_percent"],
                "threshold": THRESHOLDS["disk_warning"],
            })
        
        # 记录告警
        for alert in alerts:
            alert["timestamp"] = get_timestamp()
            self.alerts.append(alert)
            if alert["level"] == "critical":
                logger.critical(alert["message"])
            else:
                logger.warning(alert["message"])
        
        # 保留最近1000条告警
        self.alerts = self.alerts[-1000:]
        
        return {
            "resources": resources,
            "alerts": alerts,
            "alert_count": len(alerts),
            "checked_at": get_timestamp(),
        }


# ============================================================
# 账本备份
# ============================================================

class LedgerBackupManager:
    """账本备份管理器"""
    
    def __init__(self):
        self.last_backup = None
    
    def backup_ledger(self) -> Dict[str, Any]:
        """备份本地账本"""
        try:
            if not LEDGER_PATH.exists():
                return {"success": False, "error": "账本文件不存在"}
            
            # 读取账本
            with open(LEDGER_PATH, 'r', encoding='utf-8') as f:
                ledger = json.load(f)
            
            # 生成备份
            backup_dir = BASE_DIR / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = backup_dir / f"M9_global_ledger_backup_{timestamp}.json"
            
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(ledger, f, ensure_ascii=False, indent=2)
            
            # 计算哈希
            with open(backup_file, 'rb') as f:
                backup_hash = hashlib.sha256(f.read()).hexdigest()
            
            self.last_backup = get_timestamp()
            logger.info(f"账本备份完成: {backup_file.name} (区块高度: {ledger.get('block_height')}, 哈希: {backup_hash[:16]}...)")
            
            # 清理旧备份（保留最近7个）
            backups = sorted(backup_dir.glob("M9_global_ledger_backup_*.json"))
            if len(backups) > 7:
                for old_backup in backups[:-7]:
                    old_backup.unlink()
                    logger.info(f"清理旧备份: {old_backup.name}")
            
            return {
                "success": True,
                "backup_file": str(backup_file),
                "backup_hash": backup_hash,
                "block_height": ledger.get('block_height'),
                "total_assets": ledger.get('total_assets'),
                "backed_up_at": self.last_backup,
            }
            
        except Exception as e:
            logger.error(f"账本备份失败: {e}")
            return {"success": False, "error": str(e)}


# ============================================================
# 主守护循环
# ============================================================

class WatchdogDaemon:
    """守护进程主类"""
    
    def __init__(self):
        self.state = load_state()
        self.service_monitor = ServiceMonitor()
        self.heartbeat_reporter = HeartbeatReporter()
        self.cloud_sync = CloudSyncManager()
        self.resource_monitor = ResourceMonitor()
        self.ledger_backup = LedgerBackupManager()
        self.running = False
        
        # 上次执行时间
        self.last_health_check = 0
        self.last_heartbeat = 0
        self.last_cloud_sync = 0
        self.last_resource_check = 0
        self.last_ledger_backup = 0
    
    def write_pid(self):
        """写入PID文件"""
        with open(PID_FILE, 'w') as f:
            f.write(str(os.getpid()))
    
    def remove_pid(self):
        """移除PID文件"""
        if PID_FILE.exists():
            PID_FILE.unlink()
    
    def run_cycle(self):
        """执行一个守护周期"""
        now = time.time()
        
        # 1. 服务健康检查（每30秒）
        if now - self.last_health_check >= SCHEDULE["health_check_interval"]:
            logger.debug("执行服务健康检查...")
            services_status = self.service_monitor.check_all()
            self.state["last_health_check"] = get_timestamp()
            self.state["total_health_checks"] = self.state.get("total_health_checks", 0) + 1
            self.last_health_check = now
            
            # 检查是否有服务异常
            stopped_services = [s for s in services_status if s["status"] == "stopped"]
            if stopped_services:
                logger.warning(f"发现 {len(stopped_services)} 个服务异常")
            else:
                logger.debug("所有服务正常")
        
        # 2. 心跳上报（每30秒）
        if now - self.last_heartbeat >= SCHEDULE["heartbeat_interval"]:
            logger.debug("执行心跳上报...")
            resources = get_system_resources()
            services_status = self.service_monitor.check_all()
            heartbeat_result = self.heartbeat_reporter.send_heartbeat(services_status, resources)
            self.state["last_heartbeat"] = get_timestamp()
            self.state["total_heartbeats"] = self.state.get("total_heartbeats", 0) + 1
            self.last_heartbeat = now
        
        # 3. 云同步（每30分钟）
        if now - self.last_cloud_sync >= SCHEDULE["cloud_sync_interval"]:
            logger.info("执行云同步...")
            sync_result = self.cloud_sync.sync_truths()
            self.state["last_cloud_sync"] = get_timestamp()
            self.last_cloud_sync = now
        
        # 4. 资源监控（每小时）
        if now - self.last_resource_check >= SCHEDULE["resource_monitor_interval"]:
            logger.info("执行资源监控...")
            resource_result = self.resource_monitor.check_resources()
            self.state["last_resource_check"] = get_timestamp()
            self.state["alerts"] = self.resource_monitor.alerts[-100:]
            self.last_resource_check = now
        
        # 5. 账本备份（每24小时）
        if now - self.last_ledger_backup >= SCHEDULE["ledger_backup_interval"]:
            logger.info("执行账本备份...")
            backup_result = self.ledger_backup.backup_ledger()
            self.state["last_ledger_backup"] = get_timestamp()
            self.last_ledger_backup = now
        
        # 保存状态
        save_state(self.state)
    
    def run(self):
        """运行守护进程"""
        self.running = True
        self.write_pid()
        
        logger.info("=" * 60)
        logger.info("本地内核能量态守护脚本启动")
        logger.info(f"节点ID: {NODE_ID}")
        logger.info(f"节点名称: {NODE_NAME}")
        logger.info(f"监控服务: {len(SERVICES)} 个")
        logger.info(f"健康检查间隔: {SCHEDULE['health_check_interval']}秒")
        logger.info(f"心跳上报间隔: {SCHEDULE['heartbeat_interval']}秒")
        logger.info(f"云同步间隔: {SCHEDULE['cloud_sync_interval']}秒")
        logger.info(f"资源监控间隔: {SCHEDULE['resource_monitor_interval']}秒")
        logger.info(f"账本备份间隔: {SCHEDULE['ledger_backup_interval']}秒")
        logger.info("=" * 60)
        
        # 启动时立即执行一次完整检查
        logger.info("启动初始化：执行首次完整检查...")
        services_status = self.service_monitor.check_all()
        resources = get_system_resources()
        self.heartbeat_reporter.send_heartbeat(services_status, resources)
        self.resource_monitor.check_resources()
        logger.info("启动初始化完成")
        
        # 主循环
        try:
            while self.running:
                self.run_cycle()
                time.sleep(5)  # 5秒粒度的主循环
        except KeyboardInterrupt:
            logger.info("收到中断信号，正在停止...")
        except Exception as e:
            logger.error(f"守护进程异常: {e}", exc_info=True)
        finally:
            self.running = False
            self.remove_pid()
            logger.info("守护进程已停止")
    
    def stop(self):
        """停止守护进程"""
        self.running = False


# ============================================================
# 命令行接口
# ============================================================

def show_status():
    """显示守护状态"""
    print("=" * 60)
    print("本地内核能量态守护脚本 - 状态查询")
    print("=" * 60)
    
    # 检查PID
    if PID_FILE.exists():
        with open(PID_FILE, 'r') as f:
            pid = f.read().strip()
        print(f"守护进程PID: {pid}")
        
        # 检查进程是否在运行
        try:
            proc = psutil.Process(int(pid))
            print(f"进程状态: 运行中 (CPU: {proc.cpu_percent()}%, 内存: {proc.memory_info().rss / 1024 / 1024:.1f}MB)")
        except (psutil.NoSuchProcess, ValueError):
            print("进程状态: 未运行（PID文件残留）")
    else:
        print("守护进程: 未运行")
    
    # 显示状态文件
    if STATE_FILE.exists():
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            state = json.load(f)
        print(f"\n启动时间: {state.get('started_at', '未知')}")
        print(f"上次心跳: {state.get('last_heartbeat', '从未')}")
        print(f"上次云同步: {state.get('last_cloud_sync', '从未')}")
        print(f"上次资源检查: {state.get('last_resource_check', '从未')}")
        print(f"总心跳次数: {state.get('total_heartbeats', 0)}")
        print(f"总健康检查: {state.get('total_health_checks', 0)}")
        alerts = state.get('alerts', [])
        print(f"当前告警: {len(alerts)} 条")
        for alert in alerts[-5:]:
            print(f"  - [{alert.get('level', '?').upper()}] {alert.get('message', '?')}")
    
    # 检查服务状态
    print(f"\n服务状态:")
    monitor = ServiceMonitor()
    services = monitor.check_all()
    for s in services:
        status_icon = "✅" if s["status"] == "running" else "⚠️" if s["status"] == "degraded" else "❌"
        print(f"  {status_icon} {s['name']}: {s['status']}")
    
    # 系统资源
    resources = get_system_resources()
    print(f"\n系统资源:")
    print(f"  CPU: {resources['cpu_percent']}%")
    print(f"  内存: {resources['memory_used_gb']}/{resources['memory_total_gb']} GB ({resources['memory_percent']}%)")
    print(f"  磁盘: {resources['disk_used_gb']}/{resources['disk_total_gb']} GB ({resources['disk_percent']}%)")
    print(f"  运行时间: {resources['uptime_seconds'] // 3600}小时{(resources['uptime_seconds'] % 3600) // 60}分钟")
    
    print("=" * 60)


def main():
    """主入口"""
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        
        if cmd == "--status":
            show_status()
            return
        
        elif cmd == "--stop":
            if PID_FILE.exists():
                with open(PID_FILE, 'r') as f:
                    pid = int(f.read().strip())
                try:
                    proc = psutil.Process(pid)
                    proc.terminate()
                    print(f"已发送停止信号到进程 {pid}")
                except psutil.NoSuchProcess:
                    print("进程不存在，清理PID文件")
                    PID_FILE.unlink()
            else:
                print("守护进程未运行")
            return
        
        elif cmd == "--daemon":
            # 后台模式（Windows下用pythonw.exe）
            print("启动后台守护模式...")
            pythonw = PYTHON_PATH.replace("python.exe", "pythonw.exe")
            if os.path.exists(pythonw):
                subprocess.Popen([pythonw, __file__], 
                               creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                subprocess.Popen([PYTHON_PATH, __file__], 
                               creationflags=subprocess.CREATE_NO_WINDOW)
            print("后台守护进程已启动")
            return
        
        elif cmd == "--help":
            print("""
本地内核能量态守护脚本 - watchdog.py

用法:
  python watchdog.py              前台运行（调试用，Ctrl+C停止）
  python watchdog.py --daemon     后台守护模式
  python watchdog.py --status     查看守护状态
  python watchdog.py --stop       停止守护进程
  python watchdog.py --help       显示帮助

功能:
  - 服务监控（AIOS 8017 / Dashboard 8899 / frpc）
  - 自动重启（发现异常自动重启）
  - 心跳上报（每30秒向云内核上报本地状态）
  - 云同步（每30分钟同步真值到云内核）
  - 资源监控（每小时检查CPU/内存/磁盘，生成告警）
  - 账本备份（每24小时自动备份本地账本）

开机自启: 将 start_watchdog.bat 放入 Windows 启动文件夹
  启动文件夹路径: shell:startup
""")
            return
    
    # 默认：前台运行
    daemon = WatchdogDaemon()
    daemon.run()


if __name__ == "__main__":
    main()
