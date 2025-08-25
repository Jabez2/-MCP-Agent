"""
Memory管理工具

提供完整的记忆控制和管理功能
"""

import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

from autogen_core.memory import MemoryContent, MemoryMimeType

from .base_memory_manager import execution_log_manager, agent_state_manager
from .memory_config import memory_config


class MemoryManager:
    """Memory系统管理器"""
    
    def __init__(self):
        self.execution_log_manager = execution_log_manager
        self.agent_state_manager = agent_state_manager
        self.memory_config = memory_config
    
    async def initialize(self):
        """初始化管理器"""
        await self.execution_log_manager.initialize()
    
    # ================================
    # 查看和搜索功能
    # ================================
    
    async def list_all_memories(self, limit: int = 50) -> List[Dict[str, Any]]:
        """列出所有记忆"""
        try:
            # 使用通用查询获取所有记录
            all_records = await self.execution_log_manager.get_similar_executions("Agent", top_k=1000)  # 获取所有记录
            
            memories = []
            for i, record in enumerate(all_records[:limit]):
                memory_info = {
                    "index": i + 1,
                    "id": record.metadata.get("id", "unknown"),
                    "agent_name": record.metadata.get("agent_name", "Unknown"),
                    "success": record.metadata.get("success", False),
                    "timestamp": record.metadata.get("timestamp", "Unknown"),
                    "duration": record.metadata.get("duration", 0),
                    "task_type": record.metadata.get("task_type", "general"),
                    "content_preview": record.content[:100] + "..." if len(record.content) > 100 else record.content
                }
                memories.append(memory_info)
            
            return memories
        except Exception as e:
            print(f"❌ 获取记忆列表失败: {e}")
            return []
    
    async def search_memories(self, 
                            query: str = "",
                            agent_name: Optional[str] = None,
                            success_only: Optional[bool] = None,
                            date_from: Optional[str] = None,
                            date_to: Optional[str] = None) -> List[Dict[str, Any]]:
        """搜索记忆"""
        try:
            # 基础搜索
            records = await self.execution_log_manager.get_similar_executions(
                query=query,
                agent_name=agent_name,
                success_only=success_only if success_only is not None else False
            )
            
            # 日期过滤
            if date_from or date_to:
                filtered_records = []
                for record in records:
                    timestamp_str = record.metadata.get("timestamp", "")
                    if timestamp_str:
                        try:
                            record_date = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                            
                            if date_from:
                                from_date = datetime.fromisoformat(date_from)
                                if record_date < from_date:
                                    continue
                            
                            if date_to:
                                to_date = datetime.fromisoformat(date_to)
                                if record_date > to_date:
                                    continue
                            
                            filtered_records.append(record)
                        except:
                            continue
                records = filtered_records
            
            # 格式化结果
            results = []
            for i, record in enumerate(records):
                result = {
                    "index": i + 1,
                    "id": record.metadata.get("id", "unknown"),
                    "agent_name": record.metadata.get("agent_name", "Unknown"),
                    "success": record.metadata.get("success", False),
                    "timestamp": record.metadata.get("timestamp", "Unknown"),
                    "duration": record.metadata.get("duration", 0),
                    "score": record.metadata.get("score", 0),
                    "content": record.content,
                    "metadata": record.metadata
                }
                results.append(result)
            
            return results
        except Exception as e:
            print(f"❌ 搜索记忆失败: {e}")
            return []
    
    async def get_memory_by_id(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取特定记忆"""
        try:
            all_records = await self.execution_log_manager.get_similar_executions("Agent", top_k=1000)  # 获取所有记录
            
            for record in all_records:
                if record.metadata.get("id") == memory_id:
                    return {
                        "id": memory_id,
                        "content": record.content,
                        "metadata": record.metadata,
                        "agent_name": record.metadata.get("agent_name", "Unknown"),
                        "success": record.metadata.get("success", False),
                        "timestamp": record.metadata.get("timestamp", "Unknown"),
                        "duration": record.metadata.get("duration", 0)
                    }
            
            return None
        except Exception as e:
            print(f"❌ 获取记忆失败: {e}")
            return None
    
    # ================================
    # 统计和分析功能
    # ================================
    
    async def get_memory_statistics(self) -> Dict[str, Any]:
        """获取记忆统计信息"""
        try:
            all_records = await self.execution_log_manager.get_similar_executions("Agent", top_k=1000)  # 获取所有记录
            
            # 基础统计
            total_count = len(all_records)
            success_count = len([r for r in all_records if r.metadata.get("success", False)])
            failure_count = total_count - success_count
            
            # Agent统计
            agent_stats = {}
            task_type_stats = {}
            
            for record in all_records:
                agent_name = record.metadata.get("agent_name", "Unknown")
                task_type = record.metadata.get("task_type", "general")
                success = record.metadata.get("success", False)
                
                # Agent统计
                if agent_name not in agent_stats:
                    agent_stats[agent_name] = {"total": 0, "success": 0, "failure": 0}
                agent_stats[agent_name]["total"] += 1
                if success:
                    agent_stats[agent_name]["success"] += 1
                else:
                    agent_stats[agent_name]["failure"] += 1
                
                # 任务类型统计
                if task_type not in task_type_stats:
                    task_type_stats[task_type] = {"total": 0, "success": 0, "failure": 0}
                task_type_stats[task_type]["total"] += 1
                if success:
                    task_type_stats[task_type]["success"] += 1
                else:
                    task_type_stats[task_type]["failure"] += 1
            
            # 时间统计
            if all_records:
                timestamps = [r.metadata.get("timestamp", "") for r in all_records if r.metadata.get("timestamp")]
                if timestamps:
                    timestamps.sort()
                    earliest = timestamps[0]
                    latest = timestamps[-1]
                else:
                    earliest = latest = "Unknown"
            else:
                earliest = latest = "Unknown"
            
            return {
                "total_memories": total_count,
                "success_count": success_count,
                "failure_count": failure_count,
                "success_rate": (success_count / total_count * 100) if total_count > 0 else 0,
                "agent_statistics": agent_stats,
                "task_type_statistics": task_type_stats,
                "time_range": {
                    "earliest": earliest,
                    "latest": latest
                },
                "agent_states_count": len(self.agent_state_manager.list_saved_states())
            }
        except Exception as e:
            print(f"❌ 获取统计信息失败: {e}")
            return {}
    
    # ================================
    # 导出和备份功能
    # ================================
    
    async def export_memories(self, 
                            output_file: str,
                            format: str = "json",
                            filter_agent: Optional[str] = None,
                            filter_success: Optional[bool] = None) -> bool:
        """导出记忆到文件"""
        try:
            # 获取要导出的记忆
            if filter_agent or filter_success is not None:
                records = await self.search_memories(
                    agent_name=filter_agent,
                    success_only=filter_success
                )
            else:
                records = await self.list_all_memories(limit=10000)  # 导出所有
            
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            if format.lower() == "json":
                export_data = {
                    "export_time": datetime.now().isoformat(),
                    "total_count": len(records),
                    "filter_agent": filter_agent,
                    "filter_success": filter_success,
                    "memories": records
                }
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            elif format.lower() == "csv":
                import csv
                with open(output_path, 'w', newline='', encoding='utf-8') as f:
                    if records:
                        fieldnames = records[0].keys()
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        writer.writeheader()
                        for record in records:
                            # 处理复杂字段
                            row = record.copy()
                            for key, value in row.items():
                                if isinstance(value, (dict, list)):
                                    row[key] = json.dumps(value, ensure_ascii=False)
                            writer.writerow(row)
            
            print(f"✅ 成功导出 {len(records)} 条记忆到 {output_file}")
            return True
            
        except Exception as e:
            print(f"❌ 导出记忆失败: {e}")
            return False
    
    async def backup_all_data(self, backup_dir: str) -> bool:
        """备份所有Memory数据"""
        try:
            backup_path = Path(backup_dir)
            backup_path.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 备份执行记忆
            await self.export_memories(
                output_file=str(backup_path / f"execution_memories_{timestamp}.json"),
                format="json"
            )
            
            # 备份Agent状态
            states_backup = {}
            for agent_name in self.agent_state_manager.list_saved_states():
                state = await self.agent_state_manager.load_agent_state(agent_name)
                if state:
                    states_backup[agent_name] = state
            
            with open(backup_path / f"agent_states_{timestamp}.json", 'w', encoding='utf-8') as f:
                json.dump({
                    "backup_time": datetime.now().isoformat(),
                    "agent_states": states_backup
                }, f, indent=2, ensure_ascii=False)
            
            # 备份统计信息
            stats = await self.get_memory_statistics()
            with open(backup_path / f"memory_statistics_{timestamp}.json", 'w', encoding='utf-8') as f:
                json.dump(stats, f, indent=2, ensure_ascii=False)
            
            print(f"✅ 完整备份完成: {backup_path}")
            return True
            
        except Exception as e:
            print(f"❌ 备份失败: {e}")
            return False


# 全局实例
memory_manager = MemoryManager()
