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
        
        # Common CTF packages and their import names
        self.ctf_packages = {
            # Cryptography
            'pycryptodome': 'Crypto',
            'cryptography': 'cryptography',
            'pycrypto': 'Crypto',  # Legacy, prefer pycryptodome
            
            # Math and number theory
            'sympy': 'sympy',
            'gmpy2': 'gmpy2',
            'sage-math': 'sage',  # Note: Complex installation
            
            # Network and web
            'requests': 'requests',
            'urllib3': 'urllib3',
            'websockets': 'websockets',
            'scapy': 'scapy',
            
            # Binary analysis
            'pwntools': 'pwn',
            'binascii': 'binascii',  # Built-in
            'struct': 'struct',      # Built-in
            
            # Data processing
            'numpy': 'numpy',
            'pandas': 'pandas',
            'matplotlib': 'matplotlib',
            
            # Encoding/decoding
            'base64': 'base64',      # Built-in
            'codecs': 'codecs',      # Built-in
            'hashlib': 'hashlib',    # Built-in
            
            # Misc utilities
            'pillow': 'PIL',
            'qrcode': 'qrcode',
            'pyzbar': 'pyzbar',  # QR code and barcode reading (requires system zbar)
            'opencv-python': 'cv2',  # Computer vision library
            'z3-solver': 'z3',
            'angr': 'angr',
        }
        
        # Packages that are usually pre-installed or built-in
        self.builtin_packages = {
            'base64', 'codecs', 'hashlib', 'binascii', 'struct', 
            'json', 're', 'os', 'sys', 'math', 'random'
        }
    
    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Install Python packages for CTF challenges.
        
        Args:
            params: {
                "packages": ["package1", "package2"] or "package_name",
                "auto_install_common": True/False (install common CTF packages),
                "force_reinstall": True/False
            }
        """
        try:
            packages = params.get("packages", [])
            auto_install = params.get("auto_install_common", False)
            force_reinstall = params.get("force_reinstall", False)
            
            if isinstance(packages, str):
                packages = [packages]
            
            results = []
            
            # Auto-install common CTF packages if requested
            if auto_install:
                common_packages = [
                    'pycryptodome', 'requests', 'sympy', 'gmpy2', 
                    'numpy', 'pillow', 'qrcode', 'opencv-python', 'pyzbar', 'z3-solver'
                ]
                packages.extend(common_packages)
                packages = list(set(packages))  # Remove duplicates
            
            for package in packages:
                result = self._install_package(package, force_reinstall)
                results.append(result)
            
            # Summary
            successful = sum(1 for r in results if r["success"])
            failed = len(results) - successful
            
            # Test imports after installation
            import_status = []
            for package in packages:
                import_name = self.ctf_packages.get(package, package)
                try:
                    __import__(import_name)
                    import_status.append(f"✅ {package} -> {import_name}")
                except ImportError:
                    import_status.append(f"❌ {package} -> {import_name}")
            
            return {
                "success": True,
                "installed": successful,
                "failed": failed,
                "details": results,
                "import_test": import_status,
                "message": f"Installed {successful}/{len(results)} packages successfully. Import test: {', '.join(import_status)}"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _install_package(self, package: str, force: bool = False) -> Dict[str, Any]:
        """Install a single package with retry mechanism"""
        try:
            # Check if it's a built-in package
            if package in self.builtin_packages:
                return {
                    "package": package,
                    "success": True,
                    "message": "Built-in package, no installation needed",
                    "status": "built-in"
                }
            
            # Check if already installed (unless force reinstall)
            import_name = self.ctf_packages.get(package, package)
            if not force and self._is_package_available(import_name):
                return {
                    "package": package,
                    "success": True,
                    "message": "Package already available",
                    "status": "already_installed"
                }
            
            # Try installation with multiple strategies
            strategies = [
                # Strategy 1: Standard pip install
                {
                    "cmd": [sys.executable, "-m", "pip", "install", "--timeout", "60"],
                    "timeout": 120,
                    "name": "standard"
                },
                # Strategy 2: Use different index if first fails
                {
                    "cmd": [sys.executable, "-m", "pip", "install", "--timeout", "30", "--index-url", "https://pypi.org/simple/"],
                    "timeout": 60,
                    "name": "alternative_index"
                },
                # Strategy 3: No cache, shorter timeout
                {
                    "cmd": [sys.executable, "-m", "pip", "install", "--no-cache-dir", "--timeout", "30"],
                    "timeout": 60,
                    "name": "no_cache"
                }
            ]
            
            last_error = None
            
            for i, strategy in enumerate(strategies):
                try:
                    cmd = strategy["cmd"].copy()
                    if force:
                        cmd.append("--force-reinstall")
                    cmd.append(package)
                    
                    print(f"Trying installation strategy {i+1}/{len(strategies)}: {strategy['name']}")
                    
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=strategy["timeout"]
                    )
                    
                    if result.returncode == 0:
                        # Verify installation worked
                        if self._is_package_available(import_name):
                            return {
                                "package": package,
                                "success": True,
                                "message": f"Successfully installed using {strategy['name']} strategy",
                                "status": "installed",
                                "strategy": strategy['name']
                            }
                        else:
                            last_error = f"Installation succeeded but import failed for {import_name}"
                            continue
                    else:
                        last_error = result.stderr or result.stdout
                        continue
                        
                except subprocess.TimeoutExpired:
                    last_error = f"Installation timeout ({strategy['timeout']}s) with {strategy['name']} strategy"
                    continue
                except Exception as e:
                    last_error = f"Strategy {strategy['name']} failed: {str(e)}"
                    continue
            
            # All strategies failed
            return {
                "package": package,
                "success": False,
                "error": f"All installation strategies failed. Last error: {last_error}",
                "status": "failed"
            }
                
        except Exception as e:
            return {
                "package": package,
                "success": False,
                "error": str(e),
                "status": "error"
            }
    
    def _is_package_available(self, import_name: str) -> bool:
        """Check if a package can be imported"""
        try:
            importlib.import_module(import_name)
            return True
        except ImportError:
            return False
    
    def get_common_ctf_packages(self) -> List[str]:
        """Get list of commonly needed CTF packages"""
        return [
            'pycryptodome',  # RSA, AES, etc.
            'requests',      # HTTP requests
            'sympy',         # Symbolic math
            'gmpy2',         # Fast math operations
            'numpy',         # Numerical operations
            'z3-solver',     # SMT solver
            'pillow',        # Image processing
            'qrcode',        # QR code generation/reading
            'opencv-python', # Computer vision (includes QR code reading)
            'pyzbar',        # QR code and barcode reading (needs system zbar)
        ]

# Tool registration for CTF Agent
def create_package_installer_tool():
    """Create package installer tool for CTF agent"""
    installer = PackageInstaller()
    
    def package_installer_func(packages=None, auto_install_common=False, force_reinstall=False):
        """
        Install Python packages for CTF challenges.
        
        Args:
            packages: Package name(s) to install (string or list)
            auto_install_common: Install common CTF packages automatically
            force_reinstall: Force reinstall even if already installed
            
        Returns:
            Installation results and status
        """
        params = {
            "packages": packages or [],
            "auto_install_common": auto_install_common,
            "force_reinstall": force_reinstall
        }
        return installer.execute(params)
    
    return package_installer_func
