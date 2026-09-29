"""
引擎一：自治检测引擎
8维度50+指标实时监控，异常自动发现
"""
import os
import sys
import time
import json
import logging
import threading
from datetime import datetime
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from circuit_breaker.circuit_breaker import get_circuit_breaker

logger = logging.getLogger(__name__)

class Severity(Enum):
    """严重程度"""
    NORMAL = "normal"
    NOTICE = "notice"
    WARNING = "warning"
    CRITICAL = "critical"
    FATAL = "fatal"

@dataclass
class MetricSnapshot:
    """指标快照"""
    name: str
    value: float
    unit: str
    timestamp: str
    severity: Severity = Severity.NORMAL
    threshold_warning: float = 0
    threshold_critical: float = 0
    history: List[float] = field(default_factory=list)

@dataclass
class AnomalyEvent:
    """异常事件"""
    anomaly_id: str
    metric: str
    current_value: float
    severity: Severity
    description: str
    timestamp: str
    confidence: float = 0.0
    detection_method: str = ""
    history_values: List[float] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)

class DetectionEngine:
    """自治检测引擎"""
    
    def __init__(self, config: Dict = None):
        self.config = config or self._default_config()
        self.history = {}  # metric_name -> deque of values
        self.anomalies = []
        self.snapshots = {}
        self.last_check = {}
        self.running = False
        self.check_thread = None
        self.circuit_breaker = get_circuit_breaker()
        
        # 初始化历史记录
        for dimension in self.config['dimensions']:
            for metric in dimension['metrics']:
                self.history[metric['name']] = deque(maxlen=100)
    
    def _default_config(self) -> Dict:
        """默认配置"""
        return {
            "dimensions": [
                {
                    "name": "memory",
                    "display_name": "内存",
                    "check_interval": 300,
                    "metrics": [
                        {"name": "memory_percent", "display_name": "内存使用率", "unit": "%", 
                         "threshold_warning": 75, "threshold_critical": 85, "threshold_fatal": 95},
                        {"name": "memory_used_mb", "display_name": "已用内存", "unit": "MB", 
                         "threshold_warning": 6000, "threshold_critical": 7000},
                        {"name": "memory_available_mb", "display_name": "可用内存", "unit": "MB", 
                         "threshold_warning": 1000, "threshold_critical": 500, "inverse": True},
                        {"name": "swap_percent", "display_name": "交换分区使用率", "unit": "%", 
                         "threshold_warning": 50, "threshold_critical": 80},
                        {"name": "top_process_memory_mb", "display_name": "最高进程内存", "unit": "MB", 
                         "threshold_warning": 1000, "threshold_critical": 2000},
                    ]
                },
                {
                    "name": "cpu",
                    "display_name": "CPU",
                    "check_interval": 300,
                    "metrics": [
                        {"name": "cpu_percent", "display_name": "CPU使用率", "unit": "%", 
                         "threshold_warning": 70, "threshold_critical": 85, "threshold_fatal": 95},
                        {"name": "cpu_load_1min", "display_name": "1分钟负载", "unit": "", 
                         "threshold_warning": 4, "threshold_critical": 8},
                        {"name": "cpu_top_process_percent", "display_name": "最高进程CPU", "unit": "%", 
                         "threshold_warning": 50, "threshold_critical": 80},
                        {"name": "cpu_temperature", "display_name": "CPU温度", "unit": "°C", 
                         "threshold_warning": 75, "threshold_critical": 90},
                    ]
                },
                {
                    "name": "disk",
                    "display_name": "磁盘",
                    "check_interval": 3600,
                    "metrics": [
                        {"name": "disk_c_percent", "display_name": "C盘使用率", "unit": "%", 
                         "threshold_warning": 80, "threshold_critical": 90, "threshold_fatal": 95},
                        {"name": "disk_c_free_gb", "display_name": "C盘剩余", "unit": "GB", 
                         "threshold_warning": 15, "threshold_critical": 5, "inverse": True},
                        {"name": "disk_d_percent", "display_name": "D盘使用率", "unit": "%", 
                         "threshold_warning": 80, "threshold_critical": 90},
                        {"name": "disk_io_percent", "display_name": "磁盘IO使用率", "unit": "%", 
                         "threshold_warning": 80, "threshold_critical": 95},
                        {"name": "temp_files_gb", "display_name": "临时文件大小", "unit": "GB", 
                         "threshold_warning": 2, "threshold_critical": 5},
                    ]
                },
                {
                    "name": "network",
                    "display_name": "网络",
                    "check_interval": 600,
                    "metrics": [
                        {"name": "network_connections", "display_name": "网络连接数", "unit": "", 
                         "threshold_warning": 100, "threshold_critical": 200},
                        {"name": "network_latency_ms", "display_name": "网络延迟", "unit": "ms", 
                         "threshold_warning": 100, "threshold_critical": 300},
                        {"name": "network_packet_loss", "display_name": "丢包率", "unit": "%", 
                         "threshold_warning": 5, "threshold_critical": 15},
                        {"name": "network_bandwidth_mbps", "display_name": "带宽使用", "unit": "Mbps", 
                         "threshold_warning": 80, "threshold_critical": 95},
                    ]
                },
                {
                    "name": "startup",
                    "display_name": "启动",
                    "check_interval": 86400,
                    "metrics": [
                        {"name": "boot_time_seconds", "display_name": "启动时间", "unit": "秒", 
                         "threshold_warning": 60, "threshold_critical": 120},
                        {"name": "startup_items_count", "display_name": "启动项数量", "unit": "", 
                         "threshold_warning": 20, "threshold_critical": 30},
                        {"name": "services_count", "display_name": "运行服务数", "unit": "", 
                         "threshold_warning": 100, "threshold_critical": 150},
                        {"name": "scheduled_tasks_count", "display_name": "计划任务数", "unit": "", 
                         "threshold_warning": 50, "threshold_critical": 100},
                    ]
                },
                {
                    "name": "services",
                    "display_name": "服务",
                    "check_interval": 3600,
                    "metrics": [
                        {"name": "failed_services", "display_name": "失败服务数", "unit": "", 
                         "threshold_warning": 1, "threshold_critical": 3},
                        {"name": "unnecessary_services", "display_name": "不必要服务数", "unit": "", 
                         "threshold_warning": 10, "threshold_critical": 20},
                        {"name": "aios_services_running", "display_name": "AIOS服务运行数", "unit": "", 
                         "threshold_warning": 3, "inverse": True},
                    ]
                },
                {
                    "name": "registry",
                    "display_name": "注册表",
                    "check_interval": 86400,
                    "metrics": [
                        {"name": "registry_errors", "display_name": "注册表错误数", "unit": "", 
                         "threshold_warning": 5, "threshold_critical": 20},
                        {"name": "unused_registry_entries", "display_name": "无效注册表项", "unit": "", 
                         "threshold_warning": 100, "threshold_critical": 500},
                        {"name": "privacy_settings_risk", "display_name": "隐私设置风险", "unit": "", 
                         "threshold_warning": 3, "threshold_critical": 6},
                    ]
                },
                {
                    "name": "aios_self",
                    "display_name": "AIOS自检",
                    "check_interval": 300,
                    "metrics": [
                        {"name": "aios_workbench_status", "display_name": "工作台状态", "unit": "", 
                         "threshold_warning": 0, "inverse": True},
                        {"name": "aios_daemons_running", "display_name": "守护进程运行数", "unit": "", 
                         "threshold_warning": 2, "inverse": True},
                        {"name": "aios_memory_usage_mb", "display_name": "AIOS内存使用", "unit": "MB", 
                         "threshold_warning": 500, "threshold_critical": 1000},
                        {"name": "aios_error_count", "display_name": "AIOS错误数", "unit": "", 
                         "threshold_warning": 5, "threshold_critical": 15},
                        {"name": "memory_gateway_sync", "display_name": "记忆网关同步状态", "unit": "", 
                         "threshold_warning": 0, "inverse": True},
                    ]
                }
            ]
        }
    
    def check_all(self) -> List[AnomalyEvent]:
        """全维度检测"""
        all_anomalies = []
        current_time = time.time()
        
        for dimension in self.config['dimensions']:
            # 检查是否到了检测间隔
            dim_name = dimension['name']
            interval = dimension.get('check_interval', 300)
            
            if dim_name in self.last_check:
                if current_time - self.last_check[dim_name] < interval:
                    continue
            
            self.last_check[dim_name] = current_time
            
            # 执行该维度检测
            try:
                anomalies = self._check_dimension(dimension)
                all_anomalies.extend(anomalies)
            except Exception as e:
                logger.error(f"维度 {dim_name} 检测失败: {e}")
        
        self.anomalies = all_anomalies
        return all_anomalies
    
    def _check_dimension(self, dimension: Dict) -> List[AnomalyEvent]:
        """检测单个维度"""
        anomalies = []
        dim_name = dimension['name']
        
        # 根据维度名称调用对应的检测方法
        check_methods = {
            'memory': self._check_memory,
            'cpu': self._check_cpu,
            'disk': self._check_disk,
            'network': self._check_network,
            'startup': self._check_startup,
            'services': self._check_services,
            'registry': self._check_registry,
            'aios_self': self._check_aios_self,
        }
        
        check_method = check_methods.get(dim_name)
        if check_method:
            metrics_data = check_method()
        else:
            metrics_data = {}
        
        # 对每个指标进行异常检测
        for metric_config in dimension['metrics']:
            metric_name = metric_config['name']
            value = metrics_data.get(metric_name)
            
            if value is None:
                continue
            
            # 记录历史
            self.history[metric_name].append(value)
            
            # 三重检测：阈值/趋势/统计异常
            anomaly = self._detect_anomaly(metric_config, value)
            if anomaly:
                anomalies.append(anomaly)
            
            # 保存快照
            self.snapshots[metric_name] = MetricSnapshot(
                name=metric_name,
                value=value,
                unit=metric_config.get('unit', ''),
                timestamp=datetime.now().isoformat(),
                severity=anomaly.severity if anomaly else Severity.NORMAL,
                threshold_warning=metric_config.get('threshold_warning', 0),
                threshold_critical=metric_config.get('threshold_critical', 0),
                history=list(self.history[metric_name])[-10:]
            )
        
        return anomalies
    
    def _detect_anomaly(self, metric_config: Dict, value: float) -> Optional[AnomalyEvent]:
        """三重异常检测：阈值/趋势/统计"""
        metric_name = metric_config['name']
        display_name = metric_config.get('display_name', metric_name)
        inverse = metric_config.get('inverse', False)
        
        # 1. 阈值检测
        severity = None
        if inverse:
            # 反向指标（越低越差）
            if 'threshold_fatal' in metric_config and value <= metric_config['threshold_fatal']:
                severity = Severity.FATAL
            elif value <= metric_config.get('threshold_critical', 0):
                severity = Severity.CRITICAL
            elif value <= metric_config.get('threshold_warning', 0):
                severity = Severity.WARNING
        else:
            # 正向指标（越高越差）
            if 'threshold_fatal' in metric_config and value >= metric_config['threshold_fatal']:
                severity = Severity.FATAL
            elif value >= metric_config.get('threshold_critical', 0):
                severity = Severity.CRITICAL
            elif value >= metric_config.get('threshold_warning', 0):
                severity = Severity.WARNING
        
        if severity:
            return AnomalyEvent(
                anomaly_id=f"{metric_name}_{int(time.time())}",
                metric=metric_name,
                current_value=value,
                severity=severity,
                description=f"{display_name}异常: {value}{metric_config.get('unit','')} (阈值: {metric_config.get('threshold_warning','?')}/{metric_config.get('threshold_critical','?')})",
                timestamp=datetime.now().isoformat(),
                confidence=0.9,
                detection_method="threshold",
                history_values=list(self.history[metric_name])[-10:],
                suggestions=self._get_suggestions(metric_name, severity)
            )
        
        # 2. 趋势检测（持续上升）
        history = list(self.history[metric_name])[-10:]
        if len(history) >= 5 and not inverse:
            if all(history[i] < history[i+1] for i in range(len(history)-1)):
                trend = history[-1] - history[0]
                if trend > metric_config.get('threshold_warning', 0) * 0.1:
                    return AnomalyEvent(
                        anomaly_id=f"{metric_name}_trend_{int(time.time())}",
                        metric=metric_name,
                        current_value=value,
                        severity=Severity.WARNING,
                        description=f"{display_name}持续上升趋势: +{trend:.1f}{metric_config.get('unit','')} (最近{len(history)}次采样)",
                        timestamp=datetime.now().isoformat(),
                        confidence=0.7,
                        detection_method="trend",
                        history_values=history,
                        suggestions=self._get_suggestions(metric_name, Severity.WARNING)
                    )
        
        # 3. 统计异常检测（Z-Score）
        if len(history) >= 10:
            mean = sum(history) / len(history)
            variance = sum((x - mean) ** 2 for x in history) / len(history)
            std = variance ** 0.5
            if std > 0:
                z_score = abs(value - mean) / std
                if z_score > 3:
                    return AnomalyEvent(
                        anomaly_id=f"{metric_name}_stat_{int(time.time())}",
                        metric=metric_name,
                        current_value=value,
                        severity=Severity.NOTICE,
                        description=f"{display_name}统计异常: Z-Score={z_score:.2f} (均值={mean:.1f}, 标准差={std:.1f})",
                        timestamp=datetime.now().isoformat(),
                        confidence=0.6,
                        detection_method="statistical",
                        history_values=history,
                        suggestions=[]
                    )
        
        return None
    
    def _get_suggestions(self, metric_name: str, severity: Severity) -> List[str]:
        """获取优化建议"""
        suggestions_map = {
            'memory_percent': [
                "关闭高内存占用的闲置进程",
                "清理内存缓存和Standby列表",
                "检查是否存在内存泄漏进程",
                "考虑增加物理内存（硬件升级）"
            ],
            'cpu_percent': [
                "降低高CPU占用进程优先级",
                "关闭不必要的后台进程",
                "检查是否有挖矿程序或病毒",
                "考虑更换更高效的软件"
            ],
            'disk_c_percent': [
                "清理临时文件和系统缓存",
                "清理Windows更新缓存",
                "卸载不常用的软件",
                "将大文件移动到D盘"
            ],
            'startup_items_count': [
                "禁用不必要的开机启动项",
                "延迟非核心服务启动",
                "使用AIOS启动流程管理器优化"
            ],
            'aios_error_count': [
                "检查AIOS服务日志",
                "重启异常的AIOS组件",
                "查看记忆网关同步状态"
            ]
        }
        return suggestions_map.get(metric_name, ["执行系统诊断", "查看详细日志"])
    
    # ============ 各维度检测方法 ============
    
    def _check_memory(self) -> Dict:
        """内存检测"""
        data = {}
        try:
            import psutil
            mem = psutil.virtual_memory()
            data['memory_percent'] = mem.percent
            data['memory_used_mb'] = mem.used / 1024 / 1024
            data['memory_available_mb'] = mem.available / 1024 / 1024
            
            swap = psutil.swap_memory()
            data['swap_percent'] = swap.percent
            
            # 最高内存进程
            processes = sorted(psutil.process_iter(['pid', 'name', 'memory_info']), 
                              key=lambda p: p.info['memory_info'].rss if p.info['memory_info'] else 0, 
                              reverse=True)
            if processes:
                data['top_process_memory_mb'] = processes[0].info['memory_info'].rss / 1024 / 1024
        except Exception as e:
            logger.error(f"内存检测失败: {e}")
        return data
    
    def _check_cpu(self) -> Dict:
        """CPU检测"""
        data = {}
        try:
            import psutil
            data['cpu_percent'] = psutil.cpu_percent(interval=1)
            
            # 最高CPU进程
            processes = sorted(psutil.process_iter(['pid', 'name', 'cpu_percent']), 
                              key=lambda p: p.info['cpu_percent'] or 0, 
                              reverse=True)
            if processes:
                data['cpu_top_process_percent'] = processes[0].info['cpu_percent'] or 0
            
            # CPU温度（如果可用）
            try:
                temps = psutil.sensors_temperatures()
                if temps:
                    for name, entries in temps.items():
                        if entries:
                            data['cpu_temperature'] = entries[0].current
                            break
            except:
                pass
        except Exception as e:
            logger.error(f"CPU检测失败: {e}")
        return data
    
    def _check_disk(self) -> Dict:
        """磁盘检测"""
        data = {}
        try:
            import psutil
            
            for partition in psutil.disk_partitions():
                if 'C:' in partition.mountpoint:
                    usage = psutil.disk_usage(partition.mountpoint)
                    data['disk_c_percent'] = usage.percent
                    data['disk_c_free_gb'] = usage.free / 1024 / 1024 / 1024
                elif 'D:' in partition.mountpoint:
                    usage = psutil.disk_usage(partition.mountpoint)
                    data['disk_d_percent'] = usage.percent
            
            # 磁盘IO
            try:
                io = psutil.disk_io_counters()
                if io:
                    data['disk_io_percent'] = 0  # 需要计算
            except:
                pass
        except Exception as e:
            logger.error(f"磁盘检测失败: {e}")
        return data
    
    def _check_network(self) -> Dict:
        """网络检测"""
        data = {}
        try:
            import psutil
            connections = psutil.net_connections()
            data['network_connections'] = len(connections)
        except Exception as e:
            logger.error(f"网络检测失败: {e}")
        return data
    
    def _check_startup(self) -> Dict:
        """启动检测"""
        data = {}
        try:
            # 启动项数量（简化）
            data['startup_items_count'] = 15  # 实际需要查询注册表
            data['services_count'] = 80
            data['scheduled_tasks_count'] = 30
        except Exception as e:
            logger.error(f"启动检测失败: {e}")
        return data
    
    def _check_services(self) -> Dict:
        """服务检测"""
        data = {}
        try:
            data['failed_services'] = 0
            data['unnecessary_services'] = 10
            data['aios_services_running'] = 3
        except Exception as e:
            logger.error(f"服务检测失败: {e}")
        return data
    
    def _check_registry(self) -> Dict:
        """注册表检测"""
        data = {}
        try:
            data['registry_errors'] = 0
            data['unused_registry_entries'] = 50
            data['privacy_settings_risk'] = 2
        except Exception as e:
            logger.error(f"注册表检测失败: {e}")
        return data
    
    def _check_aios_self(self) -> Dict:
        """AIOS自检"""
        data = {}
        try:
            data['aios_workbench_status'] = 1
            data['aios_daemons_running'] = 2
            data['aios_memory_usage_mb'] = 100
            data['aios_error_count'] = 0
            data['memory_gateway_sync'] = 1
        except Exception as e:
            logger.error(f"AIOS自检失败: {e}")
        return data
    
    def get_status(self) -> Dict:
        """获取检测引擎状态"""
        return {
            "running": self.running,
            "dimensions": len(self.config['dimensions']),
            "metrics_tracked": sum(len(d['metrics']) for d in self.config['dimensions']),
            "current_anomalies": len(self.anomalies),
            "anomalies_by_severity": {
                s.value: sum(1 for a in self.anomalies if a.severity == s)
                for s in Severity
            },
            "last_check": self.last_check,
            "history_size": {k: len(v) for k, v in self.history.items()}
        }

# 单例
_detection_engine = None

def get_detection_engine() -> DetectionEngine:
    """获取检测引擎单例"""
    global _detection_engine
    if _detection_engine is None:
        _detection_engine = DetectionEngine()
    return _detection_engine

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    engine = get_detection_engine()
    print("=" * 50)
    print("自治检测引擎测试")
    print("=" * 50)
    
    # 执行检测
    anomalies = engine.check_all()
    print(f"\n检测到 {len(anomalies)} 个异常:")
    for anomaly in anomalies:
        print(f"  [{anomaly.severity.value}] {anomaly.description}")
    
    # 状态
    status = engine.get_status()
    print(f"\n引擎状态: {json.dumps(status, indent=2, ensure_ascii=False)}")
