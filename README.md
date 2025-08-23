# QQ频道MCP数据采集工具

一个高效的QQ频道数据采集工具，支持图片、动图、视频等多种媒体类型的自动下载。

## 🚀 主要功能

- **高效视频抓取**: 直接解析JSON-LD，无需浏览器
- **完整媒体支持**: 图片、GIF动图、视频全支持
- **智能回退机制**: 高效抓取失败时自动回退到Chrome方案
- **增量更新**: 避免重复下载，提高效率

## 📁 项目结构

```
QQChannelMCP/
├── src/                    # 源代码目录
│   ├── collector/         # 数据采集器
│   ├── core/             # 核心组件
│   ├── models/           # 数据模型
│   └── utils/            # 工具函数
├── server/                # MCP服务器
├── data/                  # 数据存储目录
├── run_mcp_server.py      # 启动脚本
└── requirements.txt       # 依赖包
```

## 🛠️ 快速开始

1. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

2. **启动MCP服务器**
   ```bash
   python run_mcp_server.py
   ```

3. **使用MCP工具**
   - `test_connection`: 测试频道连接
   - `collect_daily_hellokitty`: 收集今日HelloKitty内容
   - `get_storage_info`: 获取存储信息

## 📊 支持功能

- ✅ 高效视频检测和下载
- ✅ 图片和GIF动图下载
- ✅ 完整帖子信息采集
- ✅ 增量更新机制
- ✅ 异步并发下载
- ✅ 标准化文件命名

## 🔧 技术特点

- **FastVideoScraper**: 无需浏览器的快速抓取器
- **EnhancedQQChannelScraper**: 增强版Chrome抓取器
- **MultimediaHelloKittyDownloader**: 多媒体下载器
- **异步并发**: 提高下载效率
- **智能媒体类型检测**: 自动识别文件类型
