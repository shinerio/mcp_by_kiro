#!/usr/bin/env python3
"""
Setup script for MCP Base64 Server

This script allows the MCP Base64 Server to be installed as a Python package,
making it easy to distribute and deploy in different environments.
"""

from setuptools import setup, find_packages
from pathlib import Path
import re

# Read the README file
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

# Read the requirements file
requirements_path = Path(__file__).parent / "requirements.txt"
if requirements_path.exists():
    with open(requirements_path, 'r', encoding='utf-8') as f:
        requirements = [
            line.strip() 
            for line in f 
            if line.strip() and not line.startswith('#')
        ]
else:
    requirements = [
        "PyYAML>=6.0",
        "psutil>=5.9.0",
        "flask>=2.3.0",
        "flask-cors>=4.0.0",
        "jsonrpc-base>=2.2.0"
    ]

# Extract version from main.py or config
version = "1.0.0"
try:
    # Try to read version from config.yaml
    import yaml
    config_path = Path(__file__).parent / "config.yaml"
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            version = config.get('server', {}).get('version', version)
except ImportError:
    pass

# Development requirements
dev_requirements = [
    "pytest>=7.4.0",
    "pytest-cov>=4.1.0",
    "pytest-asyncio>=0.21.0",
    "black>=23.0.0",
    "flake8>=6.0.0",
    "mypy>=1.5.0",
    "sphinx>=7.0.0",
    "sphinx-rtd-theme>=1.3.0"
]

setup(
    name="mcp-base64-server",
    version=version,
    author="MCP Base64 Server Team",
    author_email="team@mcp-base64-server.com",
    description="MCP server providing base64 encoding and decoding tools for AI agents",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-org/mcp-base64-server",
    project_urls={
        "Bug Reports": "https://github.com/your-org/mcp-base64-server/issues",
        "Source": "https://github.com/your-org/mcp-base64-server",
        "Documentation": "https://mcp-base64-server.readthedocs.io/",
    },
    packages=find_packages(exclude=["tests", "tests.*", "docs", "docs.*"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Internet :: WWW/HTTP :: HTTP Servers",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
    extras_require={
        "dev": dev_requirements,
        "monitoring": ["prometheus-client>=0.17.0"],
        "redis": ["redis>=4.5.0"],
        "ssl": ["cryptography>=41.0.0"],
    },
    entry_points={
        "console_scripts": [
            "mcp-base64-server=main:main",
            "mcp-base64=main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": [
            "config.yaml",
            "static/*",
            "docs/*.md",
            "deploy/*",
        ],
    },
    data_files=[
        ("config", ["config.yaml"]),
        ("static", ["static/index.html", "static/styles.css", "static/app.js"]),
    ],
    zip_safe=False,
    keywords=[
        "mcp",
        "model-context-protocol", 
        "base64",
        "encoding",
        "decoding",
        "ai-agent",
        "claude",
        "server",
        "http",
        "stdio"
    ],
    platforms=["any"],
    license="MIT",
)