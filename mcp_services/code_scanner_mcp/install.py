#!/usr/bin/env python3
"""
代码扫描MCP服务安装脚本

自动安装所需的依赖包。
"""

import subprocess
import sys
from pathlib import Path


def install_dependencies():
    """安装依赖包"""
    print("🔧 开始安装代码扫描MCP服务依赖...")
    
    # 基础依赖
    base_deps = [
        "mcp>=1.2.0",
        "radon>=6.0.1",
    ]
    
    # 可选依赖（如果安装失败不影响基本功能）
    optional_deps = [
        "flake8>=7.0.0",
        "pylint>=3.0.0", 
        "bandit>=1.7.5",
        "mypy>=1.8.0",
        "black>=23.0.0",
        "isort>=5.12.0",
        "pydocstyle>=6.3.0",
        "mccabe>=0.7.0",
        "vulture>=2.10",
        "safety>=3.0.0"
    ]
    
    # 安装基础依赖
    for dep in base_deps:
        try:
            print(f"📦 安装 {dep}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", dep])
            print(f"✅ {dep} 安装成功")
        except subprocess.CalledProcessError as e:
            print(f"❌ {dep} 安装失败: {e}")
            return False
    
    # 安装可选依赖
    failed_optional = []
    for dep in optional_deps:
        try:
            print(f"📦 安装 {dep}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", dep])
            print(f"✅ {dep} 安装成功")
        except subprocess.CalledProcessError as e:
            print(f"⚠️ {dep} 安装失败: {e}")
            failed_optional.append(dep)
    
    if failed_optional:
        print(f"\n⚠️ 以下可选依赖安装失败，部分功能可能受限:")
        for dep in failed_optional:
            print(f"  - {dep}")
        print("\n💡 您可以稍后手动安装这些依赖来启用完整功能。")
    
    print("\n🎉 依赖安装完成!")
    return True


def test_installation():
    """测试安装是否成功"""
    print("\n🧪 测试安装...")
    
    try:
        # 测试导入核心模块
        sys.path.insert(0, str(Path(__file__).parent / "src"))
        from code_scanner_mcp.server import main
        from code_scanner_mcp.analyzers import CodeAnalyzer
        from code_scanner_mcp.report_generator import ReportGenerator
        
        print("✅ 核心模块导入成功")
        
        # 测试分析器初始化
        analyzer = CodeAnalyzer()
        report_generator = ReportGenerator()
        
        print("✅ 分析器初始化成功")
        print("🎉 安装测试通过!")
        return True
        
    except Exception as e:
        print(f"❌ 安装测试失败: {e}")
        return False


def main():
    """主函数"""
    print("🚀 代码扫描MCP服务安装程序")
    print("=" * 50)
    
    # 检查Python版本
    if sys.version_info < (3, 10):
        print("❌ 需要Python 3.10或更高版本")
        sys.exit(1)
    
    print(f"✅ Python版本: {sys.version}")
    
    # 安装依赖
    if not install_dependencies():
        print("❌ 依赖安装失败")
        sys.exit(1)
    
    # 测试安装
    if not test_installation():
        print("❌ 安装测试失败")
        sys.exit(1)
    
    print("\n" + "=" * 50)
    print("🎉 代码扫描MCP服务安装完成!")
    print("\n📖 使用方法:")
    print("  1. 运行服务器: python start_server.py")
    print("  2. 测试功能: python test_scanner.py")
    print("\n📝 配置Claude Desktop:")
    print('  在claude_desktop_config.json中添加:')
    print('  {')
    print('    "mcpServers": {')
    print('      "code-scanner": {')
    print('        "command": "python",')
    print(f'        "args": ["{Path(__file__).parent.absolute() / "start_server.py"}"]')
    print('      }')
    print('    }')
    print('  }')


if __name__ == "__main__":
    main()
