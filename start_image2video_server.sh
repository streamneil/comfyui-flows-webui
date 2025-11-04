#!/bin/bash

# ComfyUI Image to Video API 服务启动脚本

echo "=========================================="
echo "ComfyUI Image to Video API 启动脚本"
echo "=========================================="

# 清除所有代理环境变量
echo "清除代理环境变量..."
unset HTTP_PROXY
unset HTTPS_PROXY
unset ALL_PROXY
unset http_proxy
unset https_proxy
unset all_proxy
unset SOCKS_PROXY
unset socks_proxy

echo "✓ 代理环境变量已清除"

# 检查 Python 环境
echo ""
echo "检查 Python 环境..."
python --version
echo ""

# 检查必需文件
echo "检查必需文件..."
if [ ! -f "Image_2_Video_KSampler_Advanced.json" ]; then
    echo "❌ 错误: 找不到 Image_2_Video_KSampler_Advanced.json"
    exit 1
fi
echo "✓ 工作流模板文件存在"

if [ ! -f "image2video_api_server.py" ]; then
    echo "❌ 错误: 找不到 image2video_api_server.py"
    exit 1
fi
echo "✓ 服务主文件存在"

# 启动服务
echo ""
echo "=========================================="
echo "启动图生视频服务..."
echo "服务端口: 8001"
echo "=========================================="
echo ""

# 使用 exec 替换当前进程
exec python image2video_api_server.py
