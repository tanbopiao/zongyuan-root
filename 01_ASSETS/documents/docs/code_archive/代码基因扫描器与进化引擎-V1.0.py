#!/usr/bin/env python3
"""
代码基因扫描器与代码进化引擎 - Code Gene Scanner & Evolution Engine
实现代码载体的结构化优化和持续进化。

核心理念：
- 代码不是静态的文本，而是有生命的载体
- 同一个功能，可以用100行实现，也可以用50行实现，甚至10行实现
- 代码量不是固定的，而是可以不断优化、不断进化的
- 这就是代码载体的结构化优化——在功能不变的前提下，持续优化代码结构

功能：
1. 代码基因扫描 - 提取代码的基因特征（行数、复杂度、质量评分等）
2. 优化机会识别 - 识别代码量瓶颈、复杂度瓶颈、重复代码等
3. 代码进化日志 - 记录每次优化的完整历史，链式继承不可篡改
4. 代码基因图谱 - 建立所有代码模块的基因图谱
5. 优化建议生成 - 基于代码基因生成具体的优化建议
6. 进化效果度量 - 度量每次优化的效果（代码量减少、性能提升等）

使用方式：
    from code_gene_engine import CodeGeneEngine
    
    engine = CodeGeneEngine(data_path="./code-evolution")
    
    # 扫描代码
    gene = engine.scan_file("./my_module.py")
    
    # 识别优化机会
    opportunities = engine.identify_optimization_opportunities(gene)
    
    # 记录进化
    log = engine.record_evolution(
        module_id="my-module-001",
        before_gene=old_gene,
        after_gene=new_gene,
        optimization_type="structure",
        description="提取重复代码为公共函数"
    )
    
    # 获取进化报告
    report = engine.get_evolution_report()
"""

import ast
import os
import re
import json
import hashlib
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict, Counter


class CodeEvolutionStage(Enum):
    """代码进化阶段"""
    RAW = "raw"               # L0 原始代码 - 能跑就行
    NORMALIZED = "normalized" # L1 规范化代码 - 有基本规范
    OPTIMIZED = "optimized"   # L2 优化代码 - 经过第一轮优化
    REFINED = "refined"       # L3 精炼代码 - 深度优化
    EXTREME = "extreme"       # L4 极致代码 - 近乎完美
    GENETIC = "genetic"       # L5 基因代码 - 可遗传可变异


class OptimizationType(Enum):
    """优化类型"""
    STRUCTURE = "structure"       # 结构优化 - 提取重复、拆分函数、合并模块
    ALGORITHM = "algorithm"       # 算法优化 - 更高效的算法、缓存、批量处理
    SYNTAX = "syntax"             # 语法优化 - 语言特性、列表推导式、装饰器
    DEPENDENCY = "dependency"     # 依赖优化 - 减少第三方依赖、使用标准库
    DATA_STRUCTURE = "data_structure"  # 数据结构优化 - 更合适的数据结构
    NAMING = "naming"             # 命名优化 - 更清晰的变量和函数命名
    COMMENT = "comment"           # 注释优化 - 更精准的注释
    TEST = "test"                 # 测试优化 - 提升测试覆盖率和质量


