---
type: "always_apply"
---

项目中的LLM API为OPENAI格式。信息如下：
gpt-4o:
model_client = OpenAIChatCompletionClient(
        model="gpt-4o",
        api_key="sk-prlzG7NFLAzsjA5NFxs9BpabsRXbo8tHGFKX8AfLp2xX7B1s",
        base_url="https://try-chatapi.com/v1"
    )

qwen3-coder:
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