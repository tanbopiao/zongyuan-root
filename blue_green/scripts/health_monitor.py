#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 健康检查与自动熔断工具
功能：持续监控蓝绿环境健康状态，异常时自动触发回滚
用法：
  python3 health_monitor.py --once    # 执行一次健康检查
  python3 health_monitor.py --daemon  # 持续监控模式
  python3 health_monitor.py --status  # 查看健康状态
"""
import argparse
import json
import os
import subprocess
import time
from datetime import datetime

CONFIG_PATH = "/opt/ZONGYUAN-ROOT/blue_green/config/blue_green_config.json"
LOG_PATH = "/opt/ZONGYUAN-ROOT/blue_green/logs/health_monitor.log"
ALERT_LOG = "/opt/ZONGYUAN-ROOT/blue_green/logs/alerts.log"

class HealthMonitor:
    def __init__(self):
        self.config = self._load_config()
        self.consecutive_failures = 0
        self.error_history = []
    
    def _load_config(self):
        with open(CONFIG_PATH) as f:
            return json.load(f)
    
    def _log(self, message, level="INFO", log_file=LOG_PATH):
        log_entry = "[{}] [{}] {}\n".format(datetime.now().isoformat(), level, message)
        print(log_entry.strip())
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        with open(log_file, "a") as f:
            f.write(log_entry)
    
    def _get_current_active(self):
        return self.config.get("current_active", "blue")
    
    def _check_endpoint(self, url, timeout=5):
        """检查单个端点"""
        try:
            result = subprocess.run(
                ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}:%{time_total}",
                 url],
                capture_output=True, text=True, timeout=timeout
            )
            output = result.stdout.strip()
            if ":" in output:
                status_code, response_time = output.split(":", 1)
                return int(status_code), float(response_time)
            return 0, 0.0
        except Exception as e:
            return 0, 0.0
    
    def check_environment(self, env):
        """检查指定环境的健康状态"""
        port_base = self.config["environments"][env]["backend_port_base"]
        endpoints = self.config["health_check"]["endpoints"]
        
        results = []
        for endpoint in endpoints:
            url = "http://127.0.0.1:{}{}".format(port_base, endpoint)
            status_code, response_time = self._check_endpoint(url)
            results.append({
                "endpoint": endpoint,
                "status_code": status_code,
                "response_time_ms": response_time * 1000,
                "healthy": status_code in [200, 204]
            })
        
        healthy_count = sum(1 for r in results if r["healthy"])
        total_count = len(results)
        avg_response_time = sum(r["response_time_ms"] for r in results) / total_count if total_count > 0 else 0
        
        return {
            "environment": env,
            "timestamp": datetime.now().isoformat(),
            "healthy": healthy_count == total_count,
            "healthy_endpoints": "{}/{}".format(healthy_count, total_count),
            "avg_response_time_ms": round(avg_response_time, 2),
            "details": results
        }
    
    def check_all(self):
        """检查所有环境"""
        results = {}
        for env in ["blue", "green"]:
            results[env] = self.check_environment(env)
        return results
    
    def evaluate_health(self, result):
        """评估健康状态，判断是否需要熔断"""
        hc_config = self.config["health_check"]
        error_rate_threshold = hc_config["error_rate_threshold"]
        response_time_threshold = hc_config["response_time_threshold_ms"]
        consecutive_threshold = hc_config["consecutive_failures_threshold"]
        
        if not result["healthy"]:
            self.consecutive_failures += 1
            self._log("健康检查失败 (连续第{}次)".format(self.consecutive_failures), "WARN")
        else:
            if self.consecutive_failures > 0:
                self._log("健康检查恢复，连续失败计数重置", "INFO")
            self.consecutive_failures = 0
        
        # 检查响应时间
        if result["avg_response_time_ms"] > response_time_threshold:
            self._log("响应时间超过阈值: {:.0f}ms > {}ms".format(
                result["avg_response_time_ms"], response_time_threshold), "WARN")
        
        # 判断是否触发自动熔断
        if self.consecutive_failures >= consecutive_threshold:
            self._log("连续失败达到阈值({}次)，触发自动熔断回滚".format(consecutive_threshold), "ERROR")
            self.trigger_circuit_breaker("连续健康检查失败{}次".format(self.consecutive_failures))
            return False
        
        return True
    
    def trigger_circuit_breaker(self, reason):
        """触发熔断：自动回滚到备用环境"""
        self._log("=" * 60, "ERROR", ALERT_LOG)
        self._log("自动熔断触发: {}".format(reason), "ERROR", ALERT_LOG)
        self._log("=" * 60, "ERROR", ALERT_LOG)
        
        # 调用回滚工具
        try:
            result = subprocess.run(
                ["python3", "/opt/ZONGYUAN-ROOT/blue_green/scripts/rollback.py", "--auto",
                 "--reason", reason],
                capture_output=True, text=True, timeout=60
            )
            self._log("回滚工具执行结果: {}".format(result.stdout[-500:] if result.stdout else "无输出"))
            if result.returncode != 0:
                self._log("回滚工具执行失败: {}".format(result.stderr), "ERROR")
        except Exception as e:
            self._log("调用回滚工具异常: {}".format(e), "ERROR")
    
    def run_once(self):
        """执行一次健康检查"""
        self._log("执行健康检查...")
        active_env = self._get_current_active()
        result = self.check_environment(active_env)
        
        self._log("环境: {} | 健康: {} | 端点: {} | 平均响应: {:.0f}ms".format(
            active_env.upper(),
            "是" if result["healthy"] else "否",
            result["healthy_endpoints"],
            result["avg_response_time_ms"]
        ))
        
        self.evaluate_health(result)
        return result
    
    def run_daemon(self):
        """持续监控模式"""
        self._log("健康监控守护进程启动")
        self._log("检查间隔: {}秒".format(self.config["health_check"]["check_interval_seconds"]))
        self._log("错误率阈值: {}%".format(self.config["health_check"]["error_rate_threshold"]))
        self._log("连续失败阈值: {}次".format(self.config["health_check"]["consecutive_failures_threshold"]))
        
        interval = self.config["health_check"]["check_interval_seconds"]
        while True:
            try:
                self.run_once()
            except Exception as e:
                self._log("健康检查异常: {}".format(e), "ERROR")
            time.sleep(interval)
    
    def status(self):
        """查看健康状态"""
        print("\n" + "=" * 60)
        print("ZONGYUAN-ROOT 健康监控状态")
        print("=" * 60)
        
        results = self.check_all()
        for env, result in results.items():
            status = "🟢 健康" if result["healthy"] else "🔴 异常"
            active = " (当前活跃)" if env == self._get_current_active() else ""
            print("\n{}环境{}{}".format(env.upper(), status, active))
            print("  健康端点: {}".format(result["healthy_endpoints"]))
            print("  平均响应时间: {:.0f}ms".format(result["avg_response_time_ms"]))
            for detail in result["details"]:
                endpoint_status = "✅" if detail["healthy"] else "❌"
                print("  {} {} - HTTP {} ({:.0f}ms)".format(
                    endpoint_status, detail["endpoint"],
                    detail["status_code"], detail["response_time_ms"]))
        
        print("\n连续失败计数: {}".format(self.consecutive_failures))
        print("自动熔断: {}".format("已启用" if self.config["rollback"]["auto_rollback_enabled"] else "已禁用"))
        print("=" * 60 + "\n")

def main():
    parser = argparse.ArgumentParser(description="ZONGYUAN-ROOT 健康检查与自动熔断工具")
    parser.add_argument("--once", action="store_true", help="执行一次健康检查")
    parser.add_argument("--daemon", action="store_true", help="持续监控模式")
    parser.add_argument("--status", action="store_true", help="查看健康状态")
    args = parser.parse_args()
    
    monitor = HealthMonitor()
    
    if args.status:
        monitor.status()
    elif args.daemon:
        monitor.run_daemon()
    elif args.once:
        monitor.run_once()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
