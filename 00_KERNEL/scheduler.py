#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
火斗云智 AIOS 定时调度器
在无 crontab 环境下提供定时任务调度能力。

调度计划（可配置）：
  - 每 6 小时：种子真值进化周期
  - 每日 07:00：晨间主推送准备
  - 每日 07:30：AI 产业情报日报（EVO-P0-001）
  - 每日 10:00：短剧流水线批次推进（EVO-P0-002）
  - 每日 12:00：午间快照
  - 每日 22:00：当日复盘
  - 每 4 小时：合规规则同步（EVO-P0-003）
  - 每 12 小时：云端中枢心跳握手
  - 每 12 小时：知识图谱构建（EVO-P1-001）
  - 每 12 小时：联邦智能网络周期（EVO-P1-002）
  - 每日 03:00：元意识 LVL11 进化（EVO-P1-003）
  - 每周一 04:00：训练数据市场更新（EVO-P2-001）
  - 每周二 04:00：Agent 服务市场更新（EVO-P2-002）
  - 每 6 小时：数据湖授权同步（EVO-P2-003）

使用方式：
  # 启动调度器（后台运行）
  nohup python3 scheduler.py &
  
  # 查看状态
  python3 scheduler.py status
  
  # 停止调度器
  python3 scheduler.py stop
