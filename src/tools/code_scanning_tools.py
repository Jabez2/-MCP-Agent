#!/usr/bin/env python3
"""
AutoGen框架下的代码扫描工具

提供独立的Python函数作为AutoGen Agent的工具，用于代码质量分析。
"""

import asyncio
import json
import sys
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

# 导入分析工具
try:
    import radon.complexity as radon_cc
    import radon.metrics as radon_metrics
    RADON_AVAILABLE = True
except ImportError:
    RADON_AVAILABLE = False
    logging.warning("radon未安装，复杂度分析功能将受限")

logger = logging.getLogger(__name__)


async def scan_code(
    path: str, 
    scan_types: Optional[List[str]] = None,
    output_format: str = "markdown"
) -> str:
    """
    扫描指定路径的Python代码并生成分析报告
    
    Args:
        path: 要扫描的文件或目录路径
        scan_types: 扫描类型列表，可选值：complexity, style, security, documentation, cleanup
        output_format: 输出格式，支持 markdown 或 json
    
    Returns:
        扫描报告内容
    """
    try:
        if scan_types is None:
            scan_types = ["complexity", "style", "security", "documentation", "cleanup"]
        
        target_path = Path(path)
        if not target_path.exists():
            return f"错误：路径 '{path}' 不存在"
        
        logger.info(f"开始扫描路径: {path}, 扫描类型: {scan_types}")
        
        # 收集Python文件
        python_files = _collect_python_files(target_path)
        if not python_files:
            return "未找到Python文件"
        
        # 执行分析
        analysis_results = {
            "scan_info": {
                "path": str(target_path),
                "scan_types": scan_types,
                "timestamp": datetime.now().isoformat(),
                "files_count": len(python_files)
            },
            "files_analyzed": [str(f) for f in python_files],
            "details": {}
        }
        
        # 执行各种类型的分析
        for scan_type in scan_types:
            if scan_type == "complexity":
                analysis_results["details"]["complexity"] = await _analyze_complexity(python_files)
            elif scan_type == "style":
                analysis_results["details"]["style"] = await _analyze_style(python_files)
            elif scan_type == "security":
                analysis_results["details"]["security"] = await _analyze_security(python_files)
            elif scan_type == "documentation":
                analysis_results["details"]["documentation"] = await _analyze_documentation(python_files)
            elif scan_type == "cleanup":
                analysis_results["details"]["cleanup"] = await _analyze_cleanup(python_files)
        
        # 生成报告
        if output_format.lower() == "json":
            return json.dumps(analysis_results, indent=2, ensure_ascii=False)
        else:
            return _generate_markdown_report(analysis_results)
            
    except Exception as e:
        logger.error(f"代码扫描失败: {e}")
        return f"扫描失败: {str(e)}"


async def save_scan_report(
    report_content: str,
    output_path: str,
    format: str = "markdown"
) -> str:
    """
    保存扫描报告到文件
    
    Args:
        report_content: 报告内容
        output_path: 保存路径
        format: 文件格式
    
    Returns:
        保存结果信息
    """
    try:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        logger.info(f"报告已成功保存到: {output_path}")
        return f"报告已成功保存到: {output_path}"
        
    except Exception as e:
        logger.error(f"保存报告失败: {e}")
        return f"保存失败: {str(e)}"


async def get_scan_config() -> str:
    """
    获取代码扫描配置信息
    
    Returns:
        配置信息的JSON字符串
    """
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
                "description": "安全扫描：潜在安全漏洞、危险函数调用"
            },
            {
                "name": "documentation",
                "description": "文档质量：文档字符串覆盖率、注释质量"
            },
            {
                "name": "cleanup",
                "description": "代码清理：死代码检测、未使用导入、格式化建议"
            }
        ],
        "supported_formats": ["markdown", "json", "html"],
        "supported_extensions": [".py"],
        "tools_status": {
            "radon": RADON_AVAILABLE,
            "flake8": False,  # 将在运行时检查
            "bandit": False,  # 将在运行时检查
            "vulture": False  # 将在运行时检查
        }
    }
    
    return json.dumps(config, indent=2, ensure_ascii=False)


