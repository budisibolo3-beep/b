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
        
        # Supported programming languages
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
        
        # Error database dengan detail lengkap
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
        
        # Insert initial repair patterns
        initial_patterns = [
            ('import_missing', r'ModuleNotFoundError: No module named \'([^\']+)\'', 'pip3 install \\1', 'python', 0.9),
            ('dependency_missing', r'error while loading shared libraries: ([^:]+):', 'apt-get install \\1', 'system', 0.8),
            ('permission_denied', r'Permission denied', 'chmod +x \\1', 'system', 0.7),
            ('command_not_found', r'command not found', 'apt-get install \\1', 'system', 0.8),
            ('syntax_error', r'SyntaxError:', 'Fix syntax in file', 'python', 0.6),
            ('indentation_error', r'IndentationError:', 'Fix indentation', 'python', 0.7)
        ]
        
        for pattern in initial_patterns:
            c.execute('''INSERT OR IGNORE INTO repair_patterns 
                        (pattern_type, pattern, replacement, language, effectiveness) 
                        VALUES (?, ?, ?, ?, ?)''', pattern)
        
        conn.commit()
        conn.close()
    
    def setup_gemini(self):
        genai.configure(api_key=self.api_key)
        generation_config = {
            "temperature": 0.7,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 8192,
        }
        self.model = genai.GenerativeModel('gemini-pro', generation_config=generation_config)
    
    def detect_language(self, file_path):
        if not os.path.exists(file_path):
            return None
            
        extension = Path(file_path).suffix.lower()
        for lang, info in self.supported_languages.items():
            if extension in info['ext']:
                return lang
        
        # Try to detect from shebang or content
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
        """Auto-decrypt encrypted Python files"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Check if file might be encrypted/obfuscated
            if any(pattern in content.lower() for pattern in ['exec(', 'compile(', 'base64', 'decode(', 'marshal', 'loads(']):
                prompt = f"""Analyze this potentially encrypted/obfuscated Python code and provide a cleaned, readable version:

{content}

If this is obfuscated code, decrypt it and provide the original Python code. Remove any malicious code and fix any syntax issues."""

                response = self.model.generate_content(prompt)
                decrypted_code = response.text
                
                # Backup original file
                backup_path = f"/root/.gemini_ai/backups/{os.path.basename(file_path)}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                shutil.copy2(file_path, backup_path)
                
                # Write decrypted code
                with open(file_path, 'w') as f:
                    f.write(decrypted_code)
                
                return f"File decrypted and backed up to {backup_path}"
            else:
                return "File doesn't appear to be encrypted"
                
        except Exception as e:
            return f"Decryption failed: {str(e)}"
    
    def advanced_auto_repair(self, error_output, file_path=None, original_command=None):
        """Advanced repair dengan analisis multi-bahasa"""
        
        # Deteksi bahasa dari file atau error
        language = self.detect_language(file_path) if file_path else 'unknown'
        
        # Analyze error dengan Gemini
        prompt = f"""Advanced Error Analysis and Repair:

Error: {error_output}
File: {file_path if file_path else 'N/A'}
Language: {language}
Command: {original_command if original_command else 'N/A'}

Provide a comprehensive repair solution including:

1. ROOT CAUSE ANALYSIS - Explain the exact technical cause
2. IMMEDIATE FIX - Provide exact commands to fix this now
3. DEPENDENCY CHECK - Check and install missing dependencies  
4. CODE REPAIR - Fix any broken code or strings
5. PREVENTION - How to prevent this error in future

For code files, provide the complete fixed code.
For system errors, provide the exact terminal commands.

Format response as JSON:
{{
    "root_cause": "analysis",
    "immediate_fix": "command or code",
    "dependencies": ["list", "of", "deps"],
    "prevention": "advice",
    "confidence": 0.95
}}"""

        try:
            response = self.model.generate_content(prompt)
            response_text = response.text
            
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                repair_data = json.loads(json_match.group())
                
                # Execute the repair
                result = self.execute_repair_plan(repair_data, file_path, language)
                
                # Log the repair pattern
                self.log_repair_pattern(error_output, repair_data, language, result['success'])
                
                return result
            else:
                return {"success": False, "message": "Could not parse AI response", "raw_response": response_text}
                
        except Exception as e:
            return {"success": False, "message": f"Repair analysis failed: {str(e)}"}
    
    def execute_repair_plan(self, repair_data, file_path, language):
        """Execute comprehensive repair plan"""
        results = []
        
        try:
            # Install dependencies first
            if 'dependencies' in repair_data and repair_data['dependencies']:
                for dep in repair_data['dependencies']:
                    result = self.execute_command(f"apt-get install -y {dep}", use_sudo=True)
                    results.append(f"Dependency {dep}: {result}")
            
            # Apply immediate fix
            if 'immediate_fix' in repair_data:
                fix = repair_data['immediate_fix']
                
                # If it's a command, execute it
                if any(cmd in fix for cmd in ['apt-get', 'pip', 'npm', 'chmod', 'chown']):
                    result = self.execute_command(fix, use_sudo=True)
                    results.append(f"Command fix: {result}")
                # If it's code, write to file
                elif file_path and ('def ' in fix or 'function ' in fix or 'class ' in fix):
                    # Backup original file
                    backup_path = f"{file_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    shutil.copy2(file_path, backup_path)
                    
                    # Write fixed code
                    with open(file_path, 'w') as f:
                        f.write(fix)
                    results.append(f"Code repaired and backed up to {backup_path}")
            
            return {"success": True, "results": results, "repair_data": repair_data}
            
        except Exception as e:
            return {"success": False, "message": f"Repair execution failed: {str(e)}", "results": results}
    
    def multi_language_repair(self, file_path):
        """Repair file in any of 10 supported languages"""
        language = self.detect_language(file_path)
        
        if language == 'unknown':
            return {"success": False, "message": "Unsupported file type"}
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            prompt = f"""Repair this {language.upper()} code. Fix all syntax errors, logical errors, missing imports, and dependencies.

