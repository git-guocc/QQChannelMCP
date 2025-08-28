# QQ频道MCP数据采集工具（重构版）

一个面向“QQ 频道帖子图片采集/识别/整理”的 MCP 工具集，支持高频增量抓取、日内去重、自动目录规整与可选的 HelloKitty 识别/复制。

## 功能总览

- 抓取与回退链路（稳健）
  - Phase 3：CDP 网络层 JSON 优先（拦截 XHR/Fetch 响应直接解析）
  - 回退：JSON-LD → 脚本 JSON → DOM 锚点（`.main-feed-item`）→ 泛化 CSS（兜底）
- 媒体支持
  - 图片/GIF 下载（并发/重试/去重）
  - 视频：仅识别链接，不下载（`ENABLE_VIDEO` 可完全禁用）
- 增量与去重
  - 同日目录复用：`data/dayupdate/YYYY-MM-DD/`
  - 文件命名：`{YYYYMMDD_HHMM}_{post_id}_{type}_{index:02}{ext}`，已存在即跳过
  - manifest.json：记录 processed_post_ids、累计统计、last_run；抓取器维护 last_max_post_time（软边界）
  - 早停：硬边界=当天 00:00 + 软边界=上次最大时间；连续无新帖/仅未知时间阈值早停
- HelloKitty 识别与复制（可选）
  - 识别：多提供商（OpenRouter/Gemini/GitHub Models）
  - 复制：识别为 HelloKitty 的图片复制到 `HelloKitty/` 子目录
- 简单预设工具（更易用）
  - download_only：采集+下载（不识别、不复制）
  - full_pipeline：采集+下载+识别+复制（一步到位）

## 目录结构

```
QQChannelMCP/
├── src/
│   ├── collector/               # EnhancedQQChannelScraper（抓取器）
│   ├── core/                    # settings / results / exceptions / browser
│   ├── models/                  # QQChannelPost 等数据模型
│   ├── services/                # 下载/识别/复制服务
│   └── utils/                   # 目录管理等
├── data/                        # 存储根目录
│   └── dayupdate/
│       └── YYYY-MM-DD/          # 当日目录（复用）
│           ├── images/          # 图片
│           ├── gifs/            # 动图
│           ├── videos/          # 视频（可禁用）
│           ├── HelloKitty/      # 识别复制结果
│           └── manifest.json    # 累计统计/边界/去重
├── mcp_server_refactored.py     # MCP 服务器入口
├── pyproject.toml               # 项目配置和依赖定义
└── requirements.txt             # 依赖列表
```

## 安装与启动

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 环境配置

建议创建 `.env` 文件（不要提交到仓库）：
```
# 浏览器
CHROMEDRIVER_PATH=/usr/local/bin/chromedriver
CHROME_PATH=/usr/bin/google-chrome
HEADLESS=true

# 采集
MAX_POSTS=200
ENABLE_VIDEO=true            # true 记录视频链接（不下载）；false 完全禁用

# AI（至少配置一个，推荐 OpenRouter）
AI_PREFERRED_PROVIDER=openrouter
OPENROUTER_API_KEY=...
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
GITHUB_MODELS_API_KEY=...
GITHUB_MODELS_BASE_URL=https://models.github.ai
GEMINI_API_KEY=...
GEMINI_BASE_URL=https://generativelanguage.googleapis.com
```

### 3. 启动 MCP 服务器

```bash
python mcp_server_refactored.py
```

## 使用 Docker（可选）

不想重复配置环境时，推荐用 Docker 将依赖打包在镜像中：

#### 构建镜像

```bash
docker build -t qqchannelmcp:latest .
```

#### 运行容器

建议挂载数据/日志目录，传入 .env：

```bash
docker run --rm \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  --env-file ./.env \
  -e CHANNEL_URL="https://pd.qq.com/g/XXXX" \
  -e MAX_POSTS=200 \
  qqchannelmcp:latest
```

说明：
- 镜像内已预装 Chromium/Chromedriver 并设置 `HEADLESS=true`
- 可通过环境变量控制：`RECOGNITION=true`、`COPY_HELLOKITTY=true`
- 若想自定义命令，可在 `docker run` 末尾附加：
  `python scripts/run_incremental.py --channel-url ... --max-posts ...`

#### 定时调度（cron 示例）
```
*/15 * * * * docker run --rm \
  -v /path/QQChannelMCP/data:/app/data \
  -v /path/QQChannelMCP/logs:/app/logs \
  --env-file /path/QQChannelMCP/.env \
  -e CHANNEL_URL="https://pd.qq.com/g/XXXX" -e MAX_POSTS=200 \
  qqchannelmcp:latest >> /path/QQChannelMCP/logs/cron.out 2>&1
```

## 可用 MCP 工具

