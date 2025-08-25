# CTF Agent Architecture

## Agent Tools vs CTF Tools

### Agent Built-in Tools (8 tools)
These are Python classes that the LLM agent can directly call:

```
Agent Tools:
├── cmd    # Gateway to external CTF tools  
├── net    # Direct TCP/UDP connections
├── code   # Execute Python code
├── read   # Read challenge files
├── js     # Execute JavaScript & decrypt JS encryption
├── flag   # Extract/validate flags  
├── pip    # Install Python packages
└── task   # Task progress management
```

### CTF External Tools (254 tools)
These are system commands accessed via `cmd` tool:

```
CTF Tools (via cmd):
├── Network (27): ssh, nmap, curl, wget, nc, hydra...
├── Binary (9): gdb, objdump, readelf, strace...  
├── Crypto (11): hashcat, john, openssl...
├── Forensics (12): volatility, testdisk, binwalk...
├── Steganography (11): steghide, zsteg, outguess...
├── Web Security (14): sqlmap, nikto, dirb, burpsuite...
└── ... (21 more categories)
```

## How It Works

```python
# LLM calls agent tool
cmd.execute({
    "command": "nmap",           # One of 254 CTF tools
    "args": ["-sV", "target"],   # Command arguments  
    "input": ""                  # Stdin input
})

# Agent tool calls system command
subprocess.run(["nmap", "-sV", "target"])
```

## Security Model

**Allowed**: 254 CTF tools + any safe commands
**Blocked**: 15 dangerous commands (rm, sudo, shutdown, etc.)

```python
# Simplified security logic
if command in dangerous_commands:
    return error("Command dangerous")
else:
    return subprocess.run(command)  # Allow execution
```

## Tool Discovery

Agent can use any CTF tool without pre-configuration:
- Known tools: Explicitly listed in 24 categories
- Unknown tools: Dynamically allowed if not dangerous
- Pattern matching: Tools ending in "-ng", "crack", etc.

## Example Usage

```python
# LLM decides to use nmap
result = cmd.execute({
    "command": "nmap", 
    "args": ["-sV", "192.168.1.1"]
})

# LLM decides to analyze binary  
result = cmd.execute({
    "command": "objdump",
    "args": ["-d", "binary_file"]
})

# LLM decides to crack password
result = cmd.execute({
    "command": "hashcat",
    "args": ["-m", "0", "hash.txt", "wordlist.txt"]
})
```

The 254 CTF tools extend the agent's capabilities without requiring individual tool implementations.
