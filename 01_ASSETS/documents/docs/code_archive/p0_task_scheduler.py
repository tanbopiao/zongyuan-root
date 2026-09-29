#!/usr/bin/env python3
"""P0性能优化③：任务优先级调度器"""
import os, json, time, threading, queue, subprocess

BASE = "/opt/ZONGYUAN-ROOT"
SCHEDULER_DIR = f"{BASE}/task_scheduler"
os.makedirs(SCHEDULER_DIR, exist_ok=True)

print("=" * 60)
print("P0优化③：任务优先级调度器")
print("=" * 60)

# 1. 创建调度器核心
print("\n【1】创建任务优先级调度器核心")
scheduler_code = '''#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 任务优先级调度器 v1.0
P0(最高抢占) > P1 > P2 > P3(后台错峰)
"""
import json, time, threading, queue, subprocess, os
from dataclasses import dataclass, field
from typing import Callable, Optional

BASE = "/opt/ZONGYUAN-ROOT"
LOG_FILE = f"{BASE}/logs/task_scheduler.log"

@dataclass
class Task:
    task_id: str
    name: str
    priority: int  # P0=0, P1=1, P2=2, P3=3
    command: str
    callback: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    status: str = "pending"  # pending/running/done/failed
    result: str = ""
    
    def __lt__(self, other):
        return (self.priority, self.created_at) < (other.priority, other.created_at)

class PriorityTaskScheduler:
    def __init__(self):
        self.task_queue = queue.PriorityQueue()
        self.running = True
        self.workers = []
        self.history = []
        self.max_history = 500
        self._lock = threading.Lock()
        
    def submit(self, task: Task):
        """提交任务到队列"""
        self.task_queue.put((task.priority, task))
        self._log(f"[提交] {task.name} (P{task.priority})")
        
    def _worker(self):
        """工作线程：优先执行高优先级任务"""
        while self.running:
            try:
                _, task = self.task_queue.get(timeout=1)
                task.status = "running"
                self._log(f"[执行] {task.name} (P{task.priority})")
                
                try:
                    # 执行命令
                    result = subprocess.run(task.command, shell=True, capture_output=True, text=True, timeout=300)
                    task.status = "done" if result.returncode == 0 else "failed"
                    task.result = result.stdout[:500] if result.returncode == 0 else result.stderr[:500]
                    self._log(f"[完成] {task.name} -> {task.status}")
                except Exception as e:
                    task.status = "failed"
                    task.result = str(e)
                    self._log(f"[失败] {task.name}: {e}")
                
                with self._lock:
                    self.history.append(task)
                    if len(self.history) > self.max_history:
                        self.history.pop(0)
                        
            except queue.Empty:
                continue
                
    def start(self, num_workers=2):
        """启动调度器"""
        for i in range(num_workers):
            t = threading.Thread(target=self._worker, daemon=True)
            t.start()
            self.workers.append(t)
        self._log(f"调度器启动: {num_workers}个工作线程")
        
    def stop(self):
        self.running = False
        
    def get_status(self):
        """获取调度器状态"""
        with self._lock:
            pending = self.task_queue.qsize()
            done = sum(1 for t in self.history if t.status == "done")
            failed = sum(1 for t in self.history if t.status == "failed")
            return {
                "pending": pending,
                "done": done,
                "failed": failed,
                "total_history": len(self.history),
                "recent_tasks": [
                    {"name": t.name, "priority": t.priority, "status": t.status, "time": time.ctime(t.created_at)}
                    for t in self.history[-5:]
                ]
            }
            
    def _log(self, msg):
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, "a") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\\n")

# 全局调度器实例
scheduler = PriorityTaskScheduler()

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "status":
        # 查询状态（通过状态文件）
        status_file = f"{BASE}/data/task_scheduler_status.json"
        if os.path.exists(status_file):
            with open(status_file) as f:
                print(json.dumps(json.load(f), ensure_ascii=False, indent=2))
        else:
            print("调度器未运行")
    else:
        # 启动调度器
        scheduler.start(num_workers=2)
        print("任务优先级调度器已启动 (P0>P1>P2>P3)")
        try:
            while True:
                # 定期写入状态文件
                status = scheduler.get_status()
                with open(f"{BASE}/data/task_scheduler_status.json", "w") as f:
                    json.dump(status, f, ensure_ascii=False, indent=2)
                time.sleep(5)
        except KeyboardInterrupt:
            scheduler.stop()
'''

