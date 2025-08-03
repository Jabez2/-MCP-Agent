"""
基础Memory管理器

提供Agent执行日志存储和检索功能
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
        
        if not success and "failure_reasons" in execution_result:
            content_parts.append(f"Errors: {execution_result['failure_reasons']}")
        
        if success and "analysis" in execution_result:
            content_parts.append(f"Analysis: {execution_result['analysis']}")
        
        content = "\n".join(content_parts)
        
        # 构建metadata - 确保所有值都是ChromaDB支持的类型
        metadata = {
            "agent_name": agent_name,
            "success": success,
            "timestamp": timestamp,
            "duration": duration,
            "task_type": self._classify_task(task_description),
        }

        if context:
            # 处理context中的复杂数据类型
            for key, value in context.items():
                if isinstance(value, (list, dict)):
                    # 将列表和字典转换为字符串
                    metadata[key] = str(value)
                elif isinstance(value, (str, int, float, bool)) or value is None:
                    # 直接支持的类型
                    metadata[key] = value
                else:
                    # 其他类型转换为字符串
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
                                   success_only: bool = False) -> List[MemoryContent]:
        """获取相似的执行记录"""
        if not self._initialized:
            await self.initialize()

        # 构建查询字符串 - 优化中英文混合查询
        if agent_name:
            # 如果指定了agent，使用精确的Agent前缀
            search_query = f"Agent: {agent_name}"
            if query.strip():
                search_query += f" {query}"
        else:
            search_query = query

        try:
            query_result = await self.execution_memory.query(search_query)

            # 处理不同的返回格式
            results = []
            if hasattr(query_result, 'results'):
                # MemoryQueryResult对象
                results = query_result.results
            elif hasattr(query_result, 'memories'):
                # 如果返回的是MemoryQueryResult对象的另一种格式
                results = query_result.memories
            elif isinstance(query_result, list):
                # 如果直接返回列表
                results = query_result
            else:
                # 其他格式，尝试转换
                results = list(query_result) if query_result else []

            print(f"🔍 查询结果: 找到 {len(results)} 条记录")

            # 确保results中的每个元素都是MemoryContent对象
            filtered_results = []
            for i, r in enumerate(results):
                print(f"   结果 {i+1}: 类型={type(r)}")

                if hasattr(r, 'metadata') and hasattr(r, 'content'):
                    # 这是一个有效的MemoryContent对象
                    if success_only and not r.metadata.get("success", False):
                        continue
                    filtered_results.append(r)
                elif isinstance(r, tuple) and len(r) >= 2:
                    # 可能是(content, metadata)的元组格式
                    try:
                        content, metadata = r[0], r[1] if len(r) > 1 else {}
                        if success_only and not metadata.get("success", False):
                            continue
                        # 创建MemoryContent对象
                        memory_content = MemoryContent(
                            content=str(content),
                            mime_type=MemoryMimeType.TEXT,
                            metadata=metadata
                        )
                        filtered_results.append(memory_content)
                    except Exception as e:
                        print(f"⚠️ 处理元组结果失败: {e}")
                else:
                    print(f"⚠️ 跳过无效的查询结果: {type(r)} - {r}")

            return filtered_results

        except Exception as e:
            print(f"⚠️ 查询执行记录时出错: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    async def get_agent_success_patterns(self, agent_name: str) -> List[MemoryContent]:
        """获取特定Agent的成功模式"""
        return await self.get_similar_executions(
            query=f"successful execution patterns",
            agent_name=agent_name,
            success_only=True
        )
    
    async def get_error_solutions(self, error_description: str) -> List[MemoryContent]:
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
            results = await self.get_similar_executions(query=query, success_only=True)
            all_results.extend(results)

        # 去重并返回
        seen_ids = set()
        unique_results = []
        for result in all_results:
            result_id = result.metadata.get('id')
            if result_id and result_id not in seen_ids:
                seen_ids.add(result_id)
                unique_results.append(result)

        return unique_results[:5]  # 返回最多5个结果
    
    def _classify_task(self, task_description: str) -> str:
        """分类任务类型"""
        task_lower = task_description.lower()
        
        if "test" in task_lower:
            return "testing"
        elif "refactor" in task_lower or "fix" in task_lower:
            return "refactoring"
        elif "structure" in task_lower or "organize" in task_lower:
            return "organization"
        elif "scan" in task_lower or "security" in task_lower:
            return "scanning"
        elif "reflect" in task_lower or "review" in task_lower:
            return "reflection"
        else:
            return "general"
    
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
