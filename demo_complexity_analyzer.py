#!/usr/bin/env python3
"""
任务复杂度分析器演示

展示多维度任务复杂度评估功能的实际应用
"""

import asyncio
import sys
import json
from pathlib import Path

# 添加项目根目录到路径
sys.path.append(str(Path(__file__).parent))

from src.intelligence.task_complexity_analyzer import TaskComplexityAnalyzer, ComplexityLevel
from src.config.model_config import create_model_client


async def interactive_demo():
    """交互式演示"""
    print("🎯 任务复杂度分析器 - 交互式演示")
    print("=" * 60)
    print("请输入您的任务描述，我将为您分析其复杂度")
    print("输入 'quit' 退出程序")
    print()
    
    # 创建分析器
    try:
        model_client = create_model_client()
        analyzer = TaskComplexityAnalyzer(model_client)
        print("✅ LLM增强分析器已启动")
    except:
        analyzer = TaskComplexityAnalyzer()
        print("⚠️ 使用基础规则分析器（无LLM）")
    
    while True:
        try:
            # 获取用户输入
            task_description = input("\n📝 请输入任务描述: ").strip()
            
            if task_description.lower() in ['quit', 'exit', '退出']:
                break
            
            if not task_description:
                print("❌ 请输入有效的任务描述")
                continue
            
            print("\n🔍 正在分析...")
            
            # 分析复杂度
            metrics = await analyzer.analyze_complexity(task_description)
            summary = analyzer.get_complexity_summary(metrics)
            
            # 显示结果
            print("\n📊 分析结果:")
            print("-" * 40)
            print(f"🎯 复杂度等级: {summary['complexity_level'].upper()}")
            print(f"📈 复杂度分数: {summary['overall_complexity']:.3f}")
            print(f"🎲 置信度: {summary['confidence_score']:.3f}")
            
            print(f"\n⏱️ 预估工作量:")
            effort = summary['estimated_effort']
            print(f"  开发时间: {effort['development_time']}")
            print(f"  测试时间: {effort['testing_time']}")
            print(f"  总体工作量: {effort['total_effort']}")
            
            print(f"\n🔧 推荐方法:")
            for rec in summary['recommended_approach']:
                print(f"  • {rec}")
            
            print(f"\n⚠️ 关键挑战:")
            for challenge in summary['key_challenges']:
                print(f"  • {challenge}")
            
            # 显示详细分解
            breakdown = summary['breakdown']
            print(f"\n📋 详细分解:")
            print(f"  基础指标: {breakdown['basic_metrics']['functions']}个函数, "
                  f"{breakdown['basic_metrics']['classes']}个类, "
                  f"约{breakdown['basic_metrics']['lines_of_code']}行代码")
            
            tech = breakdown['technical_complexity']
            print(f"  技术复杂度: 算法({tech['algorithm']:.2f}), "
                  f"数据结构({tech['data_structure']:.2f}), "
                  f"集成({tech['integration']:.2f})")
            
            if breakdown['llm_evaluation']['cognitive_load'] > 0:
                llm = breakdown['llm_evaluation']
                print(f"  LLM评估: 认知负荷({llm['cognitive_load']:.2f}), "
                      f"实现难度({llm['implementation_difficulty']:.2f}), "
                      f"测试复杂度({llm['testing_complexity']:.2f})")
        
        except KeyboardInterrupt:
            print("\n\n👋 程序已退出")
            break
        except Exception as e:
            print(f"\n❌ 分析失败: {e}")
    
    # 清理资源
    if hasattr(analyzer, 'model_client') and analyzer.model_client:
        await analyzer.model_client.close()


