"""
ZIP file handler tool for CTF challenges.
"""
import zipfile
import os
import tempfile
import shutil
from typing import Dict, Any, List, Optional
import json

class ZipHandler:
    def __init__(self):
        self.name = "zip_handler"
        self.description = "Handle ZIP files: extract content and read files"
        
    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle ZIP file operations.
        
        Args:
            params: {
                "action": "list" | "extract" | "read" | "extract_and_read",
                "zip_path": "Path to ZIP file",
                "target_file": "Specific file to read" (optional),
                "extract_to": "Extraction directory" (optional, defaults to temp dir),
                "encoding": "File encoding" (optional, defaults to utf-8)
            }
        """
        try:
            action = params.get("action", "list")
            zip_path = params.get("zip_path")
            target_file = params.get("target_file")
            extract_to = params.get("extract_to")
            encoding = params.get("encoding", "utf-8")
            
            if not zip_path:
                return {"success": False, "error": "zip_path parameter is required"}
            
            if not os.path.exists(zip_path):
                return {"success": False, "error": f"ZIP file not found: {zip_path}"}
            
            # Verify if it's a valid ZIP file
            if not zipfile.is_zipfile(zip_path):
                return {"success": False, "error": f"File is not a valid ZIP format: {zip_path}"}
            
            with zipfile.ZipFile(zip_path, 'r') as zip_file:
                if action == "list":
                    return self._list_contents(zip_file)
                elif action == "extract":
                    return self._extract_files(zip_file, extract_to)
                elif action == "read":
                    return self._read_file(zip_file, target_file, encoding)
                elif action == "extract_and_read":
                    return self._extract_and_read_all(zip_file, extract_to, encoding)
                else:
                    return {"success": False, "error": f"Unsupported action: {action}"}
                    
        except Exception as e:
            return {"success": False, "error": f"ZIP processing error: {str(e)}"}
    
    def _list_contents(self, zip_file: zipfile.ZipFile) -> Dict[str, Any]:
        """List ZIP file contents"""
        try:
            file_list = []
            for info in zip_file.infolist():
                file_info = {
                    "filename": info.filename,
                    "file_size": info.file_size,
                    "compress_size": info.compress_size,
                    "is_dir": info.is_dir(),
                    "date_time": list(info.date_time),
                    "compress_type": info.compress_type
                }
                file_list.append(file_info)
            
            return {
                "success": True,
                "action": "list",
                "file_count": len(file_list),
                "files": file_list,
                "file_names": [f["filename"] for f in file_list]
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to list files: {str(e)}"}
    
    def _extract_files(self, zip_file: zipfile.ZipFile, extract_to: Optional[str] = None) -> Dict[str, Any]:
        """Extract ZIP file contents to challenge directory"""
        try:
            if extract_to is None:
                # Try to extract to current challenge directory, not temporary
                current_challenge_dir = self._get_current_challenge_dir()
                if current_challenge_dir:
                    # Create extracted subdirectory in challenge directory
                    extract_to = os.path.join(current_challenge_dir, "extracted")
                else:
                    # Fallback to temporary directory if challenge dir cannot be determined
                    extract_to = tempfile.mkdtemp(prefix="ctf_extract_")
            else:
                # If user specified path, ensure it's absolute
                if not os.path.isabs(extract_to):
                    extract_to = os.path.abspath(extract_to)
            
            # Ensure target directory exists
            os.makedirs(extract_to, exist_ok=True)
            
            # Safely extract files (prevent path traversal attacks)
            extracted_files = []
            for member in zip_file.namelist():
                # Check path safety
                if os.path.isabs(member) or ".." in member:
                    continue  # Skip unsafe paths
                
                zip_file.extract(member, extract_to)
                extracted_path = os.path.join(extract_to, member)
                if os.path.exists(extracted_path):
                    extracted_files.append({
                        "original_path": member,
                        "extracted_path": extracted_path,
                        "relative_path": member,  # 添加相对路径信息
                        "is_dir": os.path.isdir(extracted_path)
                    })
            
            # Generate clear path information for LLM
            path_info = []
            relative_paths = []
            for file_info in extracted_files:
                if not file_info["is_dir"]:
                    abs_path = file_info["extracted_path"]
                    rel_path = file_info["relative_path"]
                    path_info.append(f"  - {rel_path} → {abs_path}")
                    relative_paths.append(rel_path)
            
            usage_note = f"""Files extracted successfully! Use these paths:

EXTRACTED FILES:
{chr(10).join(path_info)}

TO ACCESS FILES:
- Use absolute paths: {extract_to}/filename
- Use relative paths from extraction directory: filename
- Current extraction directory: {extract_to}

