"""
任务复杂度分析器

基于多维度指标和LLM评估的任务复杂度分析系统
"""

import re
import json
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import math

from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core.models import UserMessage


class ComplexityLevel(Enum):
    """复杂度等级"""
    TRIVIAL = "trivial"      # 0.0-0.2: 极简单
    SIMPLE = "simple"        # 0.2-0.4: 简单
    MODERATE = "moderate"    # 0.4-0.6: 中等
    COMPLEX = "complex"      # 0.6-0.8: 复杂
    VERY_COMPLEX = "very_complex"  # 0.8-1.0: 极复杂


@dataclass
class ComplexityMetrics:
    """复杂度指标数据类"""
    
    # 基础指标
    estimated_functions: int = 0
    estimated_classes: int = 0
    estimated_modules: int = 0
    estimated_lines_of_code: int = 0
    
    # 技术复杂度指标
    algorithm_complexity: float = 0.0      # 算法复杂度 (0-1)
    data_structure_complexity: float = 0.0 # 数据结构复杂度 (0-1)
    integration_complexity: float = 0.0    # 集成复杂度 (0-1)
    
    # 领域复杂度指标
    domain_expertise_required: float = 0.0 # 领域专业知识要求 (0-1)
    business_logic_complexity: float = 0.0 # 业务逻辑复杂度 (0-1)
    
    # LLM评估指标
    llm_cognitive_load: float = 0.0        # 认知负荷 (0-1)
    llm_implementation_difficulty: float = 0.0  # 实现难度 (0-1)
    llm_testing_complexity: float = 0.0    # 测试复杂度 (0-1)
    
    # 综合指标
    overall_complexity: float = 0.0        # 总体复杂度 (0-1)
    complexity_level: ComplexityLevel = ComplexityLevel.SIMPLE
    confidence_score: float = 0.0          # 评估置信度 (0-1)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = asdict(self)
        result['complexity_level'] = self.complexity_level.value
        return result


