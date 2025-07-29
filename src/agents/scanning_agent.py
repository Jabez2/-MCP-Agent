"""
代码扫描Agent

负责对代码进行静态分析和质量扫描。
"""

from autogen_agentchat.agents import AssistantAgent


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
