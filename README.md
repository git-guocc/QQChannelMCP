# 📱 QQ频道数据采集工具

一个专注于QQ频道数据采集的自动化工具，支持通过MCP协议与AI客户端集成，实现智能化的内容采集和筛选。

## ✨ 主要特性

- 🔍 **无需登录**: 采集公开频道的公开内容
- 🤖 **AI驱动筛选**: 支持自然语言描述的复杂筛选条件
- 📊 **多维度筛选**: 时间、内容、作者、互动数据等多重筛选
- 🖼️ **图片采集**: 自动下载并保存帖子中的图片
- 💾 **结构化存储**: JSON/CSV等多种格式存储
- 🧠 **MCP协议支持**: 与Claude Desktop等AI客户端无缝集成

## 📋 功能清单

### 数据采集
- [x] **频道帖子采集** - 采集指定频道的所有帖子
- [x] **智能筛选** - 基于时间、关键词、点赞数等条件筛选
- [x] **图片下载** - 自动下载帖子中的图片资源
- [x] **AI筛选** - 使用AI进行复杂的内容筛选

### 数据存储
- [x] **JSON存储** - 结构化JSON格式存储
- [x] **CSV存储** - 表格形式存储，便于分析
- [x] **图片管理** - 本地图片存储和管理

## 🚀 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 基本使用

```python
# 导入模块
from collector.channel_scraper import QQChannelScraper
from models.filter_criteria import FilterCriteria
from storage.json_storage import JSONStorage

# 创建采集器
scraper = QQChannelScraper()

# 采集数据
posts = await scraper.scrape_channel_posts(
    "https://pd.qq.com/s/hellokitty", 
    max_posts=100
)

# 保存数据
storage = JSONStorage("data/posts.json")
await storage.save_posts(posts)
```

### MCP集成

配置Claude Desktop：

```json
{
  "mcpServers": {
    "qq-channel-collector": {
      "command": "python",
      "args": ["-m", "server.mcp_server"],
      "cwd": "/path/to/qq-channel-collector"
    }
  }
}
```

### AI对话使用

```
用户："采集HelloKitty频道最近3天的帖子，只要包含'可爱'关键词且点赞数超过10的内容"

AI会自动调用工具完成采集任务。
```

## 📁 项目结构

```
qq-channel-collector/
├── core/                   # 核心基础模块
├── collector/              # 数据采集模块
├── models/                 # 数据模型
├── storage/                # 数据存储
├── server/                 # MCP服务器
├── utils/                  # 工具模块
├── data/                   # 数据目录
└── config/                 # 配置文件
```

## 🛠️ 环境要求

- Python 3.10+
- Chrome浏览器
- ChromeDriver

## 📄 许可证

本项目基于 MIT 许可证开源。
