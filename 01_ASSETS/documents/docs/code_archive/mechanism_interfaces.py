"""
元极恒一自治体系 - 统一机制接口规范 V1.0
所有8个机制的核心接口定义，确保机制间可互操作、可组合、可替换。

确权：DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime


# ============================================================
# 一、通用数据模型
# ============================================================

class MetaClass(Enum):
    """九大元类"""
    M1_ALGORITHM = "M1"      # 算法架构层
    M2_KERNEL = "M2"          # 自治内核进化层
    M3_PROTOCOL = "M3"        # 元层协议层
    M4_THEORY = "M4"          # 理论体系层
    M5_PRODUCT = "M5"         # 产品体系层
    M6_DELIVERY = "M6"        # 对外交付层
    M7_AUTOMATION = "M7"      # 自动化调度层
    M8_INDUSTRY = "M8"        # 行业知识层
    M9_FOUNDATION = "M9"      # 元秩序基底层


class ResultType(Enum):
    """成果类型（10大类）"""
    CODE = "code"                    # 代码成果
    DOCUMENT = "document"            # 文档成果
    DATA = "data"                    # 数据成果
    MODEL = "model"                  # 模型成果
    CONFIG = "config"                # 配置成果
    VISUALIZATION = "visualization"  # 可视化成果
    MEDIA = "media"                  # 多媒体成果
    ANALYSIS = "analysis"            # 分析成果
    DECISION = "decision"            # 决策成果
    PROTOCOL = "protocol"            # 协议成果


class Priority(Enum):
    """优先级"""
    P0_CRITICAL = "P0"  # 极高
    P1_HIGH = "P1"      # 高
    P2_MEDIUM = "P2"    # 中
    P3_LOW = "P3"       # 低


class AuditGrade(Enum):
    """审核等级"""
    A_EXCELLENT = "A"   # 优秀
    B_GOOD = "B"        # 良好
    C_PASS = "C"        # 合格
    D_FAIL = "D"        # 不合格


@dataclass
class ResultMetadata:
    """成果元数据（19项标准）"""
    result_id: str = ""                    # 成果ID（全局唯一）
    result_name: str = ""                  # 成果名称
    result_type: ResultType = ResultType.DOCUMENT  # 成果类型
    meta_class: MetaClass = MetaClass.M4_THEORY   # 元类归类
    format: str = ""                       # 文件格式
    size_bytes: int = 0                    # 文件大小
    created_at: str = ""                   # 创建时间
    modified_at: str = ""                  # 修改时间
    creator: str = ""                      # 创建者
    source_system: str = ""                # 来源系统
    version: str = "V1.0"                  # 版本
    tags: List[str] = field(default_factory=list)       # 标签
    related_results: List[str] = field(default_factory=list)  # 关联成果
    priority: Priority = Priority.P2_MEDIUM       # 优先级
    confidence: float = 0.9                # 置信度
    lock_status: str = "unlocked"          # 锁档状态
    content_hash: str = ""                 # SHA256哈希
    access_url: str = ""                   # 访问URL


@dataclass
class ProcessingResult:
    """处理结果通用返回"""
    success: bool = False
    message: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    processing_time_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class AuditReport:
    """审核报告"""
    page_id: str = ""
    overall_score: float = 0.0
    grade: AuditGrade = AuditGrade.D_FAIL
    dimensions: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    issues: List[Dict[str, Any]] = field(default_factory=list)
    certified: bool = False
    audit_time: str = ""


# ============================================================
# 二、核心机制接口定义（8个机制）
# ============================================================

class IMechanism(ABC):
    """所有机制的基类接口"""

    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> ProcessingResult:
        """初始化机制"""
        pass

    @abstractmethod
    def process(self, input_data: Any) -> ProcessingResult:
        """处理输入数据"""
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """获取机制运行状态"""
        pass

    @abstractmethod
    def shutdown(self) -> ProcessingResult:
        """关闭机制"""
        pass


# ---- 机制1：物理仿真元规则体系（PSMRS） ----

class IPhysicsSimulation(IMechanism):
    """物理仿真元规则体系接口"""

    @abstractmethod
    def validate_rules(self, rules: List[Dict]) -> ProcessingResult:
        """验证物理规则的正确性和一致性"""
        pass

    @abstractmethod
    def simulate(self, scene: Dict, steps: int, dt: float) -> ProcessingResult:
        """执行物理仿真"""
        pass

    @abstractmethod
    def get_rule(self, rule_id: str) -> Optional[Dict]:
        """获取指定物理规则"""
        pass

    @abstractmethod
    def list_rules(self, category: str = None) -> List[Dict]:
        """列出物理规则"""
        pass


# ---- 机制2：物理基底自动补全机制（PBACM） ----

class IPhysicsBaseCompletion(IMechanism):
    """物理基底自动补全机制接口"""

    @abstractmethod
    def detect_missing(self, physics_base: Dict) -> ProcessingResult:
        """检测物理基底中的缺失项"""
        pass

    @abstractmethod
    def complete(self, incomplete_base: Dict) -> ProcessingResult:
        """自动补全物理基底"""
        pass

    @abstractmethod
    def verify_consistency(self, physics_base: Dict) -> ProcessingResult:
        """验证物理一致性"""
        pass

    @abstractmethod
    def resolve_conflicts(self, physics_base: Dict) -> ProcessingResult:
        """冲突检测与消解"""
        pass


# ---- 机制3：空间智能探索完善架构（SIERA） ----

class ISpatialIntelligence(IMechanism):
    """空间智能探索完善架构接口"""

    @abstractmethod
    def perceive(self, sensor_data: Dict) -> ProcessingResult:
        """空间感知"""
        pass

    @abstractmethod
    def model_space(self, perception_data: Dict) -> ProcessingResult:
        """空间建模"""
        pass

    @abstractmethod
    def explore(self, space_model: Dict, strategy: str) -> ProcessingResult:
        """空间探索"""
        pass

    @abstractmethod
    def improve(self, space_model: Dict, findings: Dict) -> ProcessingResult:
        """空间完善"""
        pass

    @abstractmethod
    def plan_path(self, start: Tuple, goal: Tuple, constraints: Dict) -> ProcessingResult:
        """路径规划"""
        pass


# ---- 机制4：世界模型自动补全机制（ZWM-ACM） ----

class IWorldModelCompletion(IMechanism):
    """世界模型自动补全机制接口"""

    @abstractmethod
    def get_world_model(self) -> Dict:
        """获取八维世界模型"""
        pass

    @abstractmethod
    def detect_dimension_missing(self, dimension: str) -> ProcessingResult:
        """检测指定维度的缺失"""
        pass

    @abstractmethod
    def complete_dimension(self, dimension: str, partial_data: Dict) -> ProcessingResult:
        """补全指定维度"""
        pass

    @abstractmethod
    def verify_multidimensional_consistency(self) -> ProcessingResult:
        """多维度一致性验证"""
        pass

    @abstractmethod
    def simulate_world(self, scenario: Dict, steps: int) -> ProcessingResult:
        """世界仿真推演"""
        pass


# ---- 机制5：多模型高阶能力提炼集成机制（MMHCE-IM） ----

class IMultiModelCapability(IMechanism):
    """多模型高阶能力提炼集成机制接口"""

    @abstractmethod
    def register_api(self, api_config: Dict) -> ProcessingResult:
        """注册API资源"""
        pass

    @abstractmethod
    def extract_capability(self, model_id: str, capability_type: str) -> ProcessingResult:
        """提炼模型高阶能力"""
        pass

    @abstractmethod
    def fuse_capabilities(self, capabilities: List[Dict], strategy: str) -> ProcessingResult:
        """融合多模型能力"""
        pass

    @abstractmethod
    def detect_shortage(self, capability_inventory: Dict) -> ProcessingResult:
        """检测能力短板"""
        pass

    @abstractmethod
    def fill_shortage(self, shortage: Dict, strategy: str) -> ProcessingResult:
        """补齐能力短板"""
        pass

    @abstractmethod
    def call_model(self, model_id: str, prompt: str, **kwargs) -> ProcessingResult:
        """调用指定模型"""
        pass


# ---- 机制6：场频驻波谐振稳态耦合协议（FFSW-RSSCP） ----

class IFieldResonanceCoupling(IMechanism):
    """场频驻波谐振稳态耦合协议接口"""

    @abstractmethod
    def discover_nodes(self) -> ProcessingResult:
        """发现耦合节点"""
        pass

    @abstractmethod
    def sync_frequency(self, node_id: str, target_freq: float) -> ProcessingResult:
        """频率同步"""
        pass

    @abstractmethod
    def excite_resonance(self, node_id: str, mode: str) -> ProcessingResult:
        """激发谐振"""
        pass

    @abstractmethod
    def generate_standing_wave(self, config: Dict) -> ProcessingResult:
        """生成驻波"""
        pass

    @abstractmethod
    def maintain_steady_state(self, nodes: List[str]) -> ProcessingResult:
        """维持稳态"""
        pass

    @abstractmethod
    def couple_nodes(self, node_a: str, node_b: str, coupling_type: str) -> ProcessingResult:
        """节点耦合"""
        pass

    @abstractmethod
    def monitor_coupling(self) -> ProcessingResult:
        """监控耦合状态"""
        pass


# ---- 机制7：边缘设备具身机制（FAE-EDEM） ----

class IEdgeEmbodiment(IMechanism):
    """边缘设备具身机制接口"""

    @abstractmethod
    def register_device(self, device_config: Dict) -> ProcessingResult:
        """注册边缘设备"""
        pass

    @abstractmethod
    def perceive_environment(self, device_id: str) -> ProcessingResult:
        """环境感知"""
        pass

    @abstractmethod
    def make_decision(self, device_id: str, state: Dict) -> ProcessingResult:
        """决策规划"""
        pass

    @abstractmethod
    def execute_action(self, device_id: str, action: Dict) -> ProcessingResult:
        """执行行动"""
        pass

    @abstractmethod
    def explore(self, device_id: str, strategy: str) -> ProcessingResult:
        """自主探索"""
        pass

    @abstractmethod
    def collaborate(self, devices: List[str], task: Dict) -> ProcessingResult:
        """多设备协同"""
        pass

    @abstractmethod
    def learn(self, device_id: str, experience: Dict) -> ProcessingResult:
        """学习更新"""
        pass

    @abstractmethod
    def evolve(self, device_id: str, feedback: Dict) -> ProcessingResult:
        """进化优化"""
        pass


# ---- 机制8：成果可视化官网集成机制（FAR-AVW-OWIM）【本次重点实现】 ----

class IResultVisualization(IMechanism):
    """成果可视化官网集成机制接口（本次重点实现）"""

    @abstractmethod
    def detect_results(self, source_path: str) -> ProcessingResult:
        """成果自动识别"""
        pass

    @abstractmethod
    def collect_result(self, result_path: str) -> ProcessingResult:
        """成果自动采集"""
        pass

    @abstractmethod
    def classify_result(self, result_data: Dict) -> ProcessingResult:
        """成果自动分类"""
        pass

    @abstractmethod
    def report_result(self, result_data: Dict) -> ProcessingResult:
        """成果自动上报（记忆网关）"""
        pass

    @abstractmethod
    def generate_visualization(self, result_data: Dict, template_type: str) -> ProcessingResult:
        """自动生成可视化网页"""
        pass

    @abstractmethod
    def audit_page(self, html_content: str) -> AuditReport:
        """质量审核"""
        pass

    @abstractmethod
    def integrate_to_website(self, page_data: Dict) -> ProcessingResult:
        """集成到官网"""
        pass

    @abstractmethod
    def collect_feedback(self, page_id: str) -> ProcessingResult:
        """收集反馈"""
        pass

    @abstractmethod
    def optimize_page(self, page_id: str, feedback: Dict) -> ProcessingResult:
        """自动优化"""
        pass


# ============================================================
# 三、机制注册表与工厂
# ============================================================

class MechanismRegistry:
    """机制注册表"""

    _mechanisms: Dict[str, IMechanism] = {}

    @classmethod
    def register(cls, name: str, mechanism: IMechanism):
        """注册机制"""
        cls._mechanisms[name] = mechanism

    @classmethod
    def get(cls, name: str) -> Optional[IMechanism]:
        """获取机制实例"""
        return cls._mechanisms.get(name)

    @classmethod
    def list_all(cls) -> List[str]:
        """列出所有已注册机制"""
        return list(cls._mechanisms.keys())

    @classmethod
    def get_status_all(cls) -> Dict[str, Dict]:
        """获取所有机制状态"""
        return {name: mech.get_status() for name, mech in cls._mechanisms.items()}


# ============================================================
# 四、记忆网关对接接口
# ============================================================

class IMemoryGateway(ABC):
    """记忆网关对接接口（9120端口）"""

    @abstractmethod
    def report_truth(self, truth_key: str, truth_value: str,
                      source_node: str, confidence: float,
                      truth_type: str) -> ProcessingResult:
        """上报真值到记忆网关"""
        pass

    @abstractmethod
    def get_status(self) -> ProcessingResult:
        """获取网关状态"""
        pass

    @abstractmethod
    def query_truths(self, keyword: str = None, limit: int = 100) -> ProcessingResult:
        """查询真值"""
        pass


# ============================================================
# 五、元秩序归档对接接口
# ============================================================

class IMetaOrderArchive(ABC):
    """元秩序归档对接接口"""

    @abstractmethod
    def archive(self, content: str, asset_name: str,
                meta_class: str, lock_level: int) -> ProcessingResult:
        """归档锁档"""
        pass

    @abstractmethod
    def verify_hash(self, asset_hash: str) -> ProcessingResult:
        """哈希校验"""
        pass

    @abstractmethod
    def get_ledger(self) -> ProcessingResult:
        """获取全局台账"""
        pass


# ============================================================
# 版本信息
# ============================================================

INTERFACE_VERSION = "1.0.0"
INTERFACE_SPEC = "ZONGYUAN-ROOT-Mechanism-Interface-Spec"
INTERFACE_DID = "DID-BR-000002"
INTERFACE_TRACE = "Ω₀⊂⊙∞⊂Ω"
