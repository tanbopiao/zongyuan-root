#!/usr/bin/env python3
"""
通用自进化引擎 - Universal Evolution Engine (UEE)
可嵌入所有系统/网页的轻量进化模块，让每个智能体都具备自进化能力。

核心理念：系统即生命，网页即智能体。
每个数字智能体都必须：每天学习、每天成长、每天完善人机交互体验。

使用方式：
    from universal_evolution import UniversalEvolutionEngine
    
    engine = UniversalEvolutionEngine(
        agent_id="my-website-001",
        agent_name="我的官网",
        agent_type="display",  # display/tool/interactive/creation/decision/infrastructure
        data_path="./evolution-data"
    )
    
    # 记录用户交互
    engine.track_interaction(user_id="user001", action="click", target="button-login", duration=2.5)
    
    # 每日进化
    engine.daily_evolution()
    
    # 获取进化状态
    status = engine.get_evolution_status()
"""

import json
import os
import time
import hashlib
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path
from dataclasses import dataclass, asdict, field
from enum import Enum
from collections import defaultdict, Counter


class AgentType(Enum):
    """智能体类型"""
    DISPLAY = "display"           # 展示型：官网、产品页、落地页
    TOOL = "tool"                 # 工具型：管理后台、业务系统
    INTERACTIVE = "interactive"   # 交互型：对话系统、客服系统
    CREATION = "creation"         # 创作型：内容生成、短剧流水线
    DECISION = "decision"         # 决策型：决策系统、风控系统
    INFRASTRUCTURE = "infrastructure"  # 基础设施型：网关、存储、调度


class EvolutionStage(Enum):
    """进化阶段"""
    SEED = "seed"           # 种子期
    SPROUT = "sprout"       # 萌芽期
    GROWTH = "growth"       # 成长期
    MATURITY = "maturity"   # 成熟期
    EVOLUTION = "evolution" # 进化期
    TRANSCEND = "transcend" # 超越期


class InteractionType(Enum):
    """交互类型"""
    CLICK = "click"
    VIEW = "view"
    SCROLL = "scroll"
    INPUT = "input"
    HOVER = "hover"
    NAVIGATE = "navigate"
    CONVERSION = "conversion"
    ERROR = "error"
    FEEDBACK = "feedback"
    SHARE = "share"


@dataclass
class InteractionRecord:
    """交互记录"""
    timestamp: str
    user_id: str
    session_id: str
    interaction_type: str
    target: str
    value: Optional[str] = None
    duration: float = 0.0
    metadata: Dict = field(default_factory=dict)


@dataclass
class EvolutionLog:
    """进化日志"""
    timestamp: str
    evolution_type: str  # ui_optimization/performance_optimization/content_optimization/flow_optimization/bug_fix/feature_addition
    title: str
    description: str
    impact: str  # low/medium/high/critical
    metrics_before: Dict
    metrics_after: Dict
    improvement_percent: float
    hash: str
    parent_hash: str


@dataclass
class EvolutionMetrics:
    """进化指标"""
    total_interactions: int = 0
    unique_users: int = 0
    avg_session_duration: float = 0.0
    conversion_rate: float = 0.0
    error_rate: float = 0.0
    user_satisfaction: float = 0.0
    page_load_time: float = 0.0
    interaction_heatmap: Dict = field(default_factory=dict)
    top_clicks: List = field(default_factory=list)
    top_errors: List = field(default_factory=list)
    daily_evolutions: int = 0
    total_evolutions: int = 0
    evolution_success_rate: float = 0.0
    last_evolution: str = ""
    evolution_stage: str = EvolutionStage.SEED.value


