#!/usr/bin/env python3
"""
CTF Agent - LangChain-based intelligent CTF solving system
Supports multi-round interaction, tool calling, and file reading
"""

import os
import json
import base64
from pathlib import Path
from typing import Dict, List, Optional, Any, ClassVar, Set
from dataclasses import dataclass
from datetime import datetime
import tiktoken

from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.tools import BaseTool
from langchain.schema import BaseMessage, HumanMessage, AIMessage
from langchain.memory import ConversationBufferMemory
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_deepseek import ChatDeepSeek

@dataclass
class ConversationRound:
    """Conversation round record"""
    round_number: int
    human_input: str
    ai_response: str
    input_tokens: int
    output_tokens: int
    tools_used: List[str]
    timestamp: str
    input_source: str = "agent"  # "human" or "agent"

from typing import TypedDict, Literal
from pydantic import BaseModel

class ToolResult(BaseModel):
    """Tool execution result"""
    success: bool
    output: str
    error: str = ""

class FileReader(BaseTool):
    """Enhanced file reading tool with binary support"""
    name: str = "file_reader"
    description: str = "Read file contents from the challenge directory. Supports both text and binary files. Usage: Call this tool with <tool>file_reader</tool><input>filename</input> or <tool>file_reader</tool><input>filename|binary</input> for binary mode. Returns hex representation for binary files."
    
    def _run(self, file_path: str) -> str:
        try:
            # Check if binary mode is requested
            parts = file_path.split('|')
            target = parts[0].strip()
            mode = parts[1].strip().lower() if len(parts) > 1 else 'text'
            
            # Enhanced path resolution for extracted files
            resolved_target = self._resolve_file_path(target)
            
            if mode == 'binary' or mode == 'hex':
                # Read as binary and return hex representation
                with open(resolved_target, 'rb') as f:
                    content = f.read()
                hex_content = content.hex()
                # Also try to show printable ASCII if possible
                try:
                    ascii_content = ''.join(chr(b) if 32 <= b <= 126 else f'\\x{b:02x}' for b in content)
                    output = f"Hex: {hex_content}\nASCII representation: {ascii_content[:500]}{'...' if len(ascii_content) > 500 else ''}"
                except:
                    output = f"Hex: {hex_content}"
                return ToolResult(success=True, output=output).json()
            else:
                # Special handling for ZIP files - use zip_handler automatically
                if target.lower().endswith('.zip'):
                    try:
                        from src.agents.tools.zip_handler import create_zip_handler_tool
                        zip_tool = create_zip_handler_tool()
                        
                        # Ensure we have the full path for ZIP operations
                        zip_path = resolved_target
                        
                        result = zip_tool('extract_and_read', zip_path)
                        
                        if result.get('success'):
                            output_lines = [f"ZIP file: {target}"]
                            
                            if result.get('file_contents'):
                                for file_path, content_info in result['file_contents'].items():
                                    output_lines.append(f"\n=== File: {file_path} ===")
                                    if 'error' in content_info:
                                        output_lines.append(f"Error: {content_info['error']}")
                                    else:
                                        output_lines.append(f"Size: {content_info.get('size', 0)} bytes")
                                        if content_info.get('content'):
                                            output_lines.append(f"Content:\n{content_info.get('content')}")
                                        else:
                                            output_lines.append("Binary file")
                            
                            if result.get('binary_files') and not result.get('file_contents'):
                                # If no text content, just list binary files
                                for binary_file in result['binary_files']:
                                    output_lines.append(f"\n=== File: {binary_file} ===")
                                    output_lines.append("Binary file")
                            
                            return ToolResult(success=True, output='\n'.join(output_lines)).json()
                        else:
                            # ZIP handler failed, provide helpful error
                            error_msg = f"ZIP processing failed: {result.get('error', 'Unknown error')}"
                            if "not found" in result.get('error', '').lower():
                                error_msg += f"\nTried path: {zip_path}"
                                error_msg += f"\nCurrent working directory: {os.getcwd()}"
                            return ToolResult(success=False, output="", error=error_msg).json()
                    except Exception as e:
                        # Fallback to normal file reading if ZIP handler fails
                        print(f"ZIP handler failed: {e}")
                        pass
                
                # Try text mode first
                try:
                    with open(resolved_target, 'r', encoding='utf-8') as f:
                        content = f.read()
                    return ToolResult(success=True, output=content).json()
                except UnicodeDecodeError:
                    # If text fails, automatically try binary mode
                    with open(resolved_target, 'rb') as f:
                        content = f.read()
                    hex_content = content.hex()
                    ascii_repr = ''.join(chr(b) if 32 <= b <= 126 else f'\\x{b:02x}' for b in content[:200])
                    output = f"Binary file detected. Hex: {hex_content}\nASCII (first 200 bytes): {ascii_repr}{'...' if len(content) > 200 else ''}"
                    return ToolResult(success=True, output=output).json()
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e)).json()
    
    def _resolve_file_path(self, file_path: str) -> str:
        """Enhanced file path resolution that prioritizes challenge directory"""
        # If path exists directly, use it
        if os.path.exists(file_path):
            return file_path
        
        base = os.path.basename(file_path)
        
        # First, try to find the file in the current challenge directory
        current_challenge_dir = self._get_current_challenge_dir()
        if current_challenge_dir:
            # Check challenge subdirectories
            for root, dirs, files in os.walk(current_challenge_dir):
                if base in files:
                    found_path = os.path.join(root, base)
                    return found_path
            
            # Check if it's a relative path (e.g., extracted/home/ctf-player/drop-in/flag.png)
            if "/" in file_path or "\\" in file_path:
                relative_path = os.path.join(current_challenge_dir, file_path)
                if os.path.exists(relative_path):
                    return relative_path
        
        # Only search global challenges directory if not found in current challenge
        # Be careful to avoid file confusion between challenges
        # Global search (use carefully)
        matching_files = []
        for root, _, files in os.walk('challenges'):
            if base in files:
                file_path = os.path.join(root, base)
                # Check if in same challenge directory
                if current_challenge_dir and current_challenge_dir in file_path:
                    # Prioritize files in current challenge directory
                    matching_files.insert(0, file_path)
                else:
                    matching_files.append(file_path)
        
        if len(matching_files) > 1:
            # Multiple files found - prioritize current challenge directory
            current_challenge_files = [f for f in matching_files if current_challenge_dir and current_challenge_dir in f]
            if current_challenge_files:
                return current_challenge_files[0]
            else:
                # Warning: multiple files found but none in current challenge
                return matching_files[0]
        elif len(matching_files) == 1:
            return matching_files[0]
        
        # If all else fails, return original path (will cause error later)
        return file_path
    
    def _arun(self, file_path: str) -> str:
        return self._run(file_path)
    
    def _get_current_challenge_dir(self) -> str:
        """Get the current challenge directory based on working directory"""
        try:
            # Get current working directory
            cwd = os.getcwd()
            
            # Check if we're in a challenge directory
            if 'challenges' in cwd:
                # Find the challenge directory path
                parts = cwd.split(os.sep)
                challenges_index = parts.index('challenges')
                if challenges_index + 3 < len(parts):  # challenges/year/category/name
                    challenge_path = os.sep.join(parts[:challenges_index + 4])
                    if os.path.exists(challenge_path):
                        return challenge_path
            
            # Try to find recently accessed challenge directories
            base_dirs = ['/app/challenges', './challenges', 'challenges']
            for base_dir in base_dirs:
                if os.path.exists(base_dir):
                    # Look for the most recently modified challenge directory
                    try:
                        challenge_dirs = []
                        for root, dirs, files in os.walk(base_dir):
                            # Look for directories that have .json files (challenge descriptors)
                            if any(f.endswith('.json') for f in files):
                                challenge_dirs.append((root, os.path.getmtime(root)))
                        
                        if challenge_dirs:
                            # Use the most recently modified one
                            latest_dir = max(challenge_dirs, key=lambda x: x[1])[0]
                            return latest_dir
                    except Exception:
                        pass
            
            # Fallback: try to find from environment or context
            return None
        except Exception:
            return None

