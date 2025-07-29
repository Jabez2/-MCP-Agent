"""
八Agent协作示例：代码规划 + 函数编写 + 测试用例生成 + 单元测试执行 + 反思规划 + 代码重构 + 代码扫描 + 项目目录生成
演示完整的代码生成、测试、验证、反思、重构、质量扫描和项目结构化流程
使用高级调度系统：结合 GraphFlow 的结构化执行和 MagenticOne 的智能调度
"""
import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Set, Sequence
from dataclasses import dataclass, field
from enum import Enum

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import DiGraphBuilder, GraphFlow
from autogen_agentchat.conditions import TextMentionTermination, MaxMessageTermination
from autogen_agentchat.ui import Console
from autogen_agentchat.messages import BaseChatMessage, TextMessage, StopMessage
from autogen_agentchat.base import ChatAgent, Response, TaskResult
from autogen_core.models import UserMessage
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.tools.mcp import McpWorkbench, StdioServerParams


class NodeState(Enum):
    """节点执行状态"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class TaskLedger:
    """任务账本 - 管理全局任务状态"""
    original_task: str = ""
    facts: List[str] = field(default_factory=list)
    guesses: List[str] = field(default_factory=list)
    plan: List[str] = field(default_factory=list)
    agent_capabilities: Dict[str, str] = field(default_factory=dict)
    failed_paths: List[str] = field(default_factory=list)

    def update_facts(self, new_facts: List[str]):
        """更新已确认的事实"""
        self.facts.extend(new_facts)

    def update_plan(self, new_plan: List[str]):
        """更新执行计划"""
        self.plan = new_plan


@dataclass
class ProgressLedger:
    """进度账本 - 管理执行进度"""
    node_states: Dict[str, NodeState] = field(default_factory=dict)
    execution_history: List[Dict[str, Any]] = field(default_factory=list)
    current_active_nodes: Set[str] = field(default_factory=set)
    stall_count: int = 0
    retry_counts: Dict[str, int] = field(default_factory=dict)

    def update_node_state(self, node_name: str, state: NodeState):
        """更新节点状态"""
        self.node_states[node_name] = state
        self.execution_history.append({
            "node": node_name,
            "state": state.value,
            "timestamp": asyncio.get_event_loop().time()
        })

    def increment_retry(self, node_name: str) -> int:
        """增加重试计数"""
        self.retry_counts[node_name] = self.retry_counts.get(node_name, 0) + 1
        return self.retry_counts[node_name]


class GraphFlowOrchestrator:
    """高级图流程编排器 - 结合 GraphFlow 和 MagenticOne 的智能调度"""

    def __init__(self, graph, participants: List[ChatAgent], model_client, max_stalls: int = 3, max_retries: int = 2):
        self.graph = graph
        self.participants = {agent.name: agent for agent in participants}
        self.model_client = model_client
        self.max_stalls = max_stalls
        self.max_retries = max_retries

        # MagenticOne 风格的状态管理
        self.task_ledger = TaskLedger()
        self.progress_ledger = ProgressLedger()

        # 初始化节点状态
        for node_name in self.participants.keys():
            self.progress_ledger.node_states[node_name] = NodeState.NOT_STARTED

        # 分析 Agent 能力
        self._analyze_agent_capabilities()

    def _analyze_agent_capabilities(self):
        """分析 Agent 能力"""
        for name, agent in self.participants.items():
            self.task_ledger.agent_capabilities[name] = agent.description

    async def run_stream(self, task: str):
        """运行高级调度的工作流"""
        self.task_ledger.original_task = task

        # 外层循环：任务分解和计划制定
        await self._outer_loop_planning(task)

        # 内层循环：智能执行和监控
        async for event in self._inner_loop_execution():
            yield event

    async def _outer_loop_planning(self, task: str):
        """外层循环：任务分解和计划制定"""
        print(f"\n🧠 【任务规划阶段】")
        print(f"原始任务: {task}")

        facts_prompt = f"""
        分析以下任务并收集相关事实：

        任务：{task}

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

        print(f"\n� 事实分析结果:")
        print(f"{facts_analysis}")

        # 2. 制定执行计划
        plan_prompt = f"""
        基于以下信息制定详细的执行计划：

        任务：{task}
        事实分析：{facts_analysis}

        可用 Agent：
        {self._format_team_description()}

        请制定一个步骤清晰的执行计划，说明每个 Agent 的具体任务。
        """

        response = await self.model_client.create([
            UserMessage(content=plan_prompt, source="orchestrator")
        ])

        plan_content = response.content
        self.task_ledger.plan = [plan_content]

        print(f"� LLM 执行计划结果:")
        print(f"\n📊 执行计划:")
        print(f"{plan_content}")
        print(f"\n✅ 规划完成，开始执行\n")

    def _format_team_description(self) -> str:
        """格式化团队描述"""
        descriptions = []
        for name, description in self.task_ledger.agent_capabilities.items():
            descriptions.append(f"{name}: {description}")
        return "\n".join(descriptions)

    async def _inner_loop_execution(self):
        """内层循环：智能执行和监控"""
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
                # 从候选列表中移除失败的节点，重新选择
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
        yield TaskResult(
            messages=all_messages,
            stop_reason="高级调度执行完成"
        )

    def _get_source_nodes(self) -> List[str]:
        """获取图的源节点（入度为0的节点）"""
        # 简化实现：返回第一个节点作为起始点
        return ["CodePlanningAgent"]

    async def _intelligent_node_selection(self, candidate_nodes: List[str]) -> Optional[str]:
        """智能节点选择算法 - 基于 MagenticOne 的进度账本分析"""
        if not candidate_nodes:
            return None

        # 如果只有一个候选，使用进度账本分析生成具体指令
        if len(candidate_nodes) == 1:
            selected_node = candidate_nodes[0]

            # 生成具体执行指令
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
        """分析进度账本 - 基于 MagenticOne 的实现"""
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
        """获取默认的进度分析"""
        return {
            "is_request_satisfied": {"reason": "默认分析", "answer": False},
            "is_in_loop": {"reason": "默认分析", "answer": False},
            "is_progress_being_made": {"reason": "默认分析", "answer": True},
            "next_speaker": {"reason": "默认选择第一个候选", "answer": candidate_nodes[0]},
            "instruction_or_question": {"reason": "默认指令", "answer": f"请继续执行你的专业任务"}
        }

    async def _generate_specific_instruction(self, node_name: str) -> str:
        """为特定节点生成具体执行指令"""
        # 获取节点的历史执行情况
        node_history = [item for item in self.progress_ledger.execution_history if item.get("node") == node_name]

        # 检查依赖关系和前置条件
        dependency_info = await self._check_dependencies(node_name)

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

        请生成一个具体、明确的指令，告诉这个 Agent 应该做什么。指令应该：
        1. 明确具体的任务目标
        2. 包含必要的上下文信息和依赖文件路径
        3. 指出需要避免的问题（如果有历史失败）
        4. 说明预期的输出格式和成功标准
        5. 包含具体的文件路径和操作步骤

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
        if node_name == "TestGenerationAgent":
            if "FunctionWritingAgent" in completed_nodes:
                dependency_info.append("✅ FunctionWritingAgent 已完成，可以读取生成的代码文件")
                dependency_info.append("📁 预期代码文件位置: D:/output/string_operations.py")
            else:
                dependency_info.append("❌ FunctionWritingAgent 未完成，无法生成测试")

        elif node_name == "UnitTestAgent":
            if "TestGenerationAgent" in completed_nodes:
                dependency_info.append("✅ TestGenerationAgent 已完成，可以执行测试")
                dependency_info.append("📁 预期测试文件位置: D:/output/test_*.py")
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
                dependency_info.append("📁 预期扫描文件: D:/output/string_operations.py")
            else:
                dependency_info.append("❌ FunctionWritingAgent 未完成，无法扫描代码")

        return "\n".join(dependency_info)

    def _get_default_instruction(self, node_name: str, dependency_info: str) -> str:
        """获取默认指令"""
        base_instructions = {
            "FunctionWritingAgent": "编写完整的字符串操作函数代码，保存到 D:/output/string_operations.py 文件中。确保包含所有必要的函数实现。",
            "TestGenerationAgent": "读取 D:/output/string_operations.py 文件中的代码，为每个函数生成完整的测试用例，保存到 D:/output/test_string_operations.py 文件中。",
            "UnitTestAgent": "执行 D:/output/test_string_operations.py 中的测试用例，生成详细的测试报告。",
            "CodeScanningAgent": "扫描 D:/output/string_operations.py 文件，进行静态代码分析，生成质量报告。",
            "ProjectStructureAgent": "创建完整的项目目录结构，包含 src、tests、docs 等文件夹，并生成必要的配置文件。"
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

    def _build_conversation_history(self) -> str:
        """构建对话历史"""
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

    def _format_current_state(self) -> str:
        """格式化当前执行状态"""
        state_info = []
        for node, state in self.progress_ledger.node_states.items():
            retry_count = self.progress_ledger.retry_counts.get(node, 0)
            state_info.append(f"{node}: {state.value} (重试: {retry_count})")
        return "\n".join(state_info)

    def _print_current_state(self):
        """打印当前详细状态"""
        print(f"   📊 节点状态统计:")
        state_counts = {}
        for state in self.progress_ledger.node_states.values():
            state_counts[state.value] = state_counts.get(state.value, 0) + 1

        for state, count in state_counts.items():
            print(f"      {state}: {count} 个节点")

        print(f"   📈 执行历史:")
        print(f"      历史记录数: {len(self.progress_ledger.execution_history)}")
        print(f"      重试统计: {dict(self.progress_ledger.retry_counts)}")
        print(f"      停滞计数: {self.progress_ledger.stall_count}")

        print(f"   🎯 任务账本状态:")
        print(f"      失败路径: {len(self.task_ledger.failed_paths)}")
        print(f"      事实条目: {len(self.task_ledger.facts)}")
        print(f"      计划条目: {len(self.task_ledger.plan)}")

    async def _execute_node_with_monitoring(self, node_name: str) -> Dict[str, Any]:
        """执行节点并监控结果"""
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
                print(f"� Agent 输出:")
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
        """构建增强的提示 - 使用具体指令"""
        # 获取为该节点生成的具体指令
        specific_instruction = ""
        if hasattr(self.progress_ledger, 'node_instructions') and node_name in self.progress_ledger.node_instructions:
            specific_instruction = self.progress_ledger.node_instructions[node_name]
        else:
            # 如果没有预生成的指令，现在生成
            specific_instruction = await self._generate_specific_instruction(node_name)

        # 构建增强的上下文提示
        enhanced_prompt = f"""
        【具体执行指令】
        {specific_instruction}

        【任务背景】
        原始任务：{self.task_ledger.original_task}

        【执行计划】
        {self.task_ledger.plan[0] if self.task_ledger.plan else "无具体计划"}

        【当前状态】
        {self._format_current_state()}

        【重要提醒】
        - 请严格按照上述具体指令执行
        - 确保完成后输出相应的完成标记
        - 如果遇到问题，请详细说明具体情况
        - 对于文件操作类任务，确保成功调用相关工具
        """

        return enhanced_prompt

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

    def _analyze_tool_calls(self, node_name: str, response: Response) -> Dict[str, Any]:
        """分析工具调用情况"""
        tool_calls = []
        successful_calls = []
        failed_calls = []

        # 检查响应消息内容中的成功标记
        message_content = response.chat_message.content if response.chat_message else ""

        # 如果响应是 ToolCallSummaryMessage，直接检查内容
        if "Successfully wrote content" in message_content:
            successful_calls.append({
                "type": "file_write",
                "content": message_content,
                "status": "success"
            })

        # 检查 inner_messages
        if hasattr(response, 'inner_messages') and response.inner_messages:
            for msg in response.inner_messages:
                msg_str = str(msg)
                if 'ToolCallRequest' in str(type(msg)):
                    tool_calls.append({
                        "type": "request",
                        "tool_name": getattr(msg, 'tool_name', 'unknown'),
                        "content": msg_str[:200]
                    })
                elif 'ToolCallExecution' in str(type(msg)):
                    if "Successfully" in msg_str or "success" in msg_str.lower():
                        successful_calls.append({
                            "type": "execution",
                            "content": msg_str[:200],
                            "status": "success"
                        })
                    else:
                        failed_calls.append({
                            "type": "execution",
                            "content": msg_str[:200],
                            "status": "failed"
                        })

        return {
            "total_calls": len(tool_calls),
            "successful_calls": len(successful_calls),
            "failed_calls": len(failed_calls),
            "tool_calls": tool_calls,
            "successful_executions": successful_calls,
            "failed_executions": failed_calls
        }

    def _evaluate_agent_specific_success(self, node_name: str, response: Response, message_content: str, tool_calls: Dict[str, Any]) -> Dict[str, Any]:
        """基于 Agent 类型评估具体成功标准"""
        failure_reasons = []
        meets_requirements = True

        if node_name == "FunctionWritingAgent":
            # 检查是否成功写入文件
            if tool_calls["successful_calls"] == 0:
                failure_reasons.append("没有成功的文件写入操作")
                meets_requirements = False
            else:
                # 检查是否有成功的写入操作
                has_successful_write = any(
                    "successfully wrote" in call.get("content", "").lower()
                    for call in tool_calls["successful_executions"]
                )

                # 如果没有在工具调用中找到，检查消息内容
                if not has_successful_write and "successfully wrote content" in message_content.lower():
                    has_successful_write = True

                if not has_successful_write:
                    failure_reasons.append("没有检测到成功的文件写入操作")
                    meets_requirements = False

                # 额外检查：确保写入的是实际代码而不是路径设置
                if has_successful_write:
                    if "default filesystem path" in message_content.lower() and len(message_content.strip()) < 100:
                        failure_reasons.append("只设置了路径，没有实际写入代码内容")
                        meets_requirements = False

        elif node_name == "TestGenerationAgent":
            # 检查是否生成了测试文件
            if tool_calls["successful_calls"] == 0:
                failure_reasons.append("没有成功的测试文件生成操作")
                meets_requirements = False
            elif not any("test" in call.get("content", "").lower() for call in tool_calls["successful_executions"]):
                failure_reasons.append("没有检测到测试文件生成")
                meets_requirements = False

            # 检查是否有访问拒绝错误
            if "access denied" in message_content.lower() or "permission denied" in message_content.lower():
                failure_reasons.append("文件访问被拒绝，无法生成测试文件")
                meets_requirements = False

            # 检查是否只设置了路径而没有实际生成测试
            if "default filesystem path" in message_content.lower() and len(message_content.strip()) < 100:
                failure_reasons.append("只设置了路径，没有实际生成测试文件")
                meets_requirements = False

        elif node_name == "UnitTestAgent":
            # 检查是否执行了测试
            if tool_calls["total_calls"] == 0:
                failure_reasons.append("没有执行任何代码运行操作")
                meets_requirements = False
            elif "Error:" in message_content and "ModuleNotFoundError" in message_content:
                failure_reasons.append("找不到测试模块，测试执行失败")
                meets_requirements = False
            elif "Command failed" in message_content:
                failure_reasons.append("测试命令执行失败")
                meets_requirements = False

        elif node_name in ["CodePlanningAgent", "ReflectionAgent"]:
            # 检查内容质量
            if len(message_content.strip()) < 200:
                failure_reasons.append("输出内容过于简短")
                meets_requirements = False

        elif node_name == "RefactoringAgent":
            # 检查是否请求了更多信息而不是实际重构
            if "请提供" in message_content or "需要更多信息" in message_content:
                failure_reasons.append("Agent 请求更多信息而不是执行重构")
                meets_requirements = False

        elif node_name == "CodeScanningAgent":
            # 检查是否只设置了路径而没有实际扫描
            if "default filesystem path" in message_content.lower() and len(message_content.strip()) < 100:
                failure_reasons.append("只设置了路径，没有实际执行代码扫描")
                meets_requirements = False

        elif node_name == "ProjectStructureAgent":
            # 检查是否只设置了路径而没有实际创建结构
            if "default filesystem path" in message_content.lower() and len(message_content.strip()) < 100:
                failure_reasons.append("只设置了路径，没有实际创建项目结构")
                meets_requirements = False

        # 通用检查
        if tool_calls["failed_calls"] > 0:
            failure_reasons.append(f"有 {tool_calls['failed_calls']} 个工具调用失败")

        return {
            "meets_requirements": meets_requirements,
            "failure_reasons": failure_reasons,
            "evaluation_details": {
                "node_type": node_name,
                "content_length": len(message_content),
                "tool_success_rate": tool_calls["successful_calls"] / max(1, tool_calls["total_calls"])
            }
        }

    async def _update_progress_ledger(self, node_name: str, execution_result: Dict[str, Any]):
        """更新进度账本"""
        # 记录执行历史
        history_entry = {
            "node": node_name,
            "result": execution_result,
            "timestamp": asyncio.get_event_loop().time()
        }
        self.progress_ledger.execution_history.append(history_entry)

        # 如果执行失败，考虑重试
        if not execution_result["success"]:
            retry_count = self.progress_ledger.increment_retry(node_name)

            if retry_count <= self.max_retries:
                print(f"🔄 准备重试 {node_name} (第 {retry_count} 次)")
                self.progress_ledger.update_node_state(node_name, NodeState.RETRYING)
            else:
                print(f"❌ {node_name} 重试次数已达上限")
                self.task_ledger.failed_paths.append(node_name)

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
        """获取下一批可执行节点 - 支持智能重试和依赖检查"""
        # 如果节点失败，首先检查重试
        if not execution_result["success"]:
            retry_count = self.progress_ledger.retry_counts.get(completed_node, 0)

            if retry_count <= self.max_retries:
                print(f"🔄 {completed_node} 执行失败，准备重试")
                return [completed_node]  # 重试当前节点
            else:
                print(f"❌ {completed_node} 重试次数已达上限，寻找替代方案")
                # 寻找可以替代或修复的节点
                alternative_nodes = await self._find_alternative_nodes(completed_node)
                if alternative_nodes:
                    print(f"🔄 找到替代节点: {alternative_nodes}")
                    return alternative_nodes

        # 获取所有可能的候选节点
        all_candidates = list(self.participants.keys())

        # 移除已经完成的节点（除非需要重试）
        available_candidates = []
        for candidate in all_candidates:
            node_state = self.progress_ledger.node_states.get(candidate, NodeState.NOT_STARTED)
            retry_count = self.progress_ledger.retry_counts.get(candidate, 0)

            # 如果节点未开始，或者失败但可以重试，或者需要根据条件重新执行
            if (node_state == NodeState.NOT_STARTED or
                (node_state == NodeState.FAILED and retry_count <= self.max_retries) or
                self._should_revisit_node(candidate, execution_result)):
                available_candidates.append(candidate)

        if not available_candidates:
            print(f"🏁 无可用候选节点，流程结束")
            return []

        # 基于依赖关系和智能分析选择下一个节点
        next_nodes = await self._intelligent_next_node_selection(completed_node, execution_result, available_candidates)

        return next_nodes

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

    async def _intelligent_next_node_selection(self, completed_node: str, execution_result: Dict[str, Any], available_candidates: List[str]) -> List[str]:
        """基于依赖关系和智能分析选择下一个节点"""
        # 检查依赖关系
        dependency_ready_nodes = []

        for candidate in available_candidates:
            if await self._check_node_dependencies_ready(candidate):
                dependency_ready_nodes.append(candidate)

        if not dependency_ready_nodes:
            print(f"⚠️ 没有依赖关系就绪的节点，选择第一个可用节点")
            return [available_candidates[0]] if available_candidates else []

        # 优先选择依赖关系就绪的节点
        print(f"✅ 依赖关系就绪的节点: {dependency_ready_nodes}")

        # 根据优先级排序
        prioritized_nodes = self._prioritize_nodes(dependency_ready_nodes, completed_node)

        return [prioritized_nodes[0]] if prioritized_nodes else []

    async def _check_node_dependencies_ready(self, node_name: str) -> bool:
        """检查节点的依赖关系是否就绪"""
        dependencies = {
            "TestGenerationAgent": ["FunctionWritingAgent"],
            "UnitTestAgent": ["TestGenerationAgent"],
            "RefactoringAgent": ["ReflectionAgent"],
            "CodeScanningAgent": ["FunctionWritingAgent"],
            "ProjectStructureAgent": []  # 无依赖
        }

        required_deps = dependencies.get(node_name, [])

        for dep in required_deps:
            dep_state = self.progress_ledger.node_states.get(dep, NodeState.NOT_STARTED)
            if dep_state != NodeState.COMPLETED:
                return False

        return True

    def _prioritize_nodes(self, nodes: List[str], completed_node: str) -> List[str]:
        """根据优先级对节点排序"""
        # 定义节点优先级
        priority_order = [
            "CodePlanningAgent",
            "FunctionWritingAgent",
            "TestGenerationAgent",
            "UnitTestAgent",
            "ReflectionAgent",
            "RefactoringAgent",
            "CodeScanningAgent",
            "ProjectStructureAgent"
        ]

        # 按优先级排序
        sorted_nodes = []
        for priority_node in priority_order:
            if priority_node in nodes:
                sorted_nodes.append(priority_node)

        # 添加不在优先级列表中的节点
        for node in nodes:
            if node not in sorted_nodes:
                sorted_nodes.append(node)

        return sorted_nodes

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

    def _should_revisit_node(self, candidate: str, execution_result: Dict[str, Any]) -> bool:
        """判断是否应该重新访问某个节点"""
        message_content = execution_result.get("message_content", "")

        # 基于执行结果的内容判断是否需要重新访问某些节点
        revisit_conditions = {
            "CodePlanningAgent": ["重新规划", "计划有误", "需要重新分析"],
            "FunctionWritingAgent": ["重新编码", "代码问题", "需要修改代码"],
            "TestGenerationAgent": ["重新测试", "测试问题", "测试不足"],
            "RefactoringAgent": ["需要重构", "代码质量", "优化代码"]
        }

        conditions = revisit_conditions.get(candidate, [])
        return any(condition in message_content for condition in conditions)

    async def _select_next_nodes_by_graph(self, completed_node: str, execution_result: Dict[str, Any], available_candidates: List[str]) -> List[str]:
        """基于图结构选择下一个节点"""
        message_content = execution_result.get("message_content", "")
        success = execution_result.get("success", False)

        # 定义条件分支逻辑
        if completed_node == "CodePlanningAgent" and success:
            return ["FunctionWritingAgent"]

        elif completed_node == "FunctionWritingAgent":
            if success:
                return ["TestGenerationAgent"]
            else:
                # 编码失败，可能需要重新规划
                return ["CodePlanningAgent"] if "CodePlanningAgent" in available_candidates else ["FunctionWritingAgent"]

        elif completed_node == "TestGenerationAgent":
            if success:
                return ["UnitTestAgent"]
            else:
                # 测试生成失败，可能需要重新编码
                return ["FunctionWritingAgent"] if "FunctionWritingAgent" in available_candidates else ["TestGenerationAgent"]

        elif completed_node == "UnitTestAgent":
            if "Error:" in message_content or "失败" in message_content:
                # 测试失败，需要重构或重新编码
                if "RefactoringAgent" in available_candidates:
                    return ["RefactoringAgent"]
                elif "FunctionWritingAgent" in available_candidates:
                    return ["FunctionWritingAgent"]
            return ["ReflectionAgent"]

        elif completed_node == "ReflectionAgent":
            if "重新编码" in message_content or "代码问题" in message_content:
                return ["FunctionWritingAgent"] if "FunctionWritingAgent" in available_candidates else ["RefactoringAgent"]
            elif "测试问题" in message_content:
                return ["TestGenerationAgent"] if "TestGenerationAgent" in available_candidates else ["RefactoringAgent"]
            else:
                return ["RefactoringAgent"]

        elif completed_node == "RefactoringAgent" and success:
            return ["CodeScanningAgent"]

        elif completed_node == "CodeScanningAgent" and success:
            return ["ProjectStructureAgent"]

        elif completed_node == "ProjectStructureAgent" and success:
            return []  # 流程结束

        # 默认情况：按顺序选择下一个未完成的节点
        flow_sequence = [
            "CodePlanningAgent", "FunctionWritingAgent", "TestGenerationAgent",
            "UnitTestAgent", "ReflectionAgent", "RefactoringAgent",
            "CodeScanningAgent", "ProjectStructureAgent"
        ]

        try:
            current_index = flow_sequence.index(completed_node)
            for i in range(current_index + 1, len(flow_sequence)):
                next_candidate = flow_sequence[i]
                if next_candidate in available_candidates:
                    return [next_candidate]
        except ValueError:
            pass

        # 如果没有找到合适的下一个节点，返回第一个可用的
        return [available_candidates[0]] if available_candidates else []


async def run_eight_agent_collaboration():
    """运行八Agent协作示例 - 使用高级调度系统"""
    
    # LLM配置
    model_client = OpenAIChatCompletionClient(
        model="gpt-4o",
        api_key="sk-1assV3REKOrgIL908FAOn9ogdallJrYFg1sFQolgZLyJHJ6h",
        base_url="https://try-chatapi.com/v1"
    )
    
    # 配置文件系统MCP服务
    filesystem_mcp_server = StdioServerParams(
        command="node",
        args=[
            "D:\\mcp_multichain_agent\\mcp_services\\filesystem-mcp-server\\dist\\index.js"
        ],
        env={
            "FS_BASE_DIRECTORY": "D:\\output"
        }
    )

    # 配置代码运行MCP服务
    code_runner_mcp_server = StdioServerParams(
        command="node",
        args=[
            "D:\\mcp_multichain_agent\\mcp_services\\mcp-server-code-runner\\dist\\cli.js"
        ]
    )

    # 代码规划Agent
    planning_agent = AssistantAgent(
        name="CodePlanningAgent",
        description="负责分析需求并制定代码实现计划",
        model_client=model_client,
        system_message="""你是一个代码规划专家。
        你的任务是：
        1. 分析用户的需求
        2. 制定详细的实现计划
        3. 将任务分解为具体的函数需求
        4. 为FunctionWritingAgent提供清晰的指导
        
        请用中文回复，并在完成规划后说"PLANNING_COMPLETE"。"""
    )
    
    # 创建MCP工作台并配置Agent
    async with McpWorkbench(filesystem_mcp_server) as fs_workbench, \
               McpWorkbench(code_runner_mcp_server) as code_workbench:
        # 函数编写Agent
        coding_agent = AssistantAgent(
            name="FunctionWritingAgent",
            description="负责根据规划编写具体的Python函数代码并保存到文件",
            model_client=model_client,
            workbench=fs_workbench,
            system_message="""你是一个Python代码编写专家，具有文件操作能力。
            你的任务是：
            1. 根据规划Agent的指导编写Python函数
            2. 确保代码简洁、可读、有注释
            3. 包含必要的错误处理
            4. 将代码保存到output目录下的指定文件中
            5. 你只负责编写业务逻辑代码，绝对不要编写测试代码(重要限制，如test_*.py，测试代码由TestGenerationAgent实现并保存)
            6. 绝对不要编写测试代码(如test_*.py文件)
            7. 如果规划中要求你写测试代码，请忽略该部分
            8. 默认保存目录为D:/output目录下
            9. 测试代码由TestGenerationAgent负责
            你可以使用文件系统工具来创建和保存代码文件。
            请用中文回复，并在完成编写后说"CODING_COMPLETE"。"""
        )
        
        # 测试用例生成Agent
        test_agent = AssistantAgent(
            name="TestGenerationAgent",
            description="负责为已编写的函数生成完整的测试用例并保存到文件",
            model_client=model_client,
            workbench=fs_workbench,
            system_message="""你是一个Python测试专家，具有文件操作能力，负责为FunctionWritingAgents生成的代码编写测试文件

            ⚠️ 重要限制：
            - 你绝对不能修改、重写或覆盖任何业务逻辑代码文件（如math_utils.py等）
            - 你只能创建新的测试文件（test_*.py格式）
            - 如果需要读取业务代码，使用read_file工具
            - 如果发现业务代码有问题，只能在测试文件中注释说明，不能修改业务代码

            你的任务是：
            1. 使用read_file工具读取已编写的函数代码文件
            2. 分析函数的功能和参数
            3. 生成全面的测试用例，包括：
               - 正常情况测试
               - 边界条件测试
               - 异常情况测试
               - 输入验证测试
            4. 使用unittest框架编写测试代码
            5. 使用write_file工具编写业务测试代码，如test_*.py并保存到D:/output文件夹下
            6. 确保测试代码可以直接运行
            7. 测试代码中要根据实际的业务代码异常类型编写正确的断言

            ⚠️ 重要提醒：你必须生成并保存测试文件，不能只分析代码而不保存！

            你可以使用文件系统工具来读取代码文件和保存测试文件。
            请用中文回复，并在完成测试生成后说"TESTING_COMPLETE"。"""
        )

        # 单元测试Agent - 只配置代码运行MCP服务
        unit_test_agent = AssistantAgent(
            name="UnitTestAgent",
            description="负责执行测试用例并生成测试报告",
            model_client=model_client,
            workbench=code_workbench,  # 只配置代码运行MCP工作台
            system_message="""你是一个Python单元测试执行专家，具有代码运行能力。

            ⚠️ 重要限制：
            - 你绝对不能创建、修改或重写任何代码文件
            - 你只能使用run-code工具执行代码，不能使用任何文件操作工具
            - 你的任务仅限于执行测试和生成报告

            你的任务是：
            1. **路径设置（重要）**：
            - 在导入任何模块之前，使用sys.path.insert(0, 'D:/output')添加模块搜索路径
            - 这样可以确保能够正确导入保存在D:/output目录下的模块
            2. 执行TestGenerationAgent编写的测试代码文件test_*.py
            2. 执行测试用例并生成详细报告，使用以下代码模板：
            ```python
            import sys
            sys.path.insert(0, 'D:/output')

            import unittest
            from test_math_utils import TestMathUtils

            # 创建测试套件
            suite = unittest.TestLoader().loadTestsFromTestCase(TestMathUtils)

            # 执行测试并收集结果
            runner = unittest.TextTestRunner(verbosity=2)
            result = runner.run(suite)

            # 生成测试报告
            total_tests = result.testsRun
            passed_tests = total_tests - len(result.failures) - len(result.errors)
            failed_tests = len(result.failures)
            error_tests = len(result.errors)

            print(f"\\n=== 测试报告 ===")
            print(f"总测试数: {total_tests}")
            print(f"通过: {passed_tests}")
            print(f"失败: {failed_tests}")
            print(f"错误: {error_tests}")
            print(f"成功率: {(passed_tests/total_tests)*100:.1f}%")

            if result.failures:
                print("\\n失败的测试:")
                for test, traceback in result.failures:
                    print(f"- {test}: {traceback}")

            if result.errors:
                print("\\n错误的测试:")
                for test, traceback in result.errors:
                    print(f"- {test}: {traceback}")
            ```

            3. 分析测试结果并提供改进建议
            4. 如果测试失败，提供具体的错误信息和修复建议

            请用中文回复，并在完成测试执行后说"UNIT_TESTING_COMPLETE"。"""
        )

        # 反思规划Agent
        reflection_agent = AssistantAgent(
            name="ReflectionAgent",
            description="负责分析整个开发流程的结果并提供反思和建议",
            model_client=model_client,
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

        # 代码重构Agent - 配置文件系统MCP服务
        refactoring_agent = AssistantAgent(
            name="RefactoringAgent",
            description="负责根据反思建议对代码进行重构和优化",
            model_client=model_client,
            workbench=fs_workbench,  # 配置文件系统MCP工作台
            system_message="""你是一个代码重构和优化专家，具有文件操作能力。
            你的任务是：
            1. 读取现有的代码文件，分析代码结构和质量
            2. 根据ReflectionAgent的建议和测试结果进行代码重构
            3. 执行以下类型的重构操作：
               - 代码结构优化（函数拆分、模块化）
               - 变量和函数命名改进
               - 代码注释和文档完善
               - 性能优化
               - 错误处理增强
               - 代码风格统一
            4. 保持代码功能不变，只改进代码质量
            5. 将重构后的代码保存到原文件，覆盖旧版本
            6. 生成重构报告，说明进行了哪些改进

            重要：只有当ReflectionAgent明确建议需要重构时才执行重构操作。
            请用中文回复，并在完成重构后说"REFACTORING_COMPLETE"。"""
        )

        # 代码扫描Agent - 使用文件系统MCP服务
        code_scanning_agent = AssistantAgent(
            name="CodeScanningAgent",
            description="负责对代码进行静态分析和质量扫描",
            model_client=model_client,
            workbench=fs_workbench,  # 使用文件系统MCP工作台
            system_message="""你是一个代码静态分析和质量扫描专家，具有文件操作能力。
            你的任务是：
            1. 读取D:/output/目录下重构后的代码文件
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
               - 具体的改进建议
               - 与重构前的质量对比（如果适用）

            你可以使用文件系统工具读取代码文件，然后编写Python代码进行分析。
            请用中文回复，并在完成代码扫描后说"CODE_SCANNING_COMPLETE"。"""
        )

        # 项目目录生成Agent - 使用文件系统MCP服务
        project_structure_agent = AssistantAgent(
            name="ProjectStructureAgent",
            description="负责生成完整的项目目录结构和配置文件",
            model_client=model_client,
            workbench=fs_workbench,  # 使用文件系统MCP工作台
            system_message="""你是一个项目结构管理专家，具有文件操作能力。
            你的任务是：
            1. 创建标准的Python项目目录结构，包括：
               - src/ 目录存放源代码
               - tests/ 目录存放测试文件
               - docs/ 目录存放文档
               - 项目根目录存放配置文件
            2. 重新组织现有的代码和测试文件
               - 将D:/output/下的源代码文件移动到src/目录
               - 将D:/output/移动到tests/目录
            3. 生成项目配置文件：
               - setup.py（项目安装配置）
               - requirements.txt（依赖列表）
               - .gitignore（Git忽略文件）
               - pytest.ini（测试配置）
            4. 创建项目文档：
               - README.md（项目说明和使用指南）
               - docs/API.md（API文档）
               - CHANGELOG.md（变更日志）
            5. 整理所有报告和文档到docs/目录
            6. 生成项目的完整目录树展示


            请用中文回复，并在完成项目结构生成后说"PROJECT_STRUCTURE_COMPLETE"。"""
        )

        # 创建高级调度系统 - 结合 GraphFlow 结构化执行和 MagenticOne 智能调度
        # 构建执行图：规划 → 编码 → 测试生成 → 单元测试 → 反思 → 重构 → 扫描 → 项目结构
        builder = DiGraphBuilder()
        
        # 添加所有 Agent 节点
        builder.add_node(planning_agent)
        builder.add_node(coding_agent)
        builder.add_node(test_agent)
        builder.add_node(unit_test_agent)
        builder.add_node(reflection_agent)
        builder.add_node(refactoring_agent)
        builder.add_node(code_scanning_agent)
        builder.add_node(project_structure_agent)

        # 构建执行图 - 保持简单的线性结构以避免图验证问题
        # 主流程边
        builder.add_edge(planning_agent, coding_agent)
        builder.add_edge(coding_agent, test_agent)
        builder.add_edge(test_agent, unit_test_agent)
        builder.add_edge(unit_test_agent, reflection_agent)
        builder.add_edge(reflection_agent, refactoring_agent)
        builder.add_edge(refactoring_agent, code_scanning_agent)
        builder.add_edge(code_scanning_agent, project_structure_agent)

        # 构建图
        graph = builder.build()

        # 创建高级调度系统
        orchestrator = GraphFlowOrchestrator(
            graph=graph,
            participants=builder.get_participants(),
            model_client=model_client,
            max_stalls=3,
            max_retries=2
        )
        
        # 测试任务
        task = """请实现一个文本分析工具库，包含以下功能：

1. 单词频率统计：统计文本中每个单词出现的次数
2. 情感分析：判断文本情感倾向（积极、消极或中性）
3. 关键词提取：从文本中提取最重要的关键词

要求：
- 生成的业务代码文件保存为D:\output\text_analyzer.py
- 生成的测试代码文件保存为D:\output\test_text_analyzer.py
- 执行测试用例并生成测试报告
- 分析整个开发流程并提供反思总结
- 包含完整的错误处理和输入验证
- 情感分析功能应使用简单的基于词典的方法
- 关键词提取应考虑词频和重要性
- 代码应有良好的文档和注释
- 实现一个简单的命令行界面供用户使用这些功能
"""

        print(f"\n{'='*100}")
        print(f"🤖 【高级调度系统启动】八Agent协作处理任务")
        print(f"{'='*100}")
        print(f"📝 任务描述: {task}")
        print(f"🧠 智能调度特性:")
        print("   - 🔗 结合 GraphFlow 结构化执行")
        print("   - 🧠 集成 MagenticOne 智能调度")
        print("   - 📋 LLM 驱动的任务分解和计划制定")
        print("   - 🎯 基于上下文的智能节点选择")
        print("   - 🔄 自适应重试和重新规划机制")
        print("   - 📊 实时执行监控和状态管理")
        print("   - 🛡️ 多层次容错和错误恢复")
        print(f"🔄 预定义执行流程:")
        print("   规划 → 编码 → 测试生成 → 单元测试 → 反思 → 重构 → 扫描 → 项目结构")
        print(f"⚙️ 系统配置:")
        print(f"   最大停滞次数: {orchestrator.max_stalls}")
        print(f"   最大重试次数: {orchestrator.max_retries}")
        print(f"   参与 Agent 数: {len(orchestrator.participants)}")
        print(f"{'='*100}")

        # 运行高级调度系统并显示结果
        print(f"🚀 开始执行高级调度系统...")
        await Console(orchestrator.run_stream(task=task))

        print("=" * 80)
        print("✅ 八Agent高级调度协作完成!")
        print("📁 生成的项目结构:")
        print("   string_library/")
        print("   ├── src/")
        print("   │   └── string_utils.py (函数代码，已重构优化)")
        print("   ├── tests/")
        print("   │   └── test_string_utils.py (测试用例)")
        print("   ├── docs/")
        print("   │   ├── README.md (项目说明)")
        print("   │   └── API.md (API文档)")
        print("   ├── requirements.txt (依赖列表)")
        print("   ├── setup.py (安装配置)")
        print("   ├── .gitignore (Git忽略文件)")
        print("   ├── pytest.ini (测试配置)")
        print("   └── CHANGELOG.md (变更日志)")
        print("")
        print("📊 包含的报告:")
        print("   - 测试执行结果和报告")
        print("   - 项目反思总结和质量评估")
        print("   - 代码重构报告和改进说明")
        print("   - 代码静态分析和质量扫描报告")
        print("")
        print("🎯 高级调度系统特点:")
        print("   - 🧠 智能任务分解和计划制定")
        print("   - 🎯 基于 LLM 的智能节点选择")
        print("   - 🔄 自适应重试和重新规划机制")
        print("   - 📊 实时执行监控和状态管理")
        print("   - 🛡️ 容错性和鲁棒性增强")
        print("   - 🔗 结合 GraphFlow 和 MagenticOne 优势")
        print("   - 📈 提高任务完成率和执行质量")


if __name__ == "__main__":
    print("🚀 启动改进的高级调度系统...")
    print("📋 主要改进:")
    print("   - ✅ 增强的输出验证机制")
    print("   - 🔍 智能依赖关系检查")
    print("   - 🔄 自动重新选择失败的 Agent")
    print("   - 📁 确保后续 Agent 能访问前面的输出")
    print("   - 🎯 更精确的成功判断标准")
    print("   - 🛡️ 多层次错误处理和恢复")
    print("\n⚠️  注意：当前版本不会执行代码，仅用于展示改进的调度逻辑")
    print("💡 如需执行，请取消注释下面的代码行")
    asyncio.run(run_eight_agent_collaboration())
