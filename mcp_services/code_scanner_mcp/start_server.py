#!/usr/bin/env python3
"""
代码扫描MCP服务启动脚本

用于启动代码扫描MCP服务器。
"""

import sys
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from code_scanner_mcp.server import main

if __name__ == "__main__":
    main()
