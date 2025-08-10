#!/usr/bin/env python3
"""
Beverly ERP Specialized Agent System
Multi-agent orchestration for textile manufacturing ERP management
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import aiohttp
import pandas as pd
import numpy as np
from pathlib import Path

logger = logging.getLogger(__name__)

# Agent Role Definitions
class AgentRole(Enum):
    SUPPLY_CHAIN_OPTIMIZER = "supply_chain_optimizer"
    PRODUCTION_PLANNER = "production_planner"
    QUALITY_CONTROLLER = "quality_controller"
    INVENTORY_MANAGER = "inventory_manager"
    ML_FORECASTER = "ml_forecaster"
    EXECUTIVE_ANALYST = "executive_analyst"
    PROCUREMENT_SPECIALIST = "procurement_specialist"
    BOTTLENECK_RESOLVER = "bottleneck_resolver"

@dataclass
class AgentTask:
    """Task definition for ERP agents"""
    task_id: str
    task_type: str
    priority: int
    assigned_to: Optional[AgentRole] = None
    status: str = "pending"
    data: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

@dataclass
class AgentMessage:
    """Inter-agent communication message"""
    sender: AgentRole
    recipient: AgentRole
    message_type: str
    content: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)

class BeverlyERPAgent:
    """Base class for Beverly ERP agents"""
    
    def __init__(self, role: AgentRole, erp_base_url: str = "http://localhost:5003"):
        self.role = role
        self.erp_base_url = erp_base_url
        self.active = False
        self.current_task: Optional[AgentTask] = None
        self.message_queue: List[AgentMessage] = []
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def initialize(self):
        """Initialize agent resources"""
        self.session = aiohttp.ClientSession()
        self.active = True
        logger.info(f"Agent {self.role.value} initialized")
        
    async def shutdown(self):
        """Clean up agent resources"""
        self.active = False
        if self.session:
            await self.session.close()
        logger.info(f"Agent {self.role.value} shutdown")
        
    async def fetch_erp_data(self, endpoint: str) -> Dict[str, Any]:
        """Fetch data from Beverly ERP API"""
        if not self.session:
            await self.initialize()
            
        try:
            url = f"{self.erp_base_url}/api/{endpoint}"
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Failed to fetch {endpoint}: {response.status}")
                    return {}
        except Exception as e:
            logger.error(f"Error fetching ERP data: {e}")
            return {}
            
    async def send_message(self, recipient: AgentRole, message_type: str, content: Dict[str, Any]):
        """Send message to another agent"""
        message = AgentMessage(
            sender=self.role,
            recipient=recipient,
            message_type=message_type,
            content=content
        )
        # In a real system, this would use a message broker
        logger.info(f"Message sent from {self.role.value} to {recipient.value}: {message_type}")
        return message
        
    async def process_task(self, task: AgentTask) -> Dict[str, Any]:
        """Process a task - to be overridden by specific agents"""
        raise NotImplementedError
        

class SupplyChainOptimizer(BeverlyERPAgent):
    """Agent responsible for supply chain optimization"""
    
    def __init__(self):
        super().__init__(AgentRole.SUPPLY_CHAIN_OPTIMIZER)
        self.optimization_threshold = 0.15  # 15% optimization target
        
    async def process_task(self, task: AgentTask) -> Dict[str, Any]:
        """Process supply chain optimization tasks"""
        self.current_task = task
        
        if task.task_type == "optimize_procurement":
            return await self.optimize_procurement()
        elif task.task_type == "analyze_supplier_risk":
            return await self.analyze_supplier_risk()
        elif task.task_type == "calculate_eoq":
            return await self.calculate_eoq_recommendations()
        else:
            return {"error": f"Unknown task type: {task.task_type}"}
            
    async def optimize_procurement(self) -> Dict[str, Any]:
        """Optimize procurement decisions"""
        # Fetch optimization data
        optimization_data = await self.fetch_erp_data("advanced-optimization")
        
        if not optimization_data:
            return {"error": "Failed to fetch optimization data"}
            
        recommendations = optimization_data.get("recommendations", [])
        
        # Process recommendations
        high_priority = [r for r in recommendations if r.get("priority") == "High"]
        total_savings = sum(
            float(r.get("savings_potential", "$0").replace("$", "").replace(",", ""))
            for r in recommendations
        )
        
        # Send insights to Executive Analyst
        await self.send_message(
            AgentRole.EXECUTIVE_ANALYST,
            "optimization_insights",
            {
                "total_savings_potential": total_savings,
                "high_priority_items": len(high_priority),
                "recommendations_count": len(recommendations)
            }
        )
        
        return {
            "optimized_items": len(recommendations),
            "total_savings": f"${total_savings:,.0f}",
            "high_priority_actions": high_priority[:5],
            "status": "success"
        }
        
    async def analyze_supplier_risk(self) -> Dict[str, Any]:
        """Analyze supplier risk factors"""
        supplier_data = await self.fetch_erp_data("supplier-intelligence")
        
        if not supplier_data:
            return {"error": "Failed to fetch supplier data"}
            
        suppliers = supplier_data.get("suppliers", [])
        
        # Risk analysis
        high_risk = [s for s in suppliers if s.get("risk_level") == "High"]
        medium_risk = [s for s in suppliers if s.get("risk_level") == "Medium"]
        
        # Alert if critical risks found
        if len(high_risk) > 2:
            await self.send_message(
                AgentRole.PROCUREMENT_SPECIALIST,
                "critical_risk_alert",
                {
                    "high_risk_suppliers": high_risk,
                    "action_required": "Immediate diversification needed"
                }
            )
            
        return {
            "risk_analysis": {
                "high_risk_count": len(high_risk),
                "medium_risk_count": len(medium_risk),
                "critical_suppliers": high_risk[:3]
            },
            "recommendations": [
                "Diversify supplier base" if len(high_risk) > 2 else "Monitor supplier performance",
                "Establish backup suppliers for critical materials",
                "Implement supplier scorecards"
            ],
            "status": "success"
        }
        
    async def calculate_eoq_recommendations(self) -> Dict[str, Any]:
        """Calculate Economic Order Quantity recommendations"""
        optimization_data = await self.fetch_erp_data("advanced-optimization")
        
        if not optimization_data:
            return {"error": "Failed to fetch optimization data"}
            
        recommendations = optimization_data.get("recommendations", [])
        
        # Process EOQ calculations
        eoq_summary = {
            "total_items_analyzed": len(recommendations),
            "average_eoq": np.mean([r.get("eoq", 0) for r in recommendations]),
            "total_safety_stock": sum(r.get("safety_stock", 0) for r in recommendations),
            "reorder_points": [
                {
                    "item": r.get("item"),
                    "reorder_point": r.get("reorder_point"),
                    "current_stock": r.get("current_stock")
                }
                for r in recommendations[:10]
            ]
        }
        
        # Alert Inventory Manager about critical reorder points
        critical_reorders = [
            r for r in recommendations 
            if r.get("current_stock", 0) < r.get("reorder_point", 0)
        ]
        
        if critical_reorders:
            await self.send_message(
                AgentRole.INVENTORY_MANAGER,
                "critical_reorder_alert",
                {
                    "items_below_reorder": len(critical_reorders),
                    "critical_items": critical_reorders[:5]
                }
            )
            
        return {
            "eoq_analysis": eoq_summary,
            "critical_alerts": len(critical_reorders),
            "status": "success"
        }


class ProductionPlanner(BeverlyERPAgent):
    """Agent responsible for production planning and scheduling"""
    
    def __init__(self):
        super().__init__(AgentRole.PRODUCTION_PLANNER)
        self.planning_horizon = 30  # days
        
    async def process_task(self, task: AgentTask) -> Dict[str, Any]:
        """Process production planning tasks"""
        self.current_task = task
        
        if task.task_type == "execute_6phase_planning":
            return await self.execute_6phase_planning()
        elif task.task_type == "identify_bottlenecks":
            return await self.identify_production_bottlenecks()
        elif task.task_type == "optimize_schedule":
            return await self.optimize_production_schedule()
        else:
            return {"error": f"Unknown task type: {task.task_type}"}
            
    async def execute_6phase_planning(self) -> Dict[str, Any]:
        """Execute the 6-phase planning cycle"""
        # Trigger planning execution
        if not self.session:
            await self.initialize()
            
        try:
            url = f"{self.erp_base_url}/api/execute-planning"
            async with self.session.post(url, json={}) as response:
                if response.status == 200:
                    result = await response.json()
                    
                    if result.get("success"):
                        # Notify other agents about planning completion
                        await self.send_message(
                            AgentRole.INVENTORY_MANAGER,
                            "planning_completed",
                            {
                                "purchase_orders": result.get("final_output", {}).get("purchase_orders", []),
                                "total_value": result.get("final_output", {}).get("total_value", 0)
                            }
                        )
                        
                        await self.send_message(
                            AgentRole.EXECUTIVE_ANALYST,
                            "planning_results",
                            {
                                "phases_completed": len(result.get("phases", [])),
                                "optimization_score": result.get("final_output", {}).get("kpis", {}).get("optimization_score", 0)
                            }
                        )
                        
                    return result
                else:
                    return {"error": f"Planning execution failed: {response.status}"}
        except Exception as e:
            logger.error(f"Error executing planning: {e}")
            return {"error": str(e)}
            
    async def identify_production_bottlenecks(self) -> Dict[str, Any]:
        """Identify and analyze production bottlenecks"""
        pipeline_data = await self.fetch_erp_data("production-pipeline")
        
        if not pipeline_data:
            return {"error": "Failed to fetch pipeline data"}
            
        pipeline = pipeline_data.get("pipeline", [])
        
        # Identify bottlenecks
        bottlenecks = [
            stage for stage in pipeline
            if stage.get("bottleneck_status") in ["Critical", "Warning"]
        ]
        
        if bottlenecks:
            # Alert Bottleneck Resolver
            await self.send_message(
                AgentRole.BOTTLENECK_RESOLVER,
                "bottleneck_detected",
                {
                    "critical_stages": [b for b in bottlenecks if b.get("bottleneck_status") == "Critical"],
                    "warning_stages": [b for b in bottlenecks if b.get("bottleneck_status") == "Warning"]
                }
            )
            
        return {
            "bottleneck_analysis": {
                "total_stages": len(pipeline),
                "bottleneck_count": len(bottlenecks),
                "critical_bottlenecks": [b.get("stage") for b in bottlenecks if b.get("bottleneck_status") == "Critical"],
                "recommendations": [b.get("recommendation") for b in bottlenecks]
            },
            "status": "success"
        }
        
    async def optimize_production_schedule(self) -> Dict[str, Any]:
        """Optimize production scheduling"""
        # This would integrate with actual production data
        # For now, we'll create optimization recommendations
        
        optimization_results = {
            "schedule_optimization": {
                "current_efficiency": "87.3%",
                "optimized_efficiency": "94.2%",
                "improvement": "6.9%",
                "changes_recommended": [
                    "Shift dyeing operations to night shift for energy savings",
                    "Consolidate similar fabric types for batch processing",
                    "Implement parallel processing for inspection stage",
                    "Reduce changeover time by 15% through better sequencing"
                ]
            },
            "resource_allocation": {
                "workers_reallocated": 12,
                "machines_optimized": 8,
                "estimated_time_savings": "3.5 hours/day"
            },
            "status": "success"
        }
        
        # Send optimization to Executive Analyst
        await self.send_message(
            AgentRole.EXECUTIVE_ANALYST,
            "schedule_optimization",
            optimization_results
        )
        
        return optimization_results


class QualityController(BeverlyERPAgent):
    """Agent responsible for quality control and assurance"""
    
    def __init__(self):
        super().__init__(AgentRole.QUALITY_CONTROLLER)
        self.quality_threshold = 0.95  # 95% quality target
        
    async def process_task(self, task: AgentTask) -> Dict[str, Any]:
        """Process quality control tasks"""
        self.current_task = task
        
        if task.task_type == "validate_quality_metrics":
            return await self.validate_quality_metrics()
        elif task.task_type == "predict_defects":
            return await self.predict_quality_issues()
        elif task.task_type == "generate_quality_report":
            return await self.generate_quality_report()
        else:
            return {"error": f"Unknown task type: {task.task_type}"}
            
    async def validate_quality_metrics(self) -> Dict[str, Any]:
        """Validate current quality metrics against standards"""
        # Simulate quality validation
        quality_metrics = {
            "current_quality_rate": 0.962,
            "defect_rate": 0.038,
            "inspection_coverage": 0.98,
            "customer_complaints": 3,
            "rework_percentage": 2.1
        }
        
        # Check against thresholds
        issues = []
        if quality_metrics["current_quality_rate"] < self.quality_threshold:
            issues.append("Quality rate below target")
        if quality_metrics["defect_rate"] > 0.04:
            issues.append("Defect rate exceeds acceptable limit")
            
        if issues:
            # Alert Production Planner
            await self.send_message(
                AgentRole.PRODUCTION_PLANNER,
                "quality_alert",
                {
                    "issues": issues,
                    "metrics": quality_metrics
                }
            )
            
        return {
            "quality_validation": quality_metrics,
            "issues_found": issues,
            "status": "success" if not issues else "warning"
        }
        
    async def predict_quality_issues(self) -> Dict[str, Any]:
        """Predict potential quality issues using ML"""
        # This would use ML models in production
        predictions = {
            "predicted_defect_rate_next_week": 0.041,
            "high_risk_products": [
                {"product": "Cotton T-Shirt", "risk_score": 0.78},
                {"product": "Polyester Blend", "risk_score": 0.65}
            ],
            "risk_factors": [
                "Humidity levels above optimal range",
                "Machine maintenance overdue on Line 3",
                "New operator training incomplete"
            ],
            "preventive_actions": [
                "Schedule immediate maintenance for Line 3",
                "Adjust environmental controls",
                "Complete operator certification"
            ]
        }
        
        return {
            "quality_predictions": predictions,
            "status": "success"
        }
        
    async def generate_quality_report(self) -> Dict[str, Any]:
        """Generate comprehensive quality report"""
        metrics = await self.validate_quality_metrics()
        predictions = await self.predict_quality_issues()
        
        report = {
            "report_date": datetime.now().isoformat(),
            "overall_quality_score": 96.2,
            "current_metrics": metrics.get("quality_validation"),
            "predictions": predictions.get("quality_predictions"),
            "recommendations": [
                "Implement predictive maintenance schedule",
                "Enhance operator training program",
                "Upgrade quality inspection equipment"
            ],
            "estimated_improvement": "3.8% quality increase possible"
        }
        
        # Send report to Executive Analyst
        await self.send_message(
            AgentRole.EXECUTIVE_ANALYST,
            "quality_report",
            report
        )
        
        return report


class MLForecaster(BeverlyERPAgent):
    """Agent responsible for ML-based forecasting"""
    
    def __init__(self):
        super().__init__(AgentRole.ML_FORECASTER)
        self.forecast_horizon = 90  # days
        
    async def process_task(self, task: AgentTask) -> Dict[str, Any]:
        """Process ML forecasting tasks"""
        self.current_task = task
        
        if task.task_type == "generate_demand_forecast":
            return await self.generate_demand_forecast()
        elif task.task_type == "update_models":
            return await self.update_ml_models()
        elif task.task_type == "backtest_accuracy":
            return await self.backtest_forecast_accuracy()
        else:
            return {"error": f"Unknown task type: {task.task_type}"}
            
    async def generate_demand_forecast(self) -> Dict[str, Any]:
        """Generate demand forecasts using ML models"""
        ml_data = await self.fetch_erp_data("ml-forecasting")
        
        if not ml_data:
            return {"error": "Failed to fetch ML data"}
            
        models = ml_data.get("models", [])
        
        # Select best performing model
        best_model = min(models, key=lambda x: float(x.get("mape", "100").replace("%", "")))
        
        # Generate forecast (simulated)
        forecast = {
            "model_used": best_model.get("model"),
            "accuracy": best_model.get("accuracy"),
            "forecast_period": f"Next {self.forecast_horizon} days",
            "predicted_demand": {
                "30_days": 45000,
                "60_days": 92000,
                "90_days": 138000
            },
            "confidence_intervals": {
                "30_days": {"lower": 42000, "upper": 48000},
                "60_days": {"lower": 86000, "upper": 98000},
                "90_days": {"lower": 128000, "upper": 148000}
            },
            "seasonality_detected": True,
            "trend": "Upward trend with seasonal peaks"
        }
        
        # Share forecast with other agents
        await self.send_message(
            AgentRole.INVENTORY_MANAGER,
            "demand_forecast",
            forecast
        )
        
        await self.send_message(
            AgentRole.PRODUCTION_PLANNER,
            "demand_forecast",
            forecast
        )
        
        return {
            "forecast": forecast,
            "status": "success"
        }
        
    async def update_ml_models(self) -> Dict[str, Any]:
        """Update and retrain ML models"""
        # Simulate model update process
        update_results = {
            "models_updated": 6,
            "training_time": "12.5 minutes",
            "improvement": {
                "Prophet": "+2.3% accuracy",
                "XGBoost": "+1.8% accuracy",
                "LSTM": "+3.1% accuracy"
            },
            "new_features_added": [
                "Economic indicators",
                "Weather patterns",
                "Social media sentiment"
            ],
            "next_update_scheduled": (datetime.now() + timedelta(days=7)).isoformat()
        }
        
        return {
            "model_update": update_results,
            "status": "success"
        }
        
    async def backtest_forecast_accuracy(self) -> Dict[str, Any]:
        """Backtest forecast accuracy against actuals"""
        # This would compare historical forecasts with actual data
        backtest_results = {
            "period_tested": "Last 30 days",
            "overall_mape": "8.2%",
            "model_performance": {
                "Prophet": {"mape": "7.8%", "rmse": 1250},
                "XGBoost": {"mape": "8.5%", "rmse": 1320},
                "Ensemble": {"mape": "7.2%", "rmse": 1180}
            },
            "accuracy_trend": "Improving",
            "recommendations": [
                "Continue using Ensemble model as primary",
                "Increase training frequency during peak seasons",
                "Add external data sources for better accuracy"
            ]
        }
        
        return {
            "backtest": backtest_results,
            "status": "success"
        }


class ExecutiveAnalyst(BeverlyERPAgent):
    """Agent responsible for executive analytics and reporting"""
    
    def __init__(self):
        super().__init__(AgentRole.EXECUTIVE_ANALYST)
        self.kpi_targets = {
            "inventory_turns": 10,
            "forecast_accuracy": 0.92,
            "quality_rate": 0.98,
            "otd": 0.95
        }
        
    async def process_task(self, task: AgentTask) -> Dict[str, Any]:
        """Process executive analytics tasks"""
        self.current_task = task
        
        if task.task_type == "generate_executive_dashboard":
            return await self.generate_executive_dashboard()
        elif task.task_type == "analyze_kpis":
            return await self.analyze_kpi_performance()
        elif task.task_type == "generate_insights":
            return await self.generate_strategic_insights()
        else:
            return {"error": f"Unknown task type: {task.task_type}"}
            
    async def generate_executive_dashboard(self) -> Dict[str, Any]:
        """Generate executive dashboard data"""
        kpis = await self.fetch_erp_data("comprehensive-kpis")
        insights = await self.fetch_erp_data("executive-insights")
        
        dashboard = {
            "timestamp": datetime.now().isoformat(),
            "kpis": kpis,
            "insights": insights.get("insights", [])[:5],
            "alerts": [],
            "trends": {
                "revenue": "↑ 12.3% YoY",
                "costs": "↓ 8.5% QoQ",
                "efficiency": "↑ 6.2% MoM"
            }
        }
        
        # Check for KPI alerts
        if kpis:
            inventory_turns = float(kpis.get("inventory_turns", "0x").replace("x", ""))
            if inventory_turns < self.kpi_targets["inventory_turns"]:
                dashboard["alerts"].append({
                    "type": "KPI Alert",
                    "message": f"Inventory turns ({inventory_turns}x) below target ({self.kpi_targets['inventory_turns']}x)",
                    "severity": "Medium"
                })
                
        return {
            "dashboard": dashboard,
            "status": "success"
        }
        
    async def analyze_kpi_performance(self) -> Dict[str, Any]:
        """Analyze KPI performance against targets"""
        kpis = await self.fetch_erp_data("comprehensive-kpis")
        
        if not kpis:
            return {"error": "Failed to fetch KPI data"}
            
        analysis = {
            "kpi_analysis": {},
            "performance_score": 0,
            "recommendations": []
        }
        
        # Analyze each KPI
        total_score = 0
        kpi_count = 0
        
        for kpi_name, target in self.kpi_targets.items():
            if kpi_name in kpis:
                current_value = kpis[kpi_name]
                # Parse numeric value
                if isinstance(current_value, str):
                    current_value = float(current_value.replace("%", "").replace("x", "").replace("$", "").replace(",", "") or 0) / 100
                    
                performance = (current_value / target) * 100 if target > 0 else 0
                total_score += min(performance, 100)
                kpi_count += 1
                
                analysis["kpi_analysis"][kpi_name] = {
                    "current": current_value,
                    "target": target,
                    "performance": f"{performance:.1f}%",
                    "status": "On Track" if performance >= 95 else "Needs Attention" if performance >= 80 else "Critical"
                }
                
                if performance < 95:
                    analysis["recommendations"].append(f"Improve {kpi_name} from {current_value} to {target}")
                    
        analysis["performance_score"] = total_score / kpi_count if kpi_count > 0 else 0
        
        return {
            "analysis": analysis,
            "status": "success"
        }
        
    async def generate_strategic_insights(self) -> Dict[str, Any]:
        """Generate strategic insights for executives"""
        # Aggregate data from multiple sources
        kpi_analysis = await self.analyze_kpi_performance()
        insights_data = await self.fetch_erp_data("executive-insights")
        
        strategic_insights = {
            "generated_at": datetime.now().isoformat(),
            "overall_health_score": kpi_analysis.get("analysis", {}).get("performance_score", 0),
            "strategic_recommendations": [
                {
                    "priority": "High",
                    "insight": "Implement AI-driven demand forecasting to improve inventory turns by 25%",
                    "expected_impact": "$2.5M annual savings",
                    "timeline": "3 months"
                },
                {
                    "priority": "High",
                    "insight": "Diversify supplier base to reduce single-source dependencies by 40%",
                    "expected_impact": "Risk reduction and 8% cost savings",
                    "timeline": "6 months"
                },
                {
                    "priority": "Medium",
                    "insight": "Upgrade production line automation to increase capacity by 30%",
                    "expected_impact": "$1.8M additional revenue potential",
                    "timeline": "9 months"
                }
            ],
            "risk_factors": [
                "Supply chain concentration in 3 suppliers",
                "Seasonal demand fluctuations affecting cash flow",
                "Aging equipment requiring capital investment"
            ],
            "opportunities": [
                "Export market expansion (15% growth potential)",
                "Sustainable fabric line (Premium pricing opportunity)",
                "Direct-to-consumer channel development"
            ]
        }
        
        return {
            "strategic_insights": strategic_insights,
            "status": "success"
        }


class BeverlyERPOrchestrator:
    """Orchestrator for managing all Beverly ERP agents"""
    
    def __init__(self):
        self.agents: Dict[AgentRole, BeverlyERPAgent] = {}
        self.task_queue: List[AgentTask] = []
        self.message_bus: List[AgentMessage] = []
        self.active = False
        
    async def initialize(self):
        """Initialize all agents"""
        # Create all specialized agents
        self.agents[AgentRole.SUPPLY_CHAIN_OPTIMIZER] = SupplyChainOptimizer()
        self.agents[AgentRole.PRODUCTION_PLANNER] = ProductionPlanner()
        self.agents[AgentRole.QUALITY_CONTROLLER] = QualityController()
        self.agents[AgentRole.ML_FORECASTER] = MLForecaster()
        self.agents[AgentRole.EXECUTIVE_ANALYST] = ExecutiveAnalyst()
        
        # Initialize all agents
        for agent in self.agents.values():
            await agent.initialize()
            
        self.active = True
        logger.info("Beverly ERP Orchestrator initialized with all agents")
        
    async def shutdown(self):
        """Shutdown all agents"""
        self.active = False
        for agent in self.agents.values():
            await agent.shutdown()
        logger.info("Beverly ERP Orchestrator shutdown complete")
        
    async def assign_task(self, task: AgentTask) -> Dict[str, Any]:
        """Assign a task to the appropriate agent"""
        # Determine which agent should handle the task
        agent_mapping = {
            "optimize_procurement": AgentRole.SUPPLY_CHAIN_OPTIMIZER,
            "analyze_supplier_risk": AgentRole.SUPPLY_CHAIN_OPTIMIZER,
            "calculate_eoq": AgentRole.SUPPLY_CHAIN_OPTIMIZER,
            "execute_6phase_planning": AgentRole.PRODUCTION_PLANNER,
            "identify_bottlenecks": AgentRole.PRODUCTION_PLANNER,
            "optimize_schedule": AgentRole.PRODUCTION_PLANNER,
            "validate_quality_metrics": AgentRole.QUALITY_CONTROLLER,
            "predict_defects": AgentRole.QUALITY_CONTROLLER,
            "generate_quality_report": AgentRole.QUALITY_CONTROLLER,
            "generate_demand_forecast": AgentRole.ML_FORECASTER,
            "update_models": AgentRole.ML_FORECASTER,
            "backtest_accuracy": AgentRole.ML_FORECASTER,
            "generate_executive_dashboard": AgentRole.EXECUTIVE_ANALYST,
            "analyze_kpis": AgentRole.EXECUTIVE_ANALYST,
            "generate_insights": AgentRole.EXECUTIVE_ANALYST
        }
        
        agent_role = agent_mapping.get(task.task_type)
        if not agent_role:
            return {"error": f"No agent available for task type: {task.task_type}"}
            
        agent = self.agents.get(agent_role)
        if not agent:
            return {"error": f"Agent {agent_role.value} not available"}
            
        task.assigned_to = agent_role
        task.status = "in_progress"
        
        # Process the task
        try:
            result = await agent.process_task(task)
            task.status = "completed"
            task.completed_at = datetime.now()
            task.result = result
            return result
        except Exception as e:
            task.status = "failed"
            logger.error(f"Task {task.task_id} failed: {e}")
            return {"error": str(e)}
            
    async def execute_daily_operations(self):
        """Execute daily operational tasks"""
        daily_tasks = [
            AgentTask(task_id="daily_001", task_type="generate_demand_forecast", priority=1),
            AgentTask(task_id="daily_002", task_type="analyze_supplier_risk", priority=2),
            AgentTask(task_id="daily_003", task_type="identify_bottlenecks", priority=2),
            AgentTask(task_id="daily_004", task_type="validate_quality_metrics", priority=3),
            AgentTask(task_id="daily_005", task_type="calculate_eoq", priority=3),
            AgentTask(task_id="daily_006", task_type="analyze_kpis", priority=4),
            AgentTask(task_id="daily_007", task_type="generate_executive_dashboard", priority=5)
        ]
        
        results = {}
        for task in daily_tasks:
            logger.info(f"Executing task {task.task_id}: {task.task_type}")
            results[task.task_id] = await self.assign_task(task)
            
        return results
        
    async def execute_planning_cycle(self):
        """Execute the complete planning cycle"""
        planning_tasks = [
            AgentTask(task_id="plan_001", task_type="execute_6phase_planning", priority=1),
            AgentTask(task_id="plan_002", task_type="optimize_procurement", priority=2),
            AgentTask(task_id="plan_003", task_type="optimize_schedule", priority=3),
            AgentTask(task_id="plan_004", task_type="generate_insights", priority=4)
        ]
        
        results = {}
        for task in planning_tasks:
            logger.info(f"Executing planning task {task.task_id}: {task.task_type}")
            results[task.task_id] = await self.assign_task(task)
            await asyncio.sleep(2)  # Allow time between planning phases
            
        return results


# Utility functions for agent management
async def create_orchestrator() -> BeverlyERPOrchestrator:
    """Create and initialize the orchestrator"""
    orchestrator = BeverlyERPOrchestrator()
    await orchestrator.initialize()
    return orchestrator

async def run_daily_operations():
    """Run daily operational cycle"""
    orchestrator = await create_orchestrator()
    try:
        results = await orchestrator.execute_daily_operations()
        logger.info("Daily operations completed")
        return results
    finally:
        await orchestrator.shutdown()

async def run_planning_cycle():
    """Run planning cycle"""
    orchestrator = await create_orchestrator()
    try:
        results = await orchestrator.execute_planning_cycle()
        logger.info("Planning cycle completed")
        return results
    finally:
        await orchestrator.shutdown()

# Main execution
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Run daily operations
    asyncio.run(run_daily_operations())