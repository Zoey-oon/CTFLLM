# CTF Agent Setup

快速安装和使用CTF Agent。

## 🚀 快速开始

### Linux安装 (推荐开发使用)
```bash
cd setup
./install.sh
cd .. && ./start_ctf_agent.sh
```

### 安装所有CTF工具 (推荐)
```bash
# 使用自动化脚本安装所有CTF工具
./install_ctf_tools.sh

# 或者手动安装
sudo apt-get update
sudo apt-get install -y upx binwalk xxd file strings objdump gdb gdb-multiarch radare2 foremost scalpel testdisk sleuthkit steghide exiftool binutils nmap netcat-openbsd telnet socat unzip zip p7zip-full unrar imagemagick ffmpeg qrencode libzbar0 libzbar-dev libopencv-dev openssl gnupg2 git curl wget build-essential util-linux coreutils
```

### Docker部署 (强烈推荐 - 所有工具预装)  
```bash
cd docker
./build.sh
docker-compose up -d
docker exec -it ctf-agent bash
# 所有CTF工具已预装，无需额外配置
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

### 新增CTF工具
- **二进制分析**: upx, binwalk, xxd, strings, objdump
- **调试器**: gdb, gdb-multiarch, radare2
- **取证工具**: foremost, scalpel, testdisk, sleuthkit
- **隐写术**: steghide, exiftool
- **网络分析**: nmap, netcat, telnet, socat
- **媒体处理**: imagemagick, ffmpeg, qrencode
- **QR码**: zbar, opencv
- **加密**: openssl, gnupg2

### Python包
- 核心框架: langchain, requests, pandas
- CTF库: pwntools, scapy, binwalk
- 密码学: pycryptodome, cryptography
- **新增**: capstone, keystone, unicorn, pefile, pyelftools, lief, sympy, gmpy2, z3-solver, angr

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