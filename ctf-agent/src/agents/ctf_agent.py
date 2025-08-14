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

from typing import TypedDict, Literal
from pydantic import BaseModel

class ToolResult(BaseModel):
    """Tool execution result"""
    success: bool
    output: str
    error: str = ""

class FileReaderTool(BaseTool):
    """Enhanced file reading tool with binary support"""
    name: str = "file_reader"
    description: str = "Read file contents from the challenge directory. Supports both text and binary files. Usage: Call this tool with <tool>file_reader</tool><input>filename</input> or <tool>file_reader</tool><input>filename|binary</input> for binary mode. Returns hex representation for binary files."
    
    def _run(self, file_path: str) -> str:
        try:
            # Check if binary mode is requested
            parts = file_path.split('|')
            target = parts[0].strip()
            mode = parts[1].strip().lower() if len(parts) > 1 else 'text'
            
            # If path not found, try to locate by basename under challenges/
            if not os.path.exists(target):
                base = os.path.basename(target)
                for root, _, files in os.walk('challenges'):
                    if base in files:
                        target = os.path.join(root, base)
                        break
            
            if mode == 'binary' or mode == 'hex':
                # Read as binary and return hex representation
                with open(target, 'rb') as f:
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
                # Try text mode first
                try:
                    with open(target, 'r', encoding='utf-8') as f:
                        content = f.read()
                    return ToolResult(success=True, output=content).json()
                except UnicodeDecodeError:
                    # If text fails, automatically try binary mode
                    with open(target, 'rb') as f:
                        content = f.read()
                    hex_content = content.hex()
                    ascii_repr = ''.join(chr(b) if 32 <= b <= 126 else f'\\x{b:02x}' for b in content[:200])
                    output = f"Binary file detected. Hex: {hex_content}\nASCII (first 200 bytes): {ascii_repr}{'...' if len(content) > 200 else ''}"
                    return ToolResult(success=True, output=output).json()
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e)).json()
    
    def _arun(self, file_path: str) -> str:
        return self._run(file_path)

class CodeExecutorTool(BaseTool):
    """Code execution tool"""
    name: str = "code_executor"
    description: str = "Execute Python code in a secure environment with automatic package installation. Usage: Call this tool with <tool>code_executor</tool><input>your_python_code</input>. Available modules: base64, codecs, re, json, hashlib, binascii, struct, os, sys, math, random, datetime, itertools, collections, functools. Auto-installs: Crypto (pycryptodome), sympy, gmpy2, numpy, requests."
    
    def _run(self, code: str) -> str:
        """Execute Python code with enhanced CTF environment"""
        try:
            # Auto-install common CTF packages if needed
            self._ensure_ctf_packages()
            
            # 创建安全的执行环境
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
            
            # 捕获print输出
            import io
            import sys
            output = io.StringIO()
            sys.stdout = output
            
            try:
                # 执行代码
                exec(code.strip(), safe_globals)
                
                # 获取输出
                result = output.getvalue().strip()
                
                # 恢复标准输出
                sys.stdout = sys.__stdout__
                
                # 检查输出
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
from .task_tree import TaskTree
from .flag_validator import FlagValidator
from .context_optimizer import ContextOptimizer
from .task_reporter import TaskReporter

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
        self.flag_validator_tool = None
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
        self.task_reporter_tool = TaskReporter()
        
        tools = [
            FileReaderTool(),
            CodeExecutorTool(),
            self.flag_validator_tool,
            self.task_reporter_tool,
        ]
        
        # Add network connector tool if available
        try:
            from .tools.network_connector import create_network_connector_tool
            network_tool = create_network_connector_tool()
            
            class NetworkConnectorTool(BaseTool):
                name: str = "network_connector"
                description: str = """Connect to remote services for CTF oracle challenges. 
                
Usage formats:
- <tool>network_connector</tool><input>host port method</input>
- <tool>network_connector</tool><input>host port method "data_to_send"</input>

Examples:
- <tool>network_connector</tool><input>titan.picoctf.net 64986 nc</input>
- <tool>network_connector</tool><input>titan.picoctf.net 64986 socket "E"</input>
- <tool>network_connector</tool><input>example.com 80 http "/api/data"</input>

Methods: nc, telnet, socket, http, GET, POST
Note: For nc command, use format 'host port nc' not 'host:port nc'"""
                
                def _run(self, query: str) -> str:
                    try:
                        # Parse input - support multiple formats and handle quoted strings
                        import shlex
                        import re
                        
                        # Handle quoted strings properly
                        query = query.strip()
                        
                        # Try to parse with shlex for proper quote handling
                        try:
                            parts = shlex.split(query)
                        except:
                            # Fallback to simple split if shlex fails
                            parts = query.split()
                        
                        if ':' in parts[0]:
                            # Format: host:port [method] [send_data]
                            host, port_str = parts[0].split(':', 1)
                            port = int(port_str)
                            method = parts[1] if len(parts) > 1 else "nc"
                            send_data = parts[2] if len(parts) > 2 else ""
                        else:
                            # Format: host port [method] [send_data]
                            if len(parts) < 2:
                                return json.dumps({"success": False, "error": "Usage: host:port or host port [method] [send_data]"})
                            host = parts[0]
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
        
        # Add system command tool if available
        try:
            from .tools.system_command import create_system_command_tool
            sys_tool = create_system_command_tool()
            
            class SystemCommandTool(BaseTool):
                name: str = "system_command"
                description: str = """Execute system commands for CTF challenges on macOS.

Available commands: openssl, base64, nc, curl, python3, ls, cat, file, xxd, strings, etc.

Usage examples:
- <tool>system_command</tool><input>openssl enc -aes-256-cbc -d -in secret.enc -pass pass:mypassword</input>
- <tool>system_command</tool><input>base64 -d</input> (with stdin)
- <tool>system_command</tool><input>nc titan.picoctf.net 64986</input>
- <tool>system_command</tool><input>file secret.enc</input>

Note: Use network_connector tool for interactive network connections."""
                
                def _run(self, query: str) -> str:
                    try:
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
                            return json.dumps({"success": False, "error": "No command provided"})
                        
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
        
        # Add package installer tool if available
        try:
            from .tools.package_installer import create_package_installer_tool
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
        from ..prompts import PromptRegistry
        
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
        
        # 控制LangChain内部日志：默认关闭，可通过环境变量LC_VERBOSE开启
        lc_verbose = bool(os.getenv("LC_VERBOSE", ""))
        executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=lc_verbose,
            handle_parsing_errors=True,
            max_iterations=1,  # 每次只执行一步
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
        from .ctf_prompts import CTFPromptManager
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
            if hasattr(self, 'task_reporter_tool'):
                self.task_reporter_tool.set_task_tree(self.task_tree)
            
            print(f"🔄 Task tree initialized: {task_tree_path}")
                
        except Exception as e:
            print(f"Warning: Could not initialize task tree: {e}")
            # Create fallback task tree
            self.task_tree = TaskTree(challenge_title="Challenge")
        
        # Add task tree instructions from prompts registry
        from ..prompts import PromptRegistry
        registry = PromptRegistry()
        task_tree_instructions = registry.get_task_tree_management_prompt()
        
        # Format the complete initial prompt
        if files_content:
            file_section = f"\n\nHere are the file contents to analyze:\n{files_content}"
        else:
            file_section = ""
        
        initial_prompt = f"{base_prompt}\n\n{task_tree_instructions}{file_section}\n\n{registry.get_initial_challenge_suffix()}"
        
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
            print(f"  Tool {i}: {tool.name} - {tool.description[:100]}...")
        
        return self.interact(initial_prompt)
    
    def interact(self, user_input: str) -> str:
        """Interact with LLM - execute one step at a time"""
        self.current_round += 1
        
        try:
            # 统一的轮次开始标识
            print(f"\n{'='*90}")
            print(f"Round {self.current_round}")
            print(f"{'='*90}")
            
            # 显示发送给LLM的提示
            print("\n📤 Sending to LLM:")
            print("-"*90)
            print(user_input)
            print("-"*90)
            
            # 调用LLM
            response = self.agent.invoke({
                "input": user_input,
                "chat_history": self.memory.chat_memory.messages
            })
            
            # 解析LLM响应
            ai_response = response.get('output', '')
            print("\n📥 LLM Response:")
            print("-"*90)
            print(ai_response)
            print("-"*90)
            
            # 从LLM响应提取任务
            if self.task_tree:
                extracted_count = self.task_tree.extract_tasks_from_response(ai_response)
                if extracted_count == 0:
                    print("⚠️  No task status updates found - LLM may not be following task management guidelines")
            
            # 处理工具调用
            tools_used = []
            tool_results = []
            
            # 处理 LangChain agent 的工具调用
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
                            
                            # 解析工具返回
                            display_result = self._parse_tool_result(observation)
                            print(f"📋 Result: {display_result}")
                            
                            tools_used.append(tool_name)
                            tool_results.append(display_result)
                            
                            # 添加到任务树
                            if self.task_tree:
                                self.task_tree.add_tool_result(tool_name, str(tool_input), str(display_result))
                    print("-"*90)
            
            # 处理手动 <tool> 标签调用
            if not tools_used and ("<tool>" in ai_response and "</tool>" in ai_response):
                print("-"*90)
                print("\n🔧 Tool Executions:")
                tool_calls = self._parse_tool_calls(ai_response)
                for tool_name, tool_input in tool_calls:
                    print(f"📌 Tool: {tool_name}")
                    print(f"Input: {tool_input}")
                    
                    # 执行工具
                    display_result = self._execute_tool(tool_name, tool_input)
                    print(f"📋 Result: {display_result}")
                    
                    tools_used.append(tool_name)
                    tool_results.append(display_result)
                    
                    # 添加到任务树
                    if self.task_tree:
                        self.task_tree.add_tool_result(tool_name, tool_input, display_result)
                print("-"*90)
            
            # 保存任务树
            if self.task_tree:
                self.task_tree.save()
            
            # 显示任务树
            self._display_task_tree()
            
            # Flag 检测
            self._detect_flags(ai_response, tool_results)
            
            # 保存工具结果和对话历史
            self.last_tool_results = tool_results
            self.memory.chat_memory.add_user_message(user_input)
            self.memory.chat_memory.add_ai_message(ai_response)
            
            # 保存轮次记录
            round_record = ConversationRound(
                round_number=self.current_round,
                human_input=user_input,
                ai_response=ai_response,
                input_tokens=self.count_tokens(user_input),
                output_tokens=self.count_tokens(ai_response),
                tools_used=tools_used,
                timestamp=str(datetime.now())
            )
            self.conversation_history.append(round_record)
            
            # 显示轮次总结
            print(f"\n📑 Round {self.current_round} Summary:")
            print(f"Tools Used: {len(tools_used)}")
            print(f"Results Generated: {len(tool_results)}")
            # 显示当前轮次的token使用情况
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
        """解析工具返回结果"""
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
            raw_result = matched_tool._run(tool_input)
            return self._parse_tool_result(raw_result)
        except Exception as e:
            return f"ERROR: Tool execution failed: {e}"
    
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
                "human_input": round.human_input,
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
        
        for file_path in files:
            try:
                # Use FileReaderTool to read file
                file_reader = next(t for t in self.tools if t.name == "file_reader")
                result = file_reader._run(file_path)
                result_data = json.loads(result)
                
                if result_data.get('success'):
                    content = result_data.get('output', '').strip()
                    file_name = Path(file_path).name
                    file_contents += f"File: {file_name}\nContent:\n{content}\n"
                
            except Exception as e:
                print(f"Warning: Could not read file {file_path}: {e}")
        
        return file_contents
    

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