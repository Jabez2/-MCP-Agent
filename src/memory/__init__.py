"""
Memory系统初始化模块

提供统一的memory系统接口
"""

from .memory_config import memory_config, MemoryConfig
from .base_memory_manager import (
    ExecutionLogManager,
    AgentStateManager,
    execution_log_manager,
    agent_state_manager
)
from .agent_communication_memory import (
    AgentCommunicationMemory,
    AgentMessage,
    AgentContext,
    agent_communication_memory
)
from .unit_test_memory_manager import (
    UnitTestMemoryManager,
    unit_test_memory_manager
)

__all__ = [
    "memory_config",
    "MemoryConfig",
    "ExecutionLogManager",
    "AgentStateManager",
    "execution_log_manager",
    "agent_state_manager",
    "AgentCommunicationMemory",
    "AgentMessage",
    "AgentContext",
    "agent_communication_memory",
    "UnitTestMemoryManager",
    "unit_test_memory_manager"
]


async def initialize_memory_system():
    """初始化整个memory系统"""
    print("🧠 初始化Memory系统...")

    try:
        # 初始化执行日志管理器
        await execution_log_manager.initialize()
        print("✅ 执行日志管理器初始化完成")

        # 初始化Agent通信Memory
        await agent_communication_memory.initialize()
        print("✅ Agent通信Memory初始化完成")

        # 检查Agent状态目录
        saved_states = agent_state_manager.list_saved_states()
        if saved_states:
            print(f"📂 发现已保存的Agent状态: {saved_states}")

        print("🎉 Memory系统初始化完成")
        return True

    except Exception as e:
        print(f"❌ Memory系统初始化失败: {e}")
        return False


async def cleanup_memory_system():
    """清理memory系统资源"""
    print("🧹 清理Memory系统资源...")

    try:
        await execution_log_manager.close()
        await agent_communication_memory.close()
        await unit_test_memory_manager.close()
        print("✅ Memory系统资源清理完成")

    except Exception as e:
        print(f"⚠️ Memory系统清理时出现警告: {e}")