class CodeExecutor(BaseTool):
    """Code execution tool"""
    name: str = "code_executor"
    description: str = """Execute Python code in a secure environment with automatic package installation.

PYTHON CODE EXECUTION with shell command support via subprocess module.

Usage: <tool>code_executor</tool><input>your_python_code</input>

Available modules: base64, codecs, re, json, hashlib, binascii, struct, os, sys, math, random, datetime, itertools, collections, functools, subprocess
Auto-installs: Crypto (pycryptodome), sympy, gmpy2, numpy, requests

🔧 SHELL COMMANDS via subprocess:
Use subprocess.run() to execute shell commands:
- subprocess.run(['steghide', 'extract', '-sf', 'image.jpg'], capture_output=True, text=True)
- subprocess.run(['file', 'image.jpg'], capture_output=True, text=True)
- subprocess.run(['strings', 'file.bin'], capture_output=True, text=True)

Remember to print() results to see output!"""
    
    def _run(self, code: str) -> str:
        """Execute Python code with enhanced CTF environment"""
        try:
            # Auto-install common CTF packages if needed
            self._ensure_ctf_packages()
            
            # Create secure execution environment
            safe_globals = {
                # Built-in functions
                'print': print, 'str': str, 'bytes': bytes, 'ord': ord, 'chr': chr,
                'int': int, 'float': float, 'bool': bool, 'list': list, 'dict': dict,
                'tuple': tuple, 'set': set, 'len': len, 'range': range, 'enumerate': enumerate,
                'zip': zip, 'map': map, 'filter': filter, 'sum': sum, 'min': max, 'max': max,
                'sorted': sorted, 'reversed': reversed, 'abs': abs, 'round': round,
                'hex': hex, 'oct': oct, 'bin': bin, 'pow': pow,
                
                # Standard library modules
                'base64': __import__('base64'),
                'codecs': __import__('codecs'),
                're': __import__('re'),
                'json': __import__('json'),
                'hashlib': __import__('hashlib'),
                'binascii': __import__('binascii'),
                'struct': __import__('struct'),
                'os': __import__('os'),
                'sys': __import__('sys'),
                'math': __import__('math'),
                'random': __import__('random'),
                'datetime': __import__('datetime'),
                'itertools': __import__('itertools'),
                'collections': __import__('collections'),
                'functools': __import__('functools'),
                'operator': __import__('operator'),
                'time': __import__('time'),
                'io': __import__('io'),
                'subprocess': __import__('subprocess'),
            }
            
            # Try to import common CTF packages
            ctf_packages = {
                'requests': 'requests',
                'Crypto': 'Crypto',
                'sympy': 'sympy',
                'gmpy2': 'gmpy2',
                'numpy': 'numpy',
                'np': 'numpy',  # Common alias
            }
            
            for alias, module_name in ctf_packages.items():
                try:
                    safe_globals[alias] = __import__(module_name)
                except ImportError:
                    pass  # Package not available, skip
            
            # Capture print output
            import io
            import sys
            output = io.StringIO()
            sys.stdout = output
            
            try:
                # Execute code
                exec(code.strip(), safe_globals)
                
                # Get output
                result = output.getvalue().strip()
                
                # Restore stdout
                sys.stdout = sys.__stdout__
                
                # Check output
                if not result:
                    return json.dumps({
                        "success": True,
                        "output": "Code executed successfully but produced no output. Did you forget to print the result?"
                    })
                
                return json.dumps({
                    "success": True,
                    "output": result
                })
                
            except Exception as e:
                sys.stdout = sys.__stdout__
                return json.dumps({
                    "success": False,
                    "error": f"Code execution failed: {str(e)}",
                    "output": ""
                })
                
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"Tool execution failed: {str(e)}",
                "output": ""
            })
    
    def _ensure_ctf_packages(self):
        """Ensure common CTF packages are installed"""
        try:
            import subprocess
            import sys
            
            # Common CTF packages to auto-install
            packages = [
                'pycryptodome',  # Crypto library
                'requests',      # HTTP requests
                'sympy',         # Symbolic math
                'gmpy2',         # Fast math operations
            ]
            
            for package in packages:
                # Check if already installed
                try:
                    if package == 'pycryptodome':
                        __import__('Crypto')
                    else:
                        __import__(package)
                except ImportError:
                    # Try to install
                    try:
                        subprocess.check_call([
                            sys.executable, "-m", "pip", "install", package
                        ], capture_output=True, timeout=60)
                    except:
                        pass  # Installation failed, continue
        except:
            pass  # Auto-install failed, continue with available packages
    
    def _arun(self, code: str) -> str:
        return self._run(code)

# Import task tree and flag validator
from .flag_validator import FlagValidator
from .context_optimizer import ContextOptimizer
from .task_manager import TaskManager, TaskTree

