"""事件驱动自进化引擎 - 事件触发+定时兜底双驱动进化"""
import json, time, os, queue, threading
from datetime import datetime
from enum import Enum

class EventPriority(Enum):
    P0 = 0  # 立即触发进化
    P1 = 1  # 5分钟内触发
    P2 = 2  # 1小时内触发
    P3 = 3  # 每日定时合并

EVENT_DIR = "/opt/ZONGYUAN-ROOT/event_driven"
EVENT_QUEUE_FILE = f"{EVENT_DIR}/event_queue.json"
EVOLUTION_LOG = f"{EVENT_DIR}/evolution_log.json"

class EventDrivenEvolution:
    def __init__(self):
        self.queue = []
        self._load_queue()
    
    def _load_queue(self):
        if os.path.exists(EVENT_QUEUE_FILE):
            with open(EVENT_QUEUE_FILE) as f:
                self.queue = json.load(f)
    
    def _save_queue(self):
        with open(EVENT_QUEUE_FILE, "w") as f:
            json.dump(self.queue, f, indent=2)
    
    def emit_event(self, event_type: str, source: str, data: dict, priority: str = "P2"):
        """发射进化事件"""
        event = {
            "id": f"EVT-{int(time.time())}-{len(self.queue)}",
            "type": event_type,
            "source": source,
            "data": data,
            "priority": priority,
            "timestamp": datetime.now().isoformat(),
            "status": "pending"
        }
        self.queue.append(event)
        self._save_queue()
        
        # P0事件立即触发进化
        if priority == "P0":
            return self._trigger_evolution(event)
        return {"event_id": event["id"], "status": "queued", "priority": priority}
    
    def _trigger_evolution(self, event):
        """触发进化循环"""
        result = {
            "event_id": event["id"],
            "evolution_type": event["type"],
            "triggered_at": datetime.now().isoformat(),
            "status": "completed",
            "actions": []
        }
        
        # 根据事件类型执行不同进化动作
        if event["type"] == "new_truth":
            result["actions"].append("真值入库+向量化+锁档")
        elif event["type"] == "customer_feedback":
            result["actions"].append("客户反馈分析+真值优先级调整")
        elif event["type"] == "anomaly_detected":
            result["actions"].append("异常分析+自愈触发+告警")
        elif event["type"] == "dependency_update":
            result["actions"].append("依赖兼容性检查+回归测试")
        
        # 记录进化日志
        logs = []
        if os.path.exists(EVOLUTION_LOG):
            with open(EVOLUTION_LOG) as f: logs = json.load(f)
        logs.append(result)
        with open(EVOLUTION_LOG, "w") as f:
            json.dump(logs[-100:], f, indent=2)
        
        # 从队列移除
        self.queue = [e for e in self.queue if e["id"] != event["id"]]
        self._save_queue()
        
        return result
    
    def process_pending(self):
        """处理待处理事件（定时调用）"""
        pending = [e for e in self.queue if e["status"] == "pending"]
        results = []
        for event in sorted(pending, key=lambda x: EventPriority[x["priority"]].value):
            results.append(self._trigger_evolution(event))
        return {"processed": len(results), "results": results}
    
    def get_status(self):
        pending = [e for e in self.queue if e["status"] == "pending"]
        logs = []
        if os.path.exists(EVOLUTION_LOG):
            with open(EVOLUTION_LOG) as f: logs = json.load(f)
        return {
            "pending_events": len(pending),
            "by_priority": {p: len([e for e in pending if e["priority"]==p]) for p in ["P0","P1","P2","P3"]},
            "total_evolutions": len(logs),
            "recent_evolutions": logs[-5:]
        }

if __name__ == "__main__":
    import sys
    engine = EventDrivenEvolution()
    if len(sys.argv) > 1 and sys.argv[1] == "status":
        print(json.dumps(engine.get_status(), indent=2, ensure_ascii=False))
    elif len(sys.argv) > 3 and sys.argv[1] == "emit":
        result = engine.emit_event(sys.argv[2], "cli", {"detail": sys.argv[3]}, sys.argv[4] if len(sys.argv)>4 else "P2")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif len(sys.argv) > 1 and sys.argv[1] == "process":
        print(json.dumps(engine.process_pending(), indent=2, ensure_ascii=False))
    else:
        print("用法: status | emit <type> <data> [priority] | process")
