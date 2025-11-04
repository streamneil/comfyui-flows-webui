# ComfyUI API 服务总览

本项目提供两个基于 FastAPI 的 ComfyUI 工作流服务：

## 📦 服务列表

### 1. 图片生成服务 (Image Generation)

**端口**: 8000
**文档**: [README.md](README.md) | [QUICKSTART.md](QUICKSTART.md)

**功能**:
- 根据文本提示词生成图片
- 基于 Qwen Image 模型
- 支持自定义采样参数、图片尺寸

**启动**:
```bash
./start_server.sh
# 或
python comfyui_api_server.py
```

**测试**:
```bash
python test_api.py
```

**主要接口**:
- `POST /api/generate` - 异步生成图片
- `POST /api/generate_sync` - 同步生成图片
- `GET /api/status/{prompt_id}` - 查询状态

---

### 2. 图生视频服务 (Image to Video)

**端口**: 8001
**文档**: [IMAGE2VIDEO_README.md](IMAGE2VIDEO_README.md) | [IMAGE2VIDEO_QUICKSTART.md](IMAGE2VIDEO_QUICKSTART.md)

**功能**:
- 上传图片转换为动态视频
- 基于 WAN 2.2 I2V 模型
- 支持自定义视频参数（分辨率、帧数、帧率）
- 输出 WEBP 和 WEBM 两种格式

**启动**:
```bash
./start_image2video_server.sh
# 或
python image2video_api_server.py
```

**测试**:
```bash
python test_image2video.py
```

**主要接口**:
- `POST /api/upload_and_generate` - 上传图片并生成视频
- `POST /api/generate` - 使用已存在的图片生成视频
- `POST /api/upload_and_generate_sync` - 同步生成视频
- `GET /api/status/{prompt_id}` - 查询状态

---

## 🚀 快速开始

### 安装依赖

```bash
# 创建 conda 环境（推荐）
conda create -n comfyui-api python=3.10
conda activate comfyui-api

# 安装依赖
pip install -r requirements.txt
```

### 同时启动两个服务

```bash
# 终端 1: 图片生成服务
conda activate comfyui-api
./start_server.sh

# 终端 2: 图生视频服务
conda activate comfyui-api
./start_image2video_server.sh
```

### 访问 API 文档

- 图片生成: http://localhost:8000/docs
- 图生视频: http://localhost:8001/docs

---

## 📊 服务对比

| 特性 | 图片生成 | 图生视频 |
|------|---------|---------|
| **端口** | 8000 | 8001 |
| **输入** | 文本提示词 | 图片 + 文本提示词 |
| **输出** | 图片 (PNG) | 视频 (WEBP/WEBM) |
| **生成时间** | 30秒 - 2分钟 | 5分钟 - 15分钟 |
| **模型** | Qwen Image | WAN 2.2 I2V (14B) |
| **显存需求** | 约 8GB | 约 16GB+ |
| **适用场景** | AI 绘画、概念图 | 动态视频、动画 |

---

## 📁 项目结构

```
comfyui-flows-webui/
├── # 图片生成服务
├── L3_Qwen_Image.json                    # 图片生成工作流模板
├── comfyui_api_server.py                 # 图片生成服务
├── test_api.py                           # 图片生成测试
├── start_server.sh                       # 图片生成启动脚本
├── README.md                             # 图片生成完整文档
├── QUICKSTART.md                         # 图片生成快速指南
│
├── # 图生视频服务
├── Image_2_Video_KSampler_Advanced.json  # 图生视频工作流模板
├── image2video_api_server.py             # 图生视频服务
├── test_image2video.py                   # 图生视频测试
├── start_image2video_server.sh           # 图生视频启动脚本
├── IMAGE2VIDEO_README.md                 # 图生视频完整文档
├── IMAGE2VIDEO_QUICKSTART.md            # 图生视频快速指南
│
├── # 通用文档
├── SERVICES_OVERVIEW.md                  # 本文档（服务总览）
├── TROUBLESHOOTING.md                    # 故障排查指南
├── requirements.txt                      # Python 依赖
└── README.md                             # 项目主文档
```

---

## 🔧 配置说明

两个服务都连接到同一个 ComfyUI 后端：

```python
COMFYUI_BASE_URL = "http://60.169.65.100:5000"
```

如需修改，请编辑对应的服务文件：
- 图片生成: `comfyui_api_server.py`
- 图生视频: `image2video_api_server.py`

---

## 💡 使用建议

### 场景 1: 创作工作流

**从文本到动态视频**：

1. 使用**图片生成服务**根据提示词生成静态图片
2. 下载生成的图片
3. 使用**图生视频服务**将图片转换为动态视频

示例：
```bash
# 步骤 1: 生成人物肖像
curl -X POST "http://localhost:8000/api/generate" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "A beautiful young woman, portrait, soft lighting"}'

# 获取 prompt_id 并查询结果
curl "http://localhost:8000/api/status/{prompt_id}"

# 步骤 2: 将图片转换为视频
curl -X POST "http://localhost:8001/api/upload_and_generate" \
  -F "image=@downloaded_image.png" \
  -F "prompt=She slowly smiles and tucks her hair behind her ear"
```

### 场景 2: 批量处理

**并行处理多个任务**：

```python
import requests
import asyncio

# 提交多个图片生成任务
async def generate_images(prompts):
    tasks = []
    for prompt in prompts:
        task = requests.post(
            "http://localhost:8000/api/generate",
            json={"prompt": prompt}
        )
        tasks.append(task)
    return tasks

# 提交多个视频生成任务
async def generate_videos(images):
    tasks = []
    for image_path in images:
        with open(image_path, 'rb') as f:
            files = {'image': f}
            data = {'prompt': 'Natural movement, cinematic'}
            task = requests.post(
                "http://localhost:8001/api/upload_and_generate",
                files=files,
                data=data
            )
            tasks.append(task)
    return tasks
```

### 场景 3: Web 应用集成

将两个服务集成到 Web 应用中：

```javascript
// 前端调用示例
class ComfyUIClient {
  constructor() {
    this.imageGenURL = 'http://localhost:8000';
    this.videoGenURL = 'http://localhost:8001';
  }

  async generateImage(prompt) {
    const response = await fetch(`${this.imageGenURL}/api/generate`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({prompt})
    });
    return response.json();
  }

  async generateVideo(imageFile, prompt) {
    const formData = new FormData();
    formData.append('image', imageFile);
    formData.append('prompt', prompt);

    const response = await fetch(`${this.videoGenURL}/api/upload_and_generate`, {
      method: 'POST',
      body: formData
    });
    return response.json();
  }

  async checkStatus(promptId, service = 'image') {
    const baseURL = service === 'image' ? this.imageGenURL : this.videoGenURL;
    const response = await fetch(`${baseURL}/api/status/${promptId}`);
    return response.json();
  }
}

// 使用
const client = new ComfyUIClient();

// 生成图片
const imageResult = await client.generateImage('A cat drinking coffee');
console.log('Image task:', imageResult.prompt_id);

// 生成视频
const videoResult = await client.generateVideo(imageFile, 'Cat waves its tail');
console.log('Video task:', videoResult.prompt_id);
```

---

## ⚠️ 注意事项

### 资源管理

1. **GPU 显存**:
   - 图片生成: 约 8GB
   - 图生视频: 约 16GB+
   - 同时运行需要更多显存

2. **队列管理**:
   - ComfyUI 会依次处理任务
   - 避免同时提交过多任务
   - 监控队列状态

3. **存储空间**:
   - 生成的文件会占用磁盘空间
   - 定期清理 ComfyUI 输出目录
   - 及时下载重要文件

### 性能优化

1. **图片生成优化**:
   - 使用适当的采样步数（20-25）
   - 合理设置图片尺寸
   - 使用异步接口避免阻塞

2. **视频生成优化**:
   - 从小参数开始测试
   - 逐步增加视频长度
   - 预估生成时间并设置合理的超时

3. **并发控制**:
   - 避免同时提交大量任务
   - 使用队列系统管理请求
   - 实现重试机制

---

## 🔍 健康检查

快速检查两个服务的状态：

```bash
# 图片生成服务
curl http://localhost:8000/health

# 图生视频服务
curl http://localhost:8001/health

# 或者一次性检查
echo "=== 图片生成服务 ===" && \
curl -s http://localhost:8000/health | jq && \
echo -e "\n=== 图生视频服务 ===" && \
curl -s http://localhost:8001/health | jq
```

预期输出：
```json
{
  "status": "healthy",
  "comfyui_status": "connected"
}
```

---

## 📚 相关文档

### 图片生成服务
- [README.md](README.md) - 完整文档
- [QUICKSTART.md](QUICKSTART.md) - 快速开始

### 图生视频服务
- [IMAGE2VIDEO_README.md](IMAGE2VIDEO_README.md) - 完整文档
- [IMAGE2VIDEO_QUICKSTART.md](IMAGE2VIDEO_QUICKSTART.md) - 快速开始

### 通用文档
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - 故障排查

---

## 🆘 获取帮助

如果遇到问题：

1. **查看日志**: 检查服务终端的输出
2. **健康检查**: 使用 `/health` 接口
3. **API 文档**: 访问 `/docs` 查看接口详情
4. **故障排查**: 查看 `TROUBLESHOOTING.md`
5. **ComfyUI 状态**: 直接访问 ComfyUI 界面检查

---

## 📝 版本信息

- **版本**: 1.0.0
- **FastAPI**: 0.104.1
- **Python**: 3.10+
- **ComfyUI**: 需要支持 Qwen Image 和 WAN 2.2 I2V 模型

---

## 📄 许可证

MIT License

---

**祝使用愉快！** 🎨🎬
