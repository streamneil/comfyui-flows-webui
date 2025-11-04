# Wan2.2 服务测试指南

## 准备工作

### 1. 保存测试图片

请将测试图片保存到以下路径：

```bash
~/Downloads/t-wan22i2v14b4.jpeg
```

或者使用任何其他图片路径。

### 2. 启动服务

在测试之前，请确保服务已启动：

```bash
./start_wan22_service.sh
```

服务将运行在 `http://localhost:5014`

## 测试方法

### 方法 1: 完整 Python 测试脚本（推荐）

**功能最全面，提供详细的测试报告**

```bash
# 使用默认图片路径
python3 test_wan22_service.py

# 或直接运行
./test_wan22_service.py
```

**测试内容包括：**
- ✓ 图片文件检查
- ✓ 服务健康检查
- ✓ 根路径信息获取
- ✓ 异步上传并生成视频
- ✓ 任务状态查询（自动轮询）
- ✓ 结果展示
- ○ 可选：同步生成测试

**特点：**
- 彩色输出，易于阅读
- 自动轮询任务状态直到完成
- 详细的错误信息
- 结构化的测试报告

### 方法 2: 快速 Bash 测试脚本

**快速简单，适合命令行测试**

```bash
# 使用默认图片路径
./quick_test_wan22.sh

# 使用自定义图片路径
./quick_test_wan22.sh ~/Pictures/my_photo.jpg
```

**特点：**
- 快速简单
- 适合 CI/CD 集成
- 可自定义图片路径
- 自动轮询任务状态

### 方法 3: 手动 curl 测试

**最底层的测试方法，适合调试**

#### 步骤 1: 健康检查

```bash
curl http://localhost:5014/health
```

#### 步骤 2: 上传图片并生成视频

```bash
curl -X POST "http://localhost:5014/api/upload_and_generate" \
  -F "image=@~/Downloads/t-wan22i2v14b4.jpeg" \
  -F "prompt=开心的女孩微笑着，自然的光线，温馨的氛围，高质量" \
  -F "width=1280" \
  -F "height=720" \
  -F "length=81" \
  -F "steps=4" \
  -F "cfg=1.0" \
  -F "fps=16"
```

这会返回一个 `prompt_id`，例如：

```json
{
  "prompt_id": "abc123-def456",
  "status": "submitted",
  "message": "Wan2.2 图生视频任务已提交..."
}
```

#### 步骤 3: 查询任务状态

使用返回的 `prompt_id` 查询：

```bash
curl http://localhost:5014/api/status/abc123-def456
```

重复查询直到状态变为 `completed`：

```json
{
  "prompt_id": "abc123-def456",
  "status": "completed",
  "videos": [
    {
      "filename": "wan2.2_i2v_00001.mp4",
      "url": "http://60.169.65.100:5000/cfui/view?filename=..."
    }
  ]
}
```

## 测试参数说明

### 默认测试参数

```python
{
    "prompt": "开心的女孩微笑着，自然的光线，温馨的氛围，高质量",
    "width": 1280,
    "height": 720,
    "length": 81,     # 81帧 ≈ 5秒 @ 16fps
    "steps": 4,       # 4步加速（推荐）
    "cfg": 1.0,       # CFG系数（推荐）
    "fps": 16         # 16帧率
}
```

### 自定义参数

你可以修改脚本中的参数来测试不同的配置：

**更长的视频：**
```python
"length": 161  # 161帧 ≈ 10秒 @ 16fps
```

**更高的分辨率：**
```python
"width": 1920,
"height": 1080
```

**更快的速度：**
```python
"steps": 4,    # 已经是最优配置
"cfg": 1.0     # 已经是最优配置
```

## 预期结果

### 正常完成

```
✓ 任务完成！
视频 1:
  文件名: wan2.2_i2v_00001.mp4
  格式: mp4
  URL: http://60.169.65.100:5000/cfui/view?filename=...
```

### 生成时间

- **4 步模式**: 约 5-10 分钟（取决于硬件）
- **分辨率**: 1280x720, 81 帧
- **质量**: 高质量，适合社交媒体

## 常见问题

### 1. 图片文件不存在

```
错误: 测试图片不存在: ~/Downloads/t-wan22i2v14b4.jpeg
```

**解决方法：**
- 确保图片已保存到正确路径
- 或使用自定义路径：`./quick_test_wan22.sh /path/to/your/image.jpg`

### 2. 无法连接到服务

```
无法连接到服务，请确保服务已启动
```

**解决方法：**
```bash
./start_wan22_service.sh
```

### 3. 任务超时

```
任务超时（600秒）
```

**可能原因：**
- ComfyUI 服务负载过高
- 网络连接问题
- 模型文件缺失

**解决方法：**
- 检查 ComfyUI 服务状态
- 增加超时时间
- 查看 ComfyUI 日志

### 4. 任务失败

```
任务失败: error message
```

**解决方法：**
- 查看详细错误信息
- 检查 ComfyUI 日志
- 确认所有模型和节点已安装

## 性能基准

### 参考配置

- **硬件**: RTX 4090 24GB
- **分辨率**: 1280x720
- **帧数**: 81 帧
- **步数**: 4 步

### 预期时间

- **提交任务**: < 5 秒
- **图片上传**: < 2 秒
- **视频生成**: 5-10 分钟
- **总耗时**: 约 10 分钟

## 高级测试

### 修改提示词

编辑 `test_wan22_service.py` 中的 `TEST_PARAMS`：

```python
TEST_PARAMS = {
    "prompt": "你的自定义提示词",
    # ... 其他参数
}
```

### 批量测试

创建一个循环脚本测试多个图片：

```bash
for img in ~/Downloads/*.jpg; do
    echo "测试: $img"
    ./quick_test_wan22.sh "$img"
done
```

### 压力测试

同时提交多个任务：

```bash
for i in {1..5}; do
    python3 test_wan22_service.py &
done
wait
```

## API 文档

访问交互式 API 文档：

```
http://localhost:5014/docs
```

在文档中可以：
- 查看所有端点
- 在线测试 API
- 查看请求/响应格式
- 下载 OpenAPI 规范

## 总结

- **推荐使用**: `python3 test_wan22_service.py` 进行完整测试
- **快速测试**: `./quick_test_wan22.sh`
- **调试问题**: 使用 curl 手动测试
- **查看文档**: http://localhost:5014/docs

祝测试顺利！
