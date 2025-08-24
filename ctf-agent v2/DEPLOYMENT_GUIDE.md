# 🚀 CTF Agent 部署指南

CTF Agent 支持两种主要部署方式：**Docker容器化部署**和**Linux原生部署**。

## 📋 部署方式对比

| 特性 | 🐳 Docker部署 | 🐧 Linux原生部署 |
|------|---------------|------------------|
| **跨平台支持** | ✅ Windows/macOS/Linux | ❌ 仅Linux |
| **环境隔离** | ✅ 完全隔离 | ❌ 与宿主系统共享 |
| **部署难度** | 🟢 简单 | 🟡 中等 |
| **性能** | 🟡 有容器开销 | 🟢 最佳性能 |
| **网络访问** | 🟡 需要配置 | 🟢 直接访问 |
| **权限管理** | 🟢 安全隔离 | 🟡 需要配置sudo |
| **工具完整性** | 🟢 预装所有工具 | 🟡 需要手动安装 |

## 🐳 方案一：Docker部署（推荐）

### 优势
- **跨平台兼容**：Windows、macOS、Linux都支持
- **一键部署**：所有依赖都已预装
- **环境隔离**：不会影响宿主系统
- **快速启动**：构建一次，到处运行

### 前置要求
```bash
# 安装Docker和Docker Compose
# Ubuntu/Debian:
sudo apt-get update
sudo apt-get install docker.io docker-compose

# CentOS/RHEL:
sudo yum install docker docker-compose

# macOS:
brew install docker docker-compose
# 或下载Docker Desktop

# Windows:
# 下载并安装Docker Desktop
```

### 部署步骤

1. **克隆项目**
```bash
git clone <repository_url>
cd ctf-agent
```

2. **构建并启动**
```bash
cd docker
./build.sh              # 构建Docker镜像
docker-compose up -d     # 后台启动容器
```

3. **使用方式**
```bash
# 进入容器
docker exec -it ctf-agent bash

# 运行CTF Agent
python3 main.py

# 停止容器
docker-compose down
```

### Docker配置说明

#### 网络访问
- 默认映射端口：`8000:8000`
- 如需其他端口，修改 `docker-compose.yml`

#### 数据持久化
```yaml
# 在docker-compose.yml中添加
volumes:
  - ./data:/app/data
  - ./challenges:/app/challenges
```

#### 特权模式
- 已启用 `privileged: true` 用于安全工具
- 如需主机网络：取消注释 `network_mode: host`

## 🐧 方案二：Linux原生部署

### 优势
- **最佳性能**：无容器开销
- **直接网络访问**：无需端口映射
- **系统集成**：可以使用所有系统工具
- **调试友好**：直接访问日志和进程

### 前置要求
- Linux系统（Ubuntu 20.04+、Debian 11+、CentOS 8+、Fedora 35+）
- sudo权限
- Python 3.8+

### 部署步骤

1. **克隆项目**
```bash
git clone <repository_url>
cd ctf-agent
```

2. **运行安装脚本**
```bash
cd setup
chmod +x install.sh
./install.sh
```

安装脚本会自动：
- 检测操作系统
- 安装系统级CTF工具
- 设置Python虚拟环境
- 配置用户权限
- 创建启动脚本

3. **启动CTF Agent**
```bash
# 方式1：使用启动脚本
./start_ctf_agent.sh

# 方式2：手动启动
source venv/bin/activate
python3 main.py
```

### 权限配置

#### 自动权限配置
安装脚本会询问是否配置免密码sudo：
```bash
🤔 是否配置免密码sudo用于CTF工具? (y/N): y
```

这会创建 `/etc/sudoers.d/ctf-agent`：
```bash
# CTF Agent sudo rules
username ALL=(ALL) NOPASSWD: /usr/bin/apt-get, /usr/bin/nmap, /usr/bin/tcpdump
```

#### 手动权限配置
```bash
# 添加用户到相关组
sudo usermod -a -G dialout,wireshark $USER

# 配置特定命令的sudo权限
sudo visudo -f /etc/sudoers.d/ctf-agent
```

### 支持的Linux发行版

#### Ubuntu/Debian/Kali
```bash
# 自动安装：
sudo apt-get install python3 git nmap gdb binutils file strace ltrace
sudo apt-get install netcat-openbsd openssh-client sshpass expect
sudo apt-get install unzip zip openssl steghide exiftool
```

