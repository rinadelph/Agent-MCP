#!/usr/bin/env python3
"""
Inventory Management Agent  
Priority #2 Agent for Beverly ERP System
Real-time inventory tracking, optimization, and predictive analytics
"""

import asyncio
import aiohttp
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
from collections import defaultdict
from dataclasses import dataclass, field

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("InventoryAgent")

@dataclass
class InventoryItem:
    """Inventory item tracking"""
    item_id: str
    description: str
    current_stock: float
    reorder_point: float
    safety_stock: float
    lead_time_days: int
    consumption_rate: float
    last_updated: datetime = field(default_factory=datetime.now)
    
    def days_until_stockout(self) -> float:
        """Calculate days until stockout at current consumption rate"""
        if self.consumption_rate > 0:
            return self.current_stock / self.consumption_rate
        return float('inf')
        
    def needs_reorder(self) -> bool:
        """Check if item needs reordering"""
        return self.current_stock <= self.reorder_point

class InventoryAgent:
    """
    Autonomous Inventory Management Agent
    Monitors stock levels, predicts demand, and optimizes inventory
    """
    
    def __init__(self, erp_url: str = "http://localhost:5003"):
        self.erp_url = erp_url
        self.session: Optional[aiohttp.ClientSession] = None
        self.running = False
        self.monitoring_interval = 60  # 1 minute for critical monitoring
        
        # Inventory tracking
        self.inventory: Dict[str, InventoryItem] = {}
        self.consumption_history: Dict[str, List[float]] = defaultdict(list)
        self.stockout_predictions: Dict[str, datetime] = {}
        
        # Alert thresholds
        self.critical_days = 3  # Days until stockout for critical alert
        self.warning_days = 7   # Days until stockout for warning
        
        # Performance metrics
        self.metrics = {
            "items_monitored": 0,
            "stockouts_prevented": 0,
            "reorders_triggered": 0,
            "inventory_turns": 0,
            "carrying_cost_saved": 0,
            "last_update": None
        }
        
        # ABC Analysis categories
        self.abc_categories = {
            "A": [],  # High value, tight control
            "B": [],  # Medium value, moderate control
            "C": []   # Low value, loose control
        }
        
    async def initialize(self):
        """Initialize agent resources"""
        self.session = aiohttp.ClientSession()
        self.running = True
        await self.load_inventory_data()
        logger.info("Inventory Agent initialized")
        
    async def shutdown(self):
        """Clean shutdown"""
        self.running = False
        if self.session:
            await self.session.close()
        logger.info("Inventory Agent shutdown")
        
    async def fetch_data(self, endpoint: str) -> Dict[str, Any]:
        """Fetch data from Beverly ERP API"""
        try:
            url = f"{self.erp_url}/api/{endpoint}"
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Failed to fetch {endpoint}: {response.status}")
                    return {}
        except Exception as e:
            logger.error(f"Error fetching data: {e}")
            return {}
            
    async def load_inventory_data(self):
        """Load initial inventory data"""
        yarn_data = await self.fetch_data("yarn")
        
        if yarn_data:
            yarns = yarn_data.get("yarns", [])
            for yarn in yarns:
                item_id = yarn.get("desc_num", "")
                if item_id:
                    self.inventory[item_id] = InventoryItem(
                        item_id=item_id,
                        description=yarn.get("description", ""),
                        current_stock=yarn.get("balance", 0),
                        reorder_point=1000,  # Default reorder point
                        safety_stock=500,     # Default safety stock
                        lead_time_days=21,    # 3 weeks default
                        consumption_rate=100  # Default daily consumption
                    )
            
            self.metrics["items_monitored"] = len(self.inventory)
            logger.info(f"Loaded {len(self.inventory)} inventory items")
            
    async def perform_abc_analysis(self) -> Dict[str, List[str]]:
        """
        Perform ABC analysis to categorize inventory items
        A: 20% of items, 80% of value
        B: 30% of items, 15% of value  
        C: 50% of items, 5% of value
        """
        # Calculate annual value for each item
        item_values = []
        for item_id, item in self.inventory.items():
            annual_consumption = item.consumption_rate * 365
            # Assume unit cost of $10 for simulation
            annual_value = annual_consumption * 10
            item_values.append((item_id, annual_value))
            
        # Sort by value
        item_values.sort(key=lambda x: x[1], reverse=True)
        total_value = sum(v for _, v in item_values)
        
        # Categorize items
        self.abc_categories = {"A": [], "B": [], "C": []}
        cumulative_value = 0
        
        for item_id, value in item_values:
            cumulative_value += value
            cumulative_percentage = cumulative_value / total_value if total_value > 0 else 0
            
            if cumulative_percentage <= 0.8:
                self.abc_categories["A"].append(item_id)
            elif cumulative_percentage <= 0.95:
                self.abc_categories["B"].append(item_id)
            else:
                self.abc_categories["C"].append(item_id)
                
        logger.info(f"ABC Analysis: A={len(self.abc_categories['A'])}, "
                   f"B={len(self.abc_categories['B'])}, C={len(self.abc_categories['C'])}")
        
        return self.abc_categories
        
    async def calculate_optimal_levels(self, item: InventoryItem) -> Tuple[float, float]:
        """
        Calculate optimal reorder point and safety stock
        Uses service level and demand variability
        """
        # Determine service level based on ABC category
        service_level_z = 2.33  # 99% for A items
        if item.item_id in self.abc_categories["B"]:
            service_level_z = 1.65  # 95% for B items
        elif item.item_id in self.abc_categories["C"]:
            service_level_z = 1.28  # 90% for C items
            
        # Calculate demand statistics
        if item.item_id in self.consumption_history:
            history = self.consumption_history[item.item_id]
            if len(history) > 7:
                avg_demand = np.mean(history)
                std_demand = np.std(history)
            else:
                avg_demand = item.consumption_rate
                std_demand = item.consumption_rate * 0.2  # 20% CV
        else:
            avg_demand = item.consumption_rate
            std_demand = item.consumption_rate * 0.2
            
        # Calculate safety stock
        lead_time_demand_std = std_demand * np.sqrt(item.lead_time_days)
        safety_stock = service_level_z * lead_time_demand_std
        
        # Calculate reorder point
        lead_time_demand = avg_demand * item.lead_time_days
        reorder_point = lead_time_demand + safety_stock
        
        return reorder_point, safety_stock
        
    async def predict_stockouts(self) -> List[Dict[str, Any]]:
        """
        Predict potential stockouts and generate alerts
        """
        predictions = []
        current_time = datetime.now()
        
        for item_id, item in self.inventory.items():
            days_to_stockout = item.days_until_stockout()
            
            if days_to_stockout < float('inf'):
                stockout_date = current_time + timedelta(days=days_to_stockout)
                self.stockout_predictions[item_id] = stockout_date
                
                # Determine alert severity
                if days_to_stockout <= self.critical_days:
                    severity = "CRITICAL"
                    action = "EMERGENCY_ORDER"
                elif days_to_stockout <= self.warning_days:
                    severity = "WARNING"
                    action = "EXPEDITE_ORDER"
                elif days_to_stockout <= item.lead_time_days:
                    severity = "ATTENTION"
                    action = "NORMAL_ORDER"
                else:
                    continue
                    
                predictions.append({
                    "item_id": item_id,
                    "description": item.description,
                    "current_stock": item.current_stock,
                    "consumption_rate": item.consumption_rate,
                    "days_to_stockout": round(days_to_stockout, 1),
                    "stockout_date": stockout_date.isoformat(),
                    "severity": severity,
                    "recommended_action": action,
                    "recommended_quantity": self.calculate_order_quantity(item)
                })
                
        # Sort by urgency
        predictions.sort(key=lambda x: x["days_to_stockout"])
        
        return predictions
        
    def calculate_order_quantity(self, item: InventoryItem) -> float:
        """
        Calculate optimal order quantity based on item category
        """
        # Base order quantity (days of supply)
        if item.item_id in self.abc_categories["A"]:
            days_supply = 30  # 1 month for A items
        elif item.item_id in self.abc_categories["B"]:
            days_supply = 60  # 2 months for B items
        else:
            days_supply = 90  # 3 months for C items
            
        order_quantity = item.consumption_rate * days_supply
        
        # Ensure minimum order covers safety stock
        min_order = item.reorder_point + item.safety_stock - item.current_stock
        
        return max(order_quantity, min_order)
        
    async def optimize_inventory_levels(self) -> Dict[str, Any]:
        """
        Optimize inventory levels across all items
        """
        optimization_results = {
            "timestamp": datetime.now().isoformat(),
            "items_optimized": 0,
            "reorder_recommendations": [],
            "excess_inventory": [],
            "estimated_savings": 0
        }
        
        # Perform ABC analysis
        await self.perform_abc_analysis()
        
        for item_id, item in self.inventory.items():
            # Calculate optimal levels
            optimal_reorder, optimal_safety = await self.calculate_optimal_levels(item)
            
            # Update item parameters
            item.reorder_point = optimal_reorder
            item.safety_stock = optimal_safety
            
            # Check if reorder needed
            if item.needs_reorder():
                order_qty = self.calculate_order_quantity(item)
                optimization_results["reorder_recommendations"].append({
                    "item_id": item_id,
                    "description": item.description,
                    "current_stock": item.current_stock,
                    "reorder_point": item.reorder_point,
                    "order_quantity": order_qty,
                    "category": self.get_item_category(item_id)
                })
                self.metrics["reorders_triggered"] += 1
                
            # Check for excess inventory
            max_stock = item.reorder_point + (item.consumption_rate * 90)  # 90 days max
            if item.current_stock > max_stock:
                excess = item.current_stock - max_stock
                excess_value = excess * 10  # $10 per unit assumption
                optimization_results["excess_inventory"].append({
                    "item_id": item_id,
                    "description": item.description,
                    "excess_quantity": excess,
                    "excess_value": excess_value,
                    "recommendation": "Reduce orders or liquidate excess"
                })
                optimization_results["estimated_savings"] += excess_value * 0.25  # 25% carrying cost
                
            optimization_results["items_optimized"] += 1
            
        self.metrics["carrying_cost_saved"] += optimization_results["estimated_savings"]
        
        return optimization_results
        
    def get_item_category(self, item_id: str) -> str:
        """Get ABC category for an item"""
        if item_id in self.abc_categories["A"]:
            return "A"
        elif item_id in self.abc_categories["B"]:
            return "B"
        else:
            return "C"
            
    async def update_consumption_rates(self):
        """
        Update consumption rates based on recent data
        Uses exponential smoothing for demand forecasting
        """
        # Fetch recent sales data
        sales_data = await self.fetch_data("sales")
        
        if sales_data:
            # Process sales to update consumption rates
            # This is simplified - in production would use actual sales data
            for item_id, item in self.inventory.items():
                # Simulate consumption data
                daily_consumption = np.random.normal(item.consumption_rate, item.consumption_rate * 0.1)
                daily_consumption = max(0, daily_consumption)
                
                # Add to history
                self.consumption_history[item_id].append(daily_consumption)
                
                # Keep only last 30 days
                if len(self.consumption_history[item_id]) > 30:
                    self.consumption_history[item_id] = self.consumption_history[item_id][-30:]
                    
                # Update consumption rate using exponential smoothing
                alpha = 0.3  # Smoothing factor
                item.consumption_rate = alpha * daily_consumption + (1 - alpha) * item.consumption_rate
                
                # Update stock (simulate consumption)
                item.current_stock = max(0, item.current_stock - daily_consumption)
                item.last_updated = datetime.now()
                
    async def calculate_inventory_kpis(self) -> Dict[str, Any]:
        """
        Calculate key inventory performance indicators
        """
        total_value = sum(item.current_stock * 10 for item in self.inventory.values())
        total_consumption = sum(item.consumption_rate * 365 for item in self.inventory.values())
        
        # Calculate inventory turnover
        if total_value > 0:
            inventory_turns = (total_consumption * 10) / total_value
        else:
            inventory_turns = 0
            
        self.metrics["inventory_turns"] = inventory_turns
        
        # Calculate other KPIs
        kpis = {
            "total_inventory_value": total_value,
            "inventory_turnover": round(inventory_turns, 2),
            "average_days_on_hand": round(365 / max(inventory_turns, 1), 1),
            "stockout_risk_items": len([i for i in self.inventory.values() if i.days_until_stockout() < 7]),
            "excess_inventory_value": sum(
                max(0, (item.current_stock - item.reorder_point * 2) * 10)
                for item in self.inventory.values()
            ),
            "service_level": self.calculate_service_level(),
            "carrying_cost": total_value * 0.25,  # 25% annual carrying cost
            "abc_distribution": {
                "A_items": len(self.abc_categories["A"]),
                "B_items": len(self.abc_categories["B"]),
                "C_items": len(self.abc_categories["C"])
            }
        }
        
        return kpis
        
    def calculate_service_level(self) -> float:
        """Calculate overall service level (% of items above safety stock)"""
        if not self.inventory:
            return 0
            
        items_above_safety = sum(
            1 for item in self.inventory.values()
            if item.current_stock > item.safety_stock
        )
        
        return (items_above_safety / len(self.inventory)) * 100
        
    async def run_continuous_monitoring(self):
        """
        Main loop for continuous inventory monitoring
        """
        logger.info("Starting continuous inventory monitoring")
        
        cycle_count = 0
        
        while self.running:
            try:
                cycle_count += 1
                
                # Update consumption rates
                await self.update_consumption_rates()
                
                # Predict stockouts
                stockout_predictions = await self.predict_stockouts()
                
                # Log critical alerts
                critical_items = [p for p in stockout_predictions if p["severity"] == "CRITICAL"]
                if critical_items:
                    logger.warning(f"CRITICAL STOCKOUT RISK: {len(critical_items)} items")
                    for item in critical_items[:5]:
                        logger.warning(f"  - {item['description']}: {item['days_to_stockout']} days remaining")
                        
                # Every 10 cycles, run full optimization
                if cycle_count % 10 == 0:
                    optimization_results = await self.optimize_inventory_levels()
                    logger.info(f"Optimization complete: {optimization_results['items_optimized']} items, "
                               f"{len(optimization_results['reorder_recommendations'])} reorders needed")
                    
                    # Calculate and log KPIs
                    kpis = await self.calculate_inventory_kpis()
                    logger.info(f"Inventory KPIs: Turnover={kpis['inventory_turnover']}x, "
                               f"Service Level={kpis['service_level']:.1f}%")
                    
                # Update metrics
                self.metrics["last_update"] = datetime.now().isoformat()
                
                # Log performance metrics every 5 cycles
                if cycle_count % 5 == 0:
                    logger.info(f"Performance Metrics: {json.dumps(self.metrics, indent=2)}")
                    
                # Wait for next cycle
                await asyncio.sleep(self.monitoring_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(30)  # Short delay on error
                
    async def handle_urgent_restock(self, item_id: str, trigger_reason: str) -> Dict[str, Any]:
        """
        Handle urgent restock requests
        """
        logger.info(f"Urgent restock triggered for {item_id}: {trigger_reason}")
        
        if item_id not in self.inventory:
            return {"error": f"Item {item_id} not found in inventory"}
            
        item = self.inventory[item_id]
        
        # Calculate emergency order quantity
        emergency_qty = self.calculate_order_quantity(item) * 1.5  # 50% buffer for emergency
        
        # Generate emergency restock order
        restock_order = {
            "order_id": f"RESTOCK-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "item_id": item_id,
            "description": item.description,
            "current_stock": item.current_stock,
            "order_quantity": emergency_qty,
            "order_type": "EMERGENCY",
            "trigger_reason": trigger_reason,
            "expected_delivery": (datetime.now() + timedelta(days=7)).isoformat(),
            "priority": "HIGHEST"
        }
        
        # Update metrics
        self.metrics["stockouts_prevented"] += 1
        
        logger.info(f"Emergency restock order generated: {restock_order['order_id']}")
        
        return restock_order

# Main execution
async def main():
    """Main entry point for Inventory Agent"""
    agent = InventoryAgent()
    
    try:
        await agent.initialize()
        
        # Start continuous monitoring
        await agent.run_continuous_monitoring()
        
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    finally:
        await agent.shutdown()

if __name__ == "__main__":
    print("=" * 60)
    print("BEVERLY ERP - INVENTORY MANAGEMENT AGENT")
    print("Priority Level: #2")
    print("=" * 60)
    print("Agent Status: INITIALIZING...")
    
    asyncio.run(main())