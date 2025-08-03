"""
Agent间通信增强Memory系统

提供Agent之间的消息传递、上下文共享和协作增强功能
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from autogen_core.memory import MemoryContent, MemoryMimeType
from .base_memory_manager import execution_log_manager
from .memory_config import memory_config


@dataclass
class AgentMessage:
    """Agent消息数据结构"""
    from_agent: str
    to_agent: str
    message_type: str  # "context", "error", "result", "request", "advice"
    content: str
    metadata: Dict[str, Any]
    timestamp: str
    message_id: str


@dataclass
class AgentContext:
    """Agent上下文数据结构"""
    agent_name: str
    current_task: str
    execution_state: str  # "starting", "in_progress", "completed", "failed"
    relevant_info: Dict[str, Any]
    dependencies: List[str]  # 依赖的其他Agent
    outputs: Dict[str, Any]  # 产出的结果
    timestamp: str


class AgentCommunicationMemory:
    """Agent间通信Memory管理器"""
    
    def __init__(self):
        self.execution_log_manager = execution_log_manager
        self.communication_memory = None
        self._initialized = False
        
        # 内存中的快速访问缓存
        self.agent_contexts: Dict[str, AgentContext] = {}
        self.message_history: List[AgentMessage] = []
        self.agent_dependencies: Dict[str, List[str]] = {}
    
    async def initialize(self):
        """初始化通信Memory系统"""
        if not self._initialized:
            self.communication_memory = memory_config.create_workflow_memory()
            self._initialized = True
            print("🔗 Agent通信Memory系统初始化完成")
    
    # ================================
    # Agent上下文管理
    # ================================
    
    async def update_agent_context(self, 
                                 agent_name: str,
                                 current_task: str,
                                 execution_state: str,
                                 relevant_info: Dict[str, Any] = None,
                                 dependencies: List[str] = None,
                                 outputs: Dict[str, Any] = None):
        """更新Agent上下文"""
        context = AgentContext(
            agent_name=agent_name,
            current_task=current_task,
            execution_state=execution_state,
            relevant_info=relevant_info or {},
            dependencies=dependencies or [],
            outputs=outputs or {},
            timestamp=datetime.now().isoformat()
        )
        
        self.agent_contexts[agent_name] = context
        
        # 存储到向量数据库
        await self._store_context_to_memory(context)
        
        print(f"📝 更新Agent上下文: {agent_name} - {execution_state}")
    
    async def get_agent_context(self, agent_name: str) -> Optional[AgentContext]:
        """获取Agent上下文"""
        return self.agent_contexts.get(agent_name)
    
    async def get_relevant_contexts_for_agent(self, agent_name: str) -> List[AgentContext]:
        """获取与指定Agent相关的其他Agent上下文"""
        relevant_contexts = []
        
        # 获取依赖的Agent上下文
        if agent_name in self.agent_dependencies:
            for dep_agent in self.agent_dependencies[agent_name]:
                if dep_agent in self.agent_contexts:
                    relevant_contexts.append(self.agent_contexts[dep_agent])
        
        # 获取最近完成的Agent上下文
        recent_completed = [
            ctx for ctx in self.agent_contexts.values()
            if ctx.execution_state == "completed" and ctx.agent_name != agent_name
        ]
        
        # 按时间排序，取最近的3个
        recent_completed.sort(key=lambda x: x.timestamp, reverse=True)
        relevant_contexts.extend(recent_completed[:3])
        
        return relevant_contexts
    
    # ================================
    # Agent间消息传递
    # ================================
    
    async def send_message(self,
                         from_agent: str,
                         to_agent: str,
                         message_type: str,
                         content: str,
                         metadata: Dict[str, Any] = None) -> str:
        """发送Agent间消息"""
        message_id = f"{from_agent}_to_{to_agent}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        message = AgentMessage(
            from_agent=from_agent,
            to_agent=to_agent,
            message_type=message_type,
            content=content,
            metadata=metadata or {},
            timestamp=datetime.now().isoformat(),
            message_id=message_id
        )
        
        self.message_history.append(message)
        
        # 存储到向量数据库
        await self._store_message_to_memory(message)
        
        print(f"📨 消息发送: {from_agent} → {to_agent} ({message_type})")
        return message_id
    
    async def get_messages_for_agent(self, 
                                   agent_name: str,
                                   message_type: str = None,
                                   from_agent: str = None,
                                   limit: int = 10) -> List[AgentMessage]:
        """获取发送给指定Agent的消息"""
        messages = [
            msg for msg in self.message_history
            if msg.to_agent == agent_name
        ]
        
        # 过滤条件
        if message_type:
            messages = [msg for msg in messages if msg.message_type == message_type]
        
        if from_agent:
            messages = [msg for msg in messages if msg.from_agent == from_agent]
        
        # 按时间排序，返回最新的
        messages.sort(key=lambda x: x.timestamp, reverse=True)
        return messages[:limit]
    
    async def get_conversation_between_agents(self, 
                                            agent1: str, 
                                            agent2: str,
                                            limit: int = 20) -> List[AgentMessage]:
        """获取两个Agent之间的对话历史"""
        conversation = [
            msg for msg in self.message_history
            if (msg.from_agent == agent1 and msg.to_agent == agent2) or
               (msg.from_agent == agent2 and msg.to_agent == agent1)
        ]
        
        conversation.sort(key=lambda x: x.timestamp)
        return conversation[-limit:]
    
    # ================================
    # 智能上下文推荐
    # ================================
    
    async def get_dependency_outputs(self, agent_name: str) -> Dict[str, Any]:
        """获取依赖Agent的输出结果"""
        dependency_outputs = {}
        
        if agent_name in self.agent_dependencies:
            for dep_agent in self.agent_dependencies[agent_name]:
                if dep_agent in self.agent_contexts:
                    context = self.agent_contexts[dep_agent]
                    if context.outputs:
                        dependency_outputs[dep_agent] = context.outputs
        
        return dependency_outputs
    
    async def suggest_next_actions(self, agent_name: str) -> List[str]:
        """基于上下文建议下一步行动"""
        suggestions = []
        
        # 获取当前Agent上下文
        current_context = await self.get_agent_context(agent_name)
        if not current_context:
            return ["开始执行任务"]
        
        # 检查依赖是否完成
        if current_context.dependencies:
            incomplete_deps = []
            for dep_agent in current_context.dependencies:
                dep_context = await self.get_agent_context(dep_agent)
                if not dep_context or dep_context.execution_state != "completed":
                    incomplete_deps.append(dep_agent)
            
            if incomplete_deps:
                suggestions.append(f"等待依赖Agent完成: {', '.join(incomplete_deps)}")
        
        # 检查是否有错误消息需要处理
        error_messages = await self.get_messages_for_agent(agent_name, message_type="error")
        if error_messages:
            suggestions.append("处理收到的错误信息")
        
        # 检查是否有上下文信息可以利用
        context_messages = await self.get_messages_for_agent(agent_name, message_type="context")
        if context_messages:
            suggestions.append("利用收到的上下文信息")
        
        return suggestions if suggestions else ["继续执行当前任务"]
    
    # ================================
    # 内部存储方法
    # ================================
    
    async def _store_context_to_memory(self, context: AgentContext):
        """将上下文存储到向量数据库"""
        if not self._initialized:
            await self.initialize()
        
        content = f"""
