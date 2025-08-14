#!/usr/bin/env python3
"""
Simple Task Tree - Simple and reliable task tree implementation
"""

import json
import os
import re
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path


class TaskTree:
    """Task tree manager"""
    
    def __init__(self, challenge_title: str = "Challenge", storage_path: str = None):
        self.challenge_title = challenge_title
        self.storage_path = storage_path or "task_tree.json"
        self.tasks = []
        self.current_task_id = 0
        
    def extract_tasks_from_response(self, llm_response: str) -> int:
        """Extract tasks from LLM response"""
        # Find lines in → Task: format, support integer numbering
        # Fix: Use more precise matching for description part, avoid stopping at "-" in description
        task_pattern = r'→\s*Task:\s*(\d+)\.\s*(.*?)\s+-\s+(completed|in-progress|failed|pending)'
        matches = re.findall(task_pattern, llm_response, re.IGNORECASE)
        
        print(f"🔄 Extracted {len(matches)} tasks from LLM response")
        
        extracted_count = 0
        for task_id_str, description, status in matches:
            try:
                task_id = int(task_id_str)  # Use integer instead of float
                task = {
                    "id": task_id,
                    "description": description.strip(),
                    "status": status.lower(),
                    "timestamp": datetime.now().isoformat(),
                    "subtasks": []
                }
                
                # Update existing task or add new task
                existing_index = None
                for i, existing_task in enumerate(self.tasks):
                    if existing_task.get("id") == task_id:
                        existing_index = i
                        break
                
                if existing_index is not None:
                    # Update existing task status and description if different
                    existing_task = self.tasks[existing_index]
                    if existing_task["status"] != status.lower() or existing_task["description"] != description.strip():
                        existing_task["status"] = status.lower()
                        existing_task["description"] = description.strip()
                        existing_task["timestamp"] = datetime.now().isoformat()
                        extracted_count += 1
                else:
                    # Add new task only if it doesn't exist
                    self.tasks.append(task)
                    extracted_count += 1
                
            except ValueError:
                continue
        
        # Sort by ID
        self.tasks.sort(key=lambda x: x.get("id", 0))
        return extracted_count
    
    def add_tool_result(self, tool_name: str, tool_input: str, tool_result: str) -> str:
        """Add tool execution result to the latest in-progress task"""
        # Skip report_task_update as it's not related to solving
        if tool_name == "report_task_update":
            return "skipped"
            
        if not self.tasks:
            # If no tasks, create a default task
            self.tasks.append({
                "id": 1,
                "description": "Solve challenge",
                "status": "in-progress",
                "timestamp": datetime.now().isoformat(),
                "subtasks": []
            })
        
        # Prefer latest in-progress task, if none then select task with highest ID
        current_task = None
        
        # First look for in-progress tasks (search from back to front, prefer latest)
        for task in reversed(self.tasks):
            if task.get("status") == "in-progress":
                current_task = task
                break
        
        # If no in-progress task, select task with highest ID (usually the newest created)
        if not current_task:
            current_task = max(self.tasks, key=lambda t: t.get("id", 0))
        
        # Add subtask
        main_id = int(current_task["id"])
        subtask_id = len(current_task["subtasks"]) + 1
        subtask_id_str = f"{main_id}.{subtask_id}"
        
        subtask = {
            "id": subtask_id_str,
            "tool": tool_name,
            "input": tool_input[:100] + "..." if len(tool_input) > 100 else tool_input,
            "result": tool_result[:200] + "..." if len(tool_result) > 200 else tool_result,
            "timestamp": datetime.now().isoformat()
        }
        
        current_task["subtasks"].append(subtask)
        return subtask_id_str
    
    def get_tree_display(self) -> str:
        """Get tree display format"""
        if not self.tasks:
            return f"{self.challenge_title} - Progress"
        
        lines = [f"{self.challenge_title} - Progress"]
        
        for task in self.tasks:
            status_icon = self._get_status_icon(task.get("status", ""))
            task_id = task.get("id", "?")
            description = task.get("description", "No description")
            
            lines.append(f"{status_icon} {task_id}. {description}")
            
            # Show subtasks (tool calls) - excluding report_task_update
            subtasks = task.get("subtasks", [])
            for subtask in subtasks:
                subtask_id = subtask.get("id", "?")
                tool_name = subtask.get("tool", "unknown")
                result = subtask.get("result", "")
                
                lines.append(f"   {subtask_id}. Used {tool_name}")
                if result:
                    clean_result = self._clean_result_for_display(result)
                    if clean_result:
                        lines.append(f"      -> {clean_result}")
        
        return "\n".join(lines)
    
    def get_recent_progress(self) -> str:
        """Get recent progress summary"""
        if not self.tasks:
            return "No steps recorded yet"
        
        # Return complete tree display
        return self.get_tree_display()
    
    def save(self) -> bool:
        """Save task tree to file"""
        try:
            if not self.storage_path:
                return False
            
            # Ensure directory exists
            dir_path = os.path.dirname(self.storage_path)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)
            
            data = {
                "metadata": {
                    "challenge_title": self.challenge_title,
                    "created": datetime.now().isoformat(),
                    "task_count": len(self.tasks)
                },
                "tasks": self.tasks
            }
            
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            print(f"Warning: Could not save task tree: {e}")
            return False
    
    def load(self) -> bool:
        """Load task tree from file"""
        try:
            if not self.storage_path or not os.path.exists(self.storage_path):
                return False
            
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.tasks = data.get("tasks", [])
            metadata = data.get("metadata", {})
            if "challenge_title" in metadata:
                self.challenge_title = metadata["challenge_title"]
            
            return True
            
        except Exception as e:
            print(f"Warning: Could not load task tree: {e}")
            return False
    
    def _get_status_icon(self, status: str) -> str:
        """Get status icon"""
        icons = {
            "completed": "[✓]",
            "in-progress": "[→]", 
            "failed": "[✗]",
            "pending": "[ ]"
        }
        return icons.get(status, "[?]")
    
    def _clean_result_for_display(self, result: str, max_length: int = 80) -> str:
        """Clean result for display with intelligent truncation"""
        if not result:
            return ""
        
        # Remove common JSON wrapping
        clean_result = result.strip()
        if clean_result.startswith('"') and clean_result.endswith('"'):
            clean_result = clean_result[1:-1]
        
        # 为重要信息保留更多空间
        if self._is_important_result(clean_result):
            max_length = min(150, max_length * 2)  # 重要结果最多显示150字符
        
        # Truncate long results
        if len(clean_result) > max_length:
            clean_result = clean_result[:max_length-3] + "..."
        
        return clean_result
    
    def _is_important_result(self, result: str) -> bool:
        """判断结果是否重要（与context_optimizer中的逻辑保持一致）"""
        if not result:
            return False
            
        result_lower = result.lower()
        
        # 重要信息模式
        important_indicators = [
            'picoctf{', 'flag', 'error:', 'traceback', 'exception',
            'extracted characters', 'decoded', 'potential flag',
            'characters from', 'combination'
        ]
        
        return any(indicator in result_lower for indicator in important_indicators)
    
    def _truncate_text(self, text: str, max_length: int) -> str:
        """Truncate text"""
        if len(text) <= max_length:
            return text
        return text[:max_length-3] + "..."
    
    def update_task_status(self, task_id: str, description: str, status: str, details: str = None):
        """Update task status (used by task reporter)"""
        # Skip task reporter updates to avoid duplicate tasks
        # Only allow explicit LLM → Task: format updates
        return
