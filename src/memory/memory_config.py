"""
Memory系统配置模块

提供统一的memory配置和初始化功能
"""

import os
from pathlib import Path
from typing import Optional

from autogen_ext.memory.chromadb import (
    ChromaDBVectorMemory,
    PersistentChromaDBVectorMemoryConfig,
    SentenceTransformerEmbeddingFunctionConfig,
)


class MemoryConfig:
    """Memory系统配置类"""
    
    def __init__(self, base_path: str = "./memory"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # 不同类型的memory存储路径
        self.execution_logs_path = self.base_path / "execution_logs"
        self.agent_states_path = self.base_path / "agent_states"
        self.workflow_patterns_path = self.base_path / "workflow_patterns"
        
        # 创建目录
        for path in [self.execution_logs_path, self.agent_states_path, self.workflow_patterns_path]:
            path.mkdir(parents=True, exist_ok=True)
    
    def create_execution_memory(self) -> ChromaDBVectorMemory:
        """创建执行日志memory"""
        return ChromaDBVectorMemory(
            config=PersistentChromaDBVectorMemoryConfig(
                collection_name="agent_execution_logs",
                persistence_path=str(self.execution_logs_path),
                k=50,  # 返回最相关的50个结果，增加查询范围
                score_threshold=0.0,  # 设置为0，不过滤任何结果
                distance_metric="cosine",  # 明确指定使用余弦距离
                embedding_function_config=SentenceTransformerEmbeddingFunctionConfig(
                    model_name="paraphrase-multilingual-MiniLM-L12-v2"
                ),
            )
        )
    
    def create_workflow_memory(self) -> ChromaDBVectorMemory:
        """创建工作流模式memory"""
        return ChromaDBVectorMemory(
            config=PersistentChromaDBVectorMemoryConfig(
                collection_name="workflow_patterns",
                persistence_path=str(self.workflow_patterns_path),
                k=3,  # 返回最相关的3个工作流模式
                score_threshold=0.0,  # 设置为0，不过滤任何结果
                distance_metric="cosine",  # 明确指定使用余弦距离
                embedding_function_config=SentenceTransformerEmbeddingFunctionConfig(
                    model_name="paraphrase-multilingual-MiniLM-L12-v2"  # 统一使用中文模型
                ),
            )
        )
    
    def get_agent_state_path(self, agent_name: str) -> Path:
        """获取Agent状态文件路径"""
        return self.agent_states_path / f"{agent_name}_state.json"


# 全局memory配置实例
memory_config = MemoryConfig()
