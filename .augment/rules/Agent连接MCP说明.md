---
type: "always_apply"
---

在搭建Agent并给Agent配置MCP服务的时候，采用stdio的通信方式。有些MCP服务可以自己写，有些MCP服务需要调用别人的，开发环境是windows环境，启动MCP服务的命令可以类似下方命令，用node + mcp的路径中的index.js 来进行启动。例如项目mcp_services文件夹下有一个filesystem-mcp-server的MCP服务，可以采用
node D:\mcp_multichain_agent\mcp_services\filesystem-mcp-server\dist\index.js D: 这条命令。
JSON格式：
{
  "mcpServers": {
    "fileSystem": {
      "command": "node",
      "args": [
        "D:\\filesystem-mcp-server\\dist\\index.js",
        "C:\\Users"
      ]
    }
  }
}