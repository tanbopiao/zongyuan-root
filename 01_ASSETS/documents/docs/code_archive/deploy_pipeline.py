#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 官网模块自动部署流水线
Website Module Auto-Deployment Pipeline

全闭环流程：
1. 模块注册（Register）
2. 中枢评估（Evaluate）
3. 导航定位（Navigate）
4. 备份当前（Backup）
5. 部署文件（Deploy）
6. 健康检查（HealthCheck）
7. 失败回滚（Rollback）
8. 标记完成（MarkDeployed）
9. 上报中枢（Report）
"""
import json
import shutil
import hashlib
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field

MODULE_DIR = Path(__file__).parent.resolve()
DEPLOY_DIR = MODULE_DIR / "deploy"
LOG_DIR = MODULE_DIR / "logs"
DEPLOY_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)


@dataclass
class DeployResult:
    """部署结果"""
    module_id: str
    success: bool
    stage: str
    message: str
    backup_path: str = ""
    deployed_path: str = ""
    url: str = ""
    health_check_passed: bool = False
    duration_seconds: float = 0.0
    deployed_at: str = ""


class DeploymentPipeline:
    """自动部署流水线"""

    def __init__(self, web_root: str = "/var/www/huodouai",
                 backup_dir: str = "/var/www/huodouai_backups",
                 domain: str = "https://www.huodouai.com"):
        self.web_root = Path(web_root)
        self.backup_dir = Path(backup_dir)
        self.domain = domain
        self.pipeline_log = LOG_DIR / f"deploy_pipeline_{datetime.now().strftime('%Y-%m-%d')}.log"

    def _log(self, stage: str, message: str, level: str = "INFO"):
        """记录流水线日志"""
        entry = f"[{datetime.now().isoformat()}] [{level}] [{stage}] {message}\n"
        with open(self.pipeline_log, 'a', encoding='utf-8') as f:
            f.write(entry)
        print(f"  [{stage}] {message}")

    def _file_hash(self, file_path: Path) -> str:
        """计算文件哈希"""
        if not file_path.exists():
            return ""
        return hashlib.sha256(file_path.read_bytes()).hexdigest()[:16]

    def backup_current(self, module_path: str) -> str:
        """
        阶段4：备份当前文件
        部署前先备份现有文件，支持回滚
        """
        target = self.web_root / module_path.lstrip("/")
        if not target.exists():
            self._log("BACKUP", f"目标文件不存在，无需备份: {module_path}")
            return ""

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{target.name}.{timestamp}.bak"
        backup_path = self.backup_dir / backup_name
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        if target.is_file():
            shutil.copy2(target, backup_path)
        else:
            shutil.copytree(target, backup_path)

        self._log("BACKUP", f"已备份: {target} -> {backup_path}")
        return str(backup_path)

    def deploy_files(self, source_path: str, module_path: str) -> bool:
        """
        阶段5：部署文件
        将源文件复制到web根目录对应路径
        """
        source = Path(source_path)
        target = self.web_root / module_path.lstrip("/")

        if not source.exists():
            self._log("DEPLOY", f"源文件不存在: {source_path}", "ERROR")
            return False

        # 确保目标目录存在
        target.parent.mkdir(parents=True, exist_ok=True)

        # 复制文件
        if source.is_file():
            shutil.copy2(source, target)
        else:
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(source, target)

        file_hash = self._file_hash(target)
        self._log("DEPLOY", f"部署完成: {source} -> {target} 哈希:{file_hash}")
        return True

    def health_check(self, url: str, retries: int = 3, delay: float = 2.0) -> bool:
        """
        阶段6：健康检查
        验证部署后页面可正常访问
        """
        import urllib.request
        import urllib.error

        for attempt in range(1, retries + 1):
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'ZONGYUAN-DeployBot/1.0'})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    if resp.status == 200:
                        self._log("HEALTH_CHECK", f"健康检查通过: {url} (HTTP {resp.status}) 尝试{attempt}")
                        return True
                    else:
                        self._log("HEALTH_CHECK", f"HTTP状态异常: {resp.status}", "WARN")
            except urllib.error.HTTPError as e:
                self._log("HEALTH_CHECK", f"HTTP错误: {e.code} (尝试{attempt}/{retries})", "WARN")
            except Exception as e:
                self._log("HEALTH_CHECK", f"检查异常: {str(e)} (尝试{attempt}/{retries})", "WARN")

            if attempt < retries:
                time.sleep(delay)

        self._log("HEALTH_CHECK", f"健康检查失败: {url}", "ERROR")
        return False

    def rollback(self, backup_path: str, module_path: str) -> bool:
        """
        阶段7：失败回滚
        健康检查失败时，从备份恢复
        """
        if not backup_path:
            self._log("ROLLBACK", "无备份文件，无法回滚", "ERROR")
            return False

        backup = Path(backup_path)
        target = self.web_root / module_path.lstrip("/")

        if not backup.exists():
            self._log("ROLLBACK", f"备份文件不存在: {backup_path}", "ERROR")
            return False

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            if backup.is_file():
                shutil.copy2(backup, target)
            else:
                if target.exists():
                    shutil.rmtree(target)
                shutil.copytree(backup, target)
            self._log("ROLLBACK", f"回滚成功: {backup} -> {target}")
            return True
        except Exception as e:
            self._log("ROLLBACK", f"回滚失败: {str(e)}", "ERROR")
            return False

    def run_full_pipeline(self, module_id: str, source_path: str,
                           module_path: str, module_name: str = "") -> DeployResult:
        """
        执行完整部署流水线
        """
        start_time = time.time()
        self._log("PIPELINE_START", f"开始部署模块: {module_id} ({module_name})")

        url = f"{self.domain}/{module_path.lstrip('/')}"

        # 阶段4：备份
        backup_path = self.backup_current(module_path)

        # 阶段5：部署
        deploy_success = self.deploy_files(source_path, module_path)
        if not deploy_success:
            return DeployResult(
                module_id=module_id, success=False, stage="DEPLOY",
                message="文件部署失败", duration_seconds=time.time() - start_time,
                deployed_at=datetime.now().isoformat()
            )

        # 阶段6：健康检查
        health_passed = self.health_check(url)

        # 阶段7：失败回滚
        if not health_passed:
            self._log("ROLLBACK_TRIGGER", "健康检查失败，触发回滚", "WARN")
            rollback_success = self.rollback(backup_path, module_path)
            return DeployResult(
                module_id=module_id, success=False, stage="HEALTH_CHECK",
                message=f"健康检查失败，已回滚: {'成功' if rollback_success else '失败'}",
                backup_path=backup_path, health_check_passed=False,
                duration_seconds=time.time() - start_time,
                deployed_at=datetime.now().isoformat()
            )

        duration = time.time() - start_time
        self._log("PIPELINE_COMPLETE",
                  f"部署完成: {module_id} URL:{url} 耗时:{duration:.2f}s")

        return DeployResult(
            module_id=module_id, success=True, stage="COMPLETE",
            message=f"部署成功，健康检查通过",
            backup_path=backup_path, deployed_path=str(self.web_root / module_path.lstrip("/")),
            url=url, health_check_passed=True,
            duration_seconds=duration, deployed_at=datetime.now().isoformat()
        )

    def get_deploy_history(self, limit: int = 20) -> List[Dict]:
        """获取部署历史"""
        history_file = LOG_DIR / "deploy_history.json"
        if not history_file.exists():
            return []
        with open(history_file, 'r', encoding='utf-8') as f:
            history = json.load(f)
        return history[-limit:]

    def record_deploy(self, result: DeployResult):
        """记录部署结果"""
        history_file = LOG_DIR / "deploy_history.json"
        history = []
        if history_file.exists():
            with open(history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
        history.append({
            "module_id": result.module_id,
            "success": result.success,
            "stage": result.stage,
            "message": result.message,
            "url": result.url,
            "duration": result.duration_seconds,
            "deployed_at": result.deployed_at
        })
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    # 测试部署流水线（仿真模式，不实际部署）
    print("ZONGYUAN-ROOT 官网模块自动部署流水线")
    print("=" * 50)

    pipeline = DeploymentPipeline(
        web_root="/tmp/test_www",
        backup_dir="/tmp/test_backup",
        domain="http://localhost:8080"
    )

    # 创建测试文件
    test_source = Path("/tmp/test_module.html")
    test_source.write_text("<html><body><h1>Test Module</h1></body></html>")

    # 运行仿真部署
    result = pipeline.run_full_pipeline(
        module_id="test-module",
        source_path=str(test_source),
        module_path="/test/index.html",
        module_name="测试模块"
    )

    print(f"\n部署结果: {'成功' if result.success else '失败'}")
    print(f"阶段: {result.stage}")
    print(f"消息: {result.message}")
    print(f"耗时: {result.duration_seconds:.2f}s")
