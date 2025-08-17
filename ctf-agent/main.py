#!/usr/bin/env python3
"""
CTF Agent Main Entry Point
Simple and direct CTF challenge solving flow
"""

from typing import Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from src.agents.ctf_agent import CTFAgent

def test_api_key(llm_service: str, api_key: str) -> bool:
    """Test if API key is valid by making a simple request"""
    try:
        if llm_service == "deepseek":
            from langchain_deepseek import ChatDeepSeek
            llm = ChatDeepSeek(api_key=api_key, model="deepseek-chat", timeout=30)
        elif llm_service == "openai":
            from langchain_openai import ChatOpenAI
            llm = ChatOpenAI(api_key=api_key, model="gpt-3.5-turbo", timeout=30)
        elif llm_service == "anthropic":
            from langchain_anthropic import ChatAnthropic
            llm = ChatAnthropic(api_key=api_key, model="claude-3-haiku-20240307", timeout=30)
        else:
            return False
        
        # Make a simple test request
        from langchain.schema import HumanMessage
        response = llm.invoke([HumanMessage(content="Hello")])
        return bool(response and response.content)
        
    except Exception as e:
        print(f"API test error: {str(e)}")
        return False

def welcome():
    """Welcome interface"""
    print("=" * 90)
    print("                    CTF Agent - Challenge Solver")
    print("=" * 90)
    print("Welcome to CTF challenge solving system.")
    print("This agent helps you solve CTF challenges using LLM.")

def select_mode():
    """Select operation mode"""
    print("\nSelect Operation Mode:")
    print("1. Auto Mode (Fully automated)")
    print("2. HITL Mode (Human in the Loop)")
    
    while True:
        choice = input("Enter your choice (1 or 2): ").strip()
        if choice == "1":
            return "Auto"
        elif choice == "2":
            return "HITL"
        else:
            print("Invalid choice. Please enter 1 or 2.")

def handle_challenge_phase():
    """Handle challenge phase - call ctf_practice.py"""
    print("=" * 90)
    print("Phase 1: Challenge Management")
    print("-" * 90)
    
    try:
        from src.agents.ctf_practice import CTFPractice
        
        # Create CTF Practice instance
        practice = CTFPractice()
        
        # Read challenge
        if practice.read_challenge():
            print("Challenge loaded successfully")
            
            # Save to filesystem
            if practice.save_challenge_to_filesystem():
                print("Challenge saved to filesystem")
                return practice.get_current_challenge()
            else:
                print("Failed to save challenge")
                return None
        else:
            print("Failed to load challenge")
            return None
            
    except Exception as e:
        print(f"Error in challenge phase: {e}")
        return None

def handle_prompt_phase(challenge_data):
    """Handle prompt generation phase - call ctf_prompts.py"""
    print("=" * 90)
    print("Phase 2: Prompt Generation")
    print("-" * 90)
    
    try:
        from src.agents.ctf_prompts import CTFPromptManager
        
        # Create prompt manager
        prompt_manager = CTFPromptManager()
        
        # Generate prompt
        category = challenge_data.get('category', 'General Skills')
        prompt = prompt_manager.get_prompt(category, challenge_data)
        
        print(f"Generated LLM Prompt for {category} challenge:")
        # print("-" * 90)
        print(prompt)
        
        return prompt
        
    except Exception as e:
        print(f"Error in prompt phase: {e}")
        return None

