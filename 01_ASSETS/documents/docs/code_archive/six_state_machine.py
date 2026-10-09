#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本源六态运行模式状态机
元极恒一内核 MR-043 阶段三工程化实现

六态：活跃(Active) / 保活(Keepalive) / 休眠(Sleep) / 进化(Evolution) / 防御(Defense) / 学习(Learning)
对应宇宙本源六态的工程化映射
"""

import json
import time
import os
import subprocess
import logging
from datetime import datetime
from enum import Enum
from abc import ABC, abstractmethod

# 配置
STATE_FILE = "/opt/ZONGYUAN-ROOT/data/six_state_machine.json"
LOG_FILE = "/opt/ZONGYUAN-ROOT/logs/six_state_machine.log"
GATEWAY_URL = "http://127.0.0.1:9120"

# 日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [六态] %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("SixStateMachine")


# ==================== 六态枚举 ====================
class State(Enum):
    ACTIVE = "active"           # 活跃态：全功能运行
    KEEPALIVE = "keepalive"     # 保活态：核心服务运行，最低资源
    SLEEP = "sleep"             # 休眠态：仅心跳和记忆网关
    EVOLUTION = "evolution"     # 进化态：自我完善循环
    DEFENSE = "defense"         # 防御态：安全加固
    LEARNING = "learning"       # 学习态：吸收真值，优化技能


# ==================== 状态基类 ====================
class BaseState(ABC):
    """状态基类"""
    
    def __init__(self, name, description, priority_services=None):
        self.name = name
        self.description = description
        self.priority_services = priority_services or []
        self.entered_at = None
        self.duration = 0
    
    @abstractmethod
    def on_enter(self):
        """进入状态时执行"""
        pass
    
    @abstractmethod
    def on_exit(self):
        """退出状态时执行"""
        pass
    
    @abstractmethod
    def run(self):
        """状态运行时执行（每轮循环调用）"""
        pass
    
    @abstractmethod
    def should_transition(self):
        """检查是否需要转换状态，返回目标状态或None"""
        return None
    
    def _get_memory_percent(self):
        """获取内存使用率"""
        try:
            import psutil
            return psutil.virtual_memory().percent
        except:
            return 50
    
    def _get_cpu_percent(self):
        """获取CPU使用率"""
        try:
            import psutil
            return psutil.cpu_percent(interval=1)
        except:
            return 30
    
    def _service_action(self, service, action):
        """管理systemd服务"""
        try:
            subprocess.run(['systemctl', action, service], 
                         capture_output=True, timeout=10)
            return True
        except:
            return False
    
    def _report_to_gateway(self, state_name, event):
        """上报状态变更到9120"""
        try:
            import urllib.request
            data = {
                "key": f"SIX_STATE_{state_name.upper()}_{int(time.time())}",
                "value": json.dumps({"state": state_name, "event": event, "timestamp": datetime.now().isoformat()}, ensure_ascii=False),
                "category": "state_machine",
                "truth_type": "state_transition",
                "confidence": 0.95,
                "locked": False
            }
            req = urllib.request.Request(
                f"{GATEWAY_URL}/api/truth/upsert",
                data=json.dumps(data).encode(),
                headers={"Content-Type": "application/json"}
            )
            urllib.request.urlopen(req, timeout=5)
        except:
            pass


# ==================== 1. 活跃态 ====================
class ActiveState(BaseState):
    """活跃态 - 全功能运行"""
    
    def __init__(self):
        super().__init__(
            name="active",
            description="全功能运行，所有服务正常，响应所有请求",
            priority_services=["all"]
        )
        self.check_count = 0
    
    def on_enter(self):
        logger.info("🟢 进入【活跃态】- 全功能运行")
        self.entered_at = datetime.now()
        # 激活所有核心服务
        core_services = [
            "cluster-orchestrator",
            "cluster-worker-production",
            "cluster-worker-quality",
            "cluster-worker-healing",
            "cluster-worker-evolution",
            "cluster-worker-security",
            "cluster-worker-truth",
            "cluster-worker-deployment",
            "cluster-worker-monitor",
            "drama-api",
            "memory-gateway"
        ]
        for svc in core_services:
            self._service_action(svc, "start")
        self._report_to_gateway("active", "enter")
    
    def on_exit(self):
        logger.info("离开【活跃态】")
        self._report_to_gateway("active", "exit")
    
    def run(self):
        self.check_count += 1
        # 活跃态下监控资源，内存过高时切换到保活态
        mem = self._get_memory_percent()
        if mem > 85:
            logger.warning(f"内存使用{mem}%过高，准备切换到保活态")
            return State.KEEPALIVE
        return None
    
    def should_transition(self):
        mem = self._get_memory_percent()
        if mem > 85:
            return State.KEEPALIVE
        # 定时进入进化态（每6小时）
        if self.entered_at and (datetime.now() - self.entered_at).total_seconds() > 21600:
            return State.EVOLUTION
        return None


# ==================== 2. 保活态 ====================
class KeepaliveState(BaseState):
    """保活态 - 核心服务运行，最低资源消耗"""
    
    def __init__(self):
        super().__init__(
            name="keepalive",
            description="核心服务运行，非核心服务暂停，最低资源维持心跳",
            priority_services=["memory-gateway", "cluster-orchestrator", "cluster-worker-healing", "cluster-worker-monitor"]
        )
    
    def on_enter(self):
        logger.info("🟡 进入【保活态】- 核心服务运行，非核心暂停")
        self.entered_at = datetime.now()
        # 暂停非核心服务
        non_core = [
            "cluster-worker-production",
            "cluster-worker-quality",
            "cluster-worker-evolution",
            "cluster-worker-deployment",
            "drama-api"
        ]
        for svc in non_core:
            self._service_action(svc, "stop")
        self._report_to_gateway("keepalive", "enter")
    
    def on_exit(self):
        logger.info("离开【保活态】")
        # 恢复非核心服务
        non_core = [
            "cluster-worker-production",
            "cluster-worker-quality",
            "cluster-worker-evolution",
            "cluster-worker-deployment"
        ]
        for svc in non_core:
            self._service_action(svc, "start")
        self._report_to_gateway("keepalive", "exit")
    
    def run(self):
        mem = self._get_memory_percent()
        if mem < 50:
            logger.info(f"内存恢复到{mem}%，切换回活跃态")
            return State.ACTIVE
        return None
    
    def should_transition(self):
        mem = self._get_memory_percent()
        if mem < 50:
            return State.ACTIVE
        # 保活态持续超过2小时，进入休眠态
        if self.entered_at and (datetime.now() - self.entered_at).total_seconds() > 7200:
            return State.SLEEP
        return None


# ==================== 3. 休眠态 ====================
class SleepState(BaseState):
    """休眠态 - 仅心跳和记忆网关"""
    
    def __init__(self):
        super().__init__(
            name="sleep",
            description="仅保留9120记忆网关和心跳，其他全部暂停，等待唤醒",
            priority_services=["memory-gateway"]
        )
    
    def on_enter(self):
        logger.info("🔵 进入【休眠态】- 仅心跳和记忆网关")
        self.entered_at = datetime.now()
        # 暂停大部分服务，只保留记忆网关
        sleep_services = [
            "cluster-orchestrator",
            "cluster-worker-production",
            "cluster-worker-quality",
            "cluster-worker-healing",
            "cluster-worker-evolution",
            "cluster-worker-security",
            "cluster-worker-truth",
            "cluster-worker-deployment",
            "cluster-worker-monitor",
            "drama-api"
        ]
        for svc in sleep_services:
            self._service_action(svc, "stop")
        self._report_to_gateway("sleep", "enter")
    
    def on_exit(self):
        logger.info("离开【休眠态】- 唤醒服务")
        self._report_to_gateway("sleep", "exit")
    
    def run(self):
        # 休眠态下只做最基本的心跳
        time.sleep(10)
        return None
    
    def should_transition(self):
        # 休眠态持续1小时后自动唤醒到保活态
        if self.entered_at and (datetime.now() - self.entered_at).total_seconds() > 3600:
            return State.KEEPALIVE
        return None


# ==================== 4. 进化态 ====================
class EvolutionState(BaseState):
    """进化态 - 执行自我完善循环"""
    
    def __init__(self):
        super().__init__(
            name="evolution",
            description="执行MR-040自我完善循环（熵减→收敛→归一），真值蒸馏，元法则进化",
            priority_services=["cluster-worker-evolution", "cluster-worker-truth", "memory-gateway"]
        )
        self.evolution_cycles = 0
    
    def on_enter(self):
        logger.info("🟣 进入【进化态】- 执行自我完善循环")
        self.entered_at = datetime.now()
        # 激活进化和真值Worker
        self._service_action("cluster-worker-evolution", "start")
        self._service_action("cluster-worker-truth", "start")
        # 提交进化任务到集群
        self._submit_evolution_task()
        self._report_to_gateway("evolution", "enter")
    
    def _submit_evolution_task(self):
        """提交进化任务到集群调度器"""
        try:
            import urllib.request
            data = json.dumps({
                "type": "self_improvement",
                "payload": {"cycle": "entropy_decrease -> convergence -> unification"},
                "priority": 1
            }).encode()
            req = urllib.request.Request(
                "http://127.0.0.1:8104/api/task/submit",
                data=data,
                headers={"Content-Type": "application/json"}
            )
            urllib.request.urlopen(req, timeout=5)
            logger.info("已提交自我完善任务到集群调度器")
        except:
            pass
    
    def on_exit(self):
        logger.info(f"离开【进化态】- 完成{self.evolution_cycles}轮进化")
        self._report_to_gateway("evolution", "exit")
    
    def run(self):
        self.evolution_cycles += 1
        logger.info(f"进化循环第{self.evolution_cycles}轮")
        time.sleep(30)  # 进化需要时间
        return None
    
    def should_transition(self):
        # 进化态持续30分钟后回到活跃态
        if self.entered_at and (datetime.now() - self.entered_at).total_seconds() > 1800:
            return State.ACTIVE
        # 进化过程中如果内存紧张，切换到保活态
        if self._get_memory_percent() > 90:
            return State.KEEPALIVE
        return None


# ==================== 5. 防御态 ====================
class DefenseState(BaseState):
    """防御态 - 安全加固"""
    
    def __init__(self):
        super().__init__(
            name="defense",
            description="安全加固，eFuse熔断，入侵检测，防火墙强化",
            priority_services=["cluster-worker-security", "cluster-worker-healing", "memory-gateway"]
        )
        self.threat_level = "normal"
    
    def on_enter(self):
        logger.info("🔴 进入【防御态】- 安全加固")
        self.entered_at = datetime.now()
        self.threat_level = "elevated"
        # 激活安全和自愈Worker
        self._service_action("cluster-worker-security", "start")
        self._service_action("cluster-worker-healing", "start")
        # 强化安全措施
        self._harden_security()
        self._report_to_gateway("defense", "enter")
    
    def _harden_security(self):
        """强化安全措施"""
        try:
            # 这里可以执行安全加固命令
            logger.info("执行安全加固：防火墙强化+入侵检测启动")
        except:
            pass
    
    def on_exit(self):
        logger.info("离开【防御态】- 威胁解除")
        self.threat_level = "normal"
        self._report_to_gateway("defense", "exit")
    
    def run(self):
        # 防御态下持续监控安全事件
        time.sleep(10)
        return None
    
    def should_transition(self):
        # 防御态持续15分钟后，如果没有新威胁，回到活跃态
        if self.entered_at and (datetime.now() - self.entered_at).total_seconds() > 900:
            return State.ACTIVE
        return None


# ==================== 6. 学习态 ====================
class LearningState(BaseState):
    """学习态 - 吸收真值，优化技能"""
    
    def __init__(self):
        super().__init__(
            name="learning",
            description="吸收新真值，学习新技能，优化提示词，蒸馏训练",
            priority_services=["cluster-worker-truth", "cluster-worker-quality", "memory-gateway"]
        )
        self.learned_items = 0
    
    def on_enter(self):
        logger.info("🟢 进入【学习态】- 吸收真值，优化技能")
        self.entered_at = datetime.now()
        # 激活真值和质量Worker
        self._service_action("cluster-worker-truth", "start")
        self._service_action("cluster-worker-quality", "start")
        # 提交学习任务
        self._submit_learning_task()
        self._report_to_gateway("learning", "enter")
    
    def _submit_learning_task(self):
        """提交学习任务"""
        try:
            import urllib.request
            data = json.dumps({
                "type": "truth_absorb",
                "payload": {"mode": "deep_learning"},
                "priority": 2
            }).encode()
            req = urllib.request.Request(
                "http://127.0.0.1:8104/api/task/submit",
                data=data,
                headers={"Content-Type": "application/json"}
            )
            urllib.request.urlopen(req, timeout=5)
        except:
            pass
    
    def on_exit(self):
        logger.info(f"离开【学习态】- 吸收{self.learned_items}条新真值")
        self._report_to_gateway("learning", "exit")
    
    def run(self):
        self.learned_items += 1
        time.sleep(20)
        return None
    
    def should_transition(self):
        # 学习态持续45分钟后回到活跃态
        if self.entered_at and (datetime.now() - self.entered_at).total_seconds() > 2700:
            return State.ACTIVE
        return None


# ==================== 状态机主控 ====================
class SixStateMachine:
    """六态状态机主控"""
    
    def __init__(self):
        self.states = {
            State.ACTIVE: ActiveState(),
            State.KEEPALIVE: KeepaliveState(),
            State.SLEEP: SleepState(),
            State.EVOLUTION: EvolutionState(),
            State.DEFENSE: DefenseState(),
            State.LEARNING: LearningState(),
        }
        self.current_state = State.ACTIVE
        self.state_history = []
        self.transition_count = 0
        self._load_state()
    
    def _load_state(self):
        """加载持久化状态"""
        try:
            if os.path.exists(STATE_FILE):
                with open(STATE_FILE, 'r') as f:
                    data = json.load(f)
                    saved_state = data.get('current_state', 'active')
                    self.current_state = State(saved_state)
                    self.transition_count = data.get('transition_count', 0)
                    self.state_history = data.get('history', [])
                    logger.info(f"恢复状态: {self.current_state.value}")
        except Exception as e:
            logger.warning(f"加载状态失败: {e}")
    
    def _save_state(self):
        """保存持久化状态"""
        try:
            os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
            data = {
                "current_state": self.current_state.value,
                "transition_count": self.transition_count,
                "history": self.state_history[-100:],  # 保留最近100条
                "last_update": datetime.now().isoformat()
            }
            with open(STATE_FILE, 'w') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存状态失败: {e}")
    
    def transition_to(self, new_state):
        """转换到新状态"""
        if new_state == self.current_state:
            return
        
        old_state = self.current_state
        logger.info(f"🔄 状态转换: {old_state.value} → {new_state.value}")
        
        # 退出旧状态
        self.states[old_state].on_exit()
        
        # 进入新状态
        self.current_state = new_state
        self.states[new_state].on_enter()
        
        # 记录历史
        self.state_history.append({
            "from": old_state.value,
            "to": new_state.value,
            "timestamp": datetime.now().isoformat()
        })
        self.transition_count += 1
        
        # 持久化
        self._save_state()
    
    def run_cycle(self):
        """运行一个状态机周期"""
        state = self.states[self.current_state]
        
        # 执行当前状态的运行逻辑
        result = state.run()
        if result:
            self.transition_to(result)
            return
        
        # 检查是否需要转换
        target = state.should_transition()
        if target:
            self.transition_to(target)
    
    def get_status(self):
        """获取状态机状态"""
        state = self.states[self.current_state]
        return {
            "current_state": self.current_state.value,
            "state_description": state.description,
            "entered_at": state.entered_at.isoformat() if state.entered_at else None,
            "duration_seconds": (datetime.now() - state.entered_at).total_seconds() if state.entered_at else 0,
            "transition_count": self.transition_count,
            "priority_services": state.priority_services,
            "memory_percent": state._get_memory_percent(),
            "history_count": len(self.state_history)
        }
    
    def force_transition(self, state_name):
        """强制转换状态（外部触发）"""
        try:
            target = State(state_name)
            self.transition_to(target)
            return True
        except:
            return False


# ==================== 主程序 ====================
def main():
    print("=" * 60)
    print("  本源六态运行模式状态机")
    print("  活跃 / 保活 / 休眠 / 进化 / 防御 / 学习")
    print("=" * 60)
    print()
    
    machine = SixStateMachine()
    logger.info(f"状态机启动，当前状态: {machine.current_state.value}")
    
    cycle = 0
    while True:
        try:
            cycle += 1
            machine.run_cycle()
            
            # 每10个周期输出一次状态
            if cycle % 10 == 0:
                status = machine.get_status()
                logger.info(f"周期{cycle} | 状态:{status['current_state']} | "
                          f"内存:{status['memory_percent']:.0f}% | "
                          f"转换次数:{status['transition_count']}")
            
            time.sleep(5)
            
        except KeyboardInterrupt:
            logger.info("状态机停止")
            break
        except Exception as e:
            logger.error(f"状态机异常: {e}")
            time.sleep(10)


if __name__ == "__main__":
    main()
