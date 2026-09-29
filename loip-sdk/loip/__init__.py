"""
LOIP - 逻辑本体智能协议 SDK v0.4
大模型上层稳态约束协议 · 认知校准底座 · 本体秩序治理系统 · 安全护栏 · 多模型适配

v0.4新增：多模型适配层（豆包/OpenAI/通义/智谱/Ollama）、loip.chat()一键调用、
          6大行业基线模板库、配置文件驱动初始化
"""
from .baseline import OntologyBaseline
from .drift import DriftDetector
from .hallucination import HallucinationGuard
from .audit import DualAuditSystem
from .sdk import LOIP
from .semantic import get_detector, KeywordBackend, SemanticBackend, extract_entities
from .security_guard import SecurityGuard
from .daemon import LOIPDaemon
from .adapters import create_adapter, get_supported_models
from .templates import list_templates, get_template, apply_template

__version__ = "0.4.0"
__all__ = ["LOIP", "OntologyBaseline", "DriftDetector", "HallucinationGuard",
           "DualAuditSystem", "get_detector", "KeywordBackend", "SemanticBackend",
           "extract_entities", "SecurityGuard", "LOIPDaemon",
           "create_adapter", "get_supported_models",
           "list_templates", "get_template", "apply_template"]
