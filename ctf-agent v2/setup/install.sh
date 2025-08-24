#!/bin/bash
set -e

echo "CTF Agent Setup"
echo "==============="

# Check sudo access
if ! sudo -n true 2>/dev/null; then
    echo "需要sudo权限安装系统包"
    sudo -v
fi

# Detect OS
detect_os() {
    if command -v apt-get &> /dev/null; then
        OS="ubuntu"
    elif command -v dnf &> /dev/null; then
        OS="fedora"
    elif command -v pacman &> /dev/null; then
        OS="arch"
    else
        echo "不支持的系统"
        exit 1
    fi
    echo "检测到系统: $OS"
}

# Install system packages
install_packages() {
    echo "安装系统包..."
    
    case $OS in
        ubuntu)
            sudo apt-get update
            sudo apt-get install -y \
                python3 python3-pip python3-venv \
                git curl wget vim build-essential \
                file binutils gdb strace ltrace objdump hexdump xxd strings \
                nmap openssh-client netcat-openbsd telnet socat \
                unzip zip p7zip-full \
                exiftool binwalk steghide testdisk sleuthkit \
                imagemagick ffmpeg qrencode zbar-tools \
                libzbar0 libzbar-dev libopencv-dev \
                openssl gnupg2 \
                util-linux coreutils
            ;;
        fedora)
            sudo dnf install -y \
                python3 python3-pip python3-venv \
                git curl wget vim gcc \
                file binutils gdb strace ltrace \
                nmap openssh-clients unzip zip p7zip \
                exiftool binwalk steghide sleuthkit \
                ImageMagick ffmpeg qrencode zbar \
                openssl gnupg2 \
                util-linux coreutils
            ;;
        arch)
            sudo pacman -S --noconfirm \
                python python-pip \
                git curl wget vim base-devel \
                file binutils gdb strace ltrace \
                nmap openssh unzip zip p7zip \
                perl-image-exiftool binwalk steghide sleuthkit \
                imagemagick ffmpeg qrencode zbar \
                openssl gnupg \
                util-linux coreutils
            ;;
    esac
}

# Setup Python environment
setup_python() {
    echo "设置Python环境..."
    
    cd "$(dirname "$0")/.."
    
    if [[ ! -d "venv" ]]; then
        python3 -m venv venv
    fi
    
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
}

# Setup sudo permissions
setup_sudo() {
    read -p "配置sudo免密码? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        SUDOERS_FILE="/etc/sudoers.d/ctf-agent"
        sudo tee "$SUDOERS_FILE" > /dev/null << EOF
$USER ALL=(ALL) NOPASSWD: /usr/bin/apt-get, /usr/bin/dnf, /usr/bin/pacman
$USER ALL=(ALL) NOPASSWD: /usr/bin/nmap
EOF
        echo "sudo权限配置完成"
    fi
}

# Create startup script
create_start_script() {
    echo "创建启动脚本..."
    
    # 确保在正确的目录中
    cd "$(dirname "$0")/.."
    
    cat > start_ctf_agent.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
if [[ -d "venv" ]]; then
    source venv/bin/activate
    python3 main.py "$@"
else
    echo "请先运行 setup/install.sh"
    exit 1
fi
EOF
    
    # 给脚本添加执行权限
    chmod +x start_ctf_agent.sh
    
    echo "启动脚本创建完成: $(pwd)/start_ctf_agent.sh"
}

# Main function
main() {
    detect_os
    install_packages
    setup_python
    setup_sudo
    create_start_script
    
    echo "安装完成!"
    echo "使用: ./start_ctf_agent.sh"
}

main "$@"
