#!/usr/bin/env python3
"""
Beverly ERP Agent Launcher
Deploys priority agents (Supply Chain, Inventory, ML) in tmux sessions
"""

import os
import sys
import time
import subprocess
import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BeverlyAgentLauncher:
    """Launcher for Beverly ERP agents in tmux sessions"""
    
    def __init__(self):
        self.tmux_session = "beverly-agents"
        self.agents = {
            "supply-chain": {
                "name": "Supply Chain Agent",
                "script": "supply_chain_agent.py",
                "priority": 1,
                "restart_on_fail": True
            },
            "inventory": {
                "name": "Inventory Agent", 
                "script": "inventory_agent.py",
                "priority": 1,
                "restart_on_fail": True
            },
            "ml-forecast": {
                "name": "ML Forecasting Agent",
                "script": "ml_forecast_agent.py", 
                "priority": 1,
                "restart_on_fail": True
            }
        }
        
    def check_tmux_session(self) -> bool:
        """Check if tmux session exists"""
        try:
            result = subprocess.run(
                ["tmux", "has-session", "-t", self.tmux_session],
                capture_output=True
            )
            return result.returncode == 0
        except:
            return False
            
    def create_tmux_session(self):
        """Create new tmux session"""
        if self.check_tmux_session():
            logger.info(f"Session {self.tmux_session} already exists")
            return
            
        subprocess.run([
            "tmux", "new-session", "-d", "-s", self.tmux_session,
            "-n", "orchestrator"
        ])
        logger.info(f"Created tmux session: {self.tmux_session}")
        
    def create_agent_window(self, window_name: str, agent_config: Dict):
        """Create tmux window for an agent"""
        # Create new window
        subprocess.run([
            "tmux", "new-window", "-t", f"{self.tmux_session}",
            "-n", window_name
        ])
        
        # Send commands to window
        commands = [
            "cd /mnt/c/Users/psytz/TMUX\\ Final/Agent-MCP",
            f"echo 'Starting {agent_config['name']}'",
            f"python3 agent_mcp/agents/{agent_config['script']}"
        ]
        
        for cmd in commands:
            subprocess.run([
                "tmux", "send-keys", "-t", f"{self.tmux_session}:{window_name}",
                cmd, "Enter"
            ])
            time.sleep(0.5)
            
        logger.info(f"Launched {agent_config['name']} in window {window_name}")
        
    def launch_all_agents(self):
        """Launch all priority agents"""
        self.create_tmux_session()
        
        for window_name, agent_config in self.agents.items():
            self.create_agent_window(window_name, agent_config)
            time.sleep(2)  # Allow time for agent to start
            
        # Create monitoring window
        subprocess.run([
            "tmux", "new-window", "-t", f"{self.tmux_session}",
            "-n", "monitor"
        ])
        
        monitor_commands = [
            "cd /mnt/c/Users/psytz/TMUX\\ Final/Agent-MCP",
            "echo 'Agent Monitoring Dashboard'",
            "python3 beverly_agent_monitor.py"
        ]
        
        for cmd in monitor_commands:
            subprocess.run([
                "tmux", "send-keys", "-t", f"{self.tmux_session}:monitor",
                cmd, "Enter"
            ])
            
        logger.info("All agents launched successfully")
        
    def attach_to_session(self):
        """Attach to tmux session"""
        subprocess.run(["tmux", "attach-session", "-t", self.tmux_session])
        
    def kill_session(self):
        """Kill tmux session"""
        if self.check_tmux_session():
            subprocess.run(["tmux", "kill-session", "-t", self.tmux_session])
            logger.info(f"Killed session {self.tmux_session}")

if __name__ == "__main__":
    launcher = BeverlyAgentLauncher()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "start":
            launcher.launch_all_agents()
            print(f"Agents launched. Attach with: tmux attach -t {launcher.tmux_session}")
            
        elif command == "stop":
            launcher.kill_session()
            print("All agents stopped")
            
        elif command == "attach":
            launcher.attach_to_session()
            
        elif command == "status":
            if launcher.check_tmux_session():
                print(f"Session {launcher.tmux_session} is running")
                subprocess.run(["tmux", "list-windows", "-t", launcher.tmux_session])
            else:
                print(f"Session {launcher.tmux_session} is not running")
    else:
        print("Usage: python beverly_agent_launcher.py [start|stop|attach|status]")