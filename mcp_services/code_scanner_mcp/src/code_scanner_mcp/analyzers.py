"""
代码分析器模块

提供各种Python代码静态分析功能。
"""

import ast
import asyncio
import json
import logging
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import radon.complexity as radon_cc
import radon.metrics as radon_metrics
from radon.visitors import ComplexityVisitor

logger = logging.getLogger(__name__)


class CodeAnalyzer:
    """代码分析器主类"""
    
    def __init__(self):
        self.supported_extensions = {'.py'}
        self._tool_availability = {}  # 缓存工具可用性
    
    async def analyze_code(self, path: Path, scan_types: List[str]) -> Dict[str, Any]:
        """
        分析指定路径的代码
        
        Args:
            path: 要分析的文件或目录路径
            scan_types: 要执行的扫描类型列表
        
        Returns:
            分析结果字典
        """
        results = {
            "scan_info": {
                "path": str(path),
                "scan_types": scan_types,
                "timestamp": asyncio.get_event_loop().time()
            },
            "files_analyzed": [],
            "summary": {},
            "details": {}
        }
        
        # 收集要分析的Python文件
        python_files = self._collect_python_files(path)
        results["files_analyzed"] = [str(f) for f in python_files]
        
        if not python_files:
            results["summary"]["error"] = "未找到Python文件"
            return results
        
        # 执行各种类型的分析
        for scan_type in scan_types:
            try:
                if scan_type == "complexity":
                    results["details"]["complexity"] = await self._analyze_complexity(python_files)
                elif scan_type == "style":
                    results["details"]["style"] = await self._analyze_style(python_files)
                elif scan_type == "security":
                    results["details"]["security"] = await self._analyze_security(python_files)
                elif scan_type == "documentation":
                    results["details"]["documentation"] = await self._analyze_documentation(python_files)
                elif scan_type == "cleanup":
                    results["details"]["cleanup"] = await self._analyze_cleanup(python_files)
                else:
                    logger.warning(f"未知的扫描类型: {scan_type}")
            except Exception as e:
                logger.error(f"分析 {scan_type} 时出错: {e}")
                results["details"][scan_type] = {"error": str(e)}
        
        # 生成总结
        results["summary"] = self._generate_summary(results["details"])
        
        return results
    
    def _collect_python_files(self, path: Path) -> List[Path]:
        """收集Python文件"""
        python_files = []
        
        if path.is_file():
            if path.suffix in self.supported_extensions:
                python_files.append(path)
        elif path.is_dir():
            for file_path in path.rglob("*"):
                if file_path.is_file() and file_path.suffix in self.supported_extensions:
                    # 跳过虚拟环境和缓存目录
                    if any(part in str(file_path) for part in ['.venv', '__pycache__', '.git', 'node_modules']):
                        continue
                    python_files.append(file_path)
        
        return python_files

    async def _check_tool_availability(self, tool_name: str) -> bool:
        """检查外部工具是否可用"""
        if tool_name in self._tool_availability:
            return self._tool_availability[tool_name]

        try:
            # 尝试运行工具的版本命令
            result = await self._run_command([sys.executable, "-m", tool_name, "--version"], timeout=5)
            available = result["returncode"] == 0
            self._tool_availability[tool_name] = available
            if available:
                logger.info(f"工具 {tool_name} 可用")
            else:
                logger.warning(f"工具 {tool_name} 不可用: {result['stderr']}")
            return available
        except Exception as e:
            logger.warning(f"检查工具 {tool_name} 时出错: {e}")
            self._tool_availability[tool_name] = False
            return False
    
    async def _analyze_complexity(self, files: List[Path]) -> Dict[str, Any]:
        """分析代码复杂度"""
        complexity_results = {
            "cyclomatic_complexity": {},
            "halstead_metrics": {},
            "maintainability_index": {},
            "summary": {
                "total_functions": 0,
                "high_complexity_functions": [],
                "average_complexity": 0.0
            }
        }
        
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
                        "type": getattr(result, 'type', 'function'),  # 默认为function
                        "complexity": result.complexity,
                        "lineno": result.lineno,
                        "endline": getattr(result, 'endline', result.lineno)  # 如果没有endline，使用lineno
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
                
                # Halstead度量
                try:
                    halstead = radon_metrics.h_visit(content)
                    complexity_results["halstead_metrics"][str(file_path)] = {
                        "h1": halstead.h1,  # 不同操作符数量
                        "h2": halstead.h2,  # 不同操作数数量
                        "N1": halstead.N1,  # 总操作符数量
                        "N2": halstead.N2,  # 总操作数数量
                        "vocabulary": halstead.vocabulary,
                        "length": halstead.length,
                        "calculated_length": halstead.calculated_length,
                        "volume": halstead.volume,
                        "difficulty": halstead.difficulty,
                        "effort": halstead.effort,
                        "time": halstead.time,
                        "bugs": halstead.bugs
                    }
                except Exception as e:
                    logger.warning(f"Halstead分析失败 {file_path}: {e}")
                
                # 可维护性指数
                try:
                    mi = radon_metrics.mi_visit(content, multi=True)
                    complexity_results["maintainability_index"][str(file_path)] = mi
                except Exception as e:
                    logger.warning(f"可维护性指数计算失败 {file_path}: {e}")
                    
            except Exception as e:
                logger.error(f"复杂度分析失败 {file_path}: {e}")
        
        # 计算平均复杂度
        if function_count > 0:
            complexity_results["summary"]["average_complexity"] = total_complexity / function_count
        complexity_results["summary"]["total_functions"] = function_count
        
        return complexity_results
    
    async def _analyze_style(self, files: List[Path]) -> Dict[str, Any]:
        """分析代码风格"""
        style_results = {
            "flake8_issues": {},
            "import_sorting": {},
            "summary": {
                "total_issues": 0,
                "error_count": 0,
                "warning_count": 0
            }
        }

        # 检查flake8是否可用
        flake8_available = await self._check_tool_availability("flake8")

        if not flake8_available:
            style_results["flake8_issues"]["error"] = "flake8工具不可用，跳过代码风格检查"
            logger.warning("flake8不可用，跳过代码风格检查")
            return style_results

        # 使用flake8检查代码风格
        for file_path in files:
            try:
                # 运行flake8
                result = await self._run_command([
                    sys.executable, "-m", "flake8",
                    "--format=json",
                    str(file_path)
                ], timeout=10)
                
                if result["stdout"]:
                    try:
                        flake8_data = json.loads(result["stdout"])
                        style_results["flake8_issues"][str(file_path)] = flake8_data
                        
                        # 统计问题数量
                        for issue in flake8_data:
                            style_results["summary"]["total_issues"] += 1
                            if issue.get("code", "").startswith("E"):
                                style_results["summary"]["error_count"] += 1
                            else:
                                style_results["summary"]["warning_count"] += 1
                    except json.JSONDecodeError:
                        # flake8可能没有JSON输出，解析文本格式
                        lines = result["stdout"].strip().split('\n')
                        issues = []
                        for line in lines:
                            if line.strip():
                                parts = line.split(':', 3)
                                if len(parts) >= 4:
                                    issues.append({
                                        "filename": parts[0],
                                        "line_number": int(parts[1]) if parts[1].isdigit() else 0,
                                        "column_number": int(parts[2]) if parts[2].isdigit() else 0,
                                        "text": parts[3].strip()
                                    })
                        style_results["flake8_issues"][str(file_path)] = issues
                        style_results["summary"]["total_issues"] += len(issues)
                
            except Exception as e:
                logger.error(f"风格检查失败 {file_path}: {e}")
        
        return style_results

    async def _analyze_security(self, files: List[Path]) -> Dict[str, Any]:
        """分析安全问题"""
        security_results = {
            "bandit_issues": {},
            "summary": {
                "total_issues": 0,
                "high_severity": 0,
                "medium_severity": 0,
                "low_severity": 0
            }
        }

        # 检查bandit是否可用
        bandit_available = await self._check_tool_availability("bandit")

        if not bandit_available:
            security_results["bandit_issues"]["error"] = "bandit工具不可用，跳过安全扫描"
            logger.warning("bandit不可用，跳过安全扫描")
            return security_results

        # 使用bandit进行安全扫描
        for file_path in files:
            try:
                result = await self._run_command([
                    sys.executable, "-m", "bandit",
                    "-f", "json",
                    str(file_path)
                ], timeout=15)

                if result["stdout"]:
                    try:
                        bandit_data = json.loads(result["stdout"])
                        security_results["bandit_issues"][str(file_path)] = bandit_data.get("results", [])

                        # 统计安全问题
                        for issue in bandit_data.get("results", []):
                            security_results["summary"]["total_issues"] += 1
                            severity = issue.get("issue_severity", "").lower()
                            if severity == "high":
                                security_results["summary"]["high_severity"] += 1
                            elif severity == "medium":
                                security_results["summary"]["medium_severity"] += 1
                            else:
                                security_results["summary"]["low_severity"] += 1

                    except json.JSONDecodeError as e:
                        logger.warning(f"解析bandit输出失败 {file_path}: {e}")

            except Exception as e:
                logger.error(f"安全扫描失败 {file_path}: {e}")

        return security_results

    async def _analyze_documentation(self, files: List[Path]) -> Dict[str, Any]:
        """分析文档质量"""
        doc_results = {
            "docstring_issues": {},
            "type_annotation_coverage": {},
            "summary": {
                "total_functions": 0,
                "documented_functions": 0,
                "documentation_coverage": 0.0
            }
        }

        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # 解析AST
                tree = ast.parse(content)

                # 分析文档字符串和类型注解
                doc_analyzer = DocumentationAnalyzer()
                doc_analyzer.visit(tree)

                doc_results["docstring_issues"][str(file_path)] = doc_analyzer.issues
                doc_results["type_annotation_coverage"][str(file_path)] = {
                    "total_functions": doc_analyzer.total_functions,
                    "annotated_functions": doc_analyzer.annotated_functions,
                    "coverage": doc_analyzer.get_annotation_coverage()
                }

                # 更新总结
                doc_results["summary"]["total_functions"] += doc_analyzer.total_functions
                doc_results["summary"]["documented_functions"] += doc_analyzer.documented_functions

            except Exception as e:
                logger.error(f"文档分析失败 {file_path}: {e}")

        # 计算总体文档覆盖率
        if doc_results["summary"]["total_functions"] > 0:
            doc_results["summary"]["documentation_coverage"] = (
                doc_results["summary"]["documented_functions"] /
                doc_results["summary"]["total_functions"]
            )

        return doc_results

    async def _analyze_cleanup(self, files: List[Path]) -> Dict[str, Any]:
        """分析代码清理建议"""
        cleanup_results = {
            "dead_code": {},
            "unused_imports": {},
            "formatting_suggestions": {},
            "summary": {
                "total_dead_code_items": 0,
                "total_unused_imports": 0
            }
        }

        # 检查vulture是否可用
        vulture_available = await self._check_tool_availability("vulture")

        if not vulture_available:
            cleanup_results["dead_code"]["error"] = "vulture工具不可用，跳过死代码检测"
            logger.warning("vulture不可用，跳过死代码检测")
            return cleanup_results

        # 使用vulture检测死代码
        for file_path in files:
            try:
                result = await self._run_command([
                    sys.executable, "-m", "vulture",
                    str(file_path)
                ], timeout=10)

                if result["stdout"]:
                    dead_code_lines = result["stdout"].strip().split('\n')
                    dead_code_items = []
                    for line in dead_code_lines:
                        if line.strip() and not line.startswith('#'):
                            dead_code_items.append(line.strip())

                    cleanup_results["dead_code"][str(file_path)] = dead_code_items
                    cleanup_results["summary"]["total_dead_code_items"] += len(dead_code_items)

            except Exception as e:
                logger.error(f"死代码检测失败 {file_path}: {e}")

        return cleanup_results

    async def _run_command(self, cmd: List[str], timeout: int = 30) -> Dict[str, str]:
        """运行外部命令，带超时机制"""
        try:
            # 添加超时机制，避免无限等待
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # 使用wait_for添加超时
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )

            return {
                "stdout": stdout.decode('utf-8', errors='ignore'),
                "stderr": stderr.decode('utf-8', errors='ignore'),
                "returncode": process.returncode
            }
        except asyncio.TimeoutError:
            logger.warning(f"命令执行超时 {' '.join(cmd)}")
            try:
                process.terminate()
                await process.wait()
            except:
                pass
            return {"stdout": "", "stderr": "命令执行超时", "returncode": -1}
        except FileNotFoundError:
            logger.warning(f"命令不存在 {' '.join(cmd)}")
            return {"stdout": "", "stderr": f"命令不存在: {cmd[0]}", "returncode": -1}
        except Exception as e:
            logger.error(f"命令执行失败 {' '.join(cmd)}: {e}")
            return {"stdout": "", "stderr": str(e), "returncode": -1}

    def _generate_summary(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """生成分析总结"""
        summary = {
            "total_issues": 0,
            "critical_issues": 0,
            "recommendations": []
        }

        # 统计各类问题
        if "complexity" in details:
            high_complexity = len(details["complexity"]["summary"]["high_complexity_functions"])
            summary["total_issues"] += high_complexity
            if high_complexity > 0:
                summary["critical_issues"] += high_complexity
                summary["recommendations"].append(f"发现 {high_complexity} 个高复杂度函数，建议重构")

        if "style" in details:
            style_issues = details["style"]["summary"]["total_issues"]
            summary["total_issues"] += style_issues
            if style_issues > 0:
                summary["recommendations"].append(f"发现 {style_issues} 个代码风格问题")

        if "security" in details:
            security_issues = details["security"]["summary"]["total_issues"]
            high_security = details["security"]["summary"]["high_severity"]
            summary["total_issues"] += security_issues
            summary["critical_issues"] += high_security
            if security_issues > 0:
                summary["recommendations"].append(f"发现 {security_issues} 个安全问题，其中 {high_security} 个高危")

        if "documentation" in details:
            doc_coverage = details["documentation"]["summary"]["documentation_coverage"]
            if doc_coverage < 0.8:
                summary["recommendations"].append(f"文档覆盖率较低 ({doc_coverage:.1%})，建议增加文档")

        if "cleanup" in details:
            dead_code = details["cleanup"]["summary"]["total_dead_code_items"]
            if dead_code > 0:
                summary["recommendations"].append(f"发现 {dead_code} 个死代码项，建议清理")

        return summary


class DocumentationAnalyzer(ast.NodeVisitor):
    """文档分析器"""

    def __init__(self):
        self.total_functions = 0
        self.documented_functions = 0
        self.annotated_functions = 0
        self.issues = []

    def visit_FunctionDef(self, node):
        """访问函数定义"""
        self.total_functions += 1

        # 检查文档字符串
        if ast.get_docstring(node):
            self.documented_functions += 1
        else:
            self.issues.append({
                "type": "missing_docstring",
                "function": node.name,
                "line": node.lineno,
                "message": f"函数 '{node.name}' 缺少文档字符串"
            })

        # 检查类型注解
        has_annotations = bool(node.returns) or any(
            arg.annotation for arg in node.args.args
        )
        if has_annotations:
            self.annotated_functions += 1
        else:
            self.issues.append({
                "type": "missing_type_annotation",
                "function": node.name,
                "line": node.lineno,
                "message": f"函数 '{node.name}' 缺少类型注解"
            })

        self.generic_visit(node)

    def get_annotation_coverage(self) -> float:
        """获取类型注解覆盖率"""
        if self.total_functions == 0:
            return 0.0
        return self.annotated_functions / self.total_functions
