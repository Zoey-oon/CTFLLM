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
        self.description = "Connect to remote services (nc, telnet, socket, http) for CTF challenges"
    
    def _scan_ports(self, host: str, start_port: int = 1, end_port: int = 65535, timeout: int = 1) -> Dict[str, Any]:
        """Scan a range of ports to find open services"""
        try:
            print(f"Scanning ports {start_port}-{end_port} on {host}...")
            open_ports = []
            
            # Limit scan range to prevent excessive scanning
            if end_port - start_port > 10000:
                print("Warning: Large port range detected. Limiting to first 10000 ports for safety.")
                end_port = min(start_port + 10000, 65535)
            
            for port in range(start_port, end_port + 1):
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(timeout)
                    result = sock.connect_ex((host, port))
                    if result == 0:
                        print(f"Port {port} is open")
                        open_ports.append(port)
                    sock.close()
                except:
                    pass
                
                # Progress indicator for large ranges
                if (end_port - start_port) > 1000 and port % 1000 == 0:
                    print(f"Scanned up to port {port}")
            
            return {
                "success": True,
                "open_ports": open_ports,
                "method": "port_scan",
                "debug": f"Found {len(open_ports)} open ports in range {start_port}-{end_port}",
                "scan_range": f"{start_port}-{end_port}"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _test_connection(self, host: str, port: int, timeout: int = 5) -> Dict[str, Any]:
        """Test if the host:port is reachable before attempting full connection"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result == 0:
                return {"success": True}
            else:
                return {"success": False, "error": f"Port {port} is not reachable"}
                
        except socket.gaierror as e:
            return {"success": False, "error": f"DNS resolution failed: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": f"Connection test failed: {str(e)}"}
    
    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Connect to remote service and interact with it.
        
        Args:
            params: {
                "host": "hostname or IP",
                "port": port number,
                "method": "nc" or "telnet" or "socket" or "scan",
                "send": "data to send (optional)",
                "timeout": timeout in seconds (default: 30)
            }
        """
        try:
            host = params.get("host")
            port = params.get("port")
            method = params.get("method", "nc")
            send_data = params.get("send", "")
            timeout = params.get("timeout", 60)  # Increased default timeout for CTF services
            
            if not host:
                return {"success": False, "error": "Host is required"}
            
            if method == "scan":
                start_port = params.get("start_port", 1)
                end_port = params.get("end_port", 65535)
                return self._scan_ports(host, start_port, end_port, timeout)
            
            if not port:
                return {"success": False, "error": "Port is required for connection methods"}
            
            # Validate port number
            try:
                port = int(port)
                if port < 1 or port > 65535:
                    return {"success": False, "error": "Port must be between 1 and 65535"}
            except (ValueError, TypeError):
                return {"success": False, "error": "Port must be a valid number"}
            
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
                return {"success": False, "error": f"Unsupported method: {method}. Supported: nc, telnet, socket, scan, http, GET, POST"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _connect_nc(self, host: str, port: int, send_data: str, timeout: int) -> Dict[str, Any]:
        """Connect using netcat with enhanced error handling and retry mechanism"""
        max_retries = 2  # Reduced from 3 to 2
        retry_delay = 2  # Increased from 1 to 2 seconds
        
        for attempt in range(max_retries):
            try:
                # Try different netcat variants
                nc_commands = ['nc', 'netcat', 'ncat']
                nc_cmd = None
                
                for cmd in nc_commands:
                    if shutil.which(cmd):
                        nc_cmd = cmd
                        break
                
                if not nc_cmd:
                    # Fallback to socket method when netcat is not available
                    print("Warning: No netcat variant found. Falling back to socket method.")
                    return self._connect_socket(host, port, send_data, timeout)
                
                # Build command with appropriate flags based on OS and netcat variant
                cmd = [nc_cmd]
                
                # Linux (Kali) netcat configuration
                # Use GNU netcat flags for Linux
                if nc_cmd in ['nc', 'netcat']:
                    cmd.extend(['-w', str(timeout)])  # GNU netcat uses -w for timeout
                elif nc_cmd == 'ncat':  # Nmap ncat
                    cmd.extend(['-w', f"{timeout}s"])
                
                cmd.extend([host, str(port)])
                
                # Test connection first
                test_result = self._test_connection(host, port, timeout=min(5, timeout))
                if not test_result["success"]:
                    if attempt < max_retries - 1:
                        print(f"Connection test failed (attempt {attempt + 1}/{max_retries}). Retrying in {retry_delay}s...")
                        time.sleep(retry_delay)
                        continue
                    else:
                        return {
                            "success": False,
                            "error": f"Cannot reach {host}:{port}. {test_result.get('error', 'Connection failed')}",
                            "method": f"nc ({nc_cmd})",
                            "attempts": max_retries
                        }
                
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
                    # For CTF services, ensure proper line termination
                    if send_data:
                        if not send_data.endswith('\n'):
                            send_data += '\n'
                    else:
                        # If no data specified, send newline to trigger response
                        send_data = '\n'
                    
                    # Use reasonable timeout for CTF services
                    data_timeout = timeout  # Use the actual timeout value
                    stdout, stderr = process.communicate(input=send_data, timeout=data_timeout)
                    
                    # Check if we got meaningful output
                    if not stdout and not stderr and send_data:
                        if attempt < max_retries - 1:
                            print(f"Empty response (attempt {attempt + 1}/{max_retries}). Retrying...")
                            time.sleep(retry_delay)
                            continue
                    
                    return {
                        "success": True,
                        "output": stdout,
                        "error": stderr if stderr else None,
                        "method": f"nc ({nc_cmd})",
                        "command": ' '.join(cmd),
                        "debug": f"Sent: '{send_data}', Received: '{stdout}' (length: {len(stdout)})",
                        "attempts": attempt + 1
                    }
                    
                except subprocess.TimeoutExpired:
                    process.kill()
                    # Try to get partial output
                    try:
                        stdout, stderr = process.communicate(timeout=1)
                        if attempt < max_retries - 1:
                            print(f"Timeout (attempt {attempt + 1}/{max_retries}). Retrying...")
                            time.sleep(retry_delay)
                            continue
                        return {
                            "success": False,
                            "error": f"Connection timeout after {data_timeout}s",
                            "partial_output": stdout,
                            "method": f"nc ({nc_cmd})",
                            "attempts": max_retries
                        }
                    except:
                        if attempt < max_retries - 1:
                            continue
                        return {
                            "success": False, 
                            "error": f"Connection timeout after {data_timeout}s",
                            "attempts": max_retries
                        }
                
            except FileNotFoundError:
                # Fallback to socket method when netcat is not available
                print("Warning: netcat not found. Falling back to socket method.")
                return self._connect_socket(host, port, send_data, timeout)
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"Error (attempt {attempt + 1}/{max_retries}): {str(e)}. Retrying...")
                    time.sleep(retry_delay)
                    continue
                return {
                    "success": False, 
                    "error": f"Failed after {max_retries} attempts: {str(e)}",
                    "attempts": max_retries
                }
        
        return {
            "success": False, 
            "error": f"All {max_retries} connection attempts failed",
            "attempts": max_retries
        }
    
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
                "method": "telnet",
                "debug": f"Sent: '{send_data}', Received: '{response}' (length: {len(response)})"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _connect_socket(self, host: str, port: int, send_data: str, timeout: int) -> Dict[str, Any]:
        """Connect using raw socket with enhanced error handling and retry logic"""
        max_retries = 2
        
        for attempt in range(max_retries):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                
                # Connect with retry logic
                try:
                    sock.connect((host, port))
                except socket.timeout:
                    sock.close()
                    if attempt < max_retries - 1:
                        print(f"Socket connection timeout (attempt {attempt + 1}/{max_retries}). Retrying...")
                        time.sleep(1)
                        continue
                    return {"success": False, "error": f"Connection timeout to {host}:{port}"}
                except socket.error as e:
                    sock.close()
                    if attempt < max_retries - 1:
                        print(f"Socket error (attempt {attempt + 1}/{max_retries}): {str(e)}. Retrying...")
                        time.sleep(1)
                        continue
                    return {"success": False, "error": f"Failed to connect to {host}:{port}: {str(e)}"}
                
                all_response = ""
                
                # CTF services often need a trigger to send initial data
                if not send_data or send_data.strip() == "":
                    # Send newline to trigger service response
                    try:
                        sock.send(b'\n')
                        time.sleep(1)  # Give service time to respond
                        
                        sock.settimeout(8)  # Reasonable timeout for CTF services
                        response = sock.recv(8192).decode('utf-8', errors='ignore')
                        all_response = response
                        
                    except socket.timeout:
                        # Some services might not have an initial response
                        pass
                    except Exception as e:
                        # Try to continue anyway - connection might still be useful
                        print(f"Note: Initial response error: {str(e)}")
                        pass
                else:
                    # We have specific data to send
                    try:
                        # Try to read any initial banner first
                        sock.settimeout(3)
                        try:
                            initial = sock.recv(8192).decode('utf-8', errors='ignore')
                            all_response += initial
                        except socket.timeout:
                            pass  # No initial banner is fine
                        
                        # Send our data
                        sock.settimeout(timeout)
                        data_to_send = send_data.encode('utf-8')
                        if not data_to_send.endswith(b'\n'):
                            data_to_send += b'\n'
                        
                        sock.send(data_to_send)
                        time.sleep(0.8)  # Give service time to process
                        
                        # Read response
                        response_data = sock.recv(8192).decode('utf-8', errors='ignore')
                        all_response += response_data
                        
                    except Exception as e:
                        sock.close()
                        if attempt < max_retries - 1:
                            print(f"Send/receive error (attempt {attempt + 1}/{max_retries}): {str(e)}. Retrying...")
                            continue
                        return {"success": False, "error": f"Failed to send/receive data: {str(e)}"}
                
                sock.close()
                
                return {
                    "success": True,
                    "output": all_response,
                    "method": "socket",
                    "debug": f"Sent: '{send_data}', Total response length: {len(all_response)}",
                    "attempts": attempt + 1
                }
                
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"Socket error (attempt {attempt + 1}/{max_retries}): {str(e)}. Retrying...")
                    time.sleep(1)
                    continue
                return {
                    "success": False, 
                    "error": f"Socket connection failed after {max_retries} attempts: {str(e)}",
                    "attempts": max_retries
                }
        
        return {
            "success": False, 
            "error": f"All {max_retries} socket connection attempts failed",
            "attempts": max_retries
        }
    
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
    
    def network_connector_func(host: str, port: int = None, method: str = "socket", send: str = "", timeout: int = 60, start_port: int = None, end_port: int = None):
        """
        Connect to remote service for CTF challenges.
        
        Args:
            host: Target hostname or IP address
            port: Target port number (optional for scan method)
            method: Connection method ('nc', 'telnet', 'socket', 'scan', 'http', 'GET', 'POST')
            send: Data to send to the service (optional)
            timeout: Connection timeout in seconds
            start_port: Start port for scanning (optional)
            end_port: End port for scanning (optional)
            
        Returns:
            Service response and connection info
        """
        params = {
            "host": host,
            "method": method,
            "send": send,
            "timeout": timeout
        }
        
        # Add port parameters based on method
        if method == "scan":
            if start_port is not None:
                params["start_port"] = start_port
            if end_port is not None:
                params["end_port"] = end_port
        elif port is not None:
            params["port"] = port
        elif method != "scan":
            return {"success": False, "error": "Port is required for connection methods"}
        
        return connector.execute(params)
    
    return network_connector_func
