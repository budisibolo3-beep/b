#!/usr/bin/env python3

import os
import sys
import subprocess
import json
import readline
import requests
import base64
import hashlib
import tempfile
from pathlib import Path
import google.generativeai as genai
import sqlite3
from datetime import datetime
import re
import shutil

class AdvancedGeminiAIAssistant:
    def __init__(self):
        self.api_key = self.get_api_key()
        self.history_db = "/root/.gemini_ai/history.db"
        self.error_db = "/root/.gemini_ai/errors.db"
        self.repair_db = "/root/.gemini_ai/repair_patterns.db"
        self.setup_directories()
        self.setup_databases()
        self.setup_gemini()
        
        self.supported_languages = {
            'python': {'ext': ['.py'], 'deps': ['python3', 'pip3']},
            'javascript': {'ext': ['.js', '.ts'], 'deps': ['node', 'npm']},
            'java': {'ext': ['.java'], 'deps': ['javac', 'java']},
            'cpp': {'ext': ['.cpp', '.cxx', '.cc'], 'deps': ['g++', 'clang++']},
            'c': {'ext': ['.c'], 'deps': ['gcc', 'clang']},
            'go': {'ext': ['.go'], 'deps': ['go']},
            'rust': {'ext': ['.rs'], 'deps': ['rustc', 'cargo']},
            'php': {'ext': ['.php'], 'deps': ['php']},
            'ruby': {'ext': ['.rb'], 'deps': ['ruby']},
            'bash': {'ext': ['.sh', '.bash'], 'deps': ['bash']}
        }
        
    def get_api_key(self):
        api_file = "/root/.gemini_ai/api_key.txt"
        if os.path.exists(api_file):
            with open(api_file, 'r') as f:
                return f.read().strip()
        else:
            print("Masukkan API Key Gemini Anda: ")
            api_key = input().strip()
            os.makedirs("/root/.gemini_ai", exist_ok=True)
            with open(api_file, 'w') as f:
                f.write(api_key)
            os.chmod(api_file, 0o600)
            return api_key
    
    def setup_directories(self):
        os.makedirs("/root/.gemini_ai", exist_ok=True)
        os.makedirs("/root/.gemini_ai/scripts", exist_ok=True)
        os.makedirs("/root/.gemini_ai/backups", exist_ok=True)
        os.makedirs("/root/.gemini_ai/repairs", exist_ok=True)
    
    def setup_databases(self):
        # History database
        conn = sqlite3.connect(self.history_db)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS history
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     timestamp TEXT,
                     command TEXT,
                     output TEXT,
                     success INTEGER,
                     language TEXT)''')
        conn.commit()
        conn.close()
        
        # Error database
        conn = sqlite3.connect(self.error_db)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS errors
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     error_pattern TEXT,
                     error_type TEXT,
                     language TEXT,
                     solution TEXT,
                     repair_script TEXT,
                     frequency INTEGER DEFAULT 1,
                     success_rate REAL DEFAULT 0.0,
                     last_occurred TEXT)''')
        conn.commit()
        conn.close()
        
        # Repair patterns database
        conn = sqlite3.connect(self.repair_db)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS repair_patterns
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     pattern_type TEXT,
                     pattern TEXT,
                     replacement TEXT,
                     language TEXT,
                     effectiveness REAL DEFAULT 1.0)''')
        conn.commit()
        conn.close()
    
    def setup_gemini(self):
        try:
            genai.configure(api_key=self.api_key)
            
            # List available models dan pilih yang tersedia
            available_models = []
            try:
                for model in genai.list_models():
                    if 'generateContent' in model.supported_generation_methods:
                        available_models.append(model.name)
                        print(f"Available model: {model.name}")
            except Exception as e:
                print(f"Error listing models: {e}")
            
            # Coba model yang umum tersedia
            preferred_models = [
                'models/gemini-1.5-flash',
                'models/gemini-1.5-pro',
                'models/gemini-pro',
                'models/gemini-1.0-pro'
            ]
            
            selected_model = None
            for model_name in preferred_models:
                if any(model_name in avail for avail in available_models):
                    selected_model = model_name
                    break
            
            if not selected_model and available_models:
                selected_model = available_models[0]
            elif not selected_model:
                # Fallback ke model default
                selected_model = 'models/gemini-1.5-flash'
            
            print(f"Using model: {selected_model}")
            self.model = genai.GenerativeModel(selected_model)
            
        except Exception as e:
            print(f"Error setting up Gemini: {e}")
            print("Trying fallback configuration...")
            # Fallback configuration
            try:
                self.model = genai.GenerativeModel('gemini-1.5-flash')
            except:
                try:
                    self.model = genai.GenerativeModel('gemini-pro')
                except:
                    print("CRITICAL: No Gemini models available. Please check your API key and model access.")
                    sys.exit(1)
    
    def detect_language(self, file_path):
        if not os.path.exists(file_path):
            return None
            
        extension = Path(file_path).suffix.lower()
        for lang, info in self.supported_languages.items():
            if extension in info['ext']:
                return lang
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                first_line = f.readline().strip()
                if first_line.startswith('#!'):
                    if 'python' in first_line:
                        return 'python'
                    elif 'node' in first_line:
                        return 'javascript'
                    elif 'bash' in first_line:
                        return 'bash'
                    elif 'ruby' in first_line:
                        return 'ruby'
        except:
            pass
            
        return 'unknown'
    
    def decrypt_file(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            if any(pattern in content.lower() for pattern in ['exec(', 'compile(', 'base64', 'decode(', 'marshal', 'loads(']):
                prompt = f"""Analyze this potentially encrypted/obfuscated code and provide a cleaned version:

{content}

If this is obfuscated code, decrypt it and provide the original code."""

                response = self.model.generate_content(prompt)
                decrypted_code = response.text
                
                backup_path = f"/root/.gemini_ai/backups/{os.path.basename(file_path)}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                shutil.copy2(file_path, backup_path)
                
                with open(file_path, 'w') as f:
                    f.write(decrypted_code)
                
                return f"✅ File decrypted and backed up to {backup_path}"
            else:
                return "ℹ️ File doesn't appear to be encrypted"
                
        except Exception as e:
            return f"❌ Decryption failed: {str(e)}"
    
    def advanced_auto_repair(self, error_output, file_path=None, original_command=None):
        language = self.detect_language(file_path) if file_path else 'unknown'
        
        prompt = f"""Analyze and fix this Linux/system error:

ERROR: {error_output}
FILE: {file_path if file_path else 'N/A'}
LANGUAGE: {language}
COMMAND: {original_command if original_command else 'N/A'}

Provide the exact terminal commands to fix this issue. Focus on:
1. Missing dependencies
2. Permission issues  
3. Configuration problems
4. Syntax errors
5. Service issues

Return ONLY the commands to execute, no explanations."""

        try:
            response = self.model.generate_content(prompt)
            solution = response.text.strip()
            
            return {"success": True, "solution": solution}
            
        except Exception as e:
            return {"success": False, "message": f"Repair analysis failed: {str(e)}"}
    
    def multi_language_repair(self, file_path):
        language = self.detect_language(file_path)
        
        if language == 'unknown':
            return {"success": False, "message": "❌ Unsupported file type"}
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            prompt = f"""Repair this {language.upper()} code. Fix all syntax errors, missing imports, and logical errors:

{content}

Provide the COMPLETE fixed code with all corrections. Return ONLY the code, no explanations."""

            response = self.model.generate_content(prompt)
            fixed_code = response.text
            
            # Clean the response (remove markdown code blocks if present)
            fixed_code = re.sub(r'```[a-z]*\n', '', fixed_code)
            fixed_code = re.sub(r'\n```', '', fixed_code)
            
            backup_path = f"/root/.gemini_ai/backups/{os.path.basename(file_path)}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy2(file_path, backup_path)
            
            with open(file_path, 'w') as f:
                f.write(fixed_code)
            
            # Install language dependencies if needed
            self.install_language_dependencies(language)
            
            return {
                "success": True, 
                "message": f"✅ File repaired successfully!", 
                "backup": backup_path,
                "language": language
            }
            
        except Exception as e:
            return {"success": False, "message": f"❌ Repair failed: {str(e)}"}
    
    def install_language_dependencies(self, language):
        """Install common dependencies for programming language"""
        if language in self.supported_languages:
            deps = self.supported_languages[language]['deps']
            for dep in deps:
                try:
                    # Check if dependency is installed
                    check_result = subprocess.run(f"which {dep}", shell=True, capture_output=True, text=True)
                    if check_result.returncode != 0:
                        print(f"📦 Installing {dep} for {language}...")
                        install_result = self.execute_command(f"apt-get install -y {dep}", use_sudo=True)
                        print(f"Install result: {install_result}")
                except Exception as e:
                    print(f"Warning: Could not install {dep}: {e}")
    
    def execute_command(self, command, use_sudo=True):
        """Execute command dengan enhanced error handling"""
        try:
            if use_sudo and not command.startswith('sudo '):
                command = f"sudo {command}"
            
            print(f"🚀 Executing: {command}")
            
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=60)
            
            success = result.returncode == 0
            output = result.stdout if success else result.stderr
            
            if not success:
                print(f"❌ Error: {output}")
                # Auto-trigger advanced repair
                repair_result = self.advanced_auto_repair(output, original_command=command)
                if repair_result.get('success'):
                    repair_solution = repair_result.get('solution')
                    print(f"🔧 Auto-repair suggestion: {repair_solution}")
                    
                    # Ask user if they want to execute the repair
                    user_input = input("Execute this repair? (y/N): ").strip().lower()
                    if user_input in ['y', 'yes']:
                        repair_output = self.execute_command(repair_solution, use_sudo=True)
                        return f"Original error: {output}\nRepair executed: {repair_output}"
                    else:
                        return f"Error: {output}\nRepair suggestion: {repair_solution}"
                else:
                    return f"Error: {output}"
            
            print(f"✅ Success: {output}")
            return output
            
        except subprocess.TimeoutExpired:
            return "❌ Error: Command timed out"
        except Exception as e:
            return f"❌ Error executing command: {str(e)}"

    def interactive_chat(self):
        print("🤖 Advanced Gemini AI Assistant - Terminal Mode")
        print("✅ Features: 10 Language Repair • Auto Decrypt • Root Access • Unlimited Execution")
        print("🔧 Supported: Python, JS, Java, C/C++, Go, Rust, PHP, Ruby, Bash")
        print("=" * 60)
        
        while True:
            try:
                user_input = input("\n🤖 AI> ").strip()
                
                if user_input.lower() in ['exit', 'quit']:
                    break
                elif user_input.startswith('repair '):
                    file_path = user_input[7:].strip()
                    if os.path.exists(file_path):
                        result = self.multi_language_repair(file_path)
                        print(json.dumps(result, indent=2))
                    else:
                        print("❌ File not found")
                elif user_input.startswith('decrypt '):
                    file_path = user_input[8:].strip()
                    if os.path.exists(file_path):
                        result = self.decrypt_file(file_path)
                        print(result)
                    else:
                        print("❌ File not found")
                elif user_input.startswith('exec '):
                    command = user_input[5:]
                    result = self.execute_command(command)
                    print(result)
                elif user_input.startswith('fix '):
                    error_desc = user_input[4:]
                    result = self.advanced_auto_repair(error_desc)
                    print(json.dumps(result, indent=2))
                elif user_input == 'models':
                    # List available models
                    try:
                        for model in genai.list_models():
                            if 'generateContent' in model.supported_generation_methods:
                                print(f"📋 {model.name}")
                    except Exception as e:
                        print(f"Error listing models: {e}")
                else:
                    prompt = f"""You are an advanced Linux AI assistant with root access and system repair capabilities.

User request: {user_input}

Provide helpful, technical assistance with executable solutions when appropriate."""
                    
                    try:
                        response = self.model.generate_content(prompt)
                        print(response.text)
                    except Exception as e:
                        print(f"❌ AI Error: {e}")
                    
            except KeyboardInterrupt:
                print("\n👋 Exiting...")
                break
            except Exception as e:
                print(f"❌ Error: {str(e)}")

def main():
    # Check if running as root, if not restart with sudo
    if os.geteuid() != 0:
        print("🔒 Restarting with root privileges...")
        os.execvp("sudo", ["sudo", "python3"] + sys.argv)
    
    assistant = AdvancedGeminiAIAssistant()
    
    if len(sys.argv) > 1:
        command = " ".join(sys.argv[1:])
        
        if sys.argv[1] == 'repair' and len(sys.argv) > 2:
            file_path = sys.argv[2]
            result = assistant.multi_language_repair(file_path)
            print(json.dumps(result, indent=2))
        elif sys.argv[1] == 'decrypt' and len(sys.argv) > 2:
            file_path = sys.argv[2]
            result = assistant.decrypt_file(file_path)
            print(result)
        elif sys.argv[1] == 'models':
            # List models
            try:
                genai.configure(api_key=assistant.api_key)
                for model in genai.list_models():
                    if 'generateContent' in model.supported_generation_methods:
                        print(f"📋 {model.name}")
            except Exception as e:
                print(f"Error: {e}")
        else:
            result = assistant.execute_command(command)
            print(result)
    else:
        assistant.interactive_chat()

if __name__ == "__main__":
    main()