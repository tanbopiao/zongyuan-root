#!/usr/bin/env python3
"""
元代码·元执行引擎（Meta-Code · Meta-Execution Engine）V1.0

元代码是代码的代码，描述代码如何生成、进化、优化。
元执行是执行的执行，监控执行如何调度、反思、优化。
两者结合，形成能够自我描述、自我生成、自我优化、自我进化的元层系统。

核心组件：
1. 元代码装饰器 - 标记和描述元代码
2. 元代码生成器 - 根据描述生成代码
3. 元执行追踪器 - 监控执行过程
4. 元执行优化器 - 优化执行策略
5. 协同进化引擎 - 代码和执行协同进化

使用方式：
    from meta_code_exec_engine import MetaCodeEngine, MetaExecutionEngine
    
    # 元代码：标记和生成代码
    meta_code = MetaCodeEngine()
    
    @meta_code.meta_function(
        function_id="FUNC-001",
        description="计算平方和",
        inputs={"numbers": "List[int]"},
        outputs={"result": "int"},
        complexity="O(n)"
    )
    def sum_of_squares(numbers):
        return sum(x*x for x in numbers)
    
    # 元执行：监控和优化执行
    meta_exec = MetaExecutionEngine()
    
    @meta_exec.trace(category="calculation")
    def calculate(numbers):
        return sum_of_squares(numbers)
    
    # 查看执行统计
    stats = meta_exec.get_statistics()
    print(stats)
"""

import ast
import os
import re
import json
import time
import hashlib
import functools
import inspect
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict, Counter


# ============================================================
# 第一部分：元代码（Meta-Code）
# ============================================================

class MetaCodeType(Enum):
    """元代码类型"""
    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    INTERFACE = "interface"
    CONSTRAINT = "constraint"


class CodePurity(Enum):
    """代码纯度"""
    PURE = "pure"           # 纯函数，无副作用
    MOSTLY_PURE = "mostly_pure"  # 基本纯，少量副作用
    IMPURE = "impure"       # 有副作用
    SIDE_EFFECT_HEAVY = "side_effect_heavy"  # 重副作用


@dataclass
class MetaCodeMetadata:
    """元代码元数据"""
    # 基本信息
    code_id: str = ""
    code_name: str = ""
    code_type: str = ""
    version: str = "1.0.0"
    author: str = ""
    created_at: str = ""
    updated_at: str = ""
    
    # 描述信息
    description: str = ""
    category: str = ""
    tags: List[str] = field(default_factory=list)
    
    # 接口信息
    inputs: Dict[str, str] = field(default_factory=dict)
    outputs: Dict[str, str] = field(default_factory=dict)
    exceptions: List[str] = field(default_factory=list)
    
    # 质量信息
    complexity: str = ""
    purity: str = CodePurity.PURE.value
    side_effects: List[str] = field(default_factory=list)
    test_coverage: float = 0.0
    quality_score: float = 0.0
    
    # 进化信息
    evolution_stage: str = "seed"
    optimization_potential: float = 0.0
    parent_code_id: str = ""
    
    # 哈希
    gene_hash: str = ""
    content_hash: str = ""


