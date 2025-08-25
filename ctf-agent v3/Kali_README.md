# CTF Agent - Kali Linux Setup Guide

## System Dependencies (for non-Docker environments)

### Essential System Tools Installation
```bash
# Update package list
sudo apt-get update

# Network tools (usually pre-installed in Kali)
sudo apt-get install -y netcat-openbsd telnet curl

# Cryptography tools (usually pre-installed)
sudo apt-get install -y openssl

# Binary Exploitation tools
sudo apt-get install -y file binutils gdb strace ltrace hexdump xxd

# Python development
sudo apt-get install -y python3-pip python3-dev

# Node.js system-wide (if not using nodeenv)
# curl -fsSL https://deb.nodesource.com/setup_18.x | sudo bash -
# sudo apt-get install -y nodejs
```

### Optional Advanced Tools
```bash
# Advanced binary analysis
sudo apt-get install -y radare2 gdb-multiarch

# Web tools
sudo apt-get install -y gobuster dirb sqlmap
```

## Quick Start

### Method 1: Automated Setup (Recommended)
```bash
# Clone the repository
git clone <ctf-agent-repo>
cd ctf-agent

# Run automated setup (includes system dependencies)
python3 setup_ctf_env.py

# Activate environment
source ./activate_ctf_env.sh

# Run CTF Agent
python3 main.py --help
```

### Method 2: Manual Setup
```bash
# Install Python dependencies (includes nodeenv for project-level Node.js)
pip3 install -r requirements.txt

# Create project-level Node.js environment
nodeenv --node=18.20.8 nodeenv

# Activate Node.js environment
source nodeenv/bin/activate

# Verify installation
node --version  # Should show v18.20.8

# Run CTF Agent
python3 main.py
```

### Method 3: Quick Setup (Python dependencies only)
```bash
# Install Python dependencies only
pip3 install -r requirements.txt

# Run CTF Agent
python3 main.py
```

### Method 4: System-wide Node.js
```bash
# Install Node.js system-wide
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo bash -
sudo apt-get install -y nodejs

# Install Python dependencies
pip3 install -r requirements.txt

# Run CTF Agent
python3 main.py
```

## Complete Environment Requirements

### Required Python Packages
All packages are listed in `requirements.txt`:
- Core: `pandas`, `numpy`, `requests`, `langchain`
- LLM Support: `langchain-openai`, `langchain-anthropic`, `langchain-deepseek`
- JavaScript Engines: `PyExecJS`, `js2py`
- Node.js Management: `nodeenv` (for project-level Node.js)

### Required System Tools
Most are pre-installed in Kali Linux:
```bash
# Network tools
netcat-openbsd telnet curl wget

# Crypto tools
openssl base64

# Verification
which nc telnet curl wget openssl base64
```

### JavaScript Engine Priority
The `js_executor` tool uses engines in this order:
1. **Node.js** (Primary - best compatibility)
2. **Deno** (Backup engine)
3. **PyExecJS** (Python-integrated engine)
4. **js2py** (Final fallback)

## Tool Capabilities

### Available Tools
- `file_reader`: Read challenge files (supports binary with |binary suffix)
- `code_executor`: Execute Python code with auto-install capabilities
- `network_connector`: Connect to remote services (nc, telnet, HTTP)
- `system_command`: Execute system commands (openssl, curl, etc.)
- `js_executor`: Execute JavaScript code (bookmarklets, client-side scripts)
- `js_decryptor`: Decrypt JavaScript-based encryption (XOR, substitution)
- `flag_validator`: Extract and validate picoCTF flags
- `package_installer`: Install Python packages

### Web Challenge Priorities
For Web Exploitation challenges:
- JavaScript/Bookmarklets: `js_executor` → `js_decryptor` → `code_executor`
- Web requests: `network_connector` (HTTP/GET/POST methods)
- Source analysis: `file_reader` → `code_executor`
- System commands: `system_command` (openssl, curl, etc.)

## Verification Script

