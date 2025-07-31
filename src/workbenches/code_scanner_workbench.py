"""
代码扫描MCP工作台

提供与代码扫描MCP服务的集成接口。
"""

import asyncio
import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from autogen_core.tools import Tool, FunctionTool

logger = logging.getLogger(__name__)


class CodeScannerWorkbench:
    """代码扫描MCP工作台"""
    
    def __init__(self, mcp_server_path: Optional[str] = None):
        """
        初始化代码扫描工作台

        Args:
            mcp_server_path: MCP服务器脚本路径，如果为None则使用默认路径
        """
        # 设置MCP服务模块路径
        project_root = Path(__file__).parent.parent.parent
        mcp_src_path = project_root / "mcp_services" / "code_scanner_mcp" / "src"

        # 添加到Python路径
        if str(mcp_src_path) not in sys.path:
            sys.path.insert(0, str(mcp_src_path))

        # 尝试导入MCP服务模块
        try:
            from code_scanner_mcp.analyzers import CodeAnalyzer
            from code_scanner_mcp.report_generator import ReportGenerator

            self.analyzer = CodeAnalyzer()
            self.report_generator = ReportGenerator()
            self.available = True
            logger.info("代码扫描MCP服务模块加载成功")
        except ImportError as e:
            logger.error(f"无法导入代码扫描MCP服务模块: {e}")
            self.analyzer = None
            self.report_generator = None
            self.available = False
    
    async def list_tools(self) -> List[Tool]:
        """获取代码扫描相关的工具"""

        # 创建包装函数，避免self参数问题
        async def scan_code(path: str, scan_types: Optional[List[str]] = None, output_format: str = "markdown") -> str:
            """扫描指定路径的Python代码并生成分析报告"""
            return await self._scan_code(path, scan_types, output_format)

        async def save_scan_report(report_content: str, output_path: str, format: str = "markdown") -> str:
            """保存扫描报告到文件"""
            return await self._save_scan_report(report_content, output_path, format)

        async def get_scan_config() -> str:
            """获取代码扫描配置信息"""
            return await self._get_scan_config()

        return [
            FunctionTool(
                scan_code,
                description="扫描指定路径的Python代码并生成分析报告"
            ),
            FunctionTool(
                save_scan_report,
                description="保存扫描报告到文件"
            ),
            FunctionTool(
                get_scan_config,
                description="获取代码扫描配置信息"
            )
        ]

    def get_tools(self) -> List[Tool]:
        """获取代码扫描相关的工具（同步版本，用于向后兼容）"""
        # 直接返回工具列表，避免在事件循环中调用asyncio.run()
        return [
            FunctionTool(
                self._scan_code,
                description="扫描指定路径的Python代码并生成分析报告"
            ),
            FunctionTool(
                self._save_scan_report,
                description="保存扫描报告到文件"
            ),
            FunctionTool(
                self._get_scan_config,
                description="获取代码扫描配置信息"
            )
        ]

    async def _scan_code(
        self,
        path: str,
        scan_types: Optional[List[str]] = None,
        output_format: str = "markdown"
    ) -> str:
        """
        扫描代码

        Args:
            path: 要扫描的路径
            scan_types: 扫描类型列表
            output_format: 输出格式

        Returns:
            扫描报告
        """
        try:
            if not self.available:
                return "代码扫描服务不可用，请检查MCP服务模块是否正确安装"

            if scan_types is None:
                scan_types = ["complexity", "style", "security", "documentation", "cleanup"]

            # 直接调用分析器
            target_path = Path(path)
            if not target_path.exists():
                return f"错误：路径 '{path}' 不存在"

            logger.info(f"开始扫描路径: {path}, 扫描类型: {scan_types}")

            # 执行代码分析
            analysis_results = await self.analyzer.analyze_code(target_path, scan_types)

            # 生成报告
            if output_format.lower() == "json":
                report = self.report_generator.generate_json_report(analysis_results)
                return json.dumps(report, indent=2, ensure_ascii=False)
            else:
                report = self.report_generator.generate_markdown_report(analysis_results)
                return report

        except Exception as e:
            logger.error(f"代码扫描失败: {e}")
            return f"代码扫描失败: {str(e)}"
    
    async def _save_scan_report(
        self,
        report_content: str,
        output_path: str,
        format: str = "markdown"
    ) -> str:
        """
        保存扫描报告

        Args:
            report_content: 报告内容
            output_path: 保存路径
            format: 文件格式

        Returns:
            保存结果
        """
        try:
            if not self.available:
                return "代码扫描服务不可用，请检查MCP服务模块是否正确安装"

            output_file = Path(output_path)

            # 确保目录存在
            output_file.parent.mkdir(parents=True, exist_ok=True)

            # 根据格式处理内容
            if format.lower() == "html":
                # 如果是HTML格式，将markdown转换为HTML
                html_content = self.report_generator.markdown_to_html(report_content)
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
            logger.error(f"保存报告失败: {e}")
            return f"保存报告失败: {str(e)}"
    
    async def _get_scan_config(self) -> str:
        """
        获取扫描配置

        Returns:
            配置信息
        """
        try:
            if not self.available:
                return "代码扫描服务不可用，请检查MCP服务模块是否正确安装"

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
                "version": "0.1.0",
                "service_status": "available" if self.available else "unavailable"
            }

            return json.dumps(config, indent=2, ensure_ascii=False)

        except Exception as e:
            logger.error(f"获取配置失败: {e}")
            return f"获取配置失败: {str(e)}"

