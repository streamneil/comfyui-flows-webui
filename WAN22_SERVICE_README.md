# Wan2.2 I2V 14B 4-Steps API 服务

基于 ComfyUI Wan2.2 模型的图生视频 FastAPI 服务

## 服务信息

- **端口**: 5014
- **模型**: Wan2.2-I2V-A14B-4steps (4步加速版)
- **工作流**: workflows/wan2.2_i2v_14b_4.json

## 快速启动

### 方式 1: 使用启动脚本（推荐）

```bash
./start_wan22_service.sh
```

### 方式 2: 直接运行 Python

```bash
python3 wan22_i2v_14b_4.py
```

## 服务地址

- **API 服务**: http://0.0.0.0:5014
- **API 文档**: http://0.0.0.0:5014/docs
- **健康检查**: http://0.0.0.0:5014/health

## API 端点

### 1. 上传图片并生成视频（异步）

**POST** `/api/upload_and_generate`

上传图片文件，提交生成任务，返回 prompt_id 用于查询状态。

**参数**:
- `image`: 图片文件（必填）
- `prompt`: 正向提示词（必填）
- `width`: 视频宽度，默认 1280
- `height`: 视频高度，默认 720
- `length`: 视频帧数，默认 81
- `steps`: 采样步数，推荐 4，默认 4
- `cfg`: CFG 系数，推荐 1.0，默认 1.0
- `fps`: 帧率，默认 16
- `noise_seed`: 随机种子（可选）

**示例**:

```bash
curl -X POST "http://localhost:5014/api/upload_and_generate" \
  -F "image=@test.jpg" \
  -F "prompt=开心的舞蹈，背景是美丽的花园" \
  -F "width=1280" \
  -F "height=720" \
  -F "length=81" \
  -F "steps=4" \
  -F "cfg=1.0" \
  -F "fps=16"
```

**响应**:

```json
{
  "prompt_id": "12345-abcde",
  "status": "submitted",
  "message": "Wan2.2 图生视频任务已提交，请使用 prompt_id 查询生成状态"
}
```

### 2. 使用已有图片文件名生成视频

**POST** `/api/generate`

使用已经上传到 ComfyUI 服务器的图片文件名生成视频。

**请求体**:

```json
{
  "image_filename": "example.jpg",
  "prompt": "开心的舞蹈，背景是美丽的花园",
  "width": 1280,
  "height": 720,
  "length": 81,
  "steps": 4,
  "cfg": 1.0,
  "fps": 16
}
```

### 3. 查询任务状态

**GET** `/api/status/{prompt_id}`

查询视频生成任务的状态和结果。

**示例**:

```bash
curl "http://localhost:5014/api/status/12345-abcde"
```

**响应（进行中）**:

```json
{
  "prompt_id": "12345-abcde",
  "status": "running",
  "progress": 50
}
```

**响应（完成）**:

```json
{
  "prompt_id": "12345-abcde",
  "status": "completed",
  "videos": [
    {
      "filename": "wan2.2_i2v_00001.mp4",
      "subfolder": "wan2.2/i2v",
      "type": "output",
      "format": "mp4",
      "url": "http://60.169.65.100:5000/cfui/view?filename=wan2.2_i2v_00001.mp4&subfolder=wan2.2/i2v&type=output"
    }
  ]
}
```

### 4. 同步生成视频（等待完成）

**POST** `/api/upload_and_generate_sync`

上传图片后等待视频生成完成，直接返回结果。适合需要立即获取结果的场景。

**参数**: 与异步接口相同，额外增加：
- `timeout`: 超时时间（秒），默认 600

**注意**: 视频生成可能需要较长时间，建议设置合适的超时时间。

## 参数说明

### 推荐参数

Wan2.2-I2V-A14B-4steps 模型针对快速生成进行了优化：

- **steps**: 4（推荐值，已经过优化的步数）
- **cfg**: 1.0（推荐值，更高的值可能导致过度饱和）
- **width x height**: 1280x720（默认值，支持 512-1920 范围）
- **length**: 81 帧（约 5 秒 @ 16fps）
- **fps**: 16（标准帧率）

### 高级参数调整

- **更长的视频**: 增加 `length` 参数（最大 240 帧）
- **更高清**: 增加 `width` 和 `height`（注意显存占用）
- **更流畅**: 增加 `fps` 参数（最大 60）

## 依赖要求

```bash
pip install fastapi uvicorn httpx pydantic python-multipart
```

## ComfyUI 配置

确保 ComfyUI 服务已启动，并且：

1. 已安装必要的模型文件：
   - Wan2.2-I2V-A14B-HighNoise-Q8_0.gguf
   - Wan2.2-I2V-A14B-LowNoise-Q8_0.gguf
   - umt5_xxl_fp8_e4m3fn_scaled.safetensors
   - wan_2.1_vae.safetensors

2. 已安装必要的 LoRA：
   - Wan2.2-I2V-A14B-4steps-lora-rank64-Seko-V1-high_noise_model.safetensors
   - Wan2.2-I2V-A14B-4steps-lora-rank64-Seko-V1-low_noise_model.safetensors

3. 已安装必要的自定义节点：
   - UnetLoaderGGUF
   - PathchSageAttentionKJ
   - ModelPatchTorchSettings
   - ImageResizeKJv2
   - VHS_VideoCombine

## 工作流说明

此服务使用两阶段采样策略：

1. **第一阶段（High Noise）**: 使用高噪声模型生成粗略结构（step 0-2）
2. **第二阶段（Low Noise）**: 使用低噪声模型细化细节（step 2-4）

这种策略在保证质量的同时，将采样步数降低到仅需 4 步。

## 故障排查

### 端口被占用

```bash
# 查看占用端口的进程
lsof -i :5014

# 终止进程
kill -9 <PID>
```

### ComfyUI 连接失败

检查 `wan22_i2v_14b_4.py` 中的 `COMFYUI_BASE_URL` 配置是否正确：

```python
COMFYUI_BASE_URL = "http://60.169.65.100:5000"
```

### 工作流执行失败

1. 检查 ComfyUI 是否已安装所有必要的模型和节点
2. 查看 ComfyUI 日志获取详细错误信息
3. 使用 `/health` 端点检查服务连接状态

## 性能优化

- 使用 4 步采样已经过优化，无需增加步数
- 如果显存不足，可以降低分辨率
- 可以通过调整 `length` 参数控制视频长度来平衡质量和速度

## 版本信息

- **服务版本**: 1.0.0
- **模型**: Wan2.2-I2V-A14B-4steps
- **FastAPI**: ^0.100.0
- **Python**: >=3.8

## 技术支持

如有问题，请检查：
1. ComfyUI 服务是否正常运行
2. 所有依赖包是否正确安装
3. 工作流文件是否完整
4. 端口是否被占用
