# 基于MCP的多链代码生成Agent开发项目

## 项目简介

这是一个基于MCP（Model Context Protocol）的多链代码生成Agent开发项目。该项目实现了一个完整的多Agent协作系统，用于代码生成、测试、验证、重构、质量扫描和项目结构化。项目采用AutoGen框架构建，集成了多个专业MCP服务，支持智能路径选择和动态调度。

## 核心特性

### 🤖 七个专业Agent协作
- **代码规划Agent (CodePlanningAgent)** - 分析需求并制定实现计划
- **函数编写Agent (FunctionWritingAgent)** - 编写具体的Python函数代码
- **测试用例生成Agent (TestGenerationAgent)** - 生成完整的测试用例
- **单元测试执行Agent (UnitTestAgent)** - 执行测试并生成报告
- **代码重构Agent (RefactoringAgent)** - 根据建议进行代码重构和优化
- **代码扫描Agent (CodeScanningAgent)** - 进行静态代码分析和质量扫描
- **项目结构Agent (ProjectStructureAgent)** - 创建完整的项目目录结构

### 🔗 多链智能调度
- 结合GraphFlow的结构化执行和MagenticOne的智能调度
- 支持动态路径选择和错误恢复
- 智能节点选择和状态管理
- 基于进度账本的执行监控

### 🛠️ MCP服务集成
- **文件系统MCP** - 提供完整的文件操作能力和智能路径解析
- **代码运行MCP** - 支持代码执行和测试运行
- **代码扫描MCP** - 提供静态代码分析和质量检测
- **网络请求MCP** - 支持外部API调用和数据获取

### 🧠 智能内存管理
- **工作流内存** - 记录执行历史和模式
- **Agent状态内存** - 跟踪各Agent的执行状态
- **单元测试内存** - 专门的测试结果管理
- **内存导出和分析** - 支持内存数据的导出和可视化

## 项目结构

```
multiAgent/
├── src/                         # 源代码目录
│   ├── __init__.py             # 包初始化文件
│   ├── main.py                 # 主入口文件
│   ├── core/                   # 核心模块
│   │   ├── __init__.py         # 核心模块初始化
│   │   ├── data_structures.py  # 数据结构定义
│   │   ├── orchestrator.py     # 核心编排器
│   │   ├── orchestrator_helpers.py # 编排器辅助方法
│   │   └── path_resolver.py    # 智能路径解析器
│   ├── agents/                 # Agent模块
│   │   ├── __init__.py         # Agent模块初始化
│   │   ├── planning_agent.py   # 代码规划Agent
│   │   ├── coding_agent.py     # 函数编写Agent
│   │   ├── test_agent.py       # 测试用例生成Agent
│   │   ├── unit_test_agent.py  # 单元测试执行Agent
│   │   ├── refactoring_agent.py # 代码重构Agent
│   │   ├── scanning_agent.py   # 代码扫描Agent
│   │   └── structure_agent.py  # 项目结构Agent
│   ├── config/                 # 配置模块
│   │   ├── __init__.py         # 配置模块初始化
│   │   ├── mcp_config.py       # MCP服务器配置
│   │   └── model_config.py     # LLM模型配置
│   ├── memory/                 # 内存管理模块
│   │   ├── __init__.py         # 内存模块初始化
│   │   ├── workflow_memory_manager.py # 工作流内存管理
│   │   ├── agent_state_memory_manager.py # Agent状态内存管理
│   │   └── unit_test_memory_manager.py # 单元测试内存管理
│   ├── tools/                  # 工具模块
│   │   ├── __init__.py         # 工具模块初始化
│   │   └── file_naming.py      # 动态文件命名系统
│   ├── utils/                  # 工具模块
│   │   ├── __init__.py         # 工具模块初始化
│   │   └── file_naming.py      # 文件命名工具
│   └── workbenches/            # 工作台模块
│       ├── __init__.py         # 工作台模块初始化
│       └── mcp_workbench.py    # MCP工作台实现
├── mcp_services/               # MCP服务目录
│   ├── filesystem-mcp-server/  # 文件系统MCP服务
│   ├── code_scanner_mcp/       # 代码扫描MCP服务
│   └── fetch-mcp/              # 网络请求MCP服务
├── memory/                     # 内存存储目录
│   ├── agent_states/           # Agent状态存储
│   ├── execution_logs/         # 执行日志存储
│   └── workflow_patterns/      # 工作流模式存储
├── tests/                      # 测试目录
│   ├── test_agents/            # Agent测试
│   ├── test_core/              # 核心模块测试
│   └── test_utils/             # 工具模块测试
├── docs/                       # 文档目录
│   ├── user-guide/             # 用户指南
│   ├── api/                    # API文档
│   └── examples/               # 示例代码
├── exports/                    # 导出文件目录
├── scripts/                    # 脚本目录
├── requirements.txt            # 项目依赖
├── pyproject.toml              # 项目配置
├── setup.py                    # 安装配置
├── README.md                   # 项目说明
└── .gitignore                  # Git忽略文件
```

