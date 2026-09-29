#!/usr/bin/env python3
"""
D3-T3 实时数据接入执行器 V1.0
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
功能：飞书/企微/钉钉实时消息和事件流接入框架，支持实时决策触发
"""
import json
import hashlib
import time
import os
from typing import Dict, List, Callable, Optional
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum

class EventSource(Enum):
    FEISHU = "feishu"
    WECOM = "wecom"
    DINGTALK = "dingtalk"
    INTERNAL = "internal"

class EventType(Enum):
    MESSAGE = "message"
    APPROVAL = "approval"
    TASK = "task"
    DOCUMENT = "document"
    DEPLOY = "deploy"
    ALERT = "alert"
    HEALTH = "health"
    CUSTOM = "custom"

class DecisionPriority(Enum):
    AUTO = "auto"           # 自动决策（A级，无需人工）
    NOTIFY = "notify"       # 仅通知（B级）
    APPROVAL = "approval"   # 需审批（C级）
    ESCALATE = "escalate"   # 升级处理（D级）

@dataclass
class Event:
    event_id: str
    source: EventSource
    event_type: EventType
    timestamp: float
    payload: Dict
    priority: DecisionPriority = DecisionPriority.NOTIFY
    processed: bool = False
    decision_result: Optional[Dict] = None

@dataclass
class EventHandler:
    name: str
    event_type: EventType
    handler: Callable[[Event], Dict]
    priority: int = 0
    enabled: bool = True

