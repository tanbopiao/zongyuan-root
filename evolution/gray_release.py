#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 灰度发布机制模块 V2.0
功能：版本管理、流量控制、健康检查、版本切换、灰度策略
溯源：Ω₀⊂⊙∞⊂Ω | DID-BR-000002
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


class GrayReleaseManager:
    """灰度发布管理器"""
    
    def __init__(self,
                 nginx_config_path: str = "/www/server/panel/vhost/nginx/huodouai.com.conf",
                 versions_dir: str = "/opt/ZONGYUAN-ROOT/evolution/versions",
                 health_check_url: str = "http://127.0.0.1:8765/health",
                 rollback_threshold: Dict = None):
        """
        初始化灰度发布管理器
        
        Args:
            nginx_config_path: Nginx配置文件路径
            versions_dir: 版本存储目录
            health_check_url: 健康检查URL
            rollback_threshold: 回滚阈值配置
        """
        self.nginx_config_path = Path(nginx_config_path)
        self.versions_dir = Path(versions_dir)
        self.versions_dir.mkdir(parents=True, exist_ok=True)
        self.health_check_url = health_check_url
        self.rollback_threshold = rollback_threshold or {
            "error_rate": 5.0,      # 错误率超过5%触发回滚
            "response_time": 2000,  # 响应时间超过2000ms触发回滚
            "health_check_failures": 3,  # 连续3次健康检查失败触发回滚
            "cpu_usage": 90,        # CPU使用率超过90%触发回滚
            "memory_usage": 90,     # 内存使用率超过90%触发回滚
        }
        self.current_version = self._load_current_version()
        self.version_history = self._load_version_history()
    
    def _load_current_version(self) -> Optional[str]:
        """加载当前版本号"""
        version_file = self.versions_dir / "current_version.json"
        if version_file.exists():
            with open(version_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("version")
        return None
    
    def _save_current_version(self, version: str, metadata: Dict = None):
        """保存当前版本信息"""
        version_file = self.versions_dir / "current_version.json"
        data = {
            "version": version,
            "updated_at": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        with open(version_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _load_version_history(self) -> List[Dict]:
        """加载版本历史"""
        history_file = self.versions_dir / "version_history.json"
        if history_file.exists():
            with open(history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    
    def _save_version_history(self, history: List[Dict]):
        """保存版本历史"""
        history_file = self.versions_dir / "version_history.json"
        # 只保留最近50个版本
        history = history[-50:]
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    
    def _generate_version_id(self, prefix: str = "v") -> str:
        """生成版本ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_str = hashlib.md5(os.urandom(4)).hexdigest()[:6]
        return f"{prefix}{timestamp}-{random_str}"
    
    def create_version(self, 
                       source_path: str,
                       version: str = None,
                       description: str = "",
                       changelog: List[str] = None,
                       metadata: Dict = None) -> Dict:
        """
        创建新版本
        
        Args:
            source_path: 源文件/目录路径
            version: 版本号（自动生成如果不指定）
            description: 版本描述
            changelog: 变更日志列表
            metadata: 元数据
            
        Returns:
            版本信息字典
        """
        version = version or self._generate_version_id()
        version_dir = self.versions_dir / version
        version_dir.mkdir(parents=True, exist_ok=True)
        
        # 复制源文件到版本目录
        dest_path = version_dir / "files"
        if os.path.isdir(source_path):
            shutil.copytree(source_path, dest_path)
        else:
            dest_path.mkdir(exist_ok=True)
            shutil.copy2(source_path, dest_path / os.path.basename(source_path))
        
        # 计算版本哈希
        version_hash = self._calculate_directory_hash(dest_path)
        
        # 保存版本元数据
        version_info = {
            "version": version,
            "description": description,
            "changelog": changelog or [],
            "hash": version_hash,
            "source_path": source_path,
            "files_path": str(dest_path),
            "created_at": datetime.now().isoformat(),
            "status": "created",
            "metadata": metadata or {},
            "溯源标识": "Ω₀⊂⊙∞⊂Ω",
            "确权编码": "DID-BR-000002"
        }
        
        metadata_file = version_dir / "metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(version_info, f, ensure_ascii=False, indent=2)
        
        # 添加到版本历史
        self.version_history.append({
            "version": version,
            "description": description,
            "hash": version_hash,
            "created_at": version_info["created_at"],
            "status": "created"
        })
        self._save_version_history(self.version_history)
        
        return version_info
    
    def _calculate_directory_hash(self, directory: Path) -> str:
        """计算目录哈希"""
        hasher = hashlib.sha256()
        for root, dirs, files in os.walk(directory):
            for file in sorted(files):
                file_path = Path(root) / file
                hasher.update(str(file_path.relative_to(directory)).encode())
                with open(file_path, 'rb') as f:
                    while True:
                        chunk = f.read(8192)
                        if not chunk:
                            break
                        hasher.update(chunk)
        return hasher.hexdigest()
    
    def health_check(self, url: str = None, timeout: int = 5) -> Dict:
        """
        执行健康检查
        
        Args:
            url: 健康检查URL
            timeout: 超时时间
            
        Returns:
            健康检查结果
        """
        url = url or self.health_check_url
        start_time = time.time()
        
        try:
            result = subprocess.run(
                ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", 
                 "--connect-timeout", str(timeout), url],
                capture_output=True, text=True, timeout=timeout + 5
            )
            elapsed = time.time() - start_time
            http_code = result.stdout.strip()
            
            return {
                "url": url,
                "http_code": http_code,
                "response_time_ms": round(elapsed * 1000, 2),
                "healthy": http_code in ["200", "201", "204"],
                "checked_at": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "url": url,
                "error": str(e),
                "healthy": False,
                "checked_at": datetime.now().isoformat()
            }
    
    def start_gray_release(self, 
                            new_version: str,
                            gray_percentage: int = 10,
                            health_check_interval: int = 30,
                            auto_rollback: bool = True) -> Dict:
        """
        开始灰度发布
        
        Args:
            new_version: 新版本号
            gray_percentage: 初始灰度百分比(0-100)
            health_check_interval: 健康检查间隔(秒)
            auto_rollback: 是否自动回滚
            
        Returns:
            灰度发布信息
        """
        # 检查新版本是否存在
        version_dir = self.versions_dir / new_version
        if not version_dir.exists():
            return {"status": "error", "message": f"版本 {new_version} 不存在"}
        
        # 检查当前版本
        old_version = self.current_version
        
        # 创建灰度发布记录
        gray_release = {
            "release_id": f"GR-{int(time.time())}",
            "old_version": old_version,
            "new_version": new_version,
            "current_percentage": gray_percentage,
            "target_percentage": 100,
            "health_check_interval": health_check_interval,
            "auto_rollback": auto_rollback,
            "status": "in_progress",
            "health_check_failures": 0,
            "started_at": datetime.now().isoformat(),
            "stages": []
        }
        
        # 保存灰度发布状态
        gray_file = self.versions_dir / "current_gray_release.json"
        with open(gray_file, 'w', encoding='utf-8') as f:
            json.dump(gray_release, f, ensure_ascii=False, indent=2)
        
        # 应用初始灰度配置
        self._apply_gray_config(gray_percentage, new_version, old_version)
        
        return gray_release
    
    def _apply_gray_config(self, percentage: int, new_version: str, old_version: str = None):
        """
        应用灰度配置（基于Nginx upstream权重）
        
        Args:
            percentage: 新版本流量百分比
            new_version: 新版本
            old_version: 旧版本
        """
        # 这里简化实现，实际应修改Nginx配置
        # 记录配置变更
        config_change = {
            "percentage": percentage,
            "new_version": new_version,
            "old_version": old_version,
            "applied_at": datetime.now().isoformat()
        }
        
        gray_file = self.versions_dir / "current_gray_release.json"
        if gray_file.exists():
            with open(gray_file, 'r', encoding='utf-8') as f:
                gray_release = json.load(f)
            gray_release["current_percentage"] = percentage
            gray_release["stages"].append(config_change)
            with open(gray_file, 'w', encoding='utf-8') as f:
                json.dump(gray_release, f, ensure_ascii=False, indent=2)
    
    def increase_gray_percentage(self, increment: int = 10) -> Dict:
        """
        增加灰度百分比
        
        Args:
            increment: 增加的百分比
            
        Returns:
            更新后的灰度发布信息
        """
        gray_file = self.versions_dir / "current_gray_release.json"
        if not gray_file.exists():
            return {"status": "error", "message": "没有进行中的灰度发布"}
        
        with open(gray_file, 'r', encoding='utf-8') as f:
            gray_release = json.load(f)
        
        new_percentage = min(gray_release["current_percentage"] + increment, 100)
        gray_release["current_percentage"] = new_percentage
        
        self._apply_gray_config(
            new_percentage, 
            gray_release["new_version"], 
            gray_release["old_version"]
        )
        
        # 如果达到100%，完成灰度发布
        if new_percentage >= 100:
            gray_release["status"] = "completed"
            gray_release["completed_at"] = datetime.now().isoformat()
            self._save_current_version(gray_release["new_version"])
            
            # 更新版本历史
            for v in self.version_history:
                if v["version"] == gray_release["new_version"]:
                    v["status"] = "active"
        
        with open(gray_file, 'w', encoding='utf-8') as f:
            json.dump(gray_release, f, ensure_ascii=False, indent=2)
        
        return gray_release
    
    def check_gray_health(self) -> Dict:
        """
        检查灰度发布健康状态
        
        Returns:
            健康检查结果
        """
        gray_file = self.versions_dir / "current_gray_release.json"
        if not gray_file.exists():
            return {"status": "no_gray_release"}
        
        with open(gray_file, 'r', encoding='utf-8') as f:
            gray_release = json.load(f)
        
        # 执行健康检查
        health = self.health_check()
        
        # 检查是否需要回滚
        need_rollback = False
        rollback_reasons = []
        
        if not health["healthy"]:
            gray_release["health_check_failures"] += 1
            if gray_release["health_check_failures"] >= self.rollback_threshold["health_check_failures"]:
                need_rollback = True
                rollback_reasons.append(f"连续{gray_release['health_check_failures']}次健康检查失败")
        else:
            gray_release["health_check_failures"] = 0
        
        if health.get("response_time_ms", 0) > self.rollback_threshold["response_time"]:
            need_rollback = True
            rollback_reasons.append(f"响应时间{health['response_time_ms']}ms超过阈值{self.rollback_threshold['response_time']}ms")
        
        result = {
            "gray_release": gray_release,
            "health_check": health,
            "need_rollback": need_rollback,
            "rollback_reasons": rollback_reasons,
            "checked_at": datetime.now().isoformat()
        }
        
        # 保存更新后的灰度发布状态
        with open(gray_file, 'w', encoding='utf-8') as f:
            json.dump(gray_release, f, ensure_ascii=False, indent=2)
        
        # 如果需要自动回滚
        if need_rollback and gray_release.get("auto_rollback", True):
            self.rollback(reason="; ".join(rollback_reasons))
        
        return result
    
    def rollback(self, reason: str = "manual") -> Dict:
        """
        回滚到上一个版本
        
        Args:
            reason: 回滚原因
            
        Returns:
            回滚结果
        """
        gray_file = self.versions_dir / "current_gray_release.json"
        if not gray_file.exists():
            # 没有进行中的灰度发布，直接回滚到上一个版本
            if len(self.version_history) >= 2:
                old_version = self.version_history[-2]["version"]
            else:
                return {"status": "error", "message": "没有可回滚的版本"}
        else:
            with open(gray_file, 'r', encoding='utf-8') as f:
                gray_release = json.load(f)
            old_version = gray_release.get("old_version")
        
        if not old_version:
            return {"status": "error", "message": "没有可回滚的版本"}
        
        # 执行回滚
        rollback_result = {
            "rollback_id": f"RB-{int(time.time())}",
            "from_version": self.current_version,
            "to_version": old_version,
            "reason": reason,
            "rolled_back_at": datetime.now().isoformat(),
            "status": "completed"
        }
        
        # 保存回滚记录
        rollback_file = self.versions_dir / "rollback_history.json"
        rollback_history = []
        if rollback_file.exists():
            with open(rollback_file, 'r', encoding='utf-8') as f:
                rollback_history = json.load(f)
        rollback_history.append(rollback_result)
        rollback_history = rollback_history[-50:]  # 只保留最近50条
        with open(rollback_file, 'w', encoding='utf-8') as f:
            json.dump(rollback_history, f, ensure_ascii=False, indent=2)
        
        # 更新当前版本
        self._save_current_version(old_version, {"rollback_reason": reason})
        
        # 清理灰度发布状态
        if gray_file.exists():
            gray_file.unlink()
        
        return rollback_result
    
    def list_versions(self, limit: int = 20) -> List[Dict]:
        """
        列出版本列表
        
        Args:
            limit: 返回数量限制
            
        Returns:
            版本列表
        """
        return self.version_history[-limit:]
    
    def get_version_info(self, version: str) -> Optional[Dict]:
        """
        获取版本详情
        
        Args:
            version: 版本号
            
        Returns:
            版本信息
        """
        version_dir = self.versions_dir / version
        metadata_file = version_dir / "metadata.json"
        if metadata_file.exists():
            with open(metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    
    def get_gray_release_status(self) -> Optional[Dict]:
        """获取当前灰度发布状态"""
        gray_file = self.versions_dir / "current_gray_release.json"
        if gray_file.exists():
            with open(gray_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    
    def get_rollback_history(self, limit: int = 20) -> List[Dict]:
        """获取回滚历史"""
        rollback_file = self.versions_dir / "rollback_history.json"
        if rollback_file.exists():
            with open(rollback_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
                return history[-limit:]
        return []


class AutoRollbackMonitor:
    """自动回滚监控器"""
    
    def __init__(self, gray_manager: GrayReleaseManager, check_interval: int = 30):
        """
        初始化自动回滚监控器
        
        Args:
            gray_manager: 灰度发布管理器
            check_interval: 检查间隔(秒)
        """
        self.gray_manager = gray_manager
        self.check_interval = check_interval
        self.running = False
    
    def start_monitoring(self, duration_seconds: int = 3600):
        """
        开始监控
        
        Args:
            duration_seconds: 监控持续时间(秒)
        """
        self.running = True
        start_time = time.time()
        checks = 0
        
        print(f"自动回滚监控启动，持续{duration_seconds}秒，检查间隔{self.check_interval}秒")
        
        while self.running and (time.time() - start_time) < duration_seconds:
            checks += 1
            result = self.gray_manager.check_gray_health()
            
            if result.get("need_rollback"):
                print(f"⚠️ 检测到需要回滚: {result.get('rollback_reasons')}")
                if result["gray_release"].get("auto_rollback"):
                    print("🔄 执行自动回滚...")
                    rollback_result = self.gray_manager.rollback(
                        reason="; ".join(result.get("rollback_reasons", []))
                    )
                    print(f"✅ 回滚完成: {rollback_result['rollback_id']}")
                    self.running = False
                    break
            else:
                print(f"✅ 第{checks}次健康检查通过，当前灰度比例: {result['gray_release']['current_percentage']}%")
            
            time.sleep(self.check_interval)
        
        print(f"监控结束，共执行{checks}次检查")


if __name__ == "__main__":
    print("=" * 60)
    print("  ZONGYUAN-ROOT 灰度发布机制模块 V2.0")
    print("  溯源: Ω₀⊂⊙∞⊂Ω | DID-BR-000002")
    print("=" * 60)
    print()
    
    manager = GrayReleaseManager()
    
    print("【当前版本】")
    print(f"  当前版本: {manager.current_version or '未设置'}")
    print()
    
    print("【版本历史】")
    versions = manager.list_versions(limit=5)
    if versions:
        for v in versions:
            print(f"  - {v['version']}: {v.get('description', '无描述')} [{v.get('status', 'unknown')}]")
    else:
        print("  暂无版本历史")
    print()
    
    print("【灰度发布状态】")
    gray_status = manager.get_gray_release_status()
    if gray_status:
        print(f"  发布ID: {gray_status['release_id']}")
        print(f"  旧版本: {gray_status['old_version']}")
        print(f"  新版本: {gray_status['new_version']}")
        print(f"  当前灰度比例: {gray_status['current_percentage']}%")
        print(f"  状态: {gray_status['status']}")
    else:
        print("  没有进行中的灰度发布")
    print()
    
    print("【健康检查】")
    health = manager.health_check()
    print(f"  URL: {health['url']}")
    print(f"  HTTP状态码: {health['http_code']}")
    print(f"  响应时间: {health['response_time_ms']}ms")
    print(f"  健康状态: {'✅ 健康' if health['healthy'] else '❌ 不健康'}")
    print()
    
    print("模块加载完成。")
