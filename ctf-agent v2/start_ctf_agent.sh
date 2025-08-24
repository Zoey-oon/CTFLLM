#!/bin/bash
cd "$(dirname "$0")"
if [[ -d "venv" ]]; then
    source venv/bin/activate
    python3 main.py "$@"
else
    echo "请先运行 setup/install.sh"
    exit 1
fi