Create `verify_setup.sh` to check all dependencies:
```bash
#!/bin/bash
echo "=== CTF Agent Dependency Check ==="

# Python dependencies
echo "Checking Python dependencies..."
python3 -c "import pandas, numpy, requests, langchain" 2>/dev/null && echo "✓ Python core packages installed" || echo "✗ Python core packages missing"

# JavaScript engines
echo "Checking JavaScript engines..."
node --version >/dev/null 2>&1 && echo "✓ Node.js installed: $(node --version)" || echo "✗ Node.js not installed"
deno --version >/dev/null 2>&1 && echo "✓ Deno installed: $(deno --version | head -1)" || echo "○ Deno not installed (optional)"

# Python JS engines
python3 -c "import PyExecJS" 2>/dev/null && echo "✓ PyExecJS installed" || echo "○ PyExecJS not installed (optional)"
python3 -c "import js2py" 2>/dev/null && echo "✓ js2py installed" || echo "○ js2py not installed (optional)"

# Network tools
which nc >/dev/null 2>&1 && echo "✓ netcat installed" || echo "✗ netcat not installed"
which telnet >/dev/null 2>&1 && echo "✓ telnet installed" || echo "✗ telnet not installed"
which curl >/dev/null 2>&1 && echo "✓ curl installed" || echo "✗ curl not installed"

# Crypto tools
which openssl >/dev/null 2>&1 && echo "✓ openssl installed" || echo "✗ openssl not installed"
which base64 >/dev/null 2>&1 && echo "✓ base64 installed" || echo "✗ base64 not installed"

# Binary analysis tools
which file >/dev/null 2>&1 && echo "✓ file installed" || echo "✗ file not installed"
which readelf >/dev/null 2>&1 && echo "✓ readelf installed" || echo "✗ readelf not installed"
which objdump >/dev/null 2>&1 && echo "✓ objdump installed" || echo "✗ objdump not installed"
which gdb >/dev/null 2>&1 && echo "✓ gdb installed" || echo "✗ gdb not installed"
which strace >/dev/null 2>&1 && echo "✓ strace installed" || echo "✗ strace not installed"

echo "=== Check Complete ==="
```

## Optional Enhancements

### Install Deno (Additional JavaScript Engine)
```bash
curl -fsSL https://deno.land/x/install/install.sh | sh
echo 'export PATH="$HOME/.deno/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
deno --version
```

### Install V8/Duktape for PyExecJS
```bash
# For V8 engine
sudo apt install -y libv8-dev

# For Duktape engine (lightweight)
sudo apt install -y duktape-dev
```

## Usage Examples

### Basic Challenge Solving
```bash
# Activate environment
source ./activate_ctf_env.sh

# Solve a challenge
python3 main.py challenges/2024/Web\ Exploitation/bookmarklet/

# Exit environment
deactivate
```

### Manual Tool Testing
```bash
# Test JavaScript execution
python3 -c "
from src.agents.tools.js_executor import create_js_executor_tool
tool = create_js_executor_tool()
result = tool(code='console.log(\"Test\"); \"success\"', engine='auto')
print(result)
"
```

## Troubleshooting

### Node.js Issues
- Check PATH: `echo $PATH | grep node`
- Verify permissions: `ls -la $(which node)`
- Reinstall if needed: `nodeenv --clear nodeenv && nodeenv --node=18.20.8 nodeenv`

### Python Dependency Issues
- Use virtual environment: `python3 -m venv venv && source venv/bin/activate`
- Clear pip cache: `pip cache purge`
- Update pip: `python3 -m pip install --upgrade pip`

### Network Connection Issues
- Test connectivity: `nc -zv example.com 80`
- Check DNS: `nslookup example.com`
- Verify firewall: `sudo ufw status`

### Permission Issues
- Some system commands may require sudo
- Check file permissions: `ls -la main.py`
- Ensure executable: `chmod +x main.py`

## Environment Structure

After setup, your project should have:
```
ctf-agent/
├── main.py                 # Main entry point
├── requirements.txt        # Python dependencies
├── setup_ctf_env.py       # Automated setup script
├── activate_ctf_env.sh    # Environment activation script
├── nodeenv/               # Project-level Node.js (if using nodeenv)
├── src/                   # Source code
└── challenges/            # CTF challenges
```

## Notes

1. **Node.js Version**: 18.20.8 is recommended for best compatibility
2. **Environment Isolation**: Project-level Node.js doesn't affect system
3. **Fallback Support**: Multiple JavaScript engines ensure reliability
4. **Kali Compatibility**: Tested on Kali Linux 2024.x
5. **Proxy Support**: Configure HTTP_PROXY/HTTPS_PROXY if needed