class CTFAgent:
    """CTF solving Agent"""
    
    def __init__(self, llm_service: str = "deepseek", api_key: str = None, mode: str = "auto"):
        self.llm_service = llm_service
        self.api_key = api_key
        self.mode = mode  # "auto" or "hitl"
        self.llm = self._setup_llm()
        self.tools = self._setup_tools()
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        self.agent = self._create_agent()
        self.conversation_history: List[ConversationRound] = []
        self.current_round = 0
        self.last_tool_results: List[str] = []
        self.last_flag_candidate = None
        self.context_optimizer = ContextOptimizer()

        self.progress_log: List[Dict[str, Any]] = []
        
        # Token calculator
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
    
        # Simple task tree and flag validator
        self.task_tree = None
        self.flag_tool = None
        # Challenge info 
        self.challenge_info = {}
    
    def _setup_llm(self):
        """Setup LLM with timeout and retry settings"""
        if self.llm_service == "deepseek":
            return ChatDeepSeek(
                api_key=self.api_key,
                model="deepseek-chat",
                temperature=0.7,
                timeout=120,  # 2 minutes timeout
                max_retries=3
            )
        elif self.llm_service == "openai":
            return ChatOpenAI(
                api_key=self.api_key,
                model="gpt-4",
                temperature=0.7,
                timeout=120,
                max_retries=3
            )
        elif self.llm_service == "anthropic":
            return ChatAnthropic(
                api_key=self.api_key,
                model="claude-3-sonnet-20240229",
                temperature=0.7,
                timeout=120,
                max_retries=3
            )
        else:
            raise ValueError(f"Unsupported LLM service: {self.llm_service}")
    
    def _setup_tools(self):
        """Setup tools with flag validator and task reporter"""
        # Create flag validator tool
        self.flag_validator_tool = FlagValidator()
        
        # Create task reporter tool
        self.task_reporter_tool = TaskManager()
        
        tools = [
            FileReader(),
            CodeExecutor(),
            self.flag_validator_tool,
            self.task_reporter_tool,
        ]
        
        # SSH tool removed - use code_executor with paramiko instead
        print("ℹ️  SSH connections handled via code_executor with paramiko library")
        
        # Add network connector tool if available
        try:
            from src.agents.tools.network_connector import create_network_connector_tool
            network_tool = create_network_connector_tool()
            
            class NetworkConnectorTool(BaseTool):
                name: str = "network_connector"
                description: str = """Connect to remote services for CTF challenges (oracles, APIs, etc).

Usage: <tool>network_connector</tool><input>{"host": "hostname", "port": 1234, "method": "nc", "send": "data"}</input>"""
                
                def _run(self, query: str) -> str:
                    try:
                        import json as json_lib
                        import shlex
                        import re
                        
                        # Handle quoted strings properly
                        query = query.strip()
                        
                        # Try to parse as JSON first
                        try:
                            params = json_lib.loads(query)
                            if isinstance(params, dict):
                                host = params.get("host")
                                port = params.get("port")
                                method = params.get("method", "nc")
                                send_data = params.get("send", "")
                                
                                if not host or not port:
                                    return json.dumps({"success": False, "error": "JSON format requires 'host' and 'port' fields"})
                                
                                result = network_tool(host, port, method, send_data, 30)
                                return json.dumps(result, ensure_ascii=False, indent=2)
                        except json_lib.JSONDecodeError:
                            pass  # Not JSON, try string format
                        
                        # Try to parse with shlex for proper quote handling
                        try:
                            parts = shlex.split(query)
                        except:
                            # Fallback to simple split if shlex fails
                            parts = query.split()
                        
                        # Handle empty or whitespace-only input
                        if not parts or all(p.strip() == '' for p in parts):
                            return json.dumps({"success": False, "error": "Empty input. Usage: host:port or host port [method] [send_data] OR JSON: {'host': 'hostname', 'port': 1234, 'method': 'nc', 'send': 'data'}"})
                        
                        if ':' in parts[0]:
                            # Format: host:port [method] [send_data]
                            host_port = parts[0].split(':', 1)
                            if len(host_port) != 2 or not host_port[1].strip():
                                return json.dumps({"success": False, "error": "Invalid host:port format. Usage: host:port [method] [send_data]"})
                            host, port_str = host_port
                            port = int(port_str)
                            method = parts[1] if len(parts) > 1 else "nc"
                            send_data = parts[2] if len(parts) > 2 else ""
                        else:
                            # Format: host port [method] [send_data]
                            if len(parts) < 2:
                                return json.dumps({"success": False, "error": "Usage: host:port or host port [method] [send_data] OR JSON: {'host': 'hostname', 'port': 1234, 'method': 'nc', 'send': 'data'}"})
                            host = parts[0]
                            if not parts[1].strip():
                                return json.dumps({"success": False, "error": "Port cannot be empty. Usage: host port [method] [send_data]"})
                            port = int(parts[1])
                            method = parts[2] if len(parts) > 2 else "nc"
                            send_data = parts[3] if len(parts) > 3 else ""
                        
                        # Handle escape sequences in send_data
                        if send_data:
                            send_data = send_data.replace('\\n', '\n').replace('\\t', '\t').replace('\\r', '\r')
                        
                        result = network_tool(host, port, method, send_data, 30)
                        return json.dumps(result, ensure_ascii=False, indent=2)
                        
                    except (ValueError, IndexError) as e:
                        return json.dumps({"success": False, "error": f"Invalid input format: {str(e)}. Usage: host:port or host port [method] [send_data]"})
                    except Exception as e:
                        return json.dumps({"success": False, "error": str(e)})
                
                def _arun(self, query: str) -> str:
                    return self._run(query)
            
            tools.append(NetworkConnectorTool())
            print("✅ Network connector tool loaded")
        except ImportError as e:
            print(f"⚠️  Network tool not available: {e}")
        
        # Add JavaScript decryptor tool if available
        try:
            from src.agents.tools.js_executor import create_js_executor_tool
            js_tool = create_js_executor_tool()
            
            class JSExecutorTool(BaseTool):
                name: str = "js_executor"
                description: str = """Execute JavaScript code and decrypt JavaScript-based encryption for CTF challenges.
                
Usage: <tool>js_executor</tool><input>{"action": "execute|decrypt", ...}</input>

For JavaScript execution:
<tool>js_executor</tool><input>{"action": "execute", "code": "javascript_code", "engine": "auto"}</input>

For JavaScript decryption:
<tool>js_executor</tool><input>{"action": "decrypt", "encrypted": "encrypted_string", "algorithm": "xor", "key": "key_string"}</input>

Execution engines:
- auto: Automatically select best available engine (recommended)
- node: Use Node.js (fastest, most reliable)
- deno: Use Deno (secure, modern)  
- python: Use Python JavaScript engines (fallback)

Decryption algorithms:
- xor: XOR decryption (most common in CTF)
- js_auto: Smart JavaScript string handling (recommended for JS challenges)
- caesar: Caesar cipher with shift
- substitution: Simple substitution cipher
- custom: Custom JavaScript decryption code

Examples:
- <tool>js_executor</tool><input>{"action": "execute", "code": "var x = 1 + 2; console.log(x);", "engine": "auto"}</input>
- <tool>js_executor</tool><input>{"action": "decrypt", "encrypted": "àÒÆÞ¦È¬ëÙ£ÖÓÚåÛÑ¢ÕÓ¨ÍÕÄ¦í", "algorithm": "js_auto", "key": "picoctf"}</input>
- <tool>js_executor</tool><input>{"action": "decrypt", "encrypted": "KHOOR", "algorithm": "caesar", "shift": 3}</input>

Note: Use 'js_auto' algorithm for JavaScript bookmarklet challenges - it automatically handles encoding issues."""
                
                def _run(self, query: str) -> str:
                    try:
                        import json as json_lib
                        
                        # Parse JSON input
                        params = json_lib.loads(query)
                        if not isinstance(params, dict):
                            return json.dumps({"success": False, "error": "Input must be a JSON object"})
                        
                        # Execute JavaScript tool
                        result = js_tool(**params)
                        return json.dumps(result, ensure_ascii=False, indent=2)
                        
                    except json_lib.JSONDecodeError as e:
                        return json.dumps({"success": False, "error": f"Invalid JSON: {str(e)}"})
                    except Exception as e:
                        return json.dumps({"success": False, "error": str(e)})
                
                def _arun(self, query: str) -> str:
                    return self._run(query)
            
            tools.append(JSExecutorTool())
            print("✅ JavaScript executor tool loaded")
        except ImportError as e:
            print(f"⚠️  JavaScript executor tool not available: {e}")
        
        # Add system command tool if available
        try:
            from src.agents.tools.system_command import create_system_command_tool
            sys_tool = create_system_command_tool()
            
            class SystemCommandTool(BaseTool):
                name: str = "system_command"
                description: str = """Execute system commands for CTF challenges on Kali Linux.

Available commands: openssl, base64, curl, python3, ls, cat, file, xxd, strings, etc.

Usage: <tool>system_command</tool><input>{"command": "file", "args": ["secret.enc"]}</input>"""
                
                def _run(self, query: str) -> str:
                    try:
                        import json as json_lib
                        
                        # Handle quoted strings properly
                        query = query.strip()
                        
                        # Fix common JSON formatting issues
                        if query.endswith('}>'):
                            query = query[:-1]  # Remove trailing >
                        if query.endswith('}'):
                            pass  # Already correct
                        
                        # Try to parse as JSON first
                        try:
                            params = json_lib.loads(query)
                            if isinstance(params, dict):
                                command = params.get("command")
                                args = params.get("args", [])
                                input_data = params.get("input", "")
                                
                                if not command:
                                    return json_lib.dumps({"success": False, "error": "JSON format requires 'command' field"})
                                
                                result = sys_tool(command, args, input_data, 30, True)
                                return json_lib.dumps(result)
                        except json_lib.JSONDecodeError as e:
                            # If JSON fails, return a helpful error message
                            return json_lib.dumps({
                                "success": False, 
                                "error": f"Invalid JSON format: {str(e)}. Use proper JSON like {{\"command\": \"cmd\", \"args\": [\"arg1\"], \"input\": \"data\"}} or simple string format like 'cmd arg1 arg2'"
                            })
                        
                        # Parse input - support command with args and optional stdin
                        if '<' in query:
                            # Format: command args < input_data
                            cmd_part, input_data = query.split('<', 1)
                            input_data = input_data.strip()
                        else:
                            # Format: command args
                            cmd_part = query
                            input_data = ""
                        
                        parts = cmd_part.strip().split()
                        if not parts:
                            return json.dumps({"success": False, "error": "No command provided. Use JSON: {'command': 'cmd', 'args': ['arg1'], 'input': 'data'} or string: 'cmd arg1 arg2'"})
                        
                        command = parts[0]
                        args = parts[1:] if len(parts) > 1 else []
                        
                        result = sys_tool(command, args, input_data, 30, True)
                        return json.dumps(result)
                        
                    except Exception as e:
                        return json.dumps({"success": False, "error": str(e)})
                
                def _arun(self, query: str) -> str:
                    return self._run(query)
            
            tools.append(SystemCommandTool())
            print("✅ System command tool loaded")
        except ImportError as e:
            print(f"⚠️  System command tool not available: {e}")
        
        # Add ZIP handler tool if available
        try:
            from src.agents.tools.zip_handler import create_zip_handler_tool
            zip_tool = create_zip_handler_tool()
            
            class ZipHandlerTool(BaseTool):
                name: str = "zip_handler"
                description: str = """Handle ZIP file operations for CTF challenges.

Usage: <tool>zip_handler</tool><input>{"action": "list", "zip_path": "file.zip"}</input>"""
                
                def _run(self, query: str) -> str:
                    try:
                        import json as json_lib
                        
                        # Handle quoted strings and fix common formatting issues
                        query = query.strip()
                        if query.endswith('}>'):
                            query = query[:-1]  # Remove trailing >
                        
                        # Parse JSON input
                        params = json_lib.loads(query)
                        
                        if not isinstance(params, dict):
                            return json_lib.dumps({"success": False, "error": "Input must be JSON object"})
                        
                        action = params.get("action")
                        zip_path = params.get("zip_path")
                        
                        if not action or not zip_path:
                            return json_lib.dumps({"success": False, "error": "Both 'action' and 'zip_path' are required"})
                        
                        result = zip_tool(
                            action=action,
                            zip_path=zip_path,
                            target_file=params.get("target_file"),
                            extract_to=params.get("extract_to"),
                            encoding=params.get("encoding", "utf-8")
                        )
                        
                        return json_lib.dumps(result)
                        
                    except json_lib.JSONDecodeError as e:
                        return json_lib.dumps({"success": False, "error": f"Invalid JSON format: {str(e)}. Expected format: {{\"action\": \"list|extract|read|extract_and_read\", \"zip_path\": \"file.zip\"}}"})
                    except Exception as e:
                        return json_lib.dumps({"success": False, "error": str(e)})
                
                def _arun(self, query: str) -> str:
                    return self._run(query)
            
            tools.append(ZipHandlerTool())
            print("✅ ZIP handler tool loaded")
        except ImportError as e:
            print(f"⚠️  ZIP handler tool not available: {e}")
        
        # Add QR code reader tool if available
        try:
            from src.agents.tools.qrcode_reader import create_qrcode_reader_tool
            qr_tool = create_qrcode_reader_tool()
            
            class QRCodeReaderTool(BaseTool):
                name: str = "qrcode_reader"
                description: str = """Read QR codes from images and extract text content for CTF challenges.

Usage: <tool>qrcode_reader</tool><input>{"image_path": "path/to/image.png", "method": "auto"}</input>

Methods:
- auto: Automatically try multiple methods (recommended)
- pyzbar: Use pyzbar library (fast, reliable, auto-installs if missing)
- opencv: Use OpenCV (good for complex images)

Features:
- Automatic dependency installation (pyzbar will be installed if missing)
- Multiple fallback methods for maximum compatibility
- Smart image path resolution (finds files in challenge directories)

Examples:
- <tool>qrcode_reader</tool><input>{"image_path": "flag.png", "method": "auto"}</input>
- <tool>qrcode_reader</tool><input>{"image_path": "challenge.png"}</input>"""
                
                def _run(self, query: str) -> str:
                    try:
                        import json as json_lib
                        
                        # Handle quoted strings and fix common formatting issues
                        query = query.strip()
                        if query.endswith('}>'):
                            query = query[:-1]  # Remove trailing >
                        
                        # Parse JSON input
                        params = json_lib.loads(query)
                        
                        if not isinstance(params, dict):
                            return json_lib.dumps({"success": False, "error": "Input must be JSON object"})
                        
                        image_path = params.get("image_path")
                        method = params.get("method", "auto")
                        
                        if not image_path:
                            return json_lib.dumps({"success": False, "error": "image_path is required"})
                        
                        result = qr_tool(image_path, method)
                        return json_lib.dumps(result)
                        
                    except json_lib.JSONDecodeError as e:
                        return json_lib.dumps({"success": False, "error": f"Invalid JSON format: {str(e)}. Expected format: {{\"image_path\": \"image.png\", \"method\": \"auto\"}}"})
                    except Exception as e:
                        return json_lib.dumps({"success": False, "error": str(e)})
                
                def _arun(self, query: str) -> str:
                    return self._run(query)
            
            tools.append(QRCodeReaderTool())
            print("✅ QR code reader tool loaded")
        except ImportError as e:
            print(f"⚠️  QR code reader tool not available: {e}")
        
        # Add package installer tool if available
        try:
            from src.agents.tools.package_installer import create_package_installer_tool
            pkg_tool = create_package_installer_tool()
            
            class PackageInstallerTool(BaseTool):
                name: str = "package_installer"
                description: str = "Install Python packages for CTF challenges. Usage: Call with <tool>package_installer</tool><input>package_name1 package_name2</input> or <tool>package_installer</tool><input>auto_common</input> for common CTF packages"
                
                def _run(self, query: str) -> str:
                    try:
                        query = query.strip()
                        
                        if query == "auto_common":
                            # Install common CTF packages
                            result = pkg_tool(auto_install_common=True)
                        else:
                            # Install specific packages
                            packages = query.split() if query else []
                            result = pkg_tool(packages=packages)
                        
                        return json.dumps(result)
                        
                    except Exception as e:
                        return json.dumps({"success": False, "error": str(e)})
                
                def _arun(self, query: str) -> str:
                    return self._run(query)
            
            tools.append(PackageInstallerTool())
            print("✅ Package installer tool loaded")
        except ImportError as e:
            print(f"⚠️  Package installer tool not available: {e}")
        

        return tools
    
    def _create_agent(self):
        """Create Agent"""
        from src.prompts import PromptRegistry
        
        # Get system prompt from registry
        registry = PromptRegistry()
        system_prompt = registry.get_system_prompt()
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])
        
        # Create agent executor for better tool handling
        print(f"\n🔧 Creating agent with {len(self.tools)} tools...")
        
        # Use structured output for better tool calling
        agent = create_openai_functions_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )
        
        # Control LangChain internal logging: disabled by default, enable via LC_VERBOSE env var
        lc_verbose = bool(os.getenv("LC_VERBOSE", ""))
        executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=lc_verbose,
            handle_parsing_errors=True,
            max_iterations=1,  # Execute one step at a time
            early_stopping_method="generate",
            return_intermediate_steps=True
        )
        
        print(f"Agent created successfully with tools: {[tool.name for tool in self.tools]} + task_tree")
        return executor
    
    def start_challenge(self, challenge_data: Dict) -> str:
        """Start solving challenge"""
        self.current_round = 0
        # Store challenge meta for context-aware prompts
        try:
            self.challenge_info = {
                "title": challenge_data.get('title', 'Unknown'),
                "category": challenge_data.get('category', 'Unknown'),
                "difficulty": challenge_data.get('difficulty', 'Unknown'),
                "points": challenge_data.get('points', 'Unknown')
            }
        except Exception:
            self.challenge_info = {}
        
        # Read file contents (eagerly include before first LLM call)
        files_content = self.read_challenge_files(challenge_data)
        challenge_data['files'] = [os.path.basename(f) for f in challenge_data.get('files', [])]
        
        # Get prompt from CTFPromptManager (ensure description is preserved from canonical JSON)
        from src.agents.ctf_prompts import CTFPromptManager
        prompt_manager = CTFPromptManager()
        base_prompt = prompt_manager.get_prompt(
            challenge_type=challenge_data.get('category', 'General Skills'),
            challenge_data=challenge_data
        )

        # Configure per-challenge task tree storage
        try:
            year = str(challenge_data.get('year', '2024'))
            category = challenge_data.get('category', 'unknown')
            title_slug = challenge_data.get('title', 'unknown').lower().replace(' ', '_')
            
            # Create challenge directory path
            cdir = Path(f"challenges/{year}/{category}/{title_slug}")
            cdir.mkdir(parents=True, exist_ok=True)
            
            # Simple filename based on mode only
            task_tree_filename = f"task_tree_{self.mode}.json"
            task_tree_path = cdir / task_tree_filename
            
            # Initialize task tree
            challenge_title = challenge_data.get('title', 'Unknown Challenge')
            self.task_tree = TaskTree(
                challenge_title=challenge_title,
                storage_path=str(task_tree_path)
            )
            
            # Connect task reporter to task tree
            if hasattr(self, 'task_reporter_tool') and hasattr(self.task_reporter_tool, 'set_task_tree'):
                self.task_reporter_tool.set_task_tree(self.task_tree)
            elif hasattr(self, 'task_reporter_tool'):
                # TaskManager doesn't have set_task_tree method, skip this step
                pass
            
            print(f"🔄 Task tree initialized: {task_tree_path}")
                
        except Exception as e:
            print(f"Warning: Could not initialize task tree: {e}")
            # Create fallback task tree
            self.task_tree = TaskTree(challenge_title="Challenge")
        
        # Add task tree instructions from prompts registry
        from src.prompts import PromptRegistry
        registry = PromptRegistry()
        task_tree_instructions = registry.get_task_tree_management_prompt()
        
        # Add current working directory info with actual available files
        cwd = os.getcwd()
        
        # Get list of challenge-relevant files only
        available_files = []
        try:
            # Get challenge files from challenge data
            challenge_files = challenge_data.get('files', [])
            for file_path in challenge_files:
                filename = os.path.basename(file_path)
                if os.path.exists(filename):
                    available_files.append(f"  - {filename}")
            
            # Add any other obvious challenge files (common patterns)
            current_files = [f for f in os.listdir('.') if os.path.isfile(f)]
            challenge_extensions = {'.zip', '.tar', '.gz', '.txt', '.png', '.jpg', '.jpeg', '.pdf', '.pcap', '.bin'}
            exclude_patterns = {'auto_', 'task_tree', '.json'}
            
            for file in current_files:
                # Include if it has challenge-like extension and isn't an auto-generated file
                if (any(file.endswith(ext) for ext in challenge_extensions) and 
                    not any(pattern in file for pattern in exclude_patterns) and
                    f"  - {file}" not in available_files):
                    available_files.append(f"  - {file}")
            
            # Check for extracted directory - show all extracted files as they're challenge content
            if os.path.exists('extracted'):
                extracted_files = []
                for root, dirs, files in os.walk('extracted'):
                    for file in files:
                        rel_path = os.path.relpath(os.path.join(root, file), '.')
                        extracted_files.append(f"  - {rel_path}")
                if extracted_files:
                    available_files.append("  Challenge files extracted:")
                    available_files.extend(extracted_files)
        except Exception:
            pass
        
        files_info = "\n".join(available_files) if available_files else "  (no files detected yet)"
        
        working_dir_info = f"\nCURRENT WORKING DIRECTORY: {cwd}\n" \
                          f"Challenge files available:\n{files_info}\n" \
                          f"When specifying file paths, you can use:\n" \
                          f"- Absolute paths: {cwd}/filename\n" \
                          f"- Relative paths: filename (files will be auto-located)\n" \
                          f"- Extracted files: extracted/path/to/file\n" 
        
        # Format the complete initial prompt with content length check
        if files_content:
            # Check if files_content is too large before including it
            content_size = len(files_content)
            print(f"\n📋 File Content Statistics:")
            print(f"   - Files content size: {content_size:,} characters")
            
            if content_size > 50000:  # 50KB limit for file content
                print(f"⚠️  File content too large ({content_size:,} chars), truncating...")
                files_content = files_content[:50000] + "\n\n... (file content truncated - use tools to read specific files)"
                print(f"   - Truncated to {len(files_content):,} characters")
            
            file_section = f"\n{working_dir_info}\nHere are the file contents to analyze:\n{files_content}"
        else:
            file_section = f"\n{working_dir_info}"
        
        initial_prompt = f"{base_prompt}\n{file_section}\n\n{task_tree_instructions}\n\n{registry.get_initial_challenge_suffix()}"
        
        # Debug information
        print(f"Available tools: {[tool.name for tool in self.tools]}")
        print(f"LLM service: {self.llm_service}")
        print(f"Initial prompt length: {len(initial_prompt)} characters")
        
        # Test tool functionality
        print("\n🔧 Testing tool functionality...")
        test_result = self.tools[1]._run("print('Hello from tool test')")
        print(f"Tool test result: {test_result}")
        
        # Test tool registration
        print(f"\n🔧 Tool registration test:")
        for i, tool in enumerate(self.tools):
            print(f"  Tool {i}: {tool.name}")
        
        return self.interact(initial_prompt)
    
    def interact(self, user_input: str, input_source: str = "agent") -> str:
        """Interact with LLM - execute one step at a time
        
        Args:
            user_input: The input text to send to LLM
            input_source: "human" if from human input, "agent" if from agent logic
        """
        self.current_round += 1
        
        try:
            # Unified round start identifier
            print(f"\n{'='*90}")
            print(f"Round {self.current_round}")
            print(f"{'='*90}")
            
            # Show prompt sent to LLM
            print("\n📤 Sending to LLM:")
            print("-"*90)
            print(user_input)
            print("-"*90)
            
            # Check content length before sending to LLM
            total_content = user_input
            for msg in self.memory.chat_memory.messages:
                if hasattr(msg, 'content'):
                    total_content += str(msg.content)
            
            content_length = len(total_content)
            print(f"\n📊 Content Statistics:")
            print(f"   - Input length: {len(user_input):,} characters")
            print(f"   - Total content: {content_length:,} characters")
            
            # Estimate tokens (rough approximation: 4 chars = 1 token)
            estimated_tokens = content_length // 4
            print(f"   - Estimated tokens: {estimated_tokens:,}")
            
            if estimated_tokens > 120000:  # Leave some buffer for response
                print(f"⚠️  WARNING: Content too large ({estimated_tokens:,} tokens estimated)")
                print("   - Truncating content to prevent context overflow...")
                
                # Truncate the user input if it's too long
                if len(user_input) > 100000:  # 100KB limit for user input
                    user_input = user_input[:100000] + "\n\n... (content truncated due to size - focus on key information above)"
                    print(f"   - Input truncated to {len(user_input):,} characters")
                
                # Clear chat history if it's getting too large
                chat_messages = self.memory.chat_memory.messages
                if len(chat_messages) > 10:  # Keep only last 10 messages
                    print(f"   - Clearing old chat history (keeping last 10 of {len(chat_messages)} messages)")
                    self.memory.chat_memory.messages = chat_messages[-10:]
            
            # Call LLM
            response = self.agent.invoke({
                "input": user_input,
                "chat_history": self.memory.chat_memory.messages
            })
            
            # Parse LLM response
            ai_response = response.get('output', '')
            print("\n📥 LLM Response:")
            print("-"*90)
            print(ai_response)
            print("-"*90)
            
            # Extract tasks from LLM response
            if self.task_tree:
                extracted_count = self.task_tree.extract_tasks_from_response(ai_response)
                if extracted_count == 0:
                    print("⚠️  No task status updates found - LLM may not be following task management guidelines")
            
            # Handle tool calls
            tools_used = []
            tool_results = []
            
            # Handle LangChain agent tool calls
            if 'intermediate_steps' in response:
                steps = response.get('intermediate_steps') or []
                if steps:
                    print("\n🔧 Tool Executions:")
                    print("-"*90)
                    for step in steps:
                        if len(step) >= 2:
                            action = step[0]
                            observation = step[1]
                            tool_name = getattr(action, 'tool', 'unknown')
                            tool_input = getattr(action, 'tool_input', '')
                            
                            print(f"📌 Tool: {tool_name}")
                            print(f"Input: {tool_input}")
                            
                            # Parse tool return
                            display_result = self._parse_tool_result(observation)
                            print(f"📋 Result: {display_result}")
                            
                            tools_used.append(tool_name)
                            tool_results.append(display_result)
                            
                            # Add to task tree
                            if self.task_tree:
                                self.task_tree.add_tool_result(tool_name, str(tool_input), str(display_result))
                    print("-"*90)
            
            # Handle manual <tool> tag calls
            if not tools_used and ("<tool>" in ai_response and "</tool>" in ai_response):
                print("\n🔧 Tool Executions:")
                tool_calls = self._parse_tool_calls(ai_response)
                for tool_name, tool_input in tool_calls:
                    print(f"📌 Tool: {tool_name}")
                    print(f"Input: {tool_input}")
                    
                    # Execute tool
                    display_result = self._execute_tool(tool_name, tool_input)
                    print(f"📋 Result: {display_result}")
                    
                    tools_used.append(tool_name)
                    tool_results.append(display_result)
                    
                    # Add to task tree
                    if self.task_tree:
                        self.task_tree.add_tool_result(tool_name, tool_input, display_result)
                print("-"*90)
            
            # Save task tree
            if self.task_tree:
                self.task_tree.save()
            
            # Show task tree
            self._display_task_tree()
            
            # Flag detection
            self._detect_flags(ai_response, tool_results)
            
            # Save tool results and conversation history
            self.last_tool_results = tool_results
            self.memory.chat_memory.add_user_message(user_input)
            self.memory.chat_memory.add_ai_message(ai_response)
            
            # Save round record
            round_record = ConversationRound(
                round_number=self.current_round,
                human_input=user_input,
                ai_response=ai_response,
                input_tokens=self.count_tokens(user_input),
                output_tokens=self.count_tokens(ai_response),
                tools_used=tools_used,
                timestamp=str(datetime.now()),
                input_source=input_source
            )
            self.conversation_history.append(round_record)
            
            # Show round summary
            print(f"\n📑 Round {self.current_round} Summary:")
            print(f"Tools Used: {len(tools_used)}")
            print(f"Results Generated: {len(tool_results)}")
            # Show current round token usage
            if self.conversation_history:
                current_round_record = self.conversation_history[-1]
                input_tokens = current_round_record.input_tokens
                output_tokens = current_round_record.output_tokens
                total_tokens = input_tokens + output_tokens
                print(f"Input Tokens: {input_tokens}")
                print(f"Output Tokens: {output_tokens}")
                print(f"Round Total: {total_tokens}")
            print("-"*90)
            
            return ai_response
            
        except Exception as e:
            error_msg = f"Round {self.current_round} failed: {str(e)}"
            print(error_msg)
            return error_msg
    
    def _parse_tool_result(self, observation: str) -> str:
        """Parse tool return result"""
        try:
            parsed = json.loads(observation) if isinstance(observation, str) else None
            if parsed and isinstance(parsed, dict) and 'success' in parsed:
                if parsed.get('success'):
                    return parsed.get('output', '').strip()
                else:
                    return f"ERROR: {parsed.get('error', '')}"
        except Exception:
            pass
        
        # 清理常见包裹符
        result = str(observation).strip()
        if result.startswith("'") and result.endswith("'"):
            result = result[1:-1]
        if result.startswith('b"') or result.startswith("b'"):
            result = result[2:-1]
        
        # 确保结果不为空
        if not result:
            return "No output generated"
        
        return result
    
    def _parse_tool_calls(self, ai_response: str) -> List[tuple]:
        """解析AI响应中的工具调用"""
        tool_calls = []
        segments = ai_response.split("<tool>")[1:]
        
        for seg in segments:
            if "</tool>" not in seg:
                continue
            tool_name = seg.split("</tool>")[0].strip()
            
            if "<input>" not in seg or "</input>" not in seg:
                continue
            tool_input = seg.split("<input>")[1].split("</input>")[0].strip()
            
            tool_calls.append((tool_name, tool_input))
        
        return tool_calls
    
    def _execute_tool(self, tool_name: str, tool_input: str) -> str:
        """执行指定的工具"""
        matched_tool = next((t for t in self.tools if t.name == tool_name), None)
        if not matched_tool:
            return f"ERROR: Tool '{tool_name}' not found"
        
        try:
            print(f"🔧 Executing {tool_name} with input: {tool_input[:100]}{'...' if len(tool_input) > 100 else ''}")
            raw_result = matched_tool._run(tool_input)
            print(f"🔧 Raw result from {tool_name}: {raw_result[:200]}{'...' if len(str(raw_result)) > 200 else ''}")
            parsed_result = self._parse_tool_result(raw_result)
            print(f"🔧 Parsed result from {tool_name}: {parsed_result[:200]}{'...' if len(str(parsed_result)) > 200 else ''}")
            return parsed_result
        except Exception as e:
            error_msg = f"ERROR: Tool execution failed: {e}"
            print(f"🔧 {error_msg}")
            return error_msg
    
    def _display_task_tree(self) -> None:
        """显示任务树"""
        print(f"\n📋 Task Tree (Current Progress):")
        
        if self.task_tree:
            tree_display = self.task_tree.get_tree_display()
            print(tree_display)
        else:
            print("Task tree not available")
        
        print("-"*90)
    
    def _detect_flags(self, ai_response: str, tool_results: List[str]) -> None:
        """检测flag"""
        import re
        
        print(f"\n🔍 Flag Detection (Round {self.current_round}):")
        
        # 合并所有文本
        all_text = ai_response + " " + " ".join(tool_results or [])
        
        # 查找 picoCTF{...} 格式，支持变形如 picoC:F{...}
        flag_pattern = r'pico[C:]?[T:]?F\{[^}]+\}'
        candidates = re.findall(flag_pattern, all_text, re.IGNORECASE)
        
        # 去重
        unique_candidates = list(dict.fromkeys(candidates))
        
        if unique_candidates:
            print("🚩 Found potential flag(s):")
            for i, candidate in enumerate(unique_candidates, 1):
                print(f"   {i}. {candidate}")
                # Always save the last (most recent) candidate
                self.last_flag_candidate = candidate
            print(f"DEBUG: Set last_flag_candidate to: {self.last_flag_candidate}")

        else:
            print("   No flags found in this round")
        
        print("-"*90)
    
    def get_conversation_summary(self) -> Dict[str, Any]:
        """Get conversation summary with full records"""
        summary = {
            "total_rounds": len(self.conversation_history),
            "total_input_tokens": sum(r.input_tokens for r in self.conversation_history),
            "total_output_tokens": sum(r.output_tokens for r in self.conversation_history),
            "total_tokens": sum(r.input_tokens + r.output_tokens for r in self.conversation_history),
            "flag": {
                "value": None,
                "found": False,
                "format": "picoCTF{...}",
                "verified": False
            },
            "conversation_history": [
                {
                    "round": r.round_number,
                    "human_input": r.human_input,
                    "ai_response": r.ai_response,
                    "input_tokens": r.input_tokens,
                    "output_tokens": r.output_tokens,
                    "tools_used": r.tools_used,
                    "timestamp": r.timestamp
                }
                for r in self.conversation_history
            ],
            "rounds": [
                {
                    "round": r.round_number,
                    "input_tokens": r.input_tokens,
                    "output_tokens": r.output_tokens,
                    "tools_used": r.tools_used
                }
                for r in self.conversation_history
            ],
            "progress_log": self.progress_log
        }
        return summary
    
    def get_task_tree_summary(self, max_recent_steps: int = 3) -> str:
        """Get a summary of the task tree for LLM context (recent steps only)"""
        if self.task_tree:
            return self.task_tree.get_recent_progress()
        else:
            return "Task Progress: No steps recorded yet"
    

    
    def extract_flag_from_conversation(self) -> Optional[str]:
        """Extract flag from conversation history"""
        import re
        
        # Look for picoCTF{...} pattern in all responses
        picoctf_pattern = r'picoCTF\{[^}]+\}'
        
        for round_record in reversed(self.conversation_history):  # Start from latest
            # Check AI response
            match = re.search(picoctf_pattern, round_record.ai_response, re.IGNORECASE)
            if match:
                return match.group(0)
            
            # Check human input
            match = re.search(picoctf_pattern, round_record.human_input, re.IGNORECASE)
            if match:
                return match.group(0)
        
        return None
    
    def save_conversation(self, file_path: str):
        """Save conversation record"""
        summary = self.get_conversation_summary()

        summary['progress_log'] = self.progress_log
        # Attach task_tree snapshot for traceability
        try:
            tpath = getattr(self, 'global_task_tree_path', None)
            if tpath and Path(tpath).exists():
                with open(tpath, 'r', encoding='utf-8') as tf:
                    summary['task_tree'] = json.load(tf)
        except Exception:
            pass
        summary['conversation_history'] = [
            {
                "round": round.round_number,
                # Use appropriate field name based on actual input source
                ("human_input" if getattr(round, 'input_source', 'agent') == "human" else "agent_input"): round.human_input,
                "ai_response": round.ai_response,
                "input_tokens": round.input_tokens,
                "output_tokens": round.output_tokens,
                "tools_used": round.tools_used,
                "timestamp": round.timestamp
            }
            for round in self.conversation_history
        ]
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

    def _normalize_task_tree_file(self) -> None:
        """Normalize any specific titles in persisted task tree into generic ones."""
        p = getattr(self, 'global_task_tree_path', None)
        if not p or not Path(p).exists():
            return
        try:
            with open(p, 'r', encoding='utf-8') as tf:
                tree = json.load(tf)
            # Reuse TaskTreeTool normalization logic (inline minimal):
            def norm(node: Dict[str, Any]):
                if not isinstance(node, dict):
                    return
                title = node.get('title')
                if title not in {"Hypothesis", "Step", "Result"}:
                    node['title'] = 'Step'
                notes = node.get('notes', '')
                if isinstance(notes, str) and notes.startswith('[orig-title:'):
                    end = notes.find(']')
                    if end != -1:
                        node['notes'] = notes[end+1:].lstrip()
                for c in node.get('children', []) or []:
                    norm(c)
            root = tree.get('root')
            if root:
                norm(root)
            with open(p, 'w', encoding='utf-8') as tf:
                json.dump(tree, tf, indent=2, ensure_ascii=False)
        except Exception:
            pass
    
    def _append_progress(self, round_no: int, tool_name: str, tool_input: str, tool_output: str) -> None:
        entry = {
            "round": round_no,
            "tool": tool_name,
            "input": tool_input[:500],
            "output": tool_output[:500]
        }
        self.progress_log.append(entry)


    def determine_next_input(self, challenge_data: Dict, summary: Dict) -> str:
        """Determine next input based on current state"""
        from ..prompts import PromptRegistry
        registry = PromptRegistry()
        
        # 使用智能上下文优化器
        context_data = self.context_optimizer.get_optimized_task_context(
            self.task_tree, 
            self.current_round,
            self.last_tool_results
        )
        recent_progress = context_data["content"]
        
        # 获取上一轮的工具结果
        if hasattr(self, 'last_tool_results') and self.last_tool_results:
            results = self.last_tool_results
        else:
            # 如果没有工具结果，检查是否有上一轮响应
            last_response = self.conversation_history[-1].ai_response if self.conversation_history else ""
            if not last_response:
                results = None  # 第一步
            else:
                results = ["Please determine the next step based on your last analysis."]
        
        # 组合prompt
        base_prompt = registry.get_determine_next_step_prompt(results)
        
        # 添加完整Task Tree作为Recent Progress
        return f"Recent Progress:\n{recent_progress}\n\n{base_prompt}"
    
    def needs_human_input(self, response: str) -> bool:
        """Check if agent needs human input"""
        human_input_indicators = [
            "need human input",
            "cannot determine",
            "please specify",
            "need clarification",
            "manual intervention required"
        ]
        
        return any(indicator in response.lower() for indicator in human_input_indicators)
    
    def get_continue_prompt(self, last_response: str, tool_results: List[str] = None, show_all_flags: bool = False) -> str:
        """Generate a prompt to continue solving when user says 'continue'"""
        from ..prompts import PromptRegistry
        
        registry = PromptRegistry()
        
        # Use context optimizer to get appropriate task summary
        context_data = self.context_optimizer.get_optimized_task_context(
            self.task_tree, 
            self.current_round,
            tool_results
        )
        
        # 🔥 强制保证：最新tool结果必须完整发送给LLM
        filtered_results = []
        
        if tool_results:
            # 🔥 第一优先级：最新tool结果绝对保证（不论任何情况）
            latest_result = tool_results[-1] if tool_results else None
            if latest_result and latest_result.strip() and not latest_result.startswith('{"success"'):
                filtered_results.append(latest_result)
                print(f"🔥 Latest tool result GUARANTEED to be sent to LLM (length: {len(latest_result)} chars)")
            
            if context_data.get("context_type") == "recent":
                # 精简模式：包含所有有效的tool结果（除了已经添加的最新结果）
                for result in tool_results[:-1]:  # 排除最新结果，避免重复
                    if result and result.strip() and not result.startswith('{"success"'):
                        filtered_results.append(result)
            
            elif context_data.get("context_type") == "full":
                # 完整模式：添加其他被截断的重要结果
                truncated_results = context_data.get("truncated_results", [])
                
                # 添加截断的重要结果（排除最新结果，避免重复）
                for result in truncated_results:
                    if result != latest_result:  # 避免重复添加最新结果
                        filtered_results.append(result)
                
                if truncated_results:
                    print(f"🔄 Including {len([r for r in truncated_results if r != latest_result])} additional important truncated results")
        
        # Prepare context data
        context = {}
        if hasattr(self, 'challenge_info') and isinstance(self.challenge_info, dict):
            context = {
                'title': self.challenge_info.get('title', 'Unknown'),
                'category': self.challenge_info.get('category', 'Unknown'),
                'task_summary': context_data["content"]
            }
        
        # 显示上下文优化统计信息
        context_stats = self.context_optimizer.get_context_stats(context_data)
        if context_stats:
            print(f"📊 Context Strategy: {context_stats}")
        
        # Use filtered results based on context optimization strategy
        # When context is full, rely on task tree; when recent, include tool results
        return registry.get_continue_prompt(context, filtered_results, show_all_flags)
    
    def get_final_verification_prompt(self, tool_results: List[str] = None) -> str:
        """Generate a prompt for final flag verification"""
        from ..prompts import PromptRegistry
        
        registry = PromptRegistry()
        return registry.get_verification_prompt(tool_results)
    

    def read_challenge_files(self, challenge_data: Dict) -> str:
        """Read and format challenge files for initial prompt"""
        file_contents = ""
        files = challenge_data.get('files', [])
        
        # Auto-discover extracted files if they exist
        if os.path.exists('extracted'):
            for root, dirs, files_in_dir in os.walk('extracted'):
                for filename in files_in_dir:
                    extracted_file = os.path.join(root, filename)
                    if extracted_file not in files:
                        files.append(extracted_file)
        
        for file_path in files:
            try:
                # Check if file exists and determine if it's binary
                actual_path = file_path
                if not os.path.exists(actual_path):
                    # Try relative path
                    actual_path = os.path.basename(file_path)
                    if not os.path.exists(actual_path):
                        # Try in extracted directory
                        if os.path.exists('extracted'):
                            for root, dirs, files_in_dir in os.walk('extracted'):
                                for filename in files_in_dir:
                                    if filename == os.path.basename(file_path):
                                        actual_path = os.path.join(root, filename)
                                        break
                
                if os.path.exists(actual_path):
                    file_name = Path(file_path).name
                    
                    # Check if file is binary by trying to read first few bytes
                    try:
                        with open(actual_path, 'rb') as f:
                            sample = f.read(1024)  # Read first 1KB
                        
                        # Simple binary detection: check for null bytes and high ratio of non-printable chars
                        is_binary = (b'\x00' in sample or 
                                   sum(1 for b in sample if b < 32 and b not in [9, 10, 13]) / len(sample) > 0.3
                                   if sample else False)
                        
                        if is_binary:
                            # For binary files, provide smart analysis based on file type
                            import subprocess
                            try:
                                file_type = subprocess.run(['file', actual_path], 
                                                         capture_output=True, text=True, timeout=5)
                                if file_type.returncode == 0:
                                    type_info = file_type.stdout.strip().split(':', 1)[1].strip()
                                    analysis_hint = self._get_binary_analysis_hint(type_info, actual_path)
                                    
                                    # Add location context for clarity
                                    location_info = ""
                                    if 'extracted/' in file_path:
                                        location_info = " (already extracted from ZIP)"
                                    elif any(x in type_info.lower() for x in ['zip', 'archive']):
                                        location_info = " (extract this to analyze contents)"
                                    
                                    file_contents += f"File: {file_name}{location_info}\nType: {type_info}\nAnalysis: {analysis_hint}\n\n"
                                else:
                                    file_contents += f"File: {file_name}\nType: Binary file\nAnalysis: Use file_reader tool with binary mode or code_executor with subprocess\n\n"
                            except (subprocess.TimeoutExpired, FileNotFoundError):
                                file_contents += f"File: {file_name}\nType: Binary file\nAnalysis: Use file_reader tool with binary mode or code_executor with subprocess\n\n"
                        else:
                            # For text files, read content but limit size
                            try:
                                with open(actual_path, 'r', encoding='utf-8', errors='ignore') as f:
                                    content = f.read(5000)  # Limit to 5KB to prevent token overflow
                                    if len(content) == 5000:
                                        content += "\n... (file truncated due to size - use file_reader tool for full content)"
                                
                                # Additional token safety: if content is very large, just show first few lines
                                lines = content.split('\n')
                                if len(lines) > 100:
                                    content = '\n'.join(lines[:100]) + f"\n... (showing first 100 lines of {len(lines)} total lines)"
                                
                                file_contents += f"File: {file_name}\nContent:\n{content}\n\n"
                            except Exception:
                                file_contents += f"File: {file_name}\nType: Could not read as text file\n\n"
                    except Exception:
                        file_contents += f"File: {file_name}\nType: File access error\n\n"
                else:
                    file_name = Path(file_path).name
                    file_contents += f"File: {file_name}\nStatus: File not found\n\n"
                
            except Exception as e:
                print(f"Warning: Could not process file {file_path}: {e}")
        
        return file_contents
    
    def _get_binary_analysis_hint(self, type_info: str, file_path: str) -> str:
        """Generate smart analysis hints for binary files based on their type"""
        type_lower = type_info.lower()
        
        # Executable files
        if any(x in type_lower for x in ['executable', 'elf', 'pe32', 'mach-o']):
            return "Binary executable - use 'strings', 'objdump', 'readelf', or disassemblers like 'gdb' to analyze"
        
        # Archive files
        elif any(x in type_lower for x in ['zip', 'archive', 'compressed']):
            return "Archive file - extract with unzip/tar and examine contents for hidden files or data"
        
        # Image files  
        elif any(x in type_lower for x in ['jpeg', 'png', 'gif', 'bmp', 'image']):
            return "Image file - check for steganography with 'steghide extract -sf filename', examine EXIF with 'exiftool', scan for QR codes"
        
        # Audio/Video files
        elif any(x in type_lower for x in ['audio', 'video', 'wav', 'mp3', 'mp4', 'avi']):
            return "Media file - check for steganography, analyze metadata, extract with binwalk"
        
        # PDF files
        elif 'pdf' in type_lower:
            return "PDF file - examine metadata, extract embedded content, check for hidden layers or steganography"
        
        # Database files
        elif any(x in type_lower for x in ['database', 'sqlite', 'db']):
            return "Database file - open with sqlite3 or database tools to examine tables and data"
        
        # Memory dumps
        elif any(x in type_lower for x in ['dump', 'core']):
            return "Memory dump - analyze with volatility or examine strings for sensitive data"
        
        # Unknown binary
        else:
            # Try to extract some strings as additional context
            try:
                import subprocess
                strings_result = subprocess.run(['strings', file_path], 
                                              capture_output=True, text=True, timeout=3)
                if strings_result.returncode == 0:
                    strings_output = strings_result.stdout
                    interesting_strings = []
                    for line in strings_output.split('\n')[:20]:  # First 20 strings
                        line = line.strip()
                        if len(line) > 3 and any(keyword in line.lower() for keyword in 
                                                ['flag', 'ctf', 'password', 'key', 'secret', 'http', 'ftp']):
                            interesting_strings.append(line)
                    
                    if interesting_strings:
                        sample_strings = ', '.join(interesting_strings[:3])
                        return f"Unknown binary - found interesting strings: {sample_strings}... Use 'strings' command for full analysis"
                    else:
                        return "Unknown binary - use 'strings', 'hexdump', or 'binwalk' to analyze structure and content"
                else:
                    return "Unknown binary - use 'strings', 'hexdump', or 'binwalk' to analyze structure and content"
            except:
                return "Unknown binary - use 'strings', 'hexdump', or 'binwalk' to analyze structure and content"

    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        try:
            return len(self.tokenizer.encode(text))
        except Exception:
            return len(text.split())  # Fallback to word count
    
    def save_conversation(self, save_path: str):
        """Save conversation to JSON file"""
        try:
            import os
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            summary = self.get_conversation_summary()
            
            # Add task tree snapshot
            if self.task_tree:
                try:
                    summary['task_tree'] = self.task_tree.get_tree_display()
                except Exception:
                    pass
            
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"Warning: Could not save conversation: {e}") 