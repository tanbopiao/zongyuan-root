#!/usr/bin/env python3
"""
昆仑洞天·多模型聚合调度引擎 V1.0
P4-1 生态闭环核心
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | 火斗云智AIOS

统一接入多个AI模型API，实现智能路由、负载均衡、失败降级、成本统计。
支持：视频生成、图像生成、VLMs帧分析、文本生成四大类任务。
"""

import json
import hashlib
import time
import uuid
import os
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Tuple
from enum import Enum
from datetime import datetime, timezone


class ModelType(Enum):
    VIDEO = "video_generation"
    IMAGE = "image_generation"
    VLMS = "vlm_analysis"
    TEXT = "text_generation"


class RouterStrategy(Enum):
    ROUND_ROBIN = "round_robin"      # 轮询
    WEIGHTED = "weighted"             # 加权
    LEAST_COST = "least_cost"         # 最低成本
    BEST_QUALITY = "best_quality"     # 最高质量
    FASTEST = "fastest"               # 最快响应
    AUTO = "auto"                     # 自动（综合评分）


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class ModelProvider:
    """模型提供商配置"""
    provider_id: str
    name: str
    model_type: ModelType
    api_endpoint: str
    api_key_env: str           # 环境变量名，不直接存key
    max_qps: int = 10
    cost_per_call: float = 0.1  # 每次调用成本（元）
    quality_score: float = 8.0  # 质量评分 0-10
    avg_latency_ms: int = 3000  # 平均延迟
    weight: int = 1             # 加权权重
    enabled: bool = True
    failure_count: int = 0
    success_count: int = 0
    total_calls: int = 0
    total_cost: float = 0.0
    circuit_breaker_open: bool = False
    circuit_breaker_reset_at: float = 0

    def get_health_score(self) -> float:
        """健康度评分 0-10"""
        if self.circuit_breaker_open:
            return 0.0
        if self.total_calls == 0:
            return 8.0
        success_rate = self.success_count / self.total_calls
        return round(success_rate * 10, 2)

    def get_composite_score(self, strategy: RouterStrategy) -> float:
        """综合评分，用于路由决策"""
        health = self.get_health_score()
        if strategy == RouterStrategy.LEAST_COST:
            return 10.0 - (self.cost_per_call * 10)
        elif strategy == RouterStrategy.BEST_QUALITY:
            return self.quality_score * (health / 10)
        elif strategy == RouterStrategy.FASTEST:
            return 10.0 - (self.avg_latency_ms / 1000)
        elif strategy == RouterStrategy.WEIGHTED:
            return self.weight * (health / 10)
        else:  # AUTO 综合
            cost_score = max(0, 10 - self.cost_per_call * 10)
            quality_score = self.quality_score
            speed_score = max(0, 10 - self.avg_latency_ms / 1000)
            return round(
                cost_score * 0.25 +
                quality_score * 0.35 +
                speed_score * 0.2 +
                health * 0.2, 2
            )

    def record_call(self, success: bool, cost: float, latency_ms: int):
        """记录一次调用"""
        self.total_calls += 1
        self.total_cost += cost
        if success:
            self.success_count += 1
            self.failure_count = max(0, self.failure_count - 1)
        else:
            self.failure_count += 1
            # 连续失败5次触发熔断
            if self.failure_count >= 5:
                self.circuit_breaker_open = True
                self.circuit_breaker_reset_at = time.time() + 60  # 60秒后恢复

    def check_circuit_breaker(self):
        """检查熔断状态"""
        if self.circuit_breaker_open and time.time() > self.circuit_breaker_reset_at:
            self.circuit_breaker_open = False
            self.failure_count = 0


@dataclass
class Task:
    """调度任务"""
    task_id: str
    task_type: ModelType
    payload: Dict
    priority: int = 2  # 0=最高, 3=最低
    status: TaskStatus = TaskStatus.PENDING
    assigned_provider: Optional[str] = None
    result: Optional[Dict] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    cost: float = 0.0
    latency_ms: int = 0

    def to_dict(self) -> Dict:
        d = asdict(self)
        d['task_type'] = self.task_type.value
        d['status'] = self.status.value
        return d


