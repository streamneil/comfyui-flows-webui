#!/bin/bash

# ComfyUI Wan2.2 I2V 14B 4-steps Service Startup Script

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# 切换到脚本目录
cd "$SCRIPT_DIR"

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}ComfyUI Wan2.2 I2V 14B 4-steps Service${NC}"
echo -e "${BLUE}========================================${NC}"

# Conda 环境名称
CONDA_ENV_NAME="lianhetongyuan-api-tmp"

# 检查 Conda 是否可用
if ! command -v conda &> /dev/null; then
    echo -e "${RED}错误: 未找到 Conda 环境${NC}"
    echo -e "${YELLOW}请确保已安装 Anaconda 或 Miniconda${NC}"
    exit 1
fi

echo -e "${GREEN}✓ 检测到 Conda: $(which conda)${NC}"

# 检查虚拟环境是否存在
echo -e "${BLUE}检查 Conda 虚拟环境...${NC}"
if conda env list | grep -q "^${CONDA_ENV_NAME} "; then
    echo -e "${GREEN}✓ 虚拟环境 '${CONDA_ENV_NAME}' 已存在${NC}"
else
    echo -e "${YELLOW}虚拟环境 '${CONDA_ENV_NAME}' 不存在，正在创建...${NC}"
    conda create -n ${CONDA_ENV_NAME} python=3.10 -y
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ 虚拟环境创建成功${NC}"
    else
        echo -e "${RED}错误: 虚拟环境创建失败${NC}"
        exit 1
    fi
fi

# 激活虚拟环境
echo -e "${BLUE}激活虚拟环境 '${CONDA_ENV_NAME}'...${NC}"
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate ${CONDA_ENV_NAME}

if [ $? -ne 0 ]; then
    echo -e "${RED}错误: 无法激活虚拟环境${NC}"
    exit 1
fi

echo -e "${GREEN}✓ 虚拟环境已激活${NC}"
echo -e "${YELLOW}使用 Python: $(which python)${NC}"
echo -e "${YELLOW}Python 版本: $(python --version)${NC}"

# 检查并安装依赖包
REQUIREMENTS_FILE="$SCRIPT_DIR/requirements.txt"
if [ -f "$REQUIREMENTS_FILE" ]; then
    echo -e "${BLUE}检查依赖包...${NC}"
    python -c "import fastapi, uvicorn, httpx, pydantic" 2>/dev/null
    if [ $? -ne 0 ]; then
        echo -e "${YELLOW}正在安装依赖包...${NC}"
        pip install -r "$REQUIREMENTS_FILE"
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ 依赖包安装成功${NC}"
        else
            echo -e "${RED}错误: 依赖包安装失败${NC}"
            exit 1
        fi
    else
        echo -e "${GREEN}✓ 依赖包检查通过${NC}"
    fi
else
    echo -e "${YELLOW}警告: 未找到 requirements.txt 文件${NC}"
fi

# 检查工作流文件
WORKFLOW_FILE="$SCRIPT_DIR/workflows/wan2.2_i2v_14b_4.json"
if [ ! -f "$WORKFLOW_FILE" ]; then
    echo -e "${RED}错误: 工作流文件不存在: $WORKFLOW_FILE${NC}"
    exit 1
fi
echo -e "${GREEN}✓ 工作流文件检查通过${NC}"

# 检查端口是否被占用
PORT=5014
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo -e "${YELLOW}警告: 端口 $PORT 已被占用${NC}"
    PID=$(lsof -Pi :$PORT -sTCP:LISTEN -t)
    echo -e "${YELLOW}占用进程 PID: $PID${NC}"
    read -p "是否终止该进程并继续? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        kill -9 $PID
        echo -e "${GREEN}已终止进程 $PID${NC}"
        sleep 1
    else
        exit 1
    fi
fi

# 启动服务
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}正在启动服务...${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "${YELLOW}服务地址: http://0.0.0.0:5014${NC}"
echo -e "${YELLOW}API 文档: http://0.0.0.0:5014/docs${NC}"
echo -e "${YELLOW}健康检查: http://0.0.0.0:5014/health${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "${YELLOW}按 Ctrl+C 停止服务${NC}"
echo -e "${BLUE}========================================${NC}"
echo

# 启动服务（使用虚拟环境中的 Python）
nohup python wan22_i2v_14b_4.py > log.txt 2>&1 &

