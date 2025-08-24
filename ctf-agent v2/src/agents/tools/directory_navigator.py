"""
Directory navigation tool for CTF challenges requiring file system navigation.
"""
import os
from typing import Dict, Any, List

class DirectoryNavigatorTool:
    def __init__(self):
        self.name = "directory_navigator"
        self.description = "Navigate directories and manage working directory for CTF challenges"
        self.current_working_dir = os.getcwd()
        self.directory_history = [self.current_working_dir]
    
    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute directory navigation commands.
        
        Args:
            params: {
                "action": "cd", "pwd", "ls", "find", "navigate",
                "path": "target path for navigation",
                "command": "specific command to execute"
            }
        """
        try:
            action = params.get("action", "navigate")
            path = params.get("path", "")
            command = params.get("command", "")
            
            if action == "cd":
                return self._change_directory(path)
            elif action == "pwd":
                return self._show_current_directory()
            elif action == "ls":
                return self._list_directory(path)
            elif action == "find":
                return self._find_files(path)
            elif action == "navigate":
                return self._navigate_to_path(path)
            else:
                return {"success": False, "error": f"Unknown action: {action}"}
                
        except Exception as e:
            return {"success": False, "error": f"Navigation failed: {str(e)}"}
    
    def _change_directory(self, path: str) -> Dict[str, Any]:
        """Change to specified directory"""
        if not path:
            # cd without args goes to home directory
            new_path = os.path.expanduser("~")
        elif path.startswith('/'):
            # Absolute path
            new_path = path
        elif path == '.':
            return {"success": True, "output": f"Current directory: {self.current_working_dir}"}
        elif path == '..':
            new_path = os.path.dirname(self.current_working_dir)
        elif path == '~':
            new_path = os.path.expanduser("~")
        elif path == '-':
            # Go to previous directory
            if len(self.directory_history) > 1:
                new_path = self.directory_history[-2]
                self.directory_history.pop()  # Remove current
            else:
                return {"success": False, "error": "No previous directory to go back to"}
        else:
            # Relative path from current directory
            new_path = os.path.join(self.current_working_dir, path)
        
        # Check if directory exists and is accessible
        if not os.path.exists(new_path):
            return {"success": False, "error": f"Directory '{new_path}' does not exist"}
        if not os.path.isdir(new_path):
            return {"success": False, "error": f"'{new_path}' is not a directory"}
        if not os.access(new_path, os.R_OK):
            return {"success": False, "error": f"Permission denied accessing '{new_path}'"}
        
        # Update directory history
        self.directory_history.append(self.current_working_dir)
        if len(self.directory_history) > 10:  # Keep only last 10 directories
            self.directory_history.pop(0)
        
        # Change working directory
        self.current_working_dir = os.path.abspath(new_path)
        return {"success": True, "output": f"Changed directory to: {self.current_working_dir}"}
    
    def _show_current_directory(self) -> Dict[str, Any]:
        """Show current working directory"""
        return {"success": True, "output": self.current_working_dir}
    
    def _list_directory(self, path: str = "") -> Dict[str, Any]:
        """List contents of specified directory or current directory"""
        target_path = path if path else self.current_working_dir
        
        if not os.path.exists(target_path):
            return {"success": False, "error": f"Path '{target_path}' does not exist"}
        if not os.path.isdir(target_path):
            return {"success": False, "error": f"'{target_path}' is not a directory"}
        
        try:
            items = os.listdir(target_path)
            # Separate files and directories
            files = []
            directories = []
            
            for item in items:
                item_path = os.path.join(target_path, item)
                if os.path.isdir(item_path):
                    directories.append(f"[DIR] {item}/")
                else:
                    # Check if it's executable
                    if os.access(item_path, os.X_OK):
                        files.append(f"[EXE] {item}*")
                    else:
                        files.append(f"[FILE] {item}")
            
            # Sort and format output
            directories.sort()
            files.sort()
            
            output_lines = [f"Contents of: {target_path}"]
            output_lines.append("")
            
            if directories:
                output_lines.append("Directories:")
                output_lines.extend(directories)
                output_lines.append("")
            
            if files:
                output_lines.append("Files:")
                output_lines.extend(files)
            
            return {"success": True, "output": "\n".join(output_lines)}
            
        except PermissionError:
            return {"success": False, "error": f"Permission denied accessing '{target_path}'"}
        except Exception as e:
            return {"success": False, "error": f"Error listing directory: {str(e)}"}
    
    def _find_files(self, pattern: str) -> Dict[str, Any]:
        """Find files matching pattern in current directory and subdirectories"""
        if not pattern:
            return {"success": False, "error": "Search pattern is required"}
        
        found_files = []
        try:
            for root, dirs, files in os.walk(self.current_working_dir):
                for file in files:
                    if pattern.lower() in file.lower():
                        rel_path = os.path.relpath(os.path.join(root, file), self.current_working_dir)
                        found_files.append(rel_path)
                
                # Limit results to avoid overwhelming output
                if len(found_files) > 50:
                    found_files.append("... (more files found)")
                    break
            
            if found_files:
                return {"success": True, "output": f"Found {len(found_files)} files matching '{pattern}':\n" + "\n".join(found_files)}
            else:
                return {"success": True, "output": f"No files found matching '{pattern}'"}
                
        except Exception as e:
            return {"success": False, "error": f"Search failed: {str(e)}"}
    
    def _navigate_to_path(self, path: str) -> Dict[str, Any]:
        """Navigate to a specific path and show its contents"""
        if not path:
            return {"success": False, "error": "Path is required for navigation"}
        
        # First change to the directory
        cd_result = self._change_directory(path)
        if not cd_result["success"]:
            return cd_result
        
        # Then list its contents
        ls_result = self._list_directory()
        if not ls_result["success"]:
            return ls_result
        
        # Combine results
        return {
            "success": True,
            "output": f"{cd_result['output']}\n\n{ls_result['output']}"
        }
    
    def get_current_directory(self) -> str:
        """Get current working directory"""
        return self.current_working_dir
    
    def get_directory_history(self) -> List[str]:
        """Get directory navigation history"""
        return self.directory_history.copy()

# Tool registration for CTF Agent
def create_directory_navigator_tool():
    """Create directory navigator tool for CTF agent"""
    tool = DirectoryNavigatorTool()
    
    def directory_navigator_func(action: str = "navigate", path: str = "", command: str = ""):
        """
        Navigate directories and manage working directory.
        
        Args:
            action: Navigation action (cd, pwd, ls, find, navigate)
            path: Target path for the action
            command: Specific command to execute
            
        Returns:
            Navigation result and directory information
        """
        params = {
            "action": action,
            "path": path,
            "command": command
        }
        return tool.execute(params)
    
    return directory_navigator_func