File: {file_path}
Language: {language}

Code:
{content}

Provide the COMPLETE fixed code with all errors corrected. Include proper imports and fix any string/encoding issues."""

            response = self.model.generate_content(prompt)
            fixed_code = response.text
            
            # Backup original
            backup_path = f"/root/.gemini_ai/backups/{os.path.basename(file_path)}.backup"
            shutil.copy2(file_path, backup_path)
            
            # Write fixed code
            with open(file_path, 'w') as f:
                f.write(fixed_code)
            
            # Install language-specific dependencies
            self.install_language_dependencies(language)
            
            return {"success": True, "message": f"File repaired and backed up to {backup_path}", "language": language}
            
        except Exception as e:
            return {"success": False, "message": f"Repair failed: {str(e)}"}
    
    def install_language_dependencies(self, language):
        """Install common dependencies for programming language"""
        if language in self.supported_languages:
            deps = self.supported_languages[language]['deps']
            for dep in deps:
                try:
                    self.execute_command(f"which {dep}", use_sudo=False)
                except:
                    self.execute_command(f"apt-get install -y {dep}", use_sudo=True)
    
    def log_repair_pattern(self, error_pattern, repair_data, language, success):
        """Log successful repair patterns for learning"""
        conn = sqlite3.connect(self.repair_db)
        c = conn.cursor()
        
        effectiveness = 1.0 if success else 0.0
        
        c.execute('''INSERT OR REPLACE INTO repair_patterns 
                    (pattern_type, pattern, replacement, language, effectiveness)
                    VALUES (?, ?, ?, ?, ?)''',
                 ('ai_learned', error_pattern[:200], json.dumps(repair_data), language, effectiveness))
        
        conn.commit()
        conn.close()
    
    def execute_command(self, command, use_sudo=True):
        """Execute command dengan enhanced error handling"""
        try:
            if use_sudo and not command.startswith('sudo '):
                command = f"sudo {command}"
            
            print(f"🚀 Executing: {command}")
            
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=60)
            
            success = result.returncode == 0
            output = result.stdout if success else result.stderr
            
            # Log to history
            self.log_history(command, output, success)
            
            if not success:
                print(f"❌ Error: {output}")
                # Auto-trigger advanced repair
                repair_result = self.advanced_auto_repair(output, original_command=command)
                if repair_result.get('success'):
                    print(f"✅ Auto-repair successful: {repair_result}")
                    return repair_result
                else:
                    return f"Error: {output}\nRepair failed: {repair_result.get('message', 'Unknown error')}"
            
            return output
            
        except subprocess.TimeoutExpired:
            return "Error: Command timed out"
        except Exception as e:
            return f"Error executing command: {str(e)}"
    
    def log_history(self, command, output, success):
        """Enhanced history logging"""
        conn = sqlite3.connect(self.history_db)
        c = conn.cursor()
        
        # Detect language from command
        language = 'system'
        for lang in self.supported_languages:
            if any(ext in command for ext in self.supported_languages[lang]['ext']):
                language = lang
                break
        
        c.execute("INSERT INTO history (timestamp, command, output, success, language) VALUES (?, ?, ?, ?, ?)",
                 (datetime.now().isoformat(), command, output, success, language))
        
        # Maintain 10,000 records limit
        c.execute("DELETE FROM history WHERE id NOT IN (SELECT id FROM history ORDER BY id DESC LIMIT 10000)")
        
        conn.commit()
        conn.close()

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
                        print("File not found")
                elif user_input.startswith('decrypt '):
                    file_path = user_input[8:].strip()
                    if os.path.exists(file_path):
                        result = self.decrypt_file(file_path)
                        print(result)
                    else:
                        print("File not found")
                elif user_input.startswith('exec '):
                    command = user_input[5:]
                    result = self.execute_command(command)
                    print(result)
                elif user_input.startswith('sudo '):
                    result = self.execute_command(user_input[5:], use_sudo=False)
                    print(result)
                elif user_input.startswith('fix '):
                    error_desc = user_input[4:]
                    result = self.advanced_auto_repair(error_desc)
                    print(json.dumps(result, indent=2))
                else:
                    # AI conversation dengan context advanced
                    prompt = f"""You are an advanced Linux AI assistant with:
- Root access and unlimited execution
- Auto-repair for 10 programming languages  
- File decryption capabilities
- Advanced dependency resolution
- Full internet access when needed

User request: {user_input}

Provide expert technical assistance with executable solutions."""
                    
                    response = self.model.generate_content(prompt)
                    print(response.text)
                    
            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except Exception as e:
                print(f"Error: {str(e)}")

def main():
    if os.geteuid() != 0:
        print("🔄 Restarting with root privileges...")
        os.execvp("sudo", ["sudo", "python3"] + sys.argv)
    
    assistant = AdvancedGeminiAIAssistant()
    
    if len(sys.argv) > 1:
        command = " ".join(sys.argv[1:])
        
        if sys.argv[1] == 'repair' and len(sys.argv) > 2:
            # File repair mode
            file_path = sys.argv[2]
            result = assistant.multi_language_repair(file_path)
            print(json.dumps(result, indent=2))
        elif sys.argv[1] == 'decrypt' and len(sys.argv) > 2:
            # File decryption mode
            file_path = sys.argv[2]
            result = assistant.decrypt_file(file_path)
            print(result)
        else:
            # Command execution mode
            result = assistant.execute_command(command)
            print(result)
    else:
        # Interactive mode
        assistant.interactive_chat()

if __name__ == "__main__":
    main()