Agent Context: {context.agent_name}
Task: {context.current_task}
State: {context.execution_state}
Timestamp: {context.timestamp}
Relevant Info: {json.dumps(context.relevant_info, ensure_ascii=False)}
Dependencies: {', '.join(context.dependencies)}
Outputs: {json.dumps(context.outputs, ensure_ascii=False)}
        """.strip()
        
        await self.communication_memory.add(
            MemoryContent(
                content=content,
                mime_type=MemoryMimeType.TEXT,
                metadata={
                    "type": "agent_context",
                    "agent_name": context.agent_name,
                    "execution_state": context.execution_state,
                    "timestamp": context.timestamp
                }
            )
        )
    
    async def _store_message_to_memory(self, message: AgentMessage):
        """将消息存储到向量数据库"""
        if not self._initialized:
            await self.initialize()
        
        content = f"""
Message: {message.from_agent} → {message.to_agent}
Type: {message.message_type}
Content: {message.content}
Timestamp: {message.timestamp}
Metadata: {json.dumps(message.metadata, ensure_ascii=False)}
        """.strip()
        
        await self.communication_memory.add(
            MemoryContent(
                content=content,
                mime_type=MemoryMimeType.TEXT,
                metadata={
                    "type": "agent_message",
                    "from_agent": message.from_agent,
                    "to_agent": message.to_agent,
                    "message_type": message.message_type,
                    "message_id": message.message_id,
                    "timestamp": message.timestamp
                }
            )
        )
    
    async def close(self):
        """关闭通信Memory连接"""
        if self.communication_memory:
            await self.communication_memory.close()


# 全局实例
agent_communication_memory = AgentCommunicationMemory()
