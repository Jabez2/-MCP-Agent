"""
链路工厂模块

根据链路配置创建相应的Agent组合，支持不同链路的Agent创建和配置
"""

from typing import List, Dict, Any
from autogen_agentchat.agents import AssistantAgent

from .planning_agent import create_planning_agent
from .coding_agent import create_coding_agent
from .test_agent import create_test_agent
from .unit_test_agent import create_unit_test_agent
from .refactoring_agent import create_refactoring_agent
from .scanning_agent import create_scanning_agent
from .structure_agent import create_structure_agent
from ..config.chain_config import ChainConfig, get_chain_config


class ChainFactory:
    """链路工厂类 - 根据配置创建不同的Agent链路"""
    
    def __init__(self):
        # Agent创建函数映射
        self._agent_creators = {
            "CodePlanningAgent": create_planning_agent, 
            "FunctionWritingAgent": create_coding_agent,
            "TestGenerationAgent": create_test_agent,
            "UnitTestAgent": create_unit_test_agent,
            "RefactoringAgent": create_refactoring_agent,
            "CodeScanningAgent": create_scanning_agent,
            "ProjectStructureAgent": create_structure_agent
        }
    
    def create_agents_for_chain(self, 
                               chain_name: str,
                               fs_workbench,
                               code_workbench, 
                               model_client,
                               project_config: Dict[str, str] = None) -> List[AssistantAgent]:
        """
        根据链路配置创建Agent列表
        
        Args:
            chain_name: 链路名称 ("standard", "minimal", "prototype", "quality")
            fs_workbench: 文件系统工作台
            code_workbench: 代码运行工作台
            model_client: 模型客户端
            project_config: 项目配置（可选）
            
        Returns:
            Agent列表
        """
        # 获取链路配置
        config = get_chain_config(chain_name)
        
        print(f"🔗 创建 {config.description}")
        print(f"📋 包含Agent: {', '.join(config.agents)}")
        
        # 创建Agent列表
        agents = []
        
        for agent_name in config.agents:
            if agent_name not in self._agent_creators:
                raise ValueError(f"未知的Agent类型: {agent_name}")
            
            # 根据Agent类型选择合适的参数
            agent = self._create_single_agent(
                agent_name, 
                fs_workbench, 
                code_workbench, 
                model_client,
                project_config
            )
            
            agents.append(agent)
            print(f"   ✅ 创建 {agent_name}: {agent.description}")
        
        print(f"🎉 成功创建 {len(agents)} 个Agent的 {chain_name} 链路")
        return agents
    
    def _create_single_agent(self, 
                           agent_name: str,
                           fs_workbench,
                           code_workbench,
                           model_client,
                           project_config: Dict[str, str] = None) -> AssistantAgent:
        """创建单个Agent"""
        creator_func = self._agent_creators[agent_name]
        
        # 根据Agent类型传递不同的参数
        if agent_name == "CodePlanningAgent":
            # 规划Agent需要项目配置
            return creator_func(model_client, fs_workbench, project_config)
        elif agent_name == "UnitTestAgent":
            # 单元测试Agent使用代码工作台
            return creator_func(model_client, code_workbench)
        else:
            # 其他Agent使用文件系统工作台
            return creator_func(model_client, fs_workbench)
    
    def get_chain_dependencies(self, chain_name: str) -> Dict[str, List[str]]:
        """获取链路的依赖关系配置"""
        config = get_chain_config(chain_name)
        return config.dependencies
    
    def get_chain_orchestrator_config(self, chain_name: str) -> Dict[str, Any]:
        """获取链路的编排器配置"""
        config = get_chain_config(chain_name)
        return {
            "max_stalls": config.max_stalls,
            "max_retries": config.max_retries,
            "dependencies": config.dependencies
        }
    
    def validate_chain_config(self, chain_name: str) -> bool:
        """验证链路配置的有效性"""
        try:
            config = get_chain_config(chain_name)
            
            # 检查所有Agent是否都有对应的创建函数
            for agent_name in config.agents:
                if agent_name not in self._agent_creators:
                    print(f"❌ 验证失败: 未找到Agent创建函数 {agent_name}")
                    return False
            
            # 检查依赖关系是否有效
            for agent, deps in config.dependencies.items():
                if agent not in config.agents:
                    print(f"❌ 验证失败: 依赖配置中的Agent {agent} 不在链路中")
                    return False
                
                for dep in deps:
                    if dep not in config.agents:
                        print(f"❌ 验证失败: Agent {agent} 依赖的 {dep} 不在链路中")
                        return False
            
            print(f"✅ 链路配置 {chain_name} 验证通过")
            return True
            
        except Exception as e:
            print(f"❌ 验证链路配置失败: {e}")
            return False


# 全局链路工厂实例
chain_factory = ChainFactory()


def create_agents_by_chain(chain_name: str,
                          fs_workbench,
                          code_workbench,
                          model_client,
                          project_config: Dict[str, str] = None) -> List[AssistantAgent]:
    """
    根据链路名称创建Agent的便捷函数
    
    Args:
        chain_name: 链路名称
        fs_workbench: 文件系统工作台
        code_workbench: 代码运行工作台
        model_client: 模型客户端
        project_config: 项目配置
        
    Returns:
        Agent列表
    """
    return chain_factory.create_agents_for_chain(
        chain_name, fs_workbench, code_workbench, model_client, project_config
    )


def get_chain_dependencies(chain_name: str) -> Dict[str, List[str]]:
    """获取链路依赖关系的便捷函数"""
    return chain_factory.get_chain_dependencies(chain_name)


def get_chain_orchestrator_config(chain_name: str) -> Dict[str, Any]:
    """获取链路编排器配置的便捷函数"""
    return chain_factory.get_chain_orchestrator_config(chain_name)


if __name__ == "__main__":
    # 测试代码
    from ..config.chain_config import chain_config_manager
    
    print("🧪 测试链路工厂...")
    
    # 打印所有链路配置
    chain_config_manager.print_chain_summary()
    
    # 验证所有链路配置
    print("\n🔍 验证链路配置...")
    factory = ChainFactory()
    
    for chain_name in ["standard", "minimal", "prototype", "quality"]:
        factory.validate_chain_config(chain_name)