#### CentOS/RHEL/Fedora
```bash
# 自动安装：
sudo dnf install python3 git nmap gdb binutils file strace ltrace
sudo dnf install netcat openssh-clients unzip zip openssl
```

#### Arch Linux
```bash
# 自动安装：
sudo pacman -S python git nmap gdb binutils file strace ltrace
sudo pacman -S netcat openssh unzip zip openssl
```

## 🔧 工具完整性对比

### Docker环境
✅ 预装所有工具，包括：
- 二进制分析：`file`, `gdb`, `objdump`, `readelf`, `strings`
- 网络工具：`nmap`, `netcat`, `ssh`, `sshpass`, `expect`
- 密码学：`openssl`, `steghide`, `john`, `hashcat`
- 文件处理：`unzip`, `exiftool`, `binwalk`, `foremost`
- 取证工具：`volatility3`, `testdisk`, `sleuthkit`

### Linux原生环境
🟡 通过安装脚本自动安装，但某些工具可能需要手动配置：
- 基础工具：✅ 完全支持
- 高级工具：🟡 部分需要额外配置
- 商业工具：❌ 需要单独购买和安装

## 🚨 常见问题与解决方案

### Docker相关问题

#### 1. 构建失败
```bash
# 清理并重新构建
docker system prune -a
cd docker && ./build.sh
```

#### 2. 权限问题
```bash
# 确保Docker daemon运行
sudo systemctl start docker
sudo usermod -a -G docker $USER
# 重新登录或重启
```

#### 3. 网络连接问题
```bash
# 检查端口映射
docker-compose ps
# 修改docker-compose.yml中的ports配置
```

### Linux原生问题

#### 1. 权限不足
```bash
# 检查sudo权限
sudo -l
# 重新运行安装脚本
cd setup && ./install.sh
```

#### 2. 包管理器问题
```bash
# Ubuntu/Debian
sudo apt-get update && sudo apt-get upgrade

# CentOS/Fedora
sudo dnf update

# 清理包缓存
sudo apt-get clean
sudo dnf clean all
```

#### 3. Python环境问题
```bash
# 重新创建虚拟环境
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 📊 性能优化建议

### Docker环境优化
```yaml
# docker-compose.yml
services:
  ctf-agent:
    # 分配更多资源
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: '2.0'
    # 使用主机网络（如果安全允许）
    network_mode: host
```

### Linux原生环境优化
```bash
# 安装性能监控工具
sudo apt-get install htop iotop

# 优化Python性能
export PYTHONOPTIMIZE=1
export PYTHONDONTWRITEBYTECODE=1

# 使用更快的包管理器镜像
# Ubuntu:
sudo sed -i 's/archive.ubuntu.com/mirrors.aliyun.com/g' /etc/apt/sources.list
```

## 🔒 安全建议

### Docker安全
- 使用非root用户运行容器
- 限制容器权限：避免 `--privileged` 除非必要
- 定期更新基础镜像
- 使用secrets管理敏感信息

### Linux原生安全
- 使用专用用户账户
- 限制sudo权限范围
- 定期更新系统和工具
- 监控异常活动

## 📚 进阶配置

### 自定义工具安装
```bash
# 在安装脚本后添加自定义工具
source venv/bin/activate
pip install custom-ctf-tool

# 或系统级安装
sudo apt-get install custom-tool
```

### 环境变量配置
```bash
# 创建.env文件
cat > .env << EOF
OPENAI_API_KEY=your_key
ANTHROPIC_API_KEY=your_key
CTF_AGENT_DEBUG=true
EOF
```

### 日志配置
```bash
# 启用详细日志
export CTF_AGENT_LOG_LEVEL=DEBUG
python3 main.py --verbose
```

## 🤝 贡献指南

欢迎提交Issue和Pull Request来改进部署过程：

1. **报告问题**：包含操作系统、错误信息、复现步骤
2. **功能建议**：描述用例和预期行为
3. **代码贡献**：遵循现有代码风格，添加测试

---

🎯 **推荐选择**：
- **新用户/跨平台**：选择Docker部署
- **Linux专家/性能要求高**：选择Linux原生部署
- **生产环境**：Docker + 专用服务器
- **开发测试**：Linux原生 + 开发机器
