#!/bin/bash
# QQ频道数据采集工具 - Ubuntu环境搭建脚本

set -e  # 遇到错误立即退出

echo "🚀 开始配置Ubuntu开发环境..."

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印彩色信息
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 检查是否为Ubuntu系统
check_ubuntu() {
    if ! command -v lsb_release &> /dev/null; then
        print_error "不是Ubuntu系统或lsb_release未安装"
        exit 1
    fi
    
    OS_NAME=$(lsb_release -si)
    OS_VERSION=$(lsb_release -sr)
    
    if [ "$OS_NAME" != "Ubuntu" ]; then
        print_error "当前系统不是Ubuntu: $OS_NAME"
        exit 1
    fi
    
    print_success "检测到Ubuntu $OS_VERSION"
}

# 更新系统包
update_system() {
    print_info "更新系统包..."
    sudo apt update && sudo apt upgrade -y
    print_success "系统包更新完成"
}

# 安装基础依赖
install_basic_deps() {
    print_info "安装基础依赖..."
    sudo apt install -y \
        curl \
        wget \
        git \
        build-essential \
        software-properties-common \
        apt-transport-https \
        ca-certificates \
        gnupg \
        lsb-release \
        unzip \
        vim \
        htop
    print_success "基础依赖安装完成"
}

# 安装Python 3.10+
install_python() {
    print_info "检查Python版本..."
    
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
        print_info "当前Python版本: $PYTHON_VERSION"
        
        # 检查版本是否满足要求 (>= 3.10)
        if [ "$(echo "$PYTHON_VERSION >= 3.10" | bc -l)" -eq 1 ]; then
            print_success "Python版本满足要求"
        else
            print_warning "Python版本过低，需要升级到3.10+"
            sudo apt install -y python3.10 python3.10-venv python3.10-pip
        fi
    else
        print_info "安装Python 3.10..."
        sudo apt install -y python3.10 python3.10-venv python3.10-pip
    fi
    
    # 安装pip和venv
    sudo apt install -y python3-pip python3-venv python3-dev
    
    # 创建软链接
    if [ ! -L "/usr/bin/python" ]; then
        sudo ln -sf /usr/bin/python3 /usr/bin/python
    fi
    
    print_success "Python环境配置完成"
}

# 安装Google Chrome
install_chrome() {
    print_info "安装Google Chrome..."
    
    if command -v google-chrome &> /dev/null; then
        CHROME_VERSION=$(google-chrome --version)
        print_success "Chrome已安装: $CHROME_VERSION"
        return
    fi
    
    # 添加Google Chrome仓库
    wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
    
    # 更新包列表并安装Chrome
    sudo apt update
    sudo apt install -y google-chrome-stable
    
    CHROME_VERSION=$(google-chrome --version)
    print_success "Chrome安装完成: $CHROME_VERSION"
}

# 安装ChromeDriver
install_chromedriver() {
    print_info "安装ChromeDriver..."
    
    # 获取Chrome版本号
    CHROME_VERSION=$(google-chrome --version | grep -oP '\d+\.\d+\.\d+')
    CHROME_MAJOR_VERSION=$(echo $CHROME_VERSION | cut -d'.' -f1)
    
    print_info "Chrome版本: $CHROME_VERSION"
    print_info "Chrome主版本: $CHROME_MAJOR_VERSION"
    
    # 获取对应的ChromeDriver版本
    CHROMEDRIVER_VERSION=$(curl -s "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_${CHROME_MAJOR_VERSION}")
    
    if [ -z "$CHROMEDRIVER_VERSION" ]; then
        print_error "无法获取ChromeDriver版本信息"
        exit 1
    fi
    
    print_info "ChromeDriver版本: $CHROMEDRIVER_VERSION"
    
    # 下载ChromeDriver
    CHROMEDRIVER_URL="https://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver_linux64.zip"
    
    cd /tmp
    wget -O chromedriver.zip "$CHROMEDRIVER_URL"
    unzip -o chromedriver.zip
    
    # 安装到系统路径
    sudo mv chromedriver /usr/local/bin/
    sudo chmod +x /usr/local/bin/chromedriver
    
    # 验证安装
    INSTALLED_VERSION=$(/usr/local/bin/chromedriver --version)
    print_success "ChromeDriver安装完成: $INSTALLED_VERSION"
    
    # 清理临时文件
    rm -f /tmp/chromedriver.zip
}

# 安装项目依赖
install_project_deps() {
    print_info "创建Python虚拟环境..."
    
    # 创建虚拟环境
    python3 -m venv venv
    source venv/bin/activate
    
    # 升级pip
    pip install --upgrade pip
    
    # 安装项目依赖
    if [ -f "requirements.txt" ]; then
        print_info "安装项目依赖..."
        pip install -r requirements.txt
        print_success "项目依赖安装完成"
    else
        print_warning "未找到requirements.txt文件"
    fi
}

# 配置环境变量
setup_env() {
    print_info "配置环境变量..."
    
    # 复制环境配置文件
    if [ -f "env_example" ] && [ ! -f ".env" ]; then
        cp env_example .env
        
        # 更新Chrome和ChromeDriver路径
        sed -i 's|^CHROME_PATH=.*|CHROME_PATH="/usr/bin/google-chrome"|' .env
        sed -i 's|^CHROMEDRIVER_PATH=.*|CHROMEDRIVER_PATH="/usr/local/bin/chromedriver"|' .env
        
        print_success "环境配置文件创建完成"
        print_info "请根据需要编辑 .env 文件"
    fi
}

# 创建必要目录
create_directories() {
    print_info "创建必要目录..."
    
    mkdir -p data/images
    mkdir -p logs
    
    # 设置权限
    chmod 755 data
    chmod 755 data/images
    chmod 755 logs
    
    print_success "目录创建完成"
}

# 运行测试
run_tests() {
    print_info "运行环境测试..."
    
    # 激活虚拟环境
    source venv/bin/activate
    
    # 测试Python导入
    python -c "
import sys
print(f'Python版本: {sys.version}')

try:
    import selenium
    print(f'Selenium版本: {selenium.__version__}')
except ImportError as e:
    print(f'Selenium导入失败: {e}')
    
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    driver = webdriver.Chrome(options=options)
    driver.get('https://www.google.com')
    print('Chrome浏览器测试成功')
    driver.quit()
    
except Exception as e:
    print(f'Chrome浏览器测试失败: {e}')
"
    
    print_success "环境测试完成"
}

# 显示完成信息
show_completion() {
    print_success "🎉 Ubuntu环境配置完成！"
    echo ""
    print_info "下一步操作："
    echo "1. 激活虚拟环境: source venv/bin/activate"
    echo "2. 编辑配置文件: vim .env"
    echo "3. 测试连接: python main.py test --url 'https://pd.qq.com/s/example'"
    echo "4. 启动MCP服务器: python run_mcp_server.py"
    echo ""
    print_info "项目路径: $(pwd)"
    print_info "Chrome路径: /usr/bin/google-chrome"
    print_info "ChromeDriver路径: /usr/local/bin/chromedriver"
}

# 主函数
main() {
    echo "🚀 QQ频道数据采集工具 - Ubuntu环境搭建"
    echo "================================================"
    
    check_ubuntu
    update_system
    install_basic_deps
    install_python
    install_chrome
    install_chromedriver
    install_project_deps
    setup_env
    create_directories
    run_tests
    show_completion
}

# 运行主函数
main "$@"
