# 功能演示清单（基于 MCP 多链代码生成 Agent 项目）

本文档列出在 PPT 功能演示部分可展示的内容、对应所需的图/素材，以及建议的现场演示步骤与产物检查点。按“从整体到关键能力”的顺序组织，便于在 10–20 分钟内完成一轮 Demo。

---

## 演示 1：端到端自动化开发流程（最小/标准链路）
- 目标：从需求到代码、测试、扫描、结构化交付的完整流水线
- 演示要点：
  - 链路装配：ChainFactory 选择 minimal/standard
  - 节点执行：Planning → Coding → TestGen → UnitTest → (Refactor) → Scan → Structure
  - 产物交付：代码文件、测试报告、扫描报告、项目结构化
- 需要的图/素材：
  - 执行层总体架构图（上下结构、Agent 一行）
  - 四条链路概览图（原型/最小/质量/标准）
  - 执行时序图（关键交互，已有于“课题总结 8.7.md”附录 A）
  - 终端/日志截屏：每个 Agent 的开始/完成日志（WorkflowLogger）
- 现场步骤：选择 minimal 或 standard → 运行 orchestrator → 展示输出目录与报告
- 验收检查点：
  - UnitTest 通过率与覆盖率达到阈值（或触发后续流程）
  - CodeScanning 无高危问题
  - 生成结构化项目目录（src/tests/docs 等）

## 演示 2：失败→重构→回测闭环（关键能力）
- 目标：展示单测失败后，RefactoringAgent 接棒修复并回到 UnitTest 验证的闭环
- 演示要点：
  - UnitTest 失败 → ProgressLedger 记录失败与错误类型
  - UnitTestMemoryManager 记录完整测试输出与智能分析
  - RefactoringAgent 读取失败明细与建议 → 修复代码 → 回测通过
- 需要的图/素材：
  - “失败-修复-回测”闭环流程小图（Mermaid）
  - 向量记忆系统架构图（标注 UnitTestMemoryManager 方法与 collection）
  - 失败用例与错误栈截屏、修复前后 diff 简图
- 现场步骤：刻意制造 1 个用例失败 → 运行 → 观察重构 → 回测通过
- 验收检查点：失败条目消除、通过率上升、执行日志新增“成功路径”

## 演示 3：多链路动态切换（速度/质量拨档）
- 目标：根据 KPI 动态从最小链路切换到质量/标准链路
- 演示要点：
  - 初始选择：TaskLedger + 复杂度评估
  - 运行中：ProgressLedger KPI 触发插入“Refactor+Scan”子图
- 需要的图/素材：
  - 链路选择菱形图 + 子图插拔示意
  - KPI 卡片：pass_rate、coverage、retries、scan_criticals
- 现场步骤：以最小链路启动 → 故意降低覆盖率/制造失败 → 自动升级链路
- 验收检查点：链路切换日志（原因/时间/KPI），后续扫描与收尾执行

## 演示 4：图结构 + 账本分析联动（决策透明）
- 目标：展示 GraphFlow 结构与双账本的联合决策
- 演示要点：
  - GraphFlow 条件边（UnitTest 通过→Scan；失败→Refactor→UnitTest）
  - TaskLedger（DoD/依赖）+ ProgressLedger（KPI/重试/耗时）共同驱动节点选择
- 需要的图/素材：
  - 双账本机制图（外层 TaskLedger / 内层 ProgressLedger + 决策引擎）
  - GraphFlow 条件边示意（简化版）
- 现场步骤：展示一次节点选择的依据（账本片段 + 日志）
- 验收检查点：
  - 账本中存有“selected_node/decision_reason/node_instructions”等证据

## 演示 5：向量记忆检索辅助修复与提示增强
- 目标：展示向量记忆如何辅助问题定位与提示增强
- 演示要点：
  - ExecutionLogManager.get_similar_executions / get_error_solutions 检索历史样例
  - AgentCommunicationMemory.update_agent_context 聚合依赖输出与最近消息
  - UnitTestMemoryManager.get_detailed_test_info_for_refactoring 提供定点修复信息
- 需要的图/素材：
  - 向量记忆系统架构图（每类方法以无序点列 + 连线带 collection 标签）
  - 相似案例检索结果截屏（命中项摘要）
- 现场步骤：在失败后调用检索 → 展示命中案例 → 套用修复建议
- 验收检查点：检索命中率、修复成功率提升

## 演示 6：MCP 工具能力（文件/执行/扫描）
- 目标：展示标准化工具的可用与隔离
- 演示要点：
  - filesystem-mcp-server：文件读写/目录管理/权限控制
  - code-runner-mcp：执行测试、捕获输出
  - code-scanner-mcp：静态分析（复杂度、风格、安全）
- 需要的图/素材：
  - MCP 服务层简图（四类服务 + MCP Protocol）
  - 工具调用日志/返回片段截屏
- 现场步骤：触发 1–2 次典型工具调用并展示返回
- 验收检查点：工具返回结构化、错误处理有日志

## 演示 7：项目结构化收尾（可交付）
- 目标：展示 ProjectStructureAgent 生成可交付的项目结构
- 演示要点：
  - 生成 src/tests/docs 等目录与必要配置文件
  - 按约定将主代码/测试/报告归档
- 需要的图/素材：
  - 目录树截图（生成前后对比）
  - 收尾日志摘要
- 现场步骤：运行到 Structure → 打开输出目录
- 验收检查点：结构清晰、可直接运行测试

## 演示 8：可观测性与复盘
- 目标：展示执行过程的可见性和可追溯
- 演示要点：
  - WorkflowLogger：Agent 开始/完成、耗时、成功/失败
  - ProgressLedger：KPI、重试、错误类型、关键路径
- 需要的图/素材：
  - 指标仪表盘样例（可用静态图示范）
  - 节点热力/粗边权示意（图结构叠加 KPI）
- 现场步骤：展示一段执行的日志与指标截图
- 验收检查点：日志与账本数据一致、能复盘到具体节点

---

## 建议的 PPT 图表清单（可直接放图的候选）
1) 执行层总体架构图（上下结构，Agent 一行）
2) 多链路概览图（四条链路 + 决策菱形）
3) 失败→重构→回测闭环图（小循环）
4) 双账本机制图（TaskLedger + ProgressLedger + 决策引擎）
5) 向量记忆系统架构图（方法无序点列 + 连线标签）
6) MCP 服务层图（四类服务 + 协议层）
7) 执行时序图（已有于“课题总结 8.7.md”）
8) KPI 仪表/热力示意图（可静态展示）

---

## 演示准备清单（可勾选）
- [ ] 准备两套链路配置（minimal / standard）
- [ ] 预置一个会失败的用例（便于展示重构闭环）
- [ ] 本地 ChromaDB 持久化目录清理/留存对比（演示检索）
- [ ] 终端窗口与日志输出模板（便于截图/录屏）
- [ ] PPT 中的图示放大比例与对比度测试

---

## 时间分配建议（15 分钟）
- 端到端流程：6 分钟
- 失败→重构→回测：4 分钟
- 多链路切换/记忆检索：3 分钟
- MCP 工具与可观测性：2 分钟

