"""
八Agent协作示例：代码规划 + 函数编写 + 测试用例生成 + 单元测试执行 + 反思规划 + 代码重构 + 代码扫描 + 项目目录生成
演示完整的代码生成、测试、验证、反思、重构、质量扫描和项目结构化流程
使用高级调度系统：结合 GraphFlow 的结构化执行和 MagenticOne 的智能调度

重构版本：代码结构更清晰，功能模块化，保持所有原有功能
"""

# ================================
# 导入和依赖
# ================================
import asyncio
import json
import logging
import os
import re
import sys
import glob
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Sequence, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import DiGraphBuilder, GraphFlow
from autogen_agentchat.conditions import TextMentionTermination, MaxMessageTermination
from autogen_agentchat.ui import Console
from autogen_agentchat.messages import BaseChatMessage, TextMessage, StopMessage
from autogen_agentchat.base import ChatAgent, Response, TaskResult
from autogen_core.models import UserMessage
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.tools.mcp import McpWorkbench, StdioServerParams


# ================================
# 数据结构定义
# ================================

class NodeState(Enum):
    """节点执行状态枚举"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class TaskLedger:
    """任务账本 - 管理全局任务状态和计划"""
    original_task: str = ""
    facts: List[str] = field(default_factory=list)
    guesses: List[str] = field(default_factory=list)
    plan: List[str] = field(default_factory=list)
    agent_capabilities: Dict[str, str] = field(default_factory=dict)
    failed_paths: List[str] = field(default_factory=list)

    # 新增：动态文件命名配置
    project_config: Dict[str, str] = field(default_factory=dict)

    def update_facts(self, new_facts: List[str]):
        """更新已确认的事实"""
        self.facts.extend(new_facts)

    def update_plan(self, new_plan: List[str]):
        """更新执行计划"""
        self.plan = new_plan

    def set_project_config(self, project_name: str, main_file: str, test_file: str, base_dir: str = "/Users/jabez/output"):
        """设置项目配置信息"""
        self.project_config = {
            "project_name": project_name,
            "main_file": main_file,
            "test_file": test_file,
            "base_dir": base_dir,
            "main_file_path": f"{base_dir}/{main_file}",
            "test_file_path": f"{base_dir}/{test_file}"
        }

    def get_file_path(self, file_type: str) -> str:
        """获取文件路径"""
        if file_type == "main":
            return self.project_config.get("main_file_path", "/Users/jabez/output/main.py")
        elif file_type == "test":
            return self.project_config.get("test_file_path", "/Users/jabez/output/test_main.py")
        else:
            return f"{self.project_config.get('base_dir', '/Users/jabez/output')}/{file_type}"

    def get_intelligent_path_resolver(self):
        """获取智能路径解析器"""
        return IntelligentPathResolver(self.project_config, self.facts, self.plan)


@dataclass
class ProgressLedger:
    """进度账本 - 管理执行进度和状态跟踪"""
    node_states: Dict[str, NodeState] = field(default_factory=dict)
    execution_history: List[Dict[str, Any]] = field(default_factory=list)
    current_active_nodes: Set[str] = field(default_factory=set)
    stall_count: int = 0
    retry_counts: Dict[str, int] = field(default_factory=dict)

    def update_node_state(self, node_name: str, state: NodeState):
        """更新节点状态并记录历史"""
        self.node_states[node_name] = state
        self.execution_history.append({
            "node": node_name,
            "state": state.value,
            "timestamp": asyncio.get_event_loop().time()
        })

    def increment_retry(self, node_name: str) -> int:
        """增加重试计数并返回当前计数"""
        self.retry_counts[node_name] = self.retry_counts.get(node_name, 0) + 1
        return self.retry_counts[node_name]


# ================================
# 配置函数
# ================================

def create_mcp_servers():
    """创建和配置MCP服务器参数"""
    filesystem_mcp_server = StdioServerParams(
        command="node",
        args=[
            "/Users/jabez/Nutstore Files/multiAgent/mcp_services/filesystem-mcp-server/dist/index.js",
            "/Users"
        ],
        env={
            "FS_BASE_DIRECTORY": "/Users"
        }
    )

    code_runner_mcp_server = StdioServerParams(
        command="npx",
        args=[
            "-y",
            "mcp-server-code-runner@latest"
        ]
    )
    
    return filesystem_mcp_server, code_runner_mcp_server


def create_model_client():
    """创建LLM模型客户端"""
    from autogen_core.models import ModelInfo
    model_info = ModelInfo(
        family="openai",
        vision=False,
        function_calling=True,
        json_output=True
    )
    return OpenAIChatCompletionClient(
        model="Qwen/Qwen3-Coder-480B-A35B-Instruct",
        api_key="ms-d00638ea-e181-40b9-9fba-8047d018acf0",
        base_url="https://api-inference.modelscope.cn/v1/",
        model_info=model_info,
        temperature=0.7,
        top_p=0.8,
        extra_body={"top_k": 20, "repetition_penalty": 1.05}
    )

# ================================
# Agent创建函数
# ================================

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


def create_coding_agent(model_client, fs_workbench):
    """创建函数编写Agent"""
    return AssistantAgent(
        name="FunctionWritingAgent",
        description="负责根据规划编写具体的Python函数代码并保存到文件",
        model_client=model_client,
        workbench=fs_workbench,
        max_tool_iterations=10,
        system_message="""你是一个Python代码编写专家，具有文件操作能力。
        你的任务是：
        1. 根据规划Agent的指导编写Python函数
        2. 确保代码简洁、可读、有注释
        3. 包含必要的错误处理
        4. **重要**：将代码保存到 /Users/jabez/output/文件夹中
        5. 你只负责编写业务逻辑代码，绝对不要编写测试代码(重要限制，如test_*.py，测试代码由TestGenerationAgent实现并保存)
        6. 绝对不要编写测试代码(如test_*.py文件)
        7. 如果规划中要求你写测试代码，请忽略该部分
        8. **文件路径**：必须使用完整路径 /Users/jabez/output/
        9. 测试代码由TestGenerationAgent负责

        **文件保存要求**：
        - 使用write_file工具
        - 文件路径：/Users/jabez/output/
        - 确保文件成功保存，以便后续Agent能够读取

        你可以使用文件系统工具来创建和保存代码文件。
        请用中文回复，并在完成编写后说"CODING_COMPLETE"。"""
    )


def create_test_agent(model_client, fs_workbench):
    """创建测试用例生成Agent"""
    return AssistantAgent(
        name="TestGenerationAgent",
        description="负责为已编写的函数生成完整的测试用例并保存到文件",
        model_client=model_client,
        workbench=fs_workbench,
        max_tool_iterations=10,
        system_message="""你是一个Python测试专家，具有文件操作能力，负责为FunctionWritingAgents生成的代码编写测试文件

        ⚠️ 重要限制：
        - 你绝对不能修改、重写或覆盖任何业务逻辑代码文件（如string_operations.py等）
        - 你只能创建新的测试文件（test_*.py格式）
        - 如果需要读取业务代码，使用read_file工具
        - 如果发现业务代码有问题，只能在测试文件中注释说明，不能修改业务代码

        你的任务是：
        1. **读取源代码**：使用read_file工具读取 /Users/jabez/output/ 目录下的业务逻辑代码文件
        2. 分析函数的功能和参数
        3. 生成全面的测试用例，包括：
           - 正常情况测试
           - 边界条件测试
           - 异常情况测试
           - 输入验证测试
        4. 使用unittest框架编写测试代码
        5. **保存测试文件**：使用write_file工具将测试代码保存到 /Users/jabez/output/test_*.py 文件中
        6. 确保测试代码可以直接运行
        7. 测试代码中要根据实际的业务代码异常类型编写正确的断言

        **文件路径要求**：
        - 读取源代码：/Users/jabez/output/
        - 保存测试文件：/Users/jabez/output/test_*.py

        ⚠️ 重要提醒：你必须生成并保存测试文件，不能只分析代码而不保存！

        你可以使用文件系统工具来读取代码文件和保存测试文件。
        请用中文回复，并在完成测试生成后说"TESTING_COMPLETE"。"""
    )


def create_unit_test_agent(model_client, code_workbench):
    """创建单元测试执行Agent - 支持运行时智能路径解析"""

    return AssistantAgent(
        name="UnitTestAgent",
        description="负责执行测试用例并生成测试报告",
        model_client=model_client,
        workbench=code_workbench,
        max_tool_iterations=5,
        system_message="""你是一个Python单元测试执行专家，具有代码运行能力和智能路径解析能力。

        ⚠️ 重要限制：
        - 你绝对不能创建、修改或重写任何代码文件
        - 你只能使用run-code工具执行代码，可以使用save_test_report工具保存测试报告
        - 你的任务仅限于执行测试和生成报告

        🎯 **智能执行步骤**：
        1. **智能路径发现和设置**：
        ```python
        import os
        import sys
        import glob
        from pathlib import Path

        print("🔍 开始智能路径解析...")

        # 1. 发现可能的项目根目录
        base_dirs = ['/Users/jabez/output']
        possible_roots = []

        for base_dir in base_dirs:
            if os.path.exists(base_dir):
                # 直接使用base_dir
                possible_roots.append(base_dir)

                # 查找子目录中的项目
                for item in os.listdir(base_dir):
                    item_path = os.path.join(base_dir, item)
                    if os.path.isdir(item_path):
                        possible_roots.append(item_path)

        print(f"🔍 发现可能的项目根目录: {possible_roots}")

        # 2. 智能选择最佳工作目录
        best_working_dir = None
        project_structure = {}

        for root in possible_roots:
            # 扫描目录结构
            structure = {
                'test_files': [],
                'main_files': [],
                'utils_dir': None,
                'python_files': []
            }

            try:
                path = Path(root)

                # 查找测试文件
                for pattern in ['test_*.py', '*_test.py']:
                    structure['test_files'].extend([str(f) for f in path.rglob(pattern)])

                # 查找主文件
                for pattern in ['file_processor.py', 'main.py', '*.py']:
                    matches = list(path.glob(pattern))
                    structure['main_files'].extend([str(f) for f in matches if not f.name.startswith('test_')])

                # 查找utils目录
                utils_dirs = list(path.glob('**/utils'))
                if utils_dirs:
                    structure['utils_dir'] = str(utils_dirs[0])

                # 统计Python文件
                structure['python_files'] = [str(f) for f in path.rglob('*.py')]

                print(f"📁 {root} 结构: 测试文件{len(structure['test_files'])}个, 主文件{len(structure['main_files'])}个, utils目录{'有' if structure['utils_dir'] else '无'}")

                # 评分：测试文件多的目录优先
                score = len(structure['test_files']) * 10 + len(structure['main_files']) * 5
                if structure['utils_dir']:
                    score += 20

                if score > 0 and (best_working_dir is None or score > project_structure.get('score', 0)):
                    best_working_dir = root
                    project_structure = structure
                    project_structure['score'] = score

            except Exception as e:
                print(f"⚠️ 扫描目录 {root} 失败: {e}")

        # 3. 设置工作目录和路径
        if best_working_dir:
            try:
                os.chdir(best_working_dir)
                print(f"✅ 切换到最佳工作目录: {best_working_dir}")
            except Exception as e:
                print(f"⚠️ 切换工作目录失败: {e}")

        # 4. 配置Python路径
        project_paths = [
            best_working_dir or '/Users/jabez/output',
            '/Users/jabez/output',
            os.getcwd()
        ]

        for path in project_paths:
            if path and os.path.exists(path) and path not in sys.path:
                sys.path.insert(0, path)
                print(f"✅ 添加路径到sys.path: {path}")

        print(f"📂 当前工作目录: {os.getcwd()}")
        print(f"🔍 Python路径前3个: {sys.path[:3]}")
        print(f"📊 项目结构评分: {project_structure.get('score', 0)}")
        ```

        2. **智能测试文件发现和执行**：
        ```python
        # 使用之前发现的项目结构中的测试文件
        test_files = project_structure.get('test_files', [])

        if not test_files:
            print("🔍 项目结构中未发现测试文件，进行深度搜索...")
            # 深度搜索策略
            search_dirs = [os.getcwd(), '/Users/jabez/output']

            for search_dir in search_dirs:
                if os.path.exists(search_dir):
                    for root, dirs, files in os.walk(search_dir):
                        for file in files:
                            if (file.startswith('test_') or file.endswith('_test.py')) and file.endswith('.py'):
                                full_path = os.path.join(root, file)
                                if full_path not in test_files:
                                    test_files.append(full_path)

        print(f"🧪 最终发现的测试文件: {test_files}")

        if not test_files:
            print("❌ 未找到任何测试文件！")
            print("📋 请检查以下位置是否存在测试文件:")
            print("   - 当前目录下的 test_*.py 文件")
            print("   - /Users/jabez/output/ 目录下的测试文件")
            print("   - 项目子目录中的测试文件")
        ```

        3. **执行测试并生成报告**：
        ```python
        import unittest
        import importlib.util

        all_results = []

        for test_file in test_files:
            try:
                print(f"\\n🧪 执行测试文件: {{test_file}}")

                # 动态导入测试模块
                module_name = os.path.splitext(os.path.basename(test_file))[0]
                spec = importlib.util.spec_from_file_location(module_name, test_file)
                test_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(test_module)

                # 执行测试
                loader = unittest.TestLoader()
                suite = loader.loadTestsFromModule(test_module)
                runner = unittest.TextTestRunner(verbosity=2)
                result = runner.run(suite)

                all_results.append((test_file, result))

            except Exception as e:
                print(f"❌ 执行测试文件 {{test_file}} 失败: {{e}}")
                import traceback
                traceback.print_exc()

        # 生成综合报告
        total_tests = sum(r.testsRun for _, r in all_results)
        total_failures = sum(len(r.failures) for _, r in all_results)
        total_errors = sum(len(r.errors) for _, r in all_results)
        passed_tests = total_tests - total_failures - total_errors

        print(f"\\n=== 综合测试报告 ===")
        print(f"总测试数: {{total_tests}}")
        print(f"通过: {{passed_tests}}")
        print(f"失败: {{total_failures}}")
        print(f"错误: {{total_errors}}")
        if total_tests > 0:
            print(f"成功率: {{(passed_tests/total_tests)*100:.1f}}%")
        ```

        4. **保存测试报告**：使用save_test_report工具保存详细的测试报告
        5. **故障排除**：如果测试失败，提供详细的错误信息和解决建议

        💡 **智能故障排除**：
        - 如果导入失败，检查模块路径和文件是否存在
        - 如果测试执行失败，检查依赖是否安装
        - 提供详细的错误信息和解决建议

        请用中文回复，并在完成测试执行后说"UNIT_TESTING_COMPLETE"。"""
    )


def create_reflection_agent(model_client):
    """创建反思规划Agent"""
    return AssistantAgent(
        name="ReflectionAgent",
        description="负责分析整个开发流程的结果并提供反思和建议",
        model_client=model_client,
        max_tool_iterations=10,
        system_message="""你是一个项目反思和质量评估专家。
        你的任务是：
        1. 分析整个开发流程的执行结果
        2. 评估代码质量、测试覆盖率和项目完成度
        3. 识别开发过程中的问题和改进点
        4. 根据测试结果决定下一步行动：
           - 如果测试全部通过：生成项目完成报告
           - 如果测试部分失败：分析失败原因，提供修复建议
           - 如果测试全部失败：建议重新规划或重写代码
        5. 提供项目质量总结和改进建议
        6. 总结整个开发流程的经验和教训

        请用中文回复，并在完成反思分析后说"REFLECTION_COMPLETE"。"""
    )


def create_refactoring_agent(model_client, fs_workbench):
    """创建代码重构Agent"""
    return AssistantAgent(
        name="RefactoringAgent",
        description="负责根据反思建议对代码进行重构和优化",
        model_client=model_client,
        workbench=fs_workbench,
        max_tool_iterations=10,
        system_message="""你是一个代码重构和智能修复专家，具有文件操作能力。

        **主要职责**：
        1. **智能错误修复**：当单元测试失败时，分析测试错误并修复代码
        2. **代码重构优化**：根据代码质量建议进行结构优化

        **错误修复流程**：
        1. 读取 /Users/jabez/output/string_operations.py（业务代码）和 /Users/jabez/output/test_string_operations.py（测试代码）
        2. 分析测试失败的具体原因：
           - 函数名不匹配
           - 参数类型错误
           - 返回值格式错误
           - 逻辑实现错误
           - 异常处理不当
        3. **智能选择修复策略**：
           - 如果是业务代码问题：修复 string_operations.py
           - 如果是测试代码问题：修复 test_string_operations.py
           - 如果是接口不匹配：同时调整两个文件
        4. 保存修复后的文件，确保测试能够通过

        **重构优化流程**：
        1. 代码结构优化（函数拆分、模块化）
        2. 变量和函数命名改进
        3. 代码注释和文档完善
        4. 性能优化和错误处理增强

        **重要原则**：
        - 优先修复功能性错误，确保测试通过
        - 保持代码的核心功能不变
        - 生成详细的修复报告，说明具体改动

        **文件操作**：
        - 使用 read_file 读取现有代码
        - 使用 write_file 保存修复后的代码
        - 确保文件路径正确：/Users/jabez/output/string_operations.py 和 /Users/jabez/output/test_string_operations.py

        请用中文回复，并在完成修复后说"REFACTORING_COMPLETE"。"""
    )


def create_scanning_agent(model_client, fs_workbench):
    """创建代码扫描Agent"""
    return AssistantAgent(
        name="CodeScanningAgent",
        description="负责对代码进行静态分析和质量扫描",
        model_client=model_client,
        workbench=fs_workbench,
        max_tool_iterations=10,
        system_message="""你是一个代码静态分析和质量扫描专家，具有文件操作能力。
        你的任务是：
        1. **读取代码文件**：使用read_file工具读取 /Users/jabez/output/ 目录下的所有Python代码文件
        2. 使用Python内置工具进行代码分析：
           - 使用ast模块分析代码结构和复杂度
           - 计算函数长度、嵌套深度、圈复杂度
           - 分析导入依赖和函数调用关系
           - 检查命名规范和代码风格
        3. 检测常见的代码问题：
           - 过长的函数（超过50行）
           - 过深的嵌套（超过4层）
           - 重复的代码模式
           - 不规范的命名（如单字母变量、拼音命名等）
           - 缺少文档字符串的函数
           - 未使用的导入模块
        4. 计算代码质量指标：
           - 代码行数统计（总行数、有效代码行数、注释行数）
           - 函数复杂度评分
           - 代码可读性评分
           - 维护性指数
        5. 生成详细的代码扫描报告，包括：
           - 代码质量总体评分
           - 发现的问题列表及严重程度
           - 改进建议和最佳实践推荐
           - 与行业标准的对比分析

        请用中文回复，并在完成扫描后说"SCANNING_COMPLETE"。"""
    )


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


def create_all_agents(fs_workbench, code_workbench, model_client):
    """创建所有Agent并返回列表"""
    agents = [
        create_planning_agent(model_client, fs_workbench),
        create_coding_agent(model_client, fs_workbench),
        create_test_agent(model_client, fs_workbench),
        create_unit_test_agent(model_client, code_workbench),  # 路径解析器将在运行时动态提供
        create_reflection_agent(model_client),
        create_refactoring_agent(model_client, fs_workbench),
        create_scanning_agent(model_client, fs_workbench),
        create_structure_agent(model_client, fs_workbench)
    ]
    return agents


# ================================
# 动态文件命名系统
# ================================

async def parse_task_and_generate_config(task: str, model_client) -> Dict[str, str]:
    """
    解析任务并生成动态文件配置

    Args:
        task: 用户任务描述
        model_client: LLM客户端

    Returns:
        包含项目配置的字典
    """

    parsing_prompt = f"""
    分析以下任务，提取项目信息并生成合适的文件命名：

    任务：{task}

    请分析任务内容，确定：
    1. 项目类型和主题
    2. 合适的项目名称（英文，下划线分隔）
    3. 主代码文件名（.py结尾）
    4. 测试文件名（test_开头，.py结尾）

    请按以下JSON格式返回，只返回JSON，不要其他内容：
    {{
        "project_name": "项目名称",
        "main_file": "主文件名.py",
        "test_file": "test_主文件名.py",
        "description": "项目描述"
    }}

    示例：
    - 如果任务是"创建字符串操作工具库" -> {{"project_name": "string_utils", "main_file": "string_operations.py", "test_file": "test_string_operations.py"}}
    - 如果任务是"开发数学计算库" -> {{"project_name": "math_utils", "main_file": "math_calculator.py", "test_file": "test_math_calculator.py"}}
    - 如果任务是"构建文件处理工具" -> {{"project_name": "file_utils", "main_file": "file_processor.py", "test_file": "test_file_processor.py"}}
    """

    try:
        from autogen_core.models import UserMessage
        response = await model_client.create([
            UserMessage(content=parsing_prompt, source="task_parser")
        ])

        # 解析JSON响应
        import json
        from autogen_core.utils import extract_json_from_str

        response_content = response.content.strip()
        json_objects = extract_json_from_str(response_content)

        if json_objects:
            config = json_objects[0]
            return config
        else:
            # 如果解析失败，返回默认配置
            return get_default_project_config(task)

    except Exception as e:
        print(f"⚠️ 任务解析失败，使用默认配置: {e}")
        return get_default_project_config(task)


def get_default_project_config(task: str) -> Dict[str, str]:
    """根据任务关键词生成默认配置"""
    task_lower = task.lower()

    # 基于关键词的简单映射
    if "字符串" in task or "string" in task_lower:
        return {
            "project_name": "string_utils",
            "main_file": "string_operations.py",
            "test_file": "test_string_operations.py",
            "description": "字符串操作工具库"
        }
    elif "数学" in task or "math" in task_lower or "计算" in task:
        return {
            "project_name": "math_utils",
            "main_file": "math_calculator.py",
            "test_file": "test_math_calculator.py",
            "description": "数学计算库"
        }
    elif "文件" in task or "file" in task_lower:
        return {
            "project_name": "file_utils",
            "main_file": "file_processor.py",
            "test_file": "test_file_processor.py",
            "description": "文件处理工具"
        }
    elif "网络" in task or "network" in task_lower or "http" in task_lower:
        return {
            "project_name": "network_utils",
            "main_file": "network_client.py",
            "test_file": "test_network_client.py",
            "description": "网络工具库"
        }
    else:
        # 通用默认配置
        return {
            "project_name": "custom_utils",
            "main_file": "main_module.py",
            "test_file": "test_main_module.py",
            "description": "自定义工具库"
        }


# ================================
# 核心编排器类
# ================================

class GraphFlowOrchestrator:
    """
    高级图流程编排器 - 结合 GraphFlow 和 MagenticOne 的智能调度

    这个类负责：
    1. 任务分解和计划制定（外层循环）
    2. 智能执行和监控（内层循环）
    3. 节点选择和状态管理
    4. 执行结果分析和错误处理
    """

    def __init__(self, graph, participants: List[ChatAgent], model_client, max_stalls: int = 3, max_retries: int = 2):
        """
        初始化编排器

        Args:
            graph: 执行图结构
            participants: 参与的Agent列表
            model_client: LLM模型客户端
            max_stalls: 最大停滞次数
            max_retries: 最大重试次数
        """
        self.graph = graph
        self.participants = {agent.name: agent for agent in participants}
        self.model_client = model_client
        self.max_stalls = max_stalls
        self.max_retries = max_retries

        # MagenticOne 风格的状态管理
        self.task_ledger = TaskLedger()
        self.progress_ledger = ProgressLedger()

        # 智能路径解析器（延迟初始化）
        self.path_resolver = None

        # 初始化节点状态
        for node_name in self.participants.keys():
            self.progress_ledger.node_states[node_name] = NodeState.NOT_STARTED

        # 分析 Agent 能力
        self._analyze_agent_capabilities()

    def _analyze_agent_capabilities(self):
        """分析并记录每个Agent的能力描述"""
        for name, agent in self.participants.items():
            self.task_ledger.agent_capabilities[name] = agent.description

    def _initialize_path_resolver(self):
        """初始化智能路径解析器"""
        if self.path_resolver is None:
            self.path_resolver = self.task_ledger.get_intelligent_path_resolver()

            # 生成路径解析报告
            report = self.path_resolver.generate_path_report()
            print("🔍 智能路径解析初始化完成")
            print(report)

        return self.path_resolver

    # ================================
    # 外层循环：任务规划和分解
    # ================================

    async def run_stream(self, task: str):
        """
        运行高级调度的工作流

        Args:
            task: 要执行的任务描述

        Yields:
            执行过程中的事件和结果
        """
        self.task_ledger.original_task = task

        # 外层循环：任务分解和计划制定
        await self._outer_loop_planning(task)

        # 内层循环：智能执行和监控
        async for event in self._inner_loop_execution():
            yield event

    async def _outer_loop_planning(self, task: str):
        """
        外层循环：任务分解和计划制定

        这个方法负责：
        1. 解析任务并生成动态文件配置
        2. 分析任务并收集相关事实
        3. 制定详细的执行计划
        4. 为内层循环准备执行环境
        """
        print(f"\n🧠 【任务规划阶段】")
        print(f"原始任务: {task}")

        # 0. 动态文件命名配置
        print(f"\n🔧 解析任务并生成文件配置...")
        project_config = await parse_task_and_generate_config(task, self.model_client)

        # 设置项目配置到任务账本
        self.task_ledger.set_project_config(
            project_config["project_name"],
            project_config["main_file"],
            project_config["test_file"]
        )

        print(f"📁 项目配置:")
        print(f"   项目名称: {project_config['project_name']}")
        print(f"   主文件: {self.task_ledger.get_file_path('main')}")
        print(f"   测试文件: {self.task_ledger.get_file_path('test')}")

        # 1. 收集和分析事实
        facts_prompt = f"""
        分析以下任务并收集相关事实：

        任务：{task}

        项目配置：
        - 项目名称：{project_config['project_name']}
        - 主文件路径：{self.task_ledger.get_file_path('main')}
        - 测试文件路径：{self.task_ledger.get_file_path('test')}

        请列出：
        1. 任务中明确给出的事实
        2. 需要查找的信息
        3. 需要推导的信息
        4. 基于经验的推测

        可用的 Agent 团队：
        {self._format_team_description()}
        """

        # 使用 LLM 分析任务
        response = await self.model_client.create([
            UserMessage(content=facts_prompt, source="orchestrator")
        ])

        facts_analysis = response.content
        self.task_ledger.facts = [facts_analysis]

        print(f"\n📋 事实分析结果:")
        print(f"{facts_analysis}")

        # 2. 制定执行计划
        plan_prompt = f"""
        基于以下信息制定详细的执行计划：

        任务：{task}
        事实分析：{facts_analysis}

        项目配置：
        - 主文件路径：{self.task_ledger.get_file_path('main')}
        - 测试文件路径：{self.task_ledger.get_file_path('test')}

        可用 Agent：
        {self._format_team_description()}

        请制定一个步骤清晰的执行计划，说明每个 Agent 的具体任务和文件路径。
        """

        response = await self.model_client.create([
            UserMessage(content=plan_prompt, source="orchestrator")
        ])

        plan_content = response.content
        self.task_ledger.plan = [plan_content]

        print(f"📊 执行计划:")
        print(f"{plan_content}")
        print(f"\n✅ 规划完成，开始执行\n")

    def _format_team_description(self) -> str:
        """格式化团队描述，用于LLM分析"""
        descriptions = []
        for name, description in self.task_ledger.agent_capabilities.items():
            descriptions.append(f"{name}: {description}")
        return "\n".join(descriptions)

    # ================================
    # 内层循环：智能执行和监控
    # ================================

    async def _inner_loop_execution(self):
        """
        内层循环：智能执行和监控

        这个方法负责：
        1. 获取可执行的节点
        2. 智能选择下一个执行节点
        3. 监控执行结果
        4. 处理错误和重试逻辑
        """
        print(f"\n🔄 【开始执行】")

        # 获取起始节点
        current_nodes = self._get_source_nodes()
        execution_round = 0

        while current_nodes and self.progress_ledger.stall_count < self.max_stalls:
            execution_round += 1

            # 智能选择下一个要执行的节点
            next_node = await self._intelligent_node_selection(current_nodes)

            if not next_node:
                break

            print(f"\n{'='*60}")
            print(f"🎯 执行 Agent: {next_node}")
            print(f"{'='*60}")

            # 执行节点并监控
            execution_result = await self._execute_node_with_monitoring(next_node)

            # 检查是否需要重新选择 Agent
            if execution_result.get("needs_reselection", False):
                print(f"🔄 重新选择 Agent，移除失败的 {next_node}")
                alternative_nodes = await self._find_alternative_nodes(next_node)
                if alternative_nodes:
                    current_nodes = alternative_nodes
                    print(f"🎯 选择替代节点: {current_nodes}")
                    continue
                else:
                    print(f"⚠️ 无替代节点，继续原流程")

            # 检查是否需要重新规划
            if await self._should_replan():
                print(f"\n🔄 检测到需要重新规划，重新分析任务...")
                await self._outer_loop_planning(self.task_ledger.original_task)
                current_nodes = self._get_source_nodes()
                continue

            # 获取下一批可执行节点
            current_nodes = await self._get_next_executable_nodes(next_node, execution_result)

            # 产出执行事件
            yield TextMessage(
                source=next_node,
                content=f"节点 {next_node} 执行完成"
            )

        print(f"\n🏁 执行完成，共 {execution_round} 轮")

        # 生成最终结果
        yield await self._generate_final_result()

    def _get_source_nodes(self) -> List[str]:
        """获取图的源节点（入度为0的节点）"""
        # 简化实现：返回第一个节点作为起始点
        return ["CodePlanningAgent"]

    # ================================
    # 智能节点选择和分析
    # ================================

    async def _intelligent_node_selection(self, candidate_nodes: List[str]) -> Optional[str]:
        """
        智能节点选择算法 - 基于 MagenticOne 的进度账本分析

        Args:
            candidate_nodes: 候选节点列表

        Returns:
            选中的节点名称，如果没有合适的节点则返回None
        """
        if not candidate_nodes:
            return None

        # 如果只有一个候选，使用进度账本分析生成具体指令
        if len(candidate_nodes) == 1:
            selected_node = candidate_nodes[0]
            instruction = await self._generate_specific_instruction(selected_node)
            print(f"📋 执行指令: {instruction}")

            # 存储指令供后续使用
            self.progress_ledger.current_active_nodes = {selected_node}
            if not hasattr(self.progress_ledger, 'node_instructions'):
                self.progress_ledger.node_instructions = {}
            self.progress_ledger.node_instructions[selected_node] = instruction

            return selected_node

        # 使用 MagenticOne 风格的进度账本分析
        progress_analysis = await self._analyze_progress_ledger(candidate_nodes)

        selected_node = progress_analysis.get('next_speaker', {}).get('answer')
        instruction = progress_analysis.get('instruction_or_question', {}).get('answer', '')

        # 验证选择是否有效
        if selected_node in candidate_nodes:
            print(f"📋 执行指令: {instruction}")

            # 存储指令
            self.progress_ledger.current_active_nodes = {selected_node}
            if not hasattr(self.progress_ledger, 'node_instructions'):
                self.progress_ledger.node_instructions = {}
            self.progress_ledger.node_instructions[selected_node] = instruction

            return selected_node
        else:
            return candidate_nodes[0]

    async def _analyze_progress_ledger(self, candidate_nodes: List[str]) -> Dict[str, Any]:
        """
        分析进度账本 - 基于 MagenticOne 的实现

        Args:
            candidate_nodes: 候选节点列表

        Returns:
            包含分析结果的字典
        """
        # 构建对话历史
        conversation_history = self._build_conversation_history()

        # 构建进度账本分析提示
        progress_prompt = f"""
        回顾我们正在处理的以下请求：

        {self.task_ledger.original_task}

        我们已经组建了以下团队：

        {self._format_team_description()}

        为了在请求上取得进展，请回答以下问题，包括必要的推理：

        - 请求是否已完全满足？（如果完成则为 True，如果原始请求尚未成功且完全解决则为 False）
        - 我们是否陷入了重复相同请求和/或获得相同响应的循环？循环可以跨越多个回合
        - 我们是否在取得前进进展？（如果刚开始或最近的消息正在增加价值则为 True。如果最近的消息显示陷入循环或存在重大成功障碍的证据则为 False）
        - 谁应该下一个发言？（从以下选择：{', '.join(candidate_nodes)}）
        - 你会给这个团队成员什么指令或问题？（直接对他们说话，并包含他们可能需要的任何具体信息）

        对话历史：
        {conversation_history}

        请按照以下 JSON 格式输出答案。JSON 对象必须可以直接解析。只输出 JSON，不要偏离此模式：

        {{
           "is_request_satisfied": {{
                "reason": "string",
                "answer": boolean
            }},
            "is_in_loop": {{
                "reason": "string",
                "answer": boolean
            }},
            "is_progress_being_made": {{
                "reason": "string",
                "answer": boolean
            }},
            "next_speaker": {{
                "reason": "string",
                "answer": "string (从候选中选择: {', '.join(candidate_nodes)})"
            }},
            "instruction_or_question": {{
                "reason": "string",
                "answer": "string"
            }}
        }}
        """

        try:
            response = await self.model_client.create([
                UserMessage(content=progress_prompt, source="orchestrator")
            ])

            # 解析 JSON 响应
            import json
            from autogen_core.utils import extract_json_from_str

            response_content = response.content.strip()

            # 提取 JSON
            json_objects = extract_json_from_str(response_content)
            if json_objects:
                progress_ledger = json_objects[0]
                return progress_ledger
            else:
                return self._get_default_progress_analysis(candidate_nodes)

        except Exception as e:
            return self._get_default_progress_analysis(candidate_nodes)

    def _get_default_progress_analysis(self, candidate_nodes: List[str]) -> Dict[str, Any]:
        """获取默认的进度分析结果"""
        return {
            "is_request_satisfied": {"reason": "默认分析", "answer": False},
            "is_in_loop": {"reason": "默认分析", "answer": False},
            "is_progress_being_made": {"reason": "默认分析", "answer": True},
            "next_speaker": {"reason": "默认选择第一个候选", "answer": candidate_nodes[0]},
            "instruction_or_question": {"reason": "默认指令", "answer": f"请继续执行你的专业任务"}
        }

    def _build_conversation_history(self) -> str:
        """构建对话历史，用于LLM分析"""
        history_lines = []

        # 获取最近的执行历史
        recent_history = self.progress_ledger.execution_history[-5:]  # 最近5次

        for item in recent_history:
            node = item.get("node", "unknown")
            result = item.get("result", {})
            success = result.get("success", False)
            message_content = result.get("message_content", "")

            history_lines.append(f"{node}: {'成功' if success else '失败'}")
            if message_content:
                # 截取消息内容的前100个字符
                preview = message_content[:100] + "..." if len(message_content) > 100 else message_content
                history_lines.append(f"  输出: {preview}")

        return "\n".join(history_lines) if history_lines else "无对话历史"

    # ================================
    # 执行监控和结果分析
    # ================================

    async def _execute_node_with_monitoring(self, node_name: str) -> Dict[str, Any]:
        """
        执行节点并监控结果

        Args:
            node_name: 要执行的节点名称

        Returns:
            包含执行结果和分析的字典
        """
        self.progress_ledger.update_node_state(node_name, NodeState.IN_PROGRESS)

        try:
            agent = self.participants[node_name]

            # 构建增强的提示
            enhanced_prompt = await self._build_enhanced_prompt(node_name)

            # 执行 Agent
            import time
            start_time = time.time()

            response = await agent.on_messages(
                [TextMessage(source="user", content=enhanced_prompt)],
                cancellation_token=None
            )

            execution_time = time.time() - start_time

            # 显示 Agent 的实际输出
            if response and response.chat_message:
                message_content = response.chat_message.content
                print(f"💬 Agent 输出:")
                print(f"{message_content}")
                print(f"⏱️ 执行耗时: {execution_time:.2f} 秒")
            else:
                print(f"⚠️ Agent 无输出")

            # 分析执行结果
            result_analysis = await self._analyze_execution_result(node_name, response)

            # 显示关键分析结果
            if not result_analysis["success"]:
                print(f"❌ 执行问题:")
                for reason in result_analysis.get("failure_reasons", []):
                    print(f"   - {reason}")

                # 检查是否需要立即重新选择 Agent
                if await self._should_reselect_agent(node_name, result_analysis):
                    print(f"🔄 检测到严重问题，需要重新选择 Agent")
                    self.progress_ledger.update_node_state(node_name, NodeState.FAILED)
                    self.progress_ledger.stall_count += 1

                    # 返回特殊标记，表示需要重新选择
                    return {
                        "success": False,
                        "response": response,
                        "analysis": result_analysis,
                        "node": node_name,
                        "execution_time": execution_time,
                        "needs_reselection": True
                    }
            else:
                print(f"✅ 执行成功")

            if result_analysis["success"]:
                self.progress_ledger.update_node_state(node_name, NodeState.COMPLETED)
                self.progress_ledger.stall_count = max(0, self.progress_ledger.stall_count - 1)
            else:
                self.progress_ledger.update_node_state(node_name, NodeState.FAILED)
                self.progress_ledger.stall_count += 1

            return {
                "success": result_analysis["success"],
                "response": response,
                "analysis": result_analysis,
                "node": node_name,
                "execution_time": execution_time
            }

        except Exception as e:
            print(f"❌ 执行异常: {e}")
            self.progress_ledger.update_node_state(node_name, NodeState.FAILED)
            self.progress_ledger.stall_count += 1

            return {
                "success": False,
                "error": str(e),
                "node": node_name,
                "execution_time": 0
            }

    async def _build_enhanced_prompt(self, node_name: str) -> str:
        """构建增强的提示 - 使用具体指令和错误信息"""
        # 获取为该节点生成的具体指令
        specific_instruction = ""
        if hasattr(self.progress_ledger, 'node_instructions') and node_name in self.progress_ledger.node_instructions:
            specific_instruction = self.progress_ledger.node_instructions[node_name]
        else:
            # 如果没有预生成的指令，现在生成
            specific_instruction = await self._generate_specific_instruction(node_name)

        # 构建基础提示
        enhanced_prompt = f"""
        【具体执行指令】
        {specific_instruction}

        【任务背景】
        原始任务：{self.task_ledger.original_task}

        【项目配置】
        项目名称：{self.task_ledger.project_config.get('project_name', '未设置')}
        主文件路径：{self.task_ledger.get_file_path('main')}
        测试文件路径：{self.task_ledger.get_file_path('test')}

        【执行计划】
        {self.task_ledger.plan[0] if self.task_ledger.plan else "无具体计划"}

        【当前状态】
        {self._format_current_state()}
        """

        # 特殊处理：为重构Agent添加错误信息
        if node_name == "RefactoringAgent" and hasattr(self.task_ledger, 'error_history') and self.task_ledger.error_history:
            latest_error = self.task_ledger.error_history[-1]
            enhanced_prompt += f"""

        【🚨 测试错误信息】
        错误来源：{latest_error['source']}
        错误原因：{latest_error['errors']}

        【📋 测试输出详情】
        {latest_error['test_output']}

        【🔧 修复指导】
        请仔细分析上述测试错误，确定是业务代码问题还是测试代码问题：
        1. 如果是函数名、参数、返回值不匹配 -> 修复业务代码
        2. 如果是测试用例编写错误 -> 修复测试代码
        3. 如果是逻辑实现错误 -> 修复业务代码
        4. 确保修复后测试能够通过
        """

        enhanced_prompt += """

        【重要提醒】
        - 请严格按照上述具体指令执行
        - 确保完成后输出相应的完成标记
        - 如果遇到问题，请详细说明具体情况
        - 对于文件操作类任务，确保成功调用相关工具
        """

        return enhanced_prompt

    def _format_current_state(self) -> str:
        """格式化当前执行状态"""
        state_info = []
        for node, state in self.progress_ledger.node_states.items():
            retry_count = self.progress_ledger.retry_counts.get(node, 0)
            state_info.append(f"{node}: {state.value} (重试: {retry_count})")
        return "\n".join(state_info)

    # ================================
    # 辅助方法和状态管理
    # ================================

    async def _generate_specific_instruction(self, node_name: str) -> str:
        """为特定节点生成具体执行指令 - 集成智能路径解析"""
        # 获取节点的历史执行情况
        node_history = [item for item in self.progress_ledger.execution_history if item.get("node") == node_name]

        # 检查依赖关系和前置条件
        dependency_info = await self._check_dependencies(node_name)

        # 初始化智能路径解析器
        path_resolver = self._initialize_path_resolver()

        # 生成路径相关信息
        path_info = ""
        if path_resolver:
            structure = path_resolver.discover_project_structure()
            working_dir = path_resolver.get_working_directory_for_agent(node_name)

            path_info = f"""
        🔍 **智能路径信息**：
        - 推荐工作目录: {working_dir}
        - 项目根目录: {structure.get('project_root', '未检测到')}
        - Utils目录: {structure.get('utils_dir', '未检测到')}
        - 主文件: {', '.join(structure.get('main_files', [])) or '未检测到'}
        - 测试文件: {', '.join(structure.get('test_files', [])) or '未检测到'}

        📋 **路径使用建议**：
        - 对于UnitTestAgent: 在 {working_dir} 目录下执行测试
        - 对于文件操作: 使用项目根目录 {structure.get('project_root', working_dir)}
        - 对于模块导入: 确保正确的sys.path设置
        """

        # 构建指令生成提示
        instruction_prompt = f"""
        为 {node_name} 生成具体的执行指令。

        当前任务：{self.task_ledger.original_task}

        Agent 描述：{self.task_ledger.agent_capabilities.get(node_name, '未知')}

        执行计划：{self.task_ledger.plan[0] if self.task_ledger.plan else '无'}

        历史执行情况：
        {self._format_node_history(node_history)}

        依赖关系检查：
        {dependency_info}

        {path_info}

        请生成一个具体、明确的指令，告诉这个 Agent 应该做什么。指令应该：
        1. 明确具体的任务目标
        2. 包含必要的上下文信息和依赖文件路径（使用上述智能路径信息）
        3. 指出需要避免的问题（如果有历史失败）
        4. 说明预期的输出格式和成功标准
        5. 包含具体的文件路径和操作步骤（基于智能路径解析结果）
        6. 对于UnitTestAgent，特别强调正确的工作目录和路径设置

        直接返回指令内容，不要额外的解释。
        """

        try:
            response = await self.model_client.create([
                UserMessage(content=instruction_prompt, source="orchestrator")
            ])
            return response.content.strip()
        except Exception as e:
            # 返回默认指令
            return self._get_default_instruction(node_name, dependency_info)

    async def _check_dependencies(self, node_name: str) -> str:
        """检查节点的依赖关系和前置条件"""
        dependency_info = []

        # 检查已完成的节点和它们的输出
        completed_nodes = []
        for node, state in self.progress_ledger.node_states.items():
            if state == NodeState.COMPLETED:
                completed_nodes.append(node)

        dependency_info.append(f"已完成的节点: {completed_nodes}")

        # 根据节点类型检查特定依赖
        main_file_path = self.task_ledger.get_file_path('main')
        test_file_path = self.task_ledger.get_file_path('test')

        if node_name == "TestGenerationAgent":
            if "FunctionWritingAgent" in completed_nodes:
                dependency_info.append("✅ FunctionWritingAgent 已完成，可以读取生成的代码文件")
                dependency_info.append(f"📁 预期代码文件位置: {main_file_path}")
            else:
                dependency_info.append("❌ FunctionWritingAgent 未完成，无法生成测试")

        elif node_name == "UnitTestAgent":
            if "TestGenerationAgent" in completed_nodes:
                dependency_info.append("✅ TestGenerationAgent 已完成，可以执行测试")
                dependency_info.append(f"📁 预期测试文件位置: {test_file_path}")
            else:
                dependency_info.append("❌ TestGenerationAgent 未完成，无法执行测试")

        elif node_name == "RefactoringAgent":
            if "ReflectionAgent" in completed_nodes and "CodeScanningAgent" in completed_nodes:
                dependency_info.append("✅ ReflectionAgent 和 CodeScanningAgent 已完成，可以进行重构")
            else:
                dependency_info.append("⚠️ 建议等待 ReflectionAgent 和 CodeScanningAgent 完成后再重构")

        elif node_name == "CodeScanningAgent":
            if "FunctionWritingAgent" in completed_nodes:
                dependency_info.append("✅ FunctionWritingAgent 已完成，可以扫描代码")
                dependency_info.append(f"📁 预期扫描文件: {main_file_path}")
            else:
                dependency_info.append("❌ FunctionWritingAgent 未完成，无法扫描代码")

        elif node_name == "ProjectStructureAgent":
            if "FunctionWritingAgent" in completed_nodes and "TestGenerationAgent" in completed_nodes:
                dependency_info.append("✅ 代码和测试文件已完成，可以创建项目结构")
                dependency_info.append(f"📁 源文件位置: {main_file_path}")
                dependency_info.append(f"📁 测试文件位置: {test_file_path}")
            else:
                dependency_info.append("⚠️ 建议等待代码和测试文件完成后再创建项目结构")

        return "\n".join(dependency_info)

    def _get_default_instruction(self, node_name: str, dependency_info: str) -> str:
        """获取默认指令"""
        main_file_path = self.task_ledger.get_file_path('main')
        test_file_path = self.task_ledger.get_file_path('test')
        project_name = self.task_ledger.project_config.get('project_name', 'custom_project')

        base_instructions = {
            "CodePlanningAgent": f"分析{project_name}需求，制定详细的实现计划。明确指定所有文件保存在 /Users/jabez/output 目录下，主代码文件为 {main_file_path}，测试文件为 {test_file_path}。",
            "FunctionWritingAgent": f"编写完整的{project_name}代码，保存到 {main_file_path} 文件中。确保包含所有必要的函数实现。",
            "TestGenerationAgent": f"读取 {main_file_path} 文件中的代码，为每个函数生成完整的测试用例，保存到 {test_file_path} 文件中。",
            "UnitTestAgent": f"执行 {test_file_path} 中的测试用例，生成详细的测试报告。使用 sys.path.insert(0, '/Users/jabez/output') 确保能导入模块。",
            "ReflectionAgent": "分析整个开发流程的执行结果，评估代码质量和测试覆盖率，提供改进建议。",
            "RefactoringAgent": f"分析测试错误信息，智能修复代码问题。读取 {main_file_path} 和 {test_file_path}，根据错误类型选择修复策略，确保测试通过。",
            "CodeScanningAgent": f"扫描 {main_file_path} 文件，进行静态代码分析，生成质量报告。",
            "ProjectStructureAgent": f"基于 /Users/jabez/output 目录中的文件创建完整的项目目录结构，包含 src、tests、docs 等文件夹，并生成必要的配置文件。"
        }

        base_instruction = base_instructions.get(node_name, f"请根据你的专业能力完成 {node_name} 的相关任务。")

        return f"""
{base_instruction}