class ModelRouter:
    """智能路由器"""

    def __init__(self):
        self.providers: Dict[str, ModelProvider] = {}
        self.round_robin_counters: Dict[str, int] = {}
        self.strategy = RouterStrategy.AUTO

    def register_provider(self, provider: ModelProvider):
        """注册模型提供商"""
        self.providers[provider.provider_id] = provider
        self.round_robin_counters[provider.provider_id] = 0

    def get_available_providers(self, task_type: ModelType) -> List[ModelProvider]:
        """获取可用的提供商列表"""
        available = []
        for p in self.providers.values():
            p.check_circuit_breaker()
            if p.enabled and p.model_type == task_type and not p.circuit_breaker_open:
                available.append(p)
        return available

    def route(self, task_type: ModelType, strategy: Optional[RouterStrategy] = None) -> Optional[ModelProvider]:
        """路由选择最优提供商"""
        strat = strategy or self.strategy
        available = self.get_available_providers(task_type)
        if not available:
            return None

        if strat == RouterStrategy.ROUND_ROBIN:
            # 轮询
            type_key = task_type.value
            if type_key not in self.round_robin_counters:
                self.round_robin_counters[type_key] = 0
            idx = self.round_robin_counters[type_key] % len(available)
            self.round_robin_counters[type_key] += 1
            return available[idx]
        else:
            # 按综合评分排序
            scored = [(p, p.get_composite_score(strat)) for p in available]
            scored.sort(key=lambda x: x[1], reverse=True)
            return scored[0][0]

    def get_fallback_provider(self, task_type: ModelType, exclude_id: str) -> Optional[ModelProvider]:
        """获取降级备用提供商"""
        available = self.get_available_providers(task_type)
        fallback = [p for p in available if p.provider_id != exclude_id]
        if not fallback:
            return None
        fallback.sort(key=lambda p: p.get_composite_score(RouterStrategy.AUTO), reverse=True)
        return fallback[0]


class TaskQueue:
    """任务队列管理"""

    def __init__(self, max_concurrent: int = 5):
        self.queue: List[Task] = []
        self.running: List[Task] = []
        self.completed: List[Task] = []
        self.failed: List[Task] = []
        self.max_concurrent = max_concurrent

    def add_task(self, task: Task):
        """添加任务"""
        self.queue.append(task)
        self.queue.sort(key=lambda t: t.priority)

    def get_next_task(self) -> Optional[Task]:
        """获取下一个待执行任务"""
        if len(self.running) >= self.max_concurrent:
            return None
        if not self.queue:
            return None
        task = self.queue.pop(0)
        task.status = TaskStatus.RUNNING
        task.started_at = time.time()
        self.running.append(task)
        return task

    def complete_task(self, task: Task, result: Dict, cost: float):
        """完成任务"""
        task.status = TaskStatus.COMPLETED
        task.result = result
        task.cost = cost
        task.completed_at = time.time()
        task.latency_ms = int((task.completed_at - task.started_at) * 1000)
        if task in self.running:
            self.running.remove(task)
        self.completed.append(task)

    def fail_task(self, task: Task, error: str):
        """任务失败，判断是否重试"""
        task.retry_count += 1
        task.error = error
        if task.retry_count < task.max_retries:
            task.status = TaskStatus.RETRYING
            task.assigned_provider = None
            self.queue.append(task)
            self.queue.sort(key=lambda t: t.priority)
        else:
            task.status = TaskStatus.FAILED
            task.completed_at = time.time()
            if task in self.running:
                self.running.remove(task)
            self.failed.append(task)

    def get_stats(self) -> Dict:
        """队列统计"""
        return {
            "pending": len(self.queue),
            "running": len(self.running),
            "completed": len(self.completed),
            "failed": len(self.failed),
            "total_cost": round(sum(t.cost for t in self.completed), 4),
            "avg_latency_ms": int(sum(t.latency_ms for t in self.completed) / max(1, len(self.completed))),
            "success_rate": round(len(self.completed) / max(1, len(self.completed) + len(self.failed)) * 100, 1)
        }


