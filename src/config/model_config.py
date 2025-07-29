"""
LLM模型配置

提供LLM模型客户端的创建和配置功能。
"""

from autogen_core.models import ModelInfo
from autogen_ext.models.openai import OpenAIChatCompletionClient


def create_model_client():
    """创建LLM模型客户端"""
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
