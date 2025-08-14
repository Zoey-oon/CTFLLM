"""
Network connection tool for CTF challenges requiring oracle interaction.
"""
import socket
import telnetlib
import subprocess
import time
import shutil
import requests
import urllib3
from typing import Dict, Any, Optional

# Disable SSL warnings for CTF challenges
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class NetworkConnector:
    def __init__(self):
        self.name = "network_connector"
        self.description = "Connect to remote services (nc, telnet) for CTF oracle challenges"
    
    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Connect to remote service and interact with it.
        
        Args:
            params: {
                "host": "hostname or IP",
                "port": port number,
                "method": "nc" or "telnet" or "socket",
                "send": "data to send (optional)",
                "timeout": timeout in seconds (default: 30)
            }
        """
        try:
            host = params.get("host")
            port = params.get("port")
            method = params.get("method", "nc")
            send_data = params.get("send", "")
            timeout = params.get("timeout", 30)
            
            if not host or not port:
                return {"success": False, "error": "Host and port are required"}
            
            if method == "nc":
                return self._connect_nc(host, port, send_data, timeout)
            elif method == "telnet":
                return self._connect_telnet(host, port, send_data, timeout)
            elif method == "socket":
                return self._connect_socket(host, port, send_data, timeout)
            elif method.upper() in ["GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS"]:
                return self._connect_http(host, port, method.upper(), send_data, timeout)
            elif method == "http":
                return self._connect_http(host, port, "GET", send_data, timeout)
            else:
                return {"success": False, "error": f"Unsupported method: {method}. Supported: nc, telnet, socket, http, GET, POST"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _connect_nc(self, host: str, port: int, send_data: str, timeout: int) -> Dict[str, Any]:
        """Connect using netcat with improved handling"""
        try:
            # Try different netcat variants
            nc_commands = ['nc', 'netcat', 'ncat']
            nc_cmd = None
            
            for cmd in nc_commands:
                if shutil.which(cmd):
                    nc_cmd = cmd
                    break
            
            if not nc_cmd:
                return {"success": False, "error": "No netcat variant found. Please install netcat."}
            
            # Build command with appropriate flags
            cmd = [nc_cmd]
            
            # Add timeout if supported
            if nc_cmd in ['nc', 'netcat']:
                cmd.extend(['-w', str(timeout)])
            
            cmd.extend([host, str(port)])
            
            # Start process
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Send data and get response
            try:
                if send_data:
                    # Add newline if not present
                    if not send_data.endswith('\n'):
                        send_data += '\n'
                
                stdout, stderr = process.communicate(input=send_data, timeout=timeout)
                
                return {
                    "success": True,
                    "output": stdout,
                    "error": stderr if stderr else None,
                    "method": f"nc ({nc_cmd})",
                    "command": ' '.join(cmd),
                    "debug": f"Sent: '{send_data}', Received: '{stdout}' (length: {len(stdout)})"
                }
                
            except subprocess.TimeoutExpired:
                process.kill()
                # Try to get partial output
                try:
                    stdout, stderr = process.communicate(timeout=1)
                    return {
                        "success": False,
                        "error": "Connection timeout",
                        "partial_output": stdout,
                        "method": f"nc ({nc_cmd})"
                    }
                except:
                    return {"success": False, "error": "Connection timeout"}
            
        except FileNotFoundError:
            return {"success": False, "error": "netcat not found. Please install it."}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _connect_telnet(self, host: str, port: int, send_data: str, timeout: int) -> Dict[str, Any]:
        """Connect using telnet"""
        try:
            tn = telnetlib.Telnet(host, port, timeout)
            
            if send_data:
                tn.write(send_data.encode('utf-8') + b'\n')
            
            # Read response
            response = tn.read_all().decode('utf-8', errors='ignore')
            tn.close()
            
            return {
                "success": True,
                "output": response,
                "method": "telnet"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _connect_socket(self, host: str, port: int, send_data: str, timeout: int) -> Dict[str, Any]:
        """Connect using raw socket with improved response handling"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((host, port))
            
            all_response = ""
            
            # Read initial response (banner/prompt)
            try:
                initial = sock.recv(4096).decode('utf-8', errors='ignore')
                all_response += initial
            except socket.timeout:
                pass  # No initial response
            
            if send_data:
                # Send data
                sock.send(send_data.encode('utf-8'))
                if not send_data.endswith('\n'):
                    sock.send(b'\n')
                
                # Wait a bit for response
                time.sleep(0.5)
                
                # Read response with multiple attempts
                for attempt in range(3):
                    try:
                        response = sock.recv(4096).decode('utf-8', errors='ignore')
                        if response:
                            all_response += response
                            # If we got more data, try to read more
                            if len(response) == 4096:
                                continue
                            break
                    except socket.timeout:
                        if attempt == 2:  # Last attempt
                            break
                        time.sleep(0.2)  # Brief pause before retry
            
            sock.close()
            
            return {
                "success": True,
                "output": all_response,
                "method": "socket",
                "debug": f"Sent: '{send_data}', Total response length: {len(all_response)}"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _connect_http(self, host: str, port: int, method: str, data: str, timeout: int) -> Dict[str, Any]:
        """Connect using HTTP/HTTPS"""
        try:
            # Determine protocol
            protocol = "https" if port == 443 else "http"
            if port in [80, 443]:
                url = f"{protocol}://{host}"
            else:
                url = f"{protocol}://{host}:{port}"
            
            # Add path if data looks like a path
            if data and data.startswith('/'):
                url += data
                data = ""
            elif data and not data.startswith('{') and '=' not in data:
                # Assume it's a path if it doesn't look like JSON or form data
                url += '/' + data.lstrip('/')
                data = ""
            
            # Prepare request
            headers = {'User-Agent': 'CTF-Agent/1.0'}
            
            # Handle different data formats
            json_data = None
            form_data = None
            
            if data:
                if data.startswith('{') and data.endswith('}'):
                    # JSON data
                    import json
                    try:
                        json_data = json.loads(data)
                        headers['Content-Type'] = 'application/json'
                    except:
                        form_data = {'data': data}
                elif '=' in data:
                    # Form data
                    form_data = {}
                    for pair in data.split('&'):
                        if '=' in pair:
                            key, value = pair.split('=', 1)
                            form_data[key] = value
                else:
                    # Raw data
                    form_data = {'data': data}
            
            # Make request
            response = requests.request(
                method=method,
                url=url,
                json=json_data,
                data=form_data,
                headers=headers,
                timeout=timeout,
                verify=False  # For CTF challenges, often self-signed certs
            )
            
            return {
                "success": True,
                "output": response.text,
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "method": f"HTTP {method}",
                "url": url
            }
            
        except requests.RequestException as e:
            return {"success": False, "error": f"HTTP request failed: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

# Tool registration for CTF Agent
def create_network_connector_tool():
    """Create network connector tool for CTF agent"""
    connector = NetworkConnector()
    
    def network_connector_func(host: str, port: int, method: str = "nc", send: str = "", timeout: int = 30):
        """
        Connect to remote service for CTF oracle challenges.
        
        Args:
            host: Target hostname or IP address
            port: Target port number  
            method: Connection method ('nc', 'telnet', 'socket')
            send: Data to send to the service (optional)
            timeout: Connection timeout in seconds
            
        Returns:
            Service response and connection info
        """
        params = {
            "host": host,
            "port": port,
            "method": method,
            "send": send,
            "timeout": timeout
        }
        return connector.execute(params)
    
    return network_connector_func
