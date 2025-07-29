"""
工作流日志管理器

提供友好的、易于理解的工作流执行日志记录功能。
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Any
from pathlib import Path


class WorkflowLogger:
    """工作流日志管理器 - 记录易于理解的执行过程"""
    
    def __init__(self, log_dir: str = "/Users/jabez/output/logs"):
        """
        初始化日志管理器
        
        Args:
            log_dir: 日志保存目录
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成唯一的日志文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"workflow_{timestamp}.md"
        self.json_file = self.log_dir / f"workflow_{timestamp}.json"
        
        # 初始化日志数据
        self.workflow_data = {
            "start_time": datetime.now().isoformat(),
            "task": "",
            "project_config": {},
            "agents": [],
            "events": [],
            "summary": {}
        }
        
        # 开始记录
        self._write_header()
    
    def log_task_start(self, task: str, project_config: Dict[str, str]):
        """记录任务开始"""
        self.workflow_data["task"] = task
        self.workflow_data["project_config"] = project_config
        
        content = f"""
## 📋 任务信息

**任务描述**: {task}

**项目配置**:
- 项目名称: {project_config.get('project_name', '未设置')}
- 主文件: {project_config.get('main_file_path', '未设置')}
- 测试文件: {project_config.get('test_file_path', '未设置')}

---

## 🚀 执行过程

"""
        self._append_to_file(content)
    
    def log_agent_start(self, agent_name: str, description: str):
        """记录Agent开始执行"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        agent_info = {
            "name": agent_name,
            "description": description,
            "start_time": datetime.now().isoformat(),
            "status": "started",
            "output": "",
            "duration": 0
        }
        self.workflow_data["agents"].append(agent_info)
        
        content = f"""
### 🎯 {timestamp} - {agent_name} 开始执行

**功能**: {description}

**状态**: 🔄 执行中...

"""
        self._append_to_file(content)
        
        # 同时在控制台显示简洁信息
        print(f"\n🎯 {timestamp} - {agent_name} 开始执行")
        print(f"   功能: {description}")
    
    def log_agent_complete(self, agent_name: str, success: bool, output: str = "", duration: float = 0):
        """记录Agent执行完成"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # 更新Agent信息
        for agent in self.workflow_data["agents"]:
            if agent["name"] == agent_name and agent["status"] == "started":
                agent["status"] = "completed" if success else "failed"
                agent["output"] = output[:200] + "..." if len(output) > 200 else output
                agent["duration"] = duration
                break
        
        status_icon = "✅" if success else "❌"
        status_text = "执行成功" if success else "执行失败"
        
        content = f"""
**状态**: {status_icon} {status_text} (耗时: {duration:.1f}秒)

"""
        if output:
            # 只显示输出的关键部分
            if "COMPLETE" in output:
                content += "**结果**: 任务完成标记已确认\n"
            elif len(output) > 100:
                content += f"**输出摘要**: {output[:100]}...\n"
            else:
                content += f"**输出**: {output}\n"
        
        content += "\n---\n"
        self._append_to_file(content)

        # 控制台显示
        print(f"   {status_icon} {status_text} (耗时: {duration:.1f}秒)")
        if not success and output:
            print(f"   ⚠️ 问题: {output[:100]}...")
        elif success and "COMPLETE" in output:
            print(f"   ✨ 完成标记已确认")
    
    def log_event(self, event_type: str, message: str):
        """记录重要事件"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        event_info = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "message": message
        }
        self.workflow_data["events"].append(event_info)
        
        # 根据事件类型选择图标
        icons = {
            "info": "ℹ️",
            "success": "✅", 
            "warning": "⚠️",
            "error": "❌",
            "progress": "🔄"
        }
        icon = icons.get(event_type, "📝")
        
        content = f"""
### {icon} {timestamp} - {message}

"""
        self._append_to_file(content)
        
        # 控制台显示
        print(f"\n{icon} {timestamp} - {message}")
    
    def log_workflow_complete(self, success: bool, summary: Dict[str, Any]):
        """记录工作流完成"""
        end_time = datetime.now()
        start_time = datetime.fromisoformat(self.workflow_data["start_time"])
        total_duration = (end_time - start_time).total_seconds()
        
        self.workflow_data["end_time"] = end_time.isoformat()
        self.workflow_data["total_duration"] = total_duration
        self.workflow_data["success"] = success
        self.workflow_data["summary"] = summary
        
        # 统计信息
        completed_agents = len([a for a in self.workflow_data["agents"] if a["status"] == "completed"])
        failed_agents = len([a for a in self.workflow_data["agents"] if a["status"] == "failed"])
        total_agents = len(self.workflow_data["agents"])
        
        status_icon = "🎉" if success else "💥"
        status_text = "工作流执行成功" if success else "工作流执行失败"
        
        content = f"""

## {status_icon} 执行总结

**状态**: {status_text}
**总耗时**: {total_duration:.1f} 秒
**Agent统计**: 
- 总数: {total_agents}
- 成功: {completed_agents}
- 失败: {failed_agents}

**生成的文件**:
"""
        
        # 添加生成的文件列表
        output_dir = Path("/Users/jabez/output")
        if output_dir.exists():
            for file_path in output_dir.glob("*.py"):
                content += f"- {file_path.name}\n"
            for file_path in output_dir.glob("*.md"):
                content += f"- {file_path.name}\n"
            for file_path in output_dir.glob("*.txt"):
                content += f"- {file_path.name}\n"
        
        content += f"""
**详细日志**: {self.log_file}
**结构化数据**: {self.json_file}

---

*日志生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*
"""
        
        self._append_to_file(content)
        
        # 保存JSON格式的结构化数据
        with open(self.json_file, 'w', encoding='utf-8') as f:
            json.dump(self.workflow_data, f, ensure_ascii=False, indent=2)
        
        # 控制台显示总结
        print(f"\n{status_icon} {status_text}")
        print(f"📊 总耗时: {total_duration:.1f} 秒")
        print(f"📁 详细日志已保存: {self.log_file}")
        print(f"📄 结构化数据: {self.json_file}")
    
    def _write_header(self):
        """写入日志文件头部"""
        header = f"""# 多Agent代码生成工作流日志

**生成时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**日志文件**: {self.log_file.name}

---
"""
        with open(self.log_file, 'w', encoding='utf-8') as f:
            f.write(header)
    
    def _append_to_file(self, content: str):
        """追加内容到日志文件"""
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(content)
    
    def get_log_file_path(self) -> str:
        """获取日志文件路径"""
        return str(self.log_file)
    
    def get_json_file_path(self) -> str:
        """获取JSON文件路径"""
        return str(self.json_file)
