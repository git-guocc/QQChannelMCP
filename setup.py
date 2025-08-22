"""
QQ频道数据采集工具安装脚本
"""

from setuptools import setup, find_packages
from pathlib import Path

# 读取README文件
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# 读取requirements文件
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    requirements = requirements_file.read_text().strip().split('\n')
    requirements = [req.strip() for req in requirements if req.strip() and not req.startswith('#')]

setup(
    name="qq-channel-collector",
    version="1.0.0",
    description="QQ频道数据采集工具，支持MCP协议与AI客户端集成",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="QQ Channel Collector Team",
    author_email="",
    url="https://github.com/your-username/qq-channel-collector",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "qq-channel-collector=main:main",
            "qqcc=main:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    keywords="qq channel data collection mcp ai automation",
    project_urls={
        "Bug Reports": "https://github.com/your-username/qq-channel-collector/issues",
        "Source": "https://github.com/your-username/qq-channel-collector",
        "Documentation": "https://github.com/your-username/qq-channel-collector/blob/main/README.md",
    },
)