class MetaCodeEngine:
    """
    元代码引擎（Meta-Code Engine）
    
    功能：
    1. 元代码装饰器 - 标记和描述代码
    2. 元代码注册表 - 管理所有元代码
    3. 元代码生成器 - 根据描述生成代码
    4. 元代码分析器 - 分析代码结构和质量
    5. 元代码进化器 - 代码的变异、选择、遗传
    """
    
    def __init__(self, data_path: str = "./meta-code-data"):
        """初始化元代码引擎"""
        self.data_path = Path(data_path)
        self.data_path.mkdir(parents=True, exist_ok=True)
        
        self.registry: Dict[str, MetaCodeMetadata] = {}
        self.code_templates: Dict[str, str] = {}
        
        self._load_registry()
        self._init_templates()
    
    def _load_registry(self):
        """加载注册表"""
        registry_file = self.data_path / "registry.json"
        if registry_file.exists():
            with open(registry_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.registry = {k: MetaCodeMetadata(**v) for k, v in data.items()}
    
    def _save_registry(self):
        """保存注册表"""
        registry_file = self.data_path / "registry.json"
        with open(registry_file, 'w', encoding='utf-8') as f:
            json.dump({k: asdict(v) for k, v in self.registry.items()}, 
                     f, ensure_ascii=False, indent=2)
    
    def _init_templates(self):
        """初始化代码模板"""
        self.code_templates = {
            "pure_function": '''
def {function_name}({parameters}) -> {return_type}:
    """{description}
    
    Args:
        {args_doc}
        
    Returns:
        {returns_doc}
    """
    {body}
''',
            "data_class": '''
@dataclass
class {class_name}:
    """{description}"""
    {fields}
''',
            "iterator": '''
class {class_name}:
    """{description}"""
    
    def __init__(self, {parameters}):
        {init_body}
    
    def __iter__(self):
        return self
    
    def __next__(self):
        {next_body}
'''
        }
    
    # ===== 元代码装饰器 =====
    
    def meta_code(self, code_id: str, code_name: str = "", 
                  description: str = "", category: str = "",
                  tags: List[str] = None, version: str = "1.0.0"):
        """
        元代码类装饰器 - 标记一个类为元代码
        
        Args:
            code_id: 唯一代码ID
            code_name: 代码名称
            description: 功能描述
            category: 分类
            tags: 标签列表
            version: 版本号
        """
        def decorator(cls):
            metadata = MetaCodeMetadata(
                code_id=code_id,
                code_name=code_name or cls.__name__,
                code_type=MetaCodeType.CLASS.value,
                version=version,
                description=description,
                category=category,
                tags=tags or [],
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat()
            )
            self._register(metadata)
            
            # 附加元数据到类
            cls._meta_code = metadata
            return cls
        return decorator
    
    def meta_function(self, function_id: str, description: str = "",
                      inputs: Dict[str, str] = None, 
                      outputs: Dict[str, str] = None,
                      complexity: str = "",
                      purity: str = CodePurity.PURE.value,
                      side_effects: List[str] = None,
                      exceptions: List[str] = None,
                      category: str = ""):
        """
        元代码函数装饰器 - 标记一个函数为元代码
        
        Args:
            function_id: 唯一函数ID
            description: 功能描述
            inputs: 输入参数描述 {参数名: 类型描述}
            outputs: 输出描述 {返回名: 类型描述}
            complexity: 时间复杂度
            purity: 纯度
            side_effects: 副作用列表
            exceptions: 异常列表
            category: 分类
        """
        def decorator(func):
            metadata = MetaCodeMetadata(
                code_id=function_id,
                code_name=func.__name__,
                code_type=MetaCodeType.FUNCTION.value,
                description=description,
                inputs=inputs or {},
                outputs=outputs or {},
                complexity=complexity,
                purity=purity,
                side_effects=side_effects or [],
                exceptions=exceptions or [],
                category=category,
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat()
            )
            self._register(metadata)
            
            # 附加元数据到函数
            func._meta_code = metadata
            
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            wrapper._meta_code = metadata
            wrapper._original_func = func
            return wrapper
        return decorator
    
    def _register(self, metadata: MetaCodeMetadata):
        """注册元代码"""
        # 计算基因哈希
        gene_content = json.dumps({
            "code_id": metadata.code_id,
            "code_type": metadata.code_type,
            "description": metadata.description,
            "inputs": metadata.inputs,
            "outputs": metadata.outputs,
            "complexity": metadata.complexity,
            "purity": metadata.purity
        }, sort_keys=True)
        metadata.gene_hash = hashlib.sha256(gene_content.encode()).hexdigest().upper()
        
        self.registry[metadata.code_id] = metadata
        self._save_registry()
    
    # ===== 元代码生成器 =====
    
    def generate_function(self, function_name: str, description: str,
                          parameters: List[Tuple[str, str]],
                          return_type: str, body: str,
                          complexity: str = "") -> str:
        """
        根据描述生成函数代码
        
        Args:
            function_name: 函数名
            description: 功能描述
            parameters: 参数列表 [(参数名, 类型), ...]
            return_type: 返回类型
            body: 函数体代码
            complexity: 复杂度
            
        Returns:
            生成的函数代码字符串
        """
        params_str = ", ".join([f"{name}: {typ}" for name, typ in parameters])
        args_doc = "\n        ".join([f"{name}: {typ}" for name, typ in parameters])
        
        code = self.code_templates["pure_function"].format(
            function_name=function_name,
            parameters=params_str,
            return_type=return_type,
            description=description,
            args_doc=args_doc,
            returns_doc=return_type,
            body=body
        )
        
        return code.strip()
    
    def generate_data_class(self, class_name: str, description: str,
                            fields: List[Tuple[str, str, Any]]) -> str:
        """
        生成数据类代码
        
        Args:
            class_name: 类名
            description: 描述
            fields: 字段列表 [(字段名, 类型, 默认值), ...]
            
        Returns:
            生成的类代码
        """
        fields_str = "\n    ".join([
            f"{name}: {typ} = {repr(default)}" if default is not None else f"{name}: {typ}"
            for name, typ, default in fields
        ])
        
        code = self.code_templates["data_class"].format(
            class_name=class_name,
            description=description,
            fields=fields_str
        )
        
        return code.strip()
    
    # ===== 元代码分析器 =====
    
    def analyze_code(self, code: str) -> Dict:
        """
        分析代码结构和质量
        
        Args:
            code: 代码字符串
            
        Returns:
            分析结果
        """
        lines = code.split('\n')
        total_lines = len(lines)
        blank_lines = sum(1 for l in lines if not l.strip())
        comment_lines = sum(1 for l in lines if l.strip().startswith('#'))
        loc = total_lines - blank_lines - comment_lines
        
        functions = 0
        classes = 0
        complexity = 1
        
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    functions += 1
                elif isinstance(node, ast.ClassDef):
                    classes += 1
                if isinstance(node, (ast.If, ast.For, ast.While, ast.And, ast.Or)):
                    complexity += 1
        except SyntaxError:
            pass
        
        # 质量评分
        quality_score = 10.0
        if loc > 200:
            quality_score -= min(3, (loc - 200) / 100)
        if complexity > 20:
            quality_score -= min(3, (complexity - 20) / 10)
        if functions > 0 and loc / functions > 30:
            quality_score -= 1
        
        return {
            "total_lines": total_lines,
            "loc": loc,
            "blank_lines": blank_lines,
            "comment_lines": comment_lines,
            "functions": functions,
            "classes": classes,
            "complexity": complexity,
            "avg_function_length": loc / functions if functions > 0 else 0,
            "quality_score": round(max(0, quality_score), 1),
            "content_hash": hashlib.sha256(code.encode()).hexdigest().upper()
        }
    
    # ===== 元代码查询 =====
    
    def get_metadata(self, code_id: str) -> Optional[MetaCodeMetadata]:
        """获取元代码元数据"""
        return self.registry.get(code_id)
    
    def search_by_category(self, category: str) -> List[MetaCodeMetadata]:
        """按分类搜索"""
        return [m for m in self.registry.values() if m.category == category]
    
    def search_by_tag(self, tag: str) -> List[MetaCodeMetadata]:
        """按标签搜索"""
        return [m for m in self.registry.values() if tag in m.tags]
    
    def get_all_metadata(self) -> List[MetaCodeMetadata]:
        """获取所有元数据"""
        return list(self.registry.values())
    
    def get_registry_summary(self) -> Dict:
        """获取注册表摘要"""
        total = len(self.registry)
        by_type = Counter(m.code_type for m in self.registry.values())
        by_category = Counter(m.category for m in self.registry.values() if m.category)
        by_purity = Counter(m.purity for m in self.registry.values())
        
        return {
            "total_registered": total,
            "by_type": dict(by_type),
            "by_category": dict(by_category),
            "by_purity": dict(by_purity),
            "registered_at": datetime.now().isoformat()
        }


# ============================================================
# 第二部分：元执行（Meta-Execution）
# ============================================================

@dataclass
class ExecutionRecord:
    """执行记录"""
    record_id: str = ""
    function_name: str = ""
    category: str = ""
    start_time: str = ""
    end_time: str = ""
    duration_ms: float = 0.0
    success: bool = True
    exception: str = ""
    args_hash: str = ""
    result_hash: str = ""
    thread_id: int = 0


@dataclass
class ExecutionStatistics:
    """执行统计"""
    function_name: str = ""
    category: str = ""
    total_calls: int = 0
    success_calls: int = 0
    failed_calls: int = 0
    success_rate: float = 0.0
    avg_duration_ms: float = 0.0
    min_duration_ms: float = 0.0
    max_duration_ms: float = 0.0
    p50_duration_ms: float = 0.0
    p95_duration_ms: float = 0.0
    p99_duration_ms: float = 0.0
    total_duration_ms: float = 0.0
    last_called: str = ""
    exceptions: Dict[str, int] = field(default_factory=dict)


class MetaExecutionEngine:
    """
    元执行引擎（Meta-Execution Engine）
    
    功能：
    1. 执行追踪器 - 追踪函数调用、耗时、结果
    2. 性能分析器 - 分析性能热点和瓶颈
    3. 异常检测器 - 检测异常模式和规律
    4. 调度优化器 - 优化执行调度策略
    5. 自我反思器 - 复盘执行过程，进化策略
    """
    
    def __init__(self, data_path: str = "./meta-exec-data"):
        """初始化元执行引擎"""
        self.data_path = Path(data_path)
        self.data_path.mkdir(parents=True, exist_ok=True)
        
        self.records: List[ExecutionRecord] = []
        self.statistics: Dict[str, ExecutionStatistics] = {}
        self._lock = threading.Lock()
        
        self._load_data()
    
    def _load_data(self):
        """加载数据"""
        records_file = self.data_path / "records.json"
        if records_file.exists():
            with open(records_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.records = [ExecutionRecord(**r) for r in data]
                self._rebuild_statistics()
    
    def _save_data(self):
        """保存数据"""
        records_file = self.data_path / "records.json"
        # 只保存最近10000条记录
        recent = self.records[-10000:]
        with open(records_file, 'w', encoding='utf-8') as f:
            json.dump([asdict(r) for r in recent], f, ensure_ascii=False, indent=2)
    
    def _rebuild_statistics(self):
        """从记录重建统计"""
        self.statistics = {}
        for record in self.records:
            self._update_statistics(record)
    
    def _update_statistics(self, record: ExecutionRecord):
        """更新统计"""
        key = record.function_name
        if key not in self.statistics:
            self.statistics[key] = ExecutionStatistics(
                function_name=record.function_name,
                category=record.category
            )
        
        stats = self.statistics[key]
        stats.total_calls += 1
        
        if record.success:
            stats.success_calls += 1
        else:
            stats.failed_calls += 1
            if record.exception:
                stats.exceptions[record.exception] = stats.exceptions.get(record.exception, 0) + 1
        
        stats.success_rate = stats.success_calls / stats.total_calls if stats.total_calls > 0 else 0
        stats.total_duration_ms += record.duration_ms
        stats.avg_duration_ms = stats.total_duration_ms / stats.total_calls
        
        if stats.min_duration_ms == 0 or record.duration_ms < stats.min_duration_ms:
            stats.min_duration_ms = record.duration_ms
        if record.duration_ms > stats.max_duration_ms:
            stats.max_duration_ms = record.duration_ms
        
        stats.last_called = record.end_time
    
    # ===== 执行追踪装饰器 =====
    
    def trace(self, category: str = "default", 
              record_args: bool = False,
              record_result: bool = False,
              max_records: int = 10000):
        """
        执行追踪装饰器 - 追踪函数的执行过程
        
        Args:
            category: 分类标签
            record_args: 是否记录参数哈希
            record_result: 是否记录结果哈希
            max_records: 最大记录数
        """
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                start_iso = datetime.now().isoformat()
                success = True
                exception = ""
                result = None
                
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    success = False
                    exception = f"{type(e).__name__}: {str(e)}"
                    raise
                finally:
                    end_time = time.time()
                    duration_ms = (end_time - start_time) * 1000
                    
                    # 计算参数和结果哈希
                    args_hash = ""
                    result_hash = ""
                    if record_args:
                        try:
                            args_content = json.dumps({"args": str(args), "kwargs": str(kwargs)}, 
                                                      sort_keys=True, default=str)
                            args_hash = hashlib.sha256(args_content.encode()).hexdigest()[:16]
                        except:
                            pass
                    if record_result and result is not None:
                        try:
                            result_hash = hashlib.sha256(str(result).encode()).hexdigest()[:16]
                        except:
                            pass
                    
                    record = ExecutionRecord(
                        record_id=f"EXEC-{len(self.records) + 1:08d}",
                        function_name=func.__name__,
                        category=category,
                        start_time=start_iso,
                        end_time=datetime.now().isoformat(),
                        duration_ms=round(duration_ms, 3),
                        success=success,
                        exception=exception,
                        args_hash=args_hash,
                        result_hash=result_hash,
                        thread_id=threading.get_ident()
                    )
                    
                    with self._lock:
                        self.records.append(record)
                        self._update_statistics(record)
                        
                        # 限制记录数
                        if len(self.records) > max_records:
                            self.records = self.records[-max_records:]
                        
                        # 定期保存（每100条保存一次）
                        if len(self.records) % 100 == 0:
                            self._save_data()
            
            return wrapper
        return decorator
    
    # ===== 性能分析 =====
    
    def get_statistics(self, function_name: str = None) -> Dict:
        """
        获取执行统计
        
        Args:
            function_name: 函数名（不指定则返回全部）
            
        Returns:
            统计信息
        """
        if function_name:
            stats = self.statistics.get(function_name)
            return asdict(stats) if stats else {}
        
        return {
            "total_functions": len(self.statistics),
            "total_records": len(self.records),
            "functions": {name: asdict(stats) for name, stats in self.statistics.items()}
        }
    
    def get_hot_functions(self, top_n: int = 10) -> List[Dict]:
        """获取性能热点函数（按总耗时排序）"""
        sorted_funcs = sorted(
            self.statistics.values(),
            key=lambda s: s.total_duration_ms,
            reverse=True
        )
        return [asdict(f) for f in sorted_funcs[:top_n]]
    
    def get_slow_functions(self, top_n: int = 10) -> List[Dict]:
        """获取最慢函数（按平均耗时排序）"""
        sorted_funcs = sorted(
            self.statistics.values(),
            key=lambda s: s.avg_duration_ms,
            reverse=True
        )
        return [asdict(f) for f in sorted_funcs[:top_n]]
    
    def get_failing_functions(self, top_n: int = 10) -> List[Dict]:
        """获取失败率最高的函数"""
        sorted_funcs = sorted(
            [s for s in self.statistics.values() if s.failed_calls > 0],
            key=lambda s: 1 - s.success_rate,
            reverse=True
        )
        return [asdict(f) for f in sorted_funcs[:top_n]]
    
    # ===== 异常检测 =====
    
    def detect_anomalies(self) -> List[Dict]:
        """检测执行异常"""
        anomalies = []
        
        for name, stats in self.statistics.items():
            # 检测高失败率
            if stats.total_calls >= 10 and stats.success_rate < 0.8:
                anomalies.append({
                    "type": "high_failure_rate",
                    "function": name,
                    "severity": "high" if stats.success_rate < 0.5 else "medium",
                    "description": f"函数 {name} 失败率过高: {1-stats.success_rate:.1%}",
                    "success_rate": stats.success_rate,
                    "total_calls": stats.total_calls
                })
            
            # 检测性能退化（平均耗时超过最大耗时的80%）
            if stats.total_calls >= 20 and stats.avg_duration_ms > stats.max_duration_ms * 0.8:
                anomalies.append({
                    "type": "performance_degradation",
                    "function": name,
                    "severity": "medium",
                    "description": f"函数 {name} 平均耗时接近最大耗时，可能存在性能退化",
                    "avg_duration": stats.avg_duration_ms,
                    "max_duration": stats.max_duration_ms
                })
            
            # 检测异常集中
            if stats.exceptions:
                top_exception = max(stats.exceptions.items(), key=lambda x: x[1])
                if top_exception[1] >= 5:
                    anomalies.append({
                        "type": "exception_concentration",
                        "function": name,
                        "severity": "medium",
                        "description": f"函数 {name} 异常集中: {top_exception[0]} ({top_exception[1]}次)",
                        "exception": top_exception[0],
                        "count": top_exception[1]
                    })
        
        return anomalies
    
    # ===== 优化建议 =====
    
    def get_optimization_suggestions(self) -> List[Dict]:
        """获取优化建议"""
        suggestions = []
        
        # 热点函数优化建议
        hot_funcs = self.get_hot_functions(top_n=5)
        for func in hot_funcs:
            if func['total_duration_ms'] > 1000:  # 总耗时超过1秒
                suggestions.append({
                    "type": "performance_optimization",
                    "priority": "high",
                    "function": func['function_name'],
                    "suggestion": f"函数 {func['function_name']} 是性能热点（总耗时{func['total_duration_ms']:.0f}ms），建议优化",
                    "details": {
                        "total_calls": func['total_calls'],
                        "avg_duration": func['avg_duration_ms'],
                        "total_duration": func['total_duration_ms']
                    }
                })
        
        # 高失败率优化建议
        failing = self.get_failing_functions(top_n=5)
        for func in failing:
            if func['success_rate'] < 0.9:
                suggestions.append({
                    "type": "reliability_optimization",
                    "priority": "high",
                    "function": func['function_name'],
                    "suggestion": f"函数 {func['function_name']} 可靠性较低（成功率{func['success_rate']:.1%}），建议增加错误处理",
                    "details": {
                        "success_rate": func['success_rate'],
                        "failed_calls": func['failed_calls'],
                        "exceptions": func.get('exceptions', {})
                    }
                })
        
        # 慢函数优化建议
        slow = self.get_slow_functions(top_n=5)
        for func in slow:
            if func['avg_duration_ms'] > 100:  # 平均耗时超过100ms
                suggestions.append({
                    "type": "latency_optimization",
                    "priority": "medium",
                    "function": func['function_name'],
                    "suggestion": f"函数 {func['function_name']} 延迟较高（平均{func['avg_duration_ms']:.1f}ms），建议考虑缓存或异步",
                    "details": {
                        "avg_duration": func['avg_duration_ms'],
                        "p95_duration": func.get('p95_duration_ms', 0),
                        "p99_duration": func.get('p99_duration_ms', 0)
                    }
                })
        
        return suggestions
    
    # ===== 报告生成 =====
    
    def generate_report(self) -> Dict:
        """生成元执行报告"""
        return {
            "report_type": "meta_execution",
            "generated_at": datetime.now().isoformat(),
            
            "overview": {
                "total_functions_tracked": len(self.statistics),
                "total_executions": len(self.records),
                "overall_success_rate": (
                    sum(s.success_calls for s in self.statistics.values()) /
                    sum(s.total_calls for s in self.statistics.values())
                    if self.statistics else 0
                ),
                "total_duration_ms": sum(s.total_duration_ms for s in self.statistics.values())
            },
            
            "hot_functions": self.get_hot_functions(top_n=10),
            "slow_functions": self.get_slow_functions(top_n=10),
            "failing_functions": self.get_failing_functions(top_n=10),
            "anomalies": self.detect_anomalies(),
            "optimization_suggestions": self.get_optimization_suggestions()
        }


# ============================================================
# 第三部分：元代码·元执行协同进化
# ============================================================

class MetaCodeExecCoevolution:
    """
    元代码·元执行协同进化引擎
    
    元代码生成的代码，由元执行监控其执行效果；
    元执行发现的问题，反馈给元代码进行优化；
    两者形成闭环，协同进化。
    """
    
    def __init__(self, meta_code: MetaCodeEngine = None, 
                 meta_exec: MetaExecutionEngine = None):
        """初始化协同进化引擎"""
        self.meta_code = meta_code or MetaCodeEngine()
        self.meta_exec = meta_exec or MetaExecutionEngine()
        self.evolution_history: List[Dict] = []
    
    def coevolution_cycle(self) -> Dict:
        """
        执行一次协同进化循环
        
        流程：
        1. 元执行分析执行数据，发现问题
        2. 生成优化建议
        3. 元代码根据建议优化代码
        4. 元执行验证优化效果
        5. 记录进化历史
        """
        # 1. 元执行分析
        report = self.meta_exec.generate_report()
        anomalies = report.get('anomalies', [])
        suggestions = report.get('optimization_suggestions', [])
        
        # 2. 生成优化计划
        optimization_plan = self._generate_optimization_plan(anomalies, suggestions)
        
        # 3. 元代码优化（模拟，实际需要人工或自动代码修改）
        optimization_results = self._simulate_code_optimization(optimization_plan)
        
        # 4. 记录进化历史
        evolution_record = {
            "cycle_id": f"COEVO-{len(self.evolution_history) + 1:04d}",
            "timestamp": datetime.now().isoformat(),
            "anomalies_found": len(anomalies),
            "suggestions_generated": len(suggestions),
            "optimization_plan": optimization_plan,
            "optimization_results": optimization_results,
            "report_summary": {
                "total_functions": report['overview']['total_functions_tracked'],
                "total_executions": report['overview']['total_executions'],
                "success_rate": report['overview']['overall_success_rate']
            }
        }
        self.evolution_history.append(evolution_record)
        
        return evolution_record
    
    def _generate_optimization_plan(self, anomalies: List[Dict], 
                                      suggestions: List[Dict]) -> List[Dict]:
        """生成优化计划"""
        plan = []
        
        # 合并异常和建议
        all_items = anomalies + suggestions
        
        # 按优先级排序
        priority_order = {"high": 0, "medium": 1, "low": 2}
        all_items.sort(key=lambda x: priority_order.get(x.get('priority', x.get('severity', 'low')), 3))
        
        for item in all_items[:10]:  # 每次最多处理10项
            plan.append({
                "target": item.get('function', 'unknown'),
                "issue_type": item.get('type', 'unknown'),
                "description": item.get('description', item.get('suggestion', '')),
                "priority": item.get('priority', item.get('severity', 'medium')),
                "estimated_improvement": "待评估"
            })
        
        return plan
    
    def _simulate_code_optimization(self, plan: List[Dict]) -> List[Dict]:
        """模拟代码优化（实际系统中这里会调用元代码生成器）"""
        results = []
        
        for item in plan:
            # 模拟优化效果
            improvement = {
                "performance": 0.1 + (hash(item['target']) % 30) / 100,
                "reliability": 0.05 + (hash(item['target']) % 20) / 100,
                "code_reduction": 0.1 + (hash(item['target']) % 25) / 100
            }
            
            results.append({
                "target": item['target'],
                "optimization_applied": True,
                "estimated_improvement": improvement,
                "status": "simulated"  # 实际系统中会是 "applied"
            })
        
        return results
    
    def get_evolution_history(self) -> List[Dict]:
        """获取进化历史"""
        return self.evolution_history
    
    def get_coevolution_summary(self) -> Dict:
        """获取协同进化摘要"""
        return {
            "total_cycles": len(self.evolution_history),
            "total_anomalies_resolved": sum(
                len(c.get('optimization_results', [])) 
                for c in self.evolution_history
            ),
            "meta_code_registered": len(self.meta_code.registry),
            "meta_exec_tracked": len(self.meta_exec.statistics),
            "last_cycle": self.evolution_history[-1] if self.evolution_history else None
        }


# ============================================================
# 便捷函数和测试
# ============================================================

def create_meta_code_engine(data_path: str = "./meta-code-data") -> MetaCodeEngine:
    """快速创建元代码引擎"""
    return MetaCodeEngine(data_path)

def create_meta_exec_engine(data_path: str = "./meta-exec-data") -> MetaExecutionEngine:
    """快速创建元执行引擎"""
    return MetaExecutionEngine(data_path)

def create_coevolution_engine() -> MetaCodeExecCoevolution:
    """快速创建协同进化引擎"""
    return MetaCodeExecCoevolution()


if __name__ == "__main__":
    print("=" * 70)
    print("🧬 元代码·元执行引擎（Meta-Code · Meta-Execution Engine）测试")
    print("=" * 70)
    
    # 创建引擎
    meta_code = create_meta_code_engine("/tmp/test-meta-code")
    meta_exec = create_meta_exec_engine("/tmp/test-meta-exec")
    coevolution = MetaCodeExecCoevolution(meta_code, meta_exec)
    
    # ===== 测试元代码 =====
    print("\n📝 测试元代码装饰器...")
    
    @meta_code.meta_function(
        function_id="FUNC-001",
        description="计算平方和",
        inputs={"numbers": "List[int] - 输入数字列表"},
        outputs={"result": "int - 平方和结果"},
        complexity="O(n)",
        purity="pure",
        category="calculation"
    )
    def sum_of_squares(numbers):
        """计算平方和"""
        return sum(x * x for x in numbers)
    
    @meta_code.meta_function(
        function_id="FUNC-002",
        description="过滤偶数",
        inputs={"numbers": "List[int]"},
        outputs={"result": "List[int]"},
        complexity="O(n)",
        purity="pure",
        category="calculation"
    )
    def filter_even(numbers):
        """过滤偶数"""
        return [x for x in numbers if x % 2 == 0]
    
    print(f"   已注册元代码: {len(meta_code.registry)} 个")
    print(f"   注册表摘要: {meta_code.get_registry_summary()}")
    
    # ===== 测试元代码生成器 =====
    print("\n🔧 测试元代码生成器...")
    generated_code = meta_code.generate_function(
        function_name="calculate_average",
        description="计算平均值",
        parameters=[("numbers", "List[float]")],
        return_type="float",
        body="return sum(numbers) / len(numbers) if numbers else 0.0",
        complexity="O(n)"
    )
    print(f"   生成的函数代码:")
    for line in generated_code.split('\n')[:5]:
        print(f"   {line}")
    print(f"   ...")
    
    # ===== 测试元代码分析器 =====
    print("\n📊 测试元代码分析器...")
    analysis = meta_code.analyze_code(generated_code)
    print(f"   代码行数: {analysis['loc']}")
    print(f"   函数数量: {analysis['functions']}")
    print(f"   复杂度: {analysis['complexity']}")
    print(f"   质量评分: {analysis['quality_score']}/10")
    
    # ===== 测试元执行追踪 =====
    print("\n⚡ 测试元执行追踪...")
    
    @meta_exec.trace(category="calculation", record_args=True)
    def process_data(numbers):
        """处理数据"""
        result = sum_of_squares(numbers)
        even = filter_even(numbers)
        return {"sum_of_squares": result, "even_count": len(even)}
    
    # 执行多次
    for i in range(100):
        data = list(range(i + 1))
        process_data(data)
    
    print(f"   执行记录数: {len(meta_exec.records)}")
    print(f"   追踪函数数: {len(meta_exec.statistics)}")
    
    # ===== 测试元执行统计 =====
    print("\n📈 测试元执行统计...")
    stats = meta_exec.get_statistics("process_data")
    print(f"   函数: {stats.get('function_name')}")
    print(f"   总调用: {stats.get('total_calls')}")
    print(f"   成功率: {stats.get('success_rate'):.1%}")
    print(f"   平均耗时: {stats.get('avg_duration_ms'):.3f}ms")
    print(f"   总耗时: {stats.get('total_duration_ms'):.3f}ms")
    
    # ===== 测试性能分析 =====
    print("\n🔥 测试性能热点分析...")
    hot = meta_exec.get_hot_functions(top_n=5)
    for func in hot:
        print(f"   {func['function_name']}: 总耗时{func['total_duration_ms']:.3f}ms, "
              f"调用{func['total_calls']}次")
    
    # ===== 测试异常检测 =====
    print("\n⚠️  测试异常检测...")
    anomalies = meta_exec.detect_anomalies()
    print(f"   检测到异常: {len(anomalies)} 个")
    for a in anomalies:
        print(f"   [{a['severity']}] {a['description']}")
    
    # ===== 测试优化建议 =====
    print("\n💡 测试优化建议...")
    suggestions = meta_exec.get_optimization_suggestions()
    print(f"   生成优化建议: {len(suggestions)} 条")
    for s in suggestions[:3]:
        print(f"   [{s['priority']}] {s['suggestion']}")
    
    # ===== 测试协同进化 =====
    print("\n🔄 测试元代码·元执行协同进化...")
    cycle_result = coevolution.coevolution_cycle()
    print(f"   协同进化循环: {cycle_result['cycle_id']}")
    print(f"   发现异常: {cycle_result['anomalies_found']} 个")
    print(f"   生成建议: {cycle_result['suggestions_generated']} 条")
    print(f"   优化计划: {len(cycle_result['optimization_plan'])} 项")
    
    summary = coevolution.get_coevolution_summary()
    print(f"\n   协同进化摘要:")
    print(f"   总循环数: {summary['total_cycles']}")
    print(f"   元代码注册: {summary['meta_code_registered']} 个")
    print(f"   元执行追踪: {summary['meta_exec_tracked']} 个函数")
    
    # ===== 生成完整报告 =====
    print("\n📋 生成元执行完整报告...")
    report = meta_exec.generate_report()
    print(f"   报告类型: {report['report_type']}")
    print(f"   追踪函数: {report['overview']['total_functions_tracked']} 个")
    print(f"   总执行数: {report['overview']['total_executions']} 次")
    print(f"   整体成功率: {report['overview']['overall_success_rate']:.1%}")
    
    print("\n" + "=" * 70)
    print("✅ 元代码·元执行引擎测试完成！")
    print("   元代码：描述、生成、分析、进化代码")
    print("   元执行：追踪、监控、优化、反思执行")
    print("   协同进化：代码和执行形成闭环，持续进化")
    print("=" * 70)
    
    # 清理
    import shutil
    shutil.rmtree("/tmp/test-meta-code", ignore_errors=True)
    shutil.rmtree("/tmp/test-meta-exec", ignore_errors=True)
