#!/usr/bin/env python3
"""
Task Manager - Comprehensive task management system
Combines task tree functionality and task reporting tool
"""

import json
import os
import re
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, Literal
from pathlib import Path
from langchain.tools import BaseTool
from pydantic import BaseModel, Field, PrivateAttr

TaskStatus = Literal["pending", "in-progress", "completed", "failed"]

class TaskUpdate(BaseModel):
    """Single task update"""
    task_id: Optional[str] = Field(None, description="Task ID, auto-generated if empty")
    description: str = Field(..., description="Task description")
    status: TaskStatus = Field("pending", description="Task status")
    parent_id: Optional[str] = Field(None, description="Parent task ID")
    details: Optional[str] = Field(None, description="Task details or results")

class TaskReportInput(BaseModel):
    """Task report input structure"""
    updates: List[TaskUpdate] = Field(..., description="Task update list")
    context: Optional[str] = Field(None, description="Context information")


class TaskTree:
    """Task tree manager"""
    
    def __init__(self, challenge_title: str = "Challenge", storage_path: str = None):
        self.challenge_title = challenge_title
        self.storage_path = storage_path or "task_tree.json"
        self.tasks = []
        self.current_task_id = 0
        
    def extract_tasks_from_response(self, llm_response: str) -> int:
        """Extract tasks from LLM response"""
        extracted_count = 0
        
        # Method 1: Try to extract traditional arrow format first (priority)
        task_pattern = r'→\s*Task:\s*(\d+)\.\s*(.*?)\s+-\s+(completed|in-progress|failed|pending)'
        matches = re.findall(task_pattern, llm_response, re.IGNORECASE)
        
        for task_id_str, description, status in matches:
            try:
                task_id = int(task_id_str)
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
                    self.tasks[existing_index]["status"] = status.lower()
                    if self.tasks[existing_index]["description"] != description.strip():
                        self.tasks[existing_index]["description"] = description.strip()
                    self.tasks[existing_index]["timestamp"] = datetime.now().isoformat()
                else:
                    # Add new task
                    self.tasks.append(task)
                    self.current_task_id = max(self.current_task_id, task_id)
                
                extracted_count += 1
                
            except (ValueError, KeyError) as e:
                print(f"Warning: Failed to parse task: {e}")
                continue
        
        # Method 2: Fallback to JSON format if no arrow format found
        if extracted_count == 0:
            try:
                import json
                # Look for task_manager tool calls with JSON input
                json_pattern = r'<tool>task_manager</tool>\s*<input>(.*?)</input>'
                json_matches = re.findall(json_pattern, llm_response, re.DOTALL)
                
                for json_input in json_matches:
                    try:
                        # Clean the JSON input
                        json_input = json_input.strip()
                        if json_input.startswith('```json'):
                            json_input = json_input[7:]
                        if json_input.endswith('```'):
                            json_input = json_input[:-3]
                        json_input = json_input.strip()
                        
                        data = json.loads(json_input)
                        updates = data.get("updates", [])
                        
                        for update in updates:
                            task_id = update.get("task_id")
                            if not task_id:
                                self.current_task_id += 1
                                task_id = self.current_task_id
                            else:
                                try:
                                    task_id = int(task_id)
                                    self.current_task_id = max(self.current_task_id, task_id)
                                except ValueError:
                                    self.current_task_id += 1
                                    task_id = self.current_task_id
                            
                            task = {
                                "id": task_id,
                                "description": update.get("description", "Unknown task"),
                                "status": update.get("status", "pending"),
                                "timestamp": datetime.now().isoformat(),
                                "subtasks": [],
                                "parent_id": update.get("parent_id"),
                                "details": update.get("details")
                            }
                            
                            # Update existing task or add new task
                            existing_index = None
                            for i, existing_task in enumerate(self.tasks):
                                if existing_task.get("id") == task_id:
                                    existing_index = i
                                    break
                            
                            if existing_index is not None:
                                # Update existing task
                                self.tasks[existing_index].update({
                                    "status": task["status"],
                                    "description": task["description"],
                                    "timestamp": task["timestamp"],
                                    "details": task.get("details")
                                })
                            else:
                                # Add new task
                                self.tasks.append(task)
                            
                            extracted_count += 1
                            
                    except json.JSONDecodeError as e:
                        print(f"Warning: Failed to parse JSON task update: {e}")
                        continue
                        
            except Exception as e:
                print(f"Warning: Failed to extract JSON tasks: {e}")
        
        # Sort tasks by ID
        self.tasks.sort(key=lambda x: x.get("id", 0))
        return extracted_count
    
    def add_tool_result(self, tool_name: str, tool_input: str, tool_result: str) -> str:
        """Add tool execution result to the latest in-progress task"""
        # Skip task_manager as it's not related to solving
        if tool_name == "task_manager":
            return "skipped"
            
        if not self.tasks:
            # If no tasks, create a default task
            self.tasks.append({
                "id": 1,
                "description": "Challenge analysis and solving",
                "status": "in-progress", 
                "timestamp": datetime.now().isoformat(),
                "subtasks": []
            })
            self.current_task_id = 1
        
        # Find the latest in-progress task
        target_task = None
        for task in reversed(self.tasks):
            if task.get("status") == "in-progress":
                target_task = task
                break
        
        # If no in-progress task found, use the latest task
        if not target_task and self.tasks:
            target_task = self.tasks[-1]
        
        if target_task:
            # Add tool call as subtask
            subtask_id = len(target_task.get("subtasks", [])) + 1
            subtask = {
                "id": subtask_id,
                "tool": tool_name,
                "input": tool_input[:200] + "..." if len(tool_input) > 200 else tool_input,
                "result": tool_result[:500] + "..." if len(tool_result) > 500 else tool_result,
                "timestamp": datetime.now().isoformat()
            }
            
            if "subtasks" not in target_task:
                target_task["subtasks"] = []
            target_task["subtasks"].append(subtask)
            
            return f"Added to task {target_task.get('id', '?')}"
        else:
            return "No target task found"
    
    def get_display_tree(self) -> str:
        """Get formatted task tree for display"""
        if not self.tasks:
            return "📋 No tasks yet"
        
        lines = [f"📋 {self.challenge_title} - Task Progress"]
        lines.append("=" * 50)
        
        for task in self.tasks:
            status = task.get("status", "unknown")
            status_icon = {
                "completed": "[✓]",
                "in-progress": "[→]", 
                "failed": "[✗]",
                "pending": "[~]"
            }.get(status, "[?]")
            
            task_id = task.get("id", "?")
            description = task.get("description", "No description")
            
            lines.append(f"{status_icon} {task_id}. {description}")
            
            # Show subtasks (tool calls) - excluding task_manager
            subtasks = task.get("subtasks", [])
            for subtask in subtasks:
                subtask_id = subtask.get("id", "?")
                tool_name = subtask.get("tool", "unknown")
                result = subtask.get("result", "")
                
                # Skip task_manager subtasks in display
                if tool_name == "task_manager":
                    continue
                
                # Determine subtask status based on result
                if "success" in result.lower() or "✓" in result:
                    subtask_status = "✓"
                elif "error" in result.lower() or "✗" in result or "failed" in result.lower():
                    subtask_status = "✗"
                else:
                    subtask_status = "?"
                
                # Truncate result for display (max 80 chars)
                if len(result) > 80:
                    result = result[:80] + "..."
                
                lines.append(f"    {subtask_id}. Used {tool_name} {subtask_status} - {result}")
        
        return "\n".join(lines)
    
    def save_to_file(self, file_path: str = None) -> bool:
        """Save task tree to JSON file"""
        try:
            target_path = file_path or self.storage_path
            
            # Create directory if needed
            Path(target_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Prepare data for saving
            data = {
                "challenge_title": self.challenge_title,
                "tasks": self.tasks,
                "current_task_id": self.current_task_id,
                "saved_at": datetime.now().isoformat()
            }
            
            # Save to file
            with open(target_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            print(f"Error saving task tree: {e}")
            return False
    
    def load_from_file(self, file_path: str = None) -> bool:
        """Load task tree from JSON file"""
        try:
            target_path = file_path or self.storage_path
            
            if not os.path.exists(target_path):
                return False
            
            with open(target_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.challenge_title = data.get("challenge_title", "Challenge")
            self.tasks = data.get("tasks", [])
            self.current_task_id = data.get("current_task_id", 0)
            
            return True
            
        except Exception as e:
            print(f"Error loading task tree: {e}")
            return False
    
    def save(self, file_path: str = None) -> bool:
        """Save task tree (alias for save_to_file for backward compatibility)"""
        return self.save_to_file(file_path)
    
    def get_tree_display(self) -> str:
        """Get tree display (alias for get_display_tree for backward compatibility)"""
        return self.get_display_tree()

    def update_task_status(self, task_id: int, status: str, description: str = None) -> bool:
        """Update task status"""
        try:
            # Normalize status to use hyphens
            status = status.lower().replace("_", "-")
            
            # Validate status
            valid_statuses = ["pending", "in-progress", "completed", "failed"]
            if status not in valid_statuses:
                print(f"Warning: Invalid status '{status}'. Using 'pending' instead.")
                status = "pending"
            
            # Find existing task
            existing_index = None
            for i, task in enumerate(self.tasks):
                if task.get("id") == task_id:
                    existing_index = i
                    break
            
            if existing_index is not None:
                # Update existing task
                self.tasks[existing_index]["status"] = status
                if description:
                    self.tasks[existing_index]["description"] = description
                self.tasks[existing_index]["timestamp"] = datetime.now().isoformat()
                return True
            else:
                # Create new task if it doesn't exist
                new_task = {
                    "id": task_id,
                    "description": description or f"Task {task_id}",
                    "status": status,
                    "timestamp": datetime.now().isoformat(),
                    "subtasks": []
                }
                self.tasks.append(new_task)
                self.current_task_id = max(self.current_task_id, task_id)
                return True
                
        except Exception as e:
            print(f"Error updating task status: {e}")
            return False


class TaskManager(BaseTool):
    """Structured task status reporting tool"""
    name: str = "task_manager"
    description: str = """Report task status updates. Used for background task progress management, reducing task management redundancy in conversations.
Input JSON format:
{
  "updates": [
    {
      "task_id": "optional, auto-generated if empty",
      "description": "task description",
      "status": "pending|in-progress|completed|failed",
      "parent_id": "optional, parent task ID",
      "details": "optional, task details"
    }
  ],
  "context": "optional context information"
}
"""
    
    # Use PrivateAttr to avoid Pydantic validation issues
    _task_tree: Any = PrivateAttr(default=None)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Initialize task tree if needed
        if not hasattr(self, '_task_tree') or self._task_tree is None:
            self._task_tree = TaskTree()
    
    def _run(self, input_str: str) -> str:
        """Process task updates"""
        try:
            # Parse the input JSON
            data = json.loads(input_str)
            
            # Validate input structure
            if not isinstance(data, dict):
                return json.dumps({"error": "Input must be a JSON object"})
            
            updates = data.get("updates", [])
            context = data.get("context", "")
            
            if not updates:
                return json.dumps({"error": "No task updates provided"})
            
            # Process each update
            results = []
            for update in updates:
                try:
                    # Generate task ID if not provided
                    task_id = update.get("task_id")
                    if not task_id:
                        if hasattr(self, '_task_tree') and self._task_tree:
                            self._task_tree.current_task_id += 1
                            task_id = str(self._task_tree.current_task_id)
                        else:
                            task_id = str(uuid.uuid4())[:8]
                    
                    # Create task update object
                    task_update = TaskUpdate(
                        task_id=task_id,
                        description=update.get("description", ""),
                        status=update.get("status", "pending"),
                        parent_id=update.get("parent_id"),
                        details=update.get("details")
                    )
                    
                    results.append({
                        "task_id": task_update.task_id,
                        "description": task_update.description,
                        "status": task_update.status,
                        "processed": True
                    })
                    
                except Exception as e:
                    results.append({
                        "error": f"Failed to process update: {str(e)}",
                        "update": update
                    })
            
            return json.dumps({
                "success": True,
                "processed_updates": len(results),
                "results": results,
                "context": context
            }, indent=2)
            
        except json.JSONDecodeError as e:
            return json.dumps({"error": f"Invalid JSON input: {str(e)}"})
        except Exception as e:
            return json.dumps({"error": f"Processing error: {str(e)}"})
    
    def _arun(self, input_str: str) -> str:
        """Async version of _run"""
        return self._run(input_str)

    def get_current_path(self) -> str:
        """Get current working directory path"""
        try:
            import os
            return os.getcwd()
        except:
            return "/app"  # Default fallback
    
    def suggest_path_navigation(self, target_path: str) -> str:
        """Suggest path navigation command"""
        current_path = self.get_current_path()
        
        if target_path.startswith("/"):
            # Absolute path
            return f"cd {target_path}"
        else:
            # Relative path from current directory
            return f"cd {target_path}"
    
    def validate_path(self, path: str) -> bool:
        """Validate if a path exists"""
        try:
            import os
            return os.path.exists(path)
        except:
            return False