## 安装和使用

### 环境要求
- Python 3.8+
- Node.js 16+ (用于MCP服务器)
- npm 或 yarn (用于安装MCP服务依赖)

### 安装步骤

1. 克隆项目
```bash
git clone https://github.com/Jabez2/-MCP-Agent.git
cd -MCP-Agent
```

2. 安装Python依赖
```bash
pip install -r requirements.txt
```

3. 安装项目
```bash
pip install -e .
```

4. 配置MCP服务
```bash
# 安装文件系统MCP服务依赖
cd mcp_services/filesystem-mcp-server
npm install
npm run build

# 安装代码扫描MCP服务依赖
cd ../code_scanner_mcp
pip install -e .

# 安装网络请求MCP服务依赖
cd ../fetch-mcp
npm install
npm run build
```

### 配置说明

1. **模型配置**: 编辑 `src/config/model_config.py` 配置LLM模型
2. **MCP服务配置**: 编辑 `src/config/mcp_config.py` 配置MCP服务路径
3. **环境变量**: 根据需要设置相关环境变量

### 运行示例

1. 使用默认任务运行
```bash
python src/main.py
```

2. 使用自定义任务运行
```bash
python src/main.py "创建一个数学计算库，包含加减乘除和高级数学函数"
```

3. 运行测试
```bash
python test.py
```

4. 内存管理工具
```bash
# 查看内存状态
python memory_cli.py

# 启动内存Web界面
python memory_web.py
```

## 详细配置

### MCP服务器配置
在 `src/config/mcp_config.py` 中配置MCP服务器路径：
```python
def create_mcp_servers():
    """创建和配置MCP服务器参数"""
    filesystem_mcp_server = StdioServerParams(
        command="node",
        args=[
            "/path/to/filesystem-mcp-server/dist/index.js",
            "/Users"  # 基础目录路径
        ],
        env={
            "FS_BASE_DIRECTORY": "/Users"
        }
    )

    code_runner_mcp_server = StdioServerParams(
        command="npx",
        args=[
            "-y",
            "mcp-server-code-runner@latest"
        ]
    )

    return filesystem_mcp_server, code_runner_mcp_server
```

### LLM模型配置
在 `src/config/model_config.py` 中配置LLM模型：
```python
def create_model_client():
    """创建LLM模型客户端"""
    model_info = ModelInfo(
        family="openai",
        vision=False,
        function_calling=True,
        json_output=True
    )
    return OpenAIChatCompletionClient(
        model="Qwen/Qwen3-Coder-480B-A35B-Instruct",
        api_key="your-api-key",
        base_url="https://api-inference.modelscope.cn/v1/",
        model_info=model_info,
        temperature=0.7,
        top_p=0.8,
        extra_body={"top_k": 20, "repetition_penalty": 1.05}
    )
```

### MCP服务详细说明

