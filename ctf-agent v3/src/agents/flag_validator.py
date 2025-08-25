#!/usr/bin/env python3
"""
Flag Validator Tool - Validates and extracts candidate flags from conversation
"""

import re
import json
from typing import List, Optional, Dict, Any
from langchain.tools import BaseTool
from pydantic import BaseModel

class ToolResult(BaseModel):
    """Tool execution result"""
    success: bool
    output: str
    error: str = ""

class FlagValidator(BaseTool):
    """Tool to validate and extract candidate flags from conversation"""
    name: str = "flag_validator"
    description: str = "Validate and extract candidate flags from conversation history and recent outputs."
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def _run(self, input_str: str) -> str:
        """执行flag检测"""
        try:
            payload = json.loads(input_str) if input_str and input_str.strip() else {"action": "extract"}
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Invalid JSON: {e}").json()
        
        action = payload.get("action", "extract").lower()
        
        try:
            if action == "extract":
                text = payload.get("text", "")
                if not text:
                    return ToolResult(success=False, output="", error="Missing 'text' parameter").json()
                
                flags = self._extract_flags(text)
                
                if flags:
                    result = {
                        "candidates": flags
                    }
                    return ToolResult(success=True, output=json.dumps(result, indent=2)).json()
                else:
                    return ToolResult(success=True, output="No flag candidates found").json()
                    
            else:
                return ToolResult(success=False, output="", error=f"Unknown action: {action}").json()
                
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Flag detection failed: {str(e)}").json()
    
    def _extract_flags(self, text: str) -> List[str]:
        """Extract potential flags from text"""
        # Pattern for picoCTF flags - supports variations like picoC:F{...}
        flag_pattern = r'pico[C:]?[T:]?F\{[^}]+\}'
        
        flags = re.findall(flag_pattern, text, re.IGNORECASE)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_flags = []
        for flag in flags:
            if flag not in seen:
                seen.add(flag)
                unique_flags.append(flag)
        
        return unique_flags
    
    def _arun(self, input_str: str) -> str:
        return self._run(input_str)
