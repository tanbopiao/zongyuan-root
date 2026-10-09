#!/usr/bin/env python3
"""
进化引擎模块 - Evolution Engine
让系统具备持续成长进化的能力：
- 进化日志记录（每次变更都有迹可循）
- 版本管理（语义化版本+进化阶段）
- 参数自优化（根据使用数据自动调整）
- 能力扩展接口（插件式功能扩展）
- 反馈闭环（用户反馈驱动进化）
- 性能自优化（根据负载自动调整）
"""
import json
import os
import time
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum


class EvolutionStage(Enum):
    """进化阶段"""
    SEED = "seed"           # 种子期：基础功能可用
    SPROUT = "sprout"       # 萌芽期：核心闭环形成
    GROWTH = "growth"       # 成长期：功能扩展完善
    MATURITY = "maturity"   # 成熟期：稳定高效运行
    EVOLUTION = "evolution" # 进化期：自我学习优化
    TRANSCEND = "transcend" # 超越期：突破原有边界


@dataclass
class EvolutionLog:
    """进化日志条目"""
    version: str
    stage: str
    timestamp: str
    type: str           # feature/fix/optimization/evolution/breaking
    title: str
    description: str
    impact: str         # low/medium/high/critical
    metrics: Dict       # 相关指标变化
    hash: str           # 变更哈希
    parent_hash: str    # 父变更哈希（链式继承）


@dataclass
class EvolutionMetrics:
    """进化指标"""
    total_files: int = 0
    total_uploads: int = 0
    total_archives: int = 0
    total_gallery_views: int = 0
    avg_upload_time: float = 0.0
    success_rate: float = 1.0
    storage_usage_mb: float = 0.0
    dedup_savings_mb: float = 0.0
    user_satisfaction: float = 0.0
    last_optimization: str = ""
    optimization_count: int = 0


