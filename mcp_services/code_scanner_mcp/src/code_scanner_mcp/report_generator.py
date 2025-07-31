"""
报告生成器模块

将代码分析结果转换为各种格式的报告。
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class ReportGenerator:
    """报告生成器"""
    
    def generate_markdown_report(self, analysis_results: Dict[str, Any]) -> str:
        """生成Markdown格式的报告"""
        try:
            report_lines = []
            
            # 报告头部
            report_lines.extend(self._generate_header(analysis_results))
            
            # 执行总结
            report_lines.extend(self._generate_summary_section(analysis_results))
            
            # 详细分析结果
            if "complexity" in analysis_results.get("details", {}):
                report_lines.extend(self._generate_complexity_section(analysis_results["details"]["complexity"]))
            
            if "style" in analysis_results.get("details", {}):
                report_lines.extend(self._generate_style_section(analysis_results["details"]["style"]))
            
            if "security" in analysis_results.get("details", {}):
                report_lines.extend(self._generate_security_section(analysis_results["details"]["security"]))
            
            if "documentation" in analysis_results.get("details", {}):
                report_lines.extend(self._generate_documentation_section(analysis_results["details"]["documentation"]))
            
            if "cleanup" in analysis_results.get("details", {}):
                report_lines.extend(self._generate_cleanup_section(analysis_results["details"]["cleanup"]))
            
            # 建议和结论
            report_lines.extend(self._generate_recommendations_section(analysis_results))
            
            return "\n".join(report_lines)
            
        except Exception as e:
            logger.error(f"生成Markdown报告失败: {e}")
            return f"报告生成失败: {str(e)}"
    
    def generate_json_report(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """生成JSON格式的报告"""
        try:
            # 添加报告元数据
            report = {
                "report_metadata": {
                    "generated_at": datetime.now().isoformat(),
                    "generator": "code-scanner-mcp",
                    "version": "0.1.0"
                },
                "analysis_results": analysis_results
            }
            
            return report
            
        except Exception as e:
            logger.error(f"生成JSON报告失败: {e}")
            return {"error": f"报告生成失败: {str(e)}"}
    
    def markdown_to_html(self, markdown_content: str) -> str:
        """将Markdown转换为HTML"""
        try:
            # 简单的Markdown到HTML转换
            html_lines = ["<!DOCTYPE html>", "<html>", "<head>", 
                         "<meta charset='utf-8'>", 
                         "<title>代码扫描报告</title>",
                         "<style>",
                         "body { font-family: Arial, sans-serif; margin: 40px; }",
                         "h1, h2, h3 { color: #333; }",
                         "pre { background: #f4f4f4; padding: 10px; border-radius: 5px; }",
                         "table { border-collapse: collapse; width: 100%; }",
                         "th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }",
                         "th { background-color: #f2f2f2; }",
                         ".error { color: #d32f2f; }",
                         ".warning { color: #f57c00; }",
                         ".success { color: #388e3c; }",
                         "</style>",
                         "</head>", "<body>"]
            
            # 简单转换Markdown语法
            lines = markdown_content.split('\n')
            for line in lines:
                if line.startswith('# '):
                    html_lines.append(f"<h1>{line[2:]}</h1>")
                elif line.startswith('## '):
                    html_lines.append(f"<h2>{line[3:]}</h2>")
                elif line.startswith('### '):
                    html_lines.append(f"<h3>{line[4:]}</h3>")
                elif line.startswith('- '):
                    html_lines.append(f"<li>{line[2:]}</li>")
                elif line.strip().startswith('```'):
                    if line.strip() == '```':
                        html_lines.append("</pre>")
                    else:
                        html_lines.append("<pre>")
                else:
                    html_lines.append(f"<p>{line}</p>")
            
            html_lines.extend(["</body>", "</html>"])
            return "\n".join(html_lines)
            
        except Exception as e:
            logger.error(f"Markdown转HTML失败: {e}")
            return f"<html><body><h1>转换失败</h1><p>{str(e)}</p></body></html>"
    
    def _generate_header(self, analysis_results: Dict[str, Any]) -> List[str]:
        """生成报告头部"""
        scan_info = analysis_results.get("scan_info", {})
        timestamp = datetime.fromtimestamp(scan_info.get("timestamp", 0))
        
        return [
            "# 代码扫描报告",
            "",
            f"**扫描路径**: {scan_info.get('path', 'N/A')}",
            f"**扫描时间**: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**扫描类型**: {', '.join(scan_info.get('scan_types', []))}",
            f"**分析文件数**: {len(analysis_results.get('files_analyzed', []))}",
            "",
            "---",
            ""
        ]
    
    def _generate_summary_section(self, analysis_results: Dict[str, Any]) -> List[str]:
        """生成总结部分"""
        summary = analysis_results.get("summary", {})
        
        lines = [
            "## 📊 扫描总结",
            "",
            f"- **总问题数**: {summary.get('total_issues', 0)}",
            f"- **严重问题数**: {summary.get('critical_issues', 0)}",
            ""
        ]
        
        recommendations = summary.get("recommendations", [])
        if recommendations:
            lines.append("### 🎯 主要建议")
            lines.append("")
            for rec in recommendations:
                lines.append(f"- {rec}")
            lines.append("")
        
        lines.extend(["---", ""])
        return lines
    
    def _generate_complexity_section(self, complexity_data: Dict[str, Any]) -> List[str]:
        """生成复杂度分析部分"""
        lines = [
            "## 🔍 复杂度分析",
            ""
        ]
        
        summary = complexity_data.get("summary", {})
        lines.extend([
            f"- **总函数数**: {summary.get('total_functions', 0)}",
            f"- **平均复杂度**: {summary.get('average_complexity', 0):.2f}",
            f"- **高复杂度函数数**: {len(summary.get('high_complexity_functions', []))}",
            ""
        ])
        
        # 高复杂度函数列表
        high_complexity = summary.get("high_complexity_functions", [])
        if high_complexity:
            lines.append("### ⚠️ 高复杂度函数")
            lines.append("")
            lines.append("| 文件 | 函数 | 复杂度 |")
            lines.append("|------|------|--------|")
            
            for func in high_complexity[:10]:  # 只显示前10个
                lines.append(f"| {func['file']} | {func['function']} | {func['complexity']} |")
            
            if len(high_complexity) > 10:
                lines.append(f"| ... | ... | ... |")
                lines.append(f"*还有 {len(high_complexity) - 10} 个高复杂度函数*")
            
            lines.append("")
        
        lines.extend(["---", ""])
        return lines
    
    def _generate_style_section(self, style_data: Dict[str, Any]) -> List[str]:
        """生成代码风格部分"""
        lines = [
            "## 📏 代码风格检查",
            ""
        ]
        
        summary = style_data.get("summary", {})
        lines.extend([
            f"- **总问题数**: {summary.get('total_issues', 0)}",
            f"- **错误数**: {summary.get('error_count', 0)}",
            f"- **警告数**: {summary.get('warning_count', 0)}",
            ""
        ])
        
        # 显示部分问题示例
        flake8_issues = style_data.get("flake8_issues", {})
        if flake8_issues:
            lines.append("### 🔧 主要风格问题")
            lines.append("")
            
            issue_count = 0
            for file_path, issues in flake8_issues.items():
                if issue_count >= 20:  # 限制显示数量
                    break
                    
                if isinstance(issues, list) and issues:
                    lines.append(f"**{file_path}**:")
                    for issue in issues[:5]:  # 每个文件最多显示5个问题
                        if isinstance(issue, dict):
                            line_num = issue.get('line_number', 'N/A')
                            text = issue.get('text', str(issue))
                            lines.append(f"- 第{line_num}行: {text}")
                        else:
                            lines.append(f"- {issue}")
                        issue_count += 1
                    lines.append("")
        
        lines.extend(["---", ""])
        return lines

    def _generate_security_section(self, security_data: Dict[str, Any]) -> List[str]:
        """生成安全分析部分"""
        lines = [
            "## 🛡️ 安全扫描",
            ""
        ]

        summary = security_data.get("summary", {})
        lines.extend([
            f"- **总安全问题数**: {summary.get('total_issues', 0)}",
            f"- **高危问题**: {summary.get('high_severity', 0)}",
            f"- **中危问题**: {summary.get('medium_severity', 0)}",
            f"- **低危问题**: {summary.get('low_severity', 0)}",
            ""
        ])

        # 显示安全问题
        bandit_issues = security_data.get("bandit_issues", {})
        if bandit_issues:
            lines.append("### 🚨 安全问题详情")
            lines.append("")

            for file_path, issues in bandit_issues.items():
                if isinstance(issues, list) and issues:
                    lines.append(f"**{file_path}**:")
                    for issue in issues[:5]:  # 每个文件最多显示5个问题
                        severity = issue.get('issue_severity', 'Unknown')
                        confidence = issue.get('issue_confidence', 'Unknown')
                        text = issue.get('issue_text', 'No description')
                        line_num = issue.get('line_number', 'N/A')

                        severity_icon = "🔴" if severity == "HIGH" else "🟡" if severity == "MEDIUM" else "🟢"
                        lines.append(f"- {severity_icon} **{severity}** (第{line_num}行): {text}")
                    lines.append("")

        lines.extend(["---", ""])
        return lines

    def _generate_documentation_section(self, doc_data: Dict[str, Any]) -> List[str]:
        """生成文档质量部分"""
        lines = [
            "## 📚 文档质量",
            ""
        ]

        summary = doc_data.get("summary", {})
        coverage = summary.get("documentation_coverage", 0)

        lines.extend([
            f"- **总函数数**: {summary.get('total_functions', 0)}",
            f"- **已文档化函数**: {summary.get('documented_functions', 0)}",
            f"- **文档覆盖率**: {coverage:.1%}",
            ""
        ])

        # 覆盖率评级
        if coverage >= 0.9:
            grade = "🟢 优秀"
        elif coverage >= 0.7:
            grade = "🟡 良好"
        elif coverage >= 0.5:
            grade = "🟠 一般"
        else:
            grade = "🔴 需改进"

        lines.append(f"**文档质量评级**: {grade}")
        lines.append("")

        # 显示文档问题
        docstring_issues = doc_data.get("docstring_issues", {})
        if docstring_issues:
            lines.append("### 📝 文档问题")
            lines.append("")

            issue_count = 0
            for file_path, issues in docstring_issues.items():
                if issue_count >= 15:  # 限制显示数量
                    break

                if isinstance(issues, list) and issues:
                    lines.append(f"**{file_path}**:")
                    for issue in issues[:3]:  # 每个文件最多显示3个问题
                        issue_type = issue.get('type', 'unknown')
                        function = issue.get('function', 'N/A')
                        line_num = issue.get('line', 'N/A')
                        message = issue.get('message', 'No message')

                        icon = "📄" if "docstring" in issue_type else "🏷️"
                        lines.append(f"- {icon} {function} (第{line_num}行): {message}")
                        issue_count += 1
                    lines.append("")

        lines.extend(["---", ""])
        return lines

    def _generate_cleanup_section(self, cleanup_data: Dict[str, Any]) -> List[str]:
        """生成代码清理部分"""
        lines = [
            "## 🧹 代码清理建议",
            ""
        ]

        summary = cleanup_data.get("summary", {})
        lines.extend([
            f"- **死代码项数**: {summary.get('total_dead_code_items', 0)}",
            f"- **未使用导入**: {summary.get('total_unused_imports', 0)}",
            ""
        ])

        # 显示死代码
        dead_code = cleanup_data.get("dead_code", {})
        if dead_code:
            lines.append("### 🗑️ 死代码检测")
            lines.append("")

            for file_path, items in dead_code.items():
                if isinstance(items, list) and items:
                    lines.append(f"**{file_path}**:")
                    for item in items[:5]:  # 每个文件最多显示5项
                        lines.append(f"- {item}")
                    lines.append("")

        lines.extend(["---", ""])
        return lines

    def _generate_recommendations_section(self, analysis_results: Dict[str, Any]) -> List[str]:
        """生成建议和结论部分"""
        lines = [
            "## 💡 改进建议",
            ""
        ]

        summary = analysis_results.get("summary", {})
        recommendations = summary.get("recommendations", [])

        if recommendations:
            lines.append("### 🎯 优先改进项")
            lines.append("")
            for i, rec in enumerate(recommendations, 1):
                lines.append(f"{i}. {rec}")
            lines.append("")

        # 总体评估
        total_issues = summary.get("total_issues", 0)
        critical_issues = summary.get("critical_issues", 0)

        if total_issues == 0:
            overall_grade = "🟢 优秀"
            conclusion = "代码质量良好，未发现明显问题。"
        elif critical_issues == 0 and total_issues < 10:
            overall_grade = "🟡 良好"
            conclusion = "代码质量较好，有少量需要改进的地方。"
        elif critical_issues < 5:
            overall_grade = "🟠 一般"
            conclusion = "代码质量一般，建议优先解决严重问题。"
        else:
            overall_grade = "🔴 需改进"
            conclusion = "代码质量需要显著改进，存在多个严重问题。"

        lines.extend([
            "### 📈 总体评估",
            "",
            f"**代码质量等级**: {overall_grade}",
            f"**结论**: {conclusion}",
            "",
            "---",
            "",
            "*报告由 code-scanner-mcp 生成*"
        ])

        return lines
