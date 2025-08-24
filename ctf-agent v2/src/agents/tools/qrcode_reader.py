"""
QR Code reader tool for CTF challenges.
"""
import os
import tempfile
from typing import Dict, Any, Optional
from PIL import Image
import qrcode
import cv2
import numpy as np

class QRCodeReader:
    """QR Code reading tool for CTF challenges"""
    
    def __init__(self):
        self.name = "qrcode_reader"
        self.description = "Read QR codes from images and extract text content"
        
        # Initialize dependencies
        self.available_methods = self._initialize_dependencies()
        
        if not self.available_methods:
            print("❌ No QR code reading methods available!")
        else:
            print(f"✅ Available QR reading methods: {', '.join(self.available_methods)}")
    
    def _initialize_dependencies(self) -> list:
        """Initialize and ensure all dependencies are available"""
        available_methods = []
        
        # Try to install missing dependencies first
        self._ensure_dependencies()
        
        # Check pyzbar availability
        try:
            import pyzbar.pyzbar
            available_methods.append("pyzbar")
        except ImportError:
            print("⚠️  pyzbar not available - pyzbar method will be skipped")
        
        # Check OpenCV availability
        try:
            import cv2
            available_methods.append("opencv")
        except ImportError:
            print("⚠️  OpenCV not available - opencv method will be skipped")
        
        # Check PIL availability
        try:
            from PIL import Image
            available_methods.append("pil")
        except ImportError:
            print("⚠️  PIL not available - pil method will be skipped")
        
        return available_methods
    
    def _ensure_dependencies(self):
        """Ensure all required dependencies are installed"""
        try:
            from .package_installer import PackageInstaller
            pkg_installer = PackageInstaller()
            
            # Install common QR code reading dependencies
            dependencies = ['pillow', 'opencv-python', 'qrcode']
            
            print("🔧 Ensuring QR code reading dependencies...")
            for dep in dependencies:
                try:
                    result = pkg_installer.execute({'packages': [dep]})
                    if result.get('success') and result.get('installed') > 0:
                        print(f"✅ {dep}: {result.get('message', 'Installed')}")
                    else:
                        print(f"⚠️  {dep}: {result.get('message', 'Installation failed')}")
                except Exception as e:
                    print(f"⚠️  {dep}: Installation error - {e}")
            
            # Try to install pyzbar (may fail due to system dependencies)
            try:
                result = pkg_installer.execute({'packages': ['pyzbar']})
                if result.get('success') and result.get('installed') > 0:
                    print("✅ pyzbar: Installed successfully")
                else:
                    print("⚠️  pyzbar: Installation failed (may need system zbar library)")
            except Exception as e:
                print(f"⚠️  pyzbar: Installation error - {e}")
                
        except Exception as e:
            print(f"⚠️  Dependency management failed: {e}")
            print("💡 Some QR reading methods may not be available")
    
    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Read QR code from image file.
        
        Args:
            params: {
                "image_path": "Path to image file",
                "method": "qr" | "barcode" | "auto" (default: "auto")
            }
        """
        try:
            image_path = params.get("image_path")
            method = params.get("method", "auto")
            
            if not image_path:
                return {"success": False, "error": "image_path parameter is required"}
            
            # Resolve image path using the same logic as FileReader
            resolved_path = self._resolve_image_path(image_path)
            if not resolved_path:
                return {"success": False, "error": f"Image file not found: {image_path}"}
            
            # Try different QR code reading methods
            result = None
            tried_methods = []
            
            # For auto mode, try methods in order of reliability
            if method == "auto":
                # Try available methods in order of preference
                if "opencv" in self.available_methods:
                    result = self._read_with_opencv(resolved_path)
                    tried_methods.append("opencv")
                
                if not result and "pil" in self.available_methods:
                    result = self._read_with_pil(resolved_path)
                    tried_methods.append("pil")
                
                if not result and "pyzbar" in self.available_methods:
                    result = self._read_with_pyzbar(resolved_path)
                    tried_methods.append("pyzbar")
            
            elif method == "opencv":
                if "opencv" in self.available_methods:
                    result = self._read_with_opencv(resolved_path)
                    tried_methods.append("opencv")
                else:
                    return {"success": False, "error": "OpenCV method not available"}
            
            elif method == "pil":
                if "pil" in self.available_methods:
                    result = self._read_with_pil(resolved_path)
                    tried_methods.append("pil")
                else:
                    return {"success": False, "error": "PIL method not available"}
                
            elif method == "pyzbar":
                if "pyzbar" in self.available_methods:
                    result = self._read_with_pyzbar(resolved_path)
                    tried_methods.append("pyzbar")
                else:
                    return {"success": False, "error": "pyzbar method not available"}
            
            if result:
                return {
                    "success": True,
                    "content": result,
                    "method": method,
                    "image_path": resolved_path,
                    "tried_methods": tried_methods
                }
            else:
                return {
                    "success": False,
                    "error": "No QR code found in image",
                    "image_path": image_path,
                    "tried_methods": tried_methods,
                    "note": "Try different methods or check if image contains a valid QR code"
                }
                
        except Exception as e:
            return {"success": False, "error": f"QR code reading error: {str(e)}"}
    
    def _read_with_pyzbar(self, image_path: str) -> Optional[str]:
        """Read QR code using pyzbar library"""
        try:
            import pyzbar.pyzbar as pyzbar
            image = Image.open(image_path)
            decoded_objects = pyzbar.decode(image)
            
            if decoded_objects:
                # Return the first decoded QR code content
                return decoded_objects[0].data.decode('utf-8')
            return None
        except ImportError:
            # This should not happen since we check availability in __init__
            print("⚠️  pyzbar import failed - method not available")
            return None
        except Exception as e:
            print(f"Pyzbar method failed: {e}")
            return None
    
    def _read_with_opencv(self, image_path: str) -> Optional[str]:
        """Read QR code using OpenCV"""
        try:
            # Read image
            image = cv2.imread(image_path)
            if image is None:
                return None
            
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Try to detect QR code
            qr_detector = cv2.QRCodeDetector()
            data, bbox, straight_qrcode = qr_detector.detectAndDecode(gray)
            
            if data:
                return data
            return None
        except Exception as e:
            print(f"OpenCV method failed: {e}")
            return None
    
    def _read_with_pil(self, image_path: str) -> Optional[str]:
        """Read QR code using PIL (basic attempt)"""
        try:
            # This is a fallback method - PIL doesn't have built-in QR reading
            # but we can try to process the image
            image = Image.open(image_path)
            
            # Convert to RGB if needed
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Try to find QR code patterns (basic approach)
            # This is not very reliable but worth trying
            return None
        except Exception as e:
            print(f"PIL method failed: {e}")
            return None
    
    def _resolve_image_path(self, image_path: str) -> Optional[str]:
        """Resolve image path with priority for current challenge directory"""
        # If absolute path or path exists directly, use it
        if os.path.isabs(image_path) or os.path.exists(image_path):
            return image_path if os.path.exists(image_path) else None
        
        # Get basename for searching
        base = os.path.basename(image_path)
        
        # First, try to find the file in the current challenge directory
        current_challenge_dir = self._get_current_challenge_dir()
        if current_challenge_dir:
            # 优先在题目目录中查找
            challenge_paths = [
                os.path.join(current_challenge_dir, base),  # 直接文件名
                os.path.join(current_challenge_dir, "extracted", base),  # extracted子目录
            ]
            
            # 检查题目目录下的所有子目录
            for root, _, files in os.walk(current_challenge_dir):
                if base in files:
                    found_path = os.path.join(root, base)
                    print(f"🔍 在题目目录中找到图片: {found_path}")
                    return found_path
            
            # 如果没找到，检查是否是相对路径
            if "/" in image_path or "\\" in image_path:
                relative_path = os.path.join(current_challenge_dir, image_path)
                if os.path.exists(relative_path):
                    print(f"🔍 找到相对路径图片: {relative_path}")
                    return relative_path
        
        # 只有在题目目录中找不到时，才搜索全局challenges目录
        # 但这里要特别小心，避免文件混淆
        if current_challenge_dir:
            print(f"⚠️  在题目目录 {current_challenge_dir} 中未找到图片: {base}")
            print("🔍 开始全局搜索（可能找到其他题目的同名文件）")
        
        # 全局搜索（谨慎使用）
        matching_files = []
        for root, _, files in os.walk('challenges'):
            if base in files:
                file_path = os.path.join(root, base)
                # 检查是否在同一个题目目录中
                if current_challenge_dir and current_challenge_dir in file_path:
                    # 优先选择当前题目目录中的文件
                    matching_files.insert(0, file_path)
                else:
                    matching_files.append(file_path)
        
        if len(matching_files) > 1:
            # 多个文件 found - 优先选择当前题目目录中的
            current_challenge_files = [f for f in matching_files if current_challenge_dir and current_challenge_dir in f]
            if current_challenge_files:
                print(f"✅ 选择当前题目目录中的图片: {current_challenge_files[0]}")
                return current_challenge_files[0]
            else:
                print(f"⚠️  警告：找到多个同名图片，但都不在当前题目目录中:")
                for f in matching_files:
                    print(f"   - {f}")
                print(f"   使用第一个: {matching_files[0]}")
                return matching_files[0]
        elif len(matching_files) == 1:
            return matching_files[0]
        
        return None
    
    def _get_current_challenge_dir(self) -> Optional[str]:
        """Get the current challenge directory based on working directory"""
        try:
            # Get current working directory
            cwd = os.getcwd()
            
            # Check if we're in a challenge directory
            if 'challenges' in cwd:
                # Find the challenge directory path
                parts = cwd.split(os.sep)
                challenges_index = parts.index('challenges')
                if challenges_index + 3 < len(parts):  # challenges/year/category/name
                    challenge_path = os.sep.join(parts[:challenges_index + 4])
                    if os.path.exists(challenge_path):
                        return challenge_path
            
            # Fallback: try to find from environment or context
            return None
        except Exception:
            return None

def create_qrcode_reader_tool():
    """Create QR code reader tool for CTF agent"""
    tool = QRCodeReader()
    
    def qrcode_reader_func(image_path: str, method: str = "auto"):
        """
        QR code reader function.
        
        Args:
            image_path: Path to image file
            method: Reading method ("auto", "opencv", "pil", "pyzbar")
            
        Returns:
            QR code content if found
        """
        params = {
            "image_path": image_path,
            "method": method
        }
        return tool.execute(params)
    
    return qrcode_reader_func
