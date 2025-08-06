"""
链路配置模块

定义不同的Agent链路配置，支持标准链路和最小可用链路
"""

from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class ChainConfig:
    """链路配置数据类"""
    name: str
    description: str
    agents: List[str]
    dependencies: Dict[str, List[str]]
    max_stalls: int = 3
    max_retries: int = 2


class ChainConfigManager:
    """链路配置管理器"""
    
    def __init__(self):
        self._configs = self._initialize_configs()
    
    def _initialize_configs(self) -> Dict[str, ChainConfig]:
        """初始化所有链路配置"""
        configs = {}
        
        # 标准链路配置（7个Agent）
        configs["standard"] = ChainConfig(
            name="standard",
            description="标准完整链路 - 包含规划、编码、测试、重构、扫描、结构化的完整流程",
            agents=[
                "CodePlanningAgent",
                "FunctionWritingAgent", 
                "TestGenerationAgent",
                "UnitTestAgent",
                "RefactoringAgent",
                "CodeScanningAgent",
                "ProjectStructureAgent"
            ],
            dependencies={
                "FunctionWritingAgent": ["CodePlanningAgent"],
                "TestGenerationAgent": ["FunctionWritingAgent"],
                "UnitTestAgent": ["TestGenerationAgent"],
                "RefactoringAgent": ["UnitTestAgent"],
                "CodeScanningAgent": ["UnitTestAgent", "RefactoringAgent"],
                "ProjectStructureAgent": ["CodeScanningAgent"]
            },
            max_stalls=3,
            max_retries=2
        )
        
        # 最小可用链路配置（4个Agent）
        configs["minimal"] = ChainConfig(
            name="minimal",
            description="最小可用链路 - 包含规划、编码、测试、验证的核心流程",
            agents=[
                "CodePlanningAgent",
                "FunctionWritingAgent",
                "TestGenerationAgent", 
                "UnitTestAgent"
            ],
            dependencies={
                "FunctionWritingAgent": ["CodePlanningAgent"],
                "TestGenerationAgent": ["FunctionWritingAgent"],
                "UnitTestAgent": ["TestGenerationAgent"]
            },
            max_stalls=2,
            max_retries=1
        )
        
        # 快速原型链路配置（2个Agent）
        configs["prototype"] = ChainConfig(
            name="prototype",
            description="快速原型链路 - 只包含规划和编码，适合快速概念验证",
            agents=[
                "CodePlanningAgent",
                "FunctionWritingAgent"
            ],
            dependencies={
                "FunctionWritingAgent": ["CodePlanningAgent"]
            },
            max_stalls=1,
            max_retries=1
        )
        
        # 质量保证链路配置（3个Agent）
        configs["quality"] = ChainConfig(
            name="quality",
            description="质量保证链路 - 专注于代码质量检查和验证",
            agents=[
                "FunctionWritingAgent",
                "UnitTestAgent",
                "CodeScanningAgent"
            ],
            dependencies={
                "UnitTestAgent": ["FunctionWritingAgent"],
                "CodeScanningAgent": ["UnitTestAgent"]
            },
            max_stalls=2,
            max_retries=1
        )
        
        return configs
    
    def get_config(self, chain_name: str) -> ChainConfig:
        """获取指定链路配置"""
        if chain_name not in self._configs:
            raise ValueError(f"未知的链路配置: {chain_name}. 可用配置: {list(self._configs.keys())}")
        return self._configs[chain_name]
    
    def list_available_chains(self) -> List[str]:
        """列出所有可用的链路配置"""
        return list(self._configs.keys())
    
    def get_chain_info(self, chain_name: str) -> Dict[str, Any]:
        """获取链路详细信息"""
        config = self.get_config(chain_name)
        return {
            "name": config.name,
            "description": config.description,
            "agent_count": len(config.agents),
            "agents": config.agents,
            "dependencies": config.dependencies,
            "max_stalls": config.max_stalls,
            "max_retries": config.max_retries
        }
    
    def print_chain_summary(self):
        """打印所有链路配置的摘要"""
        print("🔗 可用的Agent链路配置:")
        print("=" * 60)
        
        for chain_name in self.list_available_chains():
            info = self.get_chain_info(chain_name)
            print(f"\n📋 {info['name'].upper()} 链路:")
            print(f"   描述: {info['description']}")
            print(f"   Agent数量: {info['agent_count']}")
            print(f"   流程: {' → '.join(info['agents'])}")
            print(f"   配置: 最大停滞={info['max_stalls']}, 最大重试={info['max_retries']}")


# 全局链路配置管理器实例
chain_config_manager = ChainConfigManager()


def get_chain_config(chain_name: str = "standard") -> ChainConfig:
    """获取链路配置的便捷函数"""
    return chain_config_manager.get_config(chain_name)


def list_chains() -> List[str]:
    """列出可用链路的便捷函数"""
    return chain_config_manager.list_available_chains()


if __name__ == "__main__":
    # 测试代码
    manager = ChainConfigManager()
    manager.print_chain_summary()
