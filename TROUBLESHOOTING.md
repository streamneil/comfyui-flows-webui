# 故障排查指南

## 问题：SOCKS 代理错误

### 错误信息
```
Using SOCKS proxy, but the 'socksio' package is not installed.
```

### 原因
系统中配置了代理（通过环境变量 `HTTP_PROXY`、`HTTPS_PROXY` 或 `ALL_PROXY`），但 httpx 缺少 SOCKS 代理支持。

### 解决方案（任选其一）

#### 方案 1：重启服务（已修复）
代码已更新为禁用代理，直接重启服务即可：

```bash
# 停止当前服务 (Ctrl+C)
# 重新启动
python comfyui_api_server.py
```

#### 方案 2：临时禁用代理环境变量
```bash
# 在启动服务前清除代理环境变量
unset HTTP_PROXY
unset HTTPS_PROXY
unset ALL_PROXY
unset http_proxy
unset https_proxy
unset all_proxy

# 然后启动服务
python comfyui_api_server.py
```

#### 方案 3：安装 SOCKS 支持（如果需要代理）
```bash
pip install httpx[socks]
# 或
pip install -r requirements.txt --upgrade
```

### 验证修复
```bash
curl http://localhost:8000/health
```

预期响应：
```json
{
  "status": "healthy",
  "comfyui_status": "connected"
}
```

---

## 问题：无法连接到 ComfyUI

### 错误信息
```json
{
  "status": "unhealthy",
  "comfyui_status": "disconnected",
  "error": "Connection refused"
}
```

### 检查步骤

1. **检查 ComfyUI 是否运行**
   ```bash
   curl http://60.169.65.100:5000/cfui/api/queue
   ```

2. **检查网络连接**
   ```bash
   ping 60.169.65.100
   ```

3. **检查服务配置**

   编辑 `comfyui_api_server.py`，确认 URL 配置正确：
   ```python
   COMFYUI_BASE_URL = "http://60.169.65.100:5000"
   ```

4. **测试直接访问**

   浏览器访问：http://60.169.65.100:5000/cfui/

---

## 问题：任务一直 pending

### 原因
ComfyUI 正在处理其他任务，新任务在队列中等待。

### 检查队列状态
```bash
curl http://60.169.65.100:5000/cfui/api/queue
```

### 解决方案
- 等待当前任务完成
- 或清空队列（如果确定可以取消）

---

## 问题：工作流模板未找到

### 错误信息
```
无法加载工作流模板: [Errno 2] No such file or directory
```

### 检查步骤
1. 确认 `L3_Qwen_Image.json` 文件在正确位置
   ```bash
   ls -la L3_Qwen_Image.json
   ```

2. 确认文件路径
   ```bash
   pwd
   # 应该在项目根目录
   ```

3. 如果文件在其他位置，更新代码中的路径：
   ```python
   WORKFLOW_TEMPLATE_PATH = Path("/完整/路径/到/L3_Qwen_Image.json")
   ```

---

## 问题：Conda 环境问题

### 创建新的虚拟环境
```bash
# 创建环境
conda create -n comfyui-api python=3.10

# 激活环境
conda activate comfyui-api

# 安装依赖
pip install -r requirements.txt

# 启动服务
python comfyui_api_server.py
```

### 验证环境
```bash
# 检查 Python 版本
python --version

# 检查已安装的包
pip list | grep -E "(fastapi|httpx|uvicorn)"
```

---

## 问题：端口被占用

### 错误信息
```
[ERROR] [Errno 48] Address already in use
```

### 解决方案

#### 方案 1：查找并终止占用进程
```bash
# macOS/Linux
lsof -ti:8000 | xargs kill -9

# 或查看占用进程
lsof -i:8000
```

#### 方案 2：更改端口
编辑 `comfyui_api_server.py` 最后几行：
```python
uvicorn.run(
    app,
    host="0.0.0.0",
    port=8001,  # 更改为其他端口
    log_level="info"
)
```

---

## 常见调试命令

### 检查服务状态
```bash
# 健康检查
curl http://localhost:8000/health

# 查看 API 根路径
curl http://localhost:8000/

# 访问 API 文档
open http://localhost:8000/docs
```

### 检查 ComfyUI
```bash
# 查看队列
curl http://60.169.65.100:5000/cfui/api/queue

# 查看历史
curl http://60.169.65.100:5000/cfui/api/history
```

### 查看日志
服务运行时会在终端输出详细日志，注意查看错误信息。

---

## 联系支持

如果以上方案都无法解决问题，请提供以下信息：

1. 错误的完整日志
2. Python 版本：`python --version`
3. 依赖版本：`pip list`
4. 操作系统信息
5. ComfyUI 访问测试结果

## 有用的资源

- FastAPI 文档: https://fastapi.tiangolo.com/
- httpx 文档: https://www.python-httpx.org/
- ComfyUI 文档: https://github.com/comfyanonymous/ComfyUI
