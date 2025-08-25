# 基于MCP的多链代码生成Agent

## 项目简介

这是一个基于MCP（Model Context Protocol）的智能代码生成系统，通过多个Agent协作完成从需求分析到代码生成、测试、重构的完整开发流程。

## 参考资料
- [MCP官方文档](https://github.com/modelcontextprotocol)
- [AutoGen官方文档](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/quickstart.html)
- [MagenticOne官方文档](https://microsoft.github.io/autogen/stable/reference/python/autogen_agentchat.teams.html#autogen_agentchat.teams.MagenticOneGroupChate)
- [ChromaDB官方文档](https://microsoft.github.io/autogen/stable/reference/python/autogen_ext.memory.chromadb.html)
- [Sentence Transformers官方文档](https://github.com/UKPLab/sentence-transformers)
.....
]
### 配置说明
- **模型配置**: 编辑 `src/config/model_config.py` 设置LLM API
- **MCP服务**: 编辑 `src/config/mcp_config.py` 配置服务路径

## 系统架构

### 组件
- **GraphFlowOrchestrator** - 核心编排器，结合GraphFlow和MagenticOne风格
- **TaskLedger & ProgressLedger** - 双账本系统，管理任务状态和执行进度
- **7个执行Agent** - 分工协作完成代码开发全流程
- **MCP服务集成** - 文件系统、代码执行、质量扫描等工具服务

### 执行流程
1. **任务分析** - 解析用户需求，制定执行计划
2. **进度分析** - 基于进度账本分析执行情况，为 Agent 提供指令
3. **Agent协作** - 多Agent按序执行，实时状态同步
4. **质量保证** - 自动测试、重构、代码扫描
5. **结果交付** - 生成完整项目结构和文档

## 技术特点

### MagenticOne双账本
- **双账本系统** - TaskLedger管理任务状态，ProgressLedger跟踪执行进度
- **任务分析、进度分析** - 分析任务执行情况，Agent 执行情况
- **错误恢复机制** - 自动重试、重新规划

### 多链路支持
- **原型链路** (2个Agent) - 快速验证想法
- **最小链路** (4个Agent) - 基础开发流程
- **质量链路** (6个Agent) - 包含重构和扫描
- **标准链路** (7个Agent) - 完整开发流程
### GraphFlow
- 预定义有向图

### 向量化记忆
- **执行日志记忆** - 基于ChromaDB存储Agent执行历史
- **Agent状态记忆** - 跟踪Agent间的协作关系

## 技术栈

- **框架**: AutoGen AgentChat + MCP协议
- **语言**: Python 3.13+ / Node.js 16+
- **AI模型**: 支持OpenAI兼容API
- **存储**: ChromaDB向量数据库
- **工具**: 静态代码分析、自动化测试

