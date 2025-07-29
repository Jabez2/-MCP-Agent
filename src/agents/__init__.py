"""
Agents模块 - 包含所有的Agent创建函数
"""

from .planning_agent import create_planning_agent
from .coding_agent import create_coding_agent
from .test_agent import create_test_agent
from .unit_test_agent import create_unit_test_agent
from .refactoring_agent import create_refactoring_agent
from .scanning_agent import create_scanning_agent
from .structure_agent import create_structure_agent

__all__ = [
    "create_planning_agent",
    "create_coding_agent",
    "create_test_agent",
    "create_unit_test_agent",
    "create_refactoring_agent",
    "create_scanning_agent",
    "create_structure_agent"
]


def create_all_agents(fs_workbench, code_workbench, model_client):
    """创建所有Agent并返回列表 - 基于test.py的流程，不包含ReflectionAgent"""
    agents = [
        create_planning_agent(model_client, fs_workbench),
        create_coding_agent(model_client, fs_workbench),
        create_test_agent(model_client, fs_workbench),
        create_unit_test_agent(model_client, code_workbench),
        create_refactoring_agent(model_client, fs_workbench),
        create_scanning_agent(model_client, fs_workbench),
        create_structure_agent(model_client, fs_workbench)
    ]
    return agents
