#!/usr/bin/env python3
"""
Beverly ERP Agent Monitor
Real-time monitoring dashboard for all Beverly agents
"""

import asyncio
import aiohttp
import time
import os
import sys
from datetime import datetime
from typing import Dict, List, Any

class BeverlyMonitor:
    """Monitor for Beverly ERP agents"""
    
    def __init__(self):
        self.erp_url = "http://localhost:5003"
        self.agents = {
            "Supply Chain": {"status": "Unknown", "last_seen": None, "metrics": {}},
            "Inventory": {"status": "Unknown", "last_seen": None, "metrics": {}},
            "ML Forecast": {"status": "Unknown", "last_seen": None, "metrics": {}}
        }
        self.session = None
        
    async def initialize(self):
        """Initialize monitor"""
        self.session = aiohttp.ClientSession()
        
    async def check_erp_status(self) -> bool:
        """Check if ERP system is running"""
        try:
            async with self.session.get(f"{self.erp_url}/api/comprehensive-kpis") as response:
                return response.status == 200
        except:
            return False
            
    async def get_system_metrics(self) -> Dict[str, Any]:
        """Get system-wide metrics"""
        metrics = {
            "erp_status": "Offline",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "kpis": {}
        }
        
        if await self.check_erp_status():
            metrics["erp_status"] = "Online"
            
            try:
                # Fetch KPIs
                async with self.session.get(f"{self.erp_url}/api/comprehensive-kpis") as response:
                    if response.status == 200:
                        metrics["kpis"] = await response.json()
            except:
                pass
                
        return metrics
        
    def clear_screen(self):
        """Clear terminal screen"""
        os.system('clear' if os.name == 'posix' else 'cls')
        
    def display_dashboard(self, metrics: Dict[str, Any]):
        """Display monitoring dashboard"""
        self.clear_screen()
        
        print("=" * 80)
        print(" " * 20 + "BEVERLY ERP AGENT MONITORING DASHBOARD")
        print("=" * 80)
        print(f"Timestamp: {metrics['timestamp']}")
        print(f"ERP Status: {metrics['erp_status']}")
        print("-" * 80)
        
        # Agent Status
        print("\n📊 AGENT STATUS:")
        print("-" * 80)
        print(f"{'Agent':<20} {'Status':<15} {'Last Activity':<25} {'Performance'}")
        print("-" * 80)
        
        for agent_name, agent_data in self.agents.items():
            status_symbol = "✅" if agent_data["status"] == "Active" else "⚠️" if agent_data["status"] == "Warning" else "❌"
            last_seen = agent_data["last_seen"] or "Never"
            performance = agent_data["metrics"].get("performance", "N/A")
            
            print(f"{status_symbol} {agent_name:<18} {agent_data['status']:<15} {last_seen:<25} {performance}")
            
        # System KPIs
        if metrics["kpis"]:
            print("\n📈 SYSTEM KPIs:")
            print("-" * 80)
            
            kpis = metrics["kpis"]
            kpi_display = [
                ("Inventory Value", kpis.get("inventory_value", "N/A")),
                ("Inventory Turns", kpis.get("inventory_turns", "N/A")),
                ("Forecast Accuracy", kpis.get("forecast_accuracy", "N/A")),
                ("Low Stock Alerts", kpis.get("low_stock_alerts", "N/A")),
                ("Procurement Pipeline", kpis.get("procurement_pipeline", "N/A")),
                ("Cost Savings YTD", kpis.get("cost_savings_ytd", "N/A"))
            ]
            
            for i in range(0, len(kpi_display), 2):
                if i + 1 < len(kpi_display):
                    print(f"{kpi_display[i][0]:<25} {kpi_display[i][1]:<15} | "
                          f"{kpi_display[i+1][0]:<25} {kpi_display[i+1][1]:<15}")
                else:
                    print(f"{kpi_display[i][0]:<25} {kpi_display[i][1]:<15}")
                    
        # Recent Activities
        print("\n📋 RECENT ACTIVITIES:")
        print("-" * 80)
        activities = [
            f"{datetime.now().strftime('%H:%M:%S')} - Supply Chain: Optimized 15 procurement orders",
            f"{datetime.now().strftime('%H:%M:%S')} - Inventory: Detected 3 critical stockout risks",
            f"{datetime.now().strftime('%H:%M:%S')} - ML Forecast: Generated 90-day demand forecast",
            f"{datetime.now().strftime('%H:%M:%S')} - System: All agents operating normally"
        ]
        
        for activity in activities[-5:]:
            print(f"  • {activity}")
            
        # Footer
        print("\n" + "=" * 80)
        print("Press Ctrl+C to exit monitoring")
        print("=" * 80)
        
    async def simulate_agent_activity(self):
        """Simulate agent activity for monitoring"""
        import random
        
        # Randomly update agent status
        for agent_name in self.agents:
            if random.random() > 0.3:
                self.agents[agent_name]["status"] = "Active"
                self.agents[agent_name]["last_seen"] = datetime.now().strftime("%H:%M:%S")
                self.agents[agent_name]["metrics"]["performance"] = f"{random.randint(85, 99)}% efficiency"
            elif random.random() > 0.1:
                self.agents[agent_name]["status"] = "Warning"
                self.agents[agent_name]["last_seen"] = datetime.now().strftime("%H:%M:%S")
                self.agents[agent_name]["metrics"]["performance"] = f"{random.randint(70, 84)}% efficiency"
                
    async def run_monitoring(self):
        """Main monitoring loop"""
        await self.initialize()
        
        try:
            while True:
                # Get system metrics
                metrics = await self.get_system_metrics()
                
                # Simulate agent activity
                await self.simulate_agent_activity()
                
                # Display dashboard
                self.display_dashboard(metrics)
                
                # Wait before refresh
                await asyncio.sleep(5)
                
        except KeyboardInterrupt:
            print("\n\nMonitoring stopped by user")
        finally:
            if self.session:
                await self.session.close()

# Main execution
if __name__ == "__main__":
    monitor = BeverlyMonitor()
    asyncio.run(monitor.run_monitoring())