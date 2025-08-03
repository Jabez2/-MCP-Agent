"""
核心编排器类

高级图流程编排器 - 结合 GraphFlow 和 MagenticOne 的智能调度
负责任务分解、智能执行、监控和错误处理。
"""

import asyncio
import json
import time
from typing import Any, Dict, List, Optional, Set, Sequence
from autogen_agentchat.base import ChatAgent, Response
from autogen_agentchat.messages import TextMessage, StopMessage
from autogen_core.models import UserMessage

from .data_structures import NodeState, TaskLedger, ProgressLedger
from .orchestrator_helpers import OrchestratorHelpers
from ..utils.file_naming import parse_task_and_generate_config
from ..utils.workflow_logger import WorkflowLogger


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

        # 工作流日志记录器
        self.workflow_logger = WorkflowLogger()

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
        # 记录任务开始
        self.workflow_logger.log_event("info", "开始任务规划阶段")

        # 0. 动态文件命名配置
        self.workflow_logger.log_event("progress", "解析任务并生成文件配置...")
        project_config = await parse_task_and_generate_config(task, self.model_client)

        # 设置项目配置到任务账本
        self.task_ledger.set_project_config(
            project_config["project_name"],
            project_config["main_file"],
            project_config["test_file"]
        )

        # 记录任务和项目配置
        self.workflow_logger.log_task_start(task, {
            "project_name": project_config["project_name"],
            "main_file_path": self.task_ledger.get_file_path('main'),
            "test_file_path": self.task_ledger.get_file_path('test')
        })

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

        self.workflow_logger.log_event("success", "任务分析完成")

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

        self.workflow_logger.log_event("success", "执行计划制定完成，开始多Agent协作")

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
        self.workflow_logger.log_event("info", "开始多Agent协作执行")

        # 获取起始节点
        current_nodes = self._get_source_nodes()
        execution_round = 0

        while current_nodes and self.progress_ledger.stall_count < self.max_stalls:
            execution_round += 1

            # 智能选择下一个要执行的节点
            next_node = await self._intelligent_node_selection(current_nodes)

            if not next_node:
                break

            # 记录Agent开始执行
            agent_description = self.task_ledger.agent_capabilities.get(next_node, "未知功能")
            self.workflow_logger.log_agent_start(next_node, agent_description)

            # 执行节点并监控
            execution_result = await self._execute_node_with_monitoring(next_node)

            # 记录Agent执行完成
            success = execution_result.get("success", False)
            output = execution_result.get("analysis", {}).get("message_content", "")
            duration = execution_result.get("execution_time", 0)

            self.workflow_logger.log_agent_complete(next_node, success, output, duration)

            # 检查是否需要重新选择 Agent
            if execution_result.get("needs_reselection", False):
                self.workflow_logger.log_event("warning", f"Agent {next_node} 需要重新选择")
                alternative_nodes = await self._find_alternative_nodes(next_node)
                if alternative_nodes:
                    current_nodes = alternative_nodes
                    self.workflow_logger.log_event("info", f"选择替代节点: {current_nodes}")
                    continue
                else:
                    self.workflow_logger.log_event("warning", "无替代节点，继续原流程")

            # 检查是否需要重新规划
            if await self._should_replan():
                self.workflow_logger.log_event("warning", "检测到需要重新规划，重新分析任务")
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

        # 记录工作流完成
        completed_agents = len([a for a in self.workflow_logger.workflow_data["agents"] if a["status"] == "completed"])
        total_agents = len(self.workflow_logger.workflow_data["agents"])
        success = completed_agents == total_agents

        summary = {
            "total_rounds": execution_round,
            "completed_agents": completed_agents,
            "total_agents": total_agents,
            "success_rate": completed_agents / total_agents if total_agents > 0 else 0
        }

        self.workflow_logger.log_workflow_complete(success, summary)

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
            start_time = time.time()

            response = await agent.on_messages(
                [TextMessage(source="user", content=enhanced_prompt)],
                cancellation_token=None
            )

            execution_time = time.time() - start_time

            # 分析执行结果
            result_analysis = await self._analyze_execution_result(node_name, response)

            # 检查是否需要立即重新选择 Agent
            if not result_analysis["success"] and await self._should_reselect_agent(node_name, result_analysis):
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
            self.progress_ledger.update_node_state(node_name, NodeState.FAILED)
            self.progress_ledger.stall_count += 1

            return {
                "success": False,
                "error": str(e),
                "analysis": {
                    "success": False,
                    "failure_reasons": [f"执行异常: {str(e)}"],
                    "message_content": "",
                    "has_completion_marker": False
                },
                "node": node_name,
                "execution_time": 0
            }

    async def _build_enhanced_prompt(self, node_name: str) -> str:
        """构建增强的提示 - 使用具体指令和错误信息"""
        return await OrchestratorHelpers.build_enhanced_prompt(self, node_name)

    async def _generate_specific_instruction(self, node_name: str) -> str:
        """为特定节点生成具体执行指令 - 集成智能路径解析"""
        return await OrchestratorHelpers.generate_specific_instruction(self, node_name)

    async def _check_dependencies(self, node_name: str) -> str:
        """检查节点的依赖关系和前置条件"""
        return await OrchestratorHelpers.check_dependencies(self, node_name)

    def _get_default_instruction(self, node_name: str, dependency_info: str) -> str:
        """获取默认指令"""
        return OrchestratorHelpers.get_default_instruction(self, node_name, dependency_info)

    def _format_current_state(self) -> str:
        """格式化当前执行状态"""
        return OrchestratorHelpers.format_current_state(self)

    def _format_node_history(self, node_history: List[Dict[str, Any]]) -> str:
        """格式化节点历史"""
        return OrchestratorHelpers.format_node_history(node_history)

    # ================================
    # 简化的辅助方法实现
    # ================================

    async def _analyze_execution_result(self, node_name: str, response: Response) -> Dict[str, Any]:
        """分析执行结果 - 检查chat_message和inner_messages"""
        try:
            # 收集所有可能包含内容的地方
            all_content = []

            # 1. 检查主要的chat_message内容
            if response.chat_message:
                all_content.append(response.chat_message.content)

            # 2. 检查inner_messages中的内容
            if hasattr(response, 'inner_messages') and response.inner_messages:
                for inner_msg in response.inner_messages:
                    if hasattr(inner_msg, 'content'):
                        all_content.append(str(inner_msg.content))

            # 合并所有内容进行分析
            combined_content = " ".join(filter(None, all_content))

            # 检查预期的完成标记
            completion_markers = {
                "CodePlanningAgent": ["PLANNING_COMPLETE"],
                "FunctionWritingAgent": ["CODING_COMPLETE", "Successfully wrote content"],
                "TestGenerationAgent": ["TESTING_COMPLETE", "Successfully wrote content"],
                "UnitTestAgent": ["UNIT_TESTING_COMPLETE"],
                "RefactoringAgent": ["REFACTORING_COMPLETE"],
                "CodeScanningAgent": ["SCANNING_COMPLETE"],
                "ProjectStructureAgent": ["PROJECT_STRUCTURE_COMPLETE"]
            }

            expected_markers = completion_markers.get(node_name, [])
            has_completion_marker = any(marker in combined_content for marker in expected_markers)

            # 调整成功判断逻辑 - 如果有完成标记，内容长度要求可以放宽
            if has_completion_marker:
                # 特殊处理：单元测试Agent需要检查测试是否真正通过
                if node_name == "UnitTestAgent":
                    # 检查测试报告文件是否存在失败
                    try:
                        import json
                        import os
                        report_path = "/Users/jabez/output/test_report.json"
                        if os.path.exists(report_path):
                            with open(report_path, 'r', encoding='utf-8') as f:
                                report_data = json.load(f)

                            failures = report_data.get("summary", {}).get("failures", 0)
                            errors = report_data.get("summary", {}).get("errors", 0)

                            if failures > 0 or errors > 0:
                                success = False
                                failure_reasons.append(f"测试报告显示有 {failures} 个失败和 {errors} 个错误")
                            else:
                                success = True
                        else:
                            # 如果没有报告文件，检查输出内容中的测试结果
                            if any(keyword in combined_content.lower() for keyword in ["failed", "error", "assertion"]):
                                success = False
                                failure_reasons.append("输出内容中检测到测试失败信息")
                            else:
                                success = True
                    except Exception as e:
                        # 如果检查报告失败，回退到原逻辑
                        success = True
                else:
                    success = True  # 其他Agent有完成标记就认为成功
            else:
                success = len(combined_content) > 50  # 没有完成标记需要足够的内容

            failure_reasons = []
            if not has_completion_marker and len(combined_content) <= 50:
                failure_reasons.append(f"缺少完成标记: {expected_markers} 且输出内容过短")
            elif not has_completion_marker:
                failure_reasons.append(f"缺少完成标记: {expected_markers}")

            return {
                "success": success,
                "failure_reasons": failure_reasons,
                "message_content": combined_content,
                "has_completion_marker": has_completion_marker
            }

        except Exception as e:
            return {
                "success": False,
                "failure_reasons": [f"分析异常: {str(e)}"],
                "message_content": "",
                "has_completion_marker": False
            }

    async def _should_reselect_agent(self, node_name: str, result_analysis: Dict[str, Any]) -> bool:
        """判断是否需要重新选择Agent"""
        # 简化实现：如果连续失败超过2次，则重新选择
        retry_count = self.progress_ledger.retry_counts.get(node_name, 0)
        return retry_count >= 2 and not result_analysis["success"]

    async def _should_replan(self) -> bool:
        """判断是否需要重新规划"""
        # 简化实现：如果停滞次数过多，则重新规划
        return self.progress_ledger.stall_count >= self.max_stalls

    async def _get_next_executable_nodes(self, current_node: str, execution_result: Dict[str, Any]) -> List[str]:
        """获取下一批可执行节点 - 基于test.py的智能链路选择逻辑"""

        # 特殊处理：单元测试失败的情况
        if current_node == "UnitTestAgent" and not execution_result["success"]:
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
                    "timestamp": time.time()
                }

                if not hasattr(self.task_ledger, 'error_history'):
                    self.task_ledger.error_history = []
                self.task_ledger.error_history.append(error_info)

                return ["RefactoringAgent"]
            else:
                # 如果没有明确的错误信息，尝试重试
                retry_count = self.progress_ledger.retry_counts.get(current_node, 0)
                if retry_count <= self.max_retries:
                    print(f"🔄 未检测到明确错误，重试单元测试")
                    return [current_node]

        # 特殊处理：重构Agent完成后，重新进行单元测试
        elif current_node == "RefactoringAgent" and execution_result["success"]:
            print(f"🔄 重构完成，重新执行单元测试验证修复效果")
            # 重置UnitTestAgent的重试计数，给它新的机会
            if "UnitTestAgent" in self.progress_ledger.retry_counts:
                self.progress_ledger.retry_counts["UnitTestAgent"] = 0
            # 更新节点状态，允许重新执行
            self.progress_ledger.node_states["UnitTestAgent"] = NodeState.NOT_STARTED
            return ["UnitTestAgent"]

        # 特殊处理：单元测试成功后，跳过反思Agent，直接进行代码扫描
        elif current_node == "UnitTestAgent" and execution_result["success"]:
            print(f"✅ 单元测试通过，继续后续流程")
            return ["CodeScanningAgent"]  # 跳过ReflectionAgent

        # 一般失败处理：智能重试和替代
        if not execution_result["success"]:
            retry_count = self.progress_ledger.retry_counts.get(current_node, 0)

            if retry_count <= self.max_retries:
                print(f"🔄 {current_node} 执行失败，准备重试 (第{retry_count + 1}次)")
                return [current_node]  # 重试当前节点
            else:
                print(f"❌ {current_node} 重试次数已达上限，寻找替代方案")
                # 寻找可以替代或修复的节点
                alternative_nodes = await self._find_alternative_nodes(current_node)
                if alternative_nodes:
                    print(f"🔄 找到替代节点: {alternative_nodes}")
                    return alternative_nodes

        # 正常流程：按预定义顺序执行
        normal_flow_sequence = [
            "CodePlanningAgent", "FunctionWritingAgent", "TestGenerationAgent",
            "UnitTestAgent", "CodeScanningAgent", "ProjectStructureAgent"
        ]

        try:
            current_index = normal_flow_sequence.index(current_node)
            if current_index + 1 < len(normal_flow_sequence):
                next_node = normal_flow_sequence[current_index + 1]
                print(f"➡️ 正常流程：{current_node} -> {next_node}")
                return [next_node]
        except ValueError:
            # 如果当前节点不在正常流程中，返回空列表结束
            pass

        return []  # 结束流程

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

    async def _generate_final_result(self) -> StopMessage:
        """生成最终结果"""
        # 统计执行结果
        completed_nodes = [node for node, state in self.progress_ledger.node_states.items()
                          if state == NodeState.COMPLETED]
        failed_nodes = [node for node, state in self.progress_ledger.node_states.items()
                       if state == NodeState.FAILED]

        final_message = f"""
🎉 多Agent协作流程执行完成！

📊 执行统计：
✅ 成功完成的Agent: {len(completed_nodes)}
❌ 执行失败的Agent: {len(failed_nodes)}
🔄 总执行轮次: {len(self.progress_ledger.execution_history)}

📋 详细结果：
成功: {', '.join(completed_nodes)}
失败: {', '.join(failed_nodes) if failed_nodes else '无'}

🎯 项目配置：
项目名称: {self.task_ledger.project_config.get('project_name', '未设置')}
主文件: {self.task_ledger.get_file_path('main')}
测试文件: {self.task_ledger.get_file_path('test')}

感谢使用基于MCP的多链代码生成Agent系统！
        """

        return StopMessage(content=final_message, source="orchestrator")
