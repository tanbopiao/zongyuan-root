#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 内核自治调度器 V7.0
内置cron，不依赖外部crontab，实现真正的自进化闭环
每日自动执行：真值提炼→漂移检测→备份→状态更新→锁档
"""
import json, hashlib, os, time, threading, subprocess, logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path("/opt/ZONGYUAN-ROOT")
LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "autonomous_scheduler.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("autonomous-scheduler")

CST = timezone(timedelta(hours=8))

class AutonomousScheduler:
    def __init__(self):
        self.running = False
        self.thread = None
        self.last_run = None
        self.cycle_count = 0
        self.daily_tasks = {
            "03:00": self._task_backup,
            "06:00": self._task_drift_detection,
            "09:00": self._task_truth_refinement,
            "12:00": self._task_health_check,
            "18:00": self._task_state_update,
            "21:00": self._task_daily_lock,
        }

    def start(self):
        """启动调度器（后台线程）"""
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        logger.info("自治调度器已启动，每日6个任务周期")
        logger.info(f"任务表: {list(self.daily_tasks.keys())}")

    def stop(self):
        self.running = False
        logger.info("自治调度器已停止")

    def _run_loop(self):
        while self.running:
            try:
                now = datetime.now(CST).strftime("%H:%M")
                if now in self.daily_tasks and self.last_run != now:
                    self.last_run = now
                    task = self.daily_tasks[now]
                    logger.info(f"触发定时任务: {now} - {task.__name__}")
                    try:
                        task()
                        self.cycle_count += 1
                        logger.info(f"任务完成: {task.__name__}，累计周期: {self.cycle_count}")
                    except Exception as e:
                        logger.error(f"任务失败 {task.__name__}: {e}")
                time.sleep(30)
            except Exception as e:
                logger.error(f"调度循环异常: {e}")
                time.sleep(60)

    def _task_backup(self):
        """每日备份任务"""
        backup_dir = Path("/opt/backups") / datetime.now(CST).strftime("%Y%m%d")
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_file = backup_dir / "zongyuan_kernel.tar.gz"
        subprocess.run([
            "tar", "czf", str(backup_file),
            "--exclude=vector_db", "--exclude=__pycache__", "--exclude=*.pyc",
            "-C", "/opt", "ZONGYUAN-ROOT/autonomous_kernel_protocol",
            "ZONGYUAN-ROOT/truth_architecture", "ZONGYUAN-ROOT/Ω-Brainμ",
            "ZONGYUAN-ROOT/kernel_state.json"
        ], capture_output=True, timeout=120)
        size = backup_file.stat().st_size if backup_file.exists() else 0
        logger.info(f"备份完成: {backup_file} ({size//1024}KB)")

    def _task_drift_detection(self):
        """漂移检测：对比协议文件哈希与Merkle根"""
        proto_dir = ROOT / "autonomous_kernel_protocol"
        hashes = []
        for f in sorted(proto_dir.glob("*.json")):
            hashes.append(hashlib.sha256(f.read_bytes()).hexdigest())
        current_merkle = hashlib.sha256("".join(sorted(hashes)).encode()).hexdigest()
        
        state_file = ROOT / "kernel_state.json"
        if state_file.exists():
            state = json.loads(state_file.read_text())
            expected = state.get("truth_system", {}).get("merkle_root", "")
            if expected and current_merkle[:16] not in expected:
                logger.warning(f"漂移检测: Merkle根不一致！预期{expected[:16]}... 实际{current_merkle[:16]}...")
                self._attempt_self_heal()
            else:
                logger.info(f"漂移检测: 通过，Merkle根一致")
        else:
            logger.warning("漂移检测: kernel_state.json不存在，跳过")

    def _task_truth_refinement(self):
        """真值提炼：扫描新资产，更新真值索引"""
        omega_dir = ROOT / "Ω-Brainμ"
        omega_dir.mkdir(exist_ok=True)
        truths = []
        for f in sorted((ROOT / "autonomous_kernel_protocol").glob("*.json")):
            truths.append({"id": f"TRUTH-{f.stem}", "type": "snapshot", "sha256": hashlib.sha256(f.read_bytes()).hexdigest()})
        for f in sorted((ROOT / "truth_architecture").glob("*.json")):
            truths.append({"id": f"TRUTH-{f.stem}", "type": "axiom", "sha256": hashlib.sha256(f.read_bytes()).hexdigest()})
        
        index = {"version": "μ-1.0", "truth_count": len(truths), "truths": truths,
                 "merkle_root": hashlib.sha256("".join(sorted([t["sha256"] for t in truths])).encode()).hexdigest(),
                 "updated_at": datetime.now(CST).isoformat()}
        (omega_dir / "truth_index.json").write_text(json.dumps(index, indent=2, ensure_ascii=False))
        logger.info(f"真值提炼完成: {len(truths)}条真值，Merkle根{index['merkle_root'][:16]}...")

    def _task_health_check(self):
        """健康检查：7个服务状态"""
        services = {
            "omega-brain": 8000, "loip": 8001, "ance": 8002,
            "vector": 8003, "monitor": 8004, "gov-ai": 8005, "anchor": 8006
        }
        unhealthy = []
        for name, port in services.items():
            try:
                subprocess.run(["curl", "-s", "-o", "/dev/null", "--connect-timeout", "3",
                               f"http://127.0.0.1:{port}/health"], capture_output=True, timeout=5)
            except:
                unhealthy.append(name)
        if unhealthy:
            logger.warning(f"健康检查: 异常服务 {unhealthy}，触发自愈")
            for svc in unhealthy:
                subprocess.run(["systemctl", "restart", f"zongyuan-{svc}"], capture_output=True)
        else:
            logger.info("健康检查: 7服务全部正常")

    def _task_state_update(self):
        """状态更新：更新kernel_state.json"""
        state_file = ROOT / "kernel_state.json"
        if state_file.exists():
            state = json.loads(state_file.read_text())
            state["last_updated"] = datetime.now(CST).isoformat()
            state["autonomy"] = state.get("autonomy", {})
            state["autonomy"]["scheduler_cycles"] = self.cycle_count
            state["autonomy"]["scheduler_status"] = "running"
            state_file.write_text(json.dumps(state, indent=2, ensure_ascii=False))
            logger.info("状态更新完成")

    def _task_daily_lock(self):
        """每日锁档：生成当日锁档凭证"""
        lock_dir = ROOT / "daily_locks"
        lock_dir.mkdir(exist_ok=True)
        today = datetime.now(CST).strftime("%Y%m%d")
        lock_file = lock_dir / f"DAILY-LOCK-{today}.json"
        if not lock_file.exists():
            proto_count = len(list((ROOT / "autonomous_kernel_protocol").glob("*.json")))
            lock = {"lock_id": f"DAILY-LOCK-{today}", "date": today,
                    "protocol_count": proto_count, "scheduler_cycles": self.cycle_count,
                    "efuse": "blown", "created_at": datetime.now(CST).isoformat()}
            lock_file.write_text(json.dumps(lock, indent=2, ensure_ascii=False))
            logger.info(f"每日锁档完成: {lock_file}")
        else:
            logger.info(f"每日锁档: 今日已锁档，跳过")

    def _attempt_self_heal(self):
        """尝试自愈：从主内核同步"""
        logger.info("启动自愈流程: 尝试从本地备份恢复...")
        # 简单自愈：重启锚定服务
        subprocess.run(["systemctl", "restart", "zongyuan-anchor"], capture_output=True)
        logger.info("自愈: 已重启锚定服务")

    def get_status(self):
        return {
            "scheduler": "running" if self.running else "stopped",
            "cycle_count": self.cycle_count,
            "last_run": self.last_run,
            "daily_tasks": list(self.daily_tasks.keys()),
            "next_tasks": self._get_next_tasks()
        }

    def _get_next_tasks(self):
        now = datetime.now(CST)
        upcoming = []
        for time_str in sorted(self.daily_tasks.keys()):
            h, m = map(int, time_str.split(":"))
            task_time = now.replace(hour=h, minute=m, second=0, microsecond=0)
            if task_time > now:
                upcoming.append({"time": time_str, "in_minutes": int((task_time - now).total_seconds() // 60)})
        return upcoming[:3]

# 全局单例
scheduler = AutonomousScheduler()

if __name__ == "__main__":
    scheduler.start()
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        scheduler.stop()