- get_configuration_summary：配置摘要
- test_connection(channel_url)：测试连接
- download_only(channel_url, max_posts?)：采集+下载（不识别、不复制）
- full_pipeline(channel_url, max_posts?)：采集+下载+识别+复制
- execute_complete_workflow(channel_url, max_posts?, enable_recognition?, enable_copy?)：高级全流程（精细控制）
- execute_scraping_only(channel_url, max_posts?)：仅采集
- execute_recognition_only(image_directory, ai_provider?)：仅识别
- execute_copy_only(source_directory, destination_directory?)：仅复制
- get_storage_info：当日目录统计（含 manifest）
- get_workflow_performance_stats：工作流性能统计
- validate_ai_services：AI 提供商状态

说明：download_only / full_pipeline 默认在未指定 `max_posts` 时使用 `settings.scraping.max_posts`。

## 定时采集（不经 MCP）

若仅需定时增量采集，建议使用内置脚本入口，直接调用工作流编排器（无需启动 MCP 服务器）：

```
python scripts/run_incremental.py \
  --channel-url "https://pd.qq.com/g/5yy11f95s1" \
  --max-posts 200 \
  --recognition       # 可选，默认关闭
  --copy              # 可选，默认关闭
```

- 自动读取 `.env`（若存在）并遵循 `src/core/settings.py` 配置。
- 默认写日志到 `logs/cron.log`，并用 `logs/cron.lock` 做文件锁避免并发。

示例 cron（每 15 分钟运行一次，仅采集+下载）：

```
*/15 * * * * cd /path/to/QQChannelMCP && . .venv/bin/activate && \
  python scripts/run_incremental.py --channel-url "https://pd.qq.com/g/XXXX" --max-posts 200 >> logs/cron.out 2>&1
```

说明：若你需要在 IDE/Agent 里交互式地调用各阶段能力，可以继续使用本仓库自带的 MCP 服务器；若只是定时任务，上述脚本更轻量。

## 关键行为说明

### 增量与早停
- 硬边界 hard_since：当天 00:00，仅保留今天内（或时间未知）的帖子
- 软边界 soft_since：manifest.last_max_post_time（上一轮最大帖子时间），用于减少请求量
- 早停判定：
  - 连续 3 页“无新帖且大多为昨天及更早” → 停
  - 连续 2 页“仅未知时间且无新帖” → 停
- 同日目录复用 + 已存在即跳过（文件命名稳定），避免重复下载

### 文件与目录
- 当日目录：`data/dayupdate/YYYY-MM-DD/`
- 命名：`{YYYYMMDD_HHMM}_{post_id}_{type}_{index:02}{ext}`
- manifest.json：示例字段
```
{
  "processed_post_ids": ["B_...", ...],
  "total_images": 120,
  "total_gifs": 5,
  "downloaded_files_sum": 100,
  "failed_files_sum": 2,
  "total_size_sum": 12345678,
  "last_run": "2025-08-25T23:10:45",
  "last_max_post_time": "2025-08-25T22:59:01"
}
```

### AI 提供商
- 支持：OpenRouter、GitHub Models、Gemini（CherryStudio 已移除）
- 探活：不依赖固定文案，使用“请求成功且 JSON 可解析”为通过

### 视频策略
- 默认仅识别链接，不下载；`ENABLE_VIDEO=false` 可完全禁用（不记录、不统计、不创建目录）

## 典型使用建议

- 高频增量（VPS 定时，每 10–20 分钟）
  - 使用 `download_only(channel_url, max_posts?)`
  - 依赖早停与 manifest 去重，避免重复与漏抓

- 每日成果（每日 1 次）
  - 使用 `full_pipeline(channel_url, max_posts?)`
  - 自动将识别为 HelloKitty 的图片复制到 `HelloKitty/` 子目录

## 注意与限制

- 当前针对“帖子流模块”抓取；评论区与其它模块未默认纳入
- 某些接口可能存在限流/签名策略，建议适当的定时频率与 `max_posts` 配置
- `.env` 含敏感密钥，请勿提交；泄露需立即旋转

## 故障排查

- 启动报错找不到 ChromeDriver：检查 `CHROMEDRIVER_PATH` 是否可执行；否则将自动通过 webdriver-manager 安装
- 抓取很慢或抓不到：
  - 检查网络层是否启用（日志提示 CDP Network.enable）
  - 尝试调大 `MAX_POSTS` 或放宽定时间隔
  - 检查目标页是否需要登录（如需要可配置用户数据目录或注入 Cookie，当前未内置）
- 识别不可用：
  - 运行 `validate_ai_services` 检查 provider 配置与可用性
  - 推荐先用 OpenRouter 测试

## 许可证

本项目不附带开源许可证；如需对外分发请联系仓库所有者。
