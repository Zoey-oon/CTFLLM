#!/usr/bin/env python3
"""
Task Reporter Tool - Structured task status reporting tool
For background task status management, reducing redundant task management prompts in conversations
"""

import json
import uuid
from typing import List, Optional, Dict, Any, Literal
from langchain.tools import BaseTool
from pydantic import BaseModel, Field, PrivateAttr

TaskStatus = Literal["pending", "in_progress", "completed", "failed"]

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

class TaskReporter(BaseTool):
    """Structured task status reporting tool"""
    name: str = "report_task_update"
    description: str = """Report task status updates. Used for background task progress management, reducing task management redundancy in conversations.
Input JSON format:
{
  "updates": [
    {
      "task_id": "optional, auto-generated if empty",
      "description": "task description",
      "status": "pending|in_progress|completed|failed",
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
        self._task_tree = None
    
    def _run(self, input_str: str) -> str:
        """Process task updates"""
        try:
            # Parse input
            if isinstance(input_str, str):
                input_data = json.loads(input_str)
            else:
                input_data = input_str
            
            # Validate input structure
            report_input = TaskReportInput(**input_data)
            
            # Process task updates
            processed_tasks = []
            for update in report_input.updates:
                # Auto-generate ID
                if not update.task_id:
                    update.task_id = str(uuid.uuid4())[:8]
                
                # Update task tree (if available)
                if self._task_tree:
                    try:
                        self._task_tree.update_task_status(
                            task_id=update.task_id,
                            description=update.description,
                            status=update.status,
                            details=update.details
                        )
                    except Exception as e:
                        # Task tree update failure doesn't affect overall process
                        pass
                
                processed_tasks.append({
                    "task_id": update.task_id,
                    "description": update.description,
                    "status": update.status,
                    "parent_id": update.parent_id,
                    "details": update.details
                })
            
            return json.dumps({
                "success": True,
                "processed_tasks": processed_tasks,
                "count": len(processed_tasks)
            })
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"Task update failed: {str(e)}",
                "processed_tasks": []
            })
    
    def _arun(self, input_str: str) -> str:
        return self._run(input_str)

    def set_task_tree(self, task_tree):
        """Set task tree reference"""
        self._task_tree = task_tree
