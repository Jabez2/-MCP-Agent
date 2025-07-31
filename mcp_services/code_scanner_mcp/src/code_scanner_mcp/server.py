#!/usr/bin/env python3
"""
代码扫描MCP服务器

提供Python代码静态分析和质量扫描功能。
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

from .analyzers import CodeAnalyzer
from .report_generator import ReportGenerator

# 配置日志 - 使用stderr避免干扰stdio通信
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

# 初始化FastMCP服务器
mcp = FastMCP("code-scanner")

# 全局分析器和报告生成器实例
analyzer = CodeAnalyzer()
report_generator = ReportGenerator()


@mcp.tool()
async def scan_code(
    path: str,
    scan_types: List[str] = None,
    output_format: str = "markdown"
) -> str:
    """
    扫描指定路径的Python代码并生成分析报告
    
    Args:
        path: 要扫描的文件或目录路径
        scan_types: 扫描类型列表，可选值：
                   ['complexity', 'style', 'security', 'documentation', 'cleanup']
                   默认为所有类型
        output_format: 输出格式，'json' 或 'markdown'，默认为 'markdown'
    
    Returns:
        代码扫描报告
    """
    try:
        # 验证路径
        target_path = Path(path)
        if not target_path.exists():
            return f"错误：路径 '{path}' 不存在"
        
        # 默认扫描所有类型
        if scan_types is None:
            scan_types = ['complexity', 'style', 'security', 'documentation', 'cleanup']
        
        logger.info(f"开始扫描路径: {path}, 扫描类型: {scan_types}")
        
        # 执行代码分析
        analysis_results = await analyzer.analyze_code(target_path, scan_types)
        
        # 生成报告
        if output_format.lower() == "json":
            report = report_generator.generate_json_report(analysis_results)
            return json.dumps(report, indent=2, ensure_ascii=False)
        else:
            report = report_generator.generate_markdown_report(analysis_results)
            return report
            
    except Exception as e:
        error_msg = f"代码扫描失败: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return error_msg


@mcp.tool()
async def save_report(
    report_content: str,
    output_path: str,
    format: str = "markdown"
) -> str:
    """
    保存扫描报告到文件
    
    Args:
        report_content: 报告内容
        output_path: 保存路径
        format: 文件格式，'json', 'markdown', 或 'html'
    
    Returns:
        保存结果信息
    """
    try:
        output_file = Path(output_path)
        
        # 确保目录存在
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 根据格式处理内容
        if format.lower() == "html":
            # 如果是HTML格式，将markdown转换为HTML
            html_content = report_generator.markdown_to_html(report_content)
            content_to_save = html_content
        else:
            content_to_save = report_content
        
        # 保存文件
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content_to_save)
        
        success_msg = f"报告已成功保存到: {output_path}"
        logger.info(success_msg)
        return success_msg
        
    except Exception as e:
        error_msg = f"保存报告失败: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return error_msg


@mcp.tool()
async def get_scan_config() -> str:
    """
    获取当前扫描配置信息
    
    Returns:
        扫描配置的JSON字符串
    """
    try:
        config = {
            "available_scan_types": [
                {
                    "name": "complexity",
                    "description": "复杂度分析：圈复杂度、认知复杂度、Halstead复杂度"
                },
                {
                    "name": "style", 
                    "description": "代码风格检查：PEP8合规性、命名规范、导入排序"
                },
                {
                    "name": "security",
                    "description": "安全扫描：安全漏洞检测、依赖安全检查"
                },
                {
                    "name": "documentation",
                    "description": "文档质量：文档字符串检查、类型注解检查"
                },
                {
                    "name": "cleanup",
                    "description": "代码清理：死代码检测、格式化建议"
                }
            ],
            "supported_formats": ["json", "markdown", "html"],
            "supported_file_types": [".py"],
            "version": "0.1.0"
        }
        
        return json.dumps(config, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_msg = f"获取配置失败: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return error_msg


def main():
    """启动MCP服务器"""
    try:
        logger.info("启动代码扫描MCP服务器...")
        mcp.run(transport='stdio')
    except KeyboardInterrupt:
        logger.info("服务器被用户中断")
    except Exception as e:
        logger.error(f"服务器启动失败: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
