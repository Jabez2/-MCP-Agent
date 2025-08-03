#!/usr/bin/env python3
"""
Memory系统命令行管理工具

使用方法:
python memory_cli.py list                    # 列出所有记忆
python memory_cli.py search "测试"            # 搜索记忆
python memory_cli.py stats                   # 显示统计信息
python memory_cli.py export memories.json    # 导出记忆
python memory_cli.py backup ./backup         # 备份所有数据
python memory_cli.py clean --days 30         # 清理30天前的记忆
"""

import asyncio
import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目根目录到路径
sys.path.append(str(Path(__file__).parent))

from src.memory import initialize_memory_system, cleanup_memory_system
from src.memory.memory_manager import memory_manager


async def cmd_list(args):
    """列出记忆"""
    print("📋 列出所有记忆...")
    
    await memory_manager.initialize()
    
    memories = await memory_manager.list_all_memories(limit=args.limit)
    
    if not memories:
        print("📭 没有找到记忆记录")
        return
    
    print(f"\n📊 找到 {len(memories)} 条记忆:")
    print("-" * 100)
    print(f"{'序号':<4} {'Agent':<20} {'成功':<6} {'时长':<8} {'时间':<20} {'内容预览':<30}")
    print("-" * 100)
    
    for memory in memories:
        success_icon = "✅" if memory["success"] else "❌"
        duration = f"{memory['duration']:.1f}s"
        timestamp = memory["timestamp"][:19] if len(memory["timestamp"]) > 19 else memory["timestamp"]
        
        print(f"{memory['index']:<4} {memory['agent_name']:<20} {success_icon:<6} {duration:<8} {timestamp:<20} {memory['content_preview']:<30}")


async def cmd_search(args):
    """搜索记忆"""
    print(f"🔍 搜索记忆: '{args.query}'")
    
    await memory_manager.initialize()
    
    # 解析日期参数
    date_from = None
    date_to = None
    
    if args.date_from:
        try:
            date_from = datetime.fromisoformat(args.date_from).isoformat()
        except:
            print(f"❌ 无效的开始日期格式: {args.date_from}")
            return
    
    if args.date_to:
        try:
            date_to = datetime.fromisoformat(args.date_to).isoformat()
        except:
            print(f"❌ 无效的结束日期格式: {args.date_to}")
            return
    
    results = await memory_manager.search_memories(
        query=args.query,
        agent_name=args.agent,
        success_only=args.success_only,
        date_from=date_from,
        date_to=date_to
    )
    
    if not results:
        print("📭 没有找到匹配的记忆")
        return
    
    print(f"\n📊 找到 {len(results)} 条匹配记忆:")
    print("-" * 120)
    print(f"{'序号':<4} {'Agent':<20} {'成功':<6} {'时长':<8} {'相似度':<8} {'时间':<20} {'内容预览':<40}")
    print("-" * 120)
    
    for result in results[:args.limit]:
        success_icon = "✅" if result["success"] else "❌"
        duration = f"{result['duration']:.1f}s"
        score = f"{result['score']:.3f}" if result['score'] else "N/A"
        timestamp = result["timestamp"][:19] if len(result["timestamp"]) > 19 else result["timestamp"]
        content_preview = result["content"][:40] + "..." if len(result["content"]) > 40 else result["content"]
        
        print(f"{result['index']:<4} {result['agent_name']:<20} {success_icon:<6} {duration:<8} {score:<8} {timestamp:<20} {content_preview:<40}")


async def cmd_stats(args):
    """显示统计信息"""
    print("📊 Memory系统统计信息...")
    
    await memory_manager.initialize()
    
    stats = await memory_manager.get_memory_statistics()
    
    if not stats:
        print("❌ 无法获取统计信息")
        return
    
    print("\n" + "="*60)
    print("📈 总体统计")
    print("="*60)
    print(f"总记忆数量: {stats['total_memories']}")
    print(f"成功执行: {stats['success_count']}")
    print(f"失败执行: {stats['failure_count']}")
    print(f"成功率: {stats['success_rate']:.1f}%")
    print(f"Agent状态数: {stats['agent_states_count']}")
    
    print(f"\n时间范围:")
    print(f"  最早记录: {stats['time_range']['earliest']}")
    print(f"  最新记录: {stats['time_range']['latest']}")
    
    print("\n" + "="*60)
    print("🤖 Agent统计")
    print("="*60)
    for agent, agent_stats in stats['agent_statistics'].items():
        success_rate = (agent_stats['success'] / agent_stats['total'] * 100) if agent_stats['total'] > 0 else 0
        print(f"{agent:<20} 总计:{agent_stats['total']:<3} 成功:{agent_stats['success']:<3} 失败:{agent_stats['failure']:<3} 成功率:{success_rate:.1f}%")
    
    print("\n" + "="*60)
    print("📋 任务类型统计")
    print("="*60)
    for task_type, type_stats in stats['task_type_statistics'].items():
        success_rate = (type_stats['success'] / type_stats['total'] * 100) if type_stats['total'] > 0 else 0
        print(f"{task_type:<15} 总计:{type_stats['total']:<3} 成功:{type_stats['success']:<3} 失败:{type_stats['failure']:<3} 成功率:{success_rate:.1f}%")


