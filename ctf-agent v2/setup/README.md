# CTF Agent Setup

快速安装和使用CTF Agent。

## 🚀 快速开始

### Linux安装 (推荐开发使用)
```bash
cd setup
./install.sh
cd .. && ./start_ctf_agent.sh
```

### Docker部署 (推荐生产使用)  
```bash
cd docker
./build.sh
docker-compose up -d
docker exec -it ctf-agent bash
```

## 📋 系统要求

- **Linux**: Ubuntu/Debian/Fedora/Arch
- **Python**: 3.8+
- **权限**: sudo访问
- **Docker**: 20.10+ (可选)

## 🛠️ 安装内容

### 系统工具
- Python 3.8+, git, curl, wget, vim
- CTF工具: file, binutils, gdb, strace, ltrace  
- 网络工具: nmap, openssh-client
- 文件工具: unzip, zip, openssl

### Python包
- 核心框架: langchain, requests, pandas
- CTF库: pwntools, scapy, binwalk
- 密码学: pycryptodome, cryptography

## 🔧 故障排除

### 权限问题
```bash
sudo usermod -a -G dialout,wireshark $USER
```

### 包安装失败
```bash
sudo apt-get update  # 或 dnf update / pacman -Syu
./install.sh
```

### Python环境问题
```bash
rm -rf venv
python3 -m venv venv
source venv/bin/activate && pip install -r requirements.txt
```

## 📚 使用方法

```bash
# 启动CTF Agent
./start_ctf_agent.sh

# 处理具体挑战
./start_ctf_agent.sh challenges/2024/General\ Skills/binary_search/
```