class MultiModelAggregator:
    """多模型聚合调度引擎主类"""

    def __init__(self, data_dir: str = "./model_aggregator_data"):
        self.router = ModelRouter()
        self.task_queue = TaskQueue(max_concurrent=5)
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self._register_default_providers()

    def _register_default_providers(self):
        """注册默认模型提供商"""
        defaults = [
            # 视频生成
            ModelProvider("seedance_25", "Seedance 2.5", ModelType.VIDEO,
                         "https://api.seedance.com/v2/video", "SEEDANCE_API_KEY",
                         max_qps=5, cost_per_call=0.15, quality_score=9.2, avg_latency_ms=8000, weight=3),
            ModelProvider("kling_16", "可灵AI 1.6", ModelType.VIDEO,
                         "https://api.klingai.com/v1/video", "KLING_API_KEY",
                         max_qps=3, cost_per_call=0.20, quality_score=9.0, avg_latency_ms=10000, weight=2),
            ModelProvider("jimeng_35", "即梦AI 3.5 Pro", ModelType.VIDEO,
                         "https://api.jimeng.com/v1/video", "JIMENG_API_KEY",
                         max_qps=8, cost_per_call=0.10, quality_score=8.5, avg_latency_ms=6000, weight=2),
            ModelProvider("minimax_h3", "MiniMax H3", ModelType.VIDEO,
                         "https://api.minimax.io/v1/video", "MINIMAX_API_KEY",
                         max_qps=4, cost_per_call=0.18, quality_score=8.8, avg_latency_ms=9000, weight=1),
            # 图像生成
            ModelProvider("seedream_50", "Seedream 5.0", ModelType.IMAGE,
                         "https://api.seedance.com/v2/image", "SEEDANCE_API_KEY",
                         max_qps=10, cost_per_call=0.05, quality_score=9.0, avg_latency_ms=3000, weight=3),
            ModelProvider("lib_image_25", "Lib Image 2.5", ModelType.IMAGE,
                         "https://api.liblib.tv/v1/image", "LIBLIB_API_KEY",
                         max_qps=6, cost_per_call=0.08, quality_score=8.5, avg_latency_ms=4000, weight=2),
            # VLMs
            ModelProvider("qwen_vl_max", "Qwen-VL Max", ModelType.VLMS,
                         "https://api.dashscope.com/v1/chat", "DASHSCOPE_API_KEY",
                         max_qps=20, cost_per_call=0.02, quality_score=9.0, avg_latency_ms=2000, weight=3),
            ModelProvider("internvl_25", "InternVL 2.5", ModelType.VLMS,
                         "https://api.internvl.com/v1/chat", "INTERNVL_API_KEY",
                         max_qps=15, cost_per_call=0.015, quality_score=8.5, avg_latency_ms=2500, weight=2),
            # 文本
            ModelProvider("doubao_pro", "豆包Pro", ModelType.TEXT,
                         "https://api.doubao.com/v1/chat", "DOUBAO_API_KEY",
                         max_qps=30, cost_per_call=0.01, quality_score=9.0, avg_latency_ms=1500, weight=3),
        ]
        for p in defaults:
            self.router.register_provider(p)

    def submit_task(self, task_type: ModelType, payload: Dict,
                    priority: int = 2, strategy: Optional[RouterStrategy] = None) -> Task:
        """提交任务"""
        task = Task(
            task_id=f"task_{uuid.uuid4().hex[:12]}",
            task_type=task_type,
            payload=payload,
            priority=priority
        )
        self.task_queue.add_task(task)
        return task

    def execute_task(self, task: Task, strategy: Optional[RouterStrategy] = None) -> Dict:
        """执行单个任务（仿真模式）"""
        # 路由选择
        provider = self.router.route(task.task_type, strategy)
        if not provider:
            return {"success": False, "error": "无可用模型提供商", "task_id": task.task_id}

        task.assigned_provider = provider.provider_id
        if task.started_at is None:
            task.started_at = time.time()
            task.status = TaskStatus.RUNNING

        # 仿真执行（实际部署时替换为真实API调用）
        time.sleep(0.1)  # 模拟网络延迟
        success = True  # 仿真模式默认成功
        cost = provider.cost_per_call
        latency = provider.avg_latency_ms

        if success:
            result = {
                "success": True,
                "task_id": task.task_id,
                "provider": provider.name,
                "provider_id": provider.provider_id,
                "result": self._simulate_result(task),
                "cost": cost,
                "latency_ms": latency
            }
            provider.record_call(True, cost, latency)
            self.task_queue.complete_task(task, result, cost)
            return result
        else:
            error = "模型调用失败"
            provider.record_call(False, 0, latency)
            # 尝试降级
            fallback = self.router.get_fallback_provider(task.task_type, provider.provider_id)
            if fallback:
                task.assigned_provider = fallback.provider_id
                time.sleep(0.1)
                result = {
                    "success": True,
                    "task_id": task.task_id,
                    "provider": fallback.name,
                    "provider_id": fallback.provider_id,
                    "result": self._simulate_result(task),
                    "cost": fallback.cost_per_call,
                    "latency_ms": fallback.avg_latency_ms,
                    "fallback_from": provider.name
                }
                fallback.record_call(True, fallback.cost_per_call, fallback.avg_latency_ms)
                self.task_queue.complete_task(task, result, fallback.cost_per_call)
                return result
            self.task_queue.fail_task(task, error)
            return {"success": False, "error": error, "task_id": task.task_id}

    def _simulate_result(self, task: Task) -> Dict:
        """仿真生成结果"""
        if task.task_type == ModelType.VIDEO:
            return {
                "video_url": f"https://cdn.huodouai.com/videos/{task.task_id}.mp4",
                "duration": task.payload.get("duration", 5),
                "resolution": task.payload.get("resolution", "720x1280"),
                "frames": task.payload.get("duration", 5) * 24
            }
        elif task.task_type == ModelType.IMAGE:
            return {
                "image_url": f"https://cdn.huodouai.com/images/{task.task_id}.png",
                "width": task.payload.get("width", 720),
                "height": task.payload.get("height", 1280)
            }
        elif task.task_type == ModelType.VLMS:
            return {
                "analysis": "帧内容分析完成：场景=神殿金光，角色=玄女战争形态，动作=持矛而立，光影=伦勃朗光，质量评分=8.5/10",
                "scene_type": "神殿",
                "character": "九天玄女",
                "quality_score": 8.5
            }
        else:
            return {"text": "生成的文本内容..."}

    def batch_execute(self, tasks: List[Task], strategy: Optional[RouterStrategy] = None) -> List[Dict]:
        """批量执行任务"""
        results = []
        for task in tasks:
            result = self.execute_task(task, strategy)
            results.append(result)
        return results

    def get_provider_stats(self) -> List[Dict]:
        """获取所有提供商统计"""
        stats = []
        for p in self.router.providers.values():
            stats.append({
                "provider_id": p.provider_id,
                "name": p.name,
                "type": p.model_type.value,
                "enabled": p.enabled,
                "circuit_breaker": p.circuit_breaker_open,
                "total_calls": p.total_calls,
                "success_count": p.success_count,
                "failure_count": p.failure_count,
                "total_cost": round(p.total_cost, 4),
                "health_score": p.get_health_score(),
                "quality_score": p.quality_score,
                "cost_per_call": p.cost_per_call,
                "avg_latency_ms": p.avg_latency_ms
            })
        return stats

    def get_report(self) -> Dict:
        """生成完整报告"""
        return {
            "report_id": f"RPT-{uuid.uuid4().hex[:8]}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "did": "DID-BR-000002",
            "trace_chain": "Ω₀⊂⊙∞⊂Ω",
            "providers": self.get_provider_stats(),
            "queue_stats": self.task_queue.get_stats(),
            "router_strategy": self.router.strategy.value,
            "summary": {
                "total_providers": len(self.router.providers),
                "enabled_providers": len([p for p in self.router.providers.values() if p.enabled]),
                "video_providers": len([p for p in self.router.providers.values() if p.model_type == ModelType.VIDEO]),
                "image_providers": len([p for p in self.router.providers.values() if p.model_type == ModelType.IMAGE]),
                "vlms_providers": len([p for p in self.router.providers.values() if p.model_type == ModelType.VLMS]),
                "text_providers": len([p for p in self.router.providers.values() if p.model_type == ModelType.TEXT]),
            }
        }

    def save_report(self, filepath: Optional[str] = None) -> str:
        """保存报告到文件"""
        report = self.get_report()
        if filepath is None:
            filepath = os.path.join(self.data_dir, f"report_{int(time.time())}.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        return filepath


# ============ CLI ============
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="昆仑洞天·多模型聚合调度引擎")
    parser.add_argument("--demo", action="store_true", help="运行演示")
    parser.add_argument("--stats", action="store_true", help="查看提供商统计")
    parser.add_argument("--report", action="store_true", help="生成完整报告")
    parser.add_argument("--data-dir", type=str, default="./model_aggregator_data", help="数据目录")
    parser.add_argument("--strategy", type=str, default="auto",
                       choices=["round_robin", "weighted", "least_cost", "best_quality", "fastest", "auto"])
    args = parser.parse_args()

    print("=" * 60)
    print("  昆仑洞天·多模型聚合调度引擎 V1.0")
    print("  DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | 火斗云智AIOS")
    print("=" * 60)

    engine = MultiModelAggregator(data_dir=args.data_dir)

    if args.demo:
        print("\n[演示] 提交6个任务（2视频+2图像+2VLMs）...")
        tasks = [
            engine.submit_task(ModelType.VIDEO, {"prompt": "玄女降临", "duration": 5}, priority=0),
            engine.submit_task(ModelType.VIDEO, {"prompt": "神兵斩妖", "duration": 5}, priority=1),
            engine.submit_task(ModelType.IMAGE, {"prompt": "玄女战争形态", "width": 720, "height": 1280}, priority=1),
            engine.submit_task(ModelType.IMAGE, {"prompt": "神殿场景", "width": 720, "height": 1280}, priority=2),
            engine.submit_task(ModelType.VLMS, {"image_url": "frame_001.jpg"}, priority=2),
            engine.submit_task(ModelType.VLMS, {"image_url": "frame_002.jpg"}, priority=3),
        ]
        print(f"  已提交 {len(tasks)} 个任务")

        print("\n[执行] 批量执行...")
        results = engine.batch_execute(tasks)
        for r in results:
            status = "✅" if r.get("success") else "❌"
            provider = r.get("provider", "N/A")
            cost = r.get("cost", 0)
            print(f"  {status} {r['task_id']} | {provider} | 成本¥{cost}")

        print(f"\n[队列统计] {json.dumps(engine.task_queue.get_stats(), ensure_ascii=False, indent=2)}")

    elif args.stats:
        print("\n[提供商统计]")
        for s in engine.get_provider_stats():
            print(f"  {s['name']:20s} | 类型:{s['type']:18s} | 调用:{s['total_calls']:4d} | 健康:{s['health_score']:4.1f} | 成本:¥{s['cost_per_call']}")

    elif args.report:
        report_path = engine.save_report()
        print(f"\n[报告] 已保存: {report_path}")
        print(f"  提供商总数: {engine.get_report()['summary']['total_providers']}")
        print(f"  视频模型: {engine.get_report()['summary']['video_providers']}")
        print(f"  图像模型: {engine.get_report()['summary']['image_providers']}")
        print(f"  VLMs模型: {engine.get_report()['summary']['vlms_providers']}")

    else:
        parser.print_help()