class TaskComplexityAnalyzer:
    """任务复杂度分析器"""
    
    def __init__(self, model_client: Optional[OpenAIChatCompletionClient] = None):
        """
        初始化分析器
        
        Args:
            model_client: LLM模型客户端，如果为None则只使用规则基础分析
        """
        self.model_client = model_client
        
        # 复杂度关键词字典
        self.complexity_keywords = {
            "algorithm": {
                "high": ["递归", "动态规划", "图算法", "机器学习", "深度学习", "神经网络", 
                        "optimization", "recursive", "dynamic programming", "graph algorithm",
                        "machine learning", "deep learning", "neural network", "AI"],
                "medium": ["排序", "搜索", "哈希", "树", "队列", "栈", "链表",
                          "sorting", "searching", "hash", "tree", "queue", "stack", "linked list"],
                "low": ["遍历", "计数", "求和", "比较", "iteration", "counting", "sum", "comparison"]
            },
            "data_structure": {
                "high": ["图", "树", "堆", "并查集", "线段树", "字典树",
                        "graph", "tree", "heap", "union find", "segment tree", "trie"],
                "medium": ["哈希表", "队列", "栈", "链表", "数组",
                          "hash table", "queue", "stack", "linked list", "array"],
                "low": ["列表", "字典", "集合", "list", "dict", "set"]
            },
            "integration": {
                "high": ["API集成", "数据库", "微服务", "分布式", "并发", "多线程",
                        "API integration", "database", "microservice", "distributed", "concurrent", "multithreading"],
                "medium": ["文件操作", "网络请求", "配置管理", "日志",
                          "file operation", "network request", "configuration", "logging"],
                "low": ["简单输入输出", "基础计算", "simple I/O", "basic calculation"]
            }
        }
        
        
        # 权重配置
        if model_client:
            # 有LLM时，更依赖LLM评估
            self.weights = {
                "basic_metrics": 0.15,          # 基础指标权重
                "technical_complexity": 0.25,   # 技术复杂度权重
                "domain_complexity": 0.15,      # 领域复杂度权重
                "llm_evaluation": 0.45          # LLM评估权重
            }
        else:
            # 无LLM时，更依赖规则分析
            self.weights = {
                "basic_metrics": 0.3,           # 基础指标权重
                "technical_complexity": 0.4,    # 技术复杂度权重
                "domain_complexity": 0.3,       # 领域复杂度权重
                "llm_evaluation": 0.0           # LLM评估权重
            }
    
    async def analyze_complexity(self, task_description: str) -> ComplexityMetrics:
        """
        分析任务复杂度
        
        Args:
            task_description: 任务描述
            
        Returns:
            ComplexityMetrics: 复杂度指标
        """
        metrics = ComplexityMetrics()
        
        # 1. 基础指标分析
        self._analyze_basic_metrics(task_description, metrics)
        
        # 2. 技术复杂度分析
        self._analyze_technical_complexity(task_description, metrics)
        
        # 3. 领域复杂度分析
        self._analyze_domain_complexity(task_description, metrics)
        
        # 4. LLM评估 (如果有模型客户端)
        if self.model_client:
            await self._llm_complexity_evaluation(task_description, metrics)
        
        # 5. 计算综合复杂度
        self._calculate_overall_complexity(metrics)
        
        return metrics
    
    def _analyze_basic_metrics(self, task_description: str, metrics: ComplexityMetrics):
        """分析基础指标"""

        desc_lower = task_description.lower()

        # 更智能的功能数量估算
        feature_keywords = [
            "功能", "特性", "模块", "组件", "服务", "接口", "API", "方法", "函数",
            "feature", "function", "module", "component", "service", "interface", "method",
            "支持", "包含", "实现", "提供", "管理", "处理", "操作",
            "support", "include", "implement", "provide", "manage", "handle", "process"
        ]

        # 通过逗号、顿号、"和"、"及"等分隔符分析功能数量
        separators = ["，", ",", "、", "和", "及", "以及", "还有", "and", "also", "plus"]
        feature_count = 1  # 至少有一个功能

        for sep in separators:
            feature_count += desc_lower.count(sep)

        # 通过功能关键词调整
        keyword_count = sum(desc_lower.count(keyword) for keyword in feature_keywords)
        feature_count = max(feature_count, keyword_count // 2)  # 避免过度计算

        metrics.estimated_functions = max(1, min(feature_count, 20))  # 限制在合理范围

        # 更智能的类数量估算
        class_indicators = [
            "系统", "平台", "应用", "工具", "管理器", "处理器", "分析器", "生成器",
            "system", "platform", "application", "tool", "manager", "processor", "analyzer", "generator",
            "用户", "订单", "商品", "文件", "数据", "消息", "任务", "项目",
            "user", "order", "product", "file", "data", "message", "task", "project"
        ]

        class_count = 0
        for indicator in class_indicators:
            if indicator in desc_lower:
                class_count += 1

        # 根据系统复杂度调整类数量
        if any(word in desc_lower for word in ["分布式", "微服务", "架构", "distributed", "microservice", "architecture"]):
            class_count = max(class_count, 5)
        elif any(word in desc_lower for word in ["系统", "平台", "应用", "system", "platform", "application"]):
            class_count = max(class_count, 3)

        metrics.estimated_classes = min(class_count, 15)  # 限制在合理范围

        # 更智能的模块数量估算
        module_indicators = [
            "模块", "包", "库", "组件", "服务", "层", "部分",
            "module", "package", "library", "component", "service", "layer", "part"
        ]

        module_count = 1  # 至少有一个模块
        for indicator in module_indicators:
            module_count += desc_lower.count(indicator)

        # 根据功能复杂度调整模块数量
        if metrics.estimated_functions > 10:
            module_count = max(module_count, 3)
        elif metrics.estimated_functions > 5:
            module_count = max(module_count, 2)

        metrics.estimated_modules = min(module_count, 10)  # 限制在合理范围

        # 更准确的代码行数估算
        base_complexity = len(desc_lower.split()) / 10  # 基于描述长度

        # 根据不同因素调整代码行数
        lines_per_function = 20 + base_complexity * 5  # 基础每函数行数
        lines_per_class = 80 + base_complexity * 10    # 基础每类行数

        # 根据技术复杂度调整
        if any(word in desc_lower for word in ["算法", "机器学习", "深度学习", "AI", "algorithm", "machine learning", "deep learning"]):
            lines_per_function *= 2
            lines_per_class *= 1.5

        if any(word in desc_lower for word in ["数据库", "API", "网络", "并发", "database", "network", "concurrent"]):
            lines_per_function *= 1.5
            lines_per_class *= 1.3

        estimated_lines = (
            metrics.estimated_functions * lines_per_function +
            metrics.estimated_classes * lines_per_class +
            metrics.estimated_modules * 30
        )

        metrics.estimated_lines_of_code = int(min(estimated_lines, 10000))  # 限制在合理范围
    
    def _analyze_technical_complexity(self, task_description: str, metrics: ComplexityMetrics):
        """分析技术复杂度"""
        
        desc_lower = task_description.lower()
        
        # 算法复杂度分析
        algo_score = 0.0
        for level, keywords in self.complexity_keywords["algorithm"].items():
            weight = {"high": 1.0, "medium": 0.6, "low": 0.3}[level]
            for keyword in keywords:
                if keyword in desc_lower:
                    algo_score = max(algo_score, weight)
        
        metrics.algorithm_complexity = min(algo_score, 1.0)
        
        # 数据结构复杂度分析
        ds_score = 0.0
        for level, keywords in self.complexity_keywords["data_structure"].items():
            weight = {"high": 1.0, "medium": 0.6, "low": 0.3}[level]
            for keyword in keywords:
                if keyword in desc_lower:
                    ds_score = max(ds_score, weight)
        
        metrics.data_structure_complexity = min(ds_score, 1.0)
        
        # 集成复杂度分析
        integration_score = 0.0
        for level, keywords in self.complexity_keywords["integration"].items():
            weight = {"high": 1.0, "medium": 0.6, "low": 0.3}[level]
            for keyword in keywords:
                if keyword in desc_lower:
                    integration_score = max(integration_score, weight)
        
        metrics.integration_complexity = min(integration_score, 1.0)
    
    def _analyze_domain_complexity(self, task_description: str, metrics: ComplexityMetrics):
        """分析领域复杂度"""
        
        desc_lower = task_description.lower()
        
        # 领域专业知识要求
        domain_keywords = {
            "high": ["金融", "医疗", "法律", "科学计算", "密码学", "区块链",
                    "finance", "medical", "legal", "scientific computing", "cryptography", "blockchain"],
            "medium": ["电商", "教育", "游戏", "社交", "媒体",
                      "e-commerce", "education", "game", "social", "media"],
            "low": ["工具", "计算器", "转换器", "简单应用",
                   "tool", "calculator", "converter", "simple application"]
        }
        
        domain_score = 0.0
        for level, keywords in domain_keywords.items():
            weight = {"high": 1.0, "medium": 0.5, "low": 0.2}[level]
            for keyword in keywords:
                if keyword in desc_lower:
                    domain_score = max(domain_score, weight)
        
        metrics.domain_expertise_required = min(domain_score, 1.0)
        
        # 业务逻辑复杂度
        business_indicators = ["规则", "流程", "状态", "条件", "判断", "逻辑",
                              "rule", "process", "state", "condition", "judgment", "logic"]
        
        business_count = sum(desc_lower.count(indicator) for indicator in business_indicators)
        metrics.business_logic_complexity = min(business_count * 0.2, 1.0)

    async def _llm_complexity_evaluation(self, task_description: str, metrics: ComplexityMetrics):
        """使用LLM进行复杂度评估"""

        evaluation_prompt = f"""
请作为一个资深的软件工程师，从多个维度评估以下任务的复杂度。

任务描述：
{task_description}

请从以下三个维度进行评估，每个维度给出0-1之间的分数（保留2位小数）：

1. 认知负荷 (Cognitive Load): 理解和设计这个任务需要多少认知努力？
   - 0.0-0.3: 简单直观，容易理解
   - 0.3-0.6: 需要一定思考，中等难度
   - 0.6-1.0: 需要深度思考，认知负荷重

2. 实现难度 (Implementation Difficulty): 编码实现这个任务有多困难？
   - 0.0-0.3: 直接实现，代码简单
   - 0.3-0.6: 需要一些技巧，中等实现难度
   - 0.6-1.0: 需要高级技术，实现困难

3. 测试复杂度 (Testing Complexity): 为这个任务编写测试用例有多复杂？
   - 0.0-0.3: 简单的输入输出测试
   - 0.3-0.6: 需要多种测试场景
   - 0.6-1.0: 需要复杂的测试策略

请严格按照以下JSON格式回复，不要包含任何其他内容：
{{
    "cognitive_load": 0.XX,
    "implementation_difficulty": 0.XX,
    "testing_complexity": 0.XX,
    "reasoning": "简要说明评估理由"
}}
"""

        try:
            # 调用LLM进行评估
            messages = [UserMessage(content=evaluation_prompt, source="user")]
            response = await self.model_client.create(messages)

            # 解析响应
            response_content = response.content

            # 提取JSON部分
            json_match = re.search(r'\{[^{}]*\}', response_content, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                evaluation_result = json.loads(json_str)

                # 更新指标
                metrics.llm_cognitive_load = float(evaluation_result.get("cognitive_load", 0.5))
                metrics.llm_implementation_difficulty = float(evaluation_result.get("implementation_difficulty", 0.5))
                metrics.llm_testing_complexity = float(evaluation_result.get("testing_complexity", 0.5))

                # 设置高置信度
                metrics.confidence_score = 0.9

            else:
                # 解析失败，使用默认值
                metrics.llm_cognitive_load = 0.5
                metrics.llm_implementation_difficulty = 0.5
                metrics.llm_testing_complexity = 0.5
                metrics.confidence_score = 0.3

        except Exception as e:
            print(f"LLM评估失败: {e}")
            # 使用默认值
            metrics.llm_cognitive_load = 0.5
            metrics.llm_implementation_difficulty = 0.5
            metrics.llm_testing_complexity = 0.5
            metrics.confidence_score = 0.2

    def _calculate_overall_complexity(self, metrics: ComplexityMetrics):
        """计算综合复杂度"""

        # 基础指标得分 (归一化)
        basic_score = self._normalize_basic_metrics(metrics)

        # 技术复杂度得分
        technical_score = (
            metrics.algorithm_complexity * 0.4 +
            metrics.data_structure_complexity * 0.3 +
            metrics.integration_complexity * 0.3
        )

        # 领域复杂度得分
        domain_score = (
            metrics.domain_expertise_required * 0.6 +
            metrics.business_logic_complexity * 0.4
        )

        # LLM评估得分
        llm_score = (
            metrics.llm_cognitive_load * 0.4 +
            metrics.llm_implementation_difficulty * 0.4 +
            metrics.llm_testing_complexity * 0.2
        )

        # 加权计算总体复杂度
        overall_complexity = (
            basic_score * self.weights["basic_metrics"] +
            technical_score * self.weights["technical_complexity"] +
            domain_score * self.weights["domain_complexity"] +
            llm_score * self.weights["llm_evaluation"]
        )

        metrics.overall_complexity = min(overall_complexity, 1.0)

        # 确定复杂度等级 (调整阈值以提高分类准确性)
        if metrics.overall_complexity < 0.15:
            metrics.complexity_level = ComplexityLevel.TRIVIAL
        elif metrics.overall_complexity < 0.35:
            metrics.complexity_level = ComplexityLevel.SIMPLE
        elif metrics.overall_complexity < 0.55:
            metrics.complexity_level = ComplexityLevel.MODERATE
        elif metrics.overall_complexity < 0.75:
            metrics.complexity_level = ComplexityLevel.COMPLEX
        else:
            metrics.complexity_level = ComplexityLevel.VERY_COMPLEX

        # 如果没有LLM评估，降低置信度
        if metrics.confidence_score == 0.0:
            metrics.confidence_score = 0.6  # 仅基于规则的评估

    def _normalize_basic_metrics(self, metrics: ComplexityMetrics) -> float:
        """归一化基础指标"""

        # 使用对数缩放来处理大数值
        function_score = min(math.log(metrics.estimated_functions + 1) / math.log(20), 1.0)
        class_score = min(math.log(metrics.estimated_classes + 1) / math.log(10), 1.0)
        module_score = min(math.log(metrics.estimated_modules + 1) / math.log(5), 1.0)
        loc_score = min(math.log(metrics.estimated_lines_of_code + 1) / math.log(1000), 1.0)

        # 加权平均
        basic_score = (
            function_score * 0.3 +
            class_score * 0.2 +
            module_score * 0.2 +
            loc_score * 0.3
        )

        return basic_score

    def get_complexity_summary(self, metrics: ComplexityMetrics) -> Dict[str, Any]:
        """获取复杂度分析摘要"""

        return {
            "overall_complexity": round(metrics.overall_complexity, 3),
            "complexity_level": metrics.complexity_level.value,
            "confidence_score": round(metrics.confidence_score, 3),
            "estimated_effort": self._estimate_effort(metrics),
            "recommended_approach": self._recommend_approach(metrics),
            "key_challenges": self._identify_key_challenges(metrics),
            "breakdown": {
                "basic_metrics": {
                    "functions": metrics.estimated_functions,
                    "classes": metrics.estimated_classes,
                    "modules": metrics.estimated_modules,
                    "lines_of_code": metrics.estimated_lines_of_code
                },
                "technical_complexity": {
                    "algorithm": round(metrics.algorithm_complexity, 3),
                    "data_structure": round(metrics.data_structure_complexity, 3),
                    "integration": round(metrics.integration_complexity, 3)
                },
                "domain_complexity": {
                    "domain_expertise": round(metrics.domain_expertise_required, 3),
                    "business_logic": round(metrics.business_logic_complexity, 3)
                },
                "llm_evaluation": {
                    "cognitive_load": round(metrics.llm_cognitive_load, 3),
                    "implementation_difficulty": round(metrics.llm_implementation_difficulty, 3),
                    "testing_complexity": round(metrics.llm_testing_complexity, 3)
                }
            }
        }

    def _estimate_effort(self, metrics: ComplexityMetrics) -> Dict[str, str]:
        """估算开发工作量"""

        complexity = metrics.overall_complexity

        if complexity < 0.2:
            return {
                "development_time": "1-2小时",
                "testing_time": "30分钟-1小时",
                "total_effort": "低"
            }
        elif complexity < 0.4:
            return {
                "development_time": "2-6小时",
                "testing_time": "1-2小时",
                "total_effort": "中低"
            }
        elif complexity < 0.6:
            return {
                "development_time": "6-16小时",
                "testing_time": "2-4小时",
                "total_effort": "中等"
            }
        elif complexity < 0.8:
            return {
                "development_time": "1-3天",
                "testing_time": "4-8小时",
                "total_effort": "中高"
            }
        else:
            return {
                "development_time": "3-7天",
                "testing_time": "1-2天",
                "total_effort": "高"
            }

    def _recommend_approach(self, metrics: ComplexityMetrics) -> List[str]:
        """推荐开发方法"""

        recommendations = []

        if metrics.algorithm_complexity > 0.7:
            recommendations.append("建议先进行算法设计和原型验证")

        if metrics.data_structure_complexity > 0.7:
            recommendations.append("重点关注数据结构设计和性能优化")

        if metrics.integration_complexity > 0.7:
            recommendations.append("建议采用分层架构，先实现核心逻辑再处理集成")

        if metrics.domain_expertise_required > 0.7:
            recommendations.append("需要领域专家参与需求分析和验证")

        if metrics.business_logic_complexity > 0.7:
            recommendations.append("建议使用状态机或规则引擎处理复杂业务逻辑")

        if metrics.llm_testing_complexity > 0.7:
            recommendations.append("需要设计全面的测试策略，包括边界条件和异常情况")

        if not recommendations:
            recommendations.append("可以采用标准的开发流程")

        return recommendations

    def _identify_key_challenges(self, metrics: ComplexityMetrics) -> List[str]:
        """识别关键挑战"""

        challenges = []

        if metrics.algorithm_complexity > 0.6:
            challenges.append("算法实现复杂度高")

        if metrics.data_structure_complexity > 0.6:
            challenges.append("数据结构设计复杂")

        if metrics.integration_complexity > 0.6:
            challenges.append("系统集成复杂")

        if metrics.domain_expertise_required > 0.6:
            challenges.append("需要专业领域知识")

        if metrics.business_logic_complexity > 0.6:
            challenges.append("业务逻辑复杂")

        if metrics.llm_cognitive_load > 0.7:
            challenges.append("认知负荷重，需要深度思考")

        if metrics.llm_implementation_difficulty > 0.7:
            challenges.append("实现技术难度高")

        if metrics.llm_testing_complexity > 0.7:
            challenges.append("测试用例设计复杂")

        return challenges if challenges else ["无明显技术挑战"]
