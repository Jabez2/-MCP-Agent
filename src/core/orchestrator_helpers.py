"""
编排器辅助方法

包含编排器的辅助方法和工具函数。
"""

import asyncio
from typing import Any, Dict, List, Optional
from autogen_agentchat.base import Response
from autogen_agentchat.messages import TextMessage, StopMessage
from autogen_core.models import UserMessage

from .data_structures import NodeState


class OrchestratorHelpers:
    """编排器辅助方法类"""
    
    @staticmethod
    async def build_enhanced_prompt(orchestrator, node_name: str) -> str:
        """构建增强的提示 - 使用具体指令和错误信息"""
        # 获取为该节点生成的具体指令
        specific_instruction = ""
        if hasattr(orchestrator.progress_ledger, 'node_instructions') and node_name in orchestrator.progress_ledger.node_instructions:
            specific_instruction = orchestrator.progress_ledger.node_instructions[node_name]
        else:
            # 如果没有预生成的指令，现在生成
            specific_instruction = await orchestrator._generate_specific_instruction(node_name)

        # 构建基础提示
        enhanced_prompt = f"""
        【具体执行指令】
        {specific_instruction}

        【任务背景】
        原始任务：{orchestrator.task_ledger.original_task}

        【项目配置】
        项目名称：{orchestrator.task_ledger.project_config.get('project_name', '未设置')}
        主文件路径：{orchestrator.task_ledger.get_file_path('main')}
        测试文件路径：{orchestrator.task_ledger.get_file_path('test')}

        【执行计划】
        {orchestrator.task_ledger.plan[0] if orchestrator.task_ledger.plan else "无具体计划"}

        【当前状态】
        {OrchestratorHelpers.format_current_state(orchestrator)}
        """

        # 添加Agent通信增强信息
        if orchestrator.memory_initialized and hasattr(orchestrator.task_ledger, 'enhanced_contexts'):
            enhanced_context = orchestrator.task_ledger.enhanced_contexts.get(node_name, {})

            if enhanced_context:
                enhanced_prompt += "\n\n        【🔗 Agent协作信息】"

                # 依赖Agent输出
                if enhanced_context.get("dependency_outputs"):
                    enhanced_prompt += f"""

        【📋 依赖Agent输出】
        {OrchestratorHelpers._format_dependency_outputs(enhanced_context["dependency_outputs"])}"""

                # 收到的消息
                if enhanced_context.get("incoming_messages"):
                    enhanced_prompt += f"""

        【📨 收到的消息】
        {chr(10).join([f"        - {msg}" for msg in enhanced_context["incoming_messages"]])}"""

                # 智能建议
                if enhanced_context.get("suggestions"):
                    enhanced_prompt += f"""

        【💡 建议的行动】
        {chr(10).join([f"        - {suggestion}" for suggestion in enhanced_context["suggestions"]])}"""

        # 特殊处理：为重构Agent添加错误信息
        if node_name == "RefactoringAgent" and hasattr(orchestrator.task_ledger, 'error_history') and orchestrator.task_ledger.error_history:
            latest_error = orchestrator.task_ledger.error_history[-1]
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

    @staticmethod
    def format_current_state(orchestrator) -> str:
        """格式化当前执行状态"""
        state_info = []
        for node, state in orchestrator.progress_ledger.node_states.items():
            retry_count = orchestrator.progress_ledger.retry_counts.get(node, 0)
            state_info.append(f"{node}: {state.value} (重试: {retry_count})")
        return "\n".join(state_info)

    @staticmethod
    async def generate_specific_instruction(orchestrator, node_name: str) -> str:
        """为特定节点生成具体执行指令 - 集成智能路径解析"""
        # 获取节点的历史执行情况
        node_history = [item for item in orchestrator.progress_ledger.execution_history if item.get("node") == node_name]

        # 检查依赖关系和前置条件
        dependency_info = await OrchestratorHelpers.check_dependencies(orchestrator, node_name)

        # 初始化智能路径解析器
        path_resolver = orchestrator._initialize_path_resolver()

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

        当前任务：{orchestrator.task_ledger.original_task}

        Agent 描述：{orchestrator.task_ledger.agent_capabilities.get(node_name, '未知')}

        执行计划：{orchestrator.task_ledger.plan[0] if orchestrator.task_ledger.plan else '无'}

        历史执行情况：
        {OrchestratorHelpers.format_node_history(node_history)}

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
            response = await orchestrator.model_client.create([
                UserMessage(content=instruction_prompt, source="orchestrator")
            ])
            return response.content.strip()
        except Exception as e:
            # 返回默认指令
            return OrchestratorHelpers.get_default_instruction(orchestrator, node_name, dependency_info)

    @staticmethod
    async def check_dependencies(orchestrator, node_name: str) -> str:
        """检查节点的依赖关系和前置条件"""
        dependency_info = []

        # 检查已完成的节点和它们的输出
        completed_nodes = []
        for node, state in orchestrator.progress_ledger.node_states.items():
            if state == NodeState.COMPLETED:
                completed_nodes.append(node)

        dependency_info.append(f"已完成的节点: {completed_nodes}")

        # 根据节点类型检查特定依赖
        main_file_path = orchestrator.task_ledger.get_file_path('main')
        test_file_path = orchestrator.task_ledger.get_file_path('test')

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
            # RefactoringAgent 只在测试失败时触发，不需要等待其他Agent
            if "UnitTestAgent" in orchestrator.progress_ledger.node_states:
                unit_test_state = orchestrator.progress_ledger.node_states["UnitTestAgent"]
                if unit_test_state == NodeState.FAILED:
                    dependency_info.append("✅ 检测到单元测试失败，可以进行智能修复")
                else:
                    dependency_info.append("⚠️ 单元测试未失败，重构Agent可能不需要执行")
            else:
                dependency_info.append("❌ 单元测试尚未执行，无法确定是否需要重构")

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

    @staticmethod
    def get_default_instruction(orchestrator, node_name: str, dependency_info: str) -> str:
        """获取默认指令"""
        main_file_path = orchestrator.task_ledger.get_file_path('main')
        test_file_path = orchestrator.task_ledger.get_file_path('test')
        project_name = orchestrator.task_ledger.project_config.get('project_name', 'custom_project')

        base_instructions = {
            "CodePlanningAgent": f"分析{project_name}需求，制定详细的实现计划。明确指定所有文件保存在 /Users/jabez/output 目录下，主代码文件为 {main_file_path}，测试文件为 {test_file_path}。",
            "FunctionWritingAgent": f"编写完整的{project_name}代码，保存到 {main_file_path} 文件中。确保包含所有必要的函数实现。",
            "TestGenerationAgent": f"读取 {main_file_path} 文件中的代码，为每个函数生成完整的测试用例，保存到 {test_file_path} 文件中。",
            "UnitTestAgent": f"执行 {test_file_path} 中的测试用例，生成详细的测试报告。使用 sys.path.insert(0, '/Users/jabez/output') 确保能导入模块。",
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

    @staticmethod
    def format_node_history(node_history: List[Dict[str, Any]]) -> str:
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

    @staticmethod
    def _format_dependency_outputs(dependency_outputs: dict) -> str:
        """格式化依赖Agent输出信息"""
        if not dependency_outputs:
            return "        无依赖输出"

        formatted_lines = []
        for agent_name, outputs in dependency_outputs.items():
            formatted_lines.append(f"        {agent_name}:")
            if isinstance(outputs, dict):
                for key, value in outputs.items():
                    if isinstance(value, str) and len(value) > 100:
                        value = value[:100] + "..."
                    formatted_lines.append(f"          {key}: {value}")
            else:
                formatted_lines.append(f"          {str(outputs)[:100]}...")

        return "\n".join(formatted_lines)
