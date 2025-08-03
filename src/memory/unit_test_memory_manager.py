"""
UnitTestAgent专用Memory管理器

为UnitTestAgent提供完整的测试输出保存和检索功能，
确保RefactoringAgent能够获取到详细的错误信息
"""

import asyncio
import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from autogen_core.memory import MemoryContent, MemoryMimeType
from .memory_config import memory_config
from .base_memory_manager import execution_log_manager


class UnitTestMemoryManager:
    """UnitTestAgent专用Memory管理器"""
    
    def __init__(self):
        self.execution_log_manager = execution_log_manager
        self.test_memory = None
        self._initialized = False
        
        # 测试结果缓存
        self.latest_test_results = {}
        self.test_history = []
    
    async def initialize(self):
        """初始化UnitTest Memory系统"""
        if not self._initialized:
            self.test_memory = memory_config.create_workflow_memory()
            self._initialized = True
            print("🧪 UnitTest专用Memory系统初始化完成")
    
    # ================================
    # 完整测试输出保存
    # ================================
    
    async def record_complete_test_execution(self,
                                           agent_name: str,
                                           task_description: str,
                                           raw_output: str,
                                           execution_result: Dict[str, Any],
                                           success: bool,
                                           duration: float,
                                           test_files: List[str] = None,
                                           test_reports: Dict[str, Any] = None):
        """记录完整的测试执行信息"""
        if not self._initialized:
            await self.initialize()
        
        timestamp = datetime.now().isoformat()
        
        # 解析测试输出
        parsed_output = self._parse_test_output(raw_output)
        
        # 构建完整的测试记录
        complete_test_record = {
            "agent_name": agent_name,
            "task_description": task_description,
            "timestamp": timestamp,
            "success": success,
            "duration": duration,
            "raw_output": raw_output,
            "parsed_output": parsed_output,
            "execution_result": execution_result,
            "test_files": test_files or [],
            "test_reports": test_reports or {},
            "analysis": self._analyze_test_results(parsed_output, success)
        }
        
        # 更新缓存
        self.latest_test_results[agent_name] = complete_test_record
        self.test_history.append(complete_test_record)
        
        # 保存到向量数据库
        await self._store_complete_test_record(complete_test_record)
        
        print(f"🧪 完整测试记录已保存: {agent_name} - {'成功' if success else '失败'}")
        
        return complete_test_record
    
    def _parse_test_output(self, raw_output: str) -> Dict[str, Any]:
        """解析测试输出，提取关键信息"""
        parsed = {
            "test_summary": {},
            "failures": [],
            "errors": [],
            "passed_tests": [],
            "test_files_executed": [],
            "execution_details": []
        }
        
        lines = raw_output.split('\n')
        current_section = None
        current_failure = {}
        
        for line in lines:
            line = line.strip()
            
            # 解析测试摘要
            if "tests run" in line.lower() or "ran " in line.lower():
                # 提取测试数量信息
                numbers = re.findall(r'\d+', line)
                if numbers:
                    parsed["test_summary"]["total_tests"] = int(numbers[0]) if numbers else 0
            
            # 解析失败信息
            if line.startswith("FAIL:") or line.startswith("ERROR:"):
                if current_failure:
                    if current_section == "failure":
                        parsed["failures"].append(current_failure)
                    elif current_section == "error":
                        parsed["errors"].append(current_failure)
                
                current_failure = {
                    "test_name": line.split(":", 1)[1].strip() if ":" in line else line,
                    "type": "FAIL" if line.startswith("FAIL:") else "ERROR",
                    "details": []
                }
                current_section = "failure" if line.startswith("FAIL:") else "error"
            
            # 收集失败详情
            elif current_section in ["failure", "error"] and line:
                if line.startswith("AssertionError") or line.startswith("Traceback") or "File " in line:
                    current_failure["details"].append(line)
            
            # 解析通过的测试
            elif "ok" in line.lower() and "test" in line.lower():
                parsed["passed_tests"].append(line)
            
            # 解析执行的测试文件
            elif line.startswith("🧪 执行测试文件:") or "test_" in line and ".py" in line:
                parsed["test_files_executed"].append(line)
            
            # 收集执行详情
            elif line.startswith("📊") or line.startswith("✅") or line.startswith("❌"):
                parsed["execution_details"].append(line)
        
        # 处理最后一个失败记录
        if current_failure:
            if current_section == "failure":
                parsed["failures"].append(current_failure)
            elif current_section == "error":
                parsed["errors"].append(current_failure)
        
        # 计算统计信息
        parsed["test_summary"].update({
            "failures_count": len(parsed["failures"]),
            "errors_count": len(parsed["errors"]),
            "passed_count": len(parsed["passed_tests"]),
            "files_executed": len(parsed["test_files_executed"])
        })
        
        return parsed
    
    def _analyze_test_results(self, parsed_output: Dict[str, Any], success: bool) -> Dict[str, Any]:
        """分析测试结果，生成智能分析"""
        analysis = {
            "overall_status": "PASSED" if success else "FAILED",
            "key_issues": [],
            "recommendations": [],
            "error_patterns": [],
            "fix_suggestions": []
        }
        
        # 分析失败模式
        for failure in parsed_output.get("failures", []):
            issue = {
                "type": "test_failure",
                "test": failure.get("test_name", ""),
                "details": failure.get("details", [])
            }
            analysis["key_issues"].append(issue)
            
            # 分析错误模式
            details_text = " ".join(failure.get("details", []))
            if "AssertionError" in details_text:
                analysis["error_patterns"].append("assertion_error")
                if "Expected" in details_text and "but got" in details_text:
                    analysis["fix_suggestions"].append("检查函数返回值格式")
            elif "ImportError" in details_text or "ModuleNotFoundError" in details_text:
                analysis["error_patterns"].append("import_error")
                analysis["fix_suggestions"].append("检查模块导入路径")
            elif "AttributeError" in details_text:
                analysis["error_patterns"].append("attribute_error")
                analysis["fix_suggestions"].append("检查函数或属性名称")
        
        # 分析错误
        for error in parsed_output.get("errors", []):
            issue = {
                "type": "test_error",
                "test": error.get("test_name", ""),
                "details": error.get("details", [])
            }
            analysis["key_issues"].append(issue)
        
        # 生成建议
        if not success:
            if analysis["error_patterns"]:
                analysis["recommendations"].append("重点关注以下错误模式: " + ", ".join(set(analysis["error_patterns"])))
            
            if "assertion_error" in analysis["error_patterns"]:
                analysis["recommendations"].append("检查业务逻辑实现是否符合测试期望")
            
            if "import_error" in analysis["error_patterns"]:
                analysis["recommendations"].append("检查文件路径和模块结构")
        else:
            analysis["recommendations"].append("所有测试通过，代码质量良好")
        
        return analysis
    
    # ================================
    # 为RefactoringAgent提供详细信息
    # ================================
    
    async def get_detailed_test_info_for_refactoring(self, agent_name: str = "UnitTestAgent") -> Dict[str, Any]:
        """为RefactoringAgent提供详细的测试信息"""
        if agent_name in self.latest_test_results:
            test_record = self.latest_test_results[agent_name]
            
            # 构建RefactoringAgent需要的详细信息
            refactoring_info = {
                "test_execution_summary": {
                    "success": test_record["success"],
                    "duration": test_record["duration"],
                    "timestamp": test_record["timestamp"]
                },
                "complete_raw_output": test_record["raw_output"],
                "parsed_failures": test_record["parsed_output"].get("failures", []),
                "parsed_errors": test_record["parsed_output"].get("errors", []),
                "test_files": test_record["test_files"],
                "analysis": test_record["analysis"],
                "fix_suggestions": test_record["analysis"].get("fix_suggestions", []),
                "error_patterns": test_record["analysis"].get("error_patterns", []),
                "detailed_recommendations": self._generate_detailed_recommendations(test_record)
            }
            
            return refactoring_info
        
        return {}
    
    def _generate_detailed_recommendations(self, test_record: Dict[str, Any]) -> List[str]:
        """生成详细的修复建议"""
        recommendations = []
        parsed_output = test_record["parsed_output"]
        
        # 基于失败信息生成具体建议
        for failure in parsed_output.get("failures", []):
            test_name = failure.get("test_name", "")
            details = " ".join(failure.get("details", []))
            
            if "AssertionError" in details:
                if "Expected" in details and "but got" in details:
                    # 提取期望值和实际值
                    expected_match = re.search(r"Expected[:\s]+['\"]([^'\"]+)['\"]", details)
                    got_match = re.search(r"but got[:\s]+['\"]([^'\"]+)['\"]", details)
                    
                    if expected_match and got_match:
                        expected = expected_match.group(1)
                        got = got_match.group(1)
                        recommendations.append(f"测试 {test_name}: 期望返回 '{expected}'，实际返回 '{got}'，请检查函数实现")
                    else:
                        recommendations.append(f"测试 {test_name}: 断言失败，请检查函数返回值")
                else:
                    recommendations.append(f"测试 {test_name}: 断言错误，请检查测试逻辑")
            
            elif "ImportError" in details or "ModuleNotFoundError" in details:
                recommendations.append(f"测试 {test_name}: 模块导入失败，请检查文件路径和模块结构")
            
            elif "AttributeError" in details:
                recommendations.append(f"测试 {test_name}: 属性错误，请检查函数名称或类属性")
        
        return recommendations
    
    async def get_test_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取测试历史记录"""
        return self.test_history[-limit:] if self.test_history else []
    
    # ================================
    # 内部存储方法
    # ================================
    
    async def _store_complete_test_record(self, test_record: Dict[str, Any]):
        """将完整测试记录存储到向量数据库"""
        if not self._initialized:
            await self.initialize()
        
        # 构建存储内容
        content = f"""
