# 服务器部署快速指南

## 一键部署到服务器

### 步骤 1: 克隆代码

```bash
# SSH 到你的服务器
ssh user@your-server

# 克隆项目
git clone https://github.com/streamneil/comfyui-flows-webui.git
cd comfyui-flows-webui
```

### 步骤 2: 安装依赖

```bash
# 使用 pip
pip install -r requirements.txt

# 或使用 pip3
pip3 install -r requirements.txt
```

### 步骤 3: 配置 ComfyUI 地址

编辑 `wan22_i2v_14b_4.py`，修改 ComfyUI 服务器地址：

```bash
nano wan22_i2v_14b_4.py
```

找到并修改：

```python
COMFYUI_BASE_URL = "http://your-comfyui-server:port"
```

保存并退出（Ctrl+O, Enter, Ctrl+X）。

### 步骤 4: 安装 Systemd 服务

```bash
# 运行安装脚本
./install_service.sh
```

脚本会自动：
1. 检测 Python 环境
2. 验证依赖安装
3. 生成服务配置
4. 安装到系统
5. 询问是否启用开机自启
6. 询问是否立即启动

**全程自动化，按提示操作即可！**

### 步骤 5: 验证服务

```bash
# 检查服务状态
sudo systemctl status comfyui-flows-webui

# 测试 API
curl http://localhost:5014/health
```

预期输出：
```json
{
  "status": "healthy",
  "comfyui_status": "connected"
}
```

## 完整！🎉

服务现在已经运行在 **5014** 端口，并且：

- ✅ 开机自动启动
- ✅ 异常自动重启
- ✅ 日志自动记录
- ✅ 后台稳定运行

## 常用命令

### 服务管理

```bash
# 启动服务
sudo systemctl start comfyui-flows-webui

# 停止服务
sudo systemctl stop comfyui-flows-webui

# 重启服务
sudo systemctl restart comfyui-flows-webui

# 查看状态
sudo systemctl status comfyui-flows-webui
```

### 日志查看

```bash
# 实时日志
sudo journalctl -u comfyui-flows-webui -f

# 最近 100 行
sudo journalctl -u comfyui-flows-webui -n 100

# 今天的日志
sudo journalctl -u comfyui-flows-webui --since today
```

### 测试服务

```bash
# 健康检查
curl http://localhost:5014/health

# 查看 API 信息
curl http://localhost:5014/

# 上传图片测试
curl -X POST "http://localhost:5014/api/upload_and_generate" \
  -F "image=@test.jpg" \
  -F "prompt=测试提示词"
```

## 防火墙配置

如果需要从外部访问服务，配置防火墙：

### Ubuntu/Debian (UFW)

```bash
sudo ufw allow 5014/tcp
sudo ufw reload
```

### CentOS/RHEL (firewalld)

```bash
sudo firewall-cmd --permanent --add-port=5014/tcp
sudo firewall-cmd --reload
```

## Nginx 反向代理（可选）

如果想通过域名访问，配置 Nginx：

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:5014;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # 上传大文件支持
        client_max_body_size 100M;
    }
}
```

重载 Nginx：

```bash
sudo nginx -t
sudo systemctl reload nginx
```

## 故障排查

### 1. 服务无法启动

```bash
# 查看详细错误
sudo journalctl -u comfyui-flows-webui -n 50 --no-pager
```

### 2. 端口被占用

```bash
# 查找占用进程
sudo lsof -i :5014

# 停止旧服务
sudo systemctl stop comfyui-flows-webui
```

### 3. 权限问题

```bash
# 检查文件权限
ls -la /path/to/comfyui-flows-webui

# 修改所有者
sudo chown -R $USER:$USER /path/to/comfyui-flows-webui
```

### 4. ComfyUI 连接失败

```bash
# 测试 ComfyUI 连接
curl http://your-comfyui-server:port/api/queue

# 检查配置
grep COMFYUI_BASE_URL wan22_i2v_14b_4.py
```

## 卸载服务

如果需要卸载：

```bash
./uninstall_service.sh
```

会自动：
- 停止服务
- 禁用开机自启
- 删除服务配置
- 清理 systemd

## 更新服务

```bash
# 停止服务
sudo systemctl stop comfyui-flows-webui

# 拉取最新代码
git pull

# 安装新依赖（如有）
pip install -r requirements.txt

# 启动服务
sudo systemctl start comfyui-flows-webui
```

## 性能优化

### 1. 使用虚拟环境

```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 修改服务配置中的 Python 路径
sudo nano /etc/systemd/system/comfyui-flows-webui.service

# 将 ExecStart 改为：
# ExecStart=/path/to/venv/bin/python3 /path/to/wan22_i2v_14b_4.py

# 重载并重启
sudo systemctl daemon-reload
sudo systemctl restart comfyui-flows-webui
```

### 2. 资源限制（可选）

编辑服务文件：

```bash
sudo nano /etc/systemd/system/comfyui-flows-webui.service
```

添加资源限制：

```ini
[Service]
MemoryLimit=2G
CPUQuota=200%
```

重载：

```bash
sudo systemctl daemon-reload
sudo systemctl restart comfyui-flows-webui
```

## 监控建议

### 1. 日志监控

```bash
# 设置日志告警（例如使用 logwatch）
sudo apt install logwatch
```

### 2. 服务监控

```bash
# 使用 monit 监控服务
sudo apt install monit
```

### 3. 性能监控

```bash
# 实时查看资源使用
sudo systemctl status comfyui-flows-webui
```

## 安全建议

1. **防火墙**：只开放必要端口
2. **反向代理**：使用 Nginx + SSL
3. **认证**：添加 API 认证（自行实现）
4. **日志清理**：定期清理旧日志
5. **权限控制**：使用专用用户运行服务

## 完整部署检查清单

- [ ] 克隆代码到服务器
- [ ] 安装 Python 依赖
- [ ] 配置 ComfyUI 服务器地址
- [ ] 运行安装脚本
- [ ] 启动服务
- [ ] 测试健康检查
- [ ] 测试上传图片
- [ ] 配置防火墙（如需要）
- [ ] 配置反向代理（可选）
- [ ] 启用开机自启
- [ ] 设置日志监控

## 需要帮助？

- 查看完整文档：[SYSTEMD_SERVICE.md](SYSTEMD_SERVICE.md)
- 故障排查：[TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- GitHub Issues：https://github.com/streamneil/comfyui-flows-webui/issues
