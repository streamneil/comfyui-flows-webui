# Systemd Service 管理指南

本指南介绍如何将 ComfyUI Flows WebUI 作为 systemd 服务运行，实现开机自启和后台运行。

## 快速安装

### 1. 克隆项目到服务器

```bash
git clone https://github.com/streamneil/comfyui-flows-webui.git
cd comfyui-flows-webui
```

### 2. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

### 3. 运行安装脚本

```bash
chmod +x install_service.sh
./install_service.sh
```

脚本会自动：
- ✅ 检测当前用户和工作目录
- ✅ 检测 Python 环境
- ✅ 生成 systemd 服务配置
- ✅ 安装服务到系统
- ✅ 可选：启用开机自启
- ✅ 可选：立即启动服务

## 服务管理命令

### 启动服务

```bash
sudo systemctl start comfyui-flows-webui
```

### 停止服务

```bash
sudo systemctl stop comfyui-flows-webui
```

### 重启服务

```bash
sudo systemctl restart comfyui-flows-webui
```

### 查看服务状态

```bash
sudo systemctl status comfyui-flows-webui
```

输出示例：
```
● comfyui-flows-webui.service - ComfyUI Flows WebUI - Wan2.2 I2V 14B Service
     Loaded: loaded (/etc/systemd/system/comfyui-flows-webui.service; enabled)
     Active: active (running) since Mon 2025-01-06 10:00:00 UTC; 5min ago
   Main PID: 12345 (python3)
      Tasks: 5 (limit: 4915)
     Memory: 256.0M
        CPU: 2.5s
     CGroup: /system.slice/comfyui-flows-webui.service
             └─12345 /usr/bin/python3 /path/to/wan22_i2v_14b_4.py
```

### 启用开机自启

```bash
sudo systemctl enable comfyui-flows-webui
```

### 禁用开机自启

```bash
sudo systemctl disable comfyui-flows-webui
```

### 查看实时日志

```bash
sudo journalctl -u comfyui-flows-webui -f
```

### 查看最近日志

```bash
# 最近 100 行
sudo journalctl -u comfyui-flows-webui -n 100

# 最近 1 小时
sudo journalctl -u comfyui-flows-webui --since "1 hour ago"

# 今天的日志
sudo journalctl -u comfyui-flows-webui --since today
```

## 服务配置详解

### 服务文件位置

```
/etc/systemd/system/comfyui-flows-webui.service
```

### 配置文件结构

```ini
[Unit]
Description=ComfyUI Flows WebUI - Wan2.2 I2V 14B Service
After=network.target

[Service]
Type=simple
User=your-username
Group=your-group
WorkingDirectory=/path/to/comfyui-flows-webui
Environment="PATH=/path/to/python:$PATH"
ExecStart=/path/to/python3 /path/to/wan22_i2v_14b_4.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=comfyui-flows-webui

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=/path/to/comfyui-flows-webui

[Install]
WantedBy=multi-user.target
```

### 配置说明

- **Type=simple**: 简单服务类型，进程不会 fork
- **User/Group**: 运行服务的用户和组
- **WorkingDirectory**: 工作目录（项目根目录）
- **ExecStart**: 启动命令
- **Restart=always**: 服务异常退出时自动重启
- **RestartSec=10**: 重启前等待 10 秒
- **StandardOutput/Error=journal**: 日志输出到 systemd journal

### 安全设置

- **NoNewPrivileges**: 防止权限提升
- **PrivateTmp**: 使用私有临时目录
- **ProtectSystem=strict**: 系统目录只读
- **ProtectHome=read-only**: 家目录只读
- **ReadWritePaths**: 允许写入的路径（项目目录）

## 卸载服务

```bash
chmod +x uninstall_service.sh
./uninstall_service.sh
```

卸载脚本会：
- 停止运行中的服务
- 禁用开机自启
- 删除服务配置文件
- 重载 systemd daemon

## 故障排查

### 1. 服务无法启动

**查看详细错误信息：**

```bash
sudo systemctl status comfyui-flows-webui -l
sudo journalctl -u comfyui-flows-webui -n 50
```

**常见原因：**

- Python 依赖未安装
  ```bash
  pip install -r requirements.txt
  ```

- 工作目录路径错误
  ```bash
  # 检查服务文件中的 WorkingDirectory
  cat /etc/systemd/system/comfyui-flows-webui.service
  ```

- Python 路径错误
  ```bash
  # 检查 Python 是否可用
  which python3
  ```

### 2. 服务自动重启

如果服务不断重启，检查日志：

```bash
sudo journalctl -u comfyui-flows-webui -f
```