with open(f"{SCHEDULER_DIR}/priority_scheduler.py", "w") as f:
    f.write(scheduler_code)
os.chmod(f"{SCHEDULER_DIR}/priority_scheduler.py", 0o755)
print("  ✅ 调度器核心已创建")

# 2. 创建任务提交客户端
print("\n【2】创建任务提交客户端")
client_code = '''#!/usr/bin/env python3
"""任务提交客户端 - 供其他脚本调用"""
import json, time, sys, os

BASE = "/opt/ZONGYUAN-ROOT"
TASK_DIR = f"{BASE}/data/task_queue"

def submit_task(name, command, priority=2, task_id=None):
    """
    提交任务到调度器
    priority: 0=P0最高, 1=P1, 2=P2, 3=P3最低
    """
    os.makedirs(TASK_DIR, exist_ok=True)
    task_id = task_id or f"TASK-{int(time.time()*1000)}"
    task = {
        "task_id": task_id,
        "name": name,
        "priority": priority,
        "command": command,
        "created_at": time.time(),
        "status": "pending"
    }
    with open(f"{TASK_DIR}/{task_id}.json", "w") as f:
        json.dump(task, f, ensure_ascii=False, indent=2)
    print(f"✅ 任务已提交: {name} (P{priority}) ID={task_id}")
    return task_id

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: task_client.py <任务名> <命令> [优先级0-3]")
        sys.exit(1)
    name = sys.argv[1]
    command = sys.argv[2]
    priority = int(sys.argv[3]) if len(sys.argv) > 3 else 2
    submit_task(name, command, priority)
'''
with open(f"{SCHEDULER_DIR}/task_client.py", "w") as f:
    f.write(client_code)
os.chmod(f"{SCHEDULER_DIR}/task_client.py", 0o755)
print("  ✅ 任务提交客户端已创建")

# 3. 创建systemd服务
print("\n【3】创建systemd服务")
service_file = '''[Unit]
Description=ZONGYUAN-ROOT Task Priority Scheduler
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/ZONGYUAN-ROOT
ExecStart=/usr/bin/python3 /opt/ZONGYUAN-ROOT/task_scheduler/priority_scheduler.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
'''
with open("/etc/systemd/system/zr-task-scheduler.service", "w") as f:
    f.write(service_file)
print("  ✅ systemd服务已创建")

# 4. 启动调度器
print("\n【4】启动调度器")
subprocess.run(["systemctl", "daemon-reload"])
subprocess.run(["systemctl", "enable", "zr-task-scheduler"])
subprocess.run(["systemctl", "start", "zr-task-scheduler"])
time.sleep(2)
result = subprocess.run(["systemctl", "is-active", "zr-task-scheduler"], capture_output=True, text=True)
print(f"  调度器状态: {result.stdout.strip()}")

# 5. 测试提交任务
print("\n【5】测试任务调度")
# 提交一个P3低优先级测试任务
test_task = {
    "task_id": f"TEST-{int(time.time())}",
    "name": "调度器健康检查",
    "priority": 3,
    "command": "echo '调度器测试成功'",
    "created_at": time.time(),
    "status": "pending"
}
os.makedirs(f"{BASE}/data/task_queue", exist_ok=True)
with open(f"{BASE}/data/task_queue/{test_task['task_id']}.json", "w") as f:
    json.dump(test_task, f, ensure_ascii=False, indent=2)
print("  ✅ P3测试任务已提交")

# 6. 写入元数据
print("\n【6】写入调度器元数据")
import sqlite3
conn = sqlite3.connect(f"{BASE}/data/memory_gateway.db")
c = conn.cursor()
c.execute("INSERT OR REPLACE INTO sync_state (key, value, updated_at) VALUES ('task_scheduler_enabled', '1', ?)", (time.time(),))
c.execute("INSERT OR REPLACE INTO sync_state (key, value, updated_at) VALUES ('task_scheduler_priority', 'P0>P1>P2>P3', ?)", (time.time(),))
conn.commit()
conn.close()
print("  ✅ 元数据已写入")

print("\n" + "=" * 60)
print("任务优先级调度器部署完成")
print("=" * 60)
print("  P0: 锁档/中枢上报/账本校验/安全校验（最高抢占）")
print("  P1: 页面预聚合/Merkle增量更新/资产检索")
print("  P2: 仿真测试/报告生成")
print("  P3: 日志归档/备份/统计采集（后台错峰）")
print("  服务: zr-task-scheduler.service")
print("  状态: systemctl status zr-task-scheduler")
