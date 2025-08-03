#!/usr/bin/env python3
"""
Memory系统Web管理界面

启动方法:
python memory_web.py

然后访问: http://localhost:8080
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
import sys

# 添加项目根目录到路径
sys.path.append(str(Path(__file__).parent))

from aiohttp import web, web_request
from aiohttp.web_response import Response
import aiohttp_cors

from src.memory import initialize_memory_system, cleanup_memory_system
from src.memory.memory_manager import memory_manager


class MemoryWebServer:
    """Memory Web管理服务器"""
    
    def __init__(self):
        self.app = web.Application()
        self.setup_routes()
        self.setup_cors()
    
    def setup_cors(self):
        """设置CORS"""
        cors = aiohttp_cors.setup(self.app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
                allow_methods="*"
            )
        })
        
        # 为所有路由添加CORS
        for route in list(self.app.router.routes()):
            cors.add(route)
    
    def setup_routes(self):
        """设置路由"""
        # 静态文件
        self.app.router.add_get('/', self.index)
        
        # API路由
        self.app.router.add_get('/api/memories', self.api_list_memories)
        self.app.router.add_get('/api/search', self.api_search_memories)
        self.app.router.add_get('/api/stats', self.api_get_stats)
        self.app.router.add_get('/api/memory/{memory_id}', self.api_get_memory)
        self.app.router.add_post('/api/export', self.api_export_memories)
        self.app.router.add_post('/api/backup', self.api_backup_data)
    
    async def index(self, request):
        """主页"""
        html = """