可能原因：
- ComfyUI 服务器无法连接
- 端口被占用（5014）
- 配置文件错误

### 3. 端口被占用

```bash
# 查找占用 5014 端口的进程
sudo lsof -i :5014

# 或
sudo netstat -tulnp | grep 5014
```

### 4. 权限问题

确保运行用户对项目目录有读写权限：

```bash
# 检查权限
ls -la /path/to/comfyui-flows-webui

# 如果需要，修改权限
sudo chown -R your-username:your-group /path/to/comfyui-flows-webui
```

### 5. 服务状态为 failed

```bash
# 重置失败状态
sudo systemctl reset-failed comfyui-flows-webui

# 重新启动
sudo systemctl start comfyui-flows-webui
```

## 日志管理

### 查看日志大小

```bash
sudo journalctl --disk-usage
```

### 清理旧日志

```bash
# 保留最近 7 天
sudo journalctl --vacuum-time=7d

# 保留最近 500MB
sudo journalctl --vacuum-size=500M
```

### 持久化日志

默认情况下，systemd 日志在重启后会丢失。要启用持久化：

```bash
sudo mkdir -p /var/log/journal
sudo systemd-tmpfiles --create --prefix /var/log/journal
sudo systemctl restart systemd-journald
```

## 性能监控

### 查看资源使用情况

```bash
sudo systemctl status comfyui-flows-webui
```

会显示：
- CPU 使用率
- 内存占用
- 运行时长

### 详细性能统计

```bash
systemd-cgtop
```

## 配置修改

### 修改服务配置

1. 编辑服务文件：
   ```bash
   sudo nano /etc/systemd/system/comfyui-flows-webui.service
   ```

2. 重载配置：
   ```bash
   sudo systemctl daemon-reload
   ```

3. 重启服务：
   ```bash
   sudo systemctl restart comfyui-flows-webui
   ```

### 常见修改

**修改端口：**

编辑 `wan22_i2v_14b_4.py`，修改端口号，然后重启服务。

**添加环境变量：**

```ini
[Service]
Environment="CUSTOM_VAR=value"
Environment="ANOTHER_VAR=value"
```

**调整重启策略：**

```ini
[Service]
Restart=on-failure        # 仅失败时重启
RestartSec=30            # 重启前等待 30 秒
StartLimitInterval=200   # 200 秒内
StartLimitBurst=5        # 最多重启 5 次
```

## 多实例运行

如果需要运行多个实例（不同端口），可以创建多个服务文件：

```bash
# 复制服务文件
sudo cp /etc/systemd/system/comfyui-flows-webui.service \
        /etc/systemd/system/comfyui-flows-webui-2.service

# 编辑新服务文件，修改端口和配置
sudo nano /etc/systemd/system/comfyui-flows-webui-2.service

# 重载并启动
sudo systemctl daemon-reload
sudo systemctl start comfyui-flows-webui-2
```

## 开发模式 vs 生产模式

### 开发模式

使用启动脚本，方便调试：

```bash
./start_wan22_service.sh
```

### 生产模式

使用 systemd 服务，稳定可靠：

```bash
sudo systemctl start comfyui-flows-webui
```

## 最佳实践

1. **使用专用用户**：不要使用 root 用户运行服务
2. **启用日志持久化**：方便问题排查
3. **定期查看日志**：及时发现潜在问题
4. **监控资源使用**：防止资源耗尽
5. **定期更新**：保持代码最新
6. **备份配置**：重要配置文件要备份

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

# 查看状态
sudo systemctl status comfyui-flows-webui
```

## 完全重装

```bash
# 卸载服务
./uninstall_service.sh

# 重新安装
./install_service.sh
```

## 服务验证

### 检查服务是否正常运行

```bash
# 1. 检查服务状态
sudo systemctl is-active comfyui-flows-webui

# 2. 测试 API
curl http://localhost:5014/health

# 3. 查看 API 文档
curl http://localhost:5014/
```

预期输出：
```json
{
  "service": "ComfyUI Wan2.2 I2V 14B API",
  "version": "1.0.0",
  "model": "Wan2.2-I2V-A14B-4steps"
}
```

## 总结

使用 systemd 管理服务的优势：

- ✅ 自动重启：服务崩溃后自动恢复
- ✅ 开机自启：系统重启后自动运行
- ✅ 统一管理：使用标准 systemctl 命令
- ✅ 日志集成：与系统日志系统集成
- ✅ 安全性：支持多种安全限制
- ✅ 资源控制：可以限制 CPU、内存等资源

推荐在生产环境中使用 systemd 服务方式部署。
