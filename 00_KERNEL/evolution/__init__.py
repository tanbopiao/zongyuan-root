"""
SELF-TRIAD V1.0
自学习-自进化-自优化闭环 | ZONGYUAN-ROOT
"""
from .triad_orchestrator import TriadOrchestrator

__version__ = "V1.0"
__authority_tag__ = "SELF-TRIAD-V1.0"

def get_triad_orchestrator():
    return TriadOrchestrator()
