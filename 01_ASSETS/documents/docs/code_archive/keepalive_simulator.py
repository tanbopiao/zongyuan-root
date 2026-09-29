#!/usr/bin/env python3
"""
云服务器保活架构仿真测试引擎
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | 火斗云智AIOS

模拟2核2G云服务器在各种故障场景下的保活机制有效性
"""

import json
import time
import random
import hashlib
from datetime import datetime, timezone
from collections import deque
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

# ==================== 配置 ====================
TOTAL_MEMORY_MB = 2048  # 2G
TOTAL_CPU_CORES = 2
SAFE_MEMORY_THRESHOLD = 0.65  # 65%安全线
WARN_MEMORY_THRESHOLD = 0.75  # 75%告警线
CRITICAL_MEMORY_THRESHOLD = 0.85  # 85%危险线
OOM_THRESHOLD = 0.95  # 95% OOM

# 服务清单（云端实际运行的核心服务）
SERVICES = {
    "memory_gateway_9120": {"name": "记忆网关", "port": 9120, "base_mem_mb": 120, "critical": True, "restart_limit": 5},
    "vector_server_8014": {"name": "向量服务", "port": 8014, "base_mem_mb": 200, "critical": True, "restart_limit": 3},
    "aios_workbench_8765": {"name": "智能体工作台", "port": 8765, "base_mem_mb": 150, "critical": False, "restart_limit": 3},
    "op_sched_8072": {"name": "算子调度", "port": 8072, "base_mem_mb": 80, "critical": True, "restart_limit": 3},
    "unified_operator_8061": {"name": "统一算子", "port": 8061, "base_mem_mb": 100, "critical": False, "restart_limit": 3},
    "kg_api_8080": {"name": "知识图谱", "port": 8080, "base_mem_mb": 180, "critical": False, "restart_limit": 3},
    "gov_api_8201": {"name": "政务API", "port": 8201, "base_mem_mb": 90, "critical": False, "restart_limit": 3},
    "feishu_callback_8060": {"name": "飞书审批回调", "port": 8060, "base_mem_mb": 60, "critical": False, "restart_limit": 3},
    "context_assembler_9123": {"name": "上下文组装", "port": 9123, "base_mem_mb": 110, "critical": True, "restart_limit": 3},
    "handshake_8099": {"name": "同源握手", "port": 8099, "base_mem_mb": 50, "critical": True, "restart_limit": 3},
    "drama_admin_8100": {"name": "短剧后台", "port": 8100, "base_mem_mb": 130, "critical": False, "restart_limit": 3},
    "steady_ops_8090": {"name": "稳态运维", "port": 8090, "base_mem_mb": 70, "critical": False, "restart_limit": 3},
    "meta_monitor_8098": {"name": "元运维监控", "port": 8098, "base_mem_mb": 40, "critical": True, "restart_limit": 5},
    "ai_agent_8021": {"name": "AI代理", "port": 8021, "base_mem_mb": 140, "critical": False, "restart_limit": 3},
    "agent_hub_8023": {"name": "Agent Hub", "port": 8023, "base_mem_mb": 100, "critical": False, "restart_limit": 3},
    "agent_gateway_8029": {"name": "智能体网关", "port": 8029, "base_mem_mb": 80, "critical": False, "restart_limit": 3},
    "hrm_8040": {"name": "HRM系统", "port": 8040, "base_mem_mb": 160, "critical": False, "restart_limit": 3},
    "experience_center_8046": {"name": "体验中心", "port": 8046, "base_mem_mb": 120, "critical": False, "restart_limit": 3},
    "kd_pipeline_8626": {"name": "KD流水线", "port": 8626, "base_mem_mb": 90, "critical": False, "restart_limit": 3},
    "nginx": {"name": "Nginx反向代理", "port": 80, "base_mem_mb": 30, "critical": True, "restart_limit": 5},
}

SYSTEM_OVERHEAD_MB = 300  # 系统基础占用

# ==================== 数据模型 ====================
@dataclass
class ServiceInstance:
    service_id: str
    name: str
    port: int
    base_mem_mb: float
    current_mem_mb: float = 0
    critical: bool = False
    status: str = "running"  # running / crashed / restarting / stopped / oom_killed
    restart_count: int = 0
    restart_limit: int = 3
    last_health_check: float = 0
    health_score: float = 100
    memory_leak_rate: float = 0  # MB/tick 内存泄漏速率
    cpu_usage: float = 0
    response_time_ms: float = 10
    error_rate: float = 0
    startup_time: float = 0

