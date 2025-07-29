# 基于MCP的多链代码生成Agent开发项目

## 项目简介

这是一个基于MCP（Model Context Protocol）的多链代码生成Agent开发项目。该项目实现了一个完整的多Agent协作系统，用于代码生成、测试、验证、反思、重构、质量扫描和项目结构化。

## 核心特性

### 🤖 八个专业Agent协作
- **代码规划Agent** - 分析需求并制定实现计划
- **函数编写Agent** - 编写具体的Python函数代码
- **测试用例生成Agent** - 生成完整的测试用例
- **单元测试执行Agent** - 执行测试并生成报告
- **反思规划Agent** - 分析开发流程并提供建议
- **代码重构Agent** - 根据建议进行代码重构和优化
- **代码扫描Agent** - 进行静态代码分析和质量扫描
- **项目结构Agent** - 创建完整的项目目录结构

### 🔗 多链智能调度
- 结合GraphFlow的结构化执行和MagenticOne的智能调度
- 支持动态路径选择和错误恢复
- 智能节点选择和状态管理

### 🛠️ MCP集成
- 文件系统操作能力
- 代码执行和测试能力
- 智能路径解析和项目结构发现

## 项目结构

```
mcp_multichain_agent/
├── src/
│   ├── __init__.py
│   ├── core/                    # 核心模块
│   │   ├── __init__.py
│   │   ├── data_structures.py   # 数据结构定义
│   │   ├── orchestrator.py      # 核心编排器
│   │   ├── orchestrator_helpers.py  # 编排器辅助方法
│   │   └── path_resolver.py     # 智能路径解析器
│   ├── agents/                  # Agent模块
│   │   ├── __init__.py
│   │   ├── planning_agent.py    # 代码规划Agent
│   │   ├── coding_agent.py      # 函数编写Agent
│   │   ├── test_agent.py        # 测试用例生成Agent
│   │   ├── unit_test_agent.py   # 单元测试执行Agent
│   │   ├── reflection_agent.py  # 反思规划Agent
│   │   ├── refactoring_agent.py # 代码重构Agent
│   │   ├── scanning_agent.py    # 代码扫描Agent
│   │   └── structure_agent.py   # 项目结构Agent
│   ├── config/                  # 配置模块
│   │   ├── __init__.py
│   │   ├── mcp_config.py        # MCP服务器配置
│   │   └── model_config.py      # LLM模型配置
│   ├── utils/                   # 工具模块
│   │   ├── __init__.py
│   │   └── file_naming.py       # 动态文件命名系统
│   └── main.py                  # 主入口文件
├── tests/                       # 测试目录
├── docs/                        # 文档目录
├── requirements.txt             # 项目依赖
├── setup.py                     # 安装配置
├── README.md                    # 项目说明
└── .gitignore                   # Git忽略文件
```

## 安装和使用

### 环境要求
- Python 3.8+
- Node.js (用于MCP服务器)

### 安装步骤

1. 克隆项目
```bash
git clone https://github.com/mcpmultichain/mcp-multichain-agent.git
cd mcp-multichain-agent
```

2. 安装Python依赖
```bash
pip install -r requirements.txt
```

3. 安装项目
```bash
pip install -e .
```

### 运行示例

1. 使用默认任务运行
```bash
python src/main.py
```

2. 使用自定义任务运行
```bash
python src/main.py "创建一个数学计算库，包含加减乘除和高级数学函数"
```

## 配置说明

### MCP服务器配置
在 `src/config/mcp_config.py` 中配置MCP服务器路径：
```python
filesystem_mcp_server = StdioServerParams(
    command="node",
    args=[
        "/path/to/filesystem-mcp-server/dist/index.js",
        "/Users"
    ]
)
```

### LLM模型配置
在 `src/config/model_config.py` 中配置LLM模型：
```python
return OpenAIChatCompletionClient(
    model="your-model-name",
    api_key="your-api-key",
    base_url="your-base-url"
)
```

## 核心概念

### 任务账本 (TaskLedger)
管理全局任务状态和计划，包括：
- 原始任务描述
- 已确认的事实
- 执行计划
- Agent能力映射
- 项目配置信息

### 进度账本 (ProgressLedger)
管理执行进度和状态跟踪，包括：
- 节点执行状态
- 执行历史记录
- 重试计数
- 停滞检测

### 智能编排器 (GraphFlowOrchestrator)
核心编排器，负责：
- 任务分解和计划制定
- 智能节点选择
- 执行监控和错误处理
- 动态路径调整

## 开发指南

### 添加新的Agent
1. 在 `src/agents/` 目录下创建新的Agent文件
2. 实现Agent创建函数
3. 在 `src/agents/__init__.py` 中导入并添加到 `create_all_agents` 函数

### 扩展功能
- 修改 `src/core/orchestrator.py` 中的节点流程
- 添加新的数据结构到 `src/core/data_structures.py`
- 扩展工具函数到 `src/utils/` 目录

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request来改进这个项目。

## 联系方式

- 项目主页: https://github.com/mcpmultichain/mcp-multichain-agent
- 问题反馈: https://github.com/mcpmultichain/mcp-multichain-agent/issues
