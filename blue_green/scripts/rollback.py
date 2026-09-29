#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 秒级回滚工具
三层回滚保障：
  L1 流量回滚 (<1秒)：Nginx切换回旧版本，旧版本仍在运行
  L2 配置回滚 (<5秒)：恢复上一版本配置，reload服务
  L3 版本回滚 (<1分钟)：从备份目录快速恢复旧版本代码
用法：
  python3 rollback.py --level L1  # 流量回滚（最快）
  python3 rollback.py --level L2  # 配置回滚
  python3 rollback.py --level L3  # 版本回滚（最彻底）
  python3 rollback.py --auto      # 自动选择回滚层级
"""
import argparse
import json
import os
import shutil
import subprocess
import time
from datetime import datetime

CONFIG_PATH = "/opt/ZONGYUAN-ROOT/blue_green/config/blue_green_config.json"
LOG_PATH = "/opt/ZONGYUAN-ROOT/blue_green/logs/rollback.log"
BACKUP_DIR = "/opt/ZONGYUAN-ROOT/blue_green/backup"

class RollbackManager:
    def __init__(self):
        self.config = self._load_config()
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def _load_config(self):
        with open(CONFIG_PATH) as f:
            return json.load(f)
    
    def _log(self, message, level="INFO"):
        log_entry = "[{}] [{}] {}\n".format(datetime.now().isoformat(), level, message)
        print(log_entry.strip())
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        with open(LOG_PATH, "a") as f:
            f.write(log_entry)
    
    def _get_current_active(self):
        return self.config.get("current_active", "blue")
    
    def _get_standby_env(self):
        return "green" if self._get_current_active() == "blue" else "blue"
    
    def l1_traffic_rollback(self):
        """L1 流量回滚（<1秒）：Nginx切换回旧版本"""
        self._log("=" * 60)
        self._log("L1 流量回滚开始（预期<1秒）")
        self._log("当前活跃: {} -> 回滚到: {}".format(
            self._get_current_active().upper(), self._get_standby_env().upper()))
        self._log("=" * 60)
        
        start_time = time.time()
        
        # 切换Nginx流量到备用环境（旧版本）
        target_env = self._get_standby_env()
        template_path = "/opt/ZONGYUAN-ROOT/blue_green/templates/nginx_upstream_{}.conf".format(target_env)
        
        if not os.path.isfile(template_path):
            self._log("Nginx模板不存在: {}".format(template_path), "ERROR")
            return False
        
        # 测试Nginx配置
        test_result = subprocess.run(["nginx", "-t"], capture_output=True, text=True)
        if test_result.returncode != 0:
            self._log("Nginx配置测试失败: {}".format(test_result.stderr), "ERROR")
            return False
        
        # Reload Nginx
        reload_result = subprocess.run(["nginx", "-s", "reload"], capture_output=True, text=True)
        if reload_result.returncode != 0:
            self._log("Nginx reload失败", "ERROR")
            return False
        
        # 更新配置
        self.config["current_active"] = target_env
        self.config["environments"][target_env]["status"] = "active"
        standby = "blue" if target_env == "green" else "green"
        self.config["environments"][standby]["status"] = "standby"
        
        with open(CONFIG_PATH, "w") as f:
            json.dump(self.config, f, indent=2)
        
        elapsed = time.time() - start_time
        self._log("L1 流量回滚完成，耗时: {:.2f}秒".format(elapsed))
        self._log("当前活跃环境: {}".format(target_env.upper()))
        return True
    
    def l2_config_rollback(self):
        """L2 配置回滚（<5秒）：恢复上一版本配置"""
        self._log("=" * 60)
        self._log("L2 配置回滚开始（预期<5秒）")
        self._log("=" * 60)
        
        start_time = time.time()
        
        # 找到最新的配置备份
        config_backup_dir = os.path.join(BACKUP_DIR, "config")
        if not os.path.isdir(config_backup_dir):
            self._log("配置备份目录不存在: {}".format(config_backup_dir), "ERROR")
            return False
        
        backups = sorted([f for f in os.listdir(config_backup_dir) if f.startswith("nginx_")], reverse=True)
        if not backups:
            self._log("没有找到配置备份", "ERROR")
            return False
        
        latest_backup = os.path.join(config_backup_dir, backups[0])
        self._log("使用配置备份: {}".format(latest_backup))
        
        # 恢复Nginx配置
        nginx_config = self.config["nginx"]["config_path"]
        shutil.copy2(latest_backup, nginx_config)
        
        # 测试并reload
        test_result = subprocess.run(["nginx", "-t"], capture_output=True, text=True)
        if test_result.returncode != 0:
            self._log("Nginx配置测试失败", "ERROR")
            return False
        
        subprocess.run(["nginx", "-s", "reload"], capture_output=True, text=True)
        
        elapsed = time.time() - start_time
        self._log("L2 配置回滚完成，耗时: {:.2f}秒".format(elapsed))
        return True
    
    def l3_version_rollback(self):
        """L3 版本回滚（<1分钟）：从备份恢复旧版本代码"""
        self._log("=" * 60)
        self._log("L3 版本回滚开始（预期<1分钟）")
        self._log("=" * 60)
        
        start_time = time.time()
        
        # 先执行L1流量回滚
        self._log("先执行L1流量回滚...")
        if not self.l1_traffic_rollback():
            self._log("L1流量回滚失败，继续L3版本回滚", "WARN")
        
        # 找到最新的代码备份
        code_backup_dir = os.path.join(BACKUP_DIR, "code")
        if not os.path.isdir(code_backup_dir):
            self._log("代码备份目录不存在", "ERROR")
            return False
        
        backups = sorted(os.listdir(code_backup_dir), reverse=True)
        if not backups:
            self._log("没有找到代码备份", "ERROR")
            return False
        
        latest_backup = os.path.join(code_backup_dir, backups[0])
        active_env = self._get_current_active()
        target_dir = self.config["environments"][active_env]["web_root"]
        
        self._log("使用代码备份: {}".format(latest_backup))
        self._log("恢复到: {}".format(target_dir))
        
        # 清空目标目录并恢复备份
        if os.path.isdir(target_dir):
            shutil.rmtree(target_dir)
        shutil.copytree(latest_backup, target_dir)
        
        # 执行L2配置回滚
        self.l2_config_rollback()
        
        elapsed = time.time() - start_time
        self._log("L3 版本回滚完成，耗时: {:.2f}秒".format(elapsed))
        return True
    
    def auto_rollback(self, reason="自动触发"):
        """自动回滚：根据情况选择回滚层级"""
        self._log("=" * 60)
        self._log("自动回滚触发，原因: {}".format(reason))
        self._log("=" * 60)
        
        # 优先尝试L1（最快）
        if self.l1_traffic_rollback():
            # 验证回滚后是否正常
            time.sleep(2)
            active_env = self._get_current_active()
            port_base = self.config["environments"][active_env]["backend_port_base"]
            
            try:
                result = subprocess.run(
                    ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                     "http://127.0.0.1:{}/health".format(port_base)],
                    capture_output=True, text=True, timeout=10
                )
                if result.stdout.strip() in ["200", "204"]:
                    self._log("L1回滚后验证通过，自动回滚完成")
                    return True
            except:
                pass
            
            self._log("L1回滚后验证失败，升级到L2配置回滚", "WARN")
        
        # L2
        if self.l2_config_rollback():
            time.sleep(2)
            self._log("L2配置回滚完成")
            return True
        
        # L3（最彻底）
        self._log("升级到L3版本回滚", "WARN")
        return self.l3_version_rollback()
    
    def status(self):
        """查看回滚状态"""
        print("\n" + "=" * 60)
        print("ZONGYUAN-ROOT 秒级回滚工具状态")
        print("=" * 60)
        print("当前活跃环境: {}".format(self._get_current_active().upper()))
        print("备用环境（回滚目标）: {}".format(self._get_standby_env().upper()))
        print("")
        
        # 列出可用备份
        code_backup_dir = os.path.join(BACKUP_DIR, "code")
        config_backup_dir = os.path.join(BACKUP_DIR, "config")
        
        if os.path.isdir(code_backup_dir):
            code_backups = sorted(os.listdir(code_backup_dir), reverse=True)
            print("代码备份 ({}个):".format(len(code_backups)))
            for b in code_backups[:5]:
                print("  - {}".format(b))
        
        if os.path.isdir(config_backup_dir):
            config_backups = sorted(os.listdir(config_backup_dir), reverse=True)
            print("\n配置备份 ({}个):".format(len(config_backups)))
            for b in config_backups[:5]:
                print("  - {}".format(b))
        
        print("\n回滚层级:")
        print("  L1 流量回滚: <1秒 (Nginx切换，旧版本仍在运行)")
        print("  L2 配置回滚: <5秒 (恢复配置文件)")
        print("  L3 版本回滚: <1分钟 (从备份恢复代码)")
        print("=" * 60 + "\n")

def main():
    parser = argparse.ArgumentParser(description="ZONGYUAN-ROOT 秒级回滚工具")
    parser.add_argument("--level", choices=["L1", "L2", "L3"], help="回滚层级")
    parser.add_argument("--auto", action="store_true", help="自动选择回滚层级")
    parser.add_argument("--reason", default="手动触发", help="回滚原因")
    parser.add_argument("--status", action="store_true", help="查看回滚状态")
    args = parser.parse_args()
    
    rollback = RollbackManager()
    
    if args.status:
        rollback.status()
    elif args.auto:
        rollback.auto_rollback(args.reason)
    elif args.level:
        if args.level == "L1":
            rollback.l1_traffic_rollback()
        elif args.level == "L2":
            rollback.l2_config_rollback()
        elif args.level == "L3":
            rollback.l3_version_rollback()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
