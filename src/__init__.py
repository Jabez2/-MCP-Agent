"""
基于MCP的多链代码生成Agent开发项目

这个包提供了一个完整的多Agent协作系统，用于代码生成、测试、验证、反思、重构、质量扫描和项目结构化。
"""

__version__ = "1.0.0"
__author__ = "MCP MultiChain Agent Team"
__description__ = "基于MCP的多链代码生成Agent开发项目"

from .core.orchestrator import GraphFlowOrchestrator
from .core.data_structures import NodeState, TaskLedger, ProgressLedger

__all__ = [
    "GraphFlowOrchestrator",
    "NodeState", 
    "TaskLedger",
    "ProgressLedger"
]