<!DOCTYPE html>
<html>
<head>
    <title>Memory系统管理</title>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background: #f0f0f0; padding: 20px; border-radius: 5px; margin-bottom: 20px; }
        .section { margin-bottom: 30px; }
        .memory-item { border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 5px; }
        .success { background-color: #d4edda; }
        .failure { background-color: #f8d7da; }
        .btn { padding: 10px 20px; margin: 5px; border: none; border-radius: 3px; cursor: pointer; }
        .btn-primary { background: #007bff; color: white; }
        .btn-success { background: #28a745; color: white; }
        .btn-warning { background: #ffc107; color: black; }
        .search-box { width: 300px; padding: 8px; margin: 10px; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; }
        .stat-card { background: #f8f9fa; padding: 20px; border-radius: 5px; border-left: 4px solid #007bff; }
        .loading { text-align: center; padding: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧠 Memory系统管理</h1>
            <p>管理和控制您的Agent执行记忆</p>
        </div>
        
        <div class="section">
            <h2>📊 系统统计</h2>
            <div id="stats" class="stats-grid">
                <div class="loading">加载统计信息中...</div>
            </div>
        </div>
        
        <div class="section">
            <h2>🔍 搜索记忆</h2>
            <div>
                <input type="text" id="searchQuery" class="search-box" placeholder="输入搜索关键词...">
                <select id="agentFilter" class="search-box">
                    <option value="">所有Agent</option>
                </select>
                <button class="btn btn-primary" onclick="searchMemories()">搜索</button>
                <button class="btn btn-success" onclick="loadAllMemories()">显示全部</button>
            </div>
        </div>
        
        <div class="section">
            <h2>📋 记忆列表</h2>
            <div>
                <button class="btn btn-warning" onclick="exportMemories()">导出记忆</button>
                <button class="btn btn-warning" onclick="backupData()">备份数据</button>
            </div>
            <div id="memories">
                <div class="loading">加载记忆中...</div>
            </div>
        </div>
    </div>

    <script>
        // 加载统计信息
        async function loadStats() {
            try {
                const response = await fetch('/api/stats');
                const stats = await response.json();
                
                const statsHtml = `
                    <div class="stat-card">
                        <h3>总体统计</h3>
                        <p>总记忆: ${stats.total_memories}</p>
                        <p>成功: ${stats.success_count}</p>
                        <p>失败: ${stats.failure_count}</p>
                        <p>成功率: ${stats.success_rate.toFixed(1)}%</p>
                    </div>
                    <div class="stat-card">
                        <h3>Agent数量</h3>
                        <p>活跃Agent: ${Object.keys(stats.agent_statistics).length}</p>
                        <p>保存状态: ${stats.agent_states_count}</p>
                    </div>
                    <div class="stat-card">
                        <h3>时间范围</h3>
                        <p>最早: ${stats.time_range.earliest.substring(0, 19)}</p>
                        <p>最新: ${stats.time_range.latest.substring(0, 19)}</p>
                    </div>
                `;
                
                document.getElementById('stats').innerHTML = statsHtml;
                
                // 填充Agent过滤器
                const agentFilter = document.getElementById('agentFilter');
                Object.keys(stats.agent_statistics).forEach(agent => {
                    const option = document.createElement('option');
                    option.value = agent;
                    option.textContent = agent;
                    agentFilter.appendChild(option);
                });
                
            } catch (error) {
                document.getElementById('stats').innerHTML = '<div class="loading">加载统计信息失败</div>';
            }
        }
        
        // 加载所有记忆
        async function loadAllMemories() {
            try {
                const response = await fetch('/api/memories?limit=100');
                const memories = await response.json();
                displayMemories(memories);
            } catch (error) {
                document.getElementById('memories').innerHTML = '<div class="loading">加载记忆失败</div>';
            }
        }
        
        // 搜索记忆
        async function searchMemories() {
            const query = document.getElementById('searchQuery').value;
            const agent = document.getElementById('agentFilter').value;
            
            try {
                let url = '/api/search?';
                if (query) url += `query=${encodeURIComponent(query)}&`;
                if (agent) url += `agent=${encodeURIComponent(agent)}&`;
                url += 'limit=50';
                
                const response = await fetch(url);
                const memories = await response.json();
                displayMemories(memories);
            } catch (error) {
                document.getElementById('memories').innerHTML = '<div class="loading">搜索失败</div>';
            }
        }
        
        // 显示记忆列表
        function displayMemories(memories) {
            if (memories.length === 0) {
                document.getElementById('memories').innerHTML = '<div class="loading">没有找到记忆</div>';
                return;
            }
            
            const memoriesHtml = memories.map(memory => `
                <div class="memory-item ${memory.success ? 'success' : 'failure'}">
                    <h4>${memory.agent_name} ${memory.success ? '✅' : '❌'}</h4>
                    <p><strong>时间:</strong> ${memory.timestamp.substring(0, 19)}</p>
                    <p><strong>耗时:</strong> ${memory.duration}秒</p>
                    <p><strong>内容:</strong> ${memory.content_preview || memory.content.substring(0, 200) + '...'}</p>
                    ${memory.score ? `<p><strong>相似度:</strong> ${memory.score.toFixed(3)}</p>` : ''}
                </div>
            `).join('');
            
            document.getElementById('memories').innerHTML = memoriesHtml;
        }
        
        // 导出记忆
        async function exportMemories() {
            try {
                const response = await fetch('/api/export', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ format: 'json' })
                });
                
                if (response.ok) {
                    alert('导出成功！文件已保存到服务器。');
                } else {
                    alert('导出失败！');
                }
            } catch (error) {
                alert('导出失败：' + error.message);
            }
        }
        
        // 备份数据
        async function backupData() {
            try {
                const response = await fetch('/api/backup', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ backup_dir: './web_backup' })
                });
                
                if (response.ok) {
                    alert('备份成功！');
                } else {
                    alert('备份失败！');
                }
            } catch (error) {
                alert('备份失败：' + error.message);
            }
        }
        
        // 页面加载时初始化
        window.onload = function() {
            loadStats();
            loadAllMemories();
        };
    </script>
</body>
</html>
        """
        return web.Response(text=html, content_type='text/html')
    
    async def api_list_memories(self, request):
        """API: 列出记忆"""
        try:
            limit = int(request.query.get('limit', 50))
            memories = await memory_manager.list_all_memories(limit=limit)
            return web.json_response(memories)
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def api_search_memories(self, request):
        """API: 搜索记忆"""
        try:
            query = request.query.get('query', '')
            agent = request.query.get('agent', None)
            limit = int(request.query.get('limit', 20))
            
            memories = await memory_manager.search_memories(
                query=query,
                agent_name=agent if agent else None
            )
            
            return web.json_response(memories[:limit])
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def api_get_stats(self, request):
        """API: 获取统计信息"""
        try:
            stats = await memory_manager.get_memory_statistics()
            return web.json_response(stats)
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def api_get_memory(self, request):
        """API: 获取特定记忆"""
        try:
            memory_id = request.match_info['memory_id']
            memory = await memory_manager.get_memory_by_id(memory_id)
            
            if memory:
                return web.json_response(memory)
            else:
                return web.json_response({'error': 'Memory not found'}, status=404)
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def api_export_memories(self, request):
        """API: 导出记忆"""
        try:
            data = await request.json()
            format = data.get('format', 'json')
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"./exports/memories_export_{timestamp}.{format}"
            
            success = await memory_manager.export_memories(
                output_file=output_file,
                format=format
            )
            
            if success:
                return web.json_response({'success': True, 'file': output_file})
            else:
                return web.json_response({'error': 'Export failed'}, status=500)
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def api_backup_data(self, request):
        """API: 备份数据"""
        try:
            data = await request.json()
            backup_dir = data.get('backup_dir', './web_backup')
            
            success = await memory_manager.backup_all_data(backup_dir)
            
            if success:
                return web.json_response({'success': True, 'backup_dir': backup_dir})
            else:
                return web.json_response({'error': 'Backup failed'}, status=500)
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)


async def init_app():
    """初始化应用"""
    await initialize_memory_system()
    await memory_manager.initialize()
    
    server = MemoryWebServer()
    return server.app


async def cleanup_app(app):
    """清理应用"""
    await cleanup_memory_system()


def main():
    """主函数"""
    print("🌐 启动Memory Web管理界面...")
    print("📍 访问地址: http://localhost:8080")
    
    # 创建事件循环
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # 初始化应用
        app = loop.run_until_complete(init_app())
        
        # 启动服务器
        web.run_app(app, host='localhost', port=8080)
        
    except KeyboardInterrupt:
        print("\n👋 服务器已停止")
    finally:
        # 清理资源
        loop.run_until_complete(cleanup_app(None))
        loop.close()


if __name__ == "__main__":
    main()