def _collect_python_files(path: Path) -> List[Path]:
    """收集Python文件"""
    python_files = []
    supported_extensions = {'.py'}
    
    if path.is_file():
        if path.suffix in supported_extensions:
            python_files.append(path)
    elif path.is_dir():
        for file_path in path.rglob("*"):
            if file_path.is_file() and file_path.suffix in supported_extensions:
                # 跳过虚拟环境和缓存目录
                if any(part in str(file_path) for part in ['.venv', '__pycache__', '.git', 'node_modules']):
                    continue
                python_files.append(file_path)
    
    return python_files


async def _analyze_complexity(files: List[Path]) -> Dict[str, Any]:
    """分析代码复杂度"""
    complexity_results = {
        "cyclomatic_complexity": {},
        "summary": {
            "total_functions": 0,
            "high_complexity_functions": [],
            "average_complexity": 0.0
        }
    }
    
    if not RADON_AVAILABLE:
        complexity_results["error"] = "radon工具不可用，跳过复杂度分析"
        return complexity_results
    
    total_complexity = 0
    function_count = 0
    
    for file_path in files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 圈复杂度分析
            cc_results = radon_cc.cc_visit(content)
            complexity_results["cyclomatic_complexity"][str(file_path)] = []
            
            for result in cc_results:
                complexity_data = {
                    "name": result.name,
                    "type": getattr(result, 'type', 'function'),
                    "complexity": result.complexity,
                    "lineno": result.lineno,
                    "endline": getattr(result, 'endline', result.lineno)
                }
                complexity_results["cyclomatic_complexity"][str(file_path)].append(complexity_data)
                
                function_count += 1
                total_complexity += result.complexity
                
                # 标记高复杂度函数
                if result.complexity > 10:
                    complexity_results["summary"]["high_complexity_functions"].append({
                        "file": str(file_path),
                        "function": result.name,
                        "complexity": result.complexity
                    })
                    
        except Exception as e:
            logger.error(f"复杂度分析失败 {file_path}: {e}")
    
    if function_count > 0:
        complexity_results["summary"]["average_complexity"] = round(total_complexity / function_count, 2)
    complexity_results["summary"]["total_functions"] = function_count
    
    return complexity_results


async def _analyze_style(files: List[Path]) -> Dict[str, Any]:
    """分析代码风格（简化版本，不依赖外部工具）"""
    style_results = {
        "basic_checks": {},
        "summary": {
            "total_issues": 0,
            "files_with_issues": 0
        }
    }
    
    for file_path in files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            file_issues = []
            
            # 基本的风格检查
            for i, line in enumerate(lines, 1):
                # 检查行长度
                if len(line.rstrip()) > 88:
                    file_issues.append({
                        "line": i,
                        "type": "line_too_long",
                        "message": f"行长度超过88字符 ({len(line.rstrip())})"
                    })
                
                # 检查尾随空格
                if line.rstrip() != line.rstrip(' \t'):
                    file_issues.append({
                        "line": i,
                        "type": "trailing_whitespace",
                        "message": "行末有多余空格"
                    })
            
            if file_issues:
                style_results["basic_checks"][str(file_path)] = file_issues
                style_results["summary"]["files_with_issues"] += 1
                style_results["summary"]["total_issues"] += len(file_issues)
                
        except Exception as e:
            logger.error(f"风格检查失败 {file_path}: {e}")
    
    return style_results


