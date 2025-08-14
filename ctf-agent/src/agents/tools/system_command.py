"""
System command execution tool for CTF challenges requiring external tools.
"""
import subprocess
import shutil
import os
from typing import Dict, Any, List
import tempfile

class SystemCommandTool:
    def __init__(self):
        self.name = "system_command"
        self.description = "Execute system commands for CTF challenges (openssl, base64, etc.)"
        
        # Common CTF tools and their installation commands
        self.tool_install_map = {
            'openssl': {
                'debian': 'apt-get update && apt-get install -y openssl',
                'redhat': 'yum install -y openssl',
                'arch': 'pacman -S openssl',
                'mac': 'brew install openssl'
            },
            'nc': {
                'debian': 'apt-get update && apt-get install -y netcat-openbsd',
                'redhat': 'yum install -y nc',
                'arch': 'pacman -S openbsd-netcat',
                'mac': 'brew install netcat'
            },
            'base64': {
                'debian': 'apt-get update && apt-get install -y coreutils',
                'redhat': 'yum install -y coreutils',
                'arch': 'pacman -S coreutils',
                'mac': 'included'  # Usually included in macOS
            }
        }
    
    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute system command with safety checks.
        
        Args:
            params: {
                "command": "command to execute",
                "args": ["list", "of", "arguments"] (optional),
                "input": "stdin input" (optional),
                "timeout": timeout in seconds (default: 30),
                "auto_install": True/False (attempt to install missing tools)
            }
        """
        try:
            command = params.get("command")
            args = params.get("args", [])
            stdin_input = params.get("input", "")
            timeout = params.get("timeout", 30)
            auto_install = params.get("auto_install", True)
            
            if not command:
                return {"success": False, "error": "Command is required"}
            
            # Security: Only allow specific CTF-related commands
            allowed_commands = {
                # Crypto tools
                'openssl', 'gpg', 'hashcat', 'john',
                
                # Encoding/decoding
                'base64', 'base32', 'xxd', 'hexdump', 'od', 'tr',
                
                # File analysis
                'strings', 'file', 'binwalk', 'foremost', 'steghide',
                'exiftool', 'identify', 'pngcheck',
                
                # Network tools
                'nc', 'netcat', 'ncat', 'telnet', 'curl', 'wget', 'nmap',
                'dig', 'nslookup', 'ping',
                
                # Programming languages
                'python3', 'python', 'python2', 'node', 'php', 'ruby', 'perl',
                
                # Text processing
                'echo', 'cat', 'head', 'tail', 'grep', 'egrep', 'fgrep',
                'sed', 'awk', 'sort', 'uniq', 'wc', 'cut', 'tr', 'tee',
                
                # System utilities
                'ls', 'find', 'which', 'whereis', 'chmod', 'chown',
                'tar', 'gzip', 'gunzip', 'unzip', 'zip', '7z',
                
                # Math and calculation
                'bc', 'expr', 'factor',
                
                # Process and data manipulation
                'printf', 'test', 'true', 'false', 'yes', 'seq',
                'shuf', 'rev', 'tac', 'nl', 'paste', 'join', 'split',
                
                # Binary analysis
                'objdump', 'readelf', 'nm', 'strip', 'gdb', 'ltrace', 'strace',
                
                # Archive and compression
                'tar', 'gzip', 'bzip2', 'xz', 'compress', 'uncompress',
                
                # Image and media
                'convert', 'mogrify', 'ffmpeg', 'sox',
                
                # Development tools
                'git', 'make', 'gcc', 'g++', 'clang',
                
                # Misc CTF tools
                'zsteg', 'outguess', 'stegsolve', 'volatility', 'sqlmap'
            }
            
            if command not in allowed_commands:
                return {"success": False, "error": f"Command '{command}' not allowed for security reasons"}
            
            # Check if command exists, try to install if not
            if not shutil.which(command):
                if auto_install and command in self.tool_install_map:
                    install_result = self._try_install_tool(command)
                    if not install_result["success"]:
                        return {"success": False, "error": f"Command '{command}' not found and installation failed: {install_result['error']}"}
                else:
                    return {"success": False, "error": f"Command '{command}' not found. Try with auto_install=True"}
            
            # Build full command
            full_command = [command] + args
            
            # Execute command
            process = subprocess.Popen(
                full_command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate(input=stdin_input, timeout=timeout)
            
            return {
                "success": True,
                "output": stdout,
                "error": stderr if stderr else None,
                "return_code": process.returncode,
                "command": ' '.join(full_command)
            }
            
        except subprocess.TimeoutExpired:
            process.kill()
            return {"success": False, "error": "Command timeout"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _try_install_tool(self, tool: str) -> Dict[str, Any]:
        """Attempt to install a missing tool"""
        try:
            # Detect OS
            os_type = self._detect_os()
            
            if tool not in self.tool_install_map:
                return {"success": False, "error": f"No installation method known for {tool}"}
            
            install_cmd = self.tool_install_map[tool].get(os_type)
            if not install_cmd:
                return {"success": False, "error": f"No installation method for {tool} on {os_type}"}
            
            if install_cmd == 'included':
                return {"success": True, "message": f"{tool} should be included in system"}
            
            # Try to install (requires sudo privileges)
            result = subprocess.run(
                install_cmd.split(),
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                return {"success": True, "message": f"Successfully installed {tool}"}
            else:
                return {"success": False, "error": f"Installation failed: {result.stderr}"}
                
        except Exception as e:
            return {"success": False, "error": f"Installation error: {str(e)}"}
    
    def _detect_os(self) -> str:
        """Detect operating system for installation"""
        if os.path.exists('/etc/debian_version'):
            return 'debian'
        elif os.path.exists('/etc/redhat-release'):
            return 'redhat'
        elif os.path.exists('/etc/arch-release'):
            return 'arch'
        elif os.uname().sysname == 'Darwin':
            return 'mac'
        else:
            return 'unknown'

# Tool registration for CTF Agent
def create_system_command_tool():
    """Create system command tool for CTF agent"""
    tool = SystemCommandTool()
    
    def system_command_func(command: str, args: List[str] = None, input_data: str = "", timeout: int = 30, auto_install: bool = True):
        """
        Execute system commands for CTF challenges.
        
        Args:
            command: Command to execute (openssl, base64, nc, etc.)
            args: List of command arguments
            input_data: Data to send to command's stdin
            timeout: Command timeout in seconds
            auto_install: Attempt to install missing tools
            
        Returns:
            Command output and execution info
        """
        params = {
            "command": command,
            "args": args or [],
            "input": input_data,
            "timeout": timeout,
            "auto_install": auto_install
        }
        return tool.execute(params)
    
    return system_command_func
