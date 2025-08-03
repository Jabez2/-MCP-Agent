# 🧠 Memory系统管理指南

本指南将教您如何控制和管理已存储的记忆。

## 📋 目录

1. [命令行工具](#命令行工具)
2. [Web管理界面](#web管理界面)
3. [编程接口](#编程接口)
4. [常用操作](#常用操作)
5. [数据备份与恢复](#数据备份与恢复)

## 🖥️ 命令行工具

### 安装依赖
```bash
pip install aiohttp aiohttp-cors
```

### 基本命令

#### 1. 列出所有记忆
```bash
python memory_cli.py list
python memory_cli.py list --limit 100  # 显示更多记录
```

#### 2. 搜索记忆
```bash
# 基础搜索
python memory_cli.py search "测试"
python memory_cli.py search "UnitTestAgent"

# 高级搜索
python memory_cli.py search "错误" --agent UnitTestAgent
python memory_cli.py search "成功" --success-only
python memory_cli.py search "代码生成" --date-from 2025-08-01 --date-to 2025-08-02
```

#### 3. 查看统计信息
```bash
python memory_cli.py stats
```

#### 4. 导出记忆
```bash
# 导出为JSON
python memory_cli.py export memories.json

# 导出为CSV
python memory_cli.py export memories.csv --format csv

# 过滤导出
python memory_cli.py export unit_test_memories.json --agent UnitTestAgent
python memory_cli.py export success_memories.json --success-only
```

#### 5. 备份所有数据
```bash
python memory_cli.py backup ./backup_folder
```

#### 6. 清理旧记忆
```bash
# 清理30天前的记忆（需要确认）
python memory_cli.py clean --days 30

# 强制清理（不询问确认）
python memory_cli.py clean --days 30 --force
```

## 🌐 Web管理界面

### 启动Web界面
```bash
python memory_web.py
```

然后访问: http://localhost:8080

### Web界面功能
- 📊 **实时统计**: 查看记忆总数、成功率、Agent统计等
- 🔍 **智能搜索**: 通过关键词和Agent过滤搜索记忆
- 📋 **记忆浏览**: 可视化浏览所有记忆记录
- 📤 **一键导出**: 直接在网页上导出记忆数据
- 💾 **数据备份**: 在线备份所有Memory数据

## 💻 编程接口

### 基本使用
```python
import asyncio
from src.memory import initialize_memory_system, cleanup_memory_system
from src.memory.memory_manager import memory_manager

async def manage_memories():
    # 初始化
    await initialize_memory_system()
    await memory_manager.initialize()
    
    try:
        # 列出所有记忆
        memories = await memory_manager.list_all_memories(limit=50)
        print(f"找到 {len(memories)} 条记忆")
        
        # 搜索记忆
        results = await memory_manager.search_memories(
            query="测试失败",
            agent_name="UnitTestAgent"
        )
        
        # 获取统计信息
        stats = await memory_manager.get_memory_statistics()
        print(f"总成功率: {stats['success_rate']:.1f}%")
        
        # 导出记忆
        await memory_manager.export_memories(
            output_file="my_memories.json",
            format="json",
            filter_agent="UnitTestAgent"
        )
        
        # 备份数据
        await memory_manager.backup_all_data("./my_backup")
        
    finally:
        await cleanup_memory_system()

# 运行
asyncio.run(manage_memories())
```

### 高级查询
```python
# 按日期范围搜索
from datetime import datetime, timedelta

yesterday = (datetime.now() - timedelta(days=1)).isoformat()
results = await memory_manager.search_memories(
    query="代码生成",
    date_from=yesterday,
    success_only=True
)

# 获取特定记忆详情
memory_id = "some-memory-id"
memory_detail = await memory_manager.get_memory_by_id(memory_id)
if memory_detail:
    print(f"记忆内容: {memory_detail['content']}")
```

## 🔧 常用操作

### 1. 查找错误解决方案
```bash
# 命令行
python memory_cli.py search "AssertionError" --success-only

# 编程方式
solutions = await execution_log_manager.get_error_solutions("AssertionError")
```

### 2. 分析Agent性能
```bash
# 查看特定Agent的所有记录
python memory_cli.py search "" --agent UnitTestAgent

# 查看统计信息
python memory_cli.py stats
```

### 3. 导出特定时期的记忆
```bash
python memory_cli.py search "" --date-from 2025-08-01 --date-to 2025-08-02 > recent_memories.txt
```

### 4. 监控系统健康状况
```python
async def check_system_health():
    stats = await memory_manager.get_memory_statistics()
    
    # 检查成功率
    if stats['success_rate'] < 70:
        print("⚠️ 系统成功率较低，需要关注")
    
    # 检查Agent性能
    for agent, agent_stats in stats['agent_statistics'].items():
        agent_success_rate = (agent_stats['success'] / agent_stats['total'] * 100)
        if agent_success_rate < 50:
            print(f"⚠️ {agent} 成功率过低: {agent_success_rate:.1f}%")
```

## 💾 数据备份与恢复

### 自动备份
```python
import schedule
import time

async def daily_backup():
    await memory_manager.backup_all_data(f"./backups/{datetime.now().strftime('%Y%m%d')}")

# 每天凌晨2点备份
schedule.every().day.at("02:00").do(lambda: asyncio.run(daily_backup()))

while True:
    schedule.run_pending()
    time.sleep(60)
```

### 数据迁移
```bash
# 1. 备份当前数据
python memory_cli.py backup ./migration_backup

# 2. 导出为JSON格式
python memory_cli.py export all_memories.json

# 3. 在新环境中导入（需要自定义导入脚本）
```

### 清理策略
```python
async def cleanup_old_memories():
    """清理策略：保留最近30天的记忆，但保留所有成功的重要记忆"""
    
    # 导出重要的成功记忆
    await memory_manager.export_memories(
        output_file="important_success_memories.json",
        filter_success=True
    )
    
    # 清理30天前的记忆
    # 注意：实际清理需要重建数据库
    print("建议手动清理ChromaDB数据库文件")
```

## 📊 监控和分析

### 性能监控脚本
```python
async def generate_performance_report():
    stats = await memory_manager.get_memory_statistics()
    
    report = f"""
# Memory系统性能报告
生成时间: {datetime.now().isoformat()}

## 总体统计
- 总记忆数: {stats['total_memories']}
- 成功率: {stats['success_rate']:.1f}%
- Agent数量: {len(stats['agent_statistics'])}

## Agent性能排行
"""
    
    # Agent性能排序
    agent_performance = []
    for agent, agent_stats in stats['agent_statistics'].items():
        success_rate = (agent_stats['success'] / agent_stats['total'] * 100)
        agent_performance.append((agent, success_rate, agent_stats['total']))
    
    agent_performance.sort(key=lambda x: x[1], reverse=True)
    
    for agent, success_rate, total in agent_performance:
        report += f"- {agent}: {success_rate:.1f}% ({total} 次执行)\n"
    
    # 保存报告
    with open(f"performance_report_{datetime.now().strftime('%Y%m%d')}.md", 'w') as f:
        f.write(report)
    
    print("📊 性能报告已生成")
```

## 🚨 注意事项

1. **数据安全**: 定期备份重要的记忆数据
2. **存储空间**: 监控Memory数据库的大小，及时清理
3. **性能优化**: 大量记忆可能影响查询性能
4. **版本兼容**: 升级系统前先备份数据

## 🆘 故障排除

### 常见问题

1. **无法连接到Memory系统**
   ```bash
   # 检查数据库文件是否存在
   ls -la ./memory/
   
   # 重新初始化
   python -c "import asyncio; from src.memory import initialize_memory_system; asyncio.run(initialize_memory_system())"
   ```

2. **搜索结果为空**
   - 检查查询关键词是否正确
   - 尝试降低相似度阈值
   - 使用更通用的查询词

3. **导出失败**
   - 检查输出目录权限
   - 确保有足够的磁盘空间

通过这些工具和方法，您可以完全控制Memory系统中存储的所有记忆！🎯
