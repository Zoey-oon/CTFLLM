#!/usr/bin/env python3
"""
CTF Practice - Challenge Management Module
Handles challenge reading, input, and file system management
"""

import json
import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

class CTFPractice:
    
    def __init__(self, challenges_dir: str = "challenges"):
        self.challenges_dir = Path(challenges_dir)
        self.current_challenge = None
    
    def welcome(self):
        print("=" * 90)
        print("Welcome to CTF challenge management system.")
        print("This module handles challenge reading, input, and organization.")
        print("=" * 90)
    
    def read_challenge(self) -> bool:
        # print("\n" + "=" * 60)
        print("Challenge Input Method:")
        # print("=" * 60)
        print("1. Manual Input")
        print("2. Load from Local Directory")
        
        while True:
            choice = input("Select method (1 or 2): ").strip()
            
            if choice == "1":
                return self._manual_input_challenge()
            elif choice == "2":
                return self._load_from_directory()
            else:
                print("Invalid choice. Please enter 1 or 2.")
    
    def _manual_input_challenge(self) -> bool:
        print("\nManual Challenge Input")
        print("-" * 90)
        
        title = input("Challenge Title: ").strip()
        if not title:
            print("Title is required")
            return False
        
        description = input("Challenge Description: ").strip()
        if not description:
            print("Description is required")
            return False
        
        print("\nAvailable Categories:")
        categories = [
            "Web Exploitation", "Cryptography", "Forensics", 
            "Reverse Engineering", "General Skills", "Binary Exploitation"
        ]
        
        for i, cat in enumerate(categories, 1):
            print(f"  {i}. {cat}")
        
        try:
            cat_choice = int(input(f"\nSelect category (1-{len(categories)}) [optional]: ").strip())
            if 1 <= cat_choice <= len(categories):
                category = categories[cat_choice - 1]
            else:
                print("Invalid choice, using General Skills")
                category = "General Skills"
        except:
            print("Invalid input, using General Skills")
            category = "General Skills"
        
        difficulty = input("Difficulty (Easy/Medium/Hard) [Unknown]: ").strip()
        if not difficulty:
            difficulty = "Unknown"
        
        points = input("Points (50/100/200/300/400/500) [optional]: ").strip()
        if not points:
            points = "Unknown"
        
        year = input("Year (2023/2024/2025) [2024]: ").strip()
        if not year:
            year = "2024"
        
        # 处理附件文件
        attachments = []
        print("\nAttachment Files:")
        print("Enter file paths (one per line, empty line to finish):")
        while True:
            file_path = input("File path: ").strip()
            if not file_path:
                break
            
            if os.path.exists(file_path):
                attachments.append(file_path) 
                print(f"Added: {file_path}")
            else:
                print(f"File not found: {file_path}")
        
        self.current_challenge = {
            "title": title,
            "points": points,
            "year": year,
            "category": category,
            "difficulty": difficulty,
            "description": description,
            "files": attachments,
            "solutions": []
        }
        
        print(f"\nChallenge loaded: {title}")
        print(f"Category: {category}")
        print(f"Difficulty: {difficulty}")
        print(f"Files: {len(attachments)} files")
        return True
    
    def _load_from_directory(self) -> bool:
        """从challenges目录加载题目"""
        print("\nLoading from challenges directory...")
        
        if not self.challenges_dir.exists():
            print(f"Challenges directory not found: {self.challenges_dir}")
            return False
        
        challenges = []
        for year_dir in self.challenges_dir.iterdir():
            if not year_dir.is_dir():
                continue
                
            year = year_dir.name
            for category_dir in year_dir.iterdir():
                if not category_dir.is_dir():
                    continue
                    
                category = category_dir.name
                for challenge_dir in category_dir.iterdir():
                    if not challenge_dir.is_dir():
                        continue
                    
                    challenge_files = list(challenge_dir.glob("*.json"))
                    if challenge_files:
                        # Prefer file named after directory (canonical metadata), otherwise exclude solution/conversation variants
                        challenge_json = None
                        dir_basename = challenge_dir.name.lower()
                        # 1) exact match preferred
                        for jf in challenge_files:
                            if jf.stem.lower() == dir_basename:
                                challenge_json = jf
                                break
                        # 2) fallback: first non-solution/non-conversation json
                        if challenge_json is None:
                            for jf in challenge_files:
                                name = jf.name.lower()
                                if any(x in name for x in ["solution", "conversation", "_auto", "_hitl"]):
                                    continue
                                challenge_json = jf
                                break
                        
                        if challenge_json:
                            try:
                                with open(challenge_json, 'r', encoding='utf-8') as f:
                                    metadata = json.load(f)
                                    # Robust defaults for missing fields
                                    metadata.setdefault('title', challenge_dir.name)
                                    metadata.setdefault('category', category)
                                    metadata.setdefault('difficulty', 'Unknown')
                                    metadata.setdefault('description', '')
                                    metadata.setdefault('points', 'Unknown')
                                    metadata.setdefault('year', year)
                                    # Ensure files is a list
                                    files = metadata.get('files', [])
                                    if not isinstance(files, list):
                                        files = []
                                    metadata['files'] = files
                                    metadata['path'] = str(challenge_dir)
                                    metadata['challenge_json_path'] = str(challenge_json)
                                    challenges.append(metadata)
                            except Exception as e:
                                print(f"Error reading {challenge_json}: {e}")
        
        if not challenges:
            print("No challenges found in directory")
            return False
        
        # 显示可用题目
        print(f"\nFound {len(challenges)} challenges:")
        for i, challenge in enumerate(challenges, 1):
            title = challenge.get('title', 'Unknown')
            category = challenge.get('category', 'Unknown')
            difficulty = challenge.get('difficulty', 'Unknown')
            print(f"  {i}. {title} ({category}) - {difficulty}")
        
        # 选择题目
        while True:
            try:
                choice = int(input(f"\nSelect challenge (1-{len(challenges)}): ").strip())
                if 1 <= choice <= len(challenges):
                    selected_challenge = challenges[choice - 1]
                    # Normalize file paths to absolute within challenge dir
                    base_dir = Path(selected_challenge.get('path', category_dir))
                    files = selected_challenge.get('files', [])
                    normalized_files: List[str] = []
                    for fp in files:
                        p = Path(fp)
                        if not p.is_absolute():
                            sp = str(p)
                            base_str = str(base_dir)
                            if not sp.startswith(base_str + os.sep):
                                p = base_dir / p
                        normalized_files.append(str(p))
                    selected_challenge['files'] = normalized_files

                    # If files list empty, try to auto-discover files in challenge dir
                    if not normalized_files:
                        guessed = []
                        for p in base_dir.iterdir():
                            if p.is_file() and p.suffix not in {'.json'}:
                                guessed.append(str(p))
                        selected_challenge['files'] = guessed

                    self.current_challenge = selected_challenge
                    
                    print(f"\nChallenge loaded: {selected_challenge.get('title', 'Unknown')}")
                    print(f"Category: {selected_challenge.get('category', 'Unknown')}")
                    print(f"Difficulty: {selected_challenge.get('difficulty', 'Unknown')}")
                    print(f"Description: {selected_challenge.get('description', '')}")
                    return True
                else:
                    print(f"Please enter a number between 1 and {len(challenges)}")
            except ValueError:
                print("Please enter a valid number")
    
    def save_challenge_to_filesystem(self) -> bool:
        """将当前题目保存到文件系统"""
        if not self.current_challenge:
            print("No challenge to save")
            return False
        
        try:
            # 创建目录结构
            year = self.current_challenge['year']
            category = self.current_challenge['category']
            title = self.current_challenge['title']
            
            # 清理标题用于目录名
            safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_title = safe_title.replace(' ', '_').lower()
            
            # 创建目录 - 直接使用题目名
            challenge_dir = self.challenges_dir / year / category / safe_title
            challenge_dir.mkdir(parents=True, exist_ok=True)
            
            # 复制附件文件到题目目录
            saved_files = []
            if self.current_challenge.get('files'):
                for file_path in self.current_challenge['files']:
                    if os.path.exists(file_path):
                        file_name = os.path.basename(file_path)
                        dest_path = challenge_dir / file_name
                        
                        # 检查源文件和目标文件是否相同
                        if os.path.abspath(file_path) == os.path.abspath(str(dest_path)):
                            print(f"File already in target location: {file_name}")
                            saved_files.append(str(dest_path))
                        else:
                            # 复制文件
                            shutil.copy2(file_path, dest_path)
                            saved_files.append(str(dest_path))
                            print(f"Copied file: {file_name}")
            
            # 更新metadata - 保持files为完整路径
            metadata = self.current_challenge.copy()
            metadata['files'] = saved_files
            
            # 如果原本就从目录加载，且已有 JSON，则不要覆盖原题目 JSON
            existing_json_path = self.current_challenge.get('challenge_json_path')
            if existing_json_path and Path(existing_json_path).exists():
                challenge_json = Path(existing_json_path)
            else:
                # 保存题目信息JSON - 使用题目名命名（仅手工输入时创建）
                challenge_json = challenge_dir / f"{safe_title}.json"
                with open(challenge_json, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2, ensure_ascii=False)

            print(f"\nChallenge saved successfully!")
            print(f"Location: {challenge_dir}")
            print(f"Challenge info: {challenge_json}")
            print(f"Files copied: {len(saved_files)}")
            return True
            
        except Exception as e:
            print(f"Failed to save challenge: {e}")
            return False
    
    def get_current_challenge(self) -> Optional[Dict]:
        """获取当前题目"""
        return self.current_challenge
    
    def show_challenge_info(self):
        """显示当前题目信息"""
        if not self.current_challenge:
            print("No challenge loaded")
            return
        
        print(f"\nCurrent Challenge Information:")
        print("-" * 90)
        print(f"Title: {self.current_challenge['title']}")
        print(f"Category: {self.current_challenge['category']}")
        print(f"Difficulty: {self.current_challenge['difficulty']}")
        print(f"Points: {self.current_challenge['points']}")
        print(f"Year: {self.current_challenge['year']}")
        print(f"Description: {self.current_challenge['description']}")
        print(f"Files: {len(self.current_challenge.get('files', []))} files")

def main():
    """测试函数"""
    practice = CTFPractice()
    practice.welcome()
    
    if practice.read_challenge():
        print("Challenge loaded successfully")
        if practice.save_challenge_to_filesystem():
            print("Challenge saved to filesystem")
        else:
            print("Failed to save challenge")
    else:
        print("Failed to load challenge")

if __name__ == "__main__":
    main() 