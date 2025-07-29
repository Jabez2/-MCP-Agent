"""
主入口文件

基于MCP的多链代码生成Agent开发项目的主要执行入口。
演示完整的代码生成、测试、验证、反思、重构、质量扫描和项目结构化流程。
"""

import asyncio
import logging
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from autogen_agentchat.teams import DiGraphBuilder
from autogen_agentchat.conditions import TextMentionTermination, MaxMessageTermination
from autogen_agentchat.ui import Console
from autogen_ext.tools.mcp import McpWorkbench

from src.config import create_mcp_servers, create_model_client
from src.agents import create_all_agents
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


async def create_graph_and_orchestrator(agents, model_client):
    """创建执行图和编排器"""
    try:
        # 创建简单的有向图
        builder = DiGraphBuilder()
        
        # 添加所有Agent到图中
        for agent in agents:
            builder.add_node(agent)
        
        # 定义简单的线性流程（可以根据需要调整）
        agent_names = [agent.name for agent in agents]
        for i in range(len(agent_names) - 1):
            builder.add_edge(agent_names[i], agent_names[i + 1])
        
        # 添加终止条件
        termination_condition = TextMentionTermination("WORKFLOW_COMPLETE") | MaxMessageTermination(50)
        
        # 构建图
        graph = builder.build()
        
        # 创建编排器
        orchestrator = GraphFlowOrchestrator(
            graph=graph,
            participants=agents,
            model_client=model_client,
            max_stalls=3,
            max_retries=2
        )
        
        logger.info("执行图和编排器创建成功")
        return graph, orchestrator
        
    except Exception as e:
        logger.error(f"创建执行图和编排器失败: {e}")
        raise


async def run_workflow(task: str):
    """运行完整的工作流"""
    try:
        logger.info("开始初始化多Agent协作系统...")

        # 1. 创建模型客户端
        model_client = create_model_client()
        logger.info("LLM模型客户端创建成功")

        # 2. 创建MCP服务器参数
        filesystem_mcp_server, code_runner_mcp_server = create_mcp_server_params()

        # 3. 使用上下文管理器创建工作台并运行工作流
        async with McpWorkbench(server_params=filesystem_mcp_server) as fs_workbench:
            async with McpWorkbench(server_params=code_runner_mcp_server) as code_workbench:
                logger.info("MCP工作台创建成功")

                # 4. 创建所有Agent
                agents = create_all_agents(fs_workbench, code_workbench, model_client)
                logger.info(f"成功创建 {len(agents)} 个Agent")

                # 5. 创建执行图和编排器
                graph, orchestrator = await create_graph_and_orchestrator(agents, model_client)

                # 6. 运行工作流
                print("\n" + "="*80)
                print("🚀 基于MCP的多链代码生成Agent系统启动")
                print("="*80)

                # 使用编排器运行任务
                async for event in orchestrator.run_stream(task):
                    # 事件已经通过WorkflowLogger处理，这里不需要额外打印
                    pass

                print("\n" + "="*80)
                print("🎉 多Agent协作工作流执行完成")
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
    创建一个字符串操作工具库，包含以下功能：
    1. 字符串反转函数
    2. 字符串去重函数  
    3. 字符串统计函数（统计字符出现次数）
    4. 字符串格式化函数（首字母大写等）
    
    要求：
    - 使用Python实现
    - 包含完整的错误处理
    - 生成完整的测试用例
    - 确保代码质量和可维护性
    """
    
    try:
        # 可以从命令行参数获取任务，或使用默认任务
        if len(sys.argv) > 1:
            task = " ".join(sys.argv[1:])
        else:
            task = default_task
            
        print(f"📋 执行任务: {task}")
        print(f"📝 日志将保存到: /Users/jabez/output/logs/")

        # 运行工作流
        await run_workflow(task)

    except KeyboardInterrupt:
        print("\n⚠️ 用户中断执行")
    except Exception as e:
        print(f"\n❌ 程序执行失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # 运行主程序
    asyncio.run(main())
