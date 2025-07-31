#!/usr/bin/env python3
"""
单独测试ProjectStructureAgent

测试项目结构整理Agent的功能，包括：
1. 创建项目文档
2. 整理文件结构
3. 生成配置文件
"""

import asyncio
import os
from pathlib import Path

from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.tools.mcp import McpWorkbench, StdioServerParams
from autogen_agentchat.messages import TextMessage
from autogen_core.models import ModelInfo

from src.agents.structure_agent import create_structure_agent
from src.config.mcp_config import create_mcp_servers


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


async def setup_test_environment():
    """设置测试环境"""
    print("🔧 设置测试环境...")
    
    # 创建测试目录
    test_dir = Path("/Users/jabez/output")
    test_dir.mkdir(parents=True, exist_ok=True)
    
    # 创建示例项目文件
    files_to_create = {
        "string_utils.py": '''"""
字符串工具库
"""

def reverse_string(s: str) -> str:
    """反转字符串"""
    if not isinstance(s, str):
        raise TypeError("输入必须是字符串")
    return s[::-1]

def count_chars(s: str) -> dict:
    """统计字符出现次数"""
    if not isinstance(s, str):
        raise TypeError("输入必须是字符串")
    return {char: s.count(char) for char in set(s)}
''',
        
        "test_string_utils.py": '''import unittest
import sys
import os

# 添加模块路径
sys.path.insert(0, '/Users/jabez/output')

from string_utils import reverse_string, count_chars


class TestStringUtils(unittest.TestCase):
    """字符串工具测试"""
    
    def test_reverse_string(self):
        """测试字符串反转"""
        self.assertEqual(reverse_string("hello"), "olleh")
        self.assertEqual(reverse_string(""), "")
        self.assertEqual(reverse_string("a"), "a")
    
    def test_count_chars(self):
        """测试字符统计"""
        result = count_chars("hello")
        expected = {'h': 1, 'e': 1, 'l': 2, 'o': 1}
        self.assertEqual(result, expected)
        
        self.assertEqual(count_chars(""), {})


if __name__ == '__main__':
    unittest.main()
''',
        
        "config.json": '''
{
    "project_name": "string_utils",
    "version": "1.0.0",
    "description": "A simple string utility library"
}
''',
        
        "data.txt": "这是一个示例数据文件",
        
        "script.py": '''#!/usr/bin/env python3
"""
示例脚本文件
"""

def main():
    print("Hello from script!")

if __name__ == "__main__":
    main()
'''
    }
    
    # 创建文件
    for filename, content in files_to_create.items():
        file_path = test_dir / filename
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ 创建文件: {file_path}")
    
    print(f"✅ 测试环境设置完成，共创建 {len(files_to_create)} 个文件")
    return test_dir


async def test_structure_agent():
    """测试ProjectStructureAgent"""
    print("\n" + "="*60)
    print("🏗️ 开始测试ProjectStructureAgent")
    print("="*60)
    
    # 1. 设置测试环境
    test_dir = await setup_test_environment()
    
    # 2. 创建模型客户端
    model_client = create_model_client()
    
    # 3. 创建MCP服务器
    filesystem_mcp_server, code_runner_mcp_server = create_mcp_servers()
    
    # 4. 创建工作台和Agent
    async with McpWorkbench(filesystem_mcp_server) as fs_workbench:
        print("🤖 创建ProjectStructureAgent...")
        
        structure_agent = create_structure_agent(model_client, fs_workbench)
        
        print(f"✅ Agent创建成功: {structure_agent.name}")
        print(f"📝 Agent描述: {structure_agent.description}")
        
        # 5. 执行项目结构整理任务
        print("\n🎯 执行项目结构整理任务...")
        
        task_message = f"""
请整理位于 /Users/jabez/output 目录下的项目文件。

当前目录包含以下文件：
- string_utils.py (主要源代码)
- test_string_utils.py (测试文件)
- config.json (配置文件)
- data.txt (数据文件)
- script.py (脚本文件)

具体要求：
1. 分析现有文件的类型和用途
2. 创建合理的目录结构来组织这些文件
3. 生成项目README.md文档，说明项目功能和使用方法
4. 创建requirements.txt文件（即使是空的也要创建）
5. 整理文件到对应的目录中
6. 生成项目结构报告

请开始执行项目结构整理。
"""
        
        try:
            # 发送任务消息给Agent
            response = await structure_agent.on_messages(
                [TextMessage(content=task_message, source="user")],
                cancellation_token=None
            )
            
            print("\n" + "="*60)
            print("📋 Agent执行结果:")
            print("="*60)
            
            if response and response.chat_message:
                content = response.chat_message.content
                print(content)
                
                # 检查是否包含完成标记
                if "PROJECT_STRUCTURE_COMPLETE" in content:
                    print("\n✅ 发现完成标记: PROJECT_STRUCTURE_COMPLETE")
                else:
                    print("\n❌ 未发现完成标记")
            else:
                print("⚠️ Agent没有返回响应")
            
            # 6. 验证生成的文件和目录结构
            print("\n🔍 验证生成的项目结构...")
            
            expected_files = [
                "README.md",
                "requirements.txt"
            ]
            
            for file_name in expected_files:
                file_path = test_dir / file_name
                if file_path.exists():
                    print(f"✅ 文件已生成: {file_path}")
                    # 显示文件内容的前几行
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            lines = f.readlines()[:5]  # 只显示前5行
                            print(f"   内容预览: {len(lines)} 行")
                            for i, line in enumerate(lines, 1):
                                print(f"   {i}: {line.strip()}")
                            if len(f.readlines()) > 5:
                                print("   ...")
                    except Exception as e:
                        print(f"   ⚠️ 读取文件失败: {e}")
                else:
                    print(f"❌ 文件未生成: {file_path}")
            
            # 检查目录结构
            print(f"\n📁 当前目录结构:")
            for item in sorted(test_dir.iterdir()):
                if item.is_file():
                    print(f"   📄 {item.name}")
                elif item.is_dir():
                    print(f"   📁 {item.name}/")
                    # 显示子目录内容
                    for sub_item in sorted(item.iterdir()):
                        if sub_item.is_file():
                            print(f"      📄 {sub_item.name}")
                        elif sub_item.is_dir():
                            print(f"      📁 {sub_item.name}/")
                            
        except Exception as e:
            print(f"❌ 测试执行失败: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            # 7. 清理资源
            await model_client.close()
            print("\n🧹 资源清理完成")


async def main():
    """主函数"""
    print("🚀 启动ProjectStructureAgent测试")
    
    try:
        await test_structure_agent()
        print("\n🎉 测试完成!")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
