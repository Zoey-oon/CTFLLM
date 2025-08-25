"""
Python package installer tool for CTF challenges requiring crypto/math libraries.
"""
import subprocess
import sys
import importlib
from typing import Dict, Any, List

class PackageInstaller:
    def __init__(self):
        self.name = "package_installer"
        self.description = "Install Python packages required for CTF challenges"
        
        # All packages and tools commonly needed for CTF challenges
        self.ctf_packages = {
            # Python Packages - Cryptography & Math
            'pycryptodome': 'Crypto',
            'cryptography': 'cryptography',
            'sympy': 'sympy',
            'gmpy2': 'gmpy2',
            'z3-solver': 'z3',
            
            # Python Packages - Binary Analysis & Reverse Engineering
            'pwntools': 'pwn',
            'angr': 'angr',
            'capstone': 'capstone',
            'keystone': 'keystone',
            'unicorn': 'unicorn',
            'pefile': 'pefile',
            'pyelftools': 'elftools',
            'lief': 'lief',
            
            # Python Packages - Network & Web
            'requests': 'requests',
            'urllib3': 'urllib3',
            'websockets': 'websockets',
            'scapy': 'scapy',
            
            # Python Packages - Data Processing & Forensics
            'numpy': 'numpy',
            'pandas': 'pandas',
            'matplotlib': 'matplotlib',
            'pillow': 'PIL',
            
            # Python Packages - Image & QR Code Processing
            'qrcode': 'qrcode',
            'pyzbar': 'pyzbar',
            'opencv-python': 'cv2',
            
            # System Tools - Binary Analysis & Reverse Engineering
            'upx': 'system_tool',
            'binwalk': 'system_tool', 
            'file': 'system_tool',
            'strings': 'system_tool',
            'objdump': 'system_tool',
            'readelf': 'system_tool',
            'gdb': 'system_tool',
            'radare2': 'system_tool',
            'xxd': 'system_tool',
            
            # System Tools - Forensics & File Recovery
            'foremost': 'system_tool',
            'scalpel': 'system_tool',
            'testdisk': 'system_tool',
            'sleuthkit': 'system_tool',
            
            # System Tools - Steganography & Metadata
            'steghide': 'system_tool',
            'exiftool': 'system_tool',
            
            # System Tools - Network
            'nmap': 'system_tool',
            'netcat': 'system_tool',
            'telnet': 'system_tool',
        }
        
        # Built-in packages (no installation needed)
        self.builtin_packages = {
            'base64', 'codecs', 'hashlib', 'binascii', 'struct', 
            'json', 're', 'os', 'sys', 'math', 'random'
        }
    
    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Install Python packages for CTF challenges.
        
        Args:
            params: {
                "packages": "package1 package2" or ["package1", "package2"],
                "auto_install_common": bool (optional),
                "check_only": bool (optional)
            }
        
        Returns:
            Dict with installation results
        """
        try:
            packages = params.get("packages", [])
            auto_install_common = params.get("auto_install_common", False)
            check_only = params.get("check_only", False)
            
            if isinstance(packages, str):
                packages = packages.split()
            elif not isinstance(packages, list):
                packages = []
            
            if auto_install_common:
                # Install common CTF packages
                packages.extend([
                    'pycryptodome', 'requests', 'numpy', 'pillow', 
                    'sympy', 'pwntools', 'scapy', 'z3-solver'
                ])
            
            if not packages:
                return {
                    "success": False,
                    "error": "No packages specified",
                    "available_packages": list(self.ctf_packages.keys())
                }
            
            results = []
            for package in packages:
                if package in self.builtin_packages:
                    results.append({
                        "package": package,
                        "status": "builtin",
                        "success": True,
                        "message": f"{package} is a built-in Python module"
                    })
                    continue
                
                result = self._install_package(package, check_only=check_only)
                results.append(result)
            
            successful = sum(1 for r in results if r["success"])
            total = len(results)
            
            return {
                "success": successful == total,
                "installed": successful,
                "total": total,
                "results": results,
                "summary": f"Successfully processed {successful}/{total} packages"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Package installation failed: {str(e)}"
            }
    
    def _install_package(self, package_name: str, check_only: bool = False) -> Dict[str, Any]:
        """Install or check a single package (Python package or system tool)."""
        try:
            import_name = self.ctf_packages.get(package_name, package_name)
            
            # Handle system tools
            if import_name == 'system_tool':
                return self._check_system_tool(package_name)
            
            # Handle Python packages
            try:
                if import_name == package_name:
                    importlib.import_module(package_name)
                else:
                    importlib.import_module(import_name)
                
                return {
                    "package": package_name,
                    "status": "already_installed",
                    "success": True,
                    "message": f"{package_name} is already installed"
                }
            except ImportError:
                pass
            
            if check_only:
                return {
                    "package": package_name,
                    "status": "not_installed",
                    "success": False,
                    "message": f"{package_name} is not installed"
                }
            
            # Install the Python package
            try:
                subprocess.check_call([
                    sys.executable, "-m", "pip", "install", package_name
                ], capture_output=True)
                
                # Verify installation
                if import_name == package_name:
                    importlib.import_module(package_name)
                else:
                    importlib.import_module(import_name)
                
                return {
                    "package": package_name,
                    "status": "installed",
                    "success": True,
                    "message": f"Successfully installed {package_name}"
                }
                
            except subprocess.CalledProcessError as e:
                return {
                    "package": package_name,
                    "status": "install_failed",
                    "success": False,
                    "error": f"pip install failed: {e}"
                }
            except ImportError as e:
                return {
                    "package": package_name,
                    "status": "import_failed",
                    "success": False,
                    "error": f"Package installed but import failed: {e}"
                }
                
        except Exception as e:
            return {
                "package": package_name,
                "status": "error",
                "success": False,
                "error": str(e)
            }
    
    def _check_system_tool(self, tool_name: str) -> Dict[str, Any]:
        """Check if a system tool is available."""
        try:
            result = subprocess.run(['which', tool_name], capture_output=True, text=True)
            if result.returncode == 0:
                return {
                    "package": tool_name,
                    "status": "available",
                    "success": True,
                    "message": f"{tool_name} is available (system tool)"
                }
            else:
                return {
                    "package": tool_name,
                    "status": "not_available",
                    "success": False,
                    "message": f"{tool_name} is not available (should be pre-installed in Docker)"
                }
        except Exception as e:
            return {
                "package": tool_name,
                "status": "error",
                "success": False,
                "error": f"Error checking {tool_name}: {str(e)}"
            }
    
    def __call__(self, **kwargs) -> Dict[str, Any]:
        """Allow direct calling of the installer."""
        return self.execute(kwargs)

# Global instance
pkg_tool = PackageInstaller()

# Tool interface for CTF Agent (optional, only loaded when langchain is available)
try:
    from langchain.tools import BaseTool

    class PackageInstallerTool(BaseTool):
        name: str = "package_installer"
        description: str = "Install Python packages for CTF challenges. Usage: <tool>package_installer</tool><input>package_name1 package_name2</input> or <tool>package_installer</tool><input>auto_common</input> for common CTF packages"
        
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
                
                if result["success"]:
                    return f"✅ Package installation completed: {result['summary']}"
                else:
                    return f"❌ Package installation failed: {result.get('error', 'Unknown error')}"
                    
            except Exception as e:
                return f"❌ Error during package installation: {str(e)}"
        
        async def _arun(self, query: str) -> str:
            return self._run(query)

except ImportError:
    # langchain not available, PackageInstallerTool will not be created
    PackageInstallerTool = None