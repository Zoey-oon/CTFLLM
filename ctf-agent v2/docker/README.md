# CTF Agent Docker 环境

这是一个基于 Kali Linux 的 Docker 环境，用于运行 CTF Agent 项目。

## 🐳 特性

- **基础镜像**: Kali Linux Rolling (最新版本)
- **预装工具**: 包含常用的网络安全和渗透测试工具
- **Python环境**: Python 3 + 虚拟环境
- **开发友好**: 支持代码热重载和卷挂载
- **安全考虑**: 非root用户运行

## 📋 预装工具

### 基础工具
- Python 3 + pip + venv
- Git, curl, wget
- vim, nano, htop
- net-tools, iputils-ping

### 网络安全工具
- **网络分析**: nmap, wireshark
- **Web安全**: sqlmap, burpsuite
- **密码破解**: john, hashcat, hydra
- **无线安全**: aircrack-ng
- **渗透测试**: metasploit-framework

## 🚀 快速开始

### 1. 构建镜像

```bash
# 使用构建脚本
chmod +x docker/build.sh
./docker/build.sh

# 或手动构建
docker-compose -f docker/docker-compose.yml build
```

### 2. 启动容器

```bash
# 使用运行脚本
chmod +x docker/run.sh
./docker/run.sh start

# 或手动启动
docker-compose -f docker/docker-compose.yml up -d
```

### 3. 进入容器

```bash
# 使用脚本
./docker/run.sh shell

# 或手动进入
docker exec -it ctf-agent bash
```

### 4. 运行项目

```bash
# 在容器内
python3 main.py
```

## 📖 使用说明

### 脚本命令

```bash
./docker/run.sh [命令]

可用命令:
  start     启动容器（后台模式）
  stop      停止容器
  restart   重启容器
  status    查看容器状态
  logs      查看容器日志
  shell     进入容器shell
  build     重新构建镜像
  clean     清理容器和镜像
  help      显示帮助信息
```

### 常用操作

```bash
# 查看容器状态
./docker/run.sh status

# 查看日志
./docker/run.sh logs

# 重启容器
./docker/run.sh restart

# 清理资源
./docker/run.sh clean
```

## 🔧 配置选项

### 网络配置

如需网络访问，编辑 `docker-compose.yml`:

```yaml
ports:
  - "8000:8000"
```

### 特权模式

某些安全工具需要特权模式:

```yaml
privileged: true
```

### 主机网络

某些工具需要访问主机网络:

```yaml
network_mode: host
```

## 📁 目录结构

```
docker/
├── Dockerfile              # Docker镜像定义
├── docker-compose.yml      # 容器编排配置
├── .dockerignore          # Docker忽略文件
├── build.sh               # 构建脚本
├── run.sh                 # 运行管理脚本
└── README.md              # 本文档
```

## 🐛 故障排除

### 常见问题

1. **权限问题**
   ```bash
   # 确保脚本有执行权限
   chmod +x docker/*.sh
   ```

2. **端口冲突**
   ```bash
   # 检查端口占用
   lsof -i :8000
   # 修改 docker-compose.yml 中的端口映射
   ```

3. **内存不足**
   ```bash
   # 增加Docker内存限制
   # 在Docker Desktop中调整资源限制
   ```

4. **工具安装失败**
   ```bash
   # 重新构建镜像
   ./docker/run.sh build
   ```

### 日志查看

```bash
# 查看容器日志
./docker/run.sh logs

# 查看构建日志
docker-compose -f docker/docker-compose.yml build --progress=plain
```

## 🔒 安全注意事项

- 容器以非root用户运行
- 敏感文件使用只读挂载
- 网络访问默认关闭
- 定期更新基础镜像

## 📚 相关资源

- [Docker 官方文档](https://docs.docker.com/)
- [Docker Compose 文档](https://docs.docker.com/compose/)
- [Kali Linux 工具列表](https://tools.kali.org/)
- [CTF Agent 项目文档](../README.txt)

## 🤝 贡献

欢迎提交 Issue 和 Pull Request 来改进这个 Docker 环境！

## 📄 许可证

本项目遵循与主项目相同的许可证。
