"""
基础Memory管理器

提供Agent执行日志存储和检索功能
修复了AutoGen ChromaDBVectorMemory查询bug，直接使用ChromaDB查询
"""

import json
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from autogen_core.memory import MemoryContent, MemoryMimeType
from autogen_ext.memory.chromadb import ChromaDBVectorMemory

from .memory_config import memory_config


class ExecutionLogManager:
    """Agent执行日志管理器"""
    
    def __init__(self):
        self.execution_memory: Optional[ChromaDBVectorMemory] = None
        self._initialized = False
    
    async def initialize(self):
        """初始化memory系统"""
        if not self._initialized:
            self.execution_memory = memory_config.create_execution_memory()
            self._initialized = True
    
    async def record_execution(self, 
                             agent_name: str, 
                             task_description: str,
                             execution_result: Dict[str, Any],
                             success: bool,
                             duration: float,
                             context: Optional[Dict[str, Any]] = None):
        """记录Agent执行结果"""
        if not self._initialized:
            await self.initialize()
        
        timestamp = datetime.now().isoformat()
        
        # 构建执行记录内容
        content_parts = [
            f"Agent: {agent_name}",
            f"Task: {task_description}",
            f"Success: {success}",
            f"Duration: {duration:.2f}s",
            f"Timestamp: {timestamp}"
        ]
        
        if execution_result:
            content_parts.append(f"Result: {json.dumps(execution_result, ensure_ascii=False)}")
        
        if context:
            content_parts.append(f"Context: {json.dumps(context, ensure_ascii=False)}")
        
        content = "\n".join(content_parts)
        
        # 构建metadata
        metadata = {
            "agent_name": agent_name,
            "success": success,
            "timestamp": timestamp,
            "duration": duration,
            "task_type": self._classify_task(task_description),
        }

        if context:
            for key, value in context.items():
                if isinstance(value, (list, dict)):
                    metadata[key] = str(value)
                elif isinstance(value, (str, int, float, bool)) or value is None:
                    metadata[key] = value
                else:
                    metadata[key] = str(value)
        
        # 存储到向量数据库
        await self.execution_memory.add(
            MemoryContent(
                content=content,
                mime_type=MemoryMimeType.TEXT,
                metadata=metadata
            )
        )
        
        print(f"📝 记录执行日志: {agent_name} - {'成功' if success else '失败'}")
    
    async def get_similar_executions(self,
                                   query: str,
                                   agent_name: Optional[str] = None,
                                   success_only: bool = False,
                                   top_k: int = 10) -> List[Dict[str, Any]]:
        """获取相似的执行记录"""
        if not self._initialized:
            await self.initialize()

        # 构建查询字符串
        if agent_name:
            search_query = f"Agent: {agent_name}"
            if query.strip():
                search_query += f" {query}"
        else:
            search_query = query

        try:
            # 直接使用ChromaDB查询，绕过AutoGen的bug
            collection = self.execution_memory._collection
            
            # 执行查询
            query_results = collection.query(
                query_texts=[search_query],
                n_results=top_k
            )
            
            # 格式化结果
            results = []
            docs = query_results['documents'][0]
            distances = query_results['distances'][0]
            metadatas = query_results['metadatas'][0]
            ids = query_results['ids'][0]
            
            for doc, dist, meta, doc_id in zip(docs, distances, metadatas, ids):
                # 过滤条件
                if success_only and not meta.get('success', False):
                    continue
                
                if agent_name and meta.get('agent_name') != agent_name:
                    continue
                
                # 创建MemoryContent格式的结果
                result = MemoryContent(
                    content=doc,
                    mime_type=MemoryMimeType.TEXT,
                    metadata={
                        **meta,
                        'id': doc_id,
                        'distance': dist,
                        'similarity': max(0, 1 - dist/100)  # 转换为0-1的相似度分数
                    }
                )
                results.append(result)
            
            print(f"🔍 查询结果: 找到 {len(results)} 条记录")
            return results
            
        except Exception as e:
            print(f"❌ 查询执行记录失败: {e}")
            return []
    
    async def get_error_solutions(self, error_description: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """获取错误解决方案"""
        # 尝试多种查询策略
        queries = [
            f"error solution: {error_description}",
            f"Error: {error_description}",
            error_description,
            f"failure {error_description}"
        ]

        all_results = []
        for query in queries:
            results = await self.get_similar_executions(
                query=query, 
                success_only=True,
                top_k=top_k
            )
            all_results.extend(results)

        # 去重并返回
        seen_ids = set()
        unique_results = []
        for result in all_results:
            result_id = result.metadata.get('id')
            if result_id and result_id not in seen_ids:
                seen_ids.add(result_id)
                unique_results.append(result)

        return unique_results[:top_k]
    
    def _classify_task(self, task_description: str) -> str:
        """分类任务类型"""
        task_lower = task_description.lower()

        if any(keyword in task_lower for keyword in ['代码', 'code', '编程', 'programming']):
            return "代码生成"
        elif any(keyword in task_lower for keyword in ['测试', 'test', '单元测试']):
            return "测试"
        elif any(keyword in task_lower for keyword in ['重构', 'refactor', '优化']):
            return "重构"
        elif any(keyword in task_lower for keyword in ['扫描', 'scan', '检查']):
            return "代码扫描"
        elif any(keyword in task_lower for keyword in ['规划', 'plan', '设计']):
            return "规划设计"
        else:
            return "其他"

    async def close(self):
        """关闭memory连接"""
        if self.execution_memory:
            await self.execution_memory.close()


class AgentStateManager:
    """Agent状态管理器"""

    def __init__(self):
        self.states_path = memory_config.agent_states_path

    async def save_agent_state(self, agent_name: str, state: Dict[str, Any]):
        """保存Agent状态"""
        state_file = memory_config.get_agent_state_path(agent_name)

        # 添加时间戳
        state_with_timestamp = {
            "timestamp": datetime.now().isoformat(),
            "agent_name": agent_name,
            "state": state
        }

        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(state_with_timestamp, f, indent=2, ensure_ascii=False)

        print(f"💾 保存Agent状态: {agent_name}")

    async def load_agent_state(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """加载Agent状态"""
        state_file = memory_config.get_agent_state_path(agent_name)

        if not state_file.exists():
            return None

        try:
            with open(state_file, 'r', encoding='utf-8') as f:
                state_data = json.load(f)

            print(f"📂 加载Agent状态: {agent_name}")
            return state_data.get("state")

        except Exception as e:
            print(f"❌ 加载Agent状态失败 {agent_name}: {e}")
            return None

    def list_saved_states(self) -> List[str]:
        """列出所有已保存的Agent状态"""
        state_files = list(self.states_path.glob("*_state.json"))
        return [f.stem.replace("_state", "") for f in state_files]


# 全局实例
execution_log_manager = ExecutionLogManager()
agent_state_manager = AgentStateManager()