async def cmd_export(args):
    """导出记忆"""
    print(f"📤 导出记忆到: {args.output_file}")
    
    await memory_manager.initialize()
    
    success = await memory_manager.export_memories(
        output_file=args.output_file,
        format=args.format,
        filter_agent=args.agent,
        filter_success=args.success_only
    )
    
    if success:
        print("✅ 导出完成")
    else:
        print("❌ 导出失败")


async def cmd_backup(args):
    """备份所有数据"""
    print(f"💾 备份所有Memory数据到: {args.backup_dir}")
    
    await memory_manager.initialize()
    
    success = await memory_manager.backup_all_data(args.backup_dir)
    
    if success:
        print("✅ 备份完成")
    else:
        print("❌ 备份失败")


async def cmd_clean(args):
    """清理旧记忆"""
    print(f"🧹 清理 {args.days} 天前的记忆...")
    
    await memory_manager.initialize()
    
    # 计算截止日期
    cutoff_date = datetime.now() - timedelta(days=args.days)
    cutoff_str = cutoff_date.isoformat()
    
    # 搜索要删除的记忆
    old_memories = await memory_manager.search_memories(
        date_to=cutoff_str
    )
    
    if not old_memories:
        print("📭 没有找到需要清理的旧记忆")
        return
    
    print(f"⚠️  找到 {len(old_memories)} 条旧记忆")
    
    if not args.force:
        confirm = input("确认删除这些记忆吗? (y/N): ")
        if confirm.lower() != 'y':
            print("❌ 取消清理操作")
            return
    
    # 注意：ChromaDB不支持直接删除，这里只是演示
    # 实际实现需要重建数据库或使用其他方法
    print("⚠️  注意：当前版本不支持直接删除记忆")
    print("💡 建议：使用备份功能保存需要的记忆，然后重新初始化数据库")


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Memory系统管理工具")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # list命令
    list_parser = subparsers.add_parser("list", help="列出记忆")
    list_parser.add_argument("--limit", type=int, default=50, help="显示数量限制")
    
    # search命令
    search_parser = subparsers.add_parser("search", help="搜索记忆")
    search_parser.add_argument("query", help="搜索查询")
    search_parser.add_argument("--agent", help="过滤Agent")
    search_parser.add_argument("--success-only", action="store_true", help="只显示成功的记忆")
    search_parser.add_argument("--date-from", help="开始日期 (YYYY-MM-DD)")
    search_parser.add_argument("--date-to", help="结束日期 (YYYY-MM-DD)")
    search_parser.add_argument("--limit", type=int, default=20, help="显示数量限制")
    
    # stats命令
    stats_parser = subparsers.add_parser("stats", help="显示统计信息")
    
    # export命令
    export_parser = subparsers.add_parser("export", help="导出记忆")
    export_parser.add_argument("output_file", help="输出文件路径")
    export_parser.add_argument("--format", choices=["json", "csv"], default="json", help="导出格式")
    export_parser.add_argument("--agent", help="过滤Agent")
    export_parser.add_argument("--success-only", action="store_true", help="只导出成功的记忆")
    
    # backup命令
    backup_parser = subparsers.add_parser("backup", help="备份所有数据")
    backup_parser.add_argument("backup_dir", help="备份目录")
    
    # clean命令
    clean_parser = subparsers.add_parser("clean", help="清理旧记忆")
    clean_parser.add_argument("--days", type=int, default=30, help="清理多少天前的记忆")
    clean_parser.add_argument("--force", action="store_true", help="强制删除，不询问确认")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        # 初始化Memory系统
        await initialize_memory_system()
        
        # 执行命令
        if args.command == "list":
            await cmd_list(args)
        elif args.command == "search":
            await cmd_search(args)
        elif args.command == "stats":
            await cmd_stats(args)
        elif args.command == "export":
            await cmd_export(args)
        elif args.command == "backup":
            await cmd_backup(args)
        elif args.command == "clean":
            await cmd_clean(args)
        
    except Exception as e:
        print(f"❌ 执行命令时出错: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 清理资源
        await cleanup_memory_system()


if __name__ == "__main__":
    asyncio.run(main())