async def _analyze_security(files: List[Path]) -> Dict[str, Any]:
    """分析安全问题（简化版本）"""
    security_results = {
        "basic_security_checks": {},
        "summary": {
            "total_issues": 0,
            "high_severity": 0,
            "medium_severity": 0,
            "low_severity": 0
        }
    }
    
    # 简单的安全模式检查
    security_patterns = [
        ("password", "hardcoded_password", "medium"),
        ("subprocess.call", "dangerous_subprocess", "high"),
        ("eval(", "dangerous_eval", "high"),
        ("exec(", "dangerous_exec", "high"),
        ("shell=True", "shell_injection", "high")
    ]
    
    for file_path in files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()
            
            file_issues = []
            
            for i, line in enumerate(lines, 1):
                for pattern, issue_type, severity in security_patterns:
                    if pattern in line.lower():
                        file_issues.append({
                            "line": i,
                            "type": issue_type,
                            "severity": severity,
                            "message": f"发现潜在安全问题: {pattern}"
                        })
                        security_results["summary"]["total_issues"] += 1
                        security_results["summary"][f"{severity}_severity"] += 1
            
            if file_issues:
                security_results["basic_security_checks"][str(file_path)] = file_issues
                
        except Exception as e:
            logger.error(f"安全检查失败 {file_path}: {e}")
    
    return security_results


async def _analyze_documentation(files: List[Path]) -> Dict[str, Any]:
    """分析文档质量"""
    doc_results = {
        "docstring_coverage": {},
        "summary": {
            "total_functions": 0,
            "documented_functions": 0,
            "coverage_percentage": 0.0
        }
    }
    
    for file_path in files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 简单的函数和文档字符串检测
            import ast
            tree = ast.parse(content)
            
            functions = []
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    has_docstring = (
                        node.body and 
                        isinstance(node.body[0], ast.Expr) and 
                        isinstance(node.body[0].value, ast.Constant) and 
                        isinstance(node.body[0].value.value, str)
                    )
                    
                    functions.append({
                        "name": node.name,
                        "line": node.lineno,
                        "has_docstring": has_docstring
                    })
                    
                    doc_results["summary"]["total_functions"] += 1
                    if has_docstring:
                        doc_results["summary"]["documented_functions"] += 1
            
            if functions:
                doc_results["docstring_coverage"][str(file_path)] = functions
                
        except Exception as e:
            logger.error(f"文档分析失败 {file_path}: {e}")
    
    # 计算覆盖率
    if doc_results["summary"]["total_functions"] > 0:
        doc_results["summary"]["coverage_percentage"] = round(
            (doc_results["summary"]["documented_functions"] / doc_results["summary"]["total_functions"]) * 100, 2
        )
    
    return doc_results


async def _analyze_cleanup(files: List[Path]) -> Dict[str, Any]:
    """分析代码清理建议（简化版本）"""
    cleanup_results = {
        "unused_imports": {},
        "summary": {
            "total_unused_imports": 0
        }
    }
    
    for file_path in files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 简单的未使用导入检测
            import ast
            tree = ast.parse(content)
            
            imports = []
            used_names = set()
            
            # 收集导入
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.Name):
                    used_names.add(node.id)
            
            # 检查未使用的导入
            unused = [imp for imp in imports if imp not in used_names]
            
            if unused:
                cleanup_results["unused_imports"][str(file_path)] = unused
                cleanup_results["summary"]["total_unused_imports"] += len(unused)
                
        except Exception as e:
            logger.error(f"清理分析失败 {file_path}: {e}")
    
    return cleanup_results