@dataclass
class SystemState:
    tick: int = 0
    total_memory_mb: float = TOTAL_MEMORY_MB
    used_memory_mb: float = SYSTEM_OVERHEAD_MB
    cpu_usage: float = 0.1
    disk_usage_gb: float = 15.0
    uptime_ticks: int = 0
    oom_events: int = 0
    total_restarts: int = 0
    services: Dict[str, ServiceInstance] = field(default_factory=dict)
    events: List[Dict] = field(default_factory=list)
    memory_history: deque = field(default_factory=lambda: deque(maxlen=500))
    alerts: List[Dict] = field(default_factory=list)
    self_heal_actions: List[Dict] = field(default_factory=list)

# ==================== 保活机制 ====================
class KeepAliveSystem:
    """五层保活体系"""
    
    def __init__(self, state: SystemState):
        self.state = state
        self.action_log = []
    
    def log_action(self, layer: str, action: str, detail: str = ""):
        entry = {
            "tick": self.state.tick,
            "layer": layer,
            "action": action,
            "detail": detail,
            "mem_after_mb": self.state.used_memory_mb
        }
        self.action_log.append(entry)
        self.state.self_heal_actions.append(entry)
    
    # L0: 内核级 - cgroups资源限制 + OOM优先级
    def l0_kernel_protection(self):
        """OOM优先级调整：关键服务OOM分数最低，非关键服务优先被杀"""
        mem_ratio = self.state.used_memory_mb / self.state.total_memory_mb
        if mem_ratio > OOM_THRESHOLD:
            # 模拟OOM Killer：优先杀非关键、内存占用最大的服务
            candidates = [
                s for s in self.state.services.values()
                if s.status == "running" and not s.critical
            ]
            if candidates:
                victim = max(candidates, key=lambda s: s.current_mem_mb)
                victim.status = "oom_killed"
                self.state.used_memory_mb -= victim.current_mem_mb
                self.state.oom_events += 1
                self.log_action("L0-内核", "OOM_KILL", f"杀死{victim.name}释放{victim.current_mem_mb:.0f}MB")
                return True
        return False
    
    # L1: 进程级 - systemd自动重启
    def l1_process_guard(self):
        """监控崩溃服务，自动重启（有限次）"""
        for sid, svc in self.state.services.items():
            if svc.status in ("crashed", "oom_killed") and svc.restart_count < svc.restart_limit:
                svc.status = "restarting"
                svc.restart_count += 1
                svc.startup_time = self.state.tick
                self.state.total_restarts += 1
                self.log_action("L1-进程", "AUTO_RESTART", f"{svc.name}第{svc.restart_count}次重启")
            elif svc.status == "restarting":
                # 模拟启动延迟2个tick
                if self.state.tick - svc.startup_time >= 2:
                    svc.status = "running"
                    svc.current_mem_mb = svc.base_mem_mb * random.uniform(0.9, 1.1)
                    svc.health_score = 95
                    self.log_action("L1-进程", "RESTART_OK", f"{svc.name}恢复运行")
            elif svc.status in ("crashed", "oom_killed") and svc.restart_count >= svc.restart_limit:
                svc.status = "stopped"
                self.log_action("L1-进程", "RESTART_LIMIT", f"{svc.name}超过重启上限，标记停止")
    
    # L2: 服务级 - 健康检查+熔断降级
    def l2_service_health(self):
        """健康检查，异常服务熔断降级"""
        for sid, svc in self.state.services.items():
            if svc.status != "running":
                continue
            # 模拟健康检查
            if svc.error_rate > 0.1 or svc.response_time_ms > 500:
                svc.health_score = max(0, svc.health_score - 10)
                if svc.health_score < 50:
                    svc.status = "crashed"
                    self.log_action("L2-服务", "HEALTH_FAIL", f"{svc.name}健康分{svc.health_score:.0f}，标记崩溃")
            else:
                svc.health_score = min(100, svc.health_score + 2)
    
    # L3: 内存级 - 监控告警+自动释放+限流
    def l3_memory_guard(self):
        """内存超阈值时自动释放缓存、限流非关键服务"""
        mem_ratio = self.state.used_memory_mb / self.state.total_memory_mb
        
        if mem_ratio > CRITICAL_MEMORY_THRESHOLD:
            # 危险：释放页缓存 + 暂停非关键服务
            freed = 0
            for svc in self.state.services.values():
                if svc.status == "running" and not svc.critical:
                    # 模拟释放缓存（减少30%内存占用）
                    cache_free = svc.current_mem_mb * 0.3
                    svc.current_mem_mb -= cache_free
                    freed += cache_free
            self.state.used_memory_mb -= freed
            self.log_action("L3-内存", "DROP_CACHES", f"释放页缓存{freed:.0f}MB")
            
            # 限流非关键服务
            for svc in self.state.services.values():
                if not svc.critical and svc.status == "running":
                    svc.error_rate = min(0.05, svc.error_rate + 0.02)  # 模拟限流导致少量错误
            self.log_action("L3-内存", "RATE_LIMIT", "非关键服务限流")
            
        elif mem_ratio > WARN_MEMORY_THRESHOLD:
            # 告警：记录但不强制干预
            if not any(a.get("type") == "mem_warn" and a.get("tick") == self.state.tick for a in self.state.alerts):
                self.state.alerts.append({
                    "tick": self.state.tick,
                    "type": "mem_warn",
                    "message": f"内存使用率{mem_ratio*100:.1f}%超过75%告警线",
                    "mem_mb": self.state.used_memory_mb
                })
            # 轻度释放
            for svc in self.state.services.values():
                if svc.status == "running" and not svc.critical:
                    cache_free = svc.current_mem_mb * 0.1
                    svc.current_mem_mb -= cache_free
                    self.state.used_memory_mb -= cache_free
    
    # L4: 磁盘级 - 日志轮转+清理
    def l4_disk_guard(self):
        """磁盘空间监控，自动清理过期日志"""
        if self.state.disk_usage_gb > 35:  # 40G磁盘，87.5%告警
            cleaned = random.uniform(0.5, 2.0)
            self.state.disk_usage_gb -= cleaned
            self.log_action("L4-磁盘", "LOG_ROTATE", f"清理日志{cleaned:.1f}GB")
    
    # L5: 灾备级 - 快照备份（仿真中记录）
    def l5_disaster_recovery(self):
        """每100tick记录一次快照点"""
        if self.state.tick % 100 == 0 and self.state.tick > 0:
            self.log_action("L5-灾备", "SNAPSHOT", f"第{self.state.tick}tick系统快照已保存")
    
    def run_all_layers(self):
        """执行全部五层保活"""
        self.l0_kernel_protection()
        self.l1_process_guard()
        self.l2_service_health()
        self.l3_memory_guard()
        self.l4_disk_guard()
        self.l5_disaster_recovery()

