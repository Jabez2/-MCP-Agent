# 🔗 多链路Agent系统使用指南

本项目现在支持多种Agent链路配置，可以根据不同的需求选择合适的执行链路。

## 📋 可用链路配置

### 1. 标准链路 (Standard Chain) - 7个Agent
**完整的企业级开发流程**
```
CodePlanningAgent → FunctionWritingAgent → TestGenerationAgent → UnitTestAgent → RefactoringAgent → CodeScanningAgent → ProjectStructureAgent
```
- ✅ **适用场景**: 企业级项目、完整的软件开发流程
- ✅ **特点**: 包含重构、代码扫描、项目结构化等完整功能
- ✅ **质量保证**: 最高级别的代码质量和项目完整性

### 2. 最小链路 (Minimal Chain) - 4个Agent ⭐ **推荐**
**核心开发流程**
```
CodePlanningAgent → FunctionWritingAgent → TestGenerationAgent → UnitTestAgent
```
- ✅ **适用场景**: 日常开发、功能实现、学习项目
- ✅ **特点**: 包含完整的"规划-编码-测试-验证"流程
- ✅ **平衡**: 功能完整性和执行效率的最佳平衡

### 3. 快速原型链路 (Prototype Chain) - 2个Agent
**快速概念验证**
```
CodePlanningAgent → FunctionWritingAgent
```
- ⚡ **适用场景**: 快速原型、概念验证、演示代码
- ⚡ **特点**: 最快的代码生成速度
- ⚠️ **注意**: 不包含测试验证环节

### 4. 质量保证链路 (Quality Chain) - 3个Agent
**代码质量检查**
```
FunctionWritingAgent → UnitTestAgent → CodeScanningAgent
```
- 🔍 **适用场景**: 代码审查、质量检查、现有代码验证
- 🔍 **特点**: 专注于测试和代码质量分析
- 📝 **前提**: 假设代码规划已完成

## 🚀 使用方法

### 方法1: 使用标准链路（保持原有功能）
```bash
# 使用完整的7个Agent标准链路
python src/main.py
```

### 方法2: 使用最小链路（新功能）
```bash
# 使用默认的最小链路和默认任务
python minimal_main.py

# 使用最小链路和自定义任务
python minimal_main.py minimal "创建一个计算器程序"

# 使用快速原型链路
python minimal_main.py prototype "创建一个简单的Hello World函数"

# 使用质量保证链路
python minimal_main.py quality "检查现有的数学计算代码"
```

## 📊 链路对比

| 链路名称 | Agent数量 | 执行时间 | 代码质量 | 适用场景 |
|---------|----------|---------|---------|---------|
| Standard | 7 | 最长 | 最高 | 企业级项目 |
| **Minimal** | **4** | **中等** | **高** | **日常开发** ⭐ |
| Prototype | 2 | 最短 | 基础 | 快速验证 |
| Quality | 3 | 短 | 高 | 代码审查 |

## 🔧 技术实现

### 代码结构
```
src/
├── config/
│   ├── chain_config.py      # 链路配置定义
│   └── __init__.py          # 导出链路配置
├── agents/
│   ├── chain_factory.py     # 链路工厂，根据配置创建Agent
│   └── ...                  # 各个Agent实现
└── core/
    └── orchestrator.py      # 支持多链路的编排器

minimal_main.py              # 最小链路入口文件
test_chains.py              # 链路配置测试脚本
```

### 配置系统
- **链路配置**: 在 `src/config/chain_config.py` 中定义
- **Agent工厂**: 在 `src/agents/chain_factory.py` 中实现
- **依赖管理**: 每个链路都有独立的依赖关系配置

## 🧪 测试验证

运行测试脚本验证所有链路配置：
```bash
python test_chains.py
```

## 💡 使用建议

### 选择链路的建议
1. **学习和实验** → 使用 `minimal` 链路
2. **快速验证想法** → 使用 `prototype` 链路  
3. **日常开发工作** → 使用 `minimal` 链路
4. **代码质量检查** → 使用 `quality` 链路
5. **正式项目交付** → 使用 `standard` 链路

### 最佳实践
- 开发初期使用 `prototype` 快速验证
- 功能开发使用 `minimal` 保证质量
- 项目完成前使用 `standard` 确保完整性

## 🔮 未来扩展

当前实现为将来的智能链路选择功能打下了基础：
- 基于任务复杂度自动选择链路
- 基于质量要求动态调整链路
- 支持链路间的动态切换

## ⚠️ 注意事项

1. **兼容性**: 新的多链路系统完全不影响原有的标准链路功能
2. **文件分离**: `src/main.py` 保持不变，新功能通过 `minimal_main.py` 提供
3. **配置独立**: 每个链路都有独立的配置，互不干扰
4. **Memory系统**: 所有链路都支持完整的Memory和Agent通信功能

---

🎉 **现在您可以根据不同的需求选择合适的Agent链路，享受更灵活的代码生成体验！**