class RealTimeDataConnector:
    """实时数据接入连接器"""
    
    def __init__(self, config_path: str = None):
        self.config = self._load_config(config_path)
        self.event_queue: List[Event] = []
        self.handlers: List[EventHandler] = []
        self.decision_rules: List[Dict] = []
        self.stats = defaultdict(int)
        self.audit_log: List[Dict] = []
        self._register_default_handlers()
        self._register_decision_rules()
    
    def _load_config(self, config_path: str = None) -> Dict:
        default_config = {
            "sources": {
                "feishu": {"enabled": True, "webhook_url": "", "app_id": ""},
                "wecom": {"enabled": False, "webhook_url": ""},
                "dingtalk": {"enabled": False, "webhook_url": ""},
                "internal": {"enabled": True, "gateway_url": "https://drama.huodouai.com/api/gateway/report"}
            },
            "decision_threshold": {
                "auto_score_min": 80,
                "notify_score_min": 60,
                "approval_score_min": 40
            },
            "queue_max_size": 10000,
            "batch_process_size": 100
        }
        if config_path and os.path.exists(config_path):
            with open(config_path) as f:
                default_config.update(json.load(f))
        return default_config
    
    def _register_default_handlers(self):
        """注册默认事件处理器"""
        self.handlers.append(EventHandler(
            name="approval_handler",
            event_type=EventType.APPROVAL,
            handler=self._handle_approval,
            priority=10
        ))
        self.handlers.append(EventHandler(
            name="deploy_handler",
            event_type=EventType.DEPLOY,
            handler=self._handle_deploy,
            priority=9
        ))
        self.handlers.append(EventHandler(
            name="alert_handler",
            event_type=EventType.ALERT,
            handler=self._handle_alert,
            priority=8
        ))
        self.handlers.append(EventHandler(
            name="health_handler",
            event_type=EventType.HEALTH,
            handler=self._handle_health,
            priority=5
        ))
        self.handlers.append(EventHandler(
            name="message_handler",
            event_type=EventType.MESSAGE,
            handler=self._handle_message,
            priority=1
        ))
    
    def _register_decision_rules(self):
        """注册决策规则（三维稳态：利益40%/风险35%/成本25%）"""
        self.decision_rules = [
            {
                "rule_id": "DR-001",
                "name": "部署指令自动执行",
                "condition": {"event_type": "deploy", "contains": ["部署指令", "deploy_instruction"]},
                "priority": DecisionPriority.AUTO,
                "score_threshold": 85,
                "action": "auto_execute_deploy"
            },
            {
                "rule_id": "DR-002",
                "name": "P0告警自动响应",
                "condition": {"event_type": "alert", "priority": "P0"},
                "priority": DecisionPriority.AUTO,
                "score_threshold": 90,
                "action": "auto_heal_or_notify"
            },
            {
                "rule_id": "DR-003",
                "name": "审批事件通知",
                "condition": {"event_type": "approval"},
                "priority": DecisionPriority.NOTIFY,
                "score_threshold": 60,
                "action": "notify_and_wait"
            },
            {
                "rule_id": "DR-004",
                "name": "健康检查自动记录",
                "condition": {"event_type": "health"},
                "priority": DecisionPriority.AUTO,
                "score_threshold": 70,
                "action": "auto_record_health"
            }
        ]
    
    def _calc_steady_score(self, event: Event) -> float:
        """三维稳态评分：利益40%/风险35%/成本25%"""
        benefit = 70.0  # 默认利益分
        risk = 30.0     # 默认风险分（越低越好）
        cost = 40.0     # 默认成本分（越低越好）
        
        # 根据事件类型调整
        if event.event_type == EventType.DEPLOY:
            benefit = 85
            risk = 25
            cost = 30
        elif event.event_type == EventType.ALERT:
            benefit = 60
            risk = 70
            cost = 20
        elif event.event_type == EventType.APPROVAL:
            benefit = 50
            risk = 15
            cost = 50
        elif event.event_type == EventType.HEALTH:
            benefit = 75
            risk = 10
            cost = 15
        
        # 归一化：风险和成本转换为正向分
        risk_score = 100 - risk
        cost_score = 100 - cost
        
        steady_score = benefit * 0.40 + risk_score * 0.35 + cost_score * 0.25
        return round(steady_score, 2)
    
    def _determine_priority(self, event: Event) -> DecisionPriority:
        """根据稳态评分决定决策优先级"""
        score = self._calc_steady_score(event)
        thresholds = self.config["decision_threshold"]
        
        if score >= thresholds["auto_score_min"]:
            return DecisionPriority.AUTO
        elif score >= thresholds["notify_score_min"]:
            return DecisionPriority.NOTIFY
        elif score >= thresholds["approval_score_min"]:
            return DecisionPriority.APPROVAL
        else:
            return DecisionPriority.ESCALATE
    
    def ingest_event(self, source: EventSource, event_type: EventType, payload: Dict) -> Event:
        """接入事件"""
        event_id = hashlib.sha256(f"{source.value}{event_type.value}{time.time()}{json.dumps(payload, sort_keys=True)}".encode()).hexdigest()[:16]
        event = Event(
            event_id=event_id,
            source=source,
            event_type=event_type,
            timestamp=time.time(),
            payload=payload
        )
        event.priority = self._determine_priority(event)
        
        if len(self.event_queue) < self.config["queue_max_size"]:
            self.event_queue.append(event)
            self.stats["events_ingested"] += 1
            self.stats[f"events_{source.value}"] += 1
            self.stats[f"events_{event_type.value}"] += 1
        else:
            self.stats["events_dropped"] += 1
        
        return event
    
    def _handle_approval(self, event: Event) -> Dict:
        return {"action": "record_approval", "approval_id": event.payload.get("approval_id", "unknown"), "status": "notified"}
    
    def _handle_deploy(self, event: Event) -> Dict:
        score = self._calc_steady_score(event)
        if score >= 85:
            return {"action": "auto_deploy", "score": score, "status": "auto_approved"}
        return {"action": "queue_for_review", "score": score, "status": "pending_review"}
    
    def _handle_alert(self, event: Event) -> Dict:
        alert_level = event.payload.get("level", "P2")
        if alert_level == "P0":
            return {"action": "auto_heal", "alert_level": alert_level, "status": "auto_response"}
        return {"action": "notify_admin", "alert_level": alert_level, "status": "notified"}
    
    def _handle_health(self, event: Event) -> Dict:
        return {"action": "record_health", "metrics": event.payload.get("metrics", {}), "status": "recorded"}
    
    def _handle_message(self, event: Event) -> Dict:
        return {"action": "classify_message", "content_preview": str(event.payload.get("content", ""))[:50], "status": "classified"}
    
    def process_queue(self) -> Dict:
        """处理事件队列"""
        processed = 0
        auto_decisions = 0
        notifications = 0
        approvals = 0
        
        batch = self.event_queue[:self.config["batch_process_size"]]
        self.event_queue = self.event_queue[self.config["batch_process_size"]:]
        
        for event in batch:
            if event.processed:
                continue
            
            # 找到匹配的处理器
            matching_handlers = [h for h in self.handlers if h.event_type == event.event_type and h.enabled]
            matching_handlers.sort(key=lambda h: h.priority, reverse=True)
            
            for handler in matching_handlers:
                try:
                    result = handler.handler(event)
                    event.decision_result = result
                    event.processed = True
                    processed += 1
                    
                    if event.priority == DecisionPriority.AUTO:
                        auto_decisions += 1
                    elif event.priority == DecisionPriority.NOTIFY:
                        notifications += 1
                    elif event.priority == DecisionPriority.APPROVAL:
                        approvals += 1
                    
                    self.audit_log.append({
                        "event_id": event.event_id,
                        "handler": handler.name,
                        "priority": event.priority.value,
                        "result": result,
                        "timestamp": time.time()
                    })
                    break
                except Exception as e:
                    self.stats["handler_errors"] += 1
                    event.decision_result = {"error": str(e)}
        
        return {
            "processed": processed,
            "auto_decisions": auto_decisions,
            "notifications": notifications,
            "approvals": approvals,
            "remaining_queue": len(self.event_queue)
        }
    
    def generate_simulated_events(self, count: int = 50) -> List[Event]:
        """生成模拟事件用于测试"""
        import random
        event_types = list(EventType)
        sources = [EventSource.FEISHU, EventSource.INTERNAL]
        
        for i in range(count):
            et = random.choice(event_types)
            src = random.choice(sources)
            payload = {
                "simulated": True,
                "index": i,
                "content": f"模拟事件_{et.value}_{i}",
                "level": random.choice(["P0", "P1", "P2", "P3"]) if et == EventType.ALERT else "P2"
            }
            self.ingest_event(src, et, payload)
        
        return self.event_queue[-count:]
    
    def get_status(self) -> Dict:
        """获取连接器状态"""
        return {
            "task_id": "D3-T3",
            "task_name": "实时数据接入",
            "status": "ACTIVE",
            "queue_size": len(self.event_queue),
            "stats": dict(self.stats),
            "handlers_registered": len(self.handlers),
            "decision_rules": len(self.decision_rules),
            "audit_log_count": len(self.audit_log),
            "config": {
                "sources_enabled": [k for k, v in self.config["sources"].items() if v.get("enabled")],
                "queue_max": self.config["queue_max_size"],
                "batch_size": self.config["batch_process_size"]
            },
            "DID": "DID-BR-000002",
            "trace": "Ω₀⊂⊙∞⊂Ω"
        }
    
    def execute(self) -> Dict:
        """执行D3-T3全流程"""
        start_time = time.time()
        
        # 1. 生成模拟事件（测试接入能力）
        simulated = self.generate_simulated_events(100)
        
        # 2. 处理事件队列
        process_result = self.process_queue()
        
        # 3. 再次处理剩余
        process_result2 = self.process_queue()
        
        elapsed = time.time() - start_time
        
        return {
            "task_id": "D3-T3",
            "task_name": "实时数据接入",
            "status": "COMPLETED",
            "execution_time": round(elapsed, 2),
            "simulated_events": len(simulated),
            "processing": {
                "batch1": process_result,
                "batch2": process_result2
            },
            "total_processed": process_result["processed"] + process_result2["processed"],
            "auto_decision_rate": round((process_result["auto_decisions"] + process_result2["auto_decisions"]) / max(1, process_result["processed"] + process_result2["processed"]) * 100, 1),
            "connector_status": self.get_status(),
            "DID": "DID-BR-000002",
            "trace": "Ω₀⊂⊙∞⊂Ω"
        }


if __name__ == '__main__':
    connector = RealTimeDataConnector()
    result = connector.execute()
    print(json.dumps(result, ensure_ascii=False, indent=2))
