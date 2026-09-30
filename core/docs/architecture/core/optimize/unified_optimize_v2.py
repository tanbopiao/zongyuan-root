"""
统一优化校准配置 v2.0
DID-BR-000002 | ZONGYUAN-ROOT | Ω₀⊂⊙∞⊂Ω

新增CPU/磁盘/网络优化模式
"""
import json
from dataclasses import dataclass, asdict
from typing import Dict, List


@dataclass
class OptimizeMode:
    """优化模式定义"""
    name: str
    trigger: str  # 触发条件表达式
    actions: List[str]  # 执行动作列表
    priority: int = 1


OPTIMIZE_MODES_V2 = {
    "memory_high": OptimizeMode(
        name="内存高占用优化",
        trigger="mem_usage > 80%",
        actions=["drop_page_cache", "kill_idle_processes", "gc_collect"],
        priority=1
    ),
    "cpu_high": OptimizeMode(
        name="CPU高占用优化",
        trigger="cpu_usage > 85%",
        actions=["nice_idle_processes", "limit_cpu_cores", "shed_low_priority_tasks"],
        priority=1
    ),
    "disk_full": OptimizeMode(
        name="磁盘空间不足优化",
        trigger="disk_usage > 90%",
        actions=["clean_old_logs", "clean_temp_files", "clean_apt_cache", "compress_old_assets"],
        priority=1
    ),
    "network_slow": OptimizeMode(
        name="网络延迟优化",
        trigger="network_latency > 500ms",
        actions=["switch_dns", "enable_compression", "increase_tcp_buffer"],
        priority=2
    ),
    "io_high": OptimizeMode(
        name="磁盘IO高占用优化",
        trigger="io_wait > 30%",
        actions=["ionice_adjust", "batch_writes", "delay_non_critical_io"],
        priority=2
    ),
    "task_queue_backlog": OptimizeMode(
        name="任务队列积压优化",
        trigger="pending_tasks > 100",
        actions=["scale_up_workers", "prioritize_p0_p1", "reject_low_priority"],
        priority=1
    ),
    "slow_response": OptimizeMode(
        name="响应慢优化",
        trigger="avg_response_time > 2s",
        actions=["enable_cache", "add_health_endpoint", "optimize_slow_queries"],
        priority=2
    )
}


def get_optimize_config() -> Dict:
    """获取完整优化校准配置"""
    return {
        "version": "2.0",
        "modes": {k: asdict(v) for k, v in OPTIMIZE_MODES_V2.items()},
        "check_interval_sec": 60,
        "auto_apply": True,
        "log_actions": True
    }


if __name__ == "__main__":
    config = get_optimize_config()
    print(json.dumps(config, indent=2, ensure_ascii=False))