@dataclass
class CodeGene:
    """代码基因 - 决定代码模块的本质特征"""
    
    # 基本信息
    module_id: str = ""
    module_name: str = ""
    file_path: str = ""
    language: str = "python"
    function_description: str = ""
    
    # 结构基因
    lines_of_code: int = 0           # 代码行数（不含空行和注释）
    total_lines: int = 0              # 总行数
    blank_lines: int = 0              # 空行数
    comment_lines: int = 0            # 注释行数
    functions_count: int = 0          # 函数数量
    classes_count: int = 0            # 类数量
    methods_count: int = 0            # 方法数量
    imports_count: int = 0            # 导入数量
    cyclomatic_complexity: int = 0    # 圈复杂度
    avg_function_length: float = 0.0  # 平均函数长度
    max_function_length: int = 0       # 最大函数长度
    max_nesting_depth: int = 0         # 最大嵌套深度
    
    # 质量基因
    readability_score: float = 0.0     # 可读性评分(0-10)
    maintainability_score: float = 0.0  # 可维护性评分(0-10)
    test_coverage: float = 0.0          # 测试覆盖率(0-1)
    duplication_rate: float = 0.0       # 重复率(0-1)
    docstring_coverage: float = 0.0     # 文档字符串覆盖率(0-1)
    
    # 进化基因
    evolution_stage: str = CodeEvolutionStage.RAW.value  # 进化阶段
    optimization_potential: float = 0.0  # 优化潜力(0-1)
    last_optimized: str = ""              # 上次优化时间
    optimization_count: int = 0           # 优化次数
    total_loc_reduction: float = 0.0      # 累计代码量减少比例
    
    # 哈希基因（用于追溯和确权）
    gene_hash: str = ""
    parent_gene_hash: str = ""
    content_hash: str = ""
    
    # 时间戳
    scanned_at: str = ""
    
    def calculate_gene_hash(self) -> str:
        """计算基因哈希"""
        content = json.dumps({
            "module_id": self.module_id,
            "lines_of_code": self.lines_of_code,
            "functions_count": self.functions_count,
            "classes_count": self.classes_count,
            "cyclomatic_complexity": self.cyclomatic_complexity,
            "readability_score": self.readability_score,
            "maintainability_score": self.maintainability_score,
            "evolution_stage": self.evolution_stage,
            "scanned_at": self.scanned_at
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest().upper()


@dataclass
class OptimizationOpportunity:
    """优化机会"""
    opportunity_id: str = ""
    module_id: str = ""
    module_name: str = ""
    optimization_type: str = ""
    severity: str = ""  # low/medium/high/critical
    title: str = ""
    description: str = ""
    location: str = ""  # 行号或函数名
    current_metric: float = 0.0
    target_metric: float = 0.0
    estimated_improvement: float = 0.0  # 预计改进比例
    priority: int = 0  # 优先级，数字越小越优先


@dataclass
class CodeEvolutionLog:
    """代码进化日志 - 记录代码的每一次优化和进化"""
    
    # 基本信息
    log_id: str = ""
    module_id: str = ""
    module_name: str = ""
    timestamp: str = ""
    
    # 优化前状态
    before_loc: int = 0
    before_complexity: int = 0
    before_readability: float = 0.0
    before_maintainability: float = 0.0
    
    # 优化后状态
    after_loc: int = 0
    after_complexity: int = 0
    after_readability: float = 0.0
    after_maintainability: float = 0.0
    
    # 优化效果
    loc_reduction: float = 0.0        # 代码量减少比例
    complexity_reduction: float = 0.0  # 复杂度减少比例
    readability_improvement: float = 0.0  # 可读性提升
    maintainability_improvement: float = 0.0  # 可维护性提升
    
    # 优化详情
    optimization_type: str = ""
    optimization_description: str = ""
    techniques_used: List[str] = field(default_factory=list)
    
    # 验证信息
    tests_passed: bool = True
    test_coverage_before: float = 0.0
    test_coverage_after: float = 0.0
    
    # 哈希和追溯
    log_hash: str = ""
    parent_log_hash: str = ""
    before_gene_hash: str = ""
    after_gene_hash: str = ""


class CodeGeneEngine:
    """
    代码基因扫描器与代码进化引擎
    
    实现代码载体的结构化优化和持续进化。
    """
    
    VERSION = "1.0.0"
    ENGINE_ID = "CODE-GENE-ENGINE-V1"
    
    # 代码量基准表（根据功能类型）
    LOC_BENCHMARKS = {
        "simple_function": {"base": 35, "good": 15, "extreme": 8},
        "complex_function": {"base": 100, "good": 55, "extreme": 25},
        "data_class": {"base": 75, "good": 45, "extreme": 20},
        "business_class": {"base": 275, "good": 140, "extreme": 70},
        "api_layer": {"base": 200, "good": 100, "extreme": 45},
        "algorithm_module": {"base": 300, "good": 125, "extreme": 45},
        "complete_module": {"base": 1250, "good": 650, "extreme": 250},
    }
    
    def __init__(self, data_path: str = "./code-evolution"):
        """
        初始化代码基因引擎
        
        Args:
            data_path: 进化数据存储路径
        """
        self.data_path = Path(data_path)
        self.data_path.mkdir(parents=True, exist_ok=True)
        
        # 数据文件
        self.genes_file = self.data_path / "code_genes.json"
        self.logs_file = self.data_path / "evolution_logs.json"
        self.opportunities_file = self.data_path / "optimization_opportunities.json"
        self.config_file = self.data_path / "config.json"
        
        # 加载状态
        self.code_genes: Dict[str, CodeGene] = {}
        self.evolution_logs: List[CodeEvolutionLog] = []
        self.opportunities: List[OptimizationOpportunity] = []
        self.config = {}
        
        self._load_state()
        self._init_config()
    
    def _load_state(self):
        """加载状态"""
        if self.genes_file.exists():
            with open(self.genes_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.code_genes = {k: CodeGene(**v) for k, v in data.items()}
        
        if self.logs_file.exists():
            with open(self.logs_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.evolution_logs = [CodeEvolutionLog(**log) for log in data]
        
        if self.opportunities_file.exists():
            with open(self.opportunities_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.opportunities = [OptimizationOpportunity(**opp) for opp in data]
        
        if self.config_file.exists():
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
    
    def _save_state(self):
        """保存状态"""
        with open(self.genes_file, 'w', encoding='utf-8') as f:
            json.dump({k: asdict(v) for k, v in self.code_genes.items()}, f, ensure_ascii=False, indent=2)
        
        with open(self.logs_file, 'w', encoding='utf-8') as f:
            json.dump([asdict(log) for log in self.evolution_logs], f, ensure_ascii=False, indent=2)
        
        with open(self.opportunities_file, 'w', encoding='utf-8') as f:
            json.dump([asdict(opp) for opp in self.opportunities], f, ensure_ascii=False, indent=2)
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)
    
    def _init_config(self):
        """初始化配置"""
        if not self.config:
            self.config = {
                "engine_version": self.VERSION,
                "created_at": datetime.now().isoformat(),
                "scanning_rules": {
                    "min_function_length": 3,
                    "max_function_length": 50,
                    "max_nesting_depth": 4,
                    "max_cyclomatic_complexity": 15,
                    "min_docstring_coverage": 0.5
                },
                "optimization_targets": {
                    "loc_reduction_per_optimization": 0.1,  # 每次优化至少减少10%代码量
                    "target_evolution_stage": CodeEvolutionStage.REFINED.value
                },
                "total_modules_scanned": 0,
                "total_optimizations": 0
            }
            self._save_state()
    
    def scan_file(self, file_path: str, module_id: str = None, 
                  module_name: str = None) -> CodeGene:
        """
        扫描单个文件，提取代码基因
        
        Args:
            file_path: 文件路径
            module_id: 模块ID（不指定则自动生成）
            module_name: 模块名称（不指定则用文件名）
            
        Returns:
            CodeGene 代码基因
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
        
        # 基本统计
        total_lines = len(lines)
        blank_lines = sum(1 for line in lines if not line.strip())
        comment_lines = sum(1 for line in lines if line.strip().startswith('#'))
        code_lines = total_lines - blank_lines - comment_lines
        
        # 解析AST
        functions_count = 0
        classes_count = 0
        methods_count = 0
        imports_count = 0
        cyclomatic_complexity = 1  # 基础复杂度为1
        max_nesting_depth = 0
        function_lengths = []
        docstring_count = 0
        total_definitions = 0
        
        try:
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    functions_count += 1
                    total_definitions += 1
                    # 计算函数长度
                    if hasattr(node, 'end_lineno') and hasattr(node, 'lineno'):
                        func_len = node.end_lineno - node.lineno + 1
                        function_lengths.append(func_len)
                    # 检查文档字符串
                    if (node.body and isinstance(node.body[0], ast.Expr) and 
                        isinstance(node.body[0].value, ast.Constant) and 
                        isinstance(node.body[0].value.value, str)):
                        docstring_count += 1
                    # 计算圈复杂度
                    cyclomatic_complexity += self._calculate_node_complexity(node)
                    # 计算嵌套深度
                    depth = self._calculate_nesting_depth(node)
                    max_nesting_depth = max(max_nesting_depth, depth)
                
                elif isinstance(node, ast.ClassDef):
                    classes_count += 1
                    total_definitions += 1
                    if (node.body and isinstance(node.body[0], ast.Expr) and 
                        isinstance(node.body[0].value, ast.Constant) and 
                        isinstance(node.body[0].value.value, str)):
                        docstring_count += 1
                    # 统计方法
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            methods_count += 1
                
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    imports_count += 1
            
            # 顶层复杂度
            for node in tree.body:
                cyclomatic_complexity += self._calculate_node_complexity(node)
                
        except SyntaxError:
            # 语法错误时使用简单估算
            cyclomatic_complexity = code_lines // 10 + 1
            max_nesting_depth = 4
        
        # 计算平均和最大函数长度
        avg_function_length = sum(function_lengths) / len(function_lengths) if function_lengths else 0
        max_function_length = max(function_lengths) if function_lengths else 0
        
        # 计算质量评分
        readability_score = self._calculate_readability_score(
            code_lines, functions_count, avg_function_length, 
            max_nesting_depth, comment_lines, total_lines
        )
        
        maintainability_score = self._calculate_maintainability_score(
            code_lines, cyclomatic_complexity, functions_count,
            classes_count, readability_score
        )
        
        docstring_coverage = docstring_count / total_definitions if total_definitions else 0
        
        # 计算优化潜力
        optimization_potential = self._calculate_optimization_potential(
            code_lines, cyclomatic_complexity, max_function_length,
            max_nesting_depth, readability_score, maintainability_score
        )
        
        # 确定进化阶段
        evolution_stage = self._determine_evolution_stage(
            code_lines, readability_score, maintainability_score, 
            optimization_potential, function_lengths
        )
        
        # 生成模块ID和名称
        if module_id is None:
            module_id = f"module-{hashlib.md5(str(file_path).encode()).hexdigest()[:8]}"
        if module_name is None:
            module_name = file_path.stem
        
        # 计算内容哈希
        content_hash = hashlib.sha256(content.encode()).hexdigest().upper()
        
        # 创建代码基因
        gene = CodeGene(
            module_id=module_id,
            module_name=module_name,
            file_path=str(file_path),
            language="python",
            function_description="",
            
            # 结构基因
            lines_of_code=code_lines,
            total_lines=total_lines,
            blank_lines=blank_lines,
            comment_lines=comment_lines,
            functions_count=functions_count,
            classes_count=classes_count,
            methods_count=methods_count,
            imports_count=imports_count,
            cyclomatic_complexity=cyclomatic_complexity,
            avg_function_length=round(avg_function_length, 1),
            max_function_length=max_function_length,
            max_nesting_depth=max_nesting_depth,
            
            # 质量基因
            readability_score=round(readability_score, 1),
            maintainability_score=round(maintainability_score, 1),
            test_coverage=0.0,
            duplication_rate=0.0,
            docstring_coverage=round(docstring_coverage, 2),
            
            # 进化基因
            evolution_stage=evolution_stage,
            optimization_potential=round(optimization_potential, 2),
            last_optimized="",
            optimization_count=0,
            total_loc_reduction=0.0,
            
            # 哈希
            gene_hash="",
            parent_gene_hash=self.code_genes.get(module_id, CodeGene()).gene_hash,
            content_hash=content_hash,
            
            scanned_at=datetime.now().isoformat()
        )
        
        gene.gene_hash = gene.calculate_gene_hash()
        
        # 保存基因
        self.code_genes[module_id] = gene
        self.config["total_modules_scanned"] = self.config.get("total_modules_scanned", 0) + 1
        self._save_state()
        
        return gene
    
    def scan_directory(self, dir_path: str, pattern: str = "*.py",
                       recursive: bool = True) -> List[CodeGene]:
        """
        扫描目录中的所有代码文件
        
        Args:
            dir_path: 目录路径
            pattern: 文件匹配模式
            recursive: 是否递归扫描
            
        Returns:
            代码基因列表
        """
        dir_path = Path(dir_path)
        genes = []
        
        if recursive:
            files = list(dir_path.rglob(pattern))
        else:
            files = list(dir_path.glob(pattern))
        
        for file_path in files:
            if file_path.is_file():
                try:
                    gene = self.scan_file(str(file_path))
                    genes.append(gene)
                except Exception as e:
                    print(f"扫描文件失败 {file_path}: {e}")
        
        return genes
    
    def identify_optimization_opportunities(self, gene: CodeGene) -> List[OptimizationOpportunity]:
        """
        识别代码优化机会
        
        Args:
            gene: 代码基因
            
        Returns:
            优化机会列表
        """
        opportunities = []
        opp_id_counter = 0
        
        def add_opportunity(opt_type, severity, title, description, 
                           location, current, target, improvement, priority):
            nonlocal opp_id_counter
            opp_id_counter += 1
            opp = OptimizationOpportunity(
                opportunity_id=f"OPP-{gene.module_id}-{opp_id_counter:03d}",
                module_id=gene.module_id,
                module_name=gene.module_name,
                optimization_type=opt_type,
                severity=severity,
                title=title,
                description=description,
                location=location,
                current_metric=current,
                target_metric=target,
                estimated_improvement=improvement,
                priority=priority
            )
            opportunities.append(opp)
        
        # 1. 函数过长
        if gene.max_function_length > 50:
            add_opportunity(
                opt_type=OptimizationType.STRUCTURE.value,
                severity="high" if gene.max_function_length > 100 else "medium",
                title=f"函数过长: {gene.max_function_length}行",
                description=f"存在超过50行的函数，建议拆分为多个小函数，每个函数单一职责",
                location=f"最大函数 {gene.max_function_length}行",
                current=gene.max_function_length,
                target=50,
                improvement=(gene.max_function_length - 50) / gene.max_function_length,
                priority=1
            )
        
        # 2. 圈复杂度过高
        if gene.cyclomatic_complexity > 15:
            add_opportunity(
                opt_type=OptimizationType.STRUCTURE.value,
                severity="high" if gene.cyclomatic_complexity > 25 else "medium",
                title=f"圈复杂度过高: {gene.cyclomatic_complexity}",
                description=f"圈复杂度超过15，建议简化逻辑、提取条件、使用早返回",
                location="全局",
                current=gene.cyclomatic_complexity,
                target=15,
                improvement=(gene.cyclomatic_complexity - 15) / gene.cyclomatic_complexity,
                priority=2
            )
        
        # 3. 嵌套过深
        if gene.max_nesting_depth > 4:
            add_opportunity(
                opt_type=OptimizationType.STRUCTURE.value,
                severity="medium",
                title=f"嵌套过深: {gene.max_nesting_depth}层",
                description=f"最大嵌套深度超过4层，建议使用早返回、提取条件、卫语句",
                location="全局",
                current=gene.max_nesting_depth,
                target=4,
                improvement=(gene.max_nesting_depth - 4) / gene.max_nesting_depth,
                priority=3
            )
        
        # 4. 代码量超过基准
        module_type = self._guess_module_type(gene)
        benchmark = self.LOC_BENCHMARKS.get(module_type, self.LOC_BENCHMARKS["complete_module"])
        if gene.lines_of_code > benchmark["base"]:
            add_opportunity(
                opt_type=OptimizationType.STRUCTURE.value,
                severity="high" if gene.lines_of_code > benchmark["base"] * 1.5 else "medium",
                title=f"代码量超过基准: {gene.lines_of_code}行 (基准{benchmark['base']}行)",
                description=f"代码量超过{module_type}类型的基准值，建议进行结构化优化，目标减少到{benchmark['good']}行",
                location="全局",
                current=gene.lines_of_code,
                target=benchmark["good"],
                improvement=(gene.lines_of_code - benchmark["good"]) / gene.lines_of_code,
                priority=1
            )
        
        # 5. 可读性低
        if gene.readability_score < 6:
            add_opportunity(
                opt_type=OptimizationType.NAMING.value,
                severity="medium" if gene.readability_score < 4 else "low",
                title=f"可读性偏低: {gene.readability_score}/10",
                description=f"可读性评分低于6，建议优化变量命名、添加注释、简化逻辑",
                location="全局",
                current=gene.readability_score,
                target=7,
                improvement=(7 - gene.readability_score) / 10,
                priority=4
            )
        
        # 6. 文档字符串覆盖率低
        if gene.docstring_coverage < 0.5 and gene.functions_count > 0:
            add_opportunity(
                opt_type=OptimizationType.COMMENT.value,
                severity="medium",
                title=f"文档字符串覆盖率低: {gene.docstring_coverage:.0%}",
                description=f"只有{gene.docstring_coverage:.0%}的函数/类有文档字符串，建议补充",
                location="全局",
                current=gene.docstring_coverage,
                target=0.8,
                improvement=(0.8 - gene.docstring_coverage),
                priority=5
            )
        
        # 7. 导入过多
        if gene.imports_count > 15:
            add_opportunity(
                opt_type=OptimizationType.DEPENDENCY.value,
                severity="low",
                title=f"导入过多: {gene.imports_count}个",
                description=f"导入数量超过15个，建议检查是否有不必要的导入，考虑延迟加载重型依赖",
                location="文件头部",
                current=gene.imports_count,
                target=15,
                improvement=(gene.imports_count - 15) / gene.imports_count,
                priority=6
            )
        
        # 8. 平均函数长度过长
        if gene.avg_function_length > 30:
            add_opportunity(
                opt_type=OptimizationType.STRUCTURE.value,
                severity="medium",
                title=f"平均函数长度过长: {gene.avg_function_length:.0f}行",
                description=f"平均函数长度超过30行，建议拆分函数，每个函数控制在20行以内",
                location="全局",
                current=gene.avg_function_length,
                target=20,
                improvement=(gene.avg_function_length - 20) / gene.avg_function_length,
                priority=3
            )
        
        # 按优先级排序
        opportunities.sort(key=lambda x: x.priority)
        
        # 保存到全局
        self.opportunities.extend(opportunities)
        self._save_state()
        
        return opportunities
    
    def record_evolution(self, module_id: str, before_gene: CodeGene, 
                         after_gene: CodeGene, optimization_type: str,
                         description: str, techniques: List[str] = None,
                         tests_passed: bool = True) -> CodeEvolutionLog:
        """
        记录一次代码进化
        
        Args:
            module_id: 模块ID
            before_gene: 优化前的代码基因
            after_gene: 优化后的代码基因
            optimization_type: 优化类型
            description: 优化描述
            techniques: 使用的优化技术
            tests_passed: 测试是否通过
            
        Returns:
            代码进化日志
        """
        # 计算优化效果
        loc_reduction = (before_gene.lines_of_code - after_gene.lines_of_code) / before_gene.lines_of_code if before_gene.lines_of_code > 0 else 0
        complexity_reduction = (before_gene.cyclomatic_complexity - after_gene.cyclomatic_complexity) / before_gene.cyclomatic_complexity if before_gene.cyclomatic_complexity > 0 else 0
        readability_improvement = (after_gene.readability_score - before_gene.readability_score) / 10
        maintainability_improvement = (after_gene.maintainability_score - before_gene.maintainability_score) / 10
        
        # 生成日志ID
        log_id = f"EVO-{module_id}-{len(self.evolution_logs) + 1:04d}"
        
        # 父日志哈希
        parent_log_hash = self.evolution_logs[-1].log_hash if self.evolution_logs else "0" * 64
        
        # 计算日志哈希
        log_content = json.dumps({
            "log_id": log_id,
            "module_id": module_id,
            "before_loc": before_gene.lines_of_code,
            "after_loc": after_gene.lines_of_code,
            "optimization_type": optimization_type,
            "timestamp": datetime.now().isoformat()
        }, sort_keys=True)
        log_hash = hashlib.sha256(log_content.encode()).hexdigest().upper()
        
        # 创建进化日志
        log = CodeEvolutionLog(
            log_id=log_id,
            module_id=module_id,
            module_name=after_gene.module_name,
            timestamp=datetime.now().isoformat(),
            
            before_loc=before_gene.lines_of_code,
            before_complexity=before_gene.cyclomatic_complexity,
            before_readability=before_gene.readability_score,
            before_maintainability=before_gene.maintainability_score,
            
            after_loc=after_gene.lines_of_code,
            after_complexity=after_gene.cyclomatic_complexity,
            after_readability=after_gene.readability_score,
            after_maintainability=after_gene.maintainability_score,
            
            loc_reduction=round(loc_reduction, 4),
            complexity_reduction=round(complexity_reduction, 4),
            readability_improvement=round(readability_improvement, 4),
            maintainability_improvement=round(maintainability_improvement, 4),
            
            optimization_type=optimization_type,
            optimization_description=description,
            techniques_used=techniques or [],
            
            tests_passed=tests_passed,
            test_coverage_before=before_gene.test_coverage,
            test_coverage_after=after_gene.test_coverage,
            
            log_hash=log_hash,
            parent_log_hash=parent_log_hash,
            before_gene_hash=before_gene.gene_hash,
            after_gene_hash=after_gene.gene_hash
        )
        
        self.evolution_logs.append(log)
        self.config["total_optimizations"] = self.config.get("total_optimizations", 0) + 1
        
        # 更新模块基因
        if module_id in self.code_genes:
            gene = self.code_genes[module_id]
            gene.optimization_count += 1
            gene.last_optimized = datetime.now().isoformat()
            gene.total_loc_reduction += loc_reduction
            gene.evolution_stage = after_gene.evolution_stage
        
        self._save_state()
        
        return log
    
    def get_evolution_report(self, module_id: str = None) -> Dict:
        """
        获取代码进化报告
        
        Args:
            module_id: 模块ID（不指定则返回全局报告）
            
        Returns:
            进化报告
        """
        if module_id:
            return self._get_module_report(module_id)
        else:
            return self._get_global_report()
    
    def _get_global_report(self) -> Dict:
        """获取全局进化报告"""
        total_modules = len(self.code_genes)
        total_loc = sum(g.lines_of_code for g in self.code_genes.values())
        total_functions = sum(g.functions_count for g in self.code_genes.values())
        total_optimizations = len(self.evolution_logs)
        
        # 累计代码量减少
        total_loc_reduction = sum(log.loc_reduction * log.before_loc for log in self.evolution_logs)
        
        # 平均优化效果
        avg_loc_reduction = sum(log.loc_reduction for log in self.evolution_logs) / total_optimizations if total_optimizations else 0
        avg_complexity_reduction = sum(log.complexity_reduction for log in self.evolution_logs) / total_optimizations if total_optimizations else 0
        
        # 进化阶段分布
        stage_distribution = Counter(g.evolution_stage for g in self.code_genes.values())
        
        # 优化类型分布
        type_distribution = Counter(log.optimization_type for log in self.evolution_logs)
        
        # 待优化机会
        pending_opportunities = len(self.opportunities)
        high_priority = sum(1 for opp in self.opportunities if opp.priority <= 2)
        
        return {
            "report_type": "global",
            "generated_at": datetime.now().isoformat(),
            "engine_version": self.VERSION,
            
            "overview": {
                "total_modules": total_modules,
                "total_lines_of_code": total_loc,
                "total_functions": total_functions,
                "total_optimizations": total_optimizations,
                "total_loc_reduced": round(total_loc_reduction, 0),
                "avg_loc_reduction_per_optimization": f"{avg_loc_reduction:.1%}",
                "avg_complexity_reduction": f"{avg_complexity_reduction:.1%}"
            },
            
            "evolution_stage_distribution": dict(stage_distribution),
            "optimization_type_distribution": dict(type_distribution),
            
            "pending_optimizations": {
                "total": pending_opportunities,
                "high_priority": high_priority
            },
            
            "top_modules_by_loc": sorted(
                [{"module": g.module_name, "loc": g.lines_of_code, "stage": g.evolution_stage} 
                 for g in self.code_genes.values()],
                key=lambda x: x["loc"], reverse=True
            )[:10],
            
            "recent_evolutions": [
                {
                    "log_id": log.log_id,
                    "module": log.module_name,
                    "type": log.optimization_type,
                    "loc_reduction": f"{log.loc_reduction:.1%}",
                    "description": log.optimization_description,
                    "timestamp": log.timestamp
                }
                for log in self.evolution_logs[-10:][::-1]
            ]
        }
    
    def _get_module_report(self, module_id: str) -> Dict:
        """获取单个模块的进化报告"""
        if module_id not in self.code_genes:
            return {"error": f"模块不存在: {module_id}"}
        
        gene = self.code_genes[module_id]
        module_logs = [log for log in self.evolution_logs if log.module_id == module_id]
        module_opportunities = [opp for opp in self.opportunities if opp.module_id == module_id]
        
        return {
            "report_type": "module",
            "module_id": module_id,
            "module_name": gene.module_name,
            "file_path": gene.file_path,
            
            "current_gene": asdict(gene),
            
            "evolution_history": [
                {
                    "log_id": log.log_id,
                    "type": log.optimization_type,
                    "before_loc": log.before_loc,
                    "after_loc": log.after_loc,
                    "loc_reduction": f"{log.loc_reduction:.1%}",
                    "description": log.optimization_description,
                    "timestamp": log.timestamp
                }
                for log in module_logs[::-1]
            ],
            
            "optimization_opportunities": [
                {
                    "type": opp.optimization_type,
                    "severity": opp.severity,
                    "title": opp.title,
                    "description": opp.description,
                    "estimated_improvement": f"{opp.estimated_improvement:.1%}",
                    "priority": opp.priority
                }
                for opp in sorted(module_opportunities, key=lambda x: x.priority)
            ],
            
            "summary": {
                "total_optimizations": len(module_logs),
                "total_loc_reduction": sum(log.loc_reduction * log.before_loc for log in module_logs),
                "current_evolution_stage": gene.evolution_stage,
                "optimization_potential": gene.optimization_potential,
                "pending_opportunities": len(module_opportunities)
            }
        }
    
    def _calculate_node_complexity(self, node: ast.AST) -> int:
        """计算节点的圈复杂度贡献"""
        complexity = 0
        # 决策点
        if isinstance(node, (ast.If, ast.For, ast.While, ast.And, ast.Or, 
                            ast.ExceptHandler, ast.With, ast.Assert)):
            complexity += 1
        # 条件表达式
        if isinstance(node, ast.IfExp):
            complexity += 1
        # 布尔运算
        if isinstance(node, ast.BoolOp):
            complexity += len(node.values) - 1
        # 比较运算
        if isinstance(node, ast.Compare):
            complexity += len(node.ops) - 1
        return complexity
    
    def _calculate_nesting_depth(self, node: ast.AST, current_depth: int = 0) -> int:
        """计算节点的最大嵌套深度"""
        max_depth = current_depth
        
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.Try, 
                                  ast.With, ast.FunctionDef, ast.ClassDef)):
                child_depth = self._calculate_nesting_depth(child, current_depth + 1)
            else:
                child_depth = self._calculate_nesting_depth(child, current_depth)
            max_depth = max(max_depth, child_depth)
        
        return max_depth
    
    def _calculate_readability_score(self, loc, functions, avg_func_len, 
                                      max_depth, comments, total) -> float:
        """计算可读性评分 (0-10)"""
        score = 10.0
        
        # 函数长度惩罚
        if avg_func_len > 20:
            score -= min(2, (avg_func_len - 20) / 20)
        
        # 嵌套深度惩罚
        if max_depth > 4:
            score -= min(2, (max_depth - 4) * 0.5)
        
        # 代码密度（注释比例）
        if total > 0:
            comment_ratio = comments / total
            if comment_ratio < 0.1:
                score -= 1
            elif comment_ratio > 0.4:
                score -= 0.5  # 注释过多也可能是问题
        
        # 函数数量合理性
        if functions > 0:
            func_density = loc / functions
            if func_density > 50:  # 每个函数平均代码太多
                score -= 1
            elif func_density < 5:  # 函数太碎
                score -= 0.5
        
        return max(0, min(10, score))
    
    def _calculate_maintainability_score(self, loc, complexity, functions, 
                                          classes, readability) -> float:
        """计算可维护性评分 (0-10)"""
        score = 10.0
        
        # 代码量惩罚
        if loc > 500:
            score -= min(2, (loc - 500) / 500)
        
        # 复杂度惩罚
        if complexity > 20:
            score -= min(2, (complexity - 20) / 20)
        
        # 可读性关联
        score -= (10 - readability) * 0.3
        
        # 模块化奖励
        if functions > 5 and classes > 0:
            score += 0.5
        
        return max(0, min(10, score))
    
    def _calculate_optimization_potential(self, loc, complexity, max_func_len,
                                            max_depth, readability, maintainability) -> float:
        """计算优化潜力 (0-1)"""
        potential = 0.0
        
        # 代码量优化潜力
        if loc > 100:
            potential += min(0.3, (loc - 100) / 1000)
        
        # 复杂度优化潜力
        if complexity > 10:
            potential += min(0.2, (complexity - 10) / 50)
        
        # 函数长度优化潜力
        if max_func_len > 30:
            potential += min(0.2, (max_func_len - 30) / 100)
        
        # 嵌套深度优化潜力
        if max_depth > 3:
            potential += min(0.1, (max_depth - 3) / 10)
        
        # 质量提升潜力
        potential += (10 - readability) / 20
        potential += (10 - maintainability) / 20
        
        return min(1.0, potential)
    
    def _determine_evolution_stage(self, loc, readability, maintainability,
                                     potential, func_lengths) -> str:
        """确定进化阶段"""
        # L5 基因代码 - 极致优化，可遗传
        if (loc < 50 and readability > 9 and maintainability > 9 and 
            potential < 0.1 and all(f < 15 for f in func_lengths)):
            return CodeEvolutionStage.GENETIC.value
        
        # L4 极致代码 - 近乎完美
        if (loc < 100 and readability > 8.5 and maintainability > 8.5 and 
            potential < 0.2 and all(f < 25 for f in func_lengths)):
            return CodeEvolutionStage.EXTREME.value
        
        # L3 精炼代码 - 深度优化
        if (readability > 7.5 and maintainability > 7.5 and 
            potential < 0.35 and all(f < 40 for f in func_lengths)):
            return CodeEvolutionStage.REFINED.value
        
        # L2 优化代码 - 经过第一轮优化
        if (readability > 6 and maintainability > 6 and 
            potential < 0.5 and (not func_lengths or max(func_lengths) < 60)):
            return CodeEvolutionStage.OPTIMIZED.value
        
        # L1 规范化代码 - 有基本规范
        if readability > 4 and maintainability > 4:
            return CodeEvolutionStage.NORMALIZED.value
        
        # L0 原始代码
        return CodeEvolutionStage.RAW.value
    
    def _guess_module_type(self, gene: CodeGene) -> str:
        """猜测模块类型"""
        if gene.classes_count == 0 and gene.functions_count <= 5:
            return "simple_function"
        if gene.classes_count == 0 and gene.functions_count > 5:
            return "complex_function"
        if gene.classes_count == 1 and gene.methods_count <= 5:
            return "data_class"
        if gene.classes_count >= 1 and gene.methods_count > 5:
            return "business_class"
        if gene.functions_count > 10 and "api" in gene.module_name.lower():
            return "api_layer"
        return "complete_module"


# 便捷函数
def create_code_gene_engine(data_path: str = "./code-evolution") -> CodeGeneEngine:
    """快速创建代码基因引擎"""
    return CodeGeneEngine(data_path=data_path)


def scan_and_report(file_path: str, data_path: str = "./code-evolution") -> Dict:
    """扫描文件并生成完整报告"""
    engine = create_code_gene_engine(data_path)
    gene = engine.scan_file(file_path)
    opportunities = engine.identify_optimization_opportunities(gene)
    report = engine.get_evolution_report(gene.module_id)
    return report


if __name__ == "__main__":
    # 测试代码基因引擎
    print("=" * 70)
    print("🧬 代码基因扫描器与代码进化引擎 (Code Gene Engine) 测试")
    print("=" * 70)
    
    # 创建引擎
    engine = create_code_gene_engine("/tmp/test-code-evolution")
    
    # 扫描自身（递归测试）
    print("\n📂 扫描代码文件...")
    test_file = "/home/user/Doubao/chats/38429779701191938/通用自进化引擎-UEE-V1.0.py"
    
    if os.path.exists(test_file):
        gene = engine.scan_file(test_file, module_id="test-uee-001", module_name="通用自进化引擎")
        
        print(f"\n✅ 扫描完成: {gene.module_name}")
        print(f"   代码行数: {gene.lines_of_code} (总行数 {gene.total_lines})")
        print(f"   函数数量: {gene.functions_count}")
        print(f"   类数量: {gene.classes_count}")
        print(f"   圈复杂度: {gene.cyclomatic_complexity}")
        print(f"   最大嵌套深度: {gene.max_nesting_depth}")
        print(f"   平均函数长度: {gene.avg_function_length:.0f}行")
        print(f"   最大函数长度: {gene.max_function_length}行")
        print(f"   可读性评分: {gene.readability_score}/10")
        print(f"   可维护性评分: {gene.maintainability_score}/10")
        print(f"   文档字符串覆盖率: {gene.docstring_coverage:.0%}")
        print(f"   进化阶段: {gene.evolution_stage}")
        print(f"   优化潜力: {gene.optimization_potential:.0%}")
        
        # 识别优化机会
        print("\n🔍 识别优化机会...")
        opportunities = engine.identify_optimization_opportunities(gene)
        
        if opportunities:
            print(f"   发现 {len(opportunities)} 个优化机会:")
            for opp in opportunities[:5]:
                print(f"   [{opp.priority}] {opp.title} (预计改进 {opp.estimated_improvement:.0%})")
        else:
            print("   未发现明显优化机会，代码质量良好！")
        
        # 模拟一次进化
        print("\n🧬 模拟代码进化（优化后）...")
        # 创建优化后的基因（模拟）
        optimized_gene = CodeGene(
            module_id=gene.module_id,
            module_name=gene.module_name,
            file_path=gene.file_path,
            lines_of_code=int(gene.lines_of_code * 0.7),  # 减少30%
            functions_count=gene.functions_count,
            classes_count=gene.classes_count,
            cyclomatic_complexity=int(gene.cyclomatic_complexity * 0.8),
            readability_score=min(10, gene.readability_score + 1),
            maintainability_score=min(10, gene.maintainability_score + 1),
            evolution_stage=CodeEvolutionStage.OPTIMIZED.value,
            scanned_at=datetime.now().isoformat()
        )
        optimized_gene.gene_hash = optimized_gene.calculate_gene_hash()
        
        log = engine.record_evolution(
            module_id=gene.module_id,
            before_gene=gene,
            after_gene=optimized_gene,
            optimization_type=OptimizationType.STRUCTURE.value,
            description="提取重复代码为公共函数，拆分过长函数，使用列表推导式简化循环",
            techniques=["extract_method", "compose_method", "list_comprehension"],
            tests_passed=True
        )
        
        print(f"   进化日志ID: {log.log_id}")
        print(f"   代码量减少: {log.loc_reduction:.1%} ({log.before_loc} → {log.after_loc}行)")
        print(f"   复杂度减少: {log.complexity_reduction:.1%}")
        print(f"   可读性提升: {log.readability_improvement:.1%}")
        print(f"   日志哈希: {log.log_hash[:16]}...")
        
        # 获取全局报告
        print("\n📊 全局进化报告:")
        report = engine.get_evolution_report()
        print(f"   扫描模块数: {report['overview']['total_modules']}")
        print(f"   总代码行数: {report['overview']['total_lines_of_code']}")
        print(f"   总优化次数: {report['overview']['total_optimizations']}")
        print(f"   累计减少代码: {report['overview']['total_loc_reduced']:.0f}行")
        print(f"   平均每次优化减少: {report['overview']['avg_loc_reduction_per_optimization']}")
        print(f"   待优化机会: {report['pending_optimizations']['total']}个")
    
    print("\n" + "=" * 70)
    print("✅ 代码基因引擎测试完成！")
    print("   代码不是静态的文本，而是有生命的载体。")
    print("   每一次优化都是一次进化，每一行代码都有基因。")
    print("=" * 70)
    
    # 清理测试数据
    import shutil
    shutil.rmtree("/tmp/test-code-evolution", ignore_errors=True)