#### 1. 文件系统MCP服务 (filesystem-mcp-server)
- **功能**: 提供完整的文件系统操作能力
- **特性**: 智能路径解析、安全文件操作、目录结构发现
- **配置**: 支持基础目录限制和环境变量配置

#### 2. 代码扫描MCP服务 (code_scanner_mcp)
- **功能**: 静态代码分析和质量检测
- **特性**: 代码风格检查、潜在问题识别、质量评分
- **支持**: Python代码分析，可扩展其他语言

#### 3. 网络请求MCP服务 (fetch-mcp)
- **功能**: 外部API调用和数据获取
- **特性**: HTTP请求支持、响应处理、错误管理
- **用途**: 获取外部资源、API集成

## 核心概念

### 任务账本 (TaskLedger)
管理全局任务状态和计划，包括：
- 原始任务描述和需求分析
- 已确认的事实和约束条件
- 详细的执行计划和步骤
- Agent能力映射和职责分配
- 项目配置信息和路径解析

### 进度账本 (ProgressLedger)
管理执行进度和状态跟踪，包括：
- 节点执行状态和生命周期
- 详细的执行历史记录
- 智能重试计数和策略
- 停滞检测和恢复机制
- 性能指标和时间统计

### 智能编排器 (GraphFlowOrchestrator)
核心编排器，负责：
- 任务分解和计划制定
- 智能节点选择和调度
- 执行监控和错误处理
- 动态路径调整和优化
- 内存管理和状态持久化

### 内存管理系统
- **工作流内存管理器**: 记录执行模式和历史
- **Agent状态内存管理器**: 跟踪各Agent的状态变化
- **单元测试内存管理器**: 专门管理测试结果和报告
- **内存导出功能**: 支持数据导出和分析

### 工作台系统 (Workbench)
- **MCP工作台**: 统一的MCP服务接口
- **文件系统工作台**: 专门的文件操作接口
- **代码执行工作台**: 代码运行和测试接口
- **智能路径解析**: 自动发现和解析项目结构

## 开发指南

### 添加新的Agent
1. 在 `src/agents/` 目录下创建新的Agent文件
2. 实现Agent创建函数，遵循现有Agent的模式
3. 在 `src/agents/__init__.py` 中导入并添加到 `create_all_agents` 函数
4. 更新编排器中的执行流程

### 扩展MCP服务
1. 在 `mcp_services/` 目录下创建新的MCP服务
2. 实现MCP协议接口
3. 在 `src/config/mcp_config.py` 中添加服务配置
4. 更新相关Agent以使用新服务

### 扩展内存管理
1. 在 `src/memory/` 目录下创建新的内存管理器
2. 实现内存存储和检索逻辑
3. 集成到相关Agent和编排器中

### 扩展功能
- 修改 `src/core/orchestrator.py` 中的节点流程
- 添加新的数据结构到 `src/core/data_structures.py`
- 扩展工具函数到 `src/utils/` 或 `src/tools/` 目录
- 添加新的工作台到 `src/workbenches/` 目录

### 测试指南
- 在 `tests/` 目录下添加相应的测试文件
- 使用 `pytest` 运行测试
- 确保新功能有充分的测试覆盖

## 技术栈

- **框架**: AutoGen AgentChat
- **语言**: Python 3.8+
- **协议**: MCP (Model Context Protocol)
- **LLM**: 支持OpenAI兼容API (默认使用Qwen3-Coder)
- **工具**: Node.js, npm, pytest
- **存储**: 文件系统 + JSON格式内存存储

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request来改进这个项目。请确保：
1. 代码符合项目的编码规范
2. 添加适当的测试
3. 更新相关文档
4. 提交前运行测试确保通过

## 联系方式

- 项目主页: https://github.com/Jabez2/-MCP-Agent
- 问题反馈: https://github.com/Jabez2/-MCP-Agent/issues
- 文档: 查看 `docs/` 目录获取详细文档

## 更新日志

### v1.0.0
- 初始版本发布
- 实现7个专业Agent协作系统
- 集成3个MCP服务
- 完整的内存管理系统
- 智能编排和调度功能