async def preset_demo():
    """预设示例演示"""
    print("🎯 任务复杂度分析器 - 预设示例演示")
    print("=" * 60)
    
    # 创建分析器
    try:
        model_client = create_model_client()
        analyzer = TaskComplexityAnalyzer(model_client)
        print("✅ LLM增强分析器已启动\n")
    except:
        analyzer = TaskComplexityAnalyzer()
        print("⚠️ 使用基础规则分析器（无LLM）\n")
    
    # 预设示例
    examples = [
        {
            "name": "简单工具",
            "description": "创建一个密码生成器，可以生成指定长度的随机密码",
            "expected": "simple"
        },
        {
            "name": "中等系统",
            "description": "开发一个在线图书管理系统，包含图书增删改查、用户管理、借阅记录、搜索功能",
            "expected": "moderate"
        },
        {
            "name": "复杂平台",
            "description": "构建一个实时数据分析平台，支持多种数据源接入、流式处理、机器学习预测、可视化展示",
            "expected": "complex"
        },
        {
            "name": "极复杂系统",
            "description": "开发一个自动驾驶系统，包含计算机视觉、深度学习、路径规划、决策控制、安全监控",
            "expected": "very_complex"
        }
    ]
    
    for i, example in enumerate(examples, 1):
        print(f"📋 示例 {i}: {example['name']}")
        print(f"描述: {example['description']}")
        print(f"预期复杂度: {example['expected']}")
        
        # 分析复杂度
        metrics = await analyzer.analyze_complexity(example['description'])
        summary = analyzer.get_complexity_summary(metrics)
        
        # 显示结果
        actual = summary['complexity_level']
        score = summary['overall_complexity']
        confidence = summary['confidence_score']
        
        status = "✅ 符合预期" if actual == example['expected'] else "❌ 不符合预期"
        print(f"分析结果: {actual} (分数: {score:.3f}, 置信度: {confidence:.3f}) {status}")
        
        # 显示关键信息
        effort = summary['estimated_effort']['total_effort']
        challenges = summary['key_challenges'][:2]  # 只显示前2个挑战
        
        print(f"工作量: {effort}, 主要挑战: {', '.join(challenges)}")
        print("-" * 60)
    
    # 清理资源
    if hasattr(analyzer, 'model_client') and analyzer.model_client:
        await analyzer.model_client.close()


async def comparison_demo():
    """对比演示：有LLM vs 无LLM"""
    print("🎯 任务复杂度分析器 - 对比演示")
    print("=" * 60)
    
    test_task = "开发一个基于微服务架构的电商平台，包含用户服务、商品服务、订单服务、支付服务、推荐系统"
    
    print(f"测试任务: {test_task}\n")
    
    # 无LLM分析
    print("🔧 基础规则分析器:")
    basic_analyzer = TaskComplexityAnalyzer()
    basic_metrics = await basic_analyzer.analyze_complexity(test_task)
    basic_summary = basic_analyzer.get_complexity_summary(basic_metrics)
    
    print(f"  复杂度: {basic_summary['complexity_level']} (分数: {basic_summary['overall_complexity']:.3f})")
    print(f"  置信度: {basic_summary['confidence_score']:.3f}")
    print(f"  工作量: {basic_summary['estimated_effort']['total_effort']}")
    
    # 有LLM分析
    try:
        print("\n🤖 LLM增强分析器:")
        model_client = create_model_client()
        llm_analyzer = TaskComplexityAnalyzer(model_client)
        llm_metrics = await llm_analyzer.analyze_complexity(test_task)
        llm_summary = llm_analyzer.get_complexity_summary(llm_metrics)
        
        print(f"  复杂度: {llm_summary['complexity_level']} (分数: {llm_summary['overall_complexity']:.3f})")
        print(f"  置信度: {llm_summary['confidence_score']:.3f}")
        print(f"  工作量: {llm_summary['estimated_effort']['total_effort']}")
        
        # 显示LLM特有的评估
        llm_eval = llm_summary['breakdown']['llm_evaluation']
        print(f"  LLM评估: 认知负荷({llm_eval['cognitive_load']:.2f}), "
              f"实现难度({llm_eval['implementation_difficulty']:.2f}), "
              f"测试复杂度({llm_eval['testing_complexity']:.2f})")
        
        await model_client.close()
        
    except Exception as e:
        print(f"  ❌ LLM分析失败: {e}")
    
    print("\n📊 对比总结:")
    print("  • 基础分析器：快速、稳定，但准确性有限")
    print("  • LLM增强分析器：更准确、更智能，但需要API支持")


async def main():
    """主函数"""
    print("🎯 任务复杂度分析器演示程序")
    print("=" * 80)
    
    while True:
        print("\n请选择演示模式:")
        print("1. 交互式演示 - 输入自定义任务")
        print("2. 预设示例演示 - 查看典型案例")
        print("3. 对比演示 - 基础 vs LLM增强")
        print("4. 退出程序")
        
        try:
            choice = input("\n请输入选择 (1-4): ").strip()
            
            if choice == "1":
                await interactive_demo()
            elif choice == "2":
                await preset_demo()
            elif choice == "3":
                await comparison_demo()
            elif choice == "4":
                print("\n👋 感谢使用任务复杂度分析器！")
                break
            else:
                print("❌ 无效选择，请输入 1-4")
                
        except KeyboardInterrupt:
            print("\n\n👋 程序已退出")
            break
        except Exception as e:
            print(f"\n❌ 程序错误: {e}")


if __name__ == "__main__":
    asyncio.run(main())