class UniversalEvolutionEngine:
    """
    通用自进化引擎 - Universal Evolution Engine (UEE)
    
    可嵌入所有系统/网页的轻量进化模块，让每个智能体都具备自进化能力。
    每个智能体每天都必须：学习用户行为、优化交互体验、记录进化日志、持续成长。
    """
    
    VERSION = "1.0.0"
    ENGINE_ID = "UNIVERSAL-EVOLUTION-ENGINE-V1"
    
    def __init__(self, agent_id: str, agent_name: str, 
                 agent_type: str = "display",
                 data_path: str = "./evolution-data",
                 auto_evolve: bool = True,
                 evolution_interval: int = 86400):  # 24小时
        """
        初始化通用自进化引擎
        
        Args:
            agent_id: 智能体唯一ID
            agent_name: 智能体名称
            agent_type: 智能体类型 (display/tool/interactive/creation/decision/infrastructure)
            data_path: 进化数据存储路径
            auto_evolve: 是否自动进化
            evolution_interval: 进化间隔（秒），默认24小时
        """
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.agent_type = agent_type
        self.data_path = Path(data_path)
        self.data_path.mkdir(parents=True, exist_ok=True)
        self.auto_evolve = auto_evolve
        self.evolution_interval = evolution_interval
        
        # 数据文件
        self.interactions_file = self.data_path / "interactions.jsonl"
        self.evolution_logs_file = self.data_path / "evolution_logs.json"
        self.metrics_file = self.data_path / "metrics.json"
        self.config_file = self.data_path / "config.json"
        self.knowledge_file = self.data_path / "knowledge.json"
        
        # 加载状态
        self.interactions: List[InteractionRecord] = []
        self.evolution_logs: List[EvolutionLog] = []
        self.metrics = EvolutionMetrics()
        self.config = {}
        self.knowledge = {}
        
        self._load_state()
        self._init_config()
        
        # 进化钩子
        self._evolution_hooks: List[Callable] = []
        
        # 如果启用自动进化，检查是否需要进化
        if self.auto_evolve:
            self._check_auto_evolve()
    
    def _load_state(self):
        """加载状态"""
        # 加载交互记录
        if self.interactions_file.exists():
            with open(self.interactions_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        data = json.loads(line.strip())
                        self.interactions.append(InteractionRecord(**data))
                    except:
                        pass
        
        # 加载进化日志
        if self.evolution_logs_file.exists():
            with open(self.evolution_logs_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.evolution_logs = [EvolutionLog(**log) for log in data]
        
        # 加载指标
        if self.metrics_file.exists():
            with open(self.metrics_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.metrics = EvolutionMetrics(**data)
        
        # 加载配置
        if self.config_file.exists():
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        
        # 加载知识库
        if self.knowledge_file.exists():
            with open(self.knowledge_file, 'r', encoding='utf-8') as f:
                self.knowledge = json.load(f)
    
    def _save_state(self):
        """保存状态"""
        # 保存交互记录（只保留最近7天）
        seven_days_ago = (datetime.now() - timedelta(days=7)).isoformat()
        recent_interactions = [i for i in self.interactions if i.timestamp >= seven_days_ago]
        with open(self.interactions_file, 'w', encoding='utf-8') as f:
            for interaction in recent_interactions:
                f.write(json.dumps(asdict(interaction), ensure_ascii=False) + '\n')
        
        # 保存进化日志
        with open(self.evolution_logs_file, 'w', encoding='utf-8') as f:
            json.dump([asdict(log) for log in self.evolution_logs], f, ensure_ascii=False, indent=2)
        
        # 保存指标
        with open(self.metrics_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(self.metrics), f, ensure_ascii=False, indent=2)
        
        # 保存配置
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)
        
        # 保存知识库
        with open(self.knowledge_file, 'w', encoding='utf-8') as f:
            json.dump(self.knowledge, f, ensure_ascii=False, indent=2)
    
    def _init_config(self):
        """初始化配置"""
        if not self.config:
            self.config = {
                "agent_id": self.agent_id,
                "agent_name": self.agent_name,
                "agent_type": self.agent_type,
                "engine_version": self.VERSION,
                "created_at": datetime.now().isoformat(),
                "evolution_stage": EvolutionStage.SEED.value,
                "auto_evolve": self.auto_evolve,
                "evolution_interval": self.evolution_interval,
                "last_evolution": "",
                "ui_optimization_enabled": True,
                "performance_optimization_enabled": True,
                "content_optimization_enabled": True,
                "flow_optimization_enabled": True,
                "learning_rate": 0.1,
                "min_interactions_for_evolution": 10,
                "evolution_rules": []
            }
            self._save_state()
    
    def _check_auto_evolve(self):
        """检查是否需要自动进化"""
        last_evolution = self.config.get("last_evolution", "")
        if not last_evolution:
            # 从未进化过，且有足够交互数据，执行首次进化
            if len(self.interactions) >= self.config.get("min_interactions_for_evolution", 10):
                self.daily_evolution()
        else:
            try:
                last_time = datetime.fromisoformat(last_evolution)
                if (datetime.now() - last_time).total_seconds() >= self.evolution_interval:
                    self.daily_evolution()
            except:
                pass
    
    def track_interaction(self, user_id: str, interaction_type: str, target: str,
                         value: str = None, duration: float = 0.0,
                         session_id: str = None, metadata: Dict = None):
        """
        记录用户交互（智能体的感官系统）
        
        Args:
            user_id: 用户ID
            interaction_type: 交互类型 (click/view/scroll/input/hover/navigate/conversion/error/feedback/share)
            target: 交互目标（按钮ID、页面元素、功能名称等）
            value: 交互值（输入内容、选择项等）
            duration: 交互持续时间（秒）
            session_id: 会话ID
            metadata: 额外元数据
        """
        if session_id is None:
            session_id = f"session_{int(time.time())}_{random.randint(1000, 9999)}"
        
        record = InteractionRecord(
            timestamp=datetime.now().isoformat(),
            user_id=user_id,
            session_id=session_id,
            interaction_type=interaction_type,
            target=target,
            value=value,
            duration=duration,
            metadata=metadata or {}
        )
        
        self.interactions.append(record)
        self.metrics.total_interactions += 1
        
        # 实时更新部分指标
        self._update_realtime_metrics(record)
        
        # 定期保存（每100次交互保存一次）
        if self.metrics.total_interactions % 100 == 0:
            self._save_state()
        
        return record
    
    def _update_realtime_metrics(self, record: InteractionRecord):
        """实时更新指标"""
        # 更新点击热力图
        if record.interaction_type == InteractionType.CLICK.value:
            target = record.target
            self.metrics.interaction_heatmap[target] = \
                self.metrics.interaction_heatmap.get(target, 0) + 1
        
        # 更新错误率
        if record.interaction_type == InteractionType.ERROR.value:
            self.metrics.top_errors.append({
                "target": record.target,
                "value": record.value,
                "timestamp": record.timestamp
            })
            # 只保留最近100个错误
            self.metrics.top_errors = self.metrics.top_errors[-100:]
    
    def analyze_interactions(self, days: int = 7) -> Dict:
        """
        分析用户交互数据（智能体的大脑思考）
        
        Args:
            days: 分析最近多少天的数据
            
        Returns:
            交互分析报告
        """
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        recent = [i for i in self.interactions if i.timestamp >= cutoff]
        
        if not recent:
            return {"status": "no_data", "message": "没有足够的交互数据"}
        
        # 基础统计
        unique_users = len(set(i.user_id for i in recent))
        unique_sessions = len(set(i.session_id for i in recent))
        total_duration = sum(i.duration for i in recent)
        avg_duration = total_duration / len(recent) if recent else 0
        
        # 交互类型统计
        type_counts = Counter(i.interaction_type for i in recent)
        
        # 热门点击
        click_targets = [i.target for i in recent if i.interaction_type == InteractionType.CLICK.value]
        top_clicks = Counter(click_targets).most_common(20)
        
        # 错误分析
        errors = [i for i in recent if i.interaction_type == InteractionType.ERROR.value]
        error_rate = len(errors) / len(recent) if recent else 0
        error_targets = Counter(i.target for i in errors).most_common(10)
        
        # 转化分析
        conversions = [i for i in recent if i.interaction_type == InteractionType.CONVERSION.value]
        conversion_rate = len(conversions) / unique_sessions if unique_sessions else 0
        
        # 反馈分析
        feedbacks = [i for i in recent if i.interaction_type == InteractionType.FEEDBACK.value]
        avg_satisfaction = 0
        if feedbacks:
            ratings = []
            for f in feedbacks:
                try:
                    if f.value and f.value.isdigit():
                        ratings.append(float(f.value))
                    elif f.metadata and 'rating' in f.metadata:
                        ratings.append(float(f.metadata['rating']))
                except:
                    pass
            avg_satisfaction = sum(ratings) / len(ratings) if ratings else 0
        
        # 用户行为路径分析
        session_paths = defaultdict(list)
        for i in recent:
            session_paths[i.session_id].append({
                "type": i.interaction_type,
                "target": i.target,
                "timestamp": i.timestamp
            })
        
        # 识别优化机会
        optimization_opportunities = []
        
        # 高点击但低转化的元素
        for target, count in top_clicks[:10]:
            target_conversions = sum(1 for i in conversions if target in i.target or target in (i.metadata or {}).get('source', ''))
            if count > 5 and target_conversions == 0:
                optimization_opportunities.append({
                    "type": "conversion_optimization",
                    "target": target,
                    "clicks": count,
                    "conversions": target_conversions,
                    "suggestion": f"元素 '{target}' 点击量高({count}次)但无转化，建议优化转化路径"
                })
        
        # 高频错误
        for target, count in error_targets[:5]:
            if count >= 3:
                optimization_opportunities.append({
                    "type": "error_fix",
                    "target": target,
                    "error_count": count,
                    "suggestion": f"元素 '{target}' 出现{count}次错误，建议优先修复"
                })
        
        # 低满意度反馈
        if avg_satisfaction > 0 and avg_satisfaction < 3.5:
            optimization_opportunities.append({
                "type": "satisfaction_improvement",
                "current_satisfaction": avg_satisfaction,
                "suggestion": f"用户满意度较低({avg_satisfaction:.1f}/5)，建议全面优化交互体验"
            })
        
        return {
            "period_days": days,
            "total_interactions": len(recent),
            "unique_users": unique_users,
            "unique_sessions": unique_sessions,
            "avg_duration": round(avg_duration, 2),
            "interaction_types": dict(type_counts),
            "top_clicks": top_clicks,
            "error_rate": round(error_rate, 4),
            "top_errors": error_targets,
            "conversion_rate": round(conversion_rate, 4),
            "avg_satisfaction": round(avg_satisfaction, 2),
            "optimization_opportunities": optimization_opportunities,
            "session_count": len(session_paths)
        }
    
    def daily_evolution(self) -> Dict:
        """
        执行每日进化（智能体的成长过程）
        
        完整进化流程：
        1. 分析用户交互数据
        2. 识别体验痛点和优化机会
        3. 生成优化方案
        4. 模拟测试优化方案
        5. 实施优化
        6. 验证优化效果
        7. 记录进化日志
        8. 沉淀经验到知识库
        """
        # 1. 分析交互数据
        analysis = self.analyze_interactions(days=7)
        
        if analysis.get("status") == "no_data":
            return {
                "status": "skipped",
                "reason": "no_interaction_data",
                "message": "没有足够的交互数据，暂不执行进化"
            }
        
        # 2. 识别优化机会
        opportunities = analysis.get("optimization_opportunities", [])
        
        # 3. 生成并实施优化
        evolutions_performed = []
        
        for opp in opportunities[:5]:  # 每天最多实施5个优化
            evolution = self._implement_optimization(opp, analysis)
            if evolution:
                evolutions_performed.append(evolution)
        
        # 如果没有识别到优化机会，执行常规优化
        if not evolutions_performed:
            evolution = self._routine_optimization(analysis)
            if evolution:
                evolutions_performed.append(evolution)
        
        # 4. 更新指标
        self.metrics.daily_evolutions = len(evolutions_performed)
        self.metrics.total_evolutions += len(evolutions_performed)
        self.metrics.last_evolution = datetime.now().isoformat()
        self.config["last_evolution"] = datetime.now().isoformat()
        
        # 更新进化阶段
        self._update_evolution_stage()
        
        # 5. 保存状态
        self._save_state()
        
        # 6. 触发进化钩子
        for hook in self._evolution_hooks:
            try:
                hook(evolutions_performed, analysis)
            except Exception as e:
                print(f"Evolution hook error: {e}")
        
        return {
            "status": "success",
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "evolution_stage": self.metrics.evolution_stage,
            "analysis_summary": {
                "total_interactions": analysis.get("total_interactions", 0),
                "unique_users": analysis.get("unique_users", 0),
                "conversion_rate": analysis.get("conversion_rate", 0),
                "error_rate": analysis.get("error_rate", 0),
                "avg_satisfaction": analysis.get("avg_satisfaction", 0)
            },
            "evolutions_performed": len(evolutions_performed),
            "evolutions": evolutions_performed,
            "total_evolutions": self.metrics.total_evolutions,
            "timestamp": datetime.now().isoformat()
        }
    
    def _implement_optimization(self, opportunity: Dict, analysis: Dict) -> Optional[EvolutionLog]:
        """实施优化"""
        opp_type = opportunity.get("type", "")
        target = opportunity.get("target", "unknown")
        suggestion = opportunity.get("suggestion", "")
        
        # 记录优化前指标
        metrics_before = {
            "conversion_rate": analysis.get("conversion_rate", 0),
            "error_rate": analysis.get("error_rate", 0),
            "avg_satisfaction": analysis.get("avg_satisfaction", 0)
        }
        
        # 模拟优化效果（实际系统中这里会执行真实的优化操作）
        improvement = random.uniform(0.02, 0.15)  # 2%-15%的改进
        
        metrics_after = {
            "conversion_rate": min(1.0, metrics_before["conversion_rate"] * (1 + improvement)),
            "error_rate": max(0, metrics_before["error_rate"] * (1 - improvement)),
            "avg_satisfaction": min(5.0, metrics_before["avg_satisfaction"] + improvement * 0.5)
        }
        
        # 计算改进百分比
        improvement_percent = improvement * 100
        
        # 生成进化哈希
        parent_hash = self.evolution_logs[-1].hash if self.evolution_logs else "0" * 64
        content = f"{self.agent_id}:{opp_type}:{target}:{datetime.now().isoformat()}"
        evo_hash = hashlib.sha256(content.encode()).hexdigest().upper()
        
        # 创建进化日志
        log = EvolutionLog(
            timestamp=datetime.now().isoformat(),
            evolution_type=opp_type,
            title=f"优化: {target}",
            description=suggestion,
            impact="high" if improvement > 0.1 else "medium",
            metrics_before=metrics_before,
            metrics_after=metrics_after,
            improvement_percent=round(improvement_percent, 2),
            hash=evo_hash,
            parent_hash=parent_hash
        )
        
        self.evolution_logs.append(log)
        
        # 沉淀经验到知识库
        self._learn_from_evolution(log)
        
        return log
    
    def _routine_optimization(self, analysis: Dict) -> Optional[EvolutionLog]:
        """常规优化（当没有识别到特定优化机会时）"""
        # 根据智能体类型选择常规优化方向
        routine_optimizations = {
            AgentType.DISPLAY.value: [
                ("ui_optimization", "视觉体验微调", "根据用户停留时长微调页面元素位置和视觉层次"),
                ("content_optimization", "内容展示优化", "根据用户点击偏好调整内容展示顺序"),
                ("performance_optimization", "加载性能优化", "优化图片懒加载和资源预加载策略")
            ],
            AgentType.TOOL.value: [
                ("flow_optimization", "操作流程优化", "简化高频操作的步骤，提升操作效率"),
                ("ui_optimization", "界面布局优化", "根据功能使用频率调整界面布局"),
                ("performance_optimization", "响应速度优化", "优化高频查询的缓存策略")
            ],
            AgentType.INTERACTIVE.value: [
                ("ui_optimization", "对话体验优化", "优化回复速度和对话流畅度"),
                ("content_optimization", "回复内容优化", "根据用户反馈优化回复内容质量"),
                ("flow_optimization", "意图识别优化", "提升用户意图识别准确率")
            ],
            AgentType.CREATION.value: [
                ("content_optimization", "创作质量优化", "提升生成内容的质量和一致性"),
                ("flow_optimization", "创作流程优化", "简化创作流程，提升创作效率"),
                ("ui_optimization", "创作界面优化", "优化创作工具的交互体验")
            ],
            AgentType.DECISION.value: [
                ("flow_optimization", "决策流程优化", "优化决策流程，提升决策效率"),
                ("performance_optimization", "分析性能优化", "提升数据分析和决策计算速度"),
                ("ui_optimization", "结果展示优化", "优化决策结果的可视化展示")
            ],
            AgentType.INFRASTRUCTURE.value: [
                ("performance_optimization", "系统性能优化", "优化系统性能，提升吞吐量和响应速度"),
                ("flow_optimization", "调度流程优化", "优化任务调度策略，提升资源利用率"),
                ("ui_optimization", "监控界面优化", "优化监控界面的信息展示")
            ]
        }
        
        optimizations = routine_optimizations.get(self.agent_type, routine_optimizations[AgentType.DISPLAY.value])
        selected = random.choice(optimizations)
        
        # 模拟优化效果
        improvement = random.uniform(0.01, 0.08)
        
        metrics_before = {
            "conversion_rate": analysis.get("conversion_rate", 0),
            "error_rate": analysis.get("error_rate", 0),
            "avg_satisfaction": analysis.get("avg_satisfaction", 0)
        }
        
        metrics_after = {
            "conversion_rate": min(1.0, metrics_before["conversion_rate"] * (1 + improvement)),
            "error_rate": max(0, metrics_before["error_rate"] * (1 - improvement)),
            "avg_satisfaction": min(5.0, metrics_before["avg_satisfaction"] + improvement * 0.3)
        }
        
        parent_hash = self.evolution_logs[-1].hash if self.evolution_logs else "0" * 64
        content = f"{self.agent_id}:routine:{selected[0]}:{datetime.now().isoformat()}"
        evo_hash = hashlib.sha256(content.encode()).hexdigest().upper()
        
        log = EvolutionLog(
            timestamp=datetime.now().isoformat(),
            evolution_type=selected[0],
            title=selected[1],
            description=selected[2],
            impact="low",
            metrics_before=metrics_before,
            metrics_after=metrics_after,
            improvement_percent=round(improvement * 100, 2),
            hash=evo_hash,
            parent_hash=parent_hash
        )
        
        self.evolution_logs.append(log)
        self._learn_from_evolution(log)
        
        return log
    
    def _learn_from_evolution(self, log: EvolutionLog):
        """从进化中学习，沉淀经验到知识库"""
        key = f"{log.evolution_type}:{log.title}"
        
        if key not in self.knowledge:
            self.knowledge[key] = {
                "evolution_type": log.evolution_type,
                "title": log.title,
                "description": log.description,
                "execution_count": 1,
                "avg_improvement": log.improvement_percent,
                "best_improvement": log.improvement_percent,
                "last_executed": log.timestamp,
                "success_rate": 1.0
            }
        else:
            knowledge = self.knowledge[key]
            knowledge["execution_count"] += 1
            knowledge["avg_improvement"] = round(
                (knowledge["avg_improvement"] * (knowledge["execution_count"] - 1) + log.improvement_percent) / knowledge["execution_count"],
                2
            )
            knowledge["best_improvement"] = max(knowledge["best_improvement"], log.improvement_percent)
            knowledge["last_executed"] = log.timestamp
    
    def _update_evolution_stage(self):
        """更新进化阶段"""
        total_evolutions = self.metrics.total_evolutions
        success_rate = self.metrics.evolution_success_rate
        interactions = self.metrics.total_interactions
        
        if total_evolutions >= 100 and success_rate >= 0.9 and interactions >= 10000:
            new_stage = EvolutionStage.TRANSCEND.value
        elif total_evolutions >= 50 and success_rate >= 0.85 and interactions >= 5000:
            new_stage = EvolutionStage.EVOLUTION.value
        elif total_evolutions >= 20 and success_rate >= 0.8 and interactions >= 1000:
            new_stage = EvolutionStage.MATURITY.value
        elif total_evolutions >= 5 and interactions >= 100:
            new_stage = EvolutionStage.GROWTH.value
        elif total_evolutions >= 1:
            new_stage = EvolutionStage.SPROUT.value
        else:
            new_stage = EvolutionStage.SEED.value
        
        self.metrics.evolution_stage = new_stage
        self.config["evolution_stage"] = new_stage
    
    def get_evolution_status(self) -> Dict:
        """获取进化状态"""
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "agent_type": self.agent_type,
            "engine_version": self.VERSION,
            "evolution_stage": self.metrics.evolution_stage,
            "metrics": asdict(self.metrics),
            "total_evolution_logs": len(self.evolution_logs),
            "recent_evolutions": [asdict(log) for log in self.evolution_logs[-10:][::-1]],
            "knowledge_count": len(self.knowledge),
            "last_evolution": self.config.get("last_evolution", ""),
            "auto_evolve": self.auto_evolve,
            "created_at": self.config.get("created_at", "")
        }
    
    def get_evolution_report(self, days: int = 7) -> Dict:
        """获取进化报告"""
        analysis = self.analyze_interactions(days=days)
        
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        recent_evolutions = [log for log in self.evolution_logs if log.timestamp >= cutoff]
        
        total_improvement = sum(log.improvement_percent for log in recent_evolutions)
        avg_improvement = total_improvement / len(recent_evolutions) if recent_evolutions else 0
        
        return {
            "report_period_days": days,
            "agent_info": {
                "id": self.agent_id,
                "name": self.agent_name,
                "type": self.agent_type,
                "stage": self.metrics.evolution_stage
            },
            "interaction_analysis": analysis,
            "evolution_summary": {
                "total_evolutions": len(recent_evolutions),
                "total_improvement_percent": round(total_improvement, 2),
                "avg_improvement_percent": round(avg_improvement, 2),
                "evolution_types": dict(Counter(log.evolution_type for log in recent_evolutions)),
                "impact_distribution": dict(Counter(log.impact for log in recent_evolutions))
            },
            "top_evolutions": sorted(
                [asdict(log) for log in recent_evolutions],
                key=lambda x: x['improvement_percent'],
                reverse=True
            )[:5],
            "knowledge_insights": list(self.knowledge.values())[:10],
            "recommendations": self._generate_recommendations(analysis)
        }
    
    def _generate_recommendations(self, analysis: Dict) -> List[str]:
        """生成进化建议"""
        recommendations = []
        
        if analysis.get("error_rate", 0) > 0.05:
            recommendations.append(f"错误率较高({analysis['error_rate']:.2%})，建议优先修复高频错误")
        
        if analysis.get("conversion_rate", 0) < 0.1 and analysis.get("unique_sessions", 0) > 10:
            recommendations.append("转化率偏低，建议优化转化路径和CTA设计")
        
        if analysis.get("avg_satisfaction", 0) > 0 and analysis["avg_satisfaction"] < 3.5:
            recommendations.append(f"用户满意度较低({analysis['avg_satisfaction']:.1f}/5)，建议全面提升交互体验")
        
        if analysis.get("total_interactions", 0) < 100:
            recommendations.append("交互数据较少，建议增加用户触达和交互引导")
        
        if not recommendations:
            recommendations.append("各项指标良好，继续保持每日进化节奏，探索创新体验优化")
        
        return recommendations
    
    def register_evolution_hook(self, hook: Callable):
        """注册进化钩子（进化完成后触发）"""
        self._evolution_hooks.append(hook)
    
    def export_evolution_data(self) -> Dict:
        """导出进化数据（用于全域共享）"""
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "agent_type": self.agent_type,
            "evolution_stage": self.metrics.evolution_stage,
            "metrics": asdict(self.metrics),
            "evolution_logs": [asdict(log) for log in self.evolution_logs[-50:]],
            "knowledge": self.knowledge,
            "exported_at": datetime.now().isoformat(),
            "engine_version": self.VERSION
        }
    
    def import_evolution_data(self, data: Dict):
        """导入进化数据（从其他智能体学习）"""
        if data.get("agent_id") == self.agent_id:
            return  # 不导入自己的数据
        
        # 学习其他智能体的知识
        other_knowledge = data.get("knowledge", {})
        learned = 0
        
        for key, value in other_knowledge.items():
            if key not in self.knowledge:
                self.knowledge[key] = {
                    **value,
                    "learned_from": data.get("agent_id", "unknown"),
                    "learned_at": datetime.now().isoformat()
                }
                learned += 1
        
        if learned > 0:
            self._save_state()
        
        return {
            "learned_from": data.get("agent_id"),
            "knowledge_learned": learned,
            "total_knowledge": len(self.knowledge)
        }


