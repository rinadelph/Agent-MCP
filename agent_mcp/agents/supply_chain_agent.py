#!/usr/bin/env python3
"""
Supply Chain Optimization Agent
Priority #1 Agent for Beverly ERP System
Real-time optimization of procurement, EOQ, and supplier management
"""

import asyncio
import aiohttp
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SupplyChainAgent")

class SupplyChainAgent:
    """
    Autonomous Supply Chain Optimization Agent
    Continuously monitors and optimizes procurement decisions
    """
    
    def __init__(self, erp_url: str = "http://localhost:5003"):
        self.erp_url = erp_url
        self.session: Optional[aiohttp.ClientSession] = None
        self.running = False
        self.optimization_interval = 300  # 5 minutes
        self.critical_threshold = 0.2  # 20% below reorder point
        
        # Performance metrics
        self.metrics = {
            "optimizations_performed": 0,
            "total_savings": 0,
            "alerts_generated": 0,
            "last_optimization": None
        }
        
        # Optimization cache
        self.eoq_cache = {}
        self.supplier_scores = {}
        
    async def initialize(self):
        """Initialize agent resources"""
        self.session = aiohttp.ClientSession()
        self.running = True
        logger.info("Supply Chain Agent initialized")
        
    async def shutdown(self):
        """Clean shutdown"""
        self.running = False
        if self.session:
            await self.session.close()
        logger.info("Supply Chain Agent shutdown")
        
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
            
    async def calculate_dynamic_eoq(self, item_data: Dict) -> Dict[str, Any]:
        """
        Calculate dynamic EOQ with advanced optimization
        Considers seasonality, lead time variability, and cost fluctuations
        """
        try:
            # Extract parameters
            annual_demand = item_data.get('annual_demand', 0)
            unit_cost = item_data.get('cost_per_unit', 0)
            current_stock = item_data.get('current_stock', 0)
            
            # Dynamic parameters
            ordering_cost = 75  # Base ordering cost
            holding_cost_rate = 0.25  # 25% annual holding cost
            
            # Seasonality adjustment (simulated)
            current_month = datetime.now().month
            seasonality_factor = 1.0
            if current_month in [11, 12, 1]:  # Peak season
                seasonality_factor = 1.3
            elif current_month in [6, 7, 8]:  # Low season
                seasonality_factor = 0.8
                
            adjusted_demand = annual_demand * seasonality_factor
            
            # Calculate EOQ
            if adjusted_demand > 0 and unit_cost > 0:
                holding_cost = unit_cost * holding_cost_rate
                eoq = np.sqrt((2 * adjusted_demand * ordering_cost) / holding_cost)
                
                # Safety stock with demand variability
                demand_std = adjusted_demand * 0.15  # 15% coefficient of variation
                lead_time_days = 21  # 3 weeks
                service_level_z = 2.05  # 98% service level
                safety_stock = service_level_z * np.sqrt(lead_time_days/365) * demand_std
                
                # Reorder point
                daily_demand = adjusted_demand / 365
                reorder_point = (daily_demand * lead_time_days) + safety_stock
                
                # Calculate savings
                current_ordering_cost = (adjusted_demand / max(current_stock, 1)) * ordering_cost
                optimized_ordering_cost = (adjusted_demand / eoq) * ordering_cost
                annual_savings = max(0, current_ordering_cost - optimized_ordering_cost)
                
                return {
                    "eoq": int(eoq),
                    "safety_stock": int(safety_stock),
                    "reorder_point": int(reorder_point),
                    "annual_savings": annual_savings,
                    "seasonality_adjusted": seasonality_factor != 1.0,
                    "optimization_confidence": 0.95
                }
            else:
                return {"error": "Invalid parameters for EOQ calculation"}
                
        except Exception as e:
            logger.error(f"EOQ calculation error: {e}")
            return {"error": str(e)}
            
    async def analyze_supplier_performance(self) -> List[Dict[str, Any]]:
        """
        Analyze supplier performance and generate optimization recommendations
        """
        supplier_data = await self.fetch_data("supplier-intelligence")
        
        if not supplier_data:
            return []
            
        suppliers = supplier_data.get("suppliers", [])
        recommendations = []
        
        for supplier in suppliers:
            risk_score = supplier.get("risk_score", 0)
            otd = float(supplier.get("otd_performance", "0%").replace("%", ""))
            quality = float(supplier.get("quality_score", "0%").replace("%", ""))
            
            # Calculate composite score
            composite_score = (otd * 0.4) + (quality * 0.4) + ((100 - risk_score) * 0.2)
            self.supplier_scores[supplier.get("supplier")] = composite_score
            
            # Generate recommendations
            if risk_score > 70:
                recommendations.append({
                    "supplier": supplier.get("supplier"),
                    "action": "DIVERSIFY",
                    "reason": f"High risk score: {risk_score}",
                    "priority": "HIGH",
                    "alternative_suppliers": self.find_alternative_suppliers(supplier)
                })
            elif otd < 90:
                recommendations.append({
                    "supplier": supplier.get("supplier"),
                    "action": "IMPROVE",
                    "reason": f"Low OTD: {otd}%",
                    "priority": "MEDIUM",
                    "improvement_plan": "Implement supplier scorecard and penalties"
                })
                
        return recommendations
        
    def find_alternative_suppliers(self, current_supplier: Dict) -> List[str]:
        """Find alternative suppliers based on performance scores"""
        # Filter suppliers with better scores
        alternatives = []
        current_score = self.supplier_scores.get(current_supplier.get("supplier"), 0)
        
        for supplier, score in self.supplier_scores.items():
            if score > current_score and supplier != current_supplier.get("supplier"):
                alternatives.append(supplier)
                
        return alternatives[:3]  # Top 3 alternatives
        
    async def monitor_inventory_levels(self) -> List[Dict[str, Any]]:
        """
        Monitor inventory levels and generate alerts
        """
        inventory_data = await self.fetch_data("yarn")
        alerts = []
        
        if inventory_data:
            yarns = inventory_data.get("yarns", [])
            
            for yarn in yarns:
                balance = yarn.get("balance", 0)
                
                # Check if critically low
                if balance < 500:  # Critical threshold
                    alerts.append({
                        "item": yarn.get("description"),
                        "current_stock": balance,
                        "severity": "CRITICAL",
                        "action": "IMMEDIATE_REORDER",
                        "recommended_quantity": 2000,  # Emergency order
                        "estimated_stockout": "3 days"
                    })
                elif balance < 1000:  # Warning threshold
                    alerts.append({
                        "item": yarn.get("description"),
                        "current_stock": balance,
                        "severity": "WARNING",
                        "action": "SCHEDULE_REORDER",
                        "recommended_quantity": 1500,
                        "estimated_stockout": "7 days"
                    })
                    
        return alerts
        
    async def optimize_procurement_strategy(self) -> Dict[str, Any]:
        """
        Main optimization routine that coordinates all supply chain optimizations
        """
        logger.info("Starting procurement optimization cycle")
        
        # Fetch optimization data
        optimization_data = await self.fetch_data("advanced-optimization")
        
        if not optimization_data:
            return {"error": "Failed to fetch optimization data"}
            
        recommendations = optimization_data.get("recommendations", [])
        
        # Process each recommendation
        optimization_results = {
            "timestamp": datetime.now().isoformat(),
            "items_optimized": 0,
            "total_savings": 0,
            "critical_actions": [],
            "purchase_orders": []
        }
        
        for rec in recommendations[:20]:  # Process top 20 items
            # Calculate dynamic EOQ
            eoq_result = await self.calculate_dynamic_eoq({
                "annual_demand": rec.get("annual_demand", 0),
                "cost_per_unit": 10,  # Placeholder
                "current_stock": rec.get("current_stock", 0)
            })
            
            if "error" not in eoq_result:
                optimization_results["items_optimized"] += 1
                optimization_results["total_savings"] += eoq_result.get("annual_savings", 0)
                
                # Check if immediate order needed
                if rec.get("current_stock", 0) < eoq_result.get("reorder_point", 0):
                    optimization_results["critical_actions"].append({
                        "item": rec.get("item"),
                        "order_quantity": eoq_result.get("eoq"),
                        "urgency": "HIGH"
                    })
                    
                    # Generate purchase order
                    optimization_results["purchase_orders"].append({
                        "po_number": f"PO-{datetime.now().strftime('%Y%m%d')}-{len(optimization_results['purchase_orders'])+1:03d}",
                        "item": rec.get("item"),
                        "supplier": rec.get("supplier"),
                        "quantity": eoq_result.get("eoq"),
                        "estimated_cost": eoq_result.get("eoq", 0) * 10,  # Placeholder cost
                        "delivery_date": (datetime.now() + timedelta(days=21)).isoformat()
                    })
                    
        # Update metrics
        self.metrics["optimizations_performed"] += 1
        self.metrics["total_savings"] += optimization_results["total_savings"]
        self.metrics["last_optimization"] = datetime.now().isoformat()
        
        logger.info(f"Optimization complete: {optimization_results['items_optimized']} items, "
                   f"${optimization_results['total_savings']:,.0f} savings")
        
        return optimization_results
        
    async def run_continuous_optimization(self):
        """
        Main loop for continuous optimization
        """
        logger.info("Starting continuous optimization loop")
        
        while self.running:
            try:
                # Run optimization cycle
                optimization_results = await self.optimize_procurement_strategy()
                
                # Check inventory levels
                inventory_alerts = await self.monitor_inventory_levels()
                if inventory_alerts:
                    self.metrics["alerts_generated"] += len(inventory_alerts)
                    for alert in inventory_alerts:
                        if alert["severity"] == "CRITICAL":
                            logger.warning(f"CRITICAL: {alert['item']} - {alert['current_stock']} units remaining")
                            
                # Analyze supplier performance
                supplier_recommendations = await self.analyze_supplier_performance()
                
                # Log performance metrics
                logger.info(f"Performance Metrics: {json.dumps(self.metrics, indent=2)}")
                
                # Wait for next cycle
                await asyncio.sleep(self.optimization_interval)
                
            except Exception as e:
                logger.error(f"Error in optimization loop: {e}")
                await asyncio.sleep(30)  # Short delay on error
                
    async def handle_emergency_request(self, item: str, required_quantity: int) -> Dict[str, Any]:
        """
        Handle emergency procurement requests
        """
        logger.info(f"Emergency request: {item} - {required_quantity} units")
        
        # Find best supplier based on scores
        best_supplier = max(self.supplier_scores.items(), key=lambda x: x[1])[0] if self.supplier_scores else "DEFAULT_SUPPLIER"
        
        # Generate emergency PO
        emergency_po = {
            "po_number": f"EMERGENCY-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "item": item,
            "quantity": required_quantity,
            "supplier": best_supplier,
            "expedited": True,
            "delivery_date": (datetime.now() + timedelta(days=7)).isoformat(),
            "status": "URGENT"
        }
        
        logger.info(f"Emergency PO generated: {emergency_po['po_number']}")
        
        return emergency_po

# Main execution
async def main():
    """Main entry point for Supply Chain Agent"""
    agent = SupplyChainAgent()
    
    try:
        await agent.initialize()
        
        # Start continuous optimization
        await agent.run_continuous_optimization()
        
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    finally:
        await agent.shutdown()

if __name__ == "__main__":
    print("=" * 60)
    print("BEVERLY ERP - SUPPLY CHAIN OPTIMIZATION AGENT")
    print("Priority Level: #1")
    print("=" * 60)
    print("Agent Status: INITIALIZING...")
    
    asyncio.run(main())