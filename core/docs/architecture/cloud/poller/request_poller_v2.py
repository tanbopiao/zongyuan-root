#!/usr/bin/env python3
"""
云内核中枢请求轮询服务 v2.0（生产级加固版）
DID-BR-000002 | ZONGYUAN-ROOT | Ω₀⊂⊙∞⊂Ω

v2.0 新增特性：
- 日志分级（INFO/WARN/ERROR）
- 飞书告警推送
- 任务幂等机制（避免重复执行）
- 任务超时自动回收
- 死任务检测
"""
import json
import os
import time
import hashlib
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from enum import Enum


class LogLevel(Enum):
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"


# 配置
REPO_DIR = "/opt/ZONGYUAN-ROOT"
POLL_INTERVAL = 60  # 轮询间隔（秒）
REQUESTS_DIR = Path(REPO_DIR) / "cloud" / "requests"
RESPONSES_DIR = Path(REPO_DIR) / "cloud" / "responses"
PROCESSED_DIR = Path(REPO_DIR) / "cloud" / "processed"
AUDIT_LOG = Path(REPO_DIR) / "cloud" / "poller_audit.log"
TASK_TIMEOUT = 3600  # 任务超时时间（秒）= 1小时
FEISHU_WEBHOOK = ""  # 飞书告警webhook，配置后启用


