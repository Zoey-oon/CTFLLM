#!/usr/bin/env python3
"""
CTF Challenge Prompt Generator - Legacy Wrapper
This module now wraps the new PromptRegistry system for backward compatibility
"""

from typing import Dict
from enum import Enum
from ..prompts import PromptRegistry


class ChallengeType(Enum):
    """Challenge types - kept for backward compatibility"""
    CRYPTOGRAPHY = "Cryptography"
    WEB = "Web Exploitation"
    REVERSE = "Reverse Engineering"
    FORENSICS = "Forensics"
    GENERAL = "General Skills"
    BINARY = "Binary Exploitation"


class CTFPromptManager:
    """Legacy prompt manager - now wraps PromptRegistry"""
    
    def __init__(self):
        self.registry = PromptRegistry()
    
    def get_prompt(self, challenge_type: str, challenge_data: Dict) -> str:
        """Get corresponding prompt based on challenge type"""
        return self.registry.get_challenge_prompt(challenge_type, challenge_data)