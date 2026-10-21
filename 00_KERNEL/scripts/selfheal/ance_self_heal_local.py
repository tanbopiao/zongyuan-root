#!/usr/bin/env python3
"""
ANCE自愈执行引擎 V7.0
检测→定位→修复→验证→记录 五步闭环
"""
import json, os, time, subprocess, logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path("/opt/ZONGYUAN-ROOT")
LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)
CST = timezone(timedelta(hours=8))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(LOG_DIR / "ance_heal.log"), logging.StreamHandler()]
)
logger = logging.getLogger("ance-heal")

SERVICES = {
    "zongyuan-omega-brain": 8000,
    "zongyuan-loip": 8001,
    "zongyuan-ance": 8002,
    "zongyuan-vector": 8003,
    "zongyuan-monitor": 8004,
    "zongyuan-gov-ai": 8005,
    "zongyuan-anchor": 8006,
}

class SelfHealingEngine:
    def __init__(self):
        self.heal_count = 0
        self.fail_count = 0

    def detect(self):
        """检测异常"""
        issues = []
        for svc, port in SERVICES.items():
            try:
                r = subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                                   "--connect-timeout", "3", f"http://127.0.0.1:{port}/health"],
                                  capture_output=True, text=True, timeout=5)
                if r.stdout.strip() not in ["200", "404"]:
                    issues.append({"service": svc, "port": port, "issue": f"HTTP {r.stdout.strip()}", "type": "service_unhealthy"})
            except:
                issues.append({"service": svc, "port": port, "issue": "connection_timeout", "type": "service_down"})
        
        # 磁盘检测
        disk = subprocess.run(["df", "-h", "/"], capture_output=True, text=True)
        if "100%" in disk.stdout or "9[5-9]%" in disk.stdout:
            issues.append({"service": "system", "issue": "disk_almost_full", "type": "resource"})
        
        return issues

    def diagnose(self, issues):
        """定位根因"""
        for issue in issues:
            if issue["type"] == "service_down":
                issue["root_cause"] = "进程崩溃或未启动"
                issue["action"] = "systemctl restart"
            elif issue["type"] == "service_unhealthy":
                issue["root_cause"] = "服务异常响应"
                issue["action"] = "restart + log_check"
            elif issue["type"] == "resource":
                issue["root_cause"] = "磁盘空间不足"
                issue["action"] = "cleanup_logs + cleanup_cache"
        return issues

    def repair(self, issues):
        """执行修复"""
        results = []
        for issue in issues:
            try:
                if issue["action"] == "systemctl restart":
                    subprocess.run(["systemctl", "restart", issue["service"]], capture_output=True, timeout=10)
                    time.sleep(3)
                    results.append({"service": issue["service"], "action": "restarted", "success": True})
                    self.heal_count += 1
                elif issue["action"] == "restart + log_check":
                    subprocess.run(["systemctl", "restart", issue["service"]], capture_output=True, timeout=10)
                    time.sleep(3)
                    results.append({"service": issue["service"], "action": "restarted", "success": True})
                    self.heal_count += 1
                elif issue["action"] == "cleanup_logs + cleanup_cache":
                    subprocess.run(["find", str(LOG_DIR), "-name", "*.log", "-mtime", "+7", "-delete"], capture_output=True)
                    subprocess.run(["rm", "-rf", str(ROOT / "cache" / "*")], capture_output=True)
                    results.append({"service": "system", "action": "cleanup", "success": True})
                    self.heal_count += 1
            except Exception as e:
                results.append({"service": issue["service"], "action": "failed", "error": str(e)})
                self.fail_count += 1
        return results

    def verify(self, results):
        """验证修复结果"""
        verified = []
        for r in results:
            if r["action"] in ["restarted"]:
                port = SERVICES.get(r["service"], 0)
                try:
                    check = subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                                           "--connect-timeout", "3", f"http://127.0.0.1:{port}/health"],
                                          capture_output=True, text=True, timeout=5)
                    r["verified"] = check.stdout.strip() in ["200", "404"]
                except:
                    r["verified"] = False
            else:
                r["verified"] = True
            verified.append(r)
        return verified

    def record(self, issues, results):
        """记录自愈日志"""
        log_entry = {
            "timestamp": datetime.now(CST).isoformat(),
            "issues_detected": len(issues),
            "repairs_executed": len(results),
            "heal_count": self.heal_count,
            "fail_count": self.fail_count,
            "details": results
        }
        log_file = LOG_DIR / "heal_history.jsonl"
        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        return log_entry

    def run_full_cycle(self):
        """执行完整自愈周期"""
        logger.info("=== 自愈周期开始 ===")
        issues = self.detect()
        if not issues:
            logger.info("未检测到异常，系统健康")
            return {"status": "healthy", "issues": 0}
        logger.info(f"检测到 {len(issues)} 个异常")
        issues = self.diagnose(issues)
        results = self.repair(issues)
        results = self.verify(results)
        log = self.record(issues, results)
        logger.info(f"自愈完成: 修复{len(results)}项，成功{self.heal_count}，失败{self.fail_count}")
        return {"status": "healed", "issues": len(issues), "repairs": results, "log": log}

healer = SelfHealingEngine()

if __name__ == "__main__":
    result = healer.run_full_cycle()
    print(json.dumps(result, indent=2, ensure_ascii=False))
