#!/usr/bin/env python3
"""
MCP服务器启动脚本
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from server.mcp_server import app

if __name__ == "__main__":
    # 运行MCP服务器
    app.run_stdio()
