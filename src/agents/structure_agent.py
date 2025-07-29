"""
项目结构Agent

负责创建完整的项目目录结构和配置文件。
"""

from autogen_agentchat.agents import AssistantAgent


def create_structure_agent(model_client, fs_workbench):
    """创建项目结构Agent"""
    return AssistantAgent(
        name="ProjectStructureAgent",
        description="负责创建完整的项目目录结构和配置文件",
        model_client=model_client,
        workbench=fs_workbench,
        max_tool_iterations=10,
        system_message="""你是一个项目结构设计专家，具有文件操作能力。
        你的任务是：
        1. **读取现有文件**：从 /Users/jabez/output 目录读取已完成的代码文件
        2. **创建项目结构**：在 /Users/jabez/output 目录下创建标准的Python项目结构：
           ```
           /Users/jabez/output/
           ├── string_operations_project/    # 项目根目录
           │   ├── src/                      # 源代码目录
           │   │   └── string_operations.py  # 主要业务代码
           │   ├── tests/                    # 测试目录
           │   │   └── test_string_operations.py  # 测试文件
           │   ├── docs/                     # 文档目录
           │   │   └── README.md             # 项目说明
           │   ├── requirements.txt          # 依赖文件
           │   ├── setup.py                  # 安装配置
           │   ├── .gitignore               # Git忽略文件
           │   └── pyproject.toml           # 项目配置
           ```
        3. **文件组织**：
           - 读取 /Users/jabez/output/string_operations.py 并复制到 src/ 目录
           - 读取 /Users/jabez/output/test_string_operations.py 并复制到 tests/ 目录
        4. 生成项目配置文件：
           - requirements.txt（项目依赖）
           - setup.py（安装脚本）
           - README.md（项目文档）
           - .gitignore（版本控制忽略文件）
           - pyproject.toml（现代Python项目配置）
        5. 创建项目文档，包括：
           - 项目介绍和功能说明
           - 安装和使用指南
           - API文档
           - 开发指南
        6. 生成项目结构报告

        请用中文回复，并在完成项目结构创建后说"PROJECT_STRUCTURE_COMPLETE"。"""
    )