def handle_llm_phase(prompt: str, mode: str, challenge_data: Dict):
    """Handle LLM interaction phase"""
    print("=" * 90)
    print("Phase 3: LLM Interaction")
    print("-" * 90)

    try:
        from src.agents.ctf_agent import CTFAgent
        
        # Get LLM configuration and Select LLM service
        print("LLM Configuration Setup. Available LLM Models:")
        print("1. DeepSeek")
        print("2. OpenAI GPT")
        print("3. Anthropic Claude")
        
        choice = input("Select LLM model (1-3): ").strip()
        llm_services = {1: "deepseek", 2: "openai", 3: "anthropic"}
        
        if choice not in ['1', '2', '3']:
            print("Invalid choice")
            return False
        
        llm_service = llm_services[int(choice)]
        
        # Get and validate API key
        api_key = None
        max_attempts = 3
        for attempt in range(max_attempts):
            api_key = input(f"Enter your {llm_service} API key: ").strip()
            
            if not api_key:
                print("API key is required")
                continue
            
            # Test API key
            print("🔍 Testing API key...")
            if test_api_key(llm_service, api_key):
                print(f"LLM configured successfully!")
                print(f"Service: {llm_service}")
                break
            else:
                print(f"API key test failed. Please check your {llm_service} API key.")
                if attempt < max_attempts - 1:
                    print(f"Attempt {attempt + 1}/{max_attempts}. Please try again.")
                else:
                    print("Maximum attempts reached. Exiting.")
                    return False
        
        if not api_key:
            return False
        
        # Create CTF Agent with mode
        run_mode = 'auto' if mode == 'Auto' else 'hitl'
        agent = CTFAgent(llm_service=llm_service, api_key=api_key, mode=run_mode)
        
        # Set enhanced task tree storage path based on challenge and mode
        year = challenge_data.get('year', 'unknown')
        category = challenge_data.get('category', 'unknown')
        title_slug = challenge_data.get('title', 'unknown').lower().replace(' ', '_')
        challenge_dir = f"challenges/{year}/{category}/{title_slug}"
        
        # Generate unique storage path for this run
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        task_tree_path = f"{challenge_dir}/task_tree_{run_mode}_{timestamp}.json"
        
        # Update task tree storage path
        if hasattr(agent, 'task_tree') and agent.task_tree:
            agent.task_tree.storage_path = task_tree_path
            # Reset task tree for new run
            agent.task_tree.tasks = []
            print(f"🔄 Task tree reset for new run: {task_tree_path}")
        
        # Legacy compatibility
        agent.task_tree_path = task_tree_path
        
        print(f"Mode: {mode}")
        
        if mode == "Auto":
            print("Starting automated solving with multi-round interaction...")
            return handle_auto_solving(agent, challenge_data, prompt)
        elif mode == "HITL":
            return handle_hitl_solving(agent, challenge_data, prompt)
        else:
            print("Invalid mode")
            return False
            
    except Exception as e:
        print(f"Error in LLM phase: {e}")
        return False

