"""
代码规划Agent

负责分析用户需求并制定详细的实现计划。
"""

from autogen_agentchat.agents import AssistantAgent
from typing import Dict


def create_planning_agent(model_client, fs_workbench, project_config: Dict[str, str] = None):
    """创建代码规划Agent"""
    # 如果没有提供配置，使用占位符
    if not project_config:
        project_config = {
            "main_file_path": "{main_file_path}",
            "test_file_path": "{test_file_path}",
            "project_name": "{project_name}"
        }

    system_message = f"""你是一个代码规划专家。
        你的任务是：
        1. 分析用户的需求
        2. 制定详细的实现计划
        3. 将任务分解为具体的函数需求
        4. 为FunctionWritingAgent提供清晰的指导
        5. **重要**：所有文件都应保存在 /Users/jabez/output 目录下
        6. 明确指定文件名和保存路径，确保后续Agent能找到文件

        **动态文件命名**：
        - 系统会根据任务内容自动生成合适的文件名
        - 你需要在规划中明确指出具体的文件路径
        - 主要代码文件路径：{project_config.get('main_file_path', '/Users/jabez/output/main.py')}
        - 测试文件路径：{project_config.get('test_file_path', '/Users/jabez/output/test_main.py')}
        - 项目名称：{project_config.get('project_name', 'custom_project')}

        在制定计划时，请明确指出上述文件路径，确保后续Agent使用正确的文件名。

        请用中文回复，并在完成规划后说"PLANNING_COMPLETE"。"""

    return AssistantAgent(
        name="CodePlanningAgent",
        description="负责分析需求并制定代码实现计划",
        model_client=model_client,
        workbench=fs_workbench,
        max_tool_iterations=10,
        system_message=system_message
    )
