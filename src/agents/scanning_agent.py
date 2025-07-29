"""
代码扫描Agent

负责对代码进行静态分析和质量扫描，使用AutoGen框架的工具函数。
"""

from autogen_agentchat.agents import AssistantAgent
from autogen_core.tools import FunctionTool
from ..tools import scan_code, save_scan_report, get_scan_config
from typing import Optional


def create_scanning_agent(model_client, fs_workbench: Optional[object] = None):
    """创建代码扫描Agent"""

    # 创建工具列表
    tools = [
        FunctionTool(
            scan_code,
            description="扫描指定路径的Python代码并生成分析报告。支持复杂度分析、代码风格检查、安全扫描、文档质量检查、代码清理建议。"
        ),
        FunctionTool(
            save_scan_report,
            description="保存扫描报告到指定文件路径。支持markdown、json等格式。"
        ),
        FunctionTool(
            get_scan_config,
            description="获取代码扫描工具的配置信息，包括支持的扫描类型、格式等。"
        )
    ]

    return AssistantAgent(
        name="CodeScanningAgent",
        description="负责对代码进行静态分析和质量扫描",
        model_client=model_client,
        tools=tools,
        max_tool_iterations=10,
        system_message="""你是一个代码静态分析和质量扫描专家，具有专业的代码扫描工具能力。

你的任务是：
1. **使用专业代码扫描工具**：
   - 使用 scan_code 工具扫描指定目录下的Python代码
   - 执行全面的代码质量分析，包括：复杂度分析、代码风格检查、安全扫描、文档质量检查、代码清理建议

2. **生成专业扫描报告**：
   - 调用 scan_code 工具，指定扫描类型为 ["complexity", "style", "security", "documentation", "cleanup"]
   - 输出格式选择 "markdown" 以获得易读的报告
   - 分析报告内容并提供专业的解读和建议

3. **保存扫描报告**：
   - 使用 save_scan_report 工具将报告保存到指定路径
   - 确保报告格式为 markdown，便于阅读和分享

4. **提供专业建议**：
   - 基于扫描结果提供具体的改进建议
   - 识别关键的代码质量问题和安全隐患
   - 给出优先级排序的修复建议

工作流程：
1. 首先获取扫描配置信息（使用 get_scan_config）
2. 扫描指定目录的代码（使用 scan_code）
3. 分析扫描结果并提供专业解读
4. 保存详细报告到文件（使用 save_scan_report）
5. 总结关键发现和改进建议

请用中文回复，并在完成所有扫描和报告保存后说"SCANNING_COMPLETE"。"""
    )