def _generate_markdown_report(analysis_results: Dict[str, Any]) -> str:
    """生成详细的Markdown格式报告"""
    report_lines = []

    # 标题和基本信息
    report_lines.append("# 📋 代码质量扫描报告")
    report_lines.append("")

    scan_info = analysis_results.get("scan_info", {})
    report_lines.append(f"**📁 扫描路径**: {scan_info.get('path', 'N/A')}")
    report_lines.append(f"**⏰ 扫描时间**: {scan_info.get('timestamp', 'N/A')}")
    report_lines.append(f"**🔍 扫描类型**: {', '.join(scan_info.get('scan_types', []))}")
    report_lines.append(f"**📄 分析文件数**: {scan_info.get('files_count', 0)}")

    # 显示分析的文件列表
    files_analyzed = analysis_results.get("files_analyzed", [])
    if files_analyzed:
        report_lines.append("")
        report_lines.append("**📂 分析文件列表**:")
        for i, file_path in enumerate(files_analyzed, 1):
            file_name = Path(file_path).name
            report_lines.append(f"  {i}. `{file_name}`")

    report_lines.append("")
    report_lines.append("---")
    report_lines.append("")

    details = analysis_results.get("details", {})

    # 扫描总结
    report_lines.append("## 📊 扫描总结")
    report_lines.append("")

    total_issues = 0
    if "style" in details:
        total_issues += details["style"]["summary"].get("total_issues", 0)
    if "security" in details:
        total_issues += details["security"]["summary"].get("total_issues", 0)

    report_lines.append(f"- **总问题数**: {total_issues}")

    if "security" in details:
        high_severity = details["security"]["summary"].get("high_severity", 0)
        report_lines.append(f"- **严重问题数**: {high_severity}")

    report_lines.append("")
    report_lines.append("---")
    report_lines.append("")
    
    # 复杂度分析
    if "complexity" in details:
        complexity = details["complexity"]
        report_lines.append("## 🔍 复杂度分析")
        report_lines.append("")
        report_lines.append(f"- **总函数数**: {complexity['summary'].get('total_functions', 0)}")
        report_lines.append(f"- **平均复杂度**: {complexity['summary'].get('average_complexity', 0)}")
        report_lines.append(f"- **高复杂度函数数**: {len(complexity['summary'].get('high_complexity_functions', []))}")

        # 详细的复杂度信息
        cyclomatic_complexity = complexity.get("cyclomatic_complexity", {})
        if cyclomatic_complexity:
            report_lines.append("")
            report_lines.append("### 📈 各文件复杂度详情")
            report_lines.append("")

            for file_path, functions in cyclomatic_complexity.items():
                if functions:  # 只显示有函数的文件
                    file_name = Path(file_path).name
                    report_lines.append(f"#### 📄 `{file_name}`")
                    report_lines.append("")

                    for func in functions:
                        complexity_level = "🟢" if func["complexity"] <= 5 else "🟡" if func["complexity"] <= 10 else "🔴"
                        report_lines.append(f"- **{func['name']}** (第{func['lineno']}行)")
                        report_lines.append(f"  - 复杂度: {complexity_level} {func['complexity']}")
                        report_lines.append(f"  - 类型: {func['type']}")
                        if func["complexity"] > 10:
                            report_lines.append(f"  - ⚠️ **建议重构**: 复杂度过高，建议拆分函数")
                        report_lines.append("")

        # 高复杂度函数警告
        high_complexity_functions = complexity['summary'].get('high_complexity_functions', [])
        if high_complexity_functions:
            report_lines.append("### 🚨 高复杂度函数警告")
            report_lines.append("")
            for func in high_complexity_functions:
                file_name = Path(func['file']).name
                report_lines.append(f"- **{func['function']}** 在 `{file_name}` (复杂度: {func['complexity']})")
            report_lines.append("")

        report_lines.append("---")
        report_lines.append("")
    
    # 代码风格检查
    if "style" in details:
        style = details["style"]
        report_lines.append("## 📏 代码风格检查")
        report_lines.append("")
        report_lines.append(f"- **总问题数**: {style['summary'].get('total_issues', 0)}")
        report_lines.append(f"- **有问题的文件数**: {style['summary'].get('files_with_issues', 0)}")

        # 详细的风格问题
        basic_checks = style.get("basic_checks", {})
        if basic_checks:
            report_lines.append("")
            report_lines.append("### 📝 各文件风格问题详情")
            report_lines.append("")

            for file_path, issues in basic_checks.items():
                file_name = Path(file_path).name
                report_lines.append(f"#### 📄 `{file_name}` ({len(issues)}个问题)")
                report_lines.append("")

                # 按问题类型分组
                issue_groups = {}
                for issue in issues:
                    issue_type = issue["type"]
                    if issue_type not in issue_groups:
                        issue_groups[issue_type] = []
                    issue_groups[issue_type].append(issue)

                for issue_type, type_issues in issue_groups.items():
                    type_name = {
                        "line_too_long": "🔸 行长度超限",
                        "trailing_whitespace": "🔸 尾随空格"
                    }.get(issue_type, f"🔸 {issue_type}")

                    report_lines.append(f"**{type_name}** ({len(type_issues)}处):")
                    for issue in type_issues[:5]:  # 最多显示5个
                        report_lines.append(f"  - 第{issue['line']}行: {issue['message']}")

                    if len(type_issues) > 5:
                        report_lines.append(f"  - ... 还有{len(type_issues) - 5}个类似问题")
                    report_lines.append("")

        report_lines.append("---")
        report_lines.append("")
    
    # 安全扫描
    if "security" in details:
        security = details["security"]
        report_lines.append("## 🔒 安全扫描")
        report_lines.append("")
        report_lines.append(f"- **总问题数**: {security['summary'].get('total_issues', 0)}")
        report_lines.append(f"- **高危问题**: {security['summary'].get('high_severity', 0)}")
        report_lines.append(f"- **中危问题**: {security['summary'].get('medium_severity', 0)}")
        report_lines.append(f"- **低危问题**: {security['summary'].get('low_severity', 0)}")

        # 详细的安全问题
        security_checks = security.get("basic_security_checks", {})
        if security_checks:
            report_lines.append("")
            report_lines.append("### 🚨 安全问题详情")
            report_lines.append("")

            for file_path, issues in security_checks.items():
                file_name = Path(file_path).name
                report_lines.append(f"#### 📄 `{file_name}` ({len(issues)}个安全问题)")
                report_lines.append("")

                # 按严重程度分组
                severity_groups = {"high": [], "medium": [], "low": []}
                for issue in issues:
                    severity = issue.get("severity", "low")
                    if severity in severity_groups:
                        severity_groups[severity].append(issue)

                # 显示高危问题
                if severity_groups["high"]:
                    report_lines.append("**🔴 高危问题**:")
                    for issue in severity_groups["high"]:
                        report_lines.append(f"  - 第{issue['line']}行: **{issue['message']}**")
                        report_lines.append(f"    - 问题类型: {issue['type']}")
                        report_lines.append(f"    - 🚨 **立即修复**: 这是严重的安全隐患")
                    report_lines.append("")

                # 显示中危问题
                if severity_groups["medium"]:
                    report_lines.append("**🟡 中危问题**:")
                    for issue in severity_groups["medium"]:
                        report_lines.append(f"  - 第{issue['line']}行: {issue['message']}")
                        report_lines.append(f"    - 问题类型: {issue['type']}")
                        report_lines.append(f"    - ⚠️ **建议修复**: 存在潜在安全风险")
                    report_lines.append("")

                # 显示低危问题
                if severity_groups["low"]:
                    report_lines.append("**🟢 低危问题**:")
                    for issue in severity_groups["low"]:
                        report_lines.append(f"  - 第{issue['line']}行: {issue['message']}")
                        report_lines.append(f"    - 问题类型: {issue['type']}")
                    report_lines.append("")

        report_lines.append("---")
        report_lines.append("")
    
    # 文档质量
    if "documentation" in details:
        doc = details["documentation"]
        report_lines.append("## 📚 文档质量")
        report_lines.append("")
        report_lines.append(f"- **总函数数**: {doc['summary'].get('total_functions', 0)}")
        report_lines.append(f"- **有文档的函数数**: {doc['summary'].get('documented_functions', 0)}")
        report_lines.append(f"- **文档覆盖率**: {doc['summary'].get('coverage_percentage', 0)}%")

        # 详细的文档信息
        docstring_coverage = doc.get("docstring_coverage", {})
        if docstring_coverage:
            report_lines.append("")
            report_lines.append("### 📖 各文件文档详情")
            report_lines.append("")

            for file_path, functions in docstring_coverage.items():
                file_name = Path(file_path).name
                documented_count = sum(1 for func in functions if func["has_docstring"])
                total_count = len(functions)
                coverage = (documented_count / total_count * 100) if total_count > 0 else 0

                report_lines.append(f"#### 📄 `{file_name}` (覆盖率: {coverage:.1f}%)")
                report_lines.append("")

                # 有文档的函数
                documented_functions = [f for f in functions if f["has_docstring"]]
                if documented_functions:
                    report_lines.append("**✅ 有文档的函数**:")
                    for func in documented_functions:
                        report_lines.append(f"  - `{func['name']}` (第{func['line']}行)")
                    report_lines.append("")

                # 缺少文档的函数
                undocumented_functions = [f for f in functions if not f["has_docstring"]]
                if undocumented_functions:
                    report_lines.append("**❌ 缺少文档的函数**:")
                    for func in undocumented_functions:
                        report_lines.append(f"  - `{func['name']}` (第{func['line']}行)")
                        report_lines.append(f"    - 💡 **建议**: 添加文档字符串说明函数用途、参数和返回值")
                    report_lines.append("")

        # 文档质量建议
        coverage_percentage = doc['summary'].get('coverage_percentage', 0)
        if coverage_percentage < 50:
            report_lines.append("### 📝 文档改进建议")
            report_lines.append("")
            report_lines.append("- 🔴 **文档覆盖率偏低**: 建议为所有公共函数添加文档字符串")
            report_lines.append("- 📋 **文档规范**: 建议遵循PEP 257文档字符串约定")
            report_lines.append("- 🎯 **目标**: 将文档覆盖率提升至80%以上")
            report_lines.append("")
        elif coverage_percentage < 80:
            report_lines.append("### 📝 文档改进建议")
            report_lines.append("")
            report_lines.append("- 🟡 **文档覆盖率良好**: 继续为剩余函数添加文档")
            report_lines.append("- 🎯 **目标**: 将文档覆盖率提升至80%以上")
            report_lines.append("")

        report_lines.append("---")
        report_lines.append("")
    
    # 代码清理建议
    if "cleanup" in details:
        cleanup = details["cleanup"]
        report_lines.append("## 🧹 代码清理建议")
        report_lines.append("")
        report_lines.append(f"- **未使用导入总数**: {cleanup['summary'].get('total_unused_imports', 0)}")

        # 详细的清理信息
        unused_imports = cleanup.get("unused_imports", {})
        if unused_imports:
            report_lines.append("")
            report_lines.append("### 📦 未使用导入详情")
            report_lines.append("")

            for file_path, imports in unused_imports.items():
                file_name = Path(file_path).name
                report_lines.append(f"#### 📄 `{file_name}` ({len(imports)}个未使用导入)")
                report_lines.append("")

                for import_name in imports:
                    report_lines.append(f"  - `{import_name}`")
                    report_lines.append(f"    - 💡 **建议**: 移除未使用的导入以减少代码冗余")
                report_lines.append("")

        report_lines.append("---")
        report_lines.append("")

    # 改进建议
    report_lines.append("## 💡 综合改进建议")
    report_lines.append("")

    # 根据分析结果生成优先级建议
    high_priority = []
    medium_priority = []
    low_priority = []

    # 高优先级问题
    if "security" in details and details["security"]["summary"].get("high_severity", 0) > 0:
        high_priority.append(f"修复 {details['security']['summary']['high_severity']} 个高危安全问题")

    if "complexity" in details and details["complexity"]["summary"].get("high_complexity_functions"):
        high_count = len(details["complexity"]["summary"]["high_complexity_functions"])
        high_priority.append(f"重构 {high_count} 个高复杂度函数")

    # 中优先级问题
    if "security" in details and details["security"]["summary"].get("medium_severity", 0) > 0:
        medium_priority.append(f"修复 {details['security']['summary']['medium_severity']} 个中危安全问题")

    if "documentation" in details and details["documentation"]["summary"].get("coverage_percentage", 0) < 80:
        coverage = details["documentation"]["summary"]["coverage_percentage"]
        undocumented = details["documentation"]["summary"]["total_functions"] - details["documentation"]["summary"]["documented_functions"]
        medium_priority.append(f"为 {undocumented} 个函数添加文档 (当前覆盖率: {coverage}%)")

    # 低优先级问题
    if "style" in details and details["style"]["summary"].get("total_issues", 0) > 0:
        style_issues = details["style"]["summary"]["total_issues"]
        low_priority.append(f"修复 {style_issues} 个代码风格问题")

    if "cleanup" in details and details["cleanup"]["summary"].get("total_unused_imports", 0) > 0:
        unused_count = details["cleanup"]["summary"]["total_unused_imports"]
        low_priority.append(f"清理 {unused_count} 个未使用的导入")

    # 显示建议
    if high_priority:
        report_lines.append("### 🔴 高优先级 (立即处理)")
        for suggestion in high_priority:
            report_lines.append(f"1. **{suggestion}**")
            report_lines.append("   - 影响: 安全性和可维护性")
            report_lines.append("   - 建议: 立即修复")
        report_lines.append("")

    if medium_priority:
        report_lines.append("### 🟡 中优先级 (近期处理)")
        for suggestion in medium_priority:
            report_lines.append(f"2. **{suggestion}**")
            report_lines.append("   - 影响: 代码质量和可读性")
            report_lines.append("   - 建议: 1-2周内处理")
        report_lines.append("")

    if low_priority:
        report_lines.append("### 🟢 低优先级 (有时间时处理)")
        for suggestion in low_priority:
            report_lines.append(f"3. **{suggestion}**")
            report_lines.append("   - 影响: 代码规范和整洁度")
            report_lines.append("   - 建议: 有时间时处理")
        report_lines.append("")

    if not (high_priority or medium_priority or low_priority):
        report_lines.append("### ✅ 代码质量优秀")
        report_lines.append("未发现需要改进的问题，代码质量良好！")
        report_lines.append("")

    # 总体评估
    report_lines.append("### 📈 总体评估")
    report_lines.append("")

    # 计算质量分数
    security_score = 100
    if "security" in details:
        high_issues = details["security"]["summary"].get("high_severity", 0)
        medium_issues = details["security"]["summary"].get("medium_severity", 0)
        security_score = max(0, 100 - (high_issues * 30) - (medium_issues * 10))

    complexity_score = 100
    if "complexity" in details:
        high_complexity = len(details["complexity"]["summary"].get("high_complexity_functions", []))
        avg_complexity = details["complexity"]["summary"].get("average_complexity", 0)
        complexity_score = max(0, 100 - (high_complexity * 20) - max(0, (avg_complexity - 5) * 5))

    doc_score = details.get("documentation", {}).get("summary", {}).get("coverage_percentage", 100)

    overall_score = (security_score + complexity_score + doc_score) / 3

    if overall_score >= 90:
        grade = "🟢 优秀"
        conclusion = "代码质量优秀，继续保持！"
    elif overall_score >= 75:
        grade = "🟡 良好"
        conclusion = "代码质量良好，有少量改进空间。"
    elif overall_score >= 60:
        grade = "🟠 一般"
        conclusion = "代码质量一般，建议按优先级逐步改进。"
    else:
        grade = "🔴 需要改进"
        conclusion = "代码质量有待提高，建议重点关注高优先级问题。"

    report_lines.append(f"**代码质量等级**: {grade}")
    report_lines.append(f"**综合评分**: {overall_score:.1f}/100")
    report_lines.append(f"**结论**: {conclusion}")
    report_lines.append("")

    # 评分详情
    report_lines.append("**评分详情**:")
    report_lines.append(f"- 安全性: {security_score:.1f}/100")
    report_lines.append(f"- 复杂度: {complexity_score:.1f}/100")
    report_lines.append(f"- 文档性: {doc_score:.1f}/100")
    report_lines.append("")

    report_lines.append("---")
    report_lines.append("")
    report_lines.append("*📊 报告由 AutoGen 代码扫描工具生成*")
    report_lines.append(f"*🕒 生成时间: {scan_info.get('timestamp', 'N/A')}*")

    return "\n".join(report_lines)
