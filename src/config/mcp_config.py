"""
MCP服务器配置

提供MCP服务器的创建和配置功能。
"""

from autogen_ext.tools.mcp import StdioServerParams


def create_mcp_servers():
    """创建和配置MCP服务器参数"""
    filesystem_mcp_server = StdioServerParams(
        command="node",
        args=[
            "/Users/jabez/Nutstore Files/multiAgent/mcp_services/filesystem-mcp-server/dist/index.js",
            "/Users"
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
