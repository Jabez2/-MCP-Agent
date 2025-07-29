"""
反思规划Agent

负责分析整个开发流程的结果并提供反思和建议。
"""

from autogen_agentchat.agents import AssistantAgent


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
