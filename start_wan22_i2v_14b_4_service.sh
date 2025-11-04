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

# 检查 Python 环境
if command -v python3 &> /dev/null; then
    PYTHON_CMD=python3
elif command -v python &> /dev/null; then
    PYTHON_CMD=python
else
    echo -e "${RED}错误: 未找到 Python 环境${NC}"
    exit 1
fi

echo -e "${YELLOW}使用 Python: $(which $PYTHON_CMD)${NC}"
echo -e "${YELLOW}Python 版本: $($PYTHON_CMD --version)${NC}"

# 检查必要的 Python 包
echo -e "${BLUE}检查依赖包...${NC}"
$PYTHON_CMD -c "import fastapi, uvicorn, httpx, pydantic" 2>/dev/null
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}警告: 某些依赖包可能未安装${NC}"
    echo -e "${YELLOW}请运行: pip install fastapi uvicorn httpx pydantic${NC}"
    read -p "是否继续启动? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
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

# 启动服务
$PYTHON_CMD wan22_i2v_14b_4.py
