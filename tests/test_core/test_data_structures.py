"""
测试核心数据结构
"""

import pytest
from src.core.data_structures import NodeState, TaskLedger, ProgressLedger


class TestNodeState:
    """测试节点状态枚举"""
    
    def test_node_state_values(self):
        """测试节点状态值"""
        assert NodeState.NOT_STARTED.value == "not_started"
        assert NodeState.IN_PROGRESS.value == "in_progress"
        assert NodeState.COMPLETED.value == "completed"
        assert NodeState.FAILED.value == "failed"
        assert NodeState.RETRYING.value == "retrying"


class TestTaskLedger:
    """测试任务账本"""
    
    def test_task_ledger_initialization(self):
        """测试任务账本初始化"""
        ledger = TaskLedger()
        assert ledger.original_task == ""
        assert ledger.facts == []
        assert ledger.guesses == []
        assert ledger.plan == []
        assert ledger.agent_capabilities == {}
        assert ledger.failed_paths == []
        assert ledger.project_config == {}
    
    def test_update_facts(self):
        """测试更新事实"""
        ledger = TaskLedger()
        new_facts = ["事实1", "事实2"]
        ledger.update_facts(new_facts)
        assert ledger.facts == new_facts
    
    def test_update_plan(self):
        """测试更新计划"""
        ledger = TaskLedger()
        new_plan = ["步骤1", "步骤2"]
        ledger.update_plan(new_plan)
        assert ledger.plan == new_plan
    
    def test_set_project_config(self):
        """测试设置项目配置"""
        ledger = TaskLedger()
        ledger.set_project_config("test_project", "main.py", "test_main.py")
        
        assert ledger.project_config["project_name"] == "test_project"
        assert ledger.project_config["main_file"] == "main.py"
        assert ledger.project_config["test_file"] == "test_main.py"
        assert "/Users/jabez/output/main.py" in ledger.project_config["main_file_path"]
        assert "/Users/jabez/output/test_main.py" in ledger.project_config["test_file_path"]
    
    def test_get_file_path(self):
        """测试获取文件路径"""
        ledger = TaskLedger()
        ledger.set_project_config("test_project", "main.py", "test_main.py")
        
        main_path = ledger.get_file_path("main")
        test_path = ledger.get_file_path("test")
        
        assert "main.py" in main_path
        assert "test_main.py" in test_path


class TestProgressLedger:
    """测试进度账本"""
    
    def test_progress_ledger_initialization(self):
        """测试进度账本初始化"""
        ledger = ProgressLedger()
        assert ledger.node_states == {}
        assert ledger.execution_history == []
        assert ledger.current_active_nodes == set()
        assert ledger.stall_count == 0
        assert ledger.retry_counts == {}
    
    def test_update_node_state(self):
        """测试更新节点状态"""
        ledger = ProgressLedger()
        ledger.update_node_state("test_node", NodeState.IN_PROGRESS)
        
        assert ledger.node_states["test_node"] == NodeState.IN_PROGRESS
        assert len(ledger.execution_history) == 1
        assert ledger.execution_history[0]["node"] == "test_node"
        assert ledger.execution_history[0]["state"] == "in_progress"
    
    def test_increment_retry(self):
        """测试增加重试计数"""
        ledger = ProgressLedger()
        
        count1 = ledger.increment_retry("test_node")
        assert count1 == 1
        assert ledger.retry_counts["test_node"] == 1
        
        count2 = ledger.increment_retry("test_node")
        assert count2 == 2
        assert ledger.retry_counts["test_node"] == 2
