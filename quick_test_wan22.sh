#!/bin/bash

# Wan2.2 I2V 14B 快速测试脚本

# 配置
API_URL="http://localhost:5014"
IMAGE_PATH="${1:-$HOME/Downloads/t-wan22i2v14b4.jpeg}"

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Wan2.2 I2V 14B 快速测试${NC}"
echo -e "${BLUE}========================================${NC}"

# 检查图片文件
if [ ! -f "$IMAGE_PATH" ]; then
    echo -e "${RED}错误: 图片文件不存在: $IMAGE_PATH${NC}"
    echo -e "${YELLOW}使用方法: $0 <图片路径>${NC}"
    echo -e "${YELLOW}示例: $0 ~/Downloads/test.jpg${NC}"
    exit 1
fi

echo -e "${GREEN}✓ 找到测试图片: $IMAGE_PATH${NC}"

# 1. 健康检查
echo -e "\n${BLUE}1. 健康检查${NC}"
HEALTH_RESPONSE=$(curl -s "$API_URL/health")
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ 服务运行正常${NC}"
    echo "$HEALTH_RESPONSE" | python3 -m json.tool
else
    echo -e "${RED}✗ 无法连接到服务，请确保服务已启动${NC}"
    echo -e "${YELLOW}运行: ./start_wan22_service.sh${NC}"
    exit 1
fi

# 2. 提交任务
echo -e "\n${BLUE}2. 提交图生视频任务${NC}"
RESPONSE=$(curl -s -X POST "$API_URL/api/upload_and_generate" \
  -F "image=@$IMAGE_PATH" \
  -F "prompt=开心的女孩微笑着，自然的光线，温馨的氛围，高质量" \
  -F "width=1280" \
  -F "height=720" \
  -F "length=81" \
  -F "steps=4" \
  -F "cfg=1.0" \
  -F "fps=16")

if [ $? -ne 0 ]; then
    echo -e "${RED}✗ 任务提交失败${NC}"
    exit 1
fi

echo -e "${GREEN}✓ 任务提交成功${NC}"
echo "$RESPONSE" | python3 -m json.tool

# 提取 prompt_id
PROMPT_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('prompt_id', ''))")

if [ -z "$PROMPT_ID" ]; then
    echo -e "${RED}✗ 未能获取 prompt_id${NC}"
    exit 1
fi

echo -e "${YELLOW}Prompt ID: $PROMPT_ID${NC}"

# 3. 轮询状态
echo -e "\n${BLUE}3. 查询任务状态${NC}"
echo -e "${YELLOW}正在等待任务完成...${NC}"

MAX_ATTEMPTS=120
ATTEMPT=0

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    sleep 5
    ATTEMPT=$((ATTEMPT + 1))

    STATUS_RESPONSE=$(curl -s "$API_URL/api/status/$PROMPT_ID")
    STATUS=$(echo "$STATUS_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', 'unknown'))" 2>/dev/null)

    echo -e "\r第 $ATTEMPT 次查询 - 状态: $STATUS" | tr -d '\n'

    if [ "$STATUS" = "completed" ]; then
        echo ""
        echo -e "${GREEN}✓ 任务完成！${NC}"
        echo "$STATUS_RESPONSE" | python3 -m json.tool

        # 提取视频 URL
        echo -e "\n${BLUE}生成的视频:${NC}"
        echo "$STATUS_RESPONSE" | python3 -c "
import sys, json
data = json.load(sys.stdin)
videos = data.get('videos', [])
for i, video in enumerate(videos, 1):
    print(f'\n视频 {i}:')
    print(f\"  文件名: {video.get('filename')}\")
    print(f\"  格式: {video.get('format')}\")
    print(f\"  URL: {video.get('url')}\")
"
        exit 0

    elif [ "$STATUS" = "failed" ]; then
        echo ""
        echo -e "${RED}✗ 任务失败${NC}"
        echo "$STATUS_RESPONSE" | python3 -m json.tool
        exit 1

    elif [ "$STATUS" = "unknown" ]; then
        echo ""
        echo -e "${YELLOW}⚠ 未知状态，继续等待...${NC}"
    fi
done

echo ""
echo -e "${RED}✗ 任务超时（${MAX_ATTEMPTS} 次查询）${NC}"
exit 1
