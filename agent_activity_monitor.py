#!/usr/bin/env python3
"""
Real-time Agent Activity Monitor
Tracks what agents are doing and validates their code changes
"""

import subprocess
import time
import json
import re
from datetime import datetime
from pathlib import Path
import difflib
import ast

class AgentActivityMonitor:
    def __init__(self):
        self.agents = {
            'supply_chain': {'window': 'beverly-agents:2', 'last_activity': None, 'violations': []},
            'inventory': {'window': 'beverly-agents:3', 'last_activity': None, 'violations': []},
            'ml_forecast': {'window': 'beverly-agents:4', 'last_activity': None, 'violations': []},
            'monitor': {'window': 'beverly-agents:5', 'last_activity': None, 'violations': []}
        }
        self.main_file = Path("/mnt/c/Users/psytz/TMUX Final/Agent-MCP/beverly_comprehensive_erp.py")
        self.last_file_content = None
        self.quality_rules = {
            'max_function_length': 100,
            'max_line_length': 120,
            'min_docstring_coverage': 0.7,
            'max_complexity': 10,
            'forbidden_patterns': [
                r'except\s*:',  # Bare except
                r'except.*:\s*pass',  # Except pass
                r'eval\(',  # Eval usage
                r'exec\(',  # Exec usage
                r'print\(.*password',  # Password in print
            ]
        }
        
    def capture_agent_activity(self, agent_name):
        """Capture what an agent is currently doing"""
        window = self.agents[agent_name]['window']
        try:
            # Capture last 50 lines from agent window
            cmd = f"tmux capture-pane -t {window} -p | tail -50"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            activity = result.stdout
            
            # Look for specific patterns
            patterns = {
                'editing': r'(?:Edit|Update|Modify|Write)\((.*?)\)',
                'reading': r'Read\((.*?)\)',
                'running': r'(?:Bash|python|node)\((.*?)\)',
                'planning': r'(?:TODO|TASK|PLAN):\s*(.*)',
                'error': r'(?:Error|Failed|Exception):\s*(.*)'
            }
            
            current_activity = {'timestamp': datetime.now().isoformat(), 'actions': []}
            
            for activity_type, pattern in patterns.items():
                matches = re.findall(pattern, activity, re.IGNORECASE)
                if matches:
                    current_activity['actions'].append({
                        'type': activity_type,
                        'details': matches[-1][:100]  # Last match, truncated
                    })
            
            # Check if agent is modifying the main file
            if 'beverly_comprehensive_erp.py' in activity:
                current_activity['modifying_main_file'] = True
                
            self.agents[agent_name]['last_activity'] = current_activity
            return current_activity
            
        except Exception as e:
            return {'error': str(e)}
    
    def check_file_changes(self):
        """Monitor changes to the main file and validate them"""
        if not self.main_file.exists():
            return None
            
        with open(self.main_file, 'r') as f:
            current_content = f.read()
        
        if self.last_file_content is None:
            self.last_file_content = current_content
            return None
        
        if current_content != self.last_file_content:
            # File changed - analyze the changes
            changes = self.analyze_changes(self.last_file_content, current_content)
            self.last_file_content = current_content
            return changes
        
        return None
    
    def analyze_changes(self, old_content, new_content):
        """Analyze what changed and check for quality issues"""
        old_lines = old_content.splitlines()
        new_lines = new_content.splitlines()
        
        diff = list(difflib.unified_diff(old_lines, new_lines, lineterm=''))
        
        changes = {
            'timestamp': datetime.now().isoformat(),
            'lines_added': 0,
            'lines_removed': 0,
            'functions_modified': [],
            'quality_violations': []
        }
        
        # Count changes
        for line in diff:
            if line.startswith('+') and not line.startswith('+++'):
                changes['lines_added'] += 1
                # Check quality rules on new lines
                self.check_line_quality(line[1:], changes['quality_violations'])
            elif line.startswith('-') and not line.startswith('---'):
                changes['lines_removed'] += 1
        
        # Find modified functions
        func_pattern = r'def\s+(\w+)\s*\('
        old_funcs = set(re.findall(func_pattern, old_content))
        new_funcs = set(re.findall(func_pattern, new_content))
        
        changes['functions_added'] = list(new_funcs - old_funcs)
        changes['functions_removed'] = list(old_funcs - new_funcs)
        
        # Check new functions for quality
        try:
            tree = ast.parse(new_content)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if node.name in changes['functions_added']:
                        self.validate_function(node, new_lines, changes['quality_violations'])
        except:
            pass
        
        return changes
    
    def check_line_quality(self, line, violations):
        """Check a single line for quality issues"""
        # Line length
        if len(line) > self.quality_rules['max_line_length']:
            violations.append(f"Line too long ({len(line)} chars): {line[:50]}...")
        
        # Forbidden patterns
        for pattern in self.quality_rules['forbidden_patterns']:
            if re.search(pattern, line):
                violations.append(f"Forbidden pattern '{pattern}' found: {line[:50]}...")
    
    def validate_function(self, func_node, lines, violations):
        """Validate a function node for quality"""
        if hasattr(func_node, 'end_lineno'):
            func_length = func_node.end_lineno - func_node.lineno + 1
            if func_length > self.quality_rules['max_function_length']:
                violations.append(f"Function '{func_node.name}' too long ({func_length} lines)")
        
        # Check for docstring
        if not ast.get_docstring(func_node):
            violations.append(f"Function '{func_node.name}' missing docstring")
    
    def generate_report(self):
        """Generate a comprehensive report of agent activities"""
        print("\n" + "="*60)
        print("🔍 AGENT ACTIVITY & QUALITY MONITOR")
        print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        
        # Check each agent
        for agent_name, agent_data in self.agents.items():
            print(f"\n📌 {agent_name.upper()} AGENT:")
            
            # Get current activity
            activity = self.capture_agent_activity(agent_name)
            
            if activity and 'actions' in activity:
                if activity['actions']:
                    for action in activity['actions']:
                        icon = {
                            'editing': '✏️',
                            'reading': '👁️',
                            'running': '🏃',
                            'planning': '📋',
                            'error': '❌'
                        }.get(action['type'], '▶️')
                        print(f"  {icon} {action['type'].upper()}: {action['details']}")
                    
                    if activity.get('modifying_main_file'):
                        print(f"  ⚠️  MODIFYING MAIN FILE")
                else:
                    print(f"  💤 No recent activity detected")
            
            # Show violations
            if agent_data['violations']:
                print(f"  🚫 Quality Violations:")
                for violation in agent_data['violations'][-3:]:  # Last 3
                    print(f"     - {violation}")
        
        # Check file changes
        changes = self.check_file_changes()
        if changes:
            print(f"\n📝 FILE CHANGES DETECTED:")
            print(f"  ➕ Lines added: {changes['lines_added']}")
            print(f"  ➖ Lines removed: {changes['lines_removed']}")
            
            if changes['functions_added']:
                print(f"  🆕 New functions: {', '.join(changes['functions_added'])}")
            
            if changes['quality_violations']:
                print(f"\n  🚨 QUALITY VIOLATIONS IN NEW CODE:")
                for violation in changes['quality_violations'][:5]:
                    print(f"     ❌ {violation}")
                
                # Add violations to responsible agent (heuristic)
                for agent_name in self.agents:
                    if self.agents[agent_name]['last_activity'] and \
                       self.agents[agent_name]['last_activity'].get('modifying_main_file'):
                        self.agents[agent_name]['violations'].extend(changes['quality_violations'])
        
        # Overall health
        total_violations = sum(len(a['violations']) for a in self.agents.values())
        if total_violations == 0:
            print(f"\n✅ SYSTEM HEALTH: GOOD")
        elif total_violations < 5:
            print(f"\n⚠️  SYSTEM HEALTH: WARNING ({total_violations} violations)")
        else:
            print(f"\n🔴 SYSTEM HEALTH: CRITICAL ({total_violations} violations)")
        
        print("="*60)
    
    def enforce_quality_gates(self):
        """Actively prevent bad code from being committed"""
        changes = self.check_file_changes()
        
        if changes and changes['quality_violations']:
            print("\n🚫 QUALITY GATE FAILED!")
            print(f"Found {len(changes['quality_violations'])} violations")
            
            # Find responsible agent
            for agent_name, agent_data in self.agents.items():
                if agent_data['last_activity'] and \
                   agent_data['last_activity'].get('modifying_main_file'):
                    # Send warning to agent
                    window = agent_data['window']
                    warning = f"QUALITY GATE FAILED! Your changes have {len(changes['quality_violations'])} violations. FIX IMMEDIATELY!"
                    cmd = f'tmux send-keys -t {window} "{warning}" Enter'
                    subprocess.run(cmd, shell=True)
                    
                    print(f"⚠️  Warned {agent_name} agent about violations")
                    
                    # Log violations
                    with open('quality_violations.log', 'a') as f:
                        f.write(f"\n[{datetime.now()}] {agent_name}: {changes['quality_violations']}\n")
    
    def continuous_monitor(self, interval=30):
        """Run continuous monitoring"""
        print("🚀 Starting continuous agent monitoring...")
        print(f"⏰ Check interval: {interval} seconds")
        print("Press Ctrl+C to stop\n")
        
        try:
            while True:
                self.generate_report()
                self.enforce_quality_gates()
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n👋 Monitoring stopped")

if __name__ == "__main__":
    monitor = AgentActivityMonitor()
    monitor.continuous_monitor(30)  # Check every 30 seconds