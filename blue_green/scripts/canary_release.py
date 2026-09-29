#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 金丝雀发布工具
功能：逐步放量发布新版本，5%->20%->50%->100%，异常自动回滚
用法：
  python3 canary_release.py --start --target-env green  # 开始金丝雀发布
  python3 canary_release.py --status                     # 查看发布状态
  python3 canary_release.py --rollback                   # 手动回滚
"""
import argparse
import json
import os
import subprocess
import time
from datetime import datetime

CONFIG_PATH = "/opt/ZONGYUAN-ROOT/blue_green/config/blue_green_config.json"
LOG_PATH = "/opt/ZONGYUAN-ROOT/blue_green/logs/canary_release.log"
STATE_PATH = "/opt/ZONGYUAN-ROOT/blue_green/config/canary_state.json"

class CanaryRelease:
    def __init__(self):
        self.config = self._load_config()
        self.state = self._load_state()
    
    def _load_config(self):
        with open(CONFIG_PATH) as f:
            return json.load(f)
    
    def _load_state(self):
        if os.path.isfile(STATE_PATH):
            with open(STATE_PATH) as f:
                return json.load(f)
        return {"active": False, "current_stage": 0, "started_at": None}
    
    def _save_state(self):
        with open(STATE_PATH, "w") as f:
            json.dump(self.state, f, indent=2)
    
    def _log(self, message, level="INFO"):
        log_entry = "[{}] [{}] {}\n".format(datetime.now().isoformat(), level, message)
        print(log_entry.strip())
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        with open(LOG_PATH, "a") as f:
            f.write(log_entry)
    
    def _set_traffic_weight(self, blue_weight, green_weight):
        """设置流量权重"""
        template_path = "/opt/ZONGYUAN-ROOT/blue_green/templates/nginx_upstream_canary.conf"
        with open(template_path) as f:
            template = f.read()
        
        total = blue_weight + green_weight
        green_percent = int(green_weight / total * 100)
        
        config = template.replace("{{TIMESTAMP}}", datetime.now().isoformat())
        config = config.replace("{{CANARY_PERCENT}}", str(green_percent))
        config = config.replace("{{BLUE_WEIGHT}}", str(blue_weight))
        config = config.replace("{{GREEN_WEIGHT}}", str(green_weight))
        
        # 测试并reload Nginx
        test_result = subprocess.run(["nginx", "-t"], capture_output=True, text=True)
        if test_result.returncode != 0:
            self._log("Nginx配置测试失败", "ERROR")
            return False
        
        subprocess.run(["nginx", "-s", "reload"], capture_output=True, text=True)
        self._log("流量权重已设置: 蓝{}% / 绿{}%".format(
            int(blue_weight/total*100), green_percent))
        return True
    
    def _check_health(self, env):
        """检查环境健康"""
        port_base = self.config["environments"][env]["backend_port_base"]
        try:
            result = subprocess.run(
                ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                 "http://127.0.0.1:{}/health".format(port_base)],
                capture_output=True, text=True, timeout=10
            )
            return result.stdout.strip() in ["200", "204"]
        except:
            return False
    
    def start(self, target_env="green"):
        """开始金丝雀发布"""
        self._log("=" * 60)
        self._log("金丝雀发布开始")
        self._log("目标环境: {}".format(target_env.upper()))
        self._log("放量阶段: {}".format(self.config["canary_release"]["stages"]))
        self._log("阶段间隔: {}秒".format(self.config["canary_release"]["stage_interval_seconds"]))
        self._log("=" * 60)
        
        stages = self.config["canary_release"]["stages"]
        interval = self.config["canary_release"]["stage_interval_seconds"]
        
        self.state = {
            "active": True,
            "current_stage": 0,
            "target_env": target_env,
            "started_at": datetime.now().isoformat()
        }
        self._save_state()
        
        for i, percent in enumerate(stages):
            self.state["current_stage"] = i + 1
            self._save_state()
            
            blue_weight = 100 - percent
            green_weight = percent
            
            self._log("\n[阶段 {}/{}] 放量到 {}%".format(i+1, len(stages), percent))
            
            if not self._set_traffic_weight(blue_weight, green_weight):
                self._log("流量设置失败，中止发布", "ERROR")
                self.rollback()
                return False
            
            # 观察期
            self._log("观察期 {}秒...".format(interval))
            time.sleep(interval)
            
            # 健康检查
            if not self._check_health(target_env):
                self._log("目标环境健康检查失败，自动回滚", "ERROR")
                self.rollback()
                return False
            
            self._log("阶段 {} 完成，健康检查通过".format(i+1))
        
        # 全量发布完成
        self._log("\n金丝雀发布完成！新版本已承载100%流量")
        self.state["active"] = False
        self.state["completed_at"] = datetime.now().isoformat()
        self._save_state()
        return True
    
    def rollback(self):
        """回滚到旧版本"""
        self._log("金丝雀发布回滚，流量全部切回蓝环境", "WARN")
        self._set_traffic_weight(100, 0)
        self.state["active"] = False
        self.state["rolled_back_at"] = datetime.now().isoformat()
        self._save_state()
    
    def status(self):
        """查看发布状态"""
        print("\n" + "=" * 60)
        print("ZONGYUAN-ROOT 金丝雀发布状态")
        print("=" * 60)
        
        if self.state.get("active"):
            print("状态: 🟡 发布中")
            print("当前阶段: {}/{}".format(
                self.state.get("current_stage", 0),
                len(self.config["canary_release"]["stages"])))
            print("目标环境: {}".format(self.state.get("target_env", "green").upper()))
            print("开始时间: {}".format(self.state.get("started_at", "未知")))
        elif self.state.get("rolled_back_at"):
            print("状态: 🔴 已回滚")
            print("回滚时间: {}".format(self.state["rolled_back_at"]))
        elif self.state.get("completed_at"):
            print("状态: 🟢 已完成")
            print("完成时间: {}".format(self.state["completed_at"]))
        else:
            print("状态: ⚪ 空闲")
        
        print("\n放量阶段: {}".format(self.config["canary_release"]["stages"]))
        print("阶段间隔: {}秒".format(self.config["canary_release"]["stage_interval_seconds"]))
        print("自动回滚: {}".format("已启用" if self.config["canary_release"]["auto_rollback_on_error"] else "已禁用"))
        print("=" * 60 + "\n")

def main():
    parser = argparse.ArgumentParser(description="ZONGYUAN-ROOT 金丝雀发布工具")
    parser.add_argument("--start", action="store_true", help="开始金丝雀发布")
    parser.add_argument("--target-env", default="green", choices=["blue", "green"], help="目标环境")
    parser.add_argument("--status", action="store_true", help="查看发布状态")
    parser.add_argument("--rollback", action="store_true", help="手动回滚")
    args = parser.parse_args()
    
    canary = CanaryRelease()
    
    if args.status:
        canary.status()
    elif args.start:
        canary.start(args.target_env)
    elif args.rollback:
        canary.rollback()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
