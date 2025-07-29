"""
动态文件命名系统

提供基于任务内容的智能文件命名功能。
"""

import json
from typing import Dict
from autogen_core.models import UserMessage


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
        response = await model_client.create([
            UserMessage(content=parsing_prompt, source="task_parser")
        ])

        # 解析JSON响应
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
