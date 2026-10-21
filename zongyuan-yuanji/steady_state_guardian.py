#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 增强版稳态守护进程
- 多维健康检查（CPU/内存/磁盘/API/网络）
- 自动故障检测与修复
- 智能告警分级（INFO/WARNING/CRITICAL）
- 自愈操作队列（安全白名单机制）
"""

import os, sys, json, time, subprocess, requests
from datetime import datetime
from pathlib import Path
import psutil

# 配置常量
CONFIG = {
    # 资源阈值
    "cpu_warning": 75.0,
    "cpu_critical": 90.0,
    "memory_warning": 75.0,
    "memory_critical": 85.0,
    "disk_warning": 80.0,
    "disk_critical": 90.0,
    
    # API 健康检查端点
    "api_endpoints": [
        ("记忆网关", "https://www.huodouai.com/dal/health", 10),
        ("真值上报", "https://www.huodouai.com/api/report/truth", 5),
    ],
    
    # 服务检查列表
    "services": [
        ("Nginx", "nginx"),
        ("Python 推理服务", "python3.*yuanji"),
        ("监控守护进程", "monitor_daemon.py"),
    ],
    
    # 日志路径
    "log_dir": Path("/zongyuan-yuanji/logs"),
    "alert_log": Path("/zongyuan-yuanji/logs/steady_state_alerts.log"),
    
    # 自愈白名单（仅允许这些操作）
    "healing_actions": {
        "restart_service": True,
        "cleanup_logs": True,
        "clear_cache": True,
        "rotate_disk": False,  # 需要人工确认
        "scale_resources": False,  # 需要人工确认
    }
}

class SteadyStateGuardian:
    """稳态守护者"""
    
    def __init__(self):
        self.check_count = 0
        self.last_repair_time = {}
        self.repair_cooldown = 300  # 每次修复后冷却 5 分钟
        
    def get_timestamp(self):
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def log(self, level, message, details=None):
        """分级日志记录"""
        timestamp = self.get_timestamp()
        log_entry = {
            "timestamp": timestamp,
            "level": level,
            "message": message,
            "details": details or {}
        }
        
        # 输出到控制台
        color_map = {"INFO": "\033[32m", "WARNING": "\033[33m", "CRITICAL": "\033[31m"}
        color = color_map.get(level, "\033[0m")
        print(f"{color}[{timestamp}] [{level}] {message}\033[0m")
        
        # 写入日志文件
        CONFIG["log_dir"].mkdir(parents=True, exist_ok=True)
        with open(CONFIG["log_dir"] / "steady_state_monitor.jsonl", "a") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        
        # 如果是告警级别以上，单独记录
        if level in ["WARNING", "CRITICAL"]:
            with open(CONFIG["alert_log"], "a") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    
    def check_cpu(self):
        """CPU 使用率检查"""
        cpu_percent = psutil.cpu_percent(interval=1)
        status = "OK"
        
        if cpu_percent >= CONFIG["cpu_critical"]:
            status = "CRITICAL"
        elif cpu_percent >= CONFIG["cpu_warning"]:
            status = "WARNING"
        
        self.log(status, f"CPU 使用率：{cpu_percent:.1f}%", 
                {"value": cpu_percent, "warning_threshold": CONFIG["cpu_warning"]})
        return status == "OK"
    
    def check_memory(self):
        """内存使用率检查"""
        mem = psutil.virtual_memory()
        mem_percent = mem.percent
        
        status = "OK"
        if mem_percent >= CONFIG["memory_critical"]:
            status = "CRITICAL"
        elif mem_percent >= CONFIG["memory_warning"]:
            status = "WARNING"
        
        self.log(status, f"内存使用率：{mem_percent:.1f}% ({mem.available / 1024**2:.0f}MB 可用)",
                {"value": mem_percent, "available_mb": mem.available / 1024**2})
        return status == "OK"
    
    def check_disk(self):
        """磁盘使用率检查"""
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent
        
        status = "OK"
        if disk_percent >= CONFIG["disk_critical"]:
            status = "CRITICAL"
        elif disk_percent >= CONFIG["disk_warning"]:
            status = "WARNING"
        
        self.log(status, f"磁盘使用率：{disk_percent:.1f}% ({disk.free / 1024**3:.1f}GB 可用)",
                {"value": disk_percent, "free_gb": disk.free / 1024**3})
        
        # 如果超过警告线，触发清理建议
        if status == "WARNING" and CONFIG["healing_actions"]["cleanup_logs"]:
            self.try_heal("cleanup_old_logs")
        
        return status == "OK"
    
    def check_api_endpoints(self):
        """外部 API 健康检查"""
        all_healthy = True
        
        for name, url, timeout in CONFIG["api_endpoints"]:
            try:
                start = time.time()
                response = requests.get(url, timeout=timeout)
                elapsed = (time.time() - start) * 1000
                
                if response.status_code == 200:
                    self.log("INFO", f"{name} 健康检查通过 ({elapsed:.0f}ms)")
                else:
                    self.log("WARNING", f"{name} 返回非 200 状态码", 
                           {"status_code": response.status_code})
                    all_healthy = False
                    
            except requests.exceptions.Timeout:
                self.log("CRITICAL", f"{name} 连接超时", {"url": url})
                all_healthy = False
            except Exception as e:
                self.log("CRITICAL", f"{name} 检查失败", {"error": str(e)})
                all_healthy = False
        
        return all_healthy
    
    def check_services(self):
        """检查关键服务是否运行"""
        all_running = True
        
        for service_name, pattern in CONFIG["services"]:
            try:
                result = subprocess.run(
                    ["pgrep", "-f", pattern],
                    capture_output=True, text=True
                )
                
                if result.returncode == 0:
                    pids = len(result.stdout.strip().split('\n'))
                    self.log("INFO", f"{service_name} 运行中 (PID 数量：{pids})")
                else:
                    self.log("WARNING", f"{service_name} 未运行", 
                           {"pattern": pattern})
                    if CONFIG["healing_actions"]["restart_service"]:
                        self.try_heal(f"restart_{service_name.lower().replace(' ', '_')}")
                    all_running = False
                    
            except Exception as e:
                self.log("ERROR", f"检查{service_name}失败", {"error": str(e)})
        
        return all_running
    
    def try_heal(self, action_type):
        """尝试自愈操作（带冷却机制）"""
        now = time.time()
        
        # 冷却期检查
        if action_type in self.last_repair_time:
            cooldown_remaining = self.repair_cooldown - (now - self.last_repair_time[action_type])
            if cooldown_remaining > 0:
                self.log("INFO", f"自愈操作[{action_type}]处于冷却期，跳过 ({cooldown_remaining:.0f}s 后重试)")
                return False
        
        # 权限白名单检查
        if not CONFIG["healing_actions"].get(action_type, False):
            self.log("WARNING", f"自愈操作[{action_type}]不在白名单中，需要人工确认")
            return False
        
        # 执行具体的自愈动作
        success = self.execute_healing(action_type)
        
        if success:
            self.last_repair_time[action_type] = now
            self.log("INFO", f"✅ 自愈操作[{action_type}]成功执行")
        else:
            self.log("CRITICAL", f"❌ 自愈操作[{action_type}]失败")
        
        return success
    
    def execute_healing(self, action_type):
        """执行具体的自愈逻辑"""
        try:
            if action_type == "cleanup_old_logs":
                # 清理超过 7 天的日志文件
                old_logs = list(CONFIG["log_dir"].glob("*.log.*"))
                deleted = 0
                for log_file in old_logs:
                    if log_file.stat().st_mtime < time.time() - (7 * 24 * 3600):
                        log_file.unlink()
                        deleted += 1
                self.log("INFO", f"已清理 {deleted} 个旧日志文件", {"deleted_count": deleted})
                return deleted > 0
                
            elif action_type == "restart_service":
                # 这里可以根据服务名做不同的重启逻辑
                self.log("INFO", "尝试重启服务...", {"note": "实际生产环境需要更精细的控制"})
                return True
            
            elif action_type == "clear_cache":
                # 清理 pip cache 和 Python __pycache__
                subprocess.run(["pip", "cache", "purge"], capture_output=True)
                subprocess.run(["find", "/zongyuan-yuanji", "-name", "__pycache__", "-type", "d", "-exec", "rm", "-rf", "{}", "+"],
                             capture_output=True)
                self.log("INFO", "已清理缓存")
                return True
            
            else:
                self.log("WARNING", f"未知的自愈动作类型：{action_type}")
                return False
                
        except Exception as e:
            self.log("ERROR", f"自愈执行异常：{e}")
            return False
    
    def run_health_check(self):
        """执行完整健康检查"""
        self.check_count += 1
        self.log("INFO", f"========== 第{self.check_count}次健康检查 ==========")
        
        results = {
            "check_time": self.get_timestamp(),
            "checks": {},
            "overall_status": "HEALTHY",
            "issues_found": []
        }
        
        # 执行各项检查
        checks = [
            ("cpu", self.check_cpu),
            ("memory", self.check_memory),
            ("disk", self.check_disk),
            ("api_endpoints", self.check_api_endpoints),
            ("services", self.check_services),
        ]
        
        critical_count = 0
        warning_count = 0
        
        for name, check_func in checks:
            try:
                is_healthy = check_func()
                results["checks"][name] = "HEALTHY" if is_healthy else "UNHEALTHY"
                
                if not is_healthy:
                    critical_count += 1
                    results["issues_found"].append(name)
                    
            except Exception as e:
                self.log("ERROR", f"检查{name}时发生异常", {"error": str(e)})
                results["checks"][name] = "ERROR"
                critical_count += 1
        
        # 综合状态判定
        if critical_count > 0:
            results["overall_status"] = "CRITICAL"
        elif warning_count > 0:
            results["overall_status"] = "WARNING"
        
        # 生成报告
        self.log("INFO", f"健康检查完成：{results['overall_status']}", 
                {"checks": results["checks"], "issues": results["issues_found"]})
        
        return results
    
    def start(self, interval=300):
        """启动持续监控循环"""
        self.log("INFO", f"稳态守护进程已启动 (检查间隔：{interval}s)")
        self.log("INFO", f"日志目录：{CONFIG['log_dir']}")
        
        try:
            while True:
                self.run_health_check()
                time.sleep(interval)
                
        except KeyboardInterrupt:
            self.log("INFO", "稳态守护进程已停止")
        except Exception as e:
            self.log("CRITICAL", f"守护进程异常退出", {"error": str(e)})


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="ZONGYUAN-ROOT 稳态守护进程")
    parser.add_argument("--once", action="store_true", help="仅执行一次健康检查")
    parser.add_argument("--interval", type=int, default=300, help="监控间隔（秒）")
    
    args = parser.parse_args()
    
    guardian = SteadyStateGuardian()
    
    if args.once:
        guardian.run_health_check()
    else:
        guardian.start(args.interval)
