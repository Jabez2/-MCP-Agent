"""
最小链路入口文件

基于MCP的多链代码生成Agent开发项目 - 最小可用链路版本
包含：规划 → 编码 → 测试生成 → 单元测试 的核心流程
"""

import asyncio
import logging
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from autogen_agentchat.teams import DiGraphBuilder
from autogen_agentchat.conditions import TextMentionTermination, MaxMessageTermination
from autogen_ext.tools.mcp import McpWorkbench

from src.config import create_mcp_servers, create_model_client, get_chain_config
from src.agents.chain_factory import create_agents_by_chain, get_chain_orchestrator_config
from src.core import GraphFlowOrchestrator


# 配置日志 - 隐藏详细的技术日志
logging.basicConfig(
    level=logging.WARNING,  # 只显示警告和错误
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# 禁用第三方库的详细日志
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('autogen_core.events').setLevel(logging.WARNING)
logging.getLogger('autogen_core').setLevel(logging.WARNING)
logging.getLogger('autogen_agentchat').setLevel(logging.WARNING)
logging.getLogger('autogen_ext').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


def create_mcp_server_params():
    """创建MCP服务器参数"""
    try:
        # 创建MCP服务器参数
        filesystem_mcp_server, code_runner_mcp_server = create_mcp_servers()

        logger.info("MCP服务器参数创建成功")
        return filesystem_mcp_server, code_runner_mcp_server

    except Exception as e:
        logger.error(f"创建MCP服务器参数失败: {e}")
        raise


async def create_minimal_graph_and_orchestrator(agents, model_client, chain_name="minimal"):
    """创建最小链路的执行图和编排器"""
    try:
        # 获取链路配置
        chain_config = get_chain_config(chain_name)
        orchestrator_config = get_chain_orchestrator_config(chain_name)
        
        print(f"🔗 配置 {chain_config.description}")
        print(f"📋 Agent流程: {' → '.join(chain_config.agents)}")
        
        # 创建简单的有向图
        builder = DiGraphBuilder()
        
        # 添加所有Agent到图中
        for agent in agents:
            builder.add_node(agent)
        
        # 根据链路配置添加边
        agent_names = [agent.name for agent in agents]
        for i in range(len(agent_names) - 1):
            builder.add_edge(agent_names[i], agent_names[i + 1])
        
        # 添加终止条件
        termination_condition = TextMentionTermination("WORKFLOW_COMPLETE") | MaxMessageTermination(30)
        
        # 构建图
        graph = builder.build()
        
        # 创建编排器，使用链路特定的配置
        orchestrator = GraphFlowOrchestrator(
            graph=graph,
            participants=agents,
            model_client=model_client,
            max_stalls=orchestrator_config["max_stalls"],
            max_retries=orchestrator_config["max_retries"],
            chain_name=chain_name  # 传递链路名称
        )
        
        logger.info(f"最小链路执行图和编排器创建成功")
        return graph, orchestrator
        
    except Exception as e:
        logger.error(f"创建最小链路执行图和编排器失败: {e}")
        raise


async def run_minimal_workflow(task: str, chain_name: str = "minimal"):
    """运行最小链路工作流"""
    try:
        logger.info(f"开始初始化最小链路Agent协作系统...")

        # 1. 创建模型客户端
        model_client = create_model_client()
        logger.info("LLM模型客户端创建成功")

        # 2. 创建MCP服务器参数
        filesystem_mcp_server, code_runner_mcp_server = create_mcp_server_params()

        # 3. 使用上下文管理器创建工作台并运行工作流
        async with McpWorkbench(server_params=filesystem_mcp_server) as fs_workbench:
            async with McpWorkbench(server_params=code_runner_mcp_server) as code_workbench:
                logger.info("MCP工作台创建成功")

                # 4. 根据链路配置创建Agent
                agents = create_agents_by_chain(
                    chain_name=chain_name,
                    fs_workbench=fs_workbench,
                    code_workbench=code_workbench,
                    model_client=model_client
                )
                logger.info(f"成功创建 {len(agents)} 个Agent的最小链路")

                # 5. 创建执行图和编排器
                graph, orchestrator = await create_minimal_graph_and_orchestrator(
                    agents, model_client, chain_name
                )

                # 6. 运行工作流
                print("\n" + "="*80)
                print(f"🚀 基于MCP的多链代码生成Agent系统启动 - {chain_name.upper()} 链路")
                print("="*80)

                # 使用编排器运行任务
                async for event in orchestrator.run_stream(task):
                    # 事件已经通过WorkflowLogger处理，这里不需要额外打印
                    pass

                print("\n" + "="*80)
                print(f"🎉 {chain_name.upper()} 链路协作工作流执行完成")
                print(f"📁 详细日志已保存到: {orchestrator.workflow_logger.get_log_file_path()}")
                print("="*80)

        # 关闭模型客户端
        await model_client.close()

    except Exception as e:
        print(f"\n❌ 执行失败: {e}")
        raise


async def main():
    """主函数"""
    # 默认任务，可以根据需要修改
    default_task = """
    创建一个简单的数学计算工具库，包含以下功能：
    1. 加法、减法、乘法、除法基础运算
    2. 平方根和幂运算
    3. 最大公约数和最小公倍数计算
    
    要求：
    - 使用Python实现
    - 包含基本的错误处理
    - 生成对应的测试用例
    """
    
    try:
        # 可以从命令行参数获取任务和链路类型
        chain_name = "minimal"  # 默认使用最小链路
        task = default_task
        
        if len(sys.argv) > 1:
            # 第一个参数是链路类型
            if sys.argv[1] in ["minimal", "prototype", "quality"]:
                chain_name = sys.argv[1]
                if len(sys.argv) > 2:
                    task = " ".join(sys.argv[2:])
            else:
                # 第一个参数是任务描述
                task = " ".join(sys.argv[1:])
        
        # 显示链路信息
        chain_config = get_chain_config(chain_name)
        print(f"🔗 选择链路: {chain_config.description}")
        print(f"📋 包含Agent: {len(chain_config.agents)} 个")
        print(f"📝 执行任务: {task}")
        print(f"📁 日志将保存到: /Users/jabez/output/logs/")

        # 运行工作流
        await run_minimal_workflow(task, chain_name)

    except KeyboardInterrupt:
        print("\n⚠️ 用户中断执行")
    except Exception as e:
        print(f"\n❌ 程序执行失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # 显示使用说明
    print("🔗 最小链路Agent系统")
    print("使用方法:")
    print("  python minimal_main.py                    # 使用默认任务和最小链路")
    print("  python minimal_main.py minimal '任务描述'  # 指定链路和任务")
    print("  python minimal_main.py prototype '任务'   # 使用快速原型链路")
    print("  python minimal_main.py quality '任务'     # 使用质量保证链路")
    print()
    
    # 运行主程序
    asyncio.run(main())