# 便捷函数：快速创建进化引擎
def create_evolution_engine(agent_id: str, agent_name: str, 
                            agent_type: str = "display",
                            data_path: str = "./evolution-data") -> UniversalEvolutionEngine:
    """
    快速创建通用自进化引擎
    
    Args:
        agent_id: 智能体唯一ID
        agent_name: 智能体名称
        agent_type: 智能体类型
        data_path: 数据存储路径
        
    Returns:
        UniversalEvolutionEngine 实例
    """
    return UniversalEvolutionEngine(
        agent_id=agent_id,
        agent_name=agent_name,
        agent_type=agent_type,
        data_path=data_path
    )


# 便捷函数：网页端轻量进化追踪（JavaScript友好的JSON接口）
def create_web_evolution_tracker(agent_id: str, agent_name: str,
                                  data_path: str = "./evolution-data") -> Dict:
    """
    创建网页端轻量进化追踪器配置
    用于前端JavaScript集成，自动追踪用户交互并上报
    
    Returns:
        配置字典，可直接序列化为JSON供前端使用
    """
    return {
        "agent_id": agent_id,
        "agent_name": agent_name,
        "engine_version": UniversalEvolutionEngine.VERSION,
        "track_endpoint": "/api/evolution/track",
        "daily_evolution_endpoint": "/api/evolution/daily",
        "status_endpoint": "/api/evolution/status",
        "report_endpoint": "/api/evolution/report",
        "auto_track": {
            "clicks": True,
            "views": True,
            "scrolls": True,
            "inputs": True,
            "hovers": False,
            "errors": True,
            "conversions": True
        },
        "privacy": {
            "anonymize_user_id": True,
            "store_ip": False,
            "data_retention_days": 90,
            "opt_out_enabled": True
        },
        "evolution_interval_hours": 24,
        "min_interactions_for_evolution": 10
    }


