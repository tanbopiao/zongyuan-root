#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
集群Worker基础框架
元极恒一内核 L3 AIoA 多智能体协同架构
每个Worker都是一个专业智能体，由中枢调度器统一调度
"""

import json
import time
import threading
import logging
from datetime import datetime
from abc import ABC, abstractmethod
import urllib.request

# 配置
GATEWAY_URL = "http://127.0.0.1:9120"
TASK_QUEUE_FILE = "/opt/ZONGYUAN-ROOT/data/cluster_tasks.json"
WORKER_STATE_FILE = "/opt/ZONGYUAN-ROOT/data/worker_states.json"

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler('/opt/ZONGYUAN-ROOT/logs/cluster_workers.log'),
        logging.StreamHandler()
    ]
)

class BaseWorker(ABC):
    """Worker基类 - 所有专业Worker的父类"""
    
    def __init__(self, worker_id, worker_name, worker_type, priority=2):
        self.worker_id = worker_id
        self.worker_name = worker_name
        self.worker_type = worker_type
        self.priority = priority  # P0=0, P1=1, P2=2, P3=3
        self.status = "idle"  # idle/running/paused/error
        self.current_task = None
        self.tasks_completed = 0
        self.tasks_failed = 0
        self.start_time = datetime.now()
        self.last_heartbeat = datetime.now()
        self.logger = logging.getLogger(f"Worker-{worker_id}")
        
    @abstractmethod
    def execute_task(self, task):
        """执行具体任务 - 由子类实现"""
        pass
    
    @abstractmethod
    def get_capabilities(self):
        """返回Worker能处理的任务类型列表"""
        pass
    
    def can_handle(self, task_type):
        """检查是否能处理该类型任务"""
        return task_type in self.get_capabilities()
    
    def run(self):
        """Worker主循环"""
        self.logger.info(f"Worker {self.worker_id} ({self.worker_name}) 启动")
        self.status = "idle"
        self._report_state()
        
        while True:
            try:
                # 获取任务
                task = self._fetch_task()
                if task:
                    self._execute_task_wrapper(task)
                else:
                    # 空闲时执行维护任务
                    self._idle_maintenance()
                    time.sleep(5)
                
                # 心跳
                self.last_heartbeat = datetime.now()
                self._report_state()
                
            except Exception as e:
                self.logger.error(f"Worker循环异常: {e}")
                self.status = "error"
                self._report_state()
                time.sleep(10)
                self.status = "idle"
    
    def _fetch_task(self):
        """从中枢任务队列获取任务"""
        try:
            with open(TASK_QUEUE_FILE, 'r') as f:
                queue = json.load(f)
            
            # 按优先级排序，找到第一个能处理的任务
            for task in sorted(queue.get('pending', []), key=lambda x: x.get('priority', 99)):
                if self.can_handle(task.get('type', '')) and task.get('assigned_to') is None:
                    task['assigned_to'] = self.worker_id
                    task['status'] = 'running'
                    task['started_at'] = datetime.now().isoformat()
                    
                    # 更新队列
                    queue['pending'] = [t for t in queue['pending'] if t['task_id'] != task['task_id']]
                    queue['running'].append(task)
                    
                    with open(TASK_QUEUE_FILE, 'w') as f:
                        json.dump(queue, f, ensure_ascii=False, indent=2)
                    
                    return task
        except Exception as e:
            self.logger.debug(f"获取任务失败: {e}")
        return None
    
    def _execute_task_wrapper(self, task):
        """任务执行包装器 - 包含状态管理和错误处理"""
        self.status = "running"
        self.current_task = task
        self.logger.info(f"开始执行任务: {task.get('task_id')} ({task.get('type')})")
        
        try:
            result = self.execute_task(task)
            self._complete_task(task, result, success=True)
            self.tasks_completed += 1
            self.logger.info(f"任务完成: {task.get('task_id')}")
        except Exception as e:
            self.logger.error(f"任务失败: {task.get('task_id')}, 错误: {e}")
            self._complete_task(task, {"error": str(e)}, success=False)
            self.tasks_failed += 1
        finally:
            self.status = "idle"
            self.current_task = None
    
    def _complete_task(self, task, result, success=True):
        """完成任务，更新队列"""
        try:
            with open(TASK_QUEUE_FILE, 'r') as f:
                queue = json.load(f)
            
            task['status'] = 'completed' if success else 'failed'
            task['result'] = result
            task['completed_at'] = datetime.now().isoformat()
            
            queue['running'] = [t for t in queue['running'] if t['task_id'] != task['task_id']]
            queue['completed'].append(task)
            
            # 限制completed列表长度
            if len(queue['completed']) > 100:
                queue['completed'] = queue['completed'][-100:]
            
            with open(TASK_QUEUE_FILE, 'w') as f:
                json.dump(queue, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"更新任务状态失败: {e}")
    
    def _idle_maintenance(self):
        """空闲时的维护工作 - 子类可重写"""
        pass
    
    def _report_state(self):
        """上报Worker状态到状态文件"""
        try:
            states = {}
            try:
                with open(WORKER_STATE_FILE, 'r') as f:
                    states = json.load(f)
            except:
                pass
            
            states[self.worker_id] = {
                "worker_id": self.worker_id,
                "worker_name": self.worker_name,
                "worker_type": self.worker_type,
                "priority": self.priority,
                "status": self.status,
                "current_task": self.current_task.get('task_id') if self.current_task else None,
                "tasks_completed": self.tasks_completed,
                "tasks_failed": self.tasks_failed,
                "start_time": self.start_time.isoformat(),
                "last_heartbeat": self.last_heartbeat.isoformat(),
                "uptime_seconds": (datetime.now() - self.start_time).total_seconds()
            }
            
            with open(WORKER_STATE_FILE, 'w') as f:
                json.dump(states, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.debug(f"上报状态失败: {e}")
    
    def report_to_gateway(self, key, value, category="worker"):
        """上报真值到9120记忆网关"""
        try:
            data = {
                "key": key,
                "value": json.dumps(value, ensure_ascii=False),
                "category": category,
                "truth_type": "worker_report",
                "confidence": 0.9,
                "locked": False
            }
            req = urllib.request.Request(
                f"{GATEWAY_URL}/api/truth/upsert",
                data=json.dumps(data).encode(),
                headers={"Content-Type": "application/json"}
            )
            urllib.request.urlopen(req, timeout=5)
            return True
        except Exception as e:
            self.logger.debug(f"上报网关失败: {e}")
            return False


class ClusterOrchestrator:
    """中枢调度器 - 统一管理所有Worker"""
    
    def __init__(self):
        self.workers = {}
        self.task_queue = self._load_queue()
        self.logger = logging.getLogger("Orchestrator")
        self.running = False
    
    def _load_queue(self):
        """加载任务队列"""
        try:
            with open(TASK_QUEUE_FILE, 'r') as f:
                return json.load(f)
        except:
            return {"pending": [], "running": [], "completed": []}
    
    def _save_queue(self):
        """保存任务队列"""
        try:
            with open(TASK_QUEUE_FILE, 'w') as f:
                json.dump(self.task_queue, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"保存队列失败: {e}")
    
    def submit_task(self, task_type, payload, priority=2, metadata=None):
        """提交任务到队列"""
        import uuid
        task = {
            "task_id": str(uuid.uuid4())[:8],
            "type": task_type,
            "payload": payload,
            "priority": priority,
            "metadata": metadata or {},
            "status": "pending",
            "assigned_to": None,
            "created_at": datetime.now().isoformat()
        }
        self.task_queue['pending'].append(task)
        self._save_queue()
        self.logger.info(f"任务已提交: {task['task_id']} ({task_type}), 优先级P{priority}")
        return task['task_id']
    
    def get_worker_states(self):
        """获取所有Worker状态"""
        try:
            with open(WORKER_STATE_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    
    def get_cluster_status(self):
        """获取集群整体状态"""
        states = self.get_worker_states()
        return {
            "total_workers": len(states),
            "active_workers": sum(1 for w in states.values() if w['status'] in ['idle', 'running']),
            "running_tasks": len(self.task_queue.get('running', [])),
            "pending_tasks": len(self.task_queue.get('pending', [])),
            "completed_tasks": len(self.task_queue.get('completed', [])),
            "workers": states
        }
    
    def auto_scaling(self):
        """自动扩缩容 - 根据内存和任务量调整Worker数量"""
        # 简化版：检查内存使用，超过阈值时暂停低优先级Worker
        try:
            import psutil
            mem_percent = psutil.virtual_memory().percent
            
            if mem_percent > 85:
                # 内存紧张，暂停P3 Worker
                self.logger.warning(f"内存使用{mem_percent}%，暂停低优先级Worker")
                # 这里可以通过systemctl暂停特定Worker
            elif mem_percent < 50:
                # 内存充足，恢复所有Worker
                pass
        except:
            pass


# 初始化任务队列文件
def init_cluster():
    """初始化集群"""
    import os
    os.makedirs('/opt/ZONGYUAN-ROOT/data', exist_ok=True)
    os.makedirs('/opt/ZONGYUAN-ROOT/logs', exist_ok=True)
    
    # 初始化任务队列
    if not os.path.exists(TASK_QUEUE_FILE):
        with open(TASK_QUEUE_FILE, 'w') as f:
            json.dump({"pending": [], "running": [], "completed": []}, f)
    
    # 初始化Worker状态
    if not os.path.exists(WORKER_STATE_FILE):
        with open(WORKER_STATE_FILE, 'w') as f:
            json.dump({}, f)
    
    print("✅ 集群初始化完成")
    print(f"   任务队列: {TASK_QUEUE_FILE}")
    print(f"   Worker状态: {WORKER_STATE_FILE}")


if __name__ == "__main__":
    init_cluster()