EXAMPLE COMMANDS:
- Read file: use file_reader with path '{extract_to}/home/ctf-player/drop-in/flag.png'
- Or simply: 'flag.png' (will be auto-located)"""
            
            return {
                "success": True,
                "action": "extract",
                "extract_path": extract_to,
                "extracted_files": extracted_files,
                "file_count": len(extracted_files),
                "relative_paths": relative_paths,
                "message": f"Files extracted to: {extract_to}",
                "usage_note": usage_note
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to extract files: {str(e)}"}
    
    def _get_current_challenge_dir(self) -> Optional[str]:
        """Get the current challenge directory based on working directory"""
        try:
            # Get current working directory
            cwd = os.getcwd()
            
            # Check if we're in a challenge directory (support both real and test structures)
            # Priority: check test_challenges first, then challenges
            if 'test_challenges' in cwd:
                # Handle test directory structure
                parts = cwd.split(os.sep)
                test_challenges_index = parts.index('test_challenges')
                if test_challenges_index + 3 < len(parts):  # test_challenges/year/category/name
                    # Build absolute path correctly
                    challenge_path = os.sep.join(parts[:test_challenges_index + 4])
                    if os.path.exists(challenge_path):
                        return challenge_path
            elif 'challenges' in cwd:
                # Find the challenge directory path
                parts = cwd.split(os.sep)
                challenges_index = parts.index('challenges')
                if challenges_index + 3 < len(parts):  # challenges/year/category/name
                    # Build absolute path correctly
                    challenge_path = os.sep.join(parts[:challenges_index + 4])
                    if os.path.exists(challenge_path):
                        return challenge_path
            
            # Fallback: try to find from environment or context
            return None
        except Exception:
            return None
    
    def _read_file(self, zip_file: zipfile.ZipFile, target_file: str, encoding: str = "utf-8") -> Dict[str, Any]:
        """Read specific file content from ZIP"""
        try:
            if not target_file:
                return {"success": False, "error": "target_file parameter is required"}
            
            # Check if file exists in ZIP
            if target_file not in zip_file.namelist():
                available_files = zip_file.namelist()
                return {
                    "success": False, 
                    "error": f"File '{target_file}' not found in ZIP",
                    "available_files": available_files
                }
            
            # Read file content
            with zip_file.open(target_file) as file:
                try:
                    content = file.read().decode(encoding)
                    is_binary = False
                except UnicodeDecodeError:
                    # If can't decode as text, try as binary
                    file.seek(0)
                    content = file.read()
                    is_binary = True
            
            file_info = zip_file.getinfo(target_file)
            
            return {
                "success": True,
                "action": "read",
                "file_path": target_file,
                "content": content,
                "is_binary": is_binary,
                "file_size": file_info.file_size,
                "encoding": encoding if not is_binary else "binary"
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to read file: {str(e)}"}
    
    def _extract_and_read_all(self, zip_file: zipfile.ZipFile, extract_to: Optional[str] = None, encoding: str = "utf-8") -> Dict[str, Any]:
        """Extract and read all text file contents"""
        try:
            # First extract files
            extract_result = self._extract_files(zip_file, extract_to)
            if not extract_result["success"]:
                return extract_result
            
            # Then read all text files
            file_contents = {}
            binary_files = []
            
            for file_info in extract_result["extracted_files"]:
                if file_info["is_dir"]:
                    continue
                
                original_path = file_info["original_path"]
                try:
                    read_result = self._read_file(zip_file, original_path, encoding)
                    if read_result["success"]:
                        if read_result["is_binary"]:
                            binary_files.append(original_path)
                        else:
                            file_contents[original_path] = {
                                "content": read_result["content"],
                                "size": read_result["file_size"],
                                "encoding": read_result["encoding"]
                            }
                except Exception as e:
                    # Record failed files but continue processing others
                    file_contents[original_path] = {
                        "error": f"Read failed: {str(e)}"
                    }
            
            return {
                "success": True,
                "action": "extract_and_read",
                "extract_path": extract_result["extract_path"],
                "extracted_files": extract_result["extracted_files"],
                "file_contents": file_contents,
                "binary_files": binary_files,
                "text_file_count": len(file_contents),
                "binary_file_count": len(binary_files)
            }
        except Exception as e:
            return {"success": False, "error": f"Extract and read failed: {str(e)}"}

def create_zip_handler_tool():
    """Create ZIP handler tool for CTF agent"""
    tool = ZipHandler()
    
    def zip_handler_func(action: str, zip_path: str, target_file: str = None, extract_to: str = None, encoding: str = "utf-8"):
        """
        ZIP file handler function.
        
        Args:
            action: Operation type ("list", "extract", "read", "extract_and_read")
            zip_path: Path to ZIP file
            target_file: Specific file to read (only for "read" action)
            extract_to: Extraction target directory (optional)
            encoding: File encoding (default utf-8)
            
        Returns:
            Operation result and file contents
        """
        params = {
            "action": action,
            "zip_path": zip_path,
            "target_file": target_file,
            "extract_to": extract_to,
            "encoding": encoding
        }
        return tool.execute(params)
    
    return zip_handler_func
