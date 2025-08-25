# 使用Ubuntu作为基础镜像（更稳定）
FROM ubuntu:22.04

# 设置环境变量
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 更新系统并安装基础包
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    curl \
    wget \
    vim \
    nano \
    htop \
    net-tools \
    iputils-ping \
    ca-certificates \
    netcat-openbsd \
    telnet \
    gnupg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 安装Node.js (对js_executor工具必需)
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs

# Install essential CTF tools with comprehensive support
RUN apt-get update && \
    apt-get install -y --fix-missing \
    # Binary Analysis Tools (objdump, strings in binutils; hexdump in bsdmainutils)
    file binutils gdb strace ltrace xxd bsdmainutils \
    # Executable Packer/Unpacker
    upx \
    # Debuggers & Disassemblers
    gdb-multiarch \
    # Forensics and Steganography
    steghide exiftool binwalk sleuthkit testdisk foremost scalpel \
    # Network Tools  
    nmap openssh-client sshpass expect netcat-openbsd telnet socat \
    # Archive and Compression
    unzip zip p7zip-full unrar \
    # Image and Media Analysis
    imagemagick ffmpeg qrencode zbar-tools \
    # QR Code and Barcode Support
    libzbar0 libzbar-dev \
    # OpenCV for image processing (needed for QR code reading)
    libopencv-dev \
    # Cryptography
    openssl gnupg2 \
    # Development Tools
    vim git curl wget sudo build-essential \
    # Utilities
    util-linux coreutils \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install radare2 from source (more reliable than package manager)
RUN git clone --depth 1 https://github.com/radareorg/radare2.git /tmp/radare2 && \
    cd /tmp/radare2 && \
    ./sys/install.sh --install && \
    cd / && \
    rm -rf /tmp/radare2

# Install Python-based CTF tools
RUN pip3 install pwntools

# 创建项目目录
WORKDIR /app

# 复制项目文件
COPY requirements.txt .
COPY main.py .
COPY src/ ./src/
COPY challenges/ ./challenges/

# 创建Python虚拟环境
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 升级pip并安装Python依赖
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# 创建非root用户并给予sudo权限
RUN useradd -m -s /bin/bash ctfuser && \
    echo "ctfuser ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers && \
    chown -R ctfuser:ctfuser /app

# 切换到非root用户
USER ctfuser

# 设置工作目录权限
RUN chmod +x main.py

# 暴露端口（如果需要的话）
EXPOSE 8000

# 设置默认命令
CMD ["python3", "main.py"]