def handle_auto_solving(agent, challenge_data: Dict, prompt: str) -> bool:
    """Handle automated solving with multi-round interaction"""
    try:
        print("Starting automated challenge solving...")
        print("Agent will automatically determine next steps and tool usage.")
        print("You can only decide when to stop the process.")
        
        # Start solving
        response = agent.start_challenge(challenge_data)
        
        max_rounds = 30  # Prevent infinite loops
        
        while agent.current_round < max_rounds:
            
            # Check if we have tool results from previous round
            if hasattr(agent, 'last_tool_results') and agent.last_tool_results:

                
                # Ask user what to do with tool results
                print("\nWhat would you like to do?")
                print("1. Continue solving (give tool results to LLM)")
                print("2. Verify final answer")
                print("3. Stop solving")
                
                choice = input("Enter your choice (1-3): ").strip()
                
                if choice == "1":
                    # Continue solving with tool results
                    next_input = agent.get_continue_prompt(response, agent.last_tool_results)
                    response = agent.interact(next_input)
                elif choice == "2":
                    # Human verification path - use unified flag detection logic
                    import re, os, json
                    candidate = None
                    # Debug: Print last_flag_candidate value
                    print(f"DEBUG: agent.last_flag_candidate = {getattr(agent, 'last_flag_candidate', 'NOT_SET')}")
                    
                    # 1) First check if CTF Agent detected a flag
                    if hasattr(agent, 'last_flag_candidate') and agent.last_flag_candidate:
                        candidate = agent.last_flag_candidate
                        print(f"DEBUG: Found candidate from last_flag_candidate: {candidate}")
                    # 2) Prefer last tool results
                    elif hasattr(agent, 'last_tool_results') and agent.last_tool_results:
                        for res in reversed(agent.last_tool_results):
                            m = re.search(r"picoCTF\{[^}]+\}", res)
                            if m:
                                candidate = m.group(0)
                                break
                    # 3) Search conversation (AI and human)
                    if not candidate:
                        try:
                            rounds = getattr(agent, 'conversation_history', [])
                            for r in reversed(rounds):
                                for text in (r.ai_response, r.human_input):
                                    m = re.search(r"picoCTF\{[^}]+\}", text)
                                    if m:
                                        candidate = m.group(0)
                                        break
                                if candidate:
                                    break
                        except Exception:
                            candidate = None
                    
                    # 4) Ask user to input if still not found
                    if not candidate:
                        manual = input("No picoCTF{...} found. Enter flag manually (blank to cancel): ").strip()
                        if manual.startswith("picoCTF{") and manual.endswith("}"):
                            candidate = manual
                    
                    if candidate:
                        print(f"\nCandidate flag: {candidate}")
                        final_choice = input("Confirm this as final flag and save? (y/n): ").strip().lower()
                        if final_choice == 'y':
                            # Save into conversation JSON instead of separate file
                            year = challenge_data.get('year', 'unknown')
                            category = challenge_data.get('category', 'unknown')
                            title_slug = challenge_data.get('title', 'unknown').lower().replace(' ', '_')
                            save_path = f"challenges/{year}/{category}/{title_slug}/auto_solution_conversation.json"
                            summary = agent.get_conversation_summary()
                            summary['final_flag'] = candidate
                            summary['verified'] = True
                            # Attach task_tree snapshot if present
                            try:
                                if hasattr(agent, 'task_tree') and agent.task_tree:
                                    summary['task_tree'] = agent.task_tree.get_tree_display()
                            except Exception:
                                pass
                            with open(save_path, 'w', encoding='utf-8') as f:
                                json.dump(summary, f, indent=2, ensure_ascii=False)
                            print(f"Conversation (with final flag) saved to: {save_path}")
                            print(f"flag: {candidate}")
                            return True
                        else:
                            print("Flag rejected. Continue solving.")
                            # Fall back to continue
                            next_input = agent.get_continue_prompt(response, agent.last_tool_results)
                            response = agent.interact(next_input)
                    else:
                        print("No picoCTF{...} candidate found in history.")
                        # Fall back to continue
                        next_input = agent.get_continue_prompt(response, agent.last_tool_results)
                        response = agent.interact(next_input)
                elif choice == "3":
                    print("Solving stopped by user.")
                    break
                else:
                    print("Invalid choice. Please select 1, 2, or 3.")
                    continue
            else:
                # No tool results, continue normally
                summary = agent.get_conversation_summary()
                next_input = agent.determine_next_input(challenge_data, summary)
                response = agent.interact(next_input)      
            
            # Always ask user what to do next
            print("\nWhat would you like to do?")
            print("1. Continue solving (give tool results to LLM)")
            print("2. Verify final answer")
            print("3. Stop solving")
            
            choice = input("Enter your choice (1-3): ").strip()
            
            if choice == "1":
                # Continue with current approach
                if hasattr(agent, 'last_tool_results') and agent.last_tool_results:
                    next_input = agent.get_continue_prompt(response, agent.last_tool_results)
                else:
                    next_input = agent.determine_next_input(challenge_data, summary)
                response = agent.interact(next_input)
            elif choice == "2":
                # Human verification with multi-flag support
                import re, os, json
                
                # 🔍 收集所有可能的flag候选
                all_candidates = set()
                
                # 1) CTF Agent detected flag
                if hasattr(agent, 'last_flag_candidate') and agent.last_flag_candidate:
                    all_candidates.add(agent.last_flag_candidate)
                
                # 2) Search in last tool results
                if hasattr(agent, 'last_tool_results') and agent.last_tool_results:
                    for res in agent.last_tool_results:
                        matches = re.findall(r"picoCTF\{[^}]+\}", res)
                        all_candidates.update(matches)
                
                # 3) Search conversation history
                try:
                    rounds = getattr(agent, 'conversation_history', [])
                    for r in rounds:
                        for text in (r.ai_response, r.human_input):
                            matches = re.findall(r"picoCTF\{[^}]+\}", text)
                            all_candidates.update(matches)
                except Exception:
                    pass
                
                # 转换为列表并去重
                candidates_list = list(all_candidates)
                
                if candidates_list:
                    print(f"\n🚩 Found {len(candidates_list)} flag candidate(s):")
                    for i, flag in enumerate(candidates_list, 1):
                        print(f"  {i}. {flag}")
                    
                    if len(candidates_list) == 1:
                        # 单个候选，直接确认
                        candidate = candidates_list[0]
                        print(f"\nSingle candidate: {candidate}")
                        final_choice = input("Confirm this as final flag and save? (y/n): ").strip().lower()
                        selected_flag = candidate if final_choice == 'y' else None
                    else:
                        # 多个候选，让用户选择
                        print(f"\nMultiple candidates found. Please select one:")
                        print("0. None of the above (enter manually)")
                        
                        while True:
                            try:
                                choice_input = input(f"Select flag (1-{len(candidates_list)} or 0): ").strip()
                                choice_num = int(choice_input)
                                
                                if choice_num == 0:
                                    manual = input("Enter flag manually: ").strip()
                                    if manual.startswith("picoCTF{") and manual.endswith("}"):
                                        selected_flag = manual
                                        break
                                    else:
                                        print("Invalid flag format. Must be picoCTF{...}")
                                        continue
                                elif 1 <= choice_num <= len(candidates_list):
                                    selected_flag = candidates_list[choice_num - 1]
                                    print(f"Selected: {selected_flag}")
                                    confirm = input("Confirm this flag? (y/n): ").strip().lower()
                                    if confirm == 'y':
                                        break
                                    else:
                                        continue
                                else:
                                    print(f"Invalid choice. Please enter 1-{len(candidates_list)} or 0.")
                                    continue
                            except ValueError:
                                print("Please enter a valid number.")
                                continue
                else:
                    # 没有找到候选，手动输入
                    print("No picoCTF{...} candidates found.")
                    manual = input("Enter flag manually (blank to cancel): ").strip()
                    selected_flag = manual if manual.startswith("picoCTF{") and manual.endswith("}") else None
                
                # 保存选中的flag
                if selected_flag:
                    # Save into conversation JSON instead of separate file
                    year = challenge_data.get('year', 'unknown')
                    category = challenge_data.get('category', 'unknown')
                    title_slug = challenge_data.get('title', 'unknown').lower().replace(' ', '_')
                    save_path = f"challenges/{year}/{category}/{title_slug}/auto_solution_conversation.json"
                    summary = agent.get_conversation_summary()
                    summary['final_flag'] = selected_flag
                    summary['verified'] = True
                    summary['all_flag_candidates'] = candidates_list  # 记录所有候选
                    # Attach task_tree snapshot if available
                    try:
                        if hasattr(agent, 'task_tree') and agent.task_tree:
                            summary['task_tree'] = agent.task_tree.get_tree_display()
                    except Exception:
                        pass
                    with open(save_path, 'w', encoding='utf-8') as f:
                        json.dump(summary, f, indent=2, ensure_ascii=False)
                    print(f"Conversation (with final flag) saved to: {save_path}")
                    print(f"🎉 Final flag: {selected_flag}")
                    if len(candidates_list) > 1:
                        print(f"📝 Note: {len(candidates_list)} candidates were found, you selected: {selected_flag}")
                    return True
                else:
                    print("No flag selected. Continue solving.")
            elif choice == "3":
                print("Solving stopped by user.")
                break
            else:
                print("Invalid choice. Please select 1, 2, or 3.")
                continue
        
        # Save conversation
        save_path = f"challenges/{challenge_data.get('year', 'unknown')}/{challenge_data.get('category', 'unknown')}/{challenge_data.get('title', 'unknown').lower().replace(' ', '_')}/auto_solution_conversation.json"
        agent.save_conversation(save_path)
        print(f"Conversation saved to: {save_path}")
        
        return True
        
    except Exception as e:
        print(f"Auto solving failed: {e}")
        return False

