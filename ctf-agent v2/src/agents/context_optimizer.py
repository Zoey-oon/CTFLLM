"""
Context Optimization Strategy for CTF Agent
智能上下文传递策略，优化Token使用
"""

from typing import Dict, List, Optional
from datetime import datetime
import re


class ContextOptimizer:
    """智能上下文优化器"""
    
    def __init__(self):
        self.full_context_interval = 5  # 每5轮发送完整上下文
        self.max_recent_tasks = 3       # 平时只发送最近3个任务
        self.token_budget = 1000        # Task Tree的token预算
        
    def should_send_full_context(self, current_round: int, task_count: int, recent_results: List[str] = None) -> bool:
        """判断是否应该发送完整上下文"""
        # 策略1: 每N轮发送完整上下文
        if current_round % self.full_context_interval == 0:
            return True
            
        # 策略2: 任务数量较少时总是发送完整上下文
        if task_count <= 3:
            return True
            
        # 策略3: 检测到重要节点时发送完整上下文
        if recent_results:
            for result in recent_results:
                if result and isinstance(result, str):
                    # 检测到flag
                    if re.search(r'pico[C:]?[T:]?F\{[^}]+\}', result, re.IGNORECASE):
                        return True
                    # 检测到错误
                    if any(error_word in result.lower() for error_word in ['error', 'failed', 'exception', 'traceback']):
                        return True
                        
        return False
    
    def get_optimized_task_context(self, task_tree, current_round: int, recent_results: List[str] = None) -> Dict[str, str]:
        """获取优化后的任务上下文"""
        if not task_tree or not hasattr(task_tree, 'tasks'):
            return {
                "context_type": "empty",
                "content": "No tasks recorded yet",
                "token_estimate": 20,
                "truncated_results": []  # 新增字段
            }
        
        task_count = len(task_tree.tasks)
        send_full = self.should_send_full_context(current_round, task_count, recent_results)
        
        if send_full:
            # 发送完整上下文
            full_content = task_tree.get_tree_display()
            # 检查是否有重要结果在task tree中被截断
            truncated_results = self._get_truncated_important_results(task_tree, recent_results)
            return {
                "context_type": "full",
                "content": full_content,
                "token_estimate": len(full_content) // 4,
                "tasks_included": task_count,
                "truncated_results": truncated_results  # 新增字段
            }
        else:
            # 发送精简上下文
            recent_content = self._get_recent_summary(task_tree, recent_results)
            return {
                "context_type": "recent",
                "content": recent_content,
                "token_estimate": len(recent_content) // 4,
                "tasks_included": min(self.max_recent_tasks, task_count),
                "truncated_results": []  # 精简模式下通过tool_results补充
            }
    
    def _get_recent_summary(self, task_tree, recent_results: List[str] = None) -> str:
        """Get recent tasks summary"""
        if not task_tree.tasks:
            return "No tasks completed yet"
        
        # Get recent tasks
        recent_tasks = task_tree.tasks[-self.max_recent_tasks:]
        
        lines = []
        for task in recent_tasks:
            status_icon = self._get_status_icon(task.get("status", ""))
            task_id = task.get("id", "?")
            description = task.get("description", "No description")
            lines.append(f"{status_icon} {task_id}. {description}")
            
            # Show only the last subtask result if it has meaningful output
            subtasks = task.get("subtasks", [])
            if subtasks:
                last_subtask = subtasks[-1]
                result = last_subtask.get("result", "")
                if result and len(result.strip()) > 0:
                    clean_result = result[:80] + "..." if len(result) > 80 else result
                    lines.append(f"   -> {clean_result}")
        
        return "\n".join(lines)
    
    def _get_status_icon(self, status: str) -> str:
        """Get status icon"""
        icons = {
            "completed": "[✓]",
            "in-progress": "[→]", 
            "failed": "[✗]",
            "pending": "[ ]"
        }
        return icons.get(status, "[?]")
    
    def _get_truncated_important_results(self, task_tree, recent_results: List[str] = None) -> List[str]:
        """检测在task tree中被截断的重要结果，保证最新结果一定包含"""
        if not recent_results:
            return []
        
        truncated_important = []
        
        # 获取最近的任务和子任务
        recent_tasks = task_tree.tasks[-2:] if len(task_tree.tasks) >= 2 else task_tree.tasks
        
        # 🔥 优先级1: 最新的tool结果必须完整包含（不允许截断）
        latest_result = recent_results[-1] if recent_results else None
        if latest_result and len(latest_result.strip()) > 80:
            # 最新结果如果超过80字符，无论是否重要都要包含完整版本
            if self._is_truncated_in_tree(latest_result, recent_tasks):
                truncated_important.append(latest_result)
                # Latest result guaranteed - will be confirmed in CTF Agent
        
        # 🔥 优先级2: 其他重要结果的补充
        for i, result in enumerate(recent_results[-3:-1]):  # 排除最新的，检查倒数第2-3个
            if not result or len(result.strip()) <= 80:
                continue  # 短结果不需要补充
                
            # 检查是否是重要信息
            if self._is_important_result(result):
                # 检查是否在task tree中被截断
                if self._is_truncated_in_tree(result, recent_tasks):
                    truncated_important.append(result)
        
        return truncated_important
    
    def _is_important_result(self, result: str) -> bool:
        """判断结果是否重要"""
        if not result:
            return False
            
        result_lower = result.lower()
        
        # 重要信息类型
        important_patterns = [
            # Flag相关
            r'pico[c:]?[t:]?f\{[^}]+\}',
            r'flag\s*[=:]',
            r'ctf\{',
            
            # 错误信息
            r'error\s*:',
            r'traceback',
            r'exception',
            r'failed',
            
            # 代码执行结果
            r'extracted\s+characters?\s*[:=]',
            r'decoded\s*[:=]',
            r'output\s*[:=]',
            r'result\s*[:=]',
            
            # 重要数据
            r'characters?\s+from',
            r'combination',
            r'potential\s+flag',
        ]
        
        for pattern in important_patterns:
            if re.search(pattern, result_lower):
                return True
                
        # 长度超过200字符的结果也认为可能重要
        return len(result) > 200
    
    def _is_truncated_in_tree(self, result: str, recent_tasks: List[Dict]) -> bool:
        """检查结果是否在task tree中被截断"""
        # 获取结果的前80个字符
        result_prefix = result[:80].strip()
        
        for task in recent_tasks:
            subtasks = task.get("subtasks", [])
            for subtask in subtasks:
                tree_result = subtask.get("result", "")
                if tree_result and result_prefix in tree_result and len(result) > len(tree_result):
                    return True
        return False
    
    def get_context_stats(self, context_data: Dict) -> str:
        """获取上下文统计信息"""
        context_type = context_data.get("context_type", "unknown")
        token_estimate = context_data.get("token_estimate", 0)
        tasks_included = context_data.get("tasks_included", 0)
        truncated_count = len(context_data.get("truncated_results", []))
        
        base_stats = ""
        if context_type == "full":
            base_stats = f"Full context: {tasks_included} tasks (~{token_estimate} tokens)"
        elif context_type == "recent":
            base_stats = f"Recent context: {tasks_included} tasks (~{token_estimate} tokens)"
        else:
            base_stats = f"Minimal context (~{token_estimate} tokens)"
            
        if truncated_count > 0:
            base_stats += f" + {truncated_count} important results"
            
        return base_stats