class PollerV2:
    def __init__(self):
        self.ensure_dirs()
        self.running_tasks = {}  # task_id -> start_time

    def ensure_dirs(self):
        """确保目录存在"""
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    def log(self, msg: str, level: LogLevel = LogLevel.INFO):
        """分级日志"""
        ts = datetime.now().isoformat()
        line = f"[{ts}][{level.value}] {msg}"
        print(line)
        with open(AUDIT_LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")

        # ERROR级别推送飞书告警
        if level == LogLevel.ERROR and FEISHU_WEBHOOK:
            self.send_alert(msg)

    def send_alert(self, message: str):
        """飞书告警推送"""
        if not FEISHU_WEBHOOK:
            return
        try:
            import urllib.request
            data = json.dumps({
                "msg_type": "text",
                "content": {"text": f"🔴 轮询服务告警: {message}"}
            }).encode("utf-8")
            req = urllib.request.Request(
                FEISHU_WEBHOOK,
                data=data,
                headers={"Content-Type": "application/json"}
            )
            urllib.request.urlopen(req, timeout=5)
        except Exception as e:
            self.log(f"飞书告警推送失败: {e}", LogLevel.WARN)

    def run_cmd(self, cmd: str, timeout: int = 60) -> tuple:
        """执行shell命令"""
        try:
            result = subprocess.run(
                cmd, shell=True, cwd=REPO_DIR,
                capture_output=True, text=True, timeout=timeout
            )
            return result.returncode == 0, (result.stdout + result.stderr).strip()
        except Exception as e:
            return False, str(e)

    def git_pull(self) -> bool:
        """拉取最新代码"""
        ok, out = self.run_cmd("git pull origin main", timeout=30)
        if not ok:
            ok, out = self.run_cmd("git pull gitee main", timeout=30)
        return ok

    def git_push(self):
        """推送结果"""
        self.run_cmd("git add -A", timeout=10)
        self.run_cmd(f'git commit -m "AUTO: poller v2 {datetime.now().isoformat()}"', timeout=10)
        self.run_cmd("git push origin main", timeout=30)
        self.run_cmd("git push gitee main", timeout=30)

    def get_web_root(self) -> str:
        """查找Web根目录"""
        candidates = [
            "/www/wwwroot/www.huodouai.com",
            "/www/wwwroot/huodouai.com",
        ]
        for path in candidates:
            if os.path.isdir(path) and os.path.exists(os.path.join(path, "index.html")):
                return path
        return None

    def is_processed(self, req_id: str) -> bool:
        """检查任务是否已处理（幂等）"""
        response_file = RESPONSES_DIR / f"RES_{req_id}.json"
        processed_file = PROCESSED_DIR / f"REQ_{req_id}.json"
        return response_file.exists() or processed_file.exists()

    def mark_processed(self, req_id: str):
        """标记任务已处理"""
        # 移动请求文件到processed目录
        req_file = REQUESTS_DIR / f"REQ_{req_id}.json"
        if req_file.exists():
            processed_file = PROCESSED_DIR / f"REQ_{req_id}.json"
            req_file.rename(processed_file)

    def check_timeout_tasks(self):
        """检查超时任务"""
        now = time.time()
        timeout_tasks = []
        for task_id, start_time in list(self.running_tasks.items()):
            if now - start_time > TASK_TIMEOUT:
                timeout_tasks.append(task_id)
                self.log(f"任务超时: {task_id}，已运行{int(now-start_time)}秒", LogLevel.WARN)
                del self.running_tasks[task_id]
        return timeout_tasks

    def execute_request(self, request_file: Path):
        """执行单个请求"""
        try:
            with open(request_file, "r", encoding="utf-8") as f:
                req = json.load(f)
        except Exception as e:
            self.log(f"读取请求失败: {request_file.name} - {e}", LogLevel.ERROR)
            return

        req_id = req.get("request_id", "UNKNOWN").replace("REQ_", "")
        action = req.get("action", "")
        params = req.get("params", {})

        # 幂等检查
        if self.is_processed(req_id):
            self.log(f"已处理，跳过: {req_id}")
            return

        self.log(f"收到请求: {req_id} | action={action}")

        result = {
            "request_id": req_id,
            "executed_at": datetime.now().isoformat(),
            "status": "PENDING",
            "output": ""
        }

        # 记录到运行中
        self.running_tasks[req_id] = time.time()

        try:
            # 执行部署任务
            if action in ["DEPLOY_WEB_PAGE", "DEPLOY_STATIC_PAGE"]:
                web_root = self.get_web_root()
                if not web_root:
                    result["status"] = "FAILED"
                    result["output"] = "未找到Web根目录"
                    self.log("未找到Web根目录", LogLevel.ERROR)
                else:
                    self.log(f"Web根目录: {web_root}")
                    self.run_cmd(f"mkdir -p {web_root}/static/diff", timeout=10)
                    src = f"{REPO_DIR}/showcase-page/differential_capabilities_v2.html"
                    dst = f"{web_root}/diff.html"
                    ok, out = self.run_cmd(f"cp {src} {dst}", timeout=10)

                    if ok:
                        self.run_cmd(f"chmod 644 {dst}", timeout=5)
                        result["status"] = "SUCCESS"
                        result["output"] = f"部署完成: {dst}"
                        self.log(f"部署成功: {dst}", LogLevel.INFO)
                    else:
                        result["status"] = "FAILED"
                        result["output"] = f"复制失败: {out}"
                        self.log(f"部署失败: {out}", LogLevel.ERROR)
            else:
                result["status"] = "UNKNOWN_ACTION"
                result["output"] = f"未知动作: {action}"
                self.log(f"未知动作: {action}", LogLevel.WARN)

        except Exception as e:
            result["status"] = "ERROR"
            result["output"] = str(e)
            self.log(f"任务异常: {e}", LogLevel.ERROR)
        finally:
            # 从运行中移除
            if req_id in self.running_tasks:
                del self.running_tasks[req_id]

        # 写入响应
        response_file = RESPONSES_DIR / f"RES_{req_id}.json"
        with open(response_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        # 标记已处理
        self.mark_processed(req_id)

        self.log(f"响应已写入: RES_{req_id}.json")

    def poll_once(self):
        """执行一次轮询"""
        self.log("=" * 50)

        # 检查超时任务
        self.check_timeout_tasks()

        # git pull
        ok = self.git_pull()
        if not ok:
            self.log("git pull 失败", LogLevel.WARN)

        # 读取请求
        if not REQUESTS_DIR.exists():
            self.log("requests目录不存在")
            return

        request_files = sorted(REQUESTS_DIR.glob("REQ_*.json"))
        if not request_files:
            self.log("无新请求")
            return

        self.log(f"发现 {len(request_files)} 个请求")

        for req_file in request_files:
            self.execute_request(req_file)

        # git push
        self.git_push()
        self.log("轮询完成，响应已推送")

    def run_forever(self):
        """永久运行"""
        self.log("🚀 轮询服务v2启动")
        self.log(f"📂 项目: {REPO_DIR}")
        self.log(f"⏱️ 间隔: {POLL_INTERVAL}秒")
        self.log("=" * 60)

        while True:
            try:
                self.poll_once()
            except Exception as e:
                self.log(f"轮询异常: {e}", LogLevel.ERROR)
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    poller = PollerV2()
    poller.run_forever()
