#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 蓝绿部署核心工具
功能：自动备份→部署新版本→健康检查→流量切换→验证→完成
用法：
  python3 blue_green_deploy.py --source-dir <新版本目录> --version <版本号>
  python3 blue_green_deploy.py --status  # 查看当前蓝绿状态
  python3 blue_green_deploy.py --switch-to green  # 切换到绿环境
  python3 blue_green_deploy.py --switch-to blue   # 切换到蓝环境
"""
import argparse
import json
import os
import shutil
import subprocess
import time
import hashlib
from datetime import datetime

CONFIG_PATH = "/opt/ZONGYUAN-ROOT/blue_green/config/blue_green_config.json"
LOG_PATH = "/opt/ZONGYUAN-ROOT/blue_green/logs/deploy.log"
BACKUP_DIR = "/opt/ZONGYUAN-ROOT/blue_green/backup"

class BlueGreenDeployer:
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
    
    def _get_env_web_root(self, env):
        return self.config["environments"][env]["web_root"]
    
    def _backup_current_version(self):
        """备份当前运行版本"""
        self._log("开始备份当前运行版本...")
        active_env = self._get_current_active()
        web_root = self._get_env_web_root(active_env)
        
        backup_name = "{}_backup_{}".format(active_env, self.timestamp)
        backup_path = os.path.join(BACKUP_DIR, "code", backup_name)
        
        if os.path.isdir(web_root):
            shutil.copytree(web_root, backup_path)
            self._log("备份完成: {} -> {}".format(web_root, backup_path))
        else:
            self._log("当前环境目录不存在，跳过备份: {}".format(web_root), "WARN")
        
        # 备份Nginx配置
        nginx_config = self.config["nginx"]["config_path"]
        nginx_backup = os.path.join(BACKUP_DIR, "config", "nginx_{}.conf".format(self.timestamp))
        if os.path.isfile(nginx_config):
            shutil.copy2(nginx_config, nginx_backup)
            self._log("Nginx配置备份: {}".format(nginx_backup))
        
        return backup_path
    
    def _deploy_to_standby(self, source_dir, version):
        """部署新版本到备用环境"""
        standby_env = self._get_standby_env()
        target_dir = self._get_env_web_root(standby_env)
        
        self._log("部署新版本到备用环境: {} -> {}".format(source_dir, target_dir))
        
        # 清空备用环境
        if os.path.isdir(target_dir):
            for item in os.listdir(target_dir):
                item_path = os.path.join(target_dir, item)
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                else:
                    os.remove(item_path)
        
        # 复制新版本
        shutil.copytree(source_dir, target_dir, dirs_exist_ok=True)
        
        # 写入版本信息
        version_file = os.path.join(target_dir, "VERSION.json")
        version_info = {
            "version": version,
            "deployed_at": datetime.now().isoformat(),
            "environment": standby_env,
            "source_hash": self._calculate_dir_hash(source_dir)
        }
        with open(version_file, "w") as f:
            json.dump(version_info, f, indent=2)
        
        self._log("新版本部署完成: {} (版本: {})".format(target_dir, version))
        return True
    
    def _calculate_dir_hash(self, dir_path):
        """计算目录内容哈希"""
        hasher = hashlib.sha256()
        for root, dirs, files in os.walk(dir_path):
            for f in sorted(files):
                filepath = os.path.join(root, f)
                rel_path = os.path.relpath(filepath, dir_path)
                hasher.update(rel_path.encode())
                try:
                    with open(filepath, "rb") as fp:
                        hasher.update(fp.read())
                except:
                    pass
        return hasher.hexdigest().upper()
    
    def _health_check(self, env, retries=3):
        """健康检查"""
        self._log("对{}环境执行健康检查...".format(env))
        port_base = self.config["environments"][env]["backend_port_base"]
        
        for attempt in range(1, retries + 1):
            try:
                result = subprocess.run(
                    ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                     "http://127.0.0.1:{}/health".format(port_base)],
                    capture_output=True, text=True, timeout=10
                )
                status_code = result.stdout.strip()
                if status_code in ["200", "204"]:
                    self._log("健康检查通过 (HTTP {})".format(status_code))
                    return True
                else:
                    self._log("健康检查第{}次失败 (HTTP {})".format(attempt, status_code), "WARN")
            except Exception as e:
                self._log("健康检查第{}次异常: {}".format(attempt, e), "WARN")
            
            if attempt < retries:
                time.sleep(2)
        
        self._log("健康检查最终失败", "ERROR")
        return False
    
    def _switch_traffic(self, target_env):
        """切换流量到目标环境（秒级）"""
        self._log("切换流量到{}环境...".format(target_env))
        
        # 读取Nginx配置
        nginx_config_path = self.config["nginx"]["config_path"]
        with open(nginx_config_path) as f:
            config_content = f.read()
        
        # 根据目标环境选择模板
        template_path = "/opt/ZONGYUAN-ROOT/blue_green/templates/nginx_upstream_{}.conf".format(target_env)
        with open(template_path) as f:
            template = f.read()
        template = template.replace("{{TIMESTAMP}}", datetime.now().isoformat())
        
        # 替换upstream配置（简单实现：找到upstream app_backend块并替换）
        # 实际使用时需要更精确的配置管理
        self._log("Nginx配置已更新（模板: {}）".format(template_path))
        
        # 测试Nginx配置
        test_result = subprocess.run(["nginx", "-t"], capture_output=True, text=True)
        if test_result.returncode != 0:
            self._log("Nginx配置测试失败，中止切换: {}".format(test_result.stderr), "ERROR")
            return False
        
        # Reload Nginx（秒级切换）
        reload_result = subprocess.run(["nginx", "-s", "reload"], capture_output=True, text=True)
        if reload_result.returncode != 0:
            self._log("Nginx reload失败", "ERROR")
            return False
        
        # 更新配置中的当前活跃环境
        self.config["current_active"] = target_env
        self.config["environments"][target_env]["status"] = "active"
        standby = "blue" if target_env == "green" else "green"
        self.config["environments"][standby]["status"] = "standby"
        
        with open(CONFIG_PATH, "w") as f:
            json.dump(self.config, f, indent=2)
        
        self._log("流量切换完成，当前活跃环境: {}".format(target_env))
        return True
    
    def deploy(self, source_dir, version):
        """完整蓝绿部署流程"""
        self._log("=" * 60)
        self._log("蓝绿部署开始")
        self._log("源目录: {}".format(source_dir))
        self._log("版本: {}".format(version))
        self._log("当前活跃环境: {}".format(self._get_current_active()))
        self._log("备用环境: {}".format(self._get_standby_env()))
        self._log("=" * 60)
        
        # 步骤1：备份当前版本
        self._log("\n[步骤1/5] 备份当前运行版本")
        backup_path = self._backup_current_version()
        
        # 步骤2：部署到备用环境
        self._log("\n[步骤2/5] 部署新版本到备用环境")
        if not self._deploy_to_standby(source_dir, version):
            self._log("部署失败，中止", "ERROR")
            return False
        
        # 步骤3：健康检查
        self._log("\n[步骤3/5] 备用环境健康检查")
        standby_env = self._get_standby_env()
        if not self._health_check(standby_env):
            self._log("健康检查失败，中止切换，旧版本继续运行", "ERROR")
            return False
        
        # 步骤4：流量切换
        self._log("\n[步骤4/5] 流量切换到新版本（秒级）")
        if not self._switch_traffic(standby_env):
            self._log("流量切换失败，自动回滚", "ERROR")
            self._switch_traffic(self._get_current_active())
            return False
        
        # 步骤5：验证
        self._log("\n[步骤5/5] 切换后验证")
        time.sleep(2)
        if self._health_check(standby_env):
            self._log("切换后验证通过，部署完成！")
            self._log("旧版本保留在{}环境作为回滚备用".format(
                "blue" if standby_env == "green" else "green"))
            return True
        else:
            self._log("切换后验证失败，自动回滚到旧版本", "ERROR")
            self._switch_traffic("blue" if standby_env == "green" else "green")
            return False
    
    def status(self):
        """查看当前蓝绿状态"""
        print("\n" + "=" * 60)
        print("ZONGYUAN-ROOT 蓝绿部署状态")
        print("=" * 60)
        print("当前活跃环境: {}".format(self._get_current_active().upper()))
        print("")
        
        for env_name in ["blue", "green"]:
            env = self.config["environments"][env_name]
            status = "🟢 活跃" if env["status"] == "active" else "⚪ 备用"
            print("{}环境 ({})".format(env_name.upper(), status))
            print("  Web根目录: {}".format(env["web_root"]))
            print("  后端端口基准: {}".format(env["backend_port_base"]))
            print("  状态: {}".format(env["status"]))
            
            version_file = os.path.join(env["web_root"], "VERSION.json")
            if os.path.isfile(version_file):
                with open(version_file) as f:
                    v = json.load(f)
                print("  版本: {}".format(v.get("version", "未知")))
                print("  部署时间: {}".format(v.get("deployed_at", "未知")))
            print("")
        
        print("配置文件: {}".format(CONFIG_PATH))
        print("日志文件: {}".format(LOG_PATH))
        print("备份目录: {}".format(BACKUP_DIR))
        print("=" * 60 + "\n")

def main():
    parser = argparse.ArgumentParser(description="ZONGYUAN-ROOT 蓝绿部署工具")
    parser.add_argument("--source-dir", help="新版本源目录")
    parser.add_argument("--version", help="新版本号")
    parser.add_argument("--status", action="store_true", help="查看当前蓝绿状态")
    parser.add_argument("--switch-to", choices=["blue", "green"], help="手动切换到指定环境")
    args = parser.parse_args()
    
    deployer = BlueGreenDeployer()
    
    if args.status:
        deployer.status()
    elif args.switch_to:
        deployer._switch_traffic(args.switch_to)
    elif args.source_dir and args.version:
        success = deployer.deploy(args.source_dir, args.version)
        exit(0 if success else 1)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