UnitTest Complete Record: {test_record['agent_name']}
Task: {test_record['task_description']}
Timestamp: {test_record['timestamp']}
Success: {test_record['success']}
Duration: {test_record['duration']}s

=== RAW OUTPUT ===
{test_record['raw_output']}

=== PARSED ANALYSIS ===
Test Summary: {json.dumps(test_record['parsed_output']['test_summary'], ensure_ascii=False)}
Failures: {len(test_record['parsed_output']['failures'])}
Errors: {len(test_record['parsed_output']['errors'])}

=== FAILURE DETAILS ===
{json.dumps(test_record['parsed_output']['failures'], indent=2, ensure_ascii=False)}

=== ERROR DETAILS ===
{json.dumps(test_record['parsed_output']['errors'], indent=2, ensure_ascii=False)}

=== INTELLIGENT ANALYSIS ===
{json.dumps(test_record['analysis'], indent=2, ensure_ascii=False)}
        """.strip()
        
        await self.test_memory.add(
            MemoryContent(
                content=content,
                mime_type=MemoryMimeType.TEXT,
                metadata={
                    "type": "complete_unit_test",
                    "agent_name": test_record['agent_name'],
                    "success": test_record['success'],
                    "timestamp": test_record['timestamp'],
                    "duration": test_record['duration'],
                    "failures_count": len(test_record['parsed_output']['failures']),
                    "errors_count": len(test_record['parsed_output']['errors']),
                    "test_files_count": len(test_record['test_files'])
                }
            )
        )
    
    async def close(self):
        """关闭UnitTest Memory连接"""
        if self.test_memory:
            await self.test_memory.close()


# 全局实例
unit_test_memory_manager = UnitTestMemoryManager()
