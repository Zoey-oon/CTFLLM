#!/bin/bash

# CTF Agent Docker 运行脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 显示帮助信息
show_help() {
    echo "🔧 CTF Agent Docker 管理脚本"
    echo ""
    echo "用法: $0 [命令]"
    echo ""
    echo "命令:"
    echo "  start     启动容器（后台模式）"
    echo "  stop      停止容器"
    echo "  restart   重启容器"
    echo "  status    查看容器状态"
    echo "  logs      查看容器日志"
    echo "  shell     进入容器shell"
    echo "  build     重新构建镜像"
    echo "  clean     清理容器和镜像"
    echo "  help      显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 start    # 启动容器"
    echo "  $0 shell    # 进入容器"
    echo "  $0 logs     # 查看日志"
}

# 检查Docker是否安装
check_docker() {
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}❌ 错误: Docker 未安装${NC}"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        echo -e "${RED}❌ 错误: docker-compose 未安装${NC}"
        exit 1
    fi
}

# 启动容器
start_container() {
    echo -e "${BLUE}🚀 启动 CTF Agent 容器...${NC}"
    docker-compose -f docker-compose.yml up -d
    echo -e "${GREEN}✅ 容器启动成功！${NC}"
    echo ""
    echo "📖 下一步操作:"
    echo "  1. 进入容器: $0 shell"
    echo "  2. 查看日志: $0 logs"
    echo "  3. 查看状态: $0 status"
}

# 停止容器
stop_container() {
    echo -e "${YELLOW}🛑 停止 CTF Agent 容器...${NC}"
    docker-compose -f docker-compose.yml down
    echo -e "${GREEN}✅ 容器已停止${NC}"
}

# 重启容器
restart_container() {
    echo -e "${BLUE}🔄 重启 CTF Agent 容器...${NC}"
    docker-compose -f docker-compose.yml restart
    echo -e "${GREEN}✅ 容器重启完成${NC}"
}

# 查看状态
show_status() {
    echo -e "${BLUE}📊 容器状态:${NC}"
    docker-compose -f docker-compose.yml ps
    echo ""
    echo -e "${BLUE}📊 系统资源使用:${NC}"
    docker stats --no-stream ctf-agent 2>/dev/null || echo "容器未运行"
}

# 查看日志
show_logs() {
    echo -e "${BLUE}📋 容器日志:${NC}"
    docker-compose -f docker-compose.yml logs -f
}

# 进入容器shell
enter_shell() {
    echo -e "${BLUE}🐚 进入容器 shell...${NC}"
    docker exec -it ctf-agent bash
}

# 构建镜像
build_image() {
    echo -e "${BLUE}🔨 重新构建镜像...${NC}"
    docker-compose -f docker-compose.yml build --no-cache
    echo -e "${GREEN}✅ 镜像构建完成${NC}"
}

# 清理资源
clean_resources() {
    echo -e "${YELLOW}🧹 清理 Docker 资源...${NC}"
    
    # 停止并删除容器
    docker-compose -f docker-compose.yml down -v
    
    # 删除镜像
    docker rmi ctf-agent_ctf-agent 2>/dev/null || echo "镜像不存在或已被删除"
    
    # 清理未使用的资源
    docker system prune -f
    
    echo -e "${GREEN}✅ 清理完成${NC}"
}

# 主函数
main() {
    check_docker
    
    case "${1:-help}" in
        start)
            start_container
            ;;
        stop)
            stop_container
            ;;
        restart)
            restart_container
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs
            ;;
        shell)
            enter_shell
            ;;
        build)
            build_image
            ;;
        clean)
            clean_resources
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            echo -e "${RED}❌ 未知命令: $1${NC}"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# 运行主函数
main "$@"