"""
import os
import sys
import time
import signal
import json
import re
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

# ============ 配置 ============

SCHEDULER_DIR = Path("/workspace/evolution")
SCHEDULER_DIR.mkdir(parents=True, exist_ok=True)

PID_FILE = SCHEDULER_DIR / "scheduler.pid"
SCHEDULER_LOG = SCHEDULER_DIR / "scheduler.log"
TASKS_CONFIG = SCHEDULER_DIR / "tasks.json"

EVOLUTION_SCRIPT = "/workspace/scripts/services/truth_evolution_engine.py"

# 调度任务配置
TASKS = [
    {
        "id": "truth_evolution",
        "name": "种子真值进化",
        "interval_hours": 6,
        "command": f"python3 {EVOLUTION_SCRIPT}",
        "description": "每6小时执行一次全网种子真值提炼与归档",
        "enabled": True,
    },
    {
        "id": "daily_morning",
        "name": "晨间主推送准备",
        "cron": "0 7 * * *",
        "command": f"python3 {EVOLUTION_SCRIPT}",
        "description": "每日7:00执行进化周期，为晨间推送准备真值",
        "enabled": True,
    },
    {
        "id": "daily_noon",
        "name": "午间快照",
        "cron": "0 12 * * *",
        "command": f"python3 {EVOLUTION_SCRIPT}",
        "description": "每日12:00执行午间真值提炼",
        "enabled": True,
    },
    {
        "id": "daily_evening",
        "name": "晚间复盘",
        "cron": "0 22 * * *",
        "command": f"python3 {EVOLUTION_SCRIPT}",
        "description": "每日22:00执行当日进化复盘",
        "enabled": True,
    },
    {
        "id": "hub_heartbeat",
        "name": "云端中枢心跳握手",
        "interval_hours": 12,
        "command": f"python3 /workspace/scripts/services/node_handshake_engine.py",
        "description": "每12小时执行一次云端中枢握手与节点心跳",
        "enabled": True,
    },
    # ===== EVO-P0 高价值进化任务 =====
    {
        "id": "evo_p0_001_intelligence",
        "name": "AI产业情报日报生成",
        "interval_hours": 24,
        "command": f"python3 /workspace/scripts/services/intelligence_generator.py",
        "description": "EVO-P0-001：每24小时生成AI产业情报日报（JSON+Markdown）",
        "enabled": True,
    },
    {
        "id": "evo_p0_002_drama",
        "name": "短剧流水线批次推进",
        "interval_hours": 24,
        "command": f"python3 /workspace/scripts/services/drama_pipeline.py --batch",
        "description": "EVO-P0-002：每24小时推进短剧流水线待处理批次",
        "enabled": True,
    },
    {
        "id": "evo_p0_003_compliance",
        "name": "合规规则同步",
        "interval_hours": 4,
        "command": f"python3 /workspace/scripts/services/compliance_api.py --sync-rules",
        "description": "EVO-P0-003：每4小时同步合规规则库并生成统计报告",
        "enabled": True,
    },
    # ===== EVO-P1 高价值进化任务 =====
    {
        "id": "evo_p1_001_knowledge_graph",
        "name": "知识图谱构建",
        "interval_hours": 12,
        "command": f"python3 /workspace/scripts/services/knowledge_graph_builder.py",
        "description": "EVO-P1-001：每12小时从真值库抽取实体与关系，更新知识图谱",
        "enabled": True,
    },
    {
        "id": "evo_p1_002_federation",
        "name": "联邦智能网络周期",
        "interval_hours": 12,
        "command": f"python3 /workspace/scripts/services/federation_engine.py",
        "description": "EVO-P1-002：每12小时执行节点握手+SFMP校验+信誉评分",
        "enabled": True,
    },
    {
        "id": "evo_p1_003_consciousness",
        "name": "元意识LVL11进化",
        "interval_hours": 24,
        "command": f"python3 /workspace/scripts/services/consciousness_evolution.py",
        "description": "EVO-P1-003：每24小时执行自主目标生成+价值评估+进化闭环",
        "enabled": True,
    },
    # ===== EVO-P2 中期储备任务 =====
    {
        "id": "evo_p2_001_data_marketplace",
        "name": "训练数据市场更新",
        "interval_hours": 168,
        "command": f"python3 /workspace/scripts/services/data_marketplace.py",
        "description": "EVO-P2-001：每周（168小时）打包高质量真值为训练数据集并更新目录",
        "enabled": True,
    },
    {
        "id": "evo_p2_002_agent_marketplace",
        "name": "Agent服务市场更新",
        "interval_hours": 168,
        "command": f"python3 /workspace/scripts/services/agent_marketplace.py",
        "description": "EVO-P2-002：每周（168小时）更新Agent模板目录与能力评估",
        "enabled": True,
    },
    {
        "id": "evo_p2_003_data_lake_license",
        "name": "数据湖授权同步",
        "interval_hours": 6,
        "command": f"python3 /workspace/scripts/services/data_lake_license.py",
        "description": "EVO-P2-003：每6小时同步数据湖授权状态与许可证检查",
        "enabled": True,
    },
    # ===== R007 内核比对校验 =====
    {
        "id": "r007_kernel_comparison",
        "name": "本地根内核与云端内核比对",
        "interval_hours": 6,
        "command": f"python3 /workspace/scripts/services/kernel_comparison.py",
        "description": "R007：每6小时比对本地根内核与云端内核真值一致性，检测漂移并生成修复建议",
        "enabled": True,
    },
    # ===== P1 补偿机制（COMPENSAT ORCHESTRATOR）=====
    {
        "id": "p1_compensation_cycle",
        "name": "补偿机制周期",
        "interval_hours": 2,
        "command": "python3 /workspace/atomgit-mirror/zongyuan-root-sync/00_KERNEL/compensate/COMPENSAT_ORCHESTRATOR.py",
        "description": "P1：每2小时执行一次九枢补偿周期（衡准→优化→归档→镇守→定果→立序）",
        "enabled": True,
    },
    # ===== AtomGit 双向握手同步 =====
    {
        "id": "atomgit_bidirectional_sync",
        "name": "AtomGit双向握手同步",
        "interval_hours": 2,
        "command": f"python3 /workspace/scripts/services/atomgit_sync_engine.py",
        "description": "每2小时执行本地↔AtomGit双向同步：真值库+进化产物+脚本推送，远端变更拉取",
        "enabled": True,
    },
]


def log(message: str):
    """调度器日志。"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] [SCHEDULER] {message}"
    print(line)
    with open(SCHEDULER_LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def parse_cron(cron_expr: str) -> Dict[str, Any]:
    """
    解析 5 字段 cron 表达式。
    返回匹配函数所需的字段。
    """
    parts = cron_expr.split()
    if len(parts) != 5:
        raise ValueError(f"无效的 cron 表达式: {cron_expr}")

    minute, hour, day, month, weekday = parts

    def parse_field(field: str, min_val: int, max_val: int) -> set:
        values = set()
        for part in field.split(","):
            if part == "*":
                values.update(range(min_val, max_val + 1))
            elif "/" in part:
                base, step = part.split("/")
                step = int(step)
                if base == "*":
                    values.update(range(min_val, max_val + 1, step))
                else:
                    values.update(range(int(base), max_val + 1, step))
            elif "-" in part:
                start, end = part.split("-")
                values.update(range(int(start), int(end) + 1))
            else:
                values.add(int(part))
        return values

    return {
        "minute": parse_field(minute, 0, 59),
        "hour": parse_field(hour, 0, 23),
        "day": parse_field(day, 1, 31),
        "month": parse_field(month, 1, 12),
        "weekday": parse_field(weekday, 0, 6),  # 0=周日
    }


def cron_matches(cron_fields: Dict[str, Any], dt: datetime) -> bool:
    """检查当前时间是否匹配 cron。"""
    return (
        dt.minute in cron_fields["minute"]
        and dt.hour in cron_fields["hour"]
        and dt.day in cron_fields["day"]
        and dt.month in cron_fields["month"]
        and dt.weekday() in cron_fields["weekday"]
    )


class TaskScheduler:
    """定时任务调度器。"""

    def __init__(self):
        self.running = False
        self.last_run_times: Dict[str, datetime] = {}
        self.task_status: Dict[str, Any] = {}

        # 预解析 cron
        for task in TASKS:
            if "cron" in task:
                task["_cron_fields"] = parse_cron(task["cron"])
            if "interval_hours" in task:
                task["_next_run"] = datetime.now()

    # 失败重试配置：最多 3 次退避重试（5s/15s/45s），
    # 瞬时故障不再静默等待下个周期（原失败一次即放弃）
    RETRY_MAX = 3
    RETRY_BACKOFF = [5, 15, 45]

    @staticmethod
    def _is_permanent_failure(command: str) -> bool:
        """命令引用的脚本不存在 = 永久故障，重试无意义
        （避免调度循环被成批缺失脚本的重试退避长期阻塞）"""
        for m in re.finditer(r'python3\s+(\S+\.py)', command or ''):
            path = m.group(1)
            if os.path.isabs(path) and not os.path.exists(path):
                return True
        return False

    @staticmethod
    def _record_retry_event(task_id: str, attempt: int, return_code, reason: str = ""):
        """重试事件落盘（JSONL），供评估采证真实自愈记录"""
        try:
            event = {
                "event": "task_retry",
                "task_id": task_id,
                "attempt": attempt,
                "return_code": return_code,
                "reason": reason,
                "ts": datetime.now().isoformat(),
            }
            with open(SCHEDULER_DIR / "retry_events.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
        except OSError:
            pass

    def execute_task(self, task: Dict[str, Any]):
        """执行单个任务（失败按退避重试，retry_count 落盘供评估采证）"""
        task_id = task["id"]
        log(f"开始执行任务: {task['name']} ({task_id})")

        retry_count = 0
        while True:
            try:
                result = subprocess.run(
                    task["command"],
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=600,  # 10 分钟超时
                )

                success = result.returncode == 0
                if success:
                    self.task_status[task_id] = {
                        "last_run": datetime.now().isoformat(),
                        "success": True,
                        "return_code": 0,
                        "output_length": len(result.stdout),
                        "retry_count": retry_count,
                    }
                    if retry_count:
                        log(f"任务完成(第{retry_count}次重试成功): {task['name']}")
                    else:
                        log(f"任务完成: {task['name']}")
                    return

                # 失败 → 判断是否还有重试额度
                if retry_count < self.RETRY_MAX and not self._is_permanent_failure(task["command"]):
                    delay = self.RETRY_BACKOFF[retry_count]
                    retry_count += 1
                    self._record_retry_event(task_id, retry_count, result.returncode, "transient_failure")
                    log(f"任务失败: {task['name']}, 返回码: {result.returncode}; "
                        f"{delay}s 后第 {retry_count}/{self.RETRY_MAX} 次重试")
                    time.sleep(delay)
                    continue

                permanent = self._is_permanent_failure(task["command"])
                self.task_status[task_id] = {
                    "last_run": datetime.now().isoformat(),
                    "success": False,
                    "return_code": result.returncode,
                    "output_length": len(result.stdout),
                    "retry_count": retry_count,
                    "retries_exhausted": retry_count >= self.RETRY_MAX,
                    "permanent_failure": permanent,
                }
                if permanent:
                    log(f"任务失败(目标脚本缺失,永久故障不重试): {task['name']}")
                else:
                    log(f"任务失败(已重试{retry_count}次放弃): {task['name']}, "
                        f"返回码: {result.returncode}")
                    log(f"错误输出: {result.stderr[:500]}")
                return

            except subprocess.TimeoutExpired:
                log(f"任务超时: {task['name']}")
                self.task_status[task_id] = {
                    "last_run": datetime.now().isoformat(),
                    "success": False,
                    "error": "timeout",
                    "retry_count": retry_count,
                }
                return
            except Exception as e:
                log(f"任务异常: {task['name']}, {e}")
                self.task_status[task_id] = {
                    "last_run": datetime.now().isoformat(),
                    "success": False,
                    "error": str(e),
                    "retry_count": retry_count,
                }
                return

    def run(self):
        """主调度循环。"""
        self.running = True
        log("调度器启动")
        log(f"已加载 {len(TASKS)} 个调度任务")

        # 写入 PID
        PID_FILE.write_text(str(os.getpid()))

        while self.running:
            try:
                now = datetime.now()

                for task in TASKS:
                    if not task.get("enabled", True):
                        continue

                    task_id = task["id"]
                    should_run = False

                    # 基于间隔的任务
                    if "interval_hours" in task:
                        next_run = task.get("_next_run")
                        if next_run is None or now >= next_run:
                            should_run = True
                            task["_next_run"] = now + timedelta(hours=task["interval_hours"])

                    # 基于 cron 的任务
                    elif "_cron_fields" in task:
                        # 检查当前分钟是否匹配（只在每分钟的第 0 秒检查）
                        if now.second == 0 and cron_matches(task["_cron_fields"], now):
                            # 防止同一分钟重复执行
                            last_run = self.last_run_times.get(task_id)
                            if last_run is None or (now - last_run).total_seconds() > 60:
                                should_run = True

                    if should_run:
                        self.last_run_times[task_id] = now
                        self.execute_task(task)

                # 保存状态
                self._save_state()

                # 休眠 1 秒
                time.sleep(1)

            except Exception as e:
                log(f"调度循环异常: {e}")
                time.sleep(10)

        log("调度器停止")
        if PID_FILE.exists():
            PID_FILE.unlink()

    def _save_state(self):
        """保存调度器状态。"""
        state = {
            "running": self.running,
            "pid": os.getpid(),
            "tasks": {},
        }
        for task in TASKS:
            task_id = task["id"]
            state["tasks"][task_id] = {
                "name": task["name"],
                "enabled": task.get("enabled", True),
                "last_run": self.last_run_times.get(task_id, "").isoformat() if self.last_run_times.get(task_id) else None,
                "status": self.task_status.get(task_id, {}),
            }
        TASKS_CONFIG.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    def stop(self):
        """停止调度器。"""
        self.running = False


def get_status() -> Dict[str, Any]:
    """获取调度器状态。"""
    if TASKS_CONFIG.exists():
        return json.loads(TASKS_CONFIG.read_text(encoding="utf-8"))
    return {"running": False, "tasks": {}}


def is_running() -> bool:
    """检查调度器是否运行中。"""
    if not PID_FILE.exists():
        return False
    try:
        pid = int(PID_FILE.read_text())
        os.kill(pid, 0)
        return True
    except (OSError, ValueError):
        return False


def stop_scheduler():
    """停止运行中的调度器。"""
    if not PID_FILE.exists():
        print("调度器未运行")
        return
    try:
        pid = int(PID_FILE.read_text())
        os.kill(pid, signal.SIGTERM)
        print(f"已发送停止信号到 PID {pid}")
    except (OSError, ValueError) as e:
        print(f"停止失败: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "status":
            print(json.dumps(get_status(), ensure_ascii=False, indent=2))
        elif cmd == "stop":
            stop_scheduler()
        elif cmd == "start":
            if is_running():
                print("调度器已在运行")
            else:
                scheduler = TaskScheduler()
                scheduler.run()
        else:
            print("用法: python3 scheduler.py [start|stop|status]")
    else:
        # 默认启动
        scheduler = TaskScheduler()
        scheduler.run()