class EvolutionEngine:
    """进化引擎 - 系统持续成长的核心动力"""
    
    def __init__(self, data_path: str = "/opt/storage/media/evolution"):
        self.data_path = Path(data_path)
        self.data_path.mkdir(parents=True, exist_ok=True)
        
        self.log_file = self.data_path / "evolution_log.json"
        self.metrics_file = self.data_path / "metrics.json"
        self.config_file = self.data_path / "config.json"
        self.feedback_file = self.data_path / "feedback.json"
        self.plugins_dir = self.data_path / "plugins"
        self.plugins_dir.mkdir(exist_ok=True)
        
        # 加载状态
        self.logs = self._load_logs()
        self.metrics = self._load_metrics()
        self.config = self._load_config()
        self.feedbacks = self._load_feedbacks()
        self.plugins = {}
        
        # 当前版本和阶段
        self.current_version = self.config.get("current_version", "1.1.0")
        self.current_stage = self.config.get("current_stage", EvolutionStage.SPROUT.value)
        
        # 注册内置插件
        self._register_builtin_plugins()
    
    def _load_logs(self) -> List[Dict]:
        if self.log_file.exists():
            with open(self.log_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    
    def _save_logs(self):
        with open(self.log_file, 'w', encoding='utf-8') as f:
            json.dump(self.logs, f, ensure_ascii=False, indent=2)
    
    def _load_metrics(self) -> EvolutionMetrics:
        if self.metrics_file.exists():
            with open(self.metrics_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return EvolutionMetrics(**data)
        return EvolutionMetrics()
    
    def _save_metrics(self):
        with open(self.metrics_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(self.metrics), f, ensure_ascii=False, indent=2)
    
    def _load_config(self) -> Dict:
        if self.config_file.exists():
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "current_version": "1.1.0",
            "current_stage": EvolutionStage.SPROUT.value,
            "auto_optimize": True,
            "learning_rate": 0.1,
            "optimization_interval": 86400,  # 24小时
            "last_optimization": "",
            "evolution_chain_root": "0" * 64
        }
    
    def _save_config(self):
        self.config["current_version"] = self.current_version
        self.config["current_stage"] = self.current_stage
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)
    
    def _load_feedbacks(self) -> List[Dict]:
        if self.feedback_file.exists():
            with open(self.feedback_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    
    def _save_feedbacks(self):
        with open(self.feedback_file, 'w', encoding='utf-8') as f:
            json.dump(self.feedbacks, f, ensure_ascii=False, indent=2)
    
    def _calculate_hash(self, content: str) -> str:
        return hashlib.sha256(content.encode('utf-8')).hexdigest().upper()
    
    def _get_parent_hash(self) -> str:
        if self.logs:
            return self.logs[-1].get("hash", self.config["evolution_chain_root"])
        return self.config["evolution_chain_root"]
    
    def _register_builtin_plugins(self):
        """注册内置进化插件"""
        self.plugins["auto_optimize"] = {
            "name": "自动参数优化",
            "description": "根据使用数据自动调整系统参数",
            "version": "1.0.0",
            "enabled": True,
            "trigger": "metrics_update"
        }
        self.plugins["dedup_optimizer"] = {
            "name": "去重优化器",
            "description": "智能识别相似文件，优化存储策略",
            "version": "1.0.0",
            "enabled": True,
            "trigger": "file_upload"
        }
        self.plugins["gallery_optimizer"] = {
            "name": "作品库优化器",
            "description": "根据访问数据优化作品库布局和加载策略",
            "version": "1.0.0",
            "enabled": True,
            "trigger": "gallery_view"
        }
    
    def record_evolution(self, evo_type: str, title: str, description: str,
                         impact: str = "medium", metrics: Dict = None) -> EvolutionLog:
        """记录一次进化"""
        parent_hash = self._get_parent_hash()
        content = f"{self.current_version}:{title}:{description}:{time.time()}"
        evo_hash = self._calculate_hash(content)
        
        log = EvolutionLog(
            version=self.current_version,
            stage=self.current_stage,
            timestamp=datetime.now().isoformat(),
            type=evo_type,
            title=title,
            description=description,
            impact=impact,
            metrics=metrics or {},
            hash=evo_hash,
            parent_hash=parent_hash
        )
        
        self.logs.append(asdict(log))
        self._save_logs()
        
        return log
    
    def upgrade_version(self, major: int = None, minor: int = None, 
                       patch: int = None, stage: str = None) -> str:
        """版本升级"""
        parts = self.current_version.split('.')
        v_major = int(parts[0])
        v_minor = int(parts[1]) if len(parts) > 1 else 0
        v_patch = int(parts[2]) if len(parts) > 2 else 0
        
        if major is not None:
            v_major = major
            v_minor = 0
            v_patch = 0
        elif minor is not None:
            v_minor = minor
            v_patch = 0
        elif patch is not None:
            v_patch = patch
        
        self.current_version = f"{v_major}.{v_minor}.{v_patch}"
        
        if stage:
            self.current_stage = stage
        
        self._save_config()
        
        self.record_evolution(
            evo_type="evolution",
            title=f"版本升级到 v{self.current_version}",
            description=f"系统进化到新版本，当前阶段: {self.current_stage}",
            impact="high"
        )
        
        return self.current_version
    
    def update_metrics(self, **kwargs):
        """更新进化指标"""
        for key, value in kwargs.items():
            if hasattr(self.metrics, key):
                setattr(self.metrics, key, value)
        
        self.metrics.last_optimization = datetime.now().isoformat()
        self._save_metrics()
        
        # 触发自动优化
        if self.config.get("auto_optimize", True):
            self._auto_optimize()
    
    def _auto_optimize(self):
        """自动参数优化（根据指标数据）"""
        self.metrics.optimization_count += 1
        
        # 示例优化逻辑：根据成功率调整重试策略
        if self.metrics.success_rate < 0.9:
            # 成功率低，增加重试次数
            self.config["max_retries"] = min(5, self.config.get("max_retries", 3) + 1)
        
        if self.metrics.avg_upload_time > 30:
            # 上传慢，调整分片大小
            self.config["chunk_size"] = max(4*1024*1024, 
                                            self.config.get("chunk_size", 8*1024*1024) // 2)
        
        self._save_config()
        self._save_metrics()
    
    def add_feedback(self, feedback_type: str, content: str, 
                    rating: int = 0, metadata: Dict = None) -> Dict:
        """添加用户反馈（驱动进化）"""
        feedback = {
            "id": len(self.feedbacks) + 1,
            "type": feedback_type,  # bug/feature/improvement/praise/complaint
            "content": content,
            "rating": rating,  # 1-5
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat(),
            "status": "pending",  # pending/analyzing/planned/implemented/rejected
            "evolution_triggered": False
        }
        
        self.feedbacks.append(feedback)
        self._save_feedbacks()
        
        # 高优先级反馈触发进化分析
        if rating <= 2 or feedback_type in ["bug", "complaint"]:
            self._analyze_feedback(feedback)
        
        return feedback
    
    def _analyze_feedback(self, feedback: Dict):
        """分析反馈，决定是否触发进化"""
        # 简单逻辑：负面反馈或功能建议触发进化记录
        if feedback["type"] in ["bug", "complaint"]:
            self.record_evolution(
                evo_type="fix",
                title=f"反馈驱动修复: {feedback['content'][:50]}",
                description=f"用户反馈ID#{feedback['id']}触发的修复进化",
                impact="medium",
                metrics={"feedback_id": feedback["id"]}
            )
            feedback["evolution_triggered"] = True
            self._save_feedbacks()
    
    def register_plugin(self, name: str, plugin_info: Dict):
        """注册扩展插件（能力扩展）"""
        self.plugins[name] = {
            **plugin_info,
            "registered_at": datetime.now().isoformat()
        }
        
        self.record_evolution(
            evo_type="feature",
            title=f"能力扩展: {plugin_info.get('name', name)}",
            description=f"注册新插件扩展系统能力: {plugin_info.get('description', '')}",
            impact="medium"
        )
    
    def get_evolution_summary(self) -> Dict:
        """获取进化总结"""
        return {
            "current_version": self.current_version,
            "current_stage": self.current_stage,
            "stage_name": EvolutionStage(self.current_stage).name,
            "total_evolutions": len(self.logs),
            "evolution_types": self._count_by_type(),
            "metrics": asdict(self.metrics),
            "plugins_count": len(self.plugins),
            "feedbacks_count": len(self.feedbacks),
            "pending_feedbacks": sum(1 for f in self.feedbacks if f["status"] == "pending"),
            "evolution_chain_length": len(self.logs),
            "last_evolution": self.logs[-1] if self.logs else None
        }
    
    def _count_by_type(self) -> Dict:
        counts = {}
        for log in self.logs:
            t = log.get("type", "unknown")
            counts[t] = counts.get(t, 0) + 1
        return counts
    
    def get_evolution_roadmap(self) -> Dict:
        """获取进化路线图"""
        return {
            "current": {
                "version": self.current_version,
                "stage": self.current_stage,
                "features": ["基础上传归档", "作品库展示", "元秩序确权", "自动去重"]
            },
            "v2.0": {
                "target_stage": EvolutionStage.GROWTH.value,
                "eta": "3个月",
                "features": [
                    "视频缩略图自动生成",
                    "图片智能压缩/格式转换",
                    "批量导入工具",
                    "作品库主题切换",
                    "访问统计分析",
                    "多用户支持"
                ]
            },
            "v3.0": {
                "target_stage": EvolutionStage.MATURITY.value,
                "eta": "6个月",
                "features": [
                    "AI智能标签自动生成",
                    "相似图片聚类",
                    "智能搜索（语义搜索）",
                    "作品推荐系统",
                    "CDN加速集成",
                    "移动端APP"
                ]
            },
            "v4.0": {
                "target_stage": EvolutionStage.EVOLUTION.value,
                "eta": "12个月",
                "features": [
                    "自我学习优化",
                    "预测性缓存",
                    "自动容量规划",
                    "智能备份策略",
                    "跨平台同步",
                    "区块链确权"
                ]
            },
            "v5.0": {
                "target_stage": EvolutionStage.TRANSCEND.value,
                "eta": "18个月+",
                "features": [
                    "AGI协同创作",
                    "多模态内容生成",
                    "去中心化存储",
                    "元宇宙展示",
                    "脑机接口交互",
                    "突破数字边界"
                ]
            }
        }


# 全局进化引擎实例
_evolution_engine = None

def get_evolution_engine(data_path: str = None) -> EvolutionEngine:
    """获取进化引擎单例"""
    global _evolution_engine
    if _evolution_engine is None:
        path = data_path or "/opt/storage/media/evolution"
        _evolution_engine = EvolutionEngine(path)
    return _evolution_engine


if __name__ == "__main__":
    # 测试进化引擎
    engine = EvolutionEngine("/tmp/test-evolution")
    
    print("=== 进化引擎测试 ===")
    print(f"当前版本: {engine.current_version}")
    print(f"当前阶段: {engine.current_stage}")
    
    # 记录一次进化
    log = engine.record_evolution(
        evo_type="feature",
        title="进化引擎初始化",
        description="系统进化引擎首次启动，具备持续成长能力",
        impact="high"
    )
    print(f"\n记录进化: {log.title}")
    print(f"进化哈希: {log.hash[:16]}...")
    
    # 版本升级
    new_version = engine.upgrade_version(minor=2, stage=EvolutionStage.GROWTH.value)
    print(f"\n版本升级: {new_version}")
    
    # 更新指标
    engine.update_metrics(
        total_files=100,
        total_uploads=150,
        success_rate=0.98,
        avg_upload_time=2.5
    )
    
    # 获取总结
    summary = engine.get_evolution_summary()
    print(f"\n进化总结:")
    print(f"  总进化次数: {summary['total_evolutions']}")
    print(f"  插件数量: {summary['plugins_count']}")
    print(f"  进化类型: {summary['evolution_types']}")
    
    print("\n✅ 进化引擎测试完成！")
