# 🐧 Ubuntu环境快速搭建指南

## 📋 系统要求

### 推荐配置
- **操作系统**: Ubuntu 22.04 LTS 或 24.04 LTS
- **内存**: 4GB+ (推荐8GB+)
- **存储**: 20GB+ 可用空间
- **网络**: 稳定的互联网连接

### 最低配置
- **操作系统**: Ubuntu 20.04 LTS
- **内存**: 2GB
- **存储**: 10GB 可用空间

## 🚀 一键安装

### 方法一：自动安装脚本（推荐）

```bash
# 克隆项目
git clone <your-repo-url>
cd qq-channel-collector

# 给脚本执行权限
chmod +x setup_ubuntu.sh

# 运行安装脚本
./setup_ubuntu.sh
```

### 方法二：手动安装

#### 1. 更新系统
```bash
sudo apt update && sudo apt upgrade -y
```

#### 2. 安装基础依赖
```bash
sudo apt install -y curl wget git build-essential software-properties-common python3 python3-pip python3-venv
```

#### 3. 安装Google Chrome
```bash
# 添加Google Chrome仓库
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list

# 安装Chrome
sudo apt update
sudo apt install -y google-chrome-stable
```

#### 4. 安装ChromeDriver
```bash
# 获取Chrome版本
CHROME_VERSION=$(google-chrome --version | grep -oP '\d+\.\d+\.\d+')
CHROME_MAJOR_VERSION=$(echo $CHROME_VERSION | cut -d'.' -f1)

# 获取对应ChromeDriver版本
CHROMEDRIVER_VERSION=$(curl -s "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_${CHROME_MAJOR_VERSION}")

# 下载并安装ChromeDriver
cd /tmp
wget "https://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver_linux64.zip"
unzip chromedriver_linux64.zip
sudo mv chromedriver /usr/local/bin/
sudo chmod +x /usr/local/bin/chromedriver
```

#### 5. 配置项目环境
```bash
# 进入项目目录
cd qq-channel-collector

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装项目依赖
pip install --upgrade pip
pip install -r requirements.txt

# 创建配置文件
cp env_example .env

# 编辑配置文件
vim .env
```

## ⚙️ 配置文件设置

编辑 `.env` 文件，设置Ubuntu环境下的正确路径：

```bash
# Ubuntu环境配置
CHROME_PATH="/usr/bin/google-chrome"
CHROMEDRIVER_PATH="/usr/local/bin/chromedriver"
HEADLESS=true

# 数据存储配置
DATA_DIR="data"
IMAGES_DIR="data/images"
ENABLE_IMAGE_DOWNLOAD=true

# 日志配置
LOG_LEVEL=INFO
LOG_FILE="logs/qq_channel_collector.log"
```

## 🧪 测试安装

### 1. 测试基础环境
```bash
# 激活虚拟环境
source venv/bin/activate

# 检查Python版本
python --version

# 检查Chrome版本
google-chrome --version

# 检查ChromeDriver版本
chromedriver --version
```

### 2. 测试项目功能
```bash
# 测试连接（替换为实际的QQ频道URL）
python main.py test --url "https://pd.qq.com/s/example"

# 测试MCP服务器
python run_mcp_server.py &
```

## 🔧 常见问题解决

### 1. Chrome版本不匹配
```bash
# 重新安装匹配的ChromeDriver
CHROME_VERSION=$(google-chrome --version | grep -oP '\d+\.\d+\.\d+')
CHROME_MAJOR_VERSION=$(echo $CHROME_VERSION | cut -d'.' -f1)
CHROMEDRIVER_VERSION=$(curl -s "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_${CHROME_MAJOR_VERSION}")

cd /tmp
wget "https://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver_linux64.zip"
unzip -o chromedriver_linux64.zip
sudo mv chromedriver /usr/local/bin/
```

### 2. 权限问题
```bash
# 给ChromeDriver执行权限
sudo chmod +x /usr/local/bin/chromedriver

# 检查项目目录权限
ls -la data/
chmod 755 data/images/
```

### 3. 依赖包问题
```bash
# 重新安装依赖
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
```

### 4. 无头模式问题
```bash
# 安装X11相关包（如果需要）
sudo apt install -y xvfb

# 使用虚拟显示
export DISPLAY=:99
Xvfb :99 -screen 0 1024x768x24 > /dev/null 2>&1 &
```

## 🐳 Docker方式（可选）

如果你偏好使用Docker，可以创建以下Dockerfile：

```dockerfile
FROM ubuntu:22.04

# 设置非交互模式
ENV DEBIAN_FRONTEND=noninteractive

# 安装基础依赖
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    wget \
    curl \
    unzip \
    google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# 安装ChromeDriver
RUN CHROME_VERSION=$(google-chrome --version | grep -oP '\d+\.\d+\.\d+') && \
    CHROME_MAJOR_VERSION=$(echo $CHROME_VERSION | cut -d'.' -f1) && \
    CHROMEDRIVER_VERSION=$(curl -s "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_${CHROME_MAJOR_VERSION}") && \
    wget "https://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver_linux64.zip" && \
    unzip chromedriver_linux64.zip && \
    mv chromedriver /usr/local/bin/ && \
    chmod +x /usr/local/bin/chromedriver

# 设置工作目录
WORKDIR /app

# 复制项目文件
COPY . .

# 安装Python依赖
RUN pip3 install -r requirements.txt

# 创建必要目录
RUN mkdir -p data/images logs

# 启动命令
CMD ["python3", "run_mcp_server.py"]
```

## 📊 性能优化建议

### 1. 系统优化
```bash
# 增加文件描述符限制
echo "* soft nofile 65536" | sudo tee -a /etc/security/limits.conf
echo "* hard nofile 65536" | sudo tee -a /etc/security/limits.conf

# 优化内存设置
echo "vm.swappiness=10" | sudo tee -a /etc/sysctl.conf
```

### 2. Chrome优化
在 `.env` 中添加Chrome优化选项：
```bash
# Chrome启动参数优化
CHROME_ARGS="--no-sandbox,--disable-dev-shm-usage,--disable-gpu,--disable-extensions"
```

## 🔄 自动化部署

### 创建systemd服务
```bash
sudo tee /etc/systemd/system/qq-channel-collector.service > /dev/null <<EOF
[Unit]
Description=QQ Channel Collector MCP Server
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
Environment=PATH=$(pwd)/venv/bin
ExecStart=$(pwd)/venv/bin/python run_mcp_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 启用并启动服务
sudo systemctl daemon-reload
sudo systemctl enable qq-channel-collector
sudo systemctl start qq-channel-collector
```

## 📝 日常使用

### 激活环境
```bash
cd qq-channel-collector
source venv/bin/activate
```

### 常用命令
```bash
# 测试连接
python main.py test --url "频道URL"

# 采集数据
python main.py collect --url "频道URL" --max-posts 100

# 启动MCP服务器
python run_mcp_server.py
```

这个Ubuntu环境配置方案确保了最佳的开发和运行体验！🚀
