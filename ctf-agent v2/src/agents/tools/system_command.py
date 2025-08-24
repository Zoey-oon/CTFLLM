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
        self.current_working_dir = os.getcwd()  # Track current working directory
        
        # CTF tools installation for Linux (Kali/Docker)
        self.tool_install_map = {
            'openssl': {
                'linux': 'apt-get update && apt-get install -y openssl'
            },
            'nc': {
                'linux': 'apt-get update && apt-get install -y netcat-openbsd'
            },
            'base64': {
                'linux': 'apt-get update && apt-get install -y coreutils'
            },
            'unzip': {
                'linux': 'apt-get update && apt-get install -y unzip'
            },
            'zip': {
                'linux': 'apt-get update && apt-get install -y zip'
            },
            'curl': {
                'linux': 'apt-get update && apt-get install -y curl'
            },
            'wget': {
                'linux': 'apt-get update && apt-get install -y wget'
            },
            'python3': {
                'linux': 'apt-get update && apt-get install -y python3'
            },
            'git': {
                'linux': 'apt-get update && apt-get install -y git'
            }
        }
    
    def _handle_cd_command(self, args):
        """Handle cd command to change working directory"""
        if not args:
            # cd without args goes to home directory
            self.current_working_dir = os.path.expanduser("~")
            return {"success": True, "output": f"Changed directory to: {self.current_working_dir}"}
        
        target_path = args[0]
        
        # Handle relative paths
        if target_path.startswith('/'):
            # Absolute path
            new_path = target_path
        else:
            # Relative path from current directory
            new_path = os.path.join(self.current_working_dir, target_path)
        
        # Handle special cases
        if target_path == '.':
            return {"success": True, "output": f"Current directory: {self.current_working_dir}"}
        elif target_path == '..':
            new_path = os.path.dirname(self.current_working_dir)
        elif target_path == '~':
            new_path = os.path.expanduser("~")
        elif target_path == '-':
            # TODO: Implement previous directory tracking
            return {"success": False, "error": "Previous directory tracking not implemented yet"}
        
        # Check if directory exists and is accessible
        if not os.path.exists(new_path):
            return {"success": False, "error": f"Directory '{new_path}' does not exist"}
        if not os.path.isdir(new_path):
            return {"success": False, "error": f"'{new_path}' is not a directory"}
        if not os.access(new_path, os.R_OK):
            return {"success": False, "error": f"Permission denied accessing '{new_path}'"}
        
        # Change working directory
        self.current_working_dir = os.path.abspath(new_path)
        return {"success": True, "output": f"Changed directory to: {self.current_working_dir}"}
    
    def _handle_pwd_command(self):
        """Handle pwd command to show current working directory"""
        return {"success": True, "output": self.current_working_dir}
    
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
            
            # Handle built-in shell commands
            if command == "cd":
                return self._handle_cd_command(args)
            elif command == "pwd":
                return self._handle_pwd_command()
            
            # Security: Only allow specific CTF-related commands
            allowed_commands = {
                # Crypto tools
                'openssl', 'gpg', 'hashcat', 'john', 'john-the-ripper', 'johntheripper',
                'hashcat-utils', 'hash-identifier', 'findmyhash', 'hashid', 'nth',
                
                # Encoding/decoding
                'base64', 'base32', 'base85', 'ascii85', 'xxd', 'hexdump', 'od', 'tr', 'iconv', 
                'uuencode', 'uudecode', 'rot13', 'caesar', 'vigenere', 'morse',
                
                # File analysis
                'strings', 'file', 'binwalk', 'foremost', 'steghide', 'firmware-mod-kit', 
                'sasquatch', 'jefferson', 'exiftool', 'identify', 'pngcheck', 'mediainfo', 
                'ffprobe', 'yara', 'clamav', 'chkrootkit', 'rkhunter',
                
                # Network tools
                'nc', 'netcat', 'ncat', 'telnet', 'curl', 'wget', 'nmap',
                'dig', 'nslookup', 'ping', 'ssh', 'scp', 'sftp', 'ftp', 
                'rsync', 'host', 'whois', 'traceroute', 'tcpdump', 'wireshark', 'tshark',
                'ettercap', 'dsniff', 'arpspoof', 'macchanger', 'aircrack', 'aircrack-ng',
                
                # Programming languages and shells  
                'python3', 'python', 'python2', 'node', 'php', 'ruby', 'perl',
                'bash', 'sh', 'zsh', 'brainfuck', 'malbolge', 'whitespace',
                
                # Text processing
                'echo', 'cat', 'head', 'tail', 'grep', 'egrep', 'fgrep',
                'sed', 'awk', 'sort', 'uniq', 'wc', 'cut', 'tr', 'tee',
                'crunch', 'cewl', 'maskprocessor', 'princeprocessor',
                
                # System utilities
                'ls', 'find', 'which', 'whereis', 'chmod', 'chown',
                'tar', 'gzip', 'gunzip', 'unzip', 'zip', '7z', 'timeout',
                
                # Math and calculation
                'bc', 'expr', 'factor',
                
                # Process and data manipulation
                'printf', 'test', 'true', 'false', 'yes', 'seq',
                'shuf', 'rev', 'tac', 'nl', 'paste', 'join', 'split',
                
                # Binary analysis
                'objdump', 'readelf', 'nm', 'strip', 'gdb', 'ltrace', 'strace', 'checksec', 'pwn',
                
                # Archive and compression
                'tar', 'gzip', 'bzip2', 'xz', 'compress', 'uncompress',
                
                # Image and media
                'convert', 'mogrify', 'ffmpeg', 'sox', 'sonic-visualiser', 'audacity',
                'qrencode', 'qrdecode', 'zbarimg', 'dmtxread', 'dmtxwrite',
                
                # Development tools
                'git', 'make', 'gcc', 'g++', 'clang',
                
                # Web security tools
                'burpsuite', 'dirb', 'gobuster', 'nikto', 'sqlmap', 'hydra',
                'medusa', 'wfuzz', 'ffuf', 'dirbuster', 'metasploit', 'msfconsole', 
                'msfvenom', 'searchsploit',
                
                # Forensics and analysis
                'volatility', 'volatility3', 'rekall', 'lime', 'autopsy', 'sleuthkit', 
                'bulk-extractor', 'scalpel', 'photorec', 'testdisk', 'ddrescue', 'dc3dd',
                
                # Steganography tools
                'zsteg', 'outguess', 'stegsolve', 'steghide', 'stegcracker', 'stegseek',
                'steganosaurus', 'stegpy', 'stepic', 'outguess-rebirth', 'exiv2',
                
                # Reverse engineering
                'radare2', 'r2', 'ghidra', 'ida', 'x64dbg', 'ollydbg',
                'angr', 'z3', 'binaryninja',
                
                # Database tools
                'sqlite3', 'mysql', 'psql', 'mongodb', 'redis-cli',
                
                # Additional crypto tools
                'age', 'ccrypt', 'mcrypt', 'gnupg2',
                
                # Document analysis tools
                'qpdf', 'pdftk', 'pdfcrack', 'pdf-parser',
                
                # Security analysis tools
                'lynis', 'tiger', 'aide', 'samhain',
                
                # Package managers (for tool installation)
                'apt', 'apt-get', 'yum', 'dnf', 'pacman', 'brew',
                'pip', 'pip3', 'npm', 'yarn', 'gem', 'cargo',
                
                # Text editors (for file modification)
                'vim', 'nano', 'emacs', 'less', 'more',
                
                # System monitoring (safe read-only)
                'ps', 'top', 'htop', 'df', 'du', 'free', 'lsof', 'netstat',
                
                # Version control
                'git', 'svn', 'hg', 'bzr',
            }
            
            # Simplified Security Strategy: Block dangerous commands, allow everything else
            
            # Step 1: Always allow local executables for CTF analysis
            if command.startswith('./') and len(command) > 2:
                local_file = command[2:]
                if not os.path.exists(local_file):
                    return {"success": False, "error": f"Local executable '{command}' not found in current directory"}
                # Allow execution
                pass
            
            # Step 2: Block only explicitly dangerous commands
            dangerous_commands = {
                # Dangerous file operations (destructive)
                'rm', 'rmdir', 'shred',
                # System control (potentially disruptive)
                'kill', 'killall', 'pkill', 'halt', 'shutdown', 'reboot',
                # Disk operations (dangerous)
                'fdisk', 'mkfs', 'format', 'parted', 'dd',
                # User management (security risk)
                'su', 'sudo', 'passwd', 'useradd', 'userdel', 'usermod',
                # Network/firewall changes (security risk)
                'iptables', 'ufw', 'firewall-cmd',
                # System services (potentially disruptive)
                'systemctl', 'service', 'chkconfig',
                # Filesystem operations (potentially dangerous)
                'mount', 'umount', 'fsck',
            }
            
            if command in dangerous_commands:
                return {"success": False, "error": f"Command '{command}' is dangerous and not allowed"}
            
            # Step 3: Everything else is allowed!
            # If not in dangerous list, allow execution
            # This includes:
            # - All commands in allowed_commands (explicit whitelist)
            # - Any CTF tools not yet in our list
            # - System utilities that are safe for read-only operations
            # - Programming tools and compilers
            # - Network tools for CTF challenges
            else:
                # Command is allowed (not dangerous)
                pass
            
            # Check if command exists, try to install if not
            # Special handling for local executables
            if command.startswith('./'):
                # Local executable - check if file exists in current directory
                local_file = command[2:]  # Remove './'
                if not os.path.exists(local_file):
                    return {"success": False, "error": f"Local executable '{command}' not found in current directory"}
            elif not shutil.which(command):
                if auto_install and command in self.tool_install_map:
                    install_result = self._try_install_tool(command)
                    if not install_result["success"]:
                        return {"success": False, "error": f"Command '{command}' not found and installation failed: {install_result['error']}"}
                else:
                    return {"success": False, "error": f"Command '{command}' not found. Try with auto_install=True"}
            
            # Enhance args with intelligent path resolution for CTF files
            enhanced_args = []
            for arg in args:
                if os.path.exists(arg):
                    # File exists as-is
                    enhanced_args.append(os.path.abspath(arg))
                else:
                    # Try to find file in challenges directory
                    found = False
                    base_name = os.path.basename(arg)
                    
                    # Search in current working directory first
                    if os.path.exists(base_name):
                        enhanced_args.append(os.path.abspath(base_name))
                        found = True
                    else:
                        # Search in challenges directory
                        challenges_dir = os.path.join(os.getcwd(), 'challenges')
                        if os.path.exists(challenges_dir):
                            for root, _, files in os.walk(challenges_dir):
                                if base_name in files:
                                    full_path = os.path.join(root, base_name)
                                    enhanced_args.append(os.path.abspath(full_path))
                                    found = True
                                    break
                    
                    if not found:
                        enhanced_args.append(arg)  # Keep original if not found
            
            # Build full command
            full_command = [command] + enhanced_args
            
            # Execute command with enhanced error handling
            # Special handling for package installation (check if sudo needed)
            if command in ['apt-get', 'apt', 'yum', 'dnf'] and not shutil.which('sudo'):
                return {"success": False, "error": "Package installation requires sudo privileges. Run in Docker environment with proper permissions."}
            
            # Add sudo for package management if not root
            if command in ['apt-get', 'apt', 'yum', 'dnf'] and os.getuid() != 0:
                full_command = ['sudo'] + full_command
            
            # Special handling for SSH commands with password
            if command == "ssh":
                return {"success": False, "error": "SSH commands are disabled in system_command. Use ssh_tool instead.", "redirect": "Use <tool>ssh_tool</tool> for SSH connections", "reason": "SSH requires specialized handling that ssh_tool provides"}
                # Parse SSH inputs (password, commands, etc.)
                inputs = stdin_input.strip().split('\n')
                password = inputs[0] if inputs else ""
                
                # Add SSH options for better connection handling
                ssh_options = [
                    "-o", "StrictHostKeyChecking=no",
                    "-o", "UserKnownHostsFile=/dev/null",
                    "-o", "ConnectTimeout=10",
                    "-o", "ServerAliveInterval=60",
                    "-o", "ServerAliveCountMax=3",
                    "-t"  # Force pseudo-terminal allocation
                ]
                
                # Try sshpass first (most reliable)
                if shutil.which('sshpass'):
                    try:
                        # Use sshpass for password authentication with SSH options
                        sshpass_cmd = ["sshpass", "-p", password] + full_command[:1] + ssh_options + full_command[1:]
                        
                        # For interactive games, we need to handle the connection differently
                        if len(inputs) > 1:
                            # Send initial commands and wait for response
                            process = subprocess.Popen(
                                sshpass_cmd,
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True,
                                bufsize=1,
                                universal_newlines=True
                            )
                            
                            # Send password and initial commands
                            initial_input = '\n'.join(inputs) + '\n'
                            stdout, stderr = process.communicate(input=initial_input, timeout=timeout)
                            
                            # Check if we need to continue the game
                            if "Enter your guess:" in stdout:
                                # This is an interactive game, provide guidance
                                return {
                                    "success": True,
                                    "output": stdout,
                                    "interactive": True,
                                    "game_type": "binary_search",
                                    "instructions": "SSH连接成功！这是一个二进制搜索游戏。需要继续交互来猜测数字。",
                                    "next_step": "继续发送猜测数字（如：500, 250, 375等）"
                                }
                        else:
                            # Simple connection test
                            process = subprocess.Popen(
                                sshpass_cmd,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True
                            )
                            stdout, stderr = process.communicate(timeout=timeout)
                    except Exception as e:
                        return {"success": False, "error": f"SSH connection failed: {str(e)}"}
                
                # Fallback to expect if sshpass not available
                elif shutil.which('expect'):
                    try:
                        import tempfile
                        # Create expect script for SSH automation
                        commands_to_run = inputs[1:] if len(inputs) > 1 else []
                        expect_script = f'''#!/usr/bin/expect -f
set timeout 30
spawn {' '.join(full_command)}
expect {{
    "yes/no" {{
        send "yes\\r"
        exp_continue
    }}
    "password:" {{
        send "{password}\\r"
    }}
}}
'''
                        # Add commands to run after login
                        for cmd in commands_to_run:
                            expect_script += f'''
expect "$ "
send "{cmd}\\r"
'''
                        expect_script += '''
expect "$ "
send "exit\\r"
expect eof
'''
                        
                        with tempfile.NamedTemporaryFile(mode='w', suffix='.exp', delete=False) as f:
                            f.write(expect_script)
                            f.flush()
                            try:
                                process = subprocess.Popen(
                                    ["expect", f.name],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    text=True
                                )
                                stdout, stderr = process.communicate(timeout=timeout)
                            finally:
                                os.unlink(f.name)
                    except Exception as e:
                        return {"success": False, "error": f"SSH automation failed: {str(e)}"}
                else:
                    return {"success": False, "error": "SSH automation requires 'sshpass' or 'expect' tools. Install them first."}
            else:
                # Normal command execution - use current working directory
                process = subprocess.Popen(
                    full_command,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=self.current_working_dir  # Execute in tracked working directory
                )
                
                stdout, stderr = process.communicate(input=stdin_input, timeout=timeout)
            
            # Include error information even on success if there's stderr content
            result = {
                "success": process.returncode == 0,
                "output": stdout,
                "return_code": process.returncode,
                "command": ' '.join(full_command)
            }
            
            # Always include stderr if present, whether success or failure
            if stderr:
                result["error"] = stderr
                
            # If command failed, mark as unsuccessful
            if process.returncode != 0:
                result["success"] = False
                if not stderr:
                    result["error"] = f"Command failed with return code {process.returncode}"
                    
            return result
            
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
        import platform
        system = platform.system()
        
        if system == 'Linux':
            # Check for different Linux distributions
            if os.path.exists('/etc/debian_version') or os.path.exists('/etc/lsb-release'):
                return 'linux'  # Debian/Ubuntu/Kali
            elif os.path.exists('/etc/redhat-release') or os.path.exists('/etc/fedora-release'):
                return 'fedora'  # RedHat/CentOS/Fedora
            elif os.path.exists('/etc/arch-release'):
                return 'arch'   # Arch Linux
            else:
                return 'linux'  # Generic Linux
        elif system == 'Darwin':
            return 'darwin'  # macOS
        else:
            return 'unsupported'

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
