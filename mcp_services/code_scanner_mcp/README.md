# 代码扫描MCP服务

这是一个专门的MCP服务，提供Python代码静态分析和质量扫描功能。

## 功能特性

### 🔍 代码质量分析
- **复杂度分析**: 圈复杂度、认知复杂度、Halstead复杂度
- **代码度量**: 代码行数、函数长度、类大小统计
- **重复代码检测**: 识别重复的代码模式

### 📏 代码风格检查
- **PEP8合规性**: 使用flake8进行风格检查
- **命名规范**: 检查变量、函数、类的命名规范
- **导入排序**: 使用isort检查导入语句排序

### 🛡️ 安全扫描
- **安全漏洞检测**: 使用bandit检测常见安全问题
- **依赖安全检查**: 使用safety检查依赖包安全性

### 📚 文档质量
- **文档字符串检查**: 使用pydocstyle检查文档规范
- **类型注解检查**: 使用mypy进行类型检查

### 🧹 代码清理
- **死代码检测**: 使用vulture检测未使用的代码
- **代码格式化建议**: 基于black的格式化建议

## MCP工具

### `scan_code`
扫描指定目录或文件的Python代码

**参数:**
- `path` (string): 要扫描的文件或目录路径
- `scan_types` (array): 扫描类型列表，可选值：
  - `complexity`: 复杂度分析
  - `style`: 代码风格检查
  - `security`: 安全扫描
  - `documentation`: 文档质量检查
  - `cleanup`: 代码清理建议
- `output_format` (string): 输出格式，可选 `json` 或 `markdown`

**返回:**
详细的代码扫描报告，包含所有发现的问题和建议。

### `save_report`
保存扫描报告到文件

**参数:**
- `report_content` (string): 报告内容
- `output_path` (string): 保存路径
- `format` (string): 文件格式 (`json`, `markdown`, `html`)

## 安装和使用

```bash
# 安装依赖
pip install -e .

# 运行MCP服务器
python -m code_scanner_mcp.server
```

## 配置示例

在Claude Desktop配置中添加：

```json
{
  "mcpServers": {
    "code-scanner": {
      "command": "python",
      "args": ["-m", "code_scanner_mcp.server"]
    }
  }
}
```