# ==================== 仿真引擎 ====================
class SimulationEngine:
    def __init__(self):
        self.state = SystemState()
        self.keepalive = KeepAliveSystem(self.state)
        self._init_services()
    
    def _init_services(self):
        for sid, cfg in SERVICES.items():
            svc = ServiceInstance(
                service_id=sid,
                name=cfg["name"],
                port=cfg["port"],
                base_mem_mb=cfg["base_mem_mb"],
                current_mem_mb=cfg["base_mem_mb"] * random.uniform(0.9, 1.1),
                critical=cfg["critical"],
                restart_limit=cfg["restart_limit"]
            )
            self.state.services[sid] = svc
            self.state.used_memory_mb += svc.current_mem_mb
    
    def inject_fault(self, fault_type: str, **kwargs):
        """注入故障"""
        if fault_type == "memory_leak":
            # 指定服务内存泄漏
            target = kwargs.get("target", "vector_server_8014")
            rate = kwargs.get("rate_mb_per_tick", 15)
            if target in self.state.services:
                self.state.services[target].memory_leak_rate = rate
                self.state.events.append({"tick": self.state.tick, "type": "memory_leak", "target": target, "rate": rate})
        
        elif fault_type == "service_crash":
            target = kwargs.get("target", "aios_workbench_8765")
            if target in self.state.services:
                self.state.services[target].status = "crashed"
                self.state.events.append({"tick": self.state.tick, "type": "service_crash", "target": target})
        
        elif fault_type == "traffic_spike":
            # 流量突增，所有服务内存+CPU上升
            increase = kwargs.get("mem_increase_mb", 300)
            per_svc = increase / len([s for s in self.state.services.values() if s.status == "running"])
            for svc in self.state.services.values():
                if svc.status == "running":
                    svc.current_mem_mb += per_svc
                    svc.cpu_usage = min(1.0, svc.cpu_usage + 0.3)
                    svc.response_time_ms *= 2
            self.state.used_memory_mb += increase
            self.state.events.append({"tick": self.state.tick, "type": "traffic_spike", "increase": increase})
        
        elif fault_type == "disk_fill":
            self.state.disk_usage_gb = 38.0
            self.state.events.append({"tick": self.state.tick, "type": "disk_fill"})
        
        elif fault_type == "critical_crash":
            # 关键服务崩溃
            target = kwargs.get("target", "memory_gateway_9120")
            if target in self.state.services:
                self.state.services[target].status = "crashed"
                self.state.events.append({"tick": self.state.tick, "type": "critical_crash", "target": target})
    
    def tick(self):
        """推进一个仿真tick"""
        self.state.tick += 1
        self.state.uptime_ticks += 1
        
        # 1. 更新服务状态（内存泄漏自然增长）
        for svc in self.state.services.values():
            if svc.status == "running":
                # 内存泄漏
                if svc.memory_leak_rate > 0:
                    leak = svc.memory_leak_rate * random.uniform(0.8, 1.2)
                    svc.current_mem_mb += leak
                    self.state.used_memory_mb += leak
                # 自然波动
                svc.current_mem_mb *= random.uniform(0.99, 1.01)
                svc.cpu_usage = max(0.05, min(1.0, svc.cpu_usage * random.uniform(0.9, 1.1)))
                svc.response_time_ms = max(5, svc.response_time_ms * random.uniform(0.95, 1.05))
                svc.error_rate = max(0, min(0.2, svc.error_rate * random.uniform(0.9, 1.1)))
        
        # 2. 执行五层保活
        self.keepalive.run_all_layers()
        
        # 3. 记录内存历史
        self.state.memory_history.append(self.state.used_memory_mb)
        
        # 4. 磁盘自然增长
        self.state.disk_usage_gb += random.uniform(0, 0.02)
    
    def run_simulation(self, ticks: int, fault_schedule: List[Dict] = None) -> Dict:
        """运行完整仿真"""
        fault_schedule = fault_schedule or []
        results = {
            "total_ticks": ticks,
            "faults_injected": 0,
            "oom_events": 0,
            "total_restarts": 0,
            "self_heal_actions": 0,
            "alerts": 0,
            "max_memory_mb": 0,
            "min_memory_mb": float('inf'),
            "avg_memory_mb": 0,
            "critical_services_uptime": {},
            "services_final_status": {},
            "survived": True,
            "memory_curve": [],
            "action_summary": {}
        }
        
        mem_samples = []
        
        for t in range(ticks):
            # 注入计划故障
            for fault in fault_schedule:
                if fault["tick"] == t:
                    self.inject_fault(fault["type"], **fault.get("params", {}))
                    results["faults_injected"] += 1
            
            self.tick()
            mem_samples.append(self.state.used_memory_mb)
            results["max_memory_mb"] = max(results["max_memory_mb"], self.state.used_memory_mb)
            results["min_memory_mb"] = min(results["min_memory_mb"], self.state.used_memory_mb)
            
            # 检查系统是否存活（关键服务全部停止=系统死亡）
            critical_dead = all(
                s.status == "stopped"
                for s in self.state.services.values() if s.critical
            )
            if critical_dead:
                results["survived"] = False
                results["death_tick"] = t
                break
        
        # 统计
        results["oom_events"] = self.state.oom_events
        results["total_restarts"] = self.state.total_restarts
        results["self_heal_actions"] = len(self.state.self_heal_actions)
        results["alerts"] = len(self.state.alerts)
        results["avg_memory_mb"] = sum(mem_samples) / len(mem_samples) if mem_samples else 0
        
        # 关键服务正常运行时间占比
        for sid, svc in self.state.services.items():
            if svc.critical:
                # 简化：最终状态running则视为高可用
                results["critical_services_uptime"][svc.name] = "running" if svc.status == "running" else svc.status
        
        # 最终服务状态
        for sid, svc in self.state.services.items():
            results["services_final_status"][svc.name] = svc.status
        
        # 动作统计
        for action in self.state.self_heal_actions:
            layer = action["layer"]
            results["action_summary"][layer] = results["action_summary"].get(layer, 0) + 1
        
        # 内存曲线（采样）
        sample_step = max(1, len(mem_samples) // 100)
        results["memory_curve"] = mem_samples[::sample_step]
        
        return results

# ==================== 测试场景 ====================
def run_all_scenarios():
    """运行全部保活测试场景"""
    print("=" * 60)
    print("云服务器保活架构仿真测试")
    print("配置：2核2G | 20个服务 | 五层保活体系")
    print("=" * 60)
    
    scenarios = [
        {
            "name": "场景1：单服务内存泄漏（向量服务泄漏15MB/tick）",
            "ticks": 200,
            "faults": [
                {"tick": 20, "type": "memory_leak", "params": {"target": "vector_server_8014", "rate_mb_per_tick": 15}}
            ]
        },
        {
            "name": "场景2：非关键服务崩溃（智能体工作台崩溃）",
            "ticks": 150,
            "faults": [
                {"tick": 30, "type": "service_crash", "params": {"target": "aios_workbench_8765"}}
            ]
        },
        {
            "name": "场景3：流量突增（+300MB内存压力）",
            "ticks": 200,
            "faults": [
                {"tick": 50, "type": "traffic_spike", "params": {"mem_increase_mb": 300}}
            ]
        },
        {
            "name": "场景4：关键服务崩溃（记忆网关崩溃）",
            "ticks": 150,
            "faults": [
                {"tick": 40, "type": "critical_crash", "params": {"target": "memory_gateway_9120"}}
            ]
        },
        {
            "name": "场景5：复合故障（泄漏+崩溃+流量突增叠加）",
            "ticks": 300,
            "faults": [
                {"tick": 30, "type": "memory_leak", "params": {"target": "vector_server_8014", "rate_mb_per_tick": 10}},
                {"tick": 80, "type": "service_crash", "params": {"target": "drama_admin_8100"}},
                {"tick": 120, "type": "traffic_spike", "params": {"mem_increase_mb": 250}},
                {"tick": 180, "type": "critical_crash", "params": {"target": "context_assembler_9123"}}
            ]
        },
        {
            "name": "场景6：磁盘占满（日志未清理）",
            "ticks": 100,
            "faults": [
                {"tick": 20, "type": "disk_fill"}
            ]
        }
    ]
    
    all_results = []
    
    for scenario in scenarios:
        print(f"\n{'─' * 60}")
        print(f"▶ {scenario['name']}")
        print(f"  仿真时长：{scenario['ticks']} ticks")
        
        engine = SimulationEngine()
        result = engine.run_simulation(scenario["ticks"], scenario["faults"])
        result["scenario_name"] = scenario["name"]
        all_results.append(result)
        
        print(f"  系统存活：{'✅ 是' if result['survived'] else '❌ 否（死亡tick:' + str(result.get('death_tick','?')) + '）'}")
        print(f"  峰值内存：{result['max_memory_mb']:.0f}MB ({result['max_memory_mb']/TOTAL_MEMORY_MB*100:.1f}%)")
        print(f"  平均内存：{result['avg_memory_mb']:.0f}MB")
        print(f"  OOM事件：{result['oom_events']}次")
        print(f"  自动重启：{result['total_restarts']}次")
        print(f"  自愈动作：{result['self_heal_actions']}次")
        print(f"  告警次数：{result['alerts']}次")
        print(f"  动作分布：{json.dumps(result['action_summary'], ensure_ascii=False)}")
        
        critical_status = {k: v for k, v in result["critical_services_uptime"].items()}
        print(f"  关键服务状态：{json.dumps(critical_status, ensure_ascii=False)}")
    
    # 汇总
    print(f"\n{'=' * 60}")
    print("📊 测试汇总")
    print(f"{'=' * 60}")
    survived = sum(1 for r in all_results if r["survived"])
    print(f"  测试场景：{len(all_results)}个")
    print(f"  系统存活：{survived}/{len(all_results)} ({survived/len(all_results)*100:.0f}%)")
    print(f"  总OOM事件：{sum(r['oom_events'] for r in all_results)}次")
    print(f"  总自动重启：{sum(r['total_restarts'] for r in all_results)}次")
    print(f"  总自愈动作：{sum(r['self_heal_actions'] for r in all_results)}次")
    
    # 保存结果
    output = {
        "test_time": datetime.now(timezone.utc).isoformat(),
        "server_config": {"cpu": "2核", "memory": "2G", "disk": "40G", "os": "OpenCloudOS9"},
        "keepalive_layers": ["L0内核级OOM保护", "L1进程级自动重启", "L2服务级健康检查", "L3内存级监控释放", "L4磁盘级日志轮转", "L5灾备级快照备份"],
        "scenarios": all_results,
        "summary": {
            "total_scenarios": len(all_results),
            "survived": survived,
            "survival_rate": f"{survived/len(all_results)*100:.0f}%",
            "total_oom": sum(r['oom_events'] for r in all_results),
            "total_restarts": sum(r['total_restarts'] for r in all_results),
            "total_self_heal": sum(r['self_heal_actions'] for r in all_results)
        },
        "did": "DID-BR-000002",
        "trace_mark": "Ω₀⊂⊙∞⊂Ω"
    }
    
    with open("/home/user/Doubao/chats/38437335960673794/keepalive_simulation_result.json", "w") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 仿真结果已保存：keepalive_simulation_result.json")
    return output

if __name__ == "__main__":
    run_all_scenarios()
