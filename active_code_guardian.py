#!/usr/bin/env python3
"""
Active Code Guardian - Proactively prevents bad code
Monitors agents in real-time and intervenes when quality drops
"""

import subprocess
import time
import os
import hashlib
from pathlib import Path
from datetime import datetime
import json
import re

class ActiveCodeGuardian:
    def __init__(self):
        self.main_file = Path("/mnt/c/Users/psytz/TMUX Final/Agent-MCP/beverly_comprehensive_erp.py")
        self.backup_dir = Path("/mnt/c/Users/psytz/TMUX Final/Agent-MCP/backups")
        self.backup_dir.mkdir(exist_ok=True)
        
        self.agents = {
            'supply_chain': 'beverly-agents:2',
            'inventory': 'beverly-agents:3', 
            'ml_forecast': 'beverly-agents:4',
            'monitor': 'beverly-agents:5'
        }
        
        self.last_good_backup = None
        self.violation_count = {}
        self.intervention_threshold = 3
        
    def create_backup(self, reason="scheduled"):
        """Create a backup of the current file"""
        if not self.main_file.exists():
            return None
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"beverly_erp_{timestamp}_{reason}.py"
        
        with open(self.main_file, 'r') as f:
            content = f.read()
            
        with open(backup_path, 'w') as f:
            f.write(content)
            
        return backup_path
    
    def check_agent_activity(self, agent_name, window):
        """Check what an agent is doing right now"""
        try:
            # Capture recent activity
            cmd = f"tmux capture-pane -t {window} -p | tail -30"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            activity = result.stdout
            
            # Detect suspicious patterns
            suspicious_patterns = [
                (r'rm\s+-rf', 'DANGEROUS: Attempting to delete files'),
                (r'except\s*:', 'WARNING: Using bare except clause'),
                (r'except.*:\s*pass', 'WARNING: Silencing exceptions'),
                (r'while\s+True.*sleep\(0\)', 'CRITICAL: Infinite busy loop'),
                (r'exec\(|eval\(', 'CRITICAL: Using exec/eval'),
                (r'DELETE\s+FROM.*WHERE\s+1=1', 'CRITICAL: Dangerous SQL'),
            ]
            
            violations = []
            for pattern, message in suspicious_patterns:
                if re.search(pattern, activity, re.IGNORECASE):
                    violations.append(message)
                    
            return violations
            
        except Exception as e:
            return []
    
    def validate_current_file(self):
        """Validate the current state of the main file"""
        if not self.main_file.exists():
            return {'valid': False, 'errors': ['File not found']}
            
        with open(self.main_file, 'r') as f:
            content = f.read()
            
        errors = []
        warnings = []
        
        # Syntax check
        try:
            compile(content, str(self.main_file), 'exec')
        except SyntaxError as e:
            errors.append(f"SYNTAX ERROR: {e}")
            
        # Quality checks
        lines = content.splitlines()
        
        # Check for extremely long functions
        in_function = False
        func_start = 0
        func_name = ""
        
        for i, line in enumerate(lines, 1):
            if line.strip().startswith('def '):
                if in_function and (i - func_start) > 200:
                    errors.append(f"Function '{func_name}' is {i - func_start} lines (MAX: 200)")
                in_function = True
                func_start = i
                func_name = line.split('def ')[1].split('(')[0]
            elif in_function and line and not line[0].isspace():
                in_function = False
                
        # Check for duplicate functions
        func_names = re.findall(r'def\s+(\w+)\s*\(', content)
        duplicates = [name for name in func_names if func_names.count(name) > 1]
        if duplicates:
            errors.append(f"DUPLICATE FUNCTIONS: {set(duplicates)}")
            
        # Performance killers
        if re.search(r'for.*:\s*\n.*for.*:\s*\n.*for.*:', content):
            warnings.append("Triple nested loops detected")
            
        if re.search(r'\.append\(.*\).*\n.*' * 100, content):
            warnings.append("Excessive list appends in loop")
            
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    def intervene(self, agent_name, violation_type, message):
        """Actively intervene when an agent is causing problems"""
        window = self.agents[agent_name]
        
        # Track violations
        if agent_name not in self.violation_count:
            self.violation_count[agent_name] = 0
        self.violation_count[agent_name] += 1
        
        # Escalating interventions
        if self.violation_count[agent_name] == 1:
            # First violation - warning
            cmd = f'tmux send-keys -t {window} C-c'  # Stop current action
            subprocess.run(cmd, shell=True)
            time.sleep(0.5)
            
            warning = f"⚠️ GUARDIAN WARNING: {message}. Fix immediately!"
            cmd = f'tmux send-keys -t {window} "{warning}" Enter'
            subprocess.run(cmd, shell=True)
            
        elif self.violation_count[agent_name] == 2:
            # Second violation - force stop
            cmd = f'tmux send-keys -t {window} C-c C-c'  # Force stop
            subprocess.run(cmd, shell=True)
            
            warning = f"🛑 GUARDIAN STOP: {message}. This is your FINAL warning!"
            cmd = f'tmux send-keys -t {window} "{warning}" Enter'
            subprocess.run(cmd, shell=True)
            
        else:
            # Third violation - rollback and lockout
            print(f"🔒 LOCKING OUT {agent_name} - Too many violations!")
            
            # Restore last good backup
            if self.last_good_backup and self.last_good_backup.exists():
                with open(self.last_good_backup, 'r') as f:
                    good_content = f.read()
                with open(self.main_file, 'w') as f:
                    f.write(good_content)
                print(f"✅ Restored last good backup")
            
            # Clear agent window
            cmd = f'tmux send-keys -t {window} C-c C-d'
            subprocess.run(cmd, shell=True)
            
            # Log the lockout
            with open('agent_lockouts.log', 'a') as f:
                f.write(f"[{datetime.now()}] LOCKED OUT {agent_name}: {self.violation_count[agent_name]} violations\n")
    
    def monitor_loop(self):
        """Main monitoring loop"""
        print("🛡️ ACTIVE CODE GUARDIAN STARTED")
        print("👁️ Watching all agent activities")
        print("🚨 Will intervene on quality violations\n")
        
        # Create initial backup
        self.last_good_backup = self.create_backup("initial")
        last_check_hash = ""
        
        while True:
            try:
                # Check file integrity
                validation = self.validate_current_file()
                
                if not validation['valid']:
                    print(f"\n❌ FILE VALIDATION FAILED:")
                    for error in validation['errors']:
                        print(f"   - {error}")
                    
                    # Find and punish responsible agent
                    for agent_name, window in self.agents.items():
                        violations = self.check_agent_activity(agent_name, window)
                        if violations or "Edit" in subprocess.run(
                            f"tmux capture-pane -t {window} -p | tail -5", 
                            shell=True, capture_output=True, text=True).stdout:
                            self.intervene(agent_name, "file_corruption", validation['errors'][0])
                            break
                
                # Check each agent
                for agent_name, window in self.agents.items():
                    violations = self.check_agent_activity(agent_name, window)
                    
                    if violations:
                        print(f"\n⚠️  {agent_name.upper()} VIOLATIONS:")
                        for v in violations:
                            print(f"   - {v}")
                        
                        # Intervene based on severity
                        if any('CRITICAL' in v for v in violations):
                            self.intervene(agent_name, "critical", violations[0])
                        elif any('WARNING' in v for v in violations):
                            self.intervene(agent_name, "warning", violations[0])
                
                # Create periodic good backup if file is valid
                if validation['valid'] and not validation['warnings']:
                    # Check if file changed
                    with open(self.main_file, 'rb') as f:
                        current_hash = hashlib.md5(f.read()).hexdigest()
                    
                    if current_hash != last_check_hash:
                        self.last_good_backup = self.create_backup("validated")
                        print(f"✅ Created validated backup")
                        last_check_hash = current_hash
                        
                        # Reset violation counts on good commit
                        self.violation_count = {}
                
                # Brief status
                active_agents = []
                for agent_name, window in self.agents.items():
                    activity = subprocess.run(
                        f"tmux capture-pane -t {window} -p | tail -1",
                        shell=True, capture_output=True, text=True).stdout
                    if activity and not activity.startswith('>'):
                        active_agents.append(agent_name)
                
                if active_agents:
                    print(f"🔄 Active agents: {', '.join(active_agents)}", end='\r')
                
                time.sleep(10)  # Check every 10 seconds
                
            except KeyboardInterrupt:
                print("\n\n👋 Guardian shutting down")
                break
            except Exception as e:
                print(f"\n❗ Guardian error: {e}")
                time.sleep(30)

if __name__ == "__main__":
    guardian = ActiveCodeGuardian()
    guardian.monitor_loop()