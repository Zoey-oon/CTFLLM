"""
JavaScript Tool for CTF challenges
Combined execution and decryption functionality
"""
import subprocess
import tempfile
import os
import json
import re
from typing import Dict, Any, Optional

class JSExecutor:
    def __init__(self):
        self.name = "js_executor"
        self.description = "Execute JavaScript code and decrypt JavaScript-based encryption"
    
    # JavaScript Execution Methods
    def _execute_with_node(self, js_code: str) -> Dict[str, Any]:
        """Execute JavaScript using Node.js"""
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
                f.write(js_code)
                temp_file = f.name
            
            result = subprocess.run(
                ['node', temp_file],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            os.unlink(temp_file)
            
            if result.returncode == 0:
                return {
                    "success": True,
                    "output": result.stdout.strip(),
                    "error": result.stderr.strip() if result.stderr else None,
                    "method": "node"
                }
            else:
                return {
                    "success": False,
                    "error": result.stderr.strip() if result.stderr else "Unknown error",
                    "method": "node"
                }
                
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Execution timeout", "method": "node"}
        except FileNotFoundError:
            return {"success": False, "error": "Node.js not found", "method": "node"}
        except Exception as e:
            return {"success": False, "error": str(e), "method": "node"}
    
    def _execute_with_deno(self, js_code: str) -> Dict[str, Any]:
        """Execute JavaScript using Deno"""
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
                f.write(js_code)
                temp_file = f.name
            
            result = subprocess.run(
                ['deno', 'run', '--allow-all', temp_file],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            os.unlink(temp_file)
            
            if result.returncode == 0:
                return {
                    "success": True,
                    "output": result.stdout.strip(),
                    "error": result.stderr.strip() if result.stderr else None,
                    "method": "deno"
                }
            else:
                return {
                    "success": False,
                    "error": result.stderr.strip() if result.stderr else "Unknown error",
                    "method": "deno"
                }
                
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Execution timeout", "method": "deno"}
        except FileNotFoundError:
            return {"success": False, "error": "Deno not found", "method": "deno"}
        except Exception as e:
            return {"success": False, "error": str(e), "method": "deno"}
    
    def _execute_with_python_js(self, js_code: str) -> Dict[str, Any]:
        """Execute JavaScript using Python JavaScript engines"""
        try:
            # Try PyExecJS first
            try:
                import PyExecJS
                context = PyExecJS.compile(js_code)
                result = context.eval(js_code)
                return {
                    "success": True,
                    "output": str(result),
                    "method": "PyExecJS"
                }
            except ImportError:
                pass
            
            # Try js2py
            try:
                import js2py
                result = js2py.eval_js(js_code)
                return {
                    "success": True,
                    "output": str(result),
                    "method": "js2py"
                }
            except ImportError:
                pass
            
            return {"success": False, "error": "No Python JavaScript engine available"}
            
        except Exception as e:
            return {"success": False, "error": str(e), "method": "python_js"}
    
    # JavaScript Decryption Methods
    def _xor_decrypt(self, encrypted: str, key: str) -> str:
        """XOR decryption - most common in CTF challenges"""
        try:
            decrypted = ""
            for i in range(len(encrypted)):
                char_code = ord(encrypted[i])
                key_code = ord(key[i % len(key)])
                decrypted_char_code = (char_code - key_code + 256) % 256
                decrypted += chr(decrypted_char_code)
            return decrypted
        except Exception as e:
            return f"XOR decryption failed: {str(e)}"
    
    def _xor_decrypt_raw_chars(self, encrypted: str, key: str) -> str:
        """XOR decryption for raw Unicode characters"""
        try:
            decrypted = ""
            for i in range(len(encrypted)):
                char_code = ord(encrypted[i])
                key_code = ord(key[i % len(key)])
                decrypted_char_code = (char_code - key_code + 256) % 256
                decrypted += chr(decrypted_char_code)
            return decrypted
        except Exception as e:
            return f"Raw char XOR decryption failed: {str(e)}"
    
    def _handle_js_encrypted_string(self, encrypted: str, key: str) -> str:
        """Handle JavaScript encrypted strings that may have encoding issues"""
        try:
            # Method 1: Try direct decryption first (most common case)
            result = self._xor_decrypt_raw_chars(encrypted, key)
            
            # Check if result looks like a flag
            if "picoCTF" in result or "CTF" in result or "flag" in result.lower():
                return result
            
            # Method 2: If direct decryption doesn't work, try handling as UTF-8 bytes
            try:
                raw_bytes = encrypted.encode('utf-8')
                actual_bytes = []
                
                # Extract every 2nd byte (skip UTF-8 prefix bytes)
                for i in range(1, len(raw_bytes), 2):
                    if i < len(raw_bytes):
                        actual_bytes.append(raw_bytes[i])
                
                # Decrypt the actual bytes
                decrypted = ""
                for i in range(len(actual_bytes)):
                    char_code = (actual_bytes[i] - ord(key[i % len(key)]) + 256) % 256
                    decrypted += chr(char_code)
                
                return decrypted
                
            except Exception:
                pass
            
            # Method 3: Return the first result if all else fails
            return result
            
        except Exception as e:
            return f"JavaScript string handling failed: {str(e)}"
    
    def _caesar_decrypt(self, encrypted: str, shift: int) -> str:
        """Caesar cipher decryption"""
        try:
            decrypted = ""
            for char in encrypted:
                if char.isalpha():
                    base = ord('A') if char.isupper() else ord('a')
                    decrypted_char_code = (ord(char) - base - shift) % 26
                    decrypted += chr(base + decrypted_char_code)
                else:
                    decrypted += char
            return decrypted
        except Exception as e:
            return f"Caesar decryption failed: {str(e)}"
    
    def _substitution_decrypt(self, encrypted: str, key_map: Dict[str, str]) -> str:
        """Simple substitution cipher decryption"""
        try:
            decrypted = ""
            for char in encrypted:
                decrypted += key_map.get(char, char)
            return decrypted
        except Exception as e:
            return f"Substitution decryption failed: {str(e)}"
    
    def _custom_js_decrypt(self, encrypted: str, custom_code: str) -> str:
        """Execute custom JavaScript decryption code"""
        try:
            # Extract JavaScript variables and logic
            if "var encryptedFlag" in custom_code and "var key" in custom_code:
                encrypted_match = re.search(r'var encryptedFlag\s*=\s*["\']([^"\']+)["\']', custom_code)
                key_match = re.search(r'var key\s*=\s*["\']([^"\']+)["\']', custom_code)
                
                if encrypted_match and key_match:
                    encrypted_str = encrypted_match.group(1)
                    key_str = key_match.group(1)
                    return self._xor_decrypt(encrypted_str, key_str)
            
            return "Custom JavaScript parsing not implemented for this format"
        except Exception as e:
            return f"Custom JS decryption failed: {str(e)}"
    
    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute JavaScript code or decrypt JavaScript-based encryption.
        
        Args:
            params: {
                "action": "execute|decrypt",
                "code": "JavaScript code to execute (for execute action)",
                "engine": "node|deno|auto|python (for execute action)",
                "encrypted": "encrypted string (for decrypt action)",
                "algorithm": "xor|caesar|substitution|custom|js_auto (for decrypt action)",
                "key": "decryption key (for decrypt action)",
                "shift": "caesar shift (for decrypt action)",
                "key_map": "substitution mapping (for decrypt action)",
                "custom_code": "custom JavaScript code (for decrypt action)",
                "timeout": "execution timeout in seconds"
            }
        """
        try:
            action = params.get("action", "execute").lower()
            
            if action == "execute":
                return self._execute_js(params)
            elif action == "decrypt":
                return self._decrypt_js(params)
            else:
                return {"success": False, "error": f"Unknown action: {action}. Use 'execute' or 'decrypt'"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _execute_js(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle JavaScript execution"""
        js_code = params.get("code", "")
        engine = params.get("engine", "auto").lower()
        
        if not js_code:
            return {"success": False, "error": "JavaScript code is required"}
        
        # Clean and prepare the code
        js_code = js_code.strip()
        
        # If it's a bookmarklet, extract the function body
        if js_code.startswith("javascript:"):
            js_code = js_code[11:]  # Remove "javascript:" prefix
        
        # If it's wrapped in a function, extract the content
        if js_code.startswith("(function()") and js_code.endswith("})()"):
            start = js_code.find("{") + 1
            end = js_code.rfind("}")
            if start > 0 and end > start:
                js_code = js_code[start:end]
        
        # Try different execution engines based on preference
        if engine == "node":
            return self._execute_with_node(js_code)
        elif engine == "deno":
            return self._execute_with_deno(js_code)
        elif engine == "python":
            return self._execute_with_python_js(js_code)
        else:  # auto
            # Try Node.js first, then Deno, then Python
            result = self._execute_with_node(js_code)
            if result["success"]:
                return result
            
            result = self._execute_with_deno(js_code)
            if result["success"]:
                return result
            
            result = self._execute_with_python_js(js_code)
            if result["success"]:
                return result
            
            return {"success": False, "error": "No JavaScript engine available"}
    
    def _decrypt_js(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle JavaScript decryption"""
        encrypted = params.get("encrypted", "")
        algorithm = params.get("algorithm", "xor").lower()
        key = params.get("key", "")
        
        if not encrypted:
            return {"success": False, "error": "Encrypted string is required"}
        
        result = ""
        
        if algorithm == "xor":
            if not key:
                return {"success": False, "error": "Key is required for XOR decryption"}
            result = self._xor_decrypt(encrypted, key)
            
        elif algorithm == "js_auto":
            # Smart JavaScript string handling
            if not key:
                return {"success": False, "error": "Key is required for JavaScript auto-decryption"}
            result = self._handle_js_encrypted_string(encrypted, key)
            
        elif algorithm == "caesar":
            shift = params.get("shift", 3)
            result = self._caesar_decrypt(encrypted, shift)
            
        elif algorithm == "substitution":
            key_map = params.get("key_map", {})
            if not key_map:
                return {"success": False, "error": "Key map is required for substitution"}
            result = self._substitution_decrypt(encrypted, key_map)
            
        elif algorithm == "custom":
            custom_code = params.get("custom_code", "")
            if not custom_code:
                return {"success": False, "error": "Custom code is required for custom decryption"}
            result = self._custom_js_decrypt(encrypted, custom_code)
            
        else:
            return {"success": False, "error": f"Unsupported algorithm: {algorithm}"}
        
        return {
            "success": True,
            "action": "decrypt",
            "algorithm": algorithm,
            "encrypted": encrypted,
            "key": key,
            "decrypted": result,
            "debug": f"Applied {algorithm} decryption with key '{key}'"
        }

# Tool registration for CTF Agent
def create_js_executor_tool():
    """Create JavaScript tool for CTF agent"""
    js_tool = JSExecutor()
    
    def js_executor_func(action: str = "execute", code: str = "", engine: str = "auto", 
                encrypted: str = "", algorithm: str = "xor", key: str = "", 
                shift: int = 3, key_map: Dict[str, str] = None, custom_code: str = "", 
                timeout: int = 30):
        """
        Execute JavaScript code or decrypt JavaScript-based encryption.
        
        Args:
            action: 'execute' for JavaScript execution, 'decrypt' for decryption
            code: JavaScript code to execute (for execute action)
            engine: Execution engine ('node', 'deno', 'auto', 'python')
            encrypted: The encrypted string to decrypt (for decrypt action)
            algorithm: Decryption algorithm ('xor', 'caesar', 'substitution', 'custom', 'js_auto')
            key: Decryption key (for XOR and substitution)
            shift: Caesar cipher shift (default: 3)
            key_map: Substitution mapping dictionary
            custom_code: Custom JavaScript decryption code
            timeout: Execution timeout in seconds
            
        Returns:
            Execution or decryption result and metadata
        """
        params = {
            "action": action,
            "code": code,
            "engine": engine,
            "encrypted": encrypted,
            "algorithm": algorithm,
            "key": key,
            "shift": shift,
            "key_map": key_map or {},
            "custom_code": custom_code,
            "timeout": timeout
        }
        
        return js_tool.execute(params)
    
    return js_executor_func
