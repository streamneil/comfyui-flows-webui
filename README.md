# ComfyUI Flows WebUI

FastAPI-based web services for ComfyUI workflows, featuring Wan2.2 Image-to-Video generation and more.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

## 🌟 Features

- **Multiple Workflow Support**: Modular architecture for different ComfyUI workflows
- **Wan2.2 I2V 14B**: Fast 4-step image-to-video generation service
- **Async & Sync APIs**: Choose between immediate results or background processing
- **REST API**: Clean, well-documented FastAPI endpoints
- **Systemd Integration**: Production-ready service management with auto-restart
- **Health Monitoring**: Built-in health checks and status queries
- **CORS Support**: Ready for web application integration
- **Comprehensive Testing**: Includes test scripts and documentation

## 📦 Services

### 1. Wan2.2 I2V 14B (4-steps) Service

Fast image-to-video generation using the Wan2.2-I2V-A14B-4steps model.

- **Port**: 5014
- **Workflow**: `workflows/wan2.2_i2v_14b_4.json`
- **Model**: Wan2.2-I2V-A14B-4steps
- **Speed**: ~5-10 minutes for 1280x720, 81 frames

**Features:**
- 4-step optimized generation
- Dual-stage sampling (high/low noise)
- Customizable resolution (512-1920px)
- Variable frame length (16-240 frames)
- Adjustable FPS (8-60)

### 2. Image2Video Service

General-purpose image-to-video service.

- **Port**: 8001
- **Workflow**: `workflows/Image_2_Video_KSampler_Advanced.json`

### 3. ComfyUI API Server

Base ComfyUI workflow execution service.

## 🚀 Quick Start

### Prerequisites

```bash
# Python 3.8+
python3 --version

# Install dependencies
pip install -r requirements.txt
```

### Required Dependencies

```
fastapi>=0.100.0
uvicorn>=0.23.0
httpx>=0.24.0
pydantic>=2.0.0
python-multipart>=0.0.6
```

### Starting Services

#### Wan2.2 I2V Service (Recommended for Fast Generation)

```bash
./start_wan22_i2v_14b_4_service.sh
```

Service will be available at:
- API: http://localhost:5014
- Docs: http://localhost:5014/docs

#### Image2Video Service

```bash
./start_image2video_server.sh
```

### Production Deployment with Systemd

For production servers, install as a systemd service for automatic startup and management:

```bash
# Install service
./install_service.sh

# Manage service
sudo systemctl start comfyui-flows-webui
sudo systemctl stop comfyui-flows-webui
sudo systemctl restart comfyui-flows-webui
sudo systemctl status comfyui-flows-webui

# Enable auto-start on boot
sudo systemctl enable comfyui-flows-webui

# View logs
sudo journalctl -u comfyui-flows-webui -f
```

See [SYSTEMD_SERVICE.md](SYSTEMD_SERVICE.md) for complete systemd deployment guide.

## 📖 API Usage

### Upload Image and Generate Video

```bash
curl -X POST "http://localhost:5014/api/upload_and_generate" \
  -F "image=@your_image.jpg" \
  -F "prompt=A happy girl smiling, natural lighting, warm atmosphere" \
  -F "width=1280" \
  -F "height=720" \
  -F "length=81" \
  -F "steps=4" \
  -F "cfg=1.0" \
  -F "fps=16"
```

**Response:**
```json
{
  "prompt_id": "abc123-def456",
  "status": "submitted",
  "message": "Task submitted successfully"
}
```

### Check Task Status

```bash
curl "http://localhost:5014/api/status/abc123-def456"
```

**Response (Completed):**
```json
{
  "prompt_id": "abc123-def456",
  "status": "completed",
  "videos": [
    {
      "filename": "wan2.2_i2v_00001.mp4",
      "format": "mp4",
      "url": "http://your-comfyui-server/view?filename=..."
    }
  ]
}
```

### Synchronous Generation (Wait for Result)

```bash
curl -X POST "http://localhost:5014/api/upload_and_generate_sync" \
  -F "image=@your_image.jpg" \
  -F "prompt=Your prompt here" \
  -F "timeout=600"
```

## 🧪 Testing

### Method 1: Comprehensive Python Test

```bash
python3 test_wan22_i2v_14b_4_service.py
```

Features:
- ✅ Service health check
- ✅ Image upload
- ✅ Task submission
- ✅ Status polling
- ✅ Result verification

### Method 2: Quick Shell Test

```bash
./quick_test_wan22.sh ~/path/to/image.jpg
```

### Method 3: Manual Testing

See [TEST_GUIDE.md](TEST_GUIDE.md) for detailed testing instructions.

## 📁 Project Structure

```
comfyui-flows-webui/
├── README.md                           # This file
├── requirements.txt                    # Python dependencies
├── .gitignore                         # Git ignore rules
│
├── Services/
│   ├── wan22_i2v_14b_4.py            # Wan2.2 I2V service (Port 5014)
│   ├── image2video_api_server.py     # Image2Video service (Port 8001)
│   └── comfyui_api_server.py         # Base ComfyUI service
│
├── Startup Scripts/
│   ├── start_wan22_i2v_14b_4_service.sh   # Start Wan2.2 service
│   ├── start_image2video_server.sh        # Start Image2Video service
│   ├── install_service.sh                 # Install systemd service
│   ├── uninstall_service.sh               # Uninstall systemd service
│   └── comfyui-flows-webui.service.template  # Systemd template
│
├── Testing/
│   ├── test_wan22_i2v_14b_4_service.py    # Comprehensive test
│   ├── quick_test_wan22.sh                # Quick test script
│   ├── test_image2video.py                # Image2Video tests
│   └── test_api.py                        # General API tests
│
├── Workflows/
│   ├── wan2.2_i2v_14b_4.json         # Wan2.2 workflow
│   └── Image_2_Video_KSampler_Advanced.json
│
└── Documentation/
    ├── WAN22_SERVICE_README.md       # Wan2.2 service docs
    ├── TEST_GUIDE.md                 # Testing guide
    ├── SERVICES_OVERVIEW.md          # All services overview
    ├── TROUBLESHOOTING.md            # Troubleshooting guide
    └── SYSTEMD_SERVICE.md            # Systemd deployment guide
```

## ⚙️ Configuration

### ComfyUI Server

Update the `COMFYUI_BASE_URL` in service files:

```python
COMFYUI_BASE_URL = "http://your-comfyui-server:port"
```

### Service Ports

- **Wan2.2 I2V**: 5014
- **Image2Video**: 8001
- **ComfyUI API**: Custom

Modify ports in the service files or startup scripts as needed.

## 🎨 Parameters Guide

### Wan2.2 I2V Recommended Settings

```python
{
    "steps": 4,          # Optimized for 4-step generation
    "cfg": 1.0,          # Recommended CFG value
    "width": 1280,       # Default width
    "height": 720,       # Default height
    "length": 81,        # ~5 seconds @ 16fps
    "fps": 16            # Standard frame rate
}
```

### Custom Parameters

- **Resolution**: 512-1920px (higher = more VRAM)
- **Length**: 16-240 frames (longer = more time)
- **Steps**: 4 recommended (pre-optimized)
- **CFG**: 1.0 recommended (higher may oversaturate)

## 📊 Performance

### Wan2.2 I2V 14B (4-steps)

- **Hardware**: RTX 4090 24GB
- **Resolution**: 1280x720
- **Frames**: 81 (5 seconds)
- **Generation Time**: 5-10 minutes
- **Quality**: High, optimized for speed

## 🔧 Troubleshooting

### Service Won't Start

```bash
# Check if port is in use
lsof -i :5014

# Kill process if needed
kill -9 <PID>
```

### ComfyUI Connection Failed

1. Verify ComfyUI is running
2. Check `COMFYUI_BASE_URL` in service file
3. Test connection: `curl http://your-comfyui-server/api/queue`

### Task Status Shows "Unknown"

- Check ComfyUI server logs
- Verify all required models are installed
- Ensure custom nodes are available

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for more details.

## 🛠️ Development

### Adding New Workflows

1. Create workflow JSON in `workflows/` directory
2. Create new service file (use `wan22_i2v_14b_4.py` as template)
3. Update `prepare_workflow()` function for your nodes
4. Create startup script
5. Add tests

### API Extensions

All services use FastAPI. To add endpoints:

```python
@app.post("/api/your_endpoint")
async def your_endpoint(params):
    # Your logic here
    return {"result": "success"}
```

## 📝 API Documentation

Each service provides interactive API documentation:

- Wan2.2 I2V: http://localhost:5014/docs
- Image2Video: http://localhost:8001/docs

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details

## 🙏 Acknowledgments

- ComfyUI for the amazing workflow system
- Wan2.2 team for the image-to-video models
- FastAPI for the excellent web framework

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/streamneil/comfyui-flows-webui/issues)
- **Documentation**: See `docs/` directory
- **Testing Guide**: [TEST_GUIDE.md](TEST_GUIDE.md)

## 🔗 Links

- [ComfyUI](https://github.com/comfyanonymous/ComfyUI)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Wan2.2 Model](https://huggingface.co/Lightricks/LTX-Video)

---

**Note**: This project requires a running ComfyUI instance with appropriate models and custom nodes installed. Make sure your ComfyUI setup supports the workflows you want to use.

## 🚦 Status

- ✅ Wan2.2 I2V 14B Service - Production Ready
- ✅ Image2Video Service - Stable
- ✅ Testing Suite - Complete
- 🚧 Additional Workflows - In Progress

---

Made with ❤️ using [Claude Code](https://claude.com/claude-code)
