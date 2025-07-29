"""
核心数据结构定义

包含系统中使用的主要数据结构：
- NodeState: 节点执行状态枚举
- TaskLedger: 任务账本，管理全局任务状态和计划
- ProgressLedger: 进度账本，管理执行进度和状态跟踪
"""

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Set


class NodeState(Enum):
    """节点执行状态枚举"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class TaskLedger:
    """任务账本 - 管理全局任务状态和计划"""
    original_task: str = ""
    facts: List[str] = field(default_factory=list)
    guesses: List[str] = field(default_factory=list)
    plan: List[str] = field(default_factory=list)
    agent_capabilities: Dict[str, str] = field(default_factory=dict)
    failed_paths: List[str] = field(default_factory=list)

    # 新增：动态文件命名配置
    project_config: Dict[str, str] = field(default_factory=dict)

    def update_facts(self, new_facts: List[str]):
        """更新已确认的事实"""
        self.facts.extend(new_facts)

    def update_plan(self, new_plan: List[str]):
        """更新执行计划"""
        self.plan = new_plan

    def set_project_config(self, project_name: str, main_file: str, test_file: str, base_dir: str = "/Users/jabez/output"):
        """设置项目配置信息"""
        self.project_config = {
            "project_name": project_name,
            "main_file": main_file,
            "test_file": test_file,
            "base_dir": base_dir,
            "main_file_path": f"{base_dir}/{main_file}",
            "test_file_path": f"{base_dir}/{test_file}"
        }

    def get_file_path(self, file_type: str) -> str:
        """获取文件路径"""
        if file_type == "main":
            return self.project_config.get("main_file_path", "/Users/jabez/output/main.py")
        elif file_type == "test":
            return self.project_config.get("test_file_path", "/Users/jabez/output/test_main.py")
        else:
            return f"{self.project_config.get('base_dir', '/Users/jabez/output')}/{file_type}"

    def get_intelligent_path_resolver(self):
        """获取智能路径解析器"""
        from .path_resolver import IntelligentPathResolver
        return IntelligentPathResolver(self.project_config, self.facts, self.plan)


@dataclass
class ProgressLedger:
    """进度账本 - 管理执行进度和状态跟踪"""
    node_states: Dict[str, NodeState] = field(default_factory=dict)
    execution_history: List[Dict[str, Any]] = field(default_factory=list)
    current_active_nodes: Set[str] = field(default_factory=set)
    stall_count: int = 0
    retry_counts: Dict[str, int] = field(default_factory=dict)

    def update_node_state(self, node_name: str, state: NodeState):
        """更新节点状态并记录历史"""
        self.node_states[node_name] = state
        self.execution_history.append({
            "node": node_name,
            "state": state.value,
            "timestamp": asyncio.get_event_loop().time()
        })

    def increment_retry(self, node_name: str) -> int:
        """增加重试计数并返回当前计数"""
        self.retry_counts[node_name] = self.retry_counts.get(node_name, 0) + 1
        return self.retry_counts[node_name]
