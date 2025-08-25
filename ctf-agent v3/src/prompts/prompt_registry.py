"""
Centralized Prompt Registry System
Manages all prompts for CTF agent in a file-based, version-controlled manner
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from enum import Enum


class PromptType(Enum):
    """Types of prompts in the system"""
    SYSTEM = "system"
    CHALLENGE = "challenge" 
    CONTINUE = "continue"
    TOOL = "tool"
    VERIFICATION = "verification"


class ChallengeType(Enum):
    """CTF Challenge types"""
    CRYPTOGRAPHY = "Cryptography"
    WEB = "Web Exploitation"
    REVERSE = "Reverse Engineering"
    FORENSICS = "Forensics"
    GENERAL = "General Skills"
    BINARY = "Binary Exploitation"
    PWNING = "Pwning"


class PromptRegistry:
    """Centralized prompt management system"""
    
    def __init__(self, prompts_dir: Optional[str] = None):
        if prompts_dir is None:
            prompts_dir = Path(__file__).parent / "templates"
        self.prompts_dir = Path(prompts_dir)
        self.prompts_dir.mkdir(exist_ok=True)
        
        # Cache loaded prompts
        self._prompt_cache = {}
        
        # Initialize prompt files if they don't exist
        self._initialize_prompt_files()
    
    def _initialize_prompt_files(self):
        """Initialize prompt template files if they don't exist"""
        # Create subdirectories
        for prompt_type in PromptType:
            subdir = self.prompts_dir / prompt_type.value
            subdir.mkdir(exist_ok=True)
    
    def get_system_prompt(self) -> str:
        """Get system prompt for Agent creation"""
        return self._load_prompt(PromptType.SYSTEM, "agent_system")
    
    def get_challenge_prompt(self, challenge_type: str, challenge_data: Dict) -> str:
        """Get challenge-specific prompt"""
        # Normalize challenge type
        if challenge_type not in [ct.value for ct in ChallengeType]:
            challenge_type = ChallengeType.GENERAL.value
        
        template = self._load_prompt(PromptType.CHALLENGE, challenge_type.lower().replace(" ", "_"))
        return self._fill_template(template, challenge_data)
    
    def get_continue_prompt(self, context: Dict, tool_results: List[str] = None, show_all_flags: bool = False) -> str:
        """Get continue conversation prompt"""
        if show_all_flags:
            template = self._load_prompt(PromptType.CONTINUE, "show_all_flags")
        else:
            template = self._load_prompt(PromptType.CONTINUE, "standard")
        
        return self._fill_template(template, context, {"tool_results": tool_results or []})
    
    def get_verification_prompt(self, tool_results: List[str] = None) -> str:
        """Get final verification prompt"""
        template = self._load_prompt(PromptType.VERIFICATION, "final_answer")
        return self._fill_template(template, {"tool_results": tool_results or []})
    
    def get_tool_prompt(self, tool_name: str) -> str:
        """Get tool description prompt"""
        return self._load_prompt(PromptType.TOOL, tool_name)
    
    def get_initial_challenge_suffix(self) -> str:
        """Get the suffix added to initial challenge prompts"""
        return self._load_prompt(PromptType.CHALLENGE, "initial_suffix")
    
    def get_general_tool_instructions(self) -> str:
        """Get general tool usage instructions"""
        return self._load_prompt(PromptType.TOOL, "general_instructions")
    
    def get_determine_next_step_prompt(self, results: List[str] = None) -> str:
        """Get prompt for determining next step"""
        template = self._load_prompt(PromptType.CONTINUE, "determine_next_step")
        results_text = '\n'.join(results) if results else "Let's start solving this challenge. What's the first step?"
        # 直接替换模板中的{results}变量
        return template.replace("{results}", results_text)
    
    def get_human_feedback_prompt(self, human_feedback: str) -> str:
        """Get prompt for human feedback processing"""
        template = self._load_prompt(PromptType.CONTINUE, "human_feedback")
        # Directly format the template with human_feedback
        return template.format(human_feedback=human_feedback)
    
    def get_task_tree_management_prompt(self) -> str:
        """Get task tree management instructions for LLM"""
        task_tree_dir = self.prompts_dir / "task_tree"
        file_path = task_tree_dir / "llm_management.txt"
        
        if not file_path.exists():
            return "Remember to update the task tree using the task_tree tool after each step."
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except Exception:
            return "Remember to update the task tree using the task_tree tool after each step."
    
    def _load_prompt(self, prompt_type: PromptType, template_name: str) -> str:
        """Load prompt from file with caching"""
        cache_key = f"{prompt_type.value}:{template_name}"
        
        if cache_key in self._prompt_cache:
            return self._prompt_cache[cache_key]
        
        file_path = self.prompts_dir / prompt_type.value / f"{template_name}.txt"
        
        if not file_path.exists():
            # Create default prompt if file doesn't exist
            default_content = self._get_default_prompt(prompt_type, template_name)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(default_content)
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        
        self._prompt_cache[cache_key] = content
        return content
    
    def _fill_template(self, template: str, context: Dict, extra_vars: Optional[Dict] = None) -> str:
        """Fill template with context data"""
        try:
            # Prepare template variables
            variables = {
                'challenge_name': context.get('title', 'Unknown Challenge'),
                'challenge_description': context.get('description', 'No description'),
                'challenge_category': context.get('category', 'Unknown'),
                'files_list': self._format_files_list(context.get('files', [])),
                'task_summary': context.get('task_summary', ''),
                'goal': 'Find the final flag in picoCTF{{...}} format only. Do not drift from the task.'
            }
            
            # Add SSH information if available
            if 'ssh_info' in context:
                ssh_info = context['ssh_info']
                variables['ssh_connection'] = f"SSH Connection: ssh -p {ssh_info.get('port', 22)} {ssh_info.get('username', 'user')}@{ssh_info.get('host', 'localhost')}"
                variables['ssh_password'] = f"Password: {ssh_info.get('password', 'N/A')}"
            else:
                variables['ssh_connection'] = "No SSH connection required"
                variables['ssh_password'] = ""
            
            # Add challenge type information
            if 'challenge_type' in context:
                variables['challenge_type'] = context['challenge_type']
            else:
                variables['challenge_type'] = "general"
            
            if extra_vars:
                variables.update(extra_vars)
                
            # Handle tool_results formatting
            if 'tool_results' in variables:
                results = variables['tool_results']
                if isinstance(results, list) and results:
                    results_text = '\n'.join(f"Result {i+1}:\n{result}\n" for i, result in enumerate(results))
                    variables['results'] = results_text
                elif results is None:
                    # When tool_results is explicitly None, rely only on task tree
                    variables['results'] = "Based on task tree context above."
                else:
                    variables['results'] = "No previous execution results. Let's start by reading and decoding the input."
            
            return template.format(**variables)
        except KeyError as e:
            # Return template with error note if variable missing
            return f"{template}\n\n[Note: Template variable {e} not found]"
    
    def _format_files_list(self, files: List[str]) -> str:
        """Format files list for template"""
        if not files:
            return "No files provided"
        
        formatted = []
        for i, file_path in enumerate(files, 1):
            file_name = file_path.split('/')[-1] if '/' in file_path else file_path
            formatted.append(f"[File {i}]: {file_name}")
        
        return '\n'.join(formatted)
    
    def _get_default_prompt(self, prompt_type: PromptType, template_name: str) -> str:
        """Get minimal default prompt content when file doesn't exist"""
        return f"[Auto-generated default prompt for {prompt_type.value}:{template_name}]\n\nThis is a placeholder prompt. Please create the template file {prompt_type.value}/{template_name}.txt to customize this prompt."
    
    def reload_prompts(self):
        """Clear cache and reload all prompts"""
        self._prompt_cache.clear()
    
    def list_available_prompts(self) -> Dict[str, List[str]]:
        """List all available prompt templates"""
        available = {}
        for prompt_type in PromptType:
            type_dir = self.prompts_dir / prompt_type.value
            if type_dir.exists():
                available[prompt_type.value] = [
                    f.stem for f in type_dir.glob("*.txt")
                ]
            else:
                available[prompt_type.value] = []
        return available