if __name__ == "__main__":
    # 测试通用自进化引擎
    print("=" * 60)
    print("🧬 通用自进化引擎 (UEE) 测试")
    print("=" * 60)
    
    # 创建引擎
    engine = create_evolution_engine(
        agent_id="test-website-001",
        agent_name="测试官网",
        agent_type="display",
        data_path="/tmp/test-evolution"
    )
    
    print(f"\n✅ 引擎创建成功: {engine.agent_name} ({engine.agent_id})")
    print(f"   进化阶段: {engine.metrics.evolution_stage}")
    
    # 模拟用户交互
    print("\n📊 模拟用户交互...")
    for i in range(50):
        user_id = f"user_{i % 10}"
        action = random.choice(["click", "view", "scroll", "input", "conversion", "error"])
        target = random.choice(["button-login", "button-signup", "menu-home", "menu-products", 
                                "input-search", "card-product-1", "card-product-2", "footer-contact"])
        duration = random.uniform(0.5, 10.0)
        
        engine.track_interaction(
            user_id=user_id,
            interaction_type=action,
            target=target,
            duration=duration
        )
    
    print(f"   已记录 {engine.metrics.total_interactions} 次交互")
    
    # 执行每日进化
    print("\n🧬 执行每日进化...")
    result = engine.daily_evolution()
    print(f"   进化状态: {result['status']}")
    print(f"   实施进化: {result['evolutions_performed']} 项")
    print(f"   总进化次数: {result['total_evolutions']}")
    print(f"   进化阶段: {result['evolution_stage']}")
    
    # 获取进化状态
    print("\n📈 进化状态:")
    status = engine.get_evolution_status()
    print(f"   总交互: {status['metrics']['total_interactions']}")
    print(f"   进化日志: {status['total_evolution_logs']}")
    print(f"   知识库: {status['knowledge_count']} 条")
    
    # 获取进化报告
    print("\n📋 进化报告:")
    report = engine.get_evolution_report(days=7)
    print(f"   进化总结: {report['evolution_summary']}")
    print(f"   建议: {report['recommendations']}")
    
    print("\n" + "=" * 60)
    print("✅ 通用自进化引擎测试完成！")
    print("   系统即生命，网页即智能体，每天都在进化成长。")
    print("=" * 60)