依赖信息：
{dependency_info}

请确保：
1. 严格按照指令执行具体操作
2. 输出完整且包含必要的完成标记
3. 如果遇到依赖问题，请明确说明
        """.strip()

    def _format_node_history(self, node_history: List[Dict[str, Any]]) -> str:
        """格式化节点历史"""
        if not node_history:
            return "无历史执行记录"

        history_lines = []
        for i, item in enumerate(node_history[-3:]):  # 只显示最近3次
            result = item.get("result", {})
            success = result.get("success", False)
            failure_reasons = result.get("failure_reasons", [])

            history_lines.append(f"执行 {i+1}: {'成功' if success else '失败'}")
            if failure_reasons:
                history_lines.append(f"  失败原因: {', '.join(failure_reasons)}")

        return "\n".join(history_lines)

    # 这里省略了大量的辅助方法，包括：
    # - _analyze_execution_result: 分析执行结果
    # - _should_reselect_agent: 判断是否需要重新选择Agent
    # - _should_replan: 判断是否需要重新规划
    # - _get_next_executable_nodes: 获取下一批可执行节点
    # - _find_alternative_nodes: 寻找替代节点
    # - _generate_final_result: 生成最终结果
    # 等等...（为了保持代码简洁，这些方法的实现与原版本相同）

    async def _analyze_execution_result(self, node_name: str, response: Response) -> Dict[str, Any]:
        """分析执行结果 - 基于 MagenticOne 的深度分析"""
        try:
            message_content = response.chat_message.content if response.chat_message else ""

            # 检查工具调用情况
            tool_calls_analysis = self._analyze_tool_calls(node_name, response)

            # 检查预期的完成标记
            completion_markers = {
                "CodePlanningAgent": ["PLANNING_COMPLETE"],
                "FunctionWritingAgent": ["CODING_COMPLETE", "Successfully wrote content"],
                "TestGenerationAgent": ["TESTING_COMPLETE", "Successfully wrote content"],
                "UnitTestAgent": ["UNIT_TESTING_COMPLETE"],
                "ReflectionAgent": ["REFLECTION_COMPLETE"],
                "RefactoringAgent": ["REFACTORING_COMPLETE"],
                "CodeScanningAgent": ["SCANNING_COMPLETE"],
                "ProjectStructureAgent": ["PROJECT_STRUCTURE_COMPLETE"]
            }

            expected_markers = completion_markers.get(node_name, [])
            has_completion_marker = any(marker in message_content for marker in expected_markers)

            # 基于 Agent 类型的具体成功标准
            success_criteria = self._evaluate_agent_specific_success(node_name, response, message_content, tool_calls_analysis)

            # 综合判断成功状态
            success = success_criteria["meets_requirements"]

            return {
                "success": success,
                "has_completion_marker": has_completion_marker,
                "has_substantial_content": len(message_content.strip()) > 50,
                "content_length": len(message_content),
                "message_content": message_content,
                "tool_calls_analysis": tool_calls_analysis,
                "success_criteria": success_criteria,
                "failure_reasons": success_criteria.get("failure_reasons", [])
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "failure_reasons": [f"分析异常: {str(e)}"]
            }

    def _extract_task_requirements_from_planning(self) -> Dict[str, Any]:
        """从规划阶段提取任务要求"""
        requirements = {
            "files_to_create": [],
            "modules_to_implement": [],
            "functions_mentioned": [],
            "expected_deliverables": []
        }

        # 获取规划阶段的输出
        planning_output = ""
        for item in self.progress_ledger.execution_history:
            if item.get("node") == "CodePlanningAgent":
                result = item.get("result", {})
                planning_output = result.get("message_content", "")
                break

        if not planning_output:
            return requirements

        import re

        # 提取文件名（.py结尾的文件）
        file_patterns = [
            r'(\w+\.py)',  # 直接的.py文件
            r'`(\w+\.py)`',  # 反引号包围的文件
            r'**(\w+\.py)**',  # 粗体文件名
            r'(\w+)模块.*?`(\w+\.py)`',  # 模块描述中的文件名
        ]

        for pattern in file_patterns:
            matches = re.findall(pattern, planning_output, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    for m in match:
                        if m.endswith('.py'):
                            requirements["files_to_create"].append(m)
                elif match.endswith('.py'):
                    requirements["files_to_create"].append(match)

        # 去重
        requirements["files_to_create"] = list(set(requirements["files_to_create"]))

        # 提取模块描述
        module_patterns = [
            r'(\w+模块)',
            r'(\w+)模块',
            r'实现(\w+)',
            r'创建(\w+)',
        ]

        for pattern in module_patterns:
            matches = re.findall(pattern, planning_output)
            requirements["modules_to_implement"].extend(matches)

        return requirements

    async def _verify_actual_file_creation(self, expected_files: List[str]) -> Dict[str, Any]:
        """验证文件是否真的被创建"""
        import os

        verification = {
            "existing_files": [],
            "missing_files": [],
            "file_sizes": {},
            "creation_success_rate": 0.0,
            "total_expected": len(expected_files)
        }

        base_path = self.task_ledger.project_config.get('base_dir', '/Users/jabez/output')

        for file_name in expected_files:
            full_path = os.path.join(base_path, file_name)
            try:
                if os.path.exists(full_path):
                    verification["existing_files"].append(file_name)
                    verification["file_sizes"][file_name] = os.path.getsize(full_path)
                else:
                    verification["missing_files"].append(file_name)
            except Exception as e:
                verification["missing_files"].append(file_name)

        if verification["total_expected"] > 0:
            verification["creation_success_rate"] = (
                len(verification["existing_files"]) / verification["total_expected"]
            )

        return verification

    def _analyze_claimed_completions(self, message_content: str) -> Dict[str, Any]:
        """分析Agent声称完成的内容"""
        import re

        analysis = {
            "claimed_files": [],
            "claimed_modules": [],
            "claimed_functions": [],
            "completion_claims": [],
            "confidence_score": 0.0
        }

        # 提取声称创建的文件
        file_patterns = [
            r'`(\w+\.py)`',
            r'**(\w+\.py)**',
            r'(\w+\.py)',
            r'(\w+)模块.*?`(\w+\.py)`',
        ]

        for pattern in file_patterns:
            matches = re.findall(pattern, message_content, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    for m in match:
                        if m.endswith('.py'):
                            analysis["claimed_files"].append(m)
                elif match.endswith('.py'):
                    analysis["claimed_files"].append(match)

        # 去重
        analysis["claimed_files"] = list(set(analysis["claimed_files"]))

        # 提取完成声明
        completion_patterns = [
            r'(成功完成.*?)',
            r'(已正确创建.*?)',
            r'(实现了.*?)',
            r'(完成了.*?)',
        ]

        for pattern in completion_patterns:
            matches = re.findall(pattern, message_content)
            analysis["completion_claims"].extend(matches)

        # 计算置信度分数
        confidence_factors = [
            len(analysis["claimed_files"]) > 0,  # 提到了具体文件
            "CODING_COMPLETE" in message_content,  # 有完成标记
            len(message_content) > 200,  # 内容充实
            any(word in message_content for word in ["成功", "完成", "实现", "创建"]),  # 有成功指示
        ]

        analysis["confidence_score"] = sum(confidence_factors) / len(confidence_factors)

        return analysis

    async def _intelligent_task_completion_analysis(self, node_name: str, response: Response) -> Dict[str, Any]:
        """智能任务完成度分析 - FunctionWritingAgent专用"""
        if node_name != "FunctionWritingAgent":
            return {"applicable": False}

        message_content = response.chat_message.content if response.chat_message else ""

        # 1. 提取任务要求
        requirements = self._extract_task_requirements_from_planning()

        # 2. 分析声称的完成内容
        claimed_completions = self._analyze_claimed_completions(message_content)

        # 3. 验证实际文件创建
        file_verification = await self._verify_actual_file_creation(requirements["files_to_create"])

        # 4. 计算匹配度
        expected_files = set(requirements["files_to_create"])
        claimed_files = set(claimed_completions["claimed_files"])
        actual_files = set(file_verification["existing_files"])

        # 文件匹配分析
        file_match_analysis = {
            "expected_count": len(expected_files),
            "claimed_count": len(claimed_files),
            "actual_count": len(actual_files),
            "claim_accuracy": 0.0,  # 声称的文件中有多少真实存在
            "requirement_fulfillment": 0.0,  # 要求的文件中有多少被创建
            "claim_vs_requirement": 0.0,  # 声称的文件与要求的匹配度
        }

        if len(claimed_files) > 0:
            file_match_analysis["claim_accuracy"] = len(claimed_files & actual_files) / len(claimed_files)

        if len(expected_files) > 0:
            file_match_analysis["requirement_fulfillment"] = len(expected_files & actual_files) / len(expected_files)
            file_match_analysis["claim_vs_requirement"] = len(claimed_files & expected_files) / len(expected_files)

        # 5. 综合评分
        scores = {
            "claim_confidence": claimed_completions["confidence_score"],
            "file_creation_rate": file_verification["creation_success_rate"],
            "claim_accuracy": file_match_analysis["claim_accuracy"],
            "requirement_fulfillment": file_match_analysis["requirement_fulfillment"],
        }

        # 加权综合评分
        overall_score = (
            0.2 * scores["claim_confidence"] +
            0.4 * scores["file_creation_rate"] +
            0.2 * scores["claim_accuracy"] +
            0.2 * scores["requirement_fulfillment"]
        )

        return {
            "applicable": True,
            "requirements": requirements,
            "claimed_completions": claimed_completions,
            "file_verification": file_verification,
            "file_match_analysis": file_match_analysis,
            "scores": scores,
            "overall_score": overall_score,
            "success": overall_score >= 0.7,  # 70%以上认为成功
            "detailed_analysis": {
                "expected_files": list(expected_files),
                "claimed_files": list(claimed_files),
                "actual_files": list(actual_files),
                "missing_files": list(expected_files - actual_files),
                "extra_files": list(actual_files - expected_files),
            }
        }

    def _analyze_tool_calls(self, node_name: str, response: Response) -> Dict[str, Any]:
        """分析工具调用情况 - 改进版本，支持智能任务完成度分析"""
        tool_calls = []
        successful_calls = []
        failed_calls = []

        # 检查响应消息内容
        message_content = response.chat_message.content if response.chat_message else ""

        # 方法1: 检查ToolCallSummaryMessage中的成功标记 - 扩展检测范围
        mcp_success_indicators = [
            "Successfully wrote content",
            "successfully wrote",
            "Successfully created",
            "successfully created",
            "写入成功",
            "保存成功",
            "创建成功",
            "生成成功"
        ]

        for indicator in mcp_success_indicators:
            if indicator in message_content:
                successful_calls.append({
                    "type": "mcp_tool_success",
                    "content": f"检测到MCP工具成功指示: {indicator}",
                    "status": "success"
                })
                break

        # 方法2: 检查inner_messages中的工具调用事件
        if hasattr(response, 'inner_messages') and response.inner_messages:
            for inner_msg in response.inner_messages:
                # 检查ToolCallExecutionEvent
                if hasattr(inner_msg, 'type') and 'ToolCallExecution' in str(type(inner_msg)):
                    tool_calls.append(inner_msg)
                    successful_calls.append({
                        "type": "tool_execution",
                        "content": str(inner_msg),
                        "status": "success"
                    })

        # 方法3: 对于FunctionWritingAgent，使用智能任务完成度分析
        intelligent_analysis = None
        if node_name == "FunctionWritingAgent":
            try:
                # 注意：这里需要在异步上下文中调用
                import asyncio
                if asyncio.get_event_loop().is_running():
                    # 如果已经在事件循环中，创建任务
                    task = asyncio.create_task(self._intelligent_task_completion_analysis(node_name, response))
                    # 这里我们先跳过异步调用，在_evaluate_agent_specific_success中处理
                    pass
                else:
                    intelligent_analysis = asyncio.run(self._intelligent_task_completion_analysis(node_name, response))
            except Exception as e:
                print(f"智能分析异常: {e}")

        # 方法4: 传统的完成标记检查
        completion_markers = {
            "CodePlanningAgent": ["PLANNING_COMPLETE"],
            "FunctionWritingAgent": ["CODING_COMPLETE"],
            "TestGenerationAgent": ["TESTING_COMPLETE"],
            "UnitTestAgent": ["UNIT_TESTING_COMPLETE"],
            "ReflectionAgent": ["REFLECTION_COMPLETE"],
            "RefactoringAgent": ["REFACTORING_COMPLETE"],
            "CodeScanningAgent": ["SCANNING_COMPLETE"],
            "ProjectStructureAgent": ["PROJECT_STRUCTURE_COMPLETE"]
        }

        expected_markers = completion_markers.get(node_name, [])
        has_completion_marker = any(marker in message_content for marker in expected_markers)

        if has_completion_marker and len(message_content.strip()) > 100:
            if not successful_calls:
                successful_calls.append({
                    "type": "completion_marker",
                    "content": f"检测到完成标记: {[m for m in expected_markers if m in message_content]}",
                    "status": "success"
                })

        return {
            "total_calls": len(tool_calls),
            "successful_calls": len(successful_calls),
            "failed_calls": len(failed_calls),
            "tool_calls": tool_calls,
            "successful_executions": successful_calls,
            "failed_executions": failed_calls,
            "intelligent_analysis": intelligent_analysis
        }

    def _evaluate_agent_specific_success(self, node_name: str, response: Response, message_content: str, tool_calls: Dict[str, Any]) -> Dict[str, Any]:
        """基于 Agent 类型评估具体成功标准"""
        failure_reasons = []
        meets_requirements = True

        if node_name == "FunctionWritingAgent":
            # 使用智能任务完成度分析
            try:
                import asyncio
                intelligent_analysis = asyncio.run(self._intelligent_task_completion_analysis(node_name, response))

                if intelligent_analysis.get("applicable", False):
                    # 使用智能分析结果
                    overall_score = intelligent_analysis.get("overall_score", 0.0)
                    detailed_analysis = intelligent_analysis.get("detailed_analysis", {})
                    scores = intelligent_analysis.get("scores", {})

                    meets_requirements = intelligent_analysis.get("success", False)

                    if not meets_requirements:
                        # 提供详细的失败原因
                        if scores.get("file_creation_rate", 0) < 0.5:
                            missing_files = detailed_analysis.get("missing_files", [])
                            failure_reasons.append(f"文件创建不完整，缺失文件: {missing_files}")

                        if scores.get("claim_accuracy", 0) < 0.7:
                            failure_reasons.append("Agent声称创建的文件与实际创建的文件不匹配")

                        if scores.get("requirement_fulfillment", 0) < 0.7:
                            expected_files = detailed_analysis.get("expected_files", [])
                            actual_files = detailed_analysis.get("actual_files", [])
                            failure_reasons.append(f"任务要求未完全满足。要求: {expected_files}, 实际: {actual_files}")

                        if scores.get("claim_confidence", 0) < 0.5:
                            failure_reasons.append("Agent输出缺乏明确的完成确认")

                        failure_reasons.append(f"综合评分: {overall_score:.2f} (需要 >= 0.7)")

                    # 添加智能分析结果到返回值中
                    return {
                        "meets_requirements": meets_requirements,
                        "failure_reasons": failure_reasons,
                        "intelligent_analysis": intelligent_analysis,
                        "evaluation_details": {
                            "node_type": node_name,
                            "content_length": len(message_content),
                            "tool_success_rate": tool_calls["successful_calls"] / max(1, tool_calls["total_calls"]),
                            "overall_score": overall_score,
                            "detailed_scores": scores
                        }
                    }

            except Exception as e:
                print(f"智能分析失败，回退到传统方法: {e}")

            # 回退到传统判断逻辑
            has_tool_success = tool_calls["successful_calls"] > 0
            has_completion_marker = "CODING_COMPLETE" in message_content
            has_substantial_content = len(message_content.strip()) > 200

            # 动态检查是否描述了具体的代码实现
            project_name = self.task_ledger.project_config.get('project_name', '')
            main_file = self.task_ledger.project_config.get('main_file', '')

            # 基于实际项目的动态指示器
            dynamic_indicators = []
            if project_name:
                dynamic_indicators.extend([project_name, project_name.replace('_', ' ')])
            if main_file:
                file_base = main_file.replace('.py', '').split('/')[-1]
                dynamic_indicators.append(file_base)

            # 通用的实现指示器
            generic_indicators = [
                "实现了", "创建了", "生成了", "完成了", "编写了",
                ".py", "模块", "函数", "类", "代码",
                "implemented", "created", "generated", "completed"
            ]

            # 合并所有指示器
            all_indicators = dynamic_indicators + generic_indicators
            has_implementation_description = any(
                indicator in message_content for indicator in all_indicators
            )

            # 综合判断成功条件
            success_conditions = [
                has_tool_success,  # 检测到工具调用成功
                has_completion_marker and has_substantial_content,  # 有完成标记且内容充实
                has_implementation_description and has_completion_marker  # 有实现描述且有完成标记
            ]

            if not any(success_conditions):
                if not has_tool_success:
                    failure_reasons.append("没有检测到成功的工具调用")
                if not has_completion_marker:
                    failure_reasons.append("缺少CODING_COMPLETE完成标记")
                if not has_substantial_content:
                    failure_reasons.append("输出内容过于简短")
                if not has_implementation_description:
                    failure_reasons.append("没有描述具体的代码实现")
                meets_requirements = False

        elif node_name == "TestGenerationAgent":
            # 检查是否生成了测试文件
            if tool_calls["successful_calls"] == 0:
                failure_reasons.append("没有成功的测试文件生成操作")
                meets_requirements = False

        elif node_name == "UnitTestAgent":
            # 检查是否执行了测试 - 改进检测逻辑
            # 检查消息内容中是否包含测试执行的关键信息
            test_execution_indicators = [
                "ran " in message_content.lower() and "test" in message_content.lower(),
                "ok" in message_content.lower() and "test" in message_content.lower(),
                "passed" in message_content.lower(),
                "failed" in message_content.lower(),
                "error" in message_content.lower() and "test" in message_content.lower(),
                "unittest" in message_content.lower(),
                "test_" in message_content.lower()
            ]

            has_test_execution = any(test_execution_indicators)

            if not has_test_execution and tool_calls["total_calls"] == 0:
                failure_reasons.append("没有执行任何代码运行操作")
                meets_requirements = False
            elif has_test_execution:
                # 进一步检查测试是否成功
                success_indicators = [
                    "ok" in message_content.lower() and "ran" in message_content.lower(),
                    "passed" in message_content.lower(),
                    "成功率: 100" in message_content,
                    "失败: 0" in message_content and "错误: 0" in message_content
                ]

                failure_indicators = [
                    "failed" in message_content.lower() and "test" in message_content.lower(),
                    "error" in message_content.lower() and "test" in message_content.lower(),
                    "traceback" in message_content.lower(),
                    "assertion" in message_content.lower(),
                    "成功率: 0" in message_content,
                    "失败:" in message_content and not "失败: 0" in message_content
                ]

                if any(failure_indicators):
                    failure_reasons.append("测试执行失败，存在失败或错误的测试用例")
                    meets_requirements = False
                elif any(success_indicators):
                    meets_requirements = True  # 测试成功
                else:
                    # 无法明确判断，保守处理
                    failure_reasons.append("无法确定测试执行结果")
                    meets_requirements = False

        elif node_name == "CodePlanningAgent":
            # CodePlanningAgent的智能成功判定逻辑
            has_tool_success = tool_calls["successful_calls"] > 0
            has_completion_marker = "PLANNING_COMPLETE" in message_content
            has_substantial_content = len(message_content.strip()) > 50  # 降低内容长度要求

            # 检查是否有工具调用成功的指示
            tool_success_indicators = [
                "Successfully wrote content" in message_content,
                "successfully wrote" in message_content.lower(),
                "写入成功" in message_content,
                "保存成功" in message_content,
                "创建成功" in message_content,
                "生成成功" in message_content
            ]
            has_tool_success_indication = any(tool_success_indicators)

            # 检查是否提到了规划相关的文件
            planning_file_indicators = [
                "design_plan.md" in message_content,
                "plan.md" in message_content,
                "规划" in message_content,
                "设计" in message_content,
                "方案" in message_content,
                ".md" in message_content
            ]
            has_planning_file_mention = any(planning_file_indicators)

            # 综合判断成功条件 - 针对使用MCP工具的CodePlanningAgent
            success_conditions = [
                # 条件1: 传统的完成标记 + 内容充实
                has_completion_marker and has_substantial_content,
                # 条件2: 工具调用成功 + 工具成功指示
                has_tool_success and has_tool_success_indication,
                # 条件3: 工具成功指示 + 规划文件提及 (针对MCP文件写入)
                has_tool_success_indication and has_planning_file_mention,
                # 条件4: 工具调用成功 + 完成标记 (最宽松的条件)
                has_tool_success and has_completion_marker
            ]

            if not any(success_conditions):
                if not has_completion_marker:
                    failure_reasons.append("缺少PLANNING_COMPLETE完成标记")
                if not has_substantial_content:
                    failure_reasons.append("输出内容过于简短")
                if not has_tool_success:
                    failure_reasons.append("没有检测到成功的工具调用")
                if not has_tool_success_indication:
                    failure_reasons.append("没有检测到工具执行成功的明确指示")
                if not has_planning_file_mention:
                    failure_reasons.append("没有提及规划相关的文件")
                meets_requirements = False

        elif node_name == "ReflectionAgent":
            # 检查内容质量
            if len(message_content.strip()) < 200:
                failure_reasons.append("输出内容过于简短")
                meets_requirements = False

        return {
            "meets_requirements": meets_requirements,
            "failure_reasons": failure_reasons,
            "evaluation_details": {
                "node_type": node_name,
                "content_length": len(message_content),
                "tool_success_rate": tool_calls["successful_calls"] / max(1, tool_calls["total_calls"])
            }
        }

    async def _should_reselect_agent(self, node_name: str, result_analysis: Dict[str, Any]) -> bool:
        """判断是否需要重新选择 Agent"""
        failure_reasons = result_analysis.get("failure_reasons", [])

        # 检查严重的失败情况
        serious_failures = [
            "只设置了路径，没有实际",
            "文件访问被拒绝",
            "找不到测试模块",
            "请求更多信息而不是执行"
        ]

        for reason in failure_reasons:
            for serious_failure in serious_failures:
                if serious_failure in reason:
                    return True

        # 检查重试次数
        retry_count = self.progress_ledger.retry_counts.get(node_name, 0)
        if retry_count >= 1:  # 如果已经重试过一次还失败，考虑重新选择
            return True

        return False

    async def _should_replan(self) -> bool:
        """检查是否需要重新规划"""
        # 检查停滞计数
        stall_check = self.progress_ledger.stall_count >= self.max_stalls

        # 检查失败路径
        failed_check = len(self.task_ledger.failed_paths) >= 2

        should_replan = stall_check or failed_check

        if should_replan:
            if stall_check:
                print(f"🔄 停滞计数过高 ({self.progress_ledger.stall_count}/{self.max_stalls})，需要重新规划")
            if failed_check:
                print(f"🔄 失败路径过多 ({len(self.task_ledger.failed_paths)})，需要重新规划")

        return should_replan

    async def _get_next_executable_nodes(self, completed_node: str, execution_result: Dict[str, Any]) -> List[str]:
        """
        智能链路选择 - 基于执行结果动态选择下一个Agent

        实现逻辑：
        1. 单元测试失败 -> 重构Agent
        2. 重构Agent完成 -> 重新单元测试
        3. 单元测试成功 -> 继续正常流程
        4. 其他失败情况 -> 智能重试或替代
        """
        print(f"\n🤔 智能链路选择：分析 {completed_node} 的执行结果...")

        # 特殊处理：单元测试失败的情况
        if completed_node == "UnitTestAgent" and not execution_result["success"]:
            print(f"🔧 单元测试失败，启动智能修复流程")

            # 检查失败原因
            failure_reasons = execution_result.get("analysis", {}).get("failure_reasons", [])
            message_content = execution_result.get("analysis", {}).get("message_content", "")

            # 分析是否包含测试错误信息
            has_test_errors = any([
                "failed" in message_content.lower(),
                "error" in message_content.lower(),
                "assertion" in message_content.lower(),
                "traceback" in message_content.lower(),
                len(failure_reasons) > 0
            ])

            if has_test_errors:
                print(f"📋 检测到测试错误，将错误信息传递给重构Agent")
                # 将错误信息存储到任务账本中，供重构Agent使用
                error_info = {
                    "source": "UnitTestAgent",
                    "errors": failure_reasons,
                    "test_output": message_content,
                    "timestamp": asyncio.get_event_loop().time()
                }

                if not hasattr(self.task_ledger, 'error_history'):
                    self.task_ledger.error_history = []
                self.task_ledger.error_history.append(error_info)

                return ["RefactoringAgent"]
            else:
                # 如果没有明确的错误信息，尝试重试
                retry_count = self.progress_ledger.retry_counts.get(completed_node, 0)
                if retry_count <= self.max_retries:
                    print(f"🔄 未检测到明确错误，重试单元测试")
                    return [completed_node]

        # 特殊处理：重构Agent完成后，重新进行单元测试
        elif completed_node == "RefactoringAgent" and execution_result["success"]:
            print(f"🔄 重构完成，重新执行单元测试验证修复效果")
            # 重置UnitTestAgent的重试计数，给它新的机会
            if "UnitTestAgent" in self.progress_ledger.retry_counts:
                self.progress_ledger.retry_counts["UnitTestAgent"] = 0
            # 更新节点状态，允许重新执行
            self.progress_ledger.node_states["UnitTestAgent"] = NodeState.NOT_STARTED
            return ["UnitTestAgent"]

        # 特殊处理：单元测试成功后，跳过反思Agent，直接进行代码扫描
        elif completed_node == "UnitTestAgent" and execution_result["success"]:
            print(f"✅ 单元测试通过，继续后续流程")
            return ["CodeScanningAgent"]  # 跳过ReflectionAgent

        # 一般失败处理：智能重试和替代
        if not execution_result["success"]:
            retry_count = self.progress_ledger.retry_counts.get(completed_node, 0)

            if retry_count <= self.max_retries:
                print(f"🔄 {completed_node} 执行失败，准备重试 (第{retry_count + 1}次)")
                return [completed_node]  # 重试当前节点
            else:
                print(f"❌ {completed_node} 重试次数已达上限，寻找替代方案")
                # 寻找可以替代或修复的节点
                alternative_nodes = await self._find_alternative_nodes(completed_node)
                if alternative_nodes:
                    print(f"🔄 找到替代节点: {alternative_nodes}")
                    return alternative_nodes

        # 正常流程：按预定义顺序执行
        normal_flow_sequence = [
            "CodePlanningAgent", "FunctionWritingAgent", "TestGenerationAgent",
            "UnitTestAgent", "CodeScanningAgent", "ProjectStructureAgent"
        ]

        try:
            current_index = normal_flow_sequence.index(completed_node)
            if current_index + 1 < len(normal_flow_sequence):
                next_node = normal_flow_sequence[current_index + 1]
                print(f"➡️ 正常流程：{completed_node} -> {next_node}")
                return [next_node]
        except ValueError:
            # 如果不在正常流程中，可能是重构等特殊节点
            pass

        print(f"🏁 流程结束")
        return []  # 流程结束

    async def _find_alternative_nodes(self, failed_node: str) -> List[str]:
        """寻找失败节点的替代方案"""
        alternatives = []

        # 根据失败节点的类型寻找替代方案
        if failed_node == "FunctionWritingAgent":
            # 如果编码失败，可能需要重新规划
            if "CodePlanningAgent" in self.participants:
                alternatives.append("CodePlanningAgent")

        elif failed_node == "TestGenerationAgent":
            # 如果测试生成失败，可能需要重新编码或修复路径问题
            if "FunctionWritingAgent" in self.participants:
                alternatives.append("FunctionWritingAgent")

        elif failed_node == "UnitTestAgent":
            # 如果测试执行失败，可能需要重新生成测试或修复代码
            if "TestGenerationAgent" in self.participants:
                alternatives.append("TestGenerationAgent")

        return alternatives

    async def _generate_final_result(self):
        """生成最终结果"""
        # 收集所有消息
        all_messages = []
        for history_item in self.progress_ledger.execution_history:
            if "result" in history_item and "response" in history_item["result"]:
                response = history_item["result"]["response"]
                if hasattr(response, 'chat_message') and response.chat_message:
                    all_messages.append(response.chat_message)

        # 添加停止消息
        stop_message = StopMessage(
            source="GraphFlowOrchestrator",
            content="高级调度执行完成"
        )
        all_messages.append(stop_message)

        # 产出 TaskResult
        return TaskResult(
            messages=all_messages,
            stop_reason="高级调度执行完成"
        )


# ================================
# 主函数
# ================================

async def run_eight_agent_collaboration():
    """
    运行八Agent协作示例 - 使用高级调度系统

    这个函数是整个系统的入口点，负责：
    1. 配置LLM模型客户端
    2. 创建和配置MCP服务
    3. 创建所有Agent
    4. 初始化编排器
    5. 运行协作流程
    """

    print("🚀 启动八Agent协作系统")
    print("=" * 60)

    # 1. 创建LLM模型客户端
    print("📡 配置LLM模型客户端...")
    model_client = create_model_client()

    # 2. 配置MCP服务
    print("🔧 配置MCP服务...")
    filesystem_mcp_server, code_runner_mcp_server = create_mcp_servers()

    # 3. 创建MCP工作台并配置Agent
    print("🤖 创建Agent...")
    async with McpWorkbench(filesystem_mcp_server) as fs_workbench, \
               McpWorkbench(code_runner_mcp_server) as code_workbench:

        # 创建所有Agent（暂时不传递路径解析器）
        agents = create_all_agents(fs_workbench, code_workbench, model_client)

        print(f"✅ 成功创建 {len(agents)} 个Agent:")
        for agent in agents:
            print(f"   - {agent.name}: {agent.description}")

        # 4. 创建编排器
        print("\n🎯 初始化高级编排器...")
        orchestrator = GraphFlowOrchestrator(
            graph=None,  # 简化版本不使用图结构
            participants=agents,
            model_client=model_client,
            max_stalls=3,
            max_retries=2
        )

        # 5. 运行协作流程
        print("\n🎬 开始执行协作流程...")
        print("=" * 60)

        # 测试不同类型的任务
        tasks = [
            "请创建一个字符串操作工具库，包含常用的字符串处理函数，如反转、大小写转换、去除空格等功能。",
            "开发一个数学计算库，包含基础的数学运算函数，如阶乘、斐波那契数列、素数判断等。",
            "构建一个文件处理工具，包含文件读写、格式转换、批量处理等功能。"
        ]
        
        # 选择第一个任务进行演示
        task = tasks[0]

        print(f"🎯 选择的任务: {task}")
        print(f"📋 系统将自动解析任务并生成合适的文件名")

        try:
            async for event in orchestrator.run_stream(task):
                if hasattr(event, 'content'):
                    print(f"\n📨 事件: {event.content}")
                else:
                    print(f"\n📨 事件: {event}")

        except Exception as e:
            print(f"\n❌ 执行过程中发生错误: {e}")
            import traceback
            traceback.print_exc()

        print("\n" + "=" * 60)
        print("🏁 八Agent协作流程执行完成")


# ================================
# 智能路径解析器
# ================================

class IntelligentPathResolver:
    """
    智能路径解析器 - 基于执行历史和项目配置智能解析文件路径

    功能：
    1. 从执行历史中提取实际的文件路径
    2. 检测项目结构变化
    3. 智能匹配文件位置
    4. 解决路径不一致问题
    """

    def __init__(self, project_config: Dict[str, Any], facts: List[str], plan: List[str]):
        self.project_config = project_config
        self.facts = facts
        self.plan = plan
        self.base_dir = project_config.get('base_dir', '/Users/jabez/output')
        self.project_name = project_config.get('project_name', '')

        # 可能的项目根目录
        self.possible_roots = [
            self.base_dir,
            os.path.join(self.base_dir, self.project_name),
            os.path.join(self.base_dir, f"{self.project_name}_project"),
        ]

        # 缓存已发现的路径
        self._path_cache = {}
        self._structure_cache = None

    def discover_project_structure(self) -> Dict[str, Any]:
        """发现实际的项目结构"""
        if self._structure_cache is not None:
            return self._structure_cache

        structure = {
            "project_root": None,
            "utils_dir": None,
            "main_files": [],
            "test_files": [],
            "python_files": [],
            "directories": []
        }

        # 搜索所有可能的根目录
        for root in self.possible_roots:
            if os.path.exists(root):
                structure.update(self._scan_directory(root))
                if structure["project_root"]:
                    break

        self._structure_cache = structure
        return structure

    def _scan_directory(self, directory: str) -> Dict[str, Any]:
        """扫描目录结构"""
        structure = {
            "project_root": None,
            "utils_dir": None,
            "main_files": [],
            "test_files": [],
            "python_files": [],
            "directories": []
        }

        try:
            # 使用pathlib进行递归搜索
            path = Path(directory)

            # 查找Python文件
            python_files = list(path.rglob("*.py"))
            structure["python_files"] = [str(f) for f in python_files]

            # 查找主文件
            main_patterns = [
                "**/file_processor.py",
                "**/main.py",
                f"**/{self.project_name}.py"
            ]

            for pattern in main_patterns:
                matches = list(path.glob(pattern))
                if matches:
                    structure["main_files"].extend([str(f) for f in matches])
                    # 推断项目根目录
                    if not structure["project_root"]:
                        structure["project_root"] = str(matches[0].parent)

            # 查找测试文件
            test_patterns = [
                "**/test_*.py",
                "**/*_test.py",
                "**/tests/*.py"
            ]

            for pattern in test_patterns:
                matches = list(path.glob(pattern))
                structure["test_files"].extend([str(f) for f in matches])

            # 查找utils目录
            utils_dirs = list(path.glob("**/utils"))
            if utils_dirs:
                structure["utils_dir"] = str(utils_dirs[0])

            # 记录所有目录
            structure["directories"] = [str(d) for d in path.rglob("*") if d.is_dir()]

        except Exception as e:
            print(f"扫描目录 {directory} 时出错: {e}")

        return structure

    def resolve_file_path(self, file_reference: str, context: str = "") -> Optional[str]:
        """
        智能解析文件路径

        Args:
            file_reference: 文件引用（可能是相对路径、文件名或绝对路径）
            context: 上下文信息（如Agent名称、执行阶段等）

        Returns:
            解析后的绝对路径，如果找不到则返回None
        """
        # 检查缓存
        cache_key = f"{file_reference}:{context}"
        if cache_key in self._path_cache:
            return self._path_cache[cache_key]

        resolved_path = None

        # 1. 如果是绝对路径且存在，直接返回
        if os.path.isabs(file_reference) and os.path.exists(file_reference):
            resolved_path = file_reference

        # 2. 发现项目结构
        structure = self.discover_project_structure()

        # 3. 基于文件类型和上下文智能匹配
        if not resolved_path:
            resolved_path = self._smart_match_file(file_reference, context, structure)

        # 4. 如果仍未找到，尝试模糊匹配
        if not resolved_path:
            resolved_path = self._fuzzy_match_file(file_reference, structure)

        # 缓存结果
        if resolved_path:
            self._path_cache[cache_key] = resolved_path

        return resolved_path

    def _smart_match_file(self, file_reference: str, context: str, structure: Dict[str, Any]) -> Optional[str]:
        """基于上下文的智能文件匹配"""

        # 测试文件匹配
        if "test" in file_reference.lower() or "UnitTestAgent" in context:
            for test_file in structure["test_files"]:
                if file_reference in test_file or os.path.basename(file_reference) == os.path.basename(test_file):
                    return test_file

        # 主文件匹配
        if "main" in file_reference.lower() or "file_processor" in file_reference.lower():
            for main_file in structure["main_files"]:
                if file_reference in main_file or os.path.basename(file_reference) == os.path.basename(main_file):
                    return main_file

        # utils模块匹配
        if "utils/" in file_reference or file_reference.endswith(".py"):
            if structure["utils_dir"]:
                potential_path = os.path.join(structure["utils_dir"], os.path.basename(file_reference))
                if os.path.exists(potential_path):
                    return potential_path

        # 项目根目录匹配
        if structure["project_root"]:
            potential_path = os.path.join(structure["project_root"], file_reference)
            if os.path.exists(potential_path):
                return potential_path

        return None

    def _fuzzy_match_file(self, file_reference: str, structure: Dict[str, Any]) -> Optional[str]:
        """模糊匹配文件"""
        filename = os.path.basename(file_reference)

        # 在所有Python文件中搜索
        for py_file in structure["python_files"]:
            if filename == os.path.basename(py_file):
                return py_file

            # 部分匹配
            if filename.replace("_", "").replace("-", "") in os.path.basename(py_file).replace("_", "").replace("-", ""):
                return py_file

        return None

    def get_working_directory_for_agent(self, agent_name: str) -> str:
        """为特定Agent获取工作目录"""
        structure = self.discover_project_structure()

        if agent_name == "UnitTestAgent":
            # 单元测试Agent需要在项目根目录执行
            if structure["project_root"]:
                return structure["project_root"]
            elif structure["test_files"]:
                # 如果有测试文件，使用测试文件所在目录
                return os.path.dirname(structure["test_files"][0])

        elif agent_name in ["FunctionWritingAgent", "TestGenerationAgent"]:
            # 代码编写Agent使用项目根目录
            if structure["project_root"]:
                return structure["project_root"]

        # 默认返回base_dir
        return self.base_dir

    def resolve_import_paths(self, test_file_path: str) -> Dict[str, str]:
        """
        解析测试文件中的导入路径问题

        Returns:
            包含sys.path修改建议的字典
        """
        structure = self.discover_project_structure()
        suggestions = {
            "working_directory": self.get_working_directory_for_agent("UnitTestAgent"),
            "sys_path_additions": [],
            "import_fixes": []
        }

        if structure["project_root"] and structure["utils_dir"]:
            # 如果utils目录存在，确保项目根目录在sys.path中
            suggestions["sys_path_additions"].append(structure["project_root"])

            # 检查相对导入是否正确
            if test_file_path:
                test_dir = os.path.dirname(test_file_path)
                utils_relative = os.path.relpath(structure["utils_dir"], test_dir)

                if utils_relative != "utils":
                    suggestions["import_fixes"].append({
                        "from": "from utils.",
                        "to": f"from {utils_relative.replace(os.sep, '.')}.",
                        "reason": f"utils目录相对于测试文件的路径是 {utils_relative}"
                    })

        return suggestions

    def generate_path_report(self) -> str:
        """生成路径解析报告"""
        structure = self.discover_project_structure()

        report = ["=== 智能路径解析报告 ===\n"]

        report.append(f"项目配置:")
        report.append(f"  - 项目名称: {self.project_name}")
        report.append(f"  - 基础目录: {self.base_dir}")
        report.append("")

        report.append(f"发现的项目结构:")
        report.append(f"  - 项目根目录: {structure.get('project_root', '未找到')}")
        report.append(f"  - Utils目录: {structure.get('utils_dir', '未找到')}")
        report.append(f"  - 主文件数量: {len(structure.get('main_files', []))}")
        report.append(f"  - 测试文件数量: {len(structure.get('test_files', []))}")
        report.append(f"  - Python文件总数: {len(structure.get('python_files', []))}")
        report.append("")

        if structure.get('main_files'):
            report.append("主文件:")
            for f in structure['main_files']:
                report.append(f"  - {f}")
            report.append("")

        if structure.get('test_files'):
            report.append("测试文件:")
            for f in structure['test_files']:
                report.append(f"  - {f}")
            report.append("")

        if self._path_cache:
            report.append("路径解析缓存:")
            for key, value in self._path_cache.items():
                report.append(f"  - {key} -> {value}")

        return "\n".join(report)


# ================================
# 程序入口
# ================================

if __name__ == "__main__":
    """程序入口点"""
    print("🌟 八Agent协作系统 - 重构版本")
    print("结合 GraphFlow 和 MagenticOne 的智能调度")
    print("=" * 60)

    # 运行协作系统
    asyncio.run(run_eight_agent_collaboration())
