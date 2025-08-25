#!/bin/bash

# CTF Agent Docker 构建脚本

set -e

echo "🚀 开始构建 CTF Agent Docker 镜像..."

# 检查Docker是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ 错误: Docker 未安装，请先安装 Docker"
    exit 1
fi

# 检查docker-compose是否安装
if ! command -v docker-compose &> /dev/null; then
    echo "❌ 错误: docker-compose 未安装，请先安装 docker-compose"
    exit 1
fi

# 构建镜像
echo "📦 构建 Docker 镜像..."
docker-compose -f docker-compose.yml build

echo "✅ Docker 镜像构建完成！"

# 显示使用说明
echo ""
echo "📖 使用说明:"
echo "1. 启动容器: docker-compose -f docker-compose.yml up -d"
echo "2. 进入容器: docker exec -it ctf-agent bash"
echo "3. 运行项目: python3 main.py"
echo "4. 停止容器: docker-compose -f docker-compose.yml down"
echo ""
echo "🔧 开发模式:"
echo "   - 代码修改会自动同步到容器中"
echo "   - 使用 docker-compose -f docker-compose.yml up 启动（前台模式）"
echo ""
echo "🌐 网络访问:"
echo "   - 如需网络访问，请编辑 docker/docker-compose.yml 取消注释 ports 部分"
echo "   - 某些安全工具可能需要 privileged: true 或 network_mode: host"