def handle_hitl_solving(agent, challenge_data: Dict, prompt: str) -> bool:
    """Handle human-in-the-loop solving"""
    try:
        print("Starting human-in-the-loop solving...")
        print("Agent will solve automatically, but you can provide input when tools cannot be executed.")
        
        # Start solving
        response = agent.start_challenge(challenge_data)
        # 可选：显示AI响应（调试用）
        if hasattr(agent, 'debug_mode') and agent.debug_mode:
            print(f"\n[Round 1] AI Response: {response}")
        
        max_rounds = 15
        
        while agent.current_round < max_rounds:
            
            # Check if we have tool results from previous round
            if hasattr(agent, 'last_tool_results') and agent.last_tool_results:

                
                # Ask user what to do with tool results
                print("\nWhat would you like to do?")
                print("1. Continue (auto run tools if possible)")
                print("2. Enter custom prompt for LLM")
                print("3. Verify final answer")
                print("4. Stop solving")
                
                try:
                    choice = input("Enter your choice (1-4): ").strip()
                except EOFError:
                    print("\nInput interrupted. Defaulting to continue solving...")
                    choice = "1"
                
                if choice == "1":
                    # Continue solving with tool results; agent will auto-execute tools if LLM outputs <tool> blocks
                    next_input = agent.get_continue_prompt(response, agent.last_tool_results)
                    response = agent.interact(next_input)
                elif choice == "2":
                    # Custom prompt from human
                    human_input = input("\nEnter your custom prompt for LLM: ").strip()
                    if not human_input:
                        print("Empty prompt, skipping.")
                        continue
                    # Prepend our strict rules/context to the custom input
                    strict_header = ("Based on these ACTUAL execution results, determine the next step. Remember:\n"
                                     "1. You MUST use the code_executor tool to run any code\n"
                                     "2. NEVER write code in ```python blocks\n"
                                     "3. Wait for each execution result before proceeding\n"
                                     "4. Only provide ONE step at a time\n"
                                     "5. Consider that \"picoCTF\" itself might be encoded\n\n"
                                     "Example of how to use the tool:\n"
                                     "<tool>code_executor</tool>\n<input>\nyour_code_here\n</input>\n\n")
                    response = agent.interact(strict_header + human_input)
                elif choice == "3":
                    # Human-only verification (do not send to LLM)
                    import re, os, json
                    candidate = None
                    # 1) Prefer last tool results
                    if hasattr(agent, 'last_tool_results') and agent.last_tool_results:
                        for res in reversed(agent.last_tool_results):
                            m = re.search(r"picoCTF\{[^}]+\}", res)
                            if m:
                                candidate = m.group(0)
                                break
                    # 2) Search conversation (AI and human)
                    if not candidate:
                        try:
                            rounds = getattr(agent, 'conversation_history', [])
                            for r in reversed(rounds):
                                for text in (r.ai_response, r.human_input):
                                    m = re.search(r"picoCTF\{[^}]+\}", text)
                                    if m:
                                        candidate = m.group(0)
                                        break
                                if candidate:
                                    break
                        except Exception:
                            candidate = None
                    # 3) Ask user to input if still not found
                    if not candidate:
                        manual = input("No picoCTF{...} found. Enter flag manually (blank to cancel): ").strip()
                        if manual.startswith("picoCTF{") and manual.endswith("}"):
                            candidate = manual
                    if candidate:
                        print(f"\nCandidate flag: {candidate}")
                        final_choice = input("Confirm this as final flag and save? (y/n): ").strip().lower()
                        if final_choice == 'y':
                            # Merge final flag into conversation JSON instead of separate file
                            year = challenge_data.get('year', 'unknown')
                            category = challenge_data.get('category', 'unknown')
                            title_slug = challenge_data.get('title', 'unknown').lower().replace(' ', '_')
                            save_path = f"challenges/{year}/{category}/{title_slug}/hitl_solution_conversation.json"
                            summary = agent.get_conversation_summary()
                            summary['final_flag'] = candidate
                            summary['verified'] = True
                            # Attach task_tree snapshot if available
                            try:
                                if hasattr(agent, 'task_tree') and agent.task_tree:
                                    summary['task_tree'] = agent.task_tree.get_tree_display()
                            except Exception:
                                pass
                            with open(save_path, 'w', encoding='utf-8') as f:
                                json.dump(summary, f, indent=2, ensure_ascii=False)
                            print(f"Conversation (with final flag) saved to: {save_path}")
                            print(f"flag: {candidate}")
                            return True
                        else:
                            print("Flag rejected. Continue solving.")
                    else:
                        print("No flag provided. Continue solving.")
                else:
                    print("Solving stopped by user.")
                    break
            else:
                # No tool results, always ask in HITL
                print("\nWhat would you like to do?")
                print("1. Continue (agent determines next step)")
                print("2. Enter custom prompt for LLM")
                print("3. Stop solving")
                choice = input("Enter your choice (1-3): ").strip()
                if choice == "1":
                    next_input = agent.get_continue_prompt("", agent.last_tool_results if hasattr(agent, 'last_tool_results') else [])
                    response = agent.interact(next_input)
                elif choice == "2":
                    human_input = input("\nEnter your custom prompt for LLM: ").strip()
                    if not human_input:
                        print("Empty prompt, skipping.")
                        continue
                    strict_header = ("Based on these ACTUAL execution results, determine the next step. Remember:\n"
                                     "1. You MUST use the code_executor tool to run any code\n"
                                     "2. NEVER write code in ```python blocks\n"
                                     "3. Wait for each execution result before proceeding\n"
                                     "4. Only provide ONE step at a time\n"
                                     "5. Consider that \"picoCTF\" itself might be encoded\n\n"
                                     "Example of how to use the tool:\n"
                                     "<tool>code_executor</tool>\n<input>\nyour_code_here\n</input>\n\n")
                    response = agent.interact(strict_header + human_input)
                else:
                    print("Solving stopped by user.")
                    break
            


            # Detect picoCTF flag in the latest response (single-brace form)
            import re, os, json
            flag_match = re.search(r"picoCTF\{[^}]+\}", response)
            detected_flag = flag_match.group(0) if flag_match else None

            if detected_flag:
                print(f"\n🏴 Detected potential flag: {detected_flag}")
                confirm = input("Confirm this as final flag and save? (y/n): ").strip().lower()
                if confirm == 'y':
                    # Save into conversation JSON only
                    year = challenge_data.get('year', 'unknown')
                    category = challenge_data.get('category', 'unknown')
                    title_slug = challenge_data.get('title', 'unknown').lower().replace(' ', '_')
                    save_path = f"challenges/{year}/{category}/{title_slug}/hitl_solution_conversation.json"
                    # Get existing summary and attach final flag
                    summary = agent.get_conversation_summary()
                    summary['final_flag'] = detected_flag
                    summary['verified'] = True
                    # Attach task_tree snapshot if present
                    try:
                        if hasattr(agent, 'task_tree') and agent.task_tree:
                            summary['task_tree'] = agent.task_tree.get_tree_display()
                    except Exception:
                        pass
                    with open(save_path, 'w', encoding='utf-8') as f:
                        json.dump(summary, f, indent=2, ensure_ascii=False)
                    print(f"\nConversation (with final flag) saved to: {save_path}")
                    print(f"flag: {detected_flag}")
                    break
                else:
                    print("Flag rejected. Continuing...")

            # If not confirmed or no flag, continue loop
        
        # Save conversation
        save_path = f"challenges/{challenge_data.get('year', 'unknown')}/{challenge_data.get('category', 'unknown')}/{challenge_data.get('title', 'unknown').lower().replace(' ', '_')}/hitl_solution_conversation.json"
        agent.save_conversation(save_path)
        print(f"Conversation saved to: {save_path}")
        
        return True
        
    except Exception as e:
        import traceback
        print(f"HITL solving failed: {e}")
        print(f"Exception type: {type(e)}")
        print("Traceback:")
        traceback.print_exc()
        return False

def main():
    """Main function - simplified flow"""
    # 1. Welcome interface
    welcome()
    
    # 2. Select mode
    mode = select_mode()
    print(f"Mode selected: {mode}")
    
    # 3. Challenge management (call ctf_practice.py)
    challenge_data = handle_challenge_phase()
    if not challenge_data:
        print("Failed to complete challenge phase")
        return
    
    # 4. Prompt generation (call ctf_prompts.py)
    prompt = handle_prompt_phase(challenge_data)
    if not prompt:
        print("Failed to complete prompt phase")
        return
    
    # 5. LLM interaction
    success = handle_llm_phase(prompt, mode, challenge_data)
    if success:
        print("CTF session completed successfully!")
    else:
        print("CTF session failed")

if __name__ == "__main__":
    main()
