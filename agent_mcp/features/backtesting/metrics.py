"""
Performance Metrics System for Textile ERP Backtesting

Provides comprehensive metrics for evaluating strategy performance:
- Production efficiency metrics (OEE, throughput, cycle time)
- Inventory metrics (turnover, carrying cost, stockout rate)
- Quality metrics (defect rate, first-pass yield, rework rate)
- Financial metrics (ROI, cost per unit, profit margins)
- Supply chain metrics (lead time, on-time delivery, fill rate)
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass
from enum import Enum
from abc import ABC, abstractmethod
import math
from collections import defaultdict

from ...core.config import logger


class MetricCategory(Enum):
    """Categories of performance metrics"""
    PRODUCTION = "production"
    INVENTORY = "inventory"  
    QUALITY = "quality"
    FINANCIAL = "financial"
    SUPPLY_CHAIN = "supply_chain"
    OVERALL = "overall"


class MetricType(Enum):
    """Types of metric calculations"""
    CUMULATIVE = "cumulative"
    AVERAGE = "average"
    RATIO = "ratio"
    PERCENTAGE = "percentage"
    RATE = "rate"
    INDEX = "index"


@dataclass
class MetricResult:
    """Container for metric calculation results"""
    name: str
    value: float
    category: MetricCategory
    metric_type: MetricType
    unit: str
    description: str
    timestamp: datetime
    benchmark_value: Optional[float] = None
    target_value: Optional[float] = None
    
    @property
    def vs_benchmark(self) -> Optional[float]:
        """Calculate performance vs benchmark"""
        if self.benchmark_value is not None and self.benchmark_value != 0:
            return (self.value - self.benchmark_value) / self.benchmark_value * 100
        return None
    
    @property
    def vs_target(self) -> Optional[float]:
        """Calculate performance vs target"""
        if self.target_value is not None and self.target_value != 0:
            return (self.value - self.target_value) / self.target_value * 100
        return None


class BaseMetrics(ABC):
    """Abstract base class for metric calculators"""
    
    def __init__(self, category: MetricCategory):
        self.category = category
        self.historical_values = {}
        self.benchmarks = {}
        self.targets = {}
    
    @abstractmethod
    def calculate_metrics(self, data: Dict[str, Any], timestamp: datetime) -> List[MetricResult]:
        """Calculate metrics from provided data"""
        pass
    
    def set_benchmark(self, metric_name: str, value: float):
        """Set benchmark value for a metric"""
        self.benchmarks[metric_name] = value
    
    def set_target(self, metric_name: str, value: float):
        """Set target value for a metric"""
        self.targets[metric_name] = value
    
    def _create_metric_result(self, name: str, value: float, metric_type: MetricType,
                             unit: str, description: str, timestamp: datetime) -> MetricResult:
        """Helper to create MetricResult with benchmarks and targets"""
        return MetricResult(
            name=name,
            value=value,
            category=self.category,
            metric_type=metric_type,
            unit=unit,
            description=description,
            timestamp=timestamp,
            benchmark_value=self.benchmarks.get(name),
            target_value=self.targets.get(name)
        )


class ProductionMetrics(BaseMetrics):
    """
    Production efficiency metrics calculator.
    
    Calculates key production metrics including OEE, throughput,
    cycle time, capacity utilization, and productivity measures.
    """
    
    def __init__(self):
        super().__init__(MetricCategory.PRODUCTION)
        
        # Production tracking
        self.total_production_time = 0.0
        self.total_downtime = 0.0
        self.total_units_produced = 0
        self.quality_production = 0
        self.planned_production_time = 0.0
        
        # Set default benchmarks
        self.set_benchmark('oee', 85.0)  # 85% OEE benchmark
        self.set_benchmark('capacity_utilization', 80.0)  # 80% capacity utilization
        self.set_benchmark('throughput_rate', 100.0)  # 100 units/hour
        
        # Set default targets
        self.set_target('oee', 90.0)  # 90% OEE target
        self.set_target('capacity_utilization', 85.0)  # 85% capacity utilization target
    
    def calculate_metrics(self, data: Dict[str, Any], timestamp: datetime) -> List[MetricResult]:
        """Calculate production metrics"""
        metrics = []
        
        # Extract data
        daily_production = data.get('daily_production', 0)
        planned_production = data.get('planned_production', daily_production)
        downtime_hours = data.get('downtime_hours', 0)
        operating_time = data.get('operating_time', 24 - downtime_hours)
        defect_rate = data.get('defect_rate', 0.0)
        capacity = data.get('capacity', 1000)  # units per day
        
        # Update cumulative values
        self.total_units_produced += daily_production
        self.total_downtime += downtime_hours
        self.total_production_time += operating_time
        self.planned_production_time += 24  # 24 hours per day planned
        self.quality_production += daily_production * (1 - defect_rate)
        
        # 1. Overall Equipment Effectiveness (OEE)
        availability = (24 - downtime_hours) / 24 if 24 > 0 else 0
        performance = (daily_production / planned_production) if planned_production > 0 else 0
        quality = 1 - defect_rate
        oee = availability * performance * quality * 100
        
        metrics.append(self._create_metric_result(
            name='oee',
            value=oee,
            metric_type=MetricType.PERCENTAGE,
            unit='%',
            description='Overall Equipment Effectiveness',
            timestamp=timestamp
        ))
        
        # 2. Capacity Utilization
        capacity_utilization = (daily_production / capacity * 100) if capacity > 0 else 0
        
        metrics.append(self._create_metric_result(
            name='capacity_utilization',
            value=capacity_utilization,
            metric_type=MetricType.PERCENTAGE,
            unit='%',
            description='Production capacity utilization',
            timestamp=timestamp
        ))
        
        # 3. Throughput Rate
        throughput_rate = (daily_production / operating_time) if operating_time > 0 else 0
        
        metrics.append(self._create_metric_result(
            name='throughput_rate',
            value=throughput_rate,
            metric_type=MetricType.RATE,
            unit='units/hour',
            description='Production throughput rate',
            timestamp=timestamp
        ))
        
        # 4. Cycle Time
        cycle_time = (operating_time * 60 / daily_production) if daily_production > 0 else 0  # minutes per unit
        
        metrics.append(self._create_metric_result(
            name='cycle_time',
            value=cycle_time,
            metric_type=MetricType.AVERAGE,
            unit='minutes/unit',
            description='Average production cycle time',
            timestamp=timestamp
        ))
        
        # 5. Productivity Index
        cumulative_productivity = (self.total_units_produced / self.total_production_time) if self.total_production_time > 0 else 0
        
        metrics.append(self._create_metric_result(
            name='productivity_index',
            value=cumulative_productivity,
            metric_type=MetricType.INDEX,
            unit='units/hour',
            description='Cumulative productivity index',
            timestamp=timestamp
        ))
        
        # 6. Equipment Availability
        equipment_availability = (self.planned_production_time - self.total_downtime) / self.planned_production_time * 100 if self.planned_production_time > 0 else 0
        
        metrics.append(self._create_metric_result(
            name='equipment_availability',
            value=equipment_availability,
            metric_type=MetricType.PERCENTAGE,
            unit='%',
            description='Cumulative equipment availability',
            timestamp=timestamp
        ))
        
        return metrics


class InventoryMetrics(BaseMetrics):
    """
    Inventory management metrics calculator.
    
    Calculates inventory turnover, carrying costs, stockout rates,
    service levels, and other inventory optimization metrics.
    """
    
    def __init__(self):
        super().__init__(MetricCategory.INVENTORY)
        
        # Inventory tracking
        self.total_carrying_cost = 0.0
        self.total_ordering_cost = 0.0
        self.stockout_days = 0
        self.total_demand = 0
        self.unfilled_demand = 0
        
        # Set default benchmarks
        self.set_benchmark('inventory_turnover', 12.0)  # 12 times per year
        self.set_benchmark('carrying_cost_ratio', 20.0)  # 20% of inventory value
        self.set_benchmark('service_level', 95.0)  # 95% service level
        
        # Set default targets
        self.set_target('inventory_turnover', 15.0)  # 15 times per year
        self.set_target('service_level', 98.0)  # 98% service level
    
    def calculate_metrics(self, data: Dict[str, Any], timestamp: datetime) -> List[MetricResult]:
        """Calculate inventory metrics"""
        metrics = []
        
        # Extract data
        inventory_value = data.get('total_inventory_value', 0)
        daily_carrying_cost = data.get('carrying_cost', 0)
        daily_ordering_cost = data.get('ordering_cost', 0)
        stockout_events = data.get('stockout_events', 0)
        daily_demand = data.get('demand', 0)
        unfilled_orders = data.get('unfilled_orders', 0)
        inventory_items = data.get('inventory_items', {})
        
        # Update cumulative values
        self.total_carrying_cost += daily_carrying_cost
        self.total_ordering_cost += daily_ordering_cost
        self.total_demand += daily_demand
        self.unfilled_demand += unfilled_orders
        
        if stockout_events > 0:
            self.stockout_days += 1
        
        # 1. Inventory Turnover Ratio
        days_elapsed = (timestamp - datetime(timestamp.year, 1, 1)).days + 1
        cogs_estimate = inventory_value * 0.7  # Estimate COGS as 70% of inventory value
        annual_cogs = cogs_estimate * (365 / days_elapsed)
        inventory_turnover = (annual_cogs / inventory_value) if inventory_value > 0 else 0
        
        metrics.append(self._create_metric_result(
            name='inventory_turnover',
            value=inventory_turnover,
            metric_type=MetricType.RATIO,
            unit='times/year',
            description='Inventory turnover ratio (annualized)',
            timestamp=timestamp
        ))
        
        # 2. Carrying Cost Ratio
        carrying_cost_ratio = (self.total_carrying_cost / inventory_value * 100) if inventory_value > 0 else 0
        
        metrics.append(self._create_metric_result(
            name='carrying_cost_ratio',
            value=carrying_cost_ratio,
            metric_type=MetricType.PERCENTAGE,
            unit='%',
            description='Carrying cost as percentage of inventory value',
            timestamp=timestamp
        ))
        
        # 3. Stockout Rate
        stockout_rate = (self.stockout_days / days_elapsed * 100) if days_elapsed > 0 else 0
        
        metrics.append(self._create_metric_result(
            name='stockout_rate',
            value=stockout_rate,
            metric_type=MetricType.PERCENTAGE,
            unit='%',
            description='Percentage of days with stockouts',
            timestamp=timestamp
        ))
        
        # 4. Service Level (Fill Rate)
        service_level = ((self.total_demand - self.unfilled_demand) / self.total_demand * 100) if self.total_demand > 0 else 100
        
        metrics.append(self._create_metric_result(
            name='service_level',
            value=service_level,
            metric_type=MetricType.PERCENTAGE,
            unit='%',
            description='Order fill rate (service level)',
            timestamp=timestamp
        ))
        
        # 5. Inventory Days Outstanding
        daily_usage_rate = (self.total_demand / days_elapsed) if days_elapsed > 0 else 1
        days_outstanding = (inventory_value / daily_usage_rate) if daily_usage_rate > 0 else 0
        
        metrics.append(self._create_metric_result(
            name='inventory_days_outstanding',
            value=days_outstanding,
            metric_type=MetricType.AVERAGE,
            unit='days',
            description='Days of inventory on hand',
            timestamp=timestamp
        ))
        
        # 6. Total Inventory Cost
        total_inventory_cost = self.total_carrying_cost + self.total_ordering_cost
        
        metrics.append(self._create_metric_result(
            name='total_inventory_cost',
            value=total_inventory_cost,
            metric_type=MetricType.CUMULATIVE,
            unit='$',
            description='Total cumulative inventory cost',
            timestamp=timestamp
        ))
        
        return metrics


class QualityMetrics(BaseMetrics):
    """
    Quality control metrics calculator.
    
    Calculates defect rates, first-pass yield, rework rates,
    quality costs, and other quality performance metrics.
    """
    
    def __init__(self):
        super().__init__(MetricCategory.QUALITY)
        
        # Quality tracking
        self.total_inspected = 0
        self.total_defects = 0
        self.total_rework_cost = 0.0
        self.total_scrap_cost = 0.0
        self.total_units_produced = 0
        self.first_pass_units = 0
        
        # Set default benchmarks
        self.set_benchmark('defect_rate', 3.0)  # 3% defect rate
        self.set_benchmark('first_pass_yield', 95.0)  # 95% first pass yield
        self.set_benchmark('quality_cost_ratio', 5.0)  # 5% of revenue
        
        # Set default targets
        self.set_target('defect_rate', 1.0)  # 1% defect rate target
        self.set_target('first_pass_yield', 98.0)  # 98% first pass yield target
    
    def calculate_metrics(self, data: Dict[str, Any], timestamp: datetime) -> List[MetricResult]:
        """Calculate quality metrics"""
        metrics = []
        
        # Extract data
        inspected_units = data.get('inspected_units', 0)
        defects_found = data.get('defects_found', 0)
        rework_cost = data.get('rework_cost', 0.0)
        scrap_cost = data.get('scrap_cost', 0.0)
        daily_production = data.get('daily_production', 0)
        first_pass_units = data.get('first_pass_units', daily_production - defects_found)
        
        # Update cumulative values
        self.total_inspected += inspected_units
        self.total_defects += defects_found
        self.total_rework_cost += rework_cost
        self.total_scrap_cost += scrap_cost
        self.total_units_produced += daily_production
        self.first_pass_units += first_pass_units
        
        # 1. Defect Rate
        defect_rate = (self.total_defects / self.total_inspected * 100) if self.total_inspected > 0 else 0
        
        metrics.append(self._create_metric_result(
            name='defect_rate',
            value=defect_rate,
            metric_type=MetricType.PERCENTAGE,
            unit='%',
            description='Cumulative defect rate',
            timestamp=timestamp
        ))
        
        # 2. First Pass Yield
        first_pass_yield = (self.first_pass_units / self.total_units_produced * 100) if self.total_units_produced > 0 else 100
        
        metrics.append(self._create_metric_result(
            name='first_pass_yield',
            value=first_pass_yield,
            metric_type=MetricType.PERCENTAGE,
            unit='%',
            description='First pass yield rate',
            timestamp=timestamp
        ))
        
        # 3. Rework Rate
        rework_rate = ((self.total_defects - (self.total_scrap_cost / 10)) / self.total_units_produced * 100) if self.total_units_produced > 0 else 0  # Assume $10 per scrapped unit
        
        metrics.append(self._create_metric_result(
            name='rework_rate',
            value=max(0, rework_rate),
            metric_type=MetricType.PERCENTAGE,
            unit='%',
            description='Rework rate as percentage of production',
            timestamp=timestamp
        ))
        
        # 4. Quality Cost Ratio
        total_quality_cost = self.total_rework_cost + self.total_scrap_cost
        estimated_revenue = self.total_units_produced * 50  # Assume $50 per unit revenue
        quality_cost_ratio = (total_quality_cost / estimated_revenue * 100) if estimated_revenue > 0 else 0
        
        metrics.append(self._create_metric_result(
            name='quality_cost_ratio',
            value=quality_cost_ratio,
            metric_type=MetricType.PERCENTAGE,
            unit='%',
            description='Quality costs as percentage of revenue',
            timestamp=timestamp
        ))
        
        # 5. Parts Per Million (PPM) Defects
        ppm_defects = (self.total_defects / self.total_inspected * 1_000_000) if self.total_inspected > 0 else 0
        
        metrics.append(self._create_metric_result(
            name='ppm_defects',
            value=ppm_defects,
            metric_type=MetricType.RATE,
            unit='PPM',
            description='Defects per million units',
            timestamp=timestamp
        ))
        
        # 6. Sigma Level (simplified calculation)
        if defect_rate > 0:
            # Convert defect rate to sigma level (simplified)
            defect_proportion = defect_rate / 100
            if defect_proportion < 0.5:
                sigma_level = -np.log10(defect_proportion) + 1.5  # Simplified formula
                sigma_level = max(1, min(6, sigma_level))  # Bound between 1 and 6 sigma
            else:
                sigma_level = 1.0
        else:
            sigma_level = 6.0
        
        metrics.append(self._create_metric_result(
            name='sigma_level',
            value=sigma_level,
            metric_type=MetricType.INDEX,
            unit='sigma',
            description='Quality sigma level',
            timestamp=timestamp
        ))
        
        return metrics


class FinancialMetrics(BaseMetrics):
    """
    Financial performance metrics calculator.
    
    Calculates ROI, cost per unit, profit margins, and other
    financial KPIs for production strategies.
    """
    
    def __init__(self):
        super().__init__(MetricCategory.FINANCIAL)
        
        # Financial tracking
        self.total_revenue = 0.0
        self.total_costs = 0.0
        self.total_investment = 0.0
        self.total_units_sold = 0
        
        # Set default benchmarks
        self.set_benchmark('roi', 15.0)  # 15% ROI
        self.set_benchmark('profit_margin', 20.0)  # 20% profit margin
        self.set_benchmark('cost_per_unit', 35.0)  # $35 per unit
        
        # Set default targets
        self.set_target('roi', 25.0)  # 25% ROI target
        self.set_target('profit_margin', 30.0)  # 30% profit margin target
    
    def calculate_metrics(self, data: Dict[str, Any], timestamp: datetime) -> List[MetricResult]:
        """Calculate financial metrics"""
        metrics = []
        
        # Extract data
        daily_revenue = data.get('revenue', 0.0)
        daily_costs = data.get('total_costs', 0.0)
        daily_investment = data.get('investment', 0.0)
        units_sold = data.get('units_sold', 0)
        
        # Calculate costs from components if not provided
        if daily_costs == 0.0:
            production_cost = data.get('production_cost', 0.0)
            inventory_cost = data.get('inventory_cost', 0.0)
            quality_cost = data.get('quality_cost', 0.0)
            maintenance_cost = data.get('maintenance_cost', 0.0)
            daily_costs = production_cost + inventory_cost + quality_cost + maintenance_cost
        
        # Calculate revenue if not provided
        if daily_revenue == 0.0:
            units_produced = data.get('units_produced', 0)
            unit_price = data.get('unit_price', 50.0)
            daily_revenue = units_produced * unit_price
        
        # Update cumulative values
        self.total_revenue += daily_revenue
        self.total_costs += daily_costs
        self.total_investment += daily_investment
        self.total_units_sold += units_sold if units_sold > 0 else data.get('units_produced', 0)
        
        # 1. Return on Investment (ROI)
        total_profit = self.total_revenue - self.total_costs
        roi = (total_profit / self.total_investment * 100) if self.total_investment > 0 else 0
        
        metrics.append(self._create_metric_result(
            name='roi',
            value=roi,
            metric_type=MetricType.PERCENTAGE,
            unit='%',
            description='Return on Investment',
            timestamp=timestamp
        ))
        
        # 2. Profit Margin
        profit_margin = (total_profit / self.total_revenue * 100) if self.total_revenue > 0 else 0
        
        metrics.append(self._create_metric_result(
            name='profit_margin',
            value=profit_margin,
            metric_type=MetricType.PERCENTAGE,
            unit='%',
            description='Profit margin percentage',
            timestamp=timestamp
        ))
        
        # 3. Cost Per Unit
        cost_per_unit = (self.total_costs / self.total_units_sold) if self.total_units_sold > 0 else 0
        
        metrics.append(self._create_metric_result(
            name='cost_per_unit',
            value=cost_per_unit,
            metric_type=MetricType.AVERAGE,
            unit='$/unit',
            description='Average cost per unit produced',
            timestamp=timestamp
        ))
        
        # 4. Revenue Per Unit
        revenue_per_unit = (self.total_revenue / self.total_units_sold) if self.total_units_sold > 0 else 0
        
        metrics.append(self._create_metric_result(
            name='revenue_per_unit',
            value=revenue_per_unit,
            metric_type=MetricType.AVERAGE,
            unit='$/unit',
            description='Average revenue per unit sold',
            timestamp=timestamp
        ))
        
        # 5. Break-even Point
        variable_cost_ratio = 0.6  # Assume 60% of costs are variable
        variable_cost_per_unit = cost_per_unit * variable_cost_ratio
        fixed_costs = self.total_costs * (1 - variable_cost_ratio)
        contribution_margin = revenue_per_unit - variable_cost_per_unit
        
        breakeven_units = (fixed_costs / contribution_margin) if contribution_margin > 0 else float('inf')
        
        metrics.append(self._create_metric_result(
            name='breakeven_units',
            value=breakeven_units if breakeven_units != float('inf') else 0,
            metric_type=MetricType.INDEX,
            unit='units',
            description='Break-even point in units',
            timestamp=timestamp
        ))
        
        # 6. Economic Value Added (EVA)
        cost_of_capital = 0.1  # 10% cost of capital
        capital_charge = self.total_investment * cost_of_capital
        eva = total_profit - capital_charge
        
        metrics.append(self._create_metric_result(
            name='eva',
            value=eva,
            metric_type=MetricType.CUMULATIVE,
            unit='$',
            description='Economic Value Added',
            timestamp=timestamp
        ))
        
        return metrics


class SupplyChainMetrics(BaseMetrics):
    """
    Supply chain performance metrics calculator.
    
    Calculates lead times, on-time delivery rates, fill rates,
    and other supply chain optimization metrics.
    """
    
    def __init__(self):
        super().__init__(MetricCategory.SUPPLY_CHAIN)
        
        # Supply chain tracking
        self.total_orders = 0
        self.on_time_deliveries = 0
        self.total_lead_time = 0.0
        self.total_demand = 0
        self.fulfilled_demand = 0
        self.supplier_performance = defaultdict(list)
        
        # Set default benchmarks
        self.set_benchmark('on_time_delivery_rate', 95.0)  # 95% on-time delivery
        self.set_benchmark('average_lead_time', 7.0)  # 7 days average lead time
        self.set_benchmark('fill_rate', 98.0)  # 98% fill rate
        
        # Set default targets
        self.set_target('on_time_delivery_rate', 98.0)  # 98% on-time delivery target
        self.set_target('average_lead_time', 5.0)  # 5 days lead time target
    
    def calculate_metrics(self, data: Dict[str, Any], timestamp: datetime) -> List[MetricResult]:
        """Calculate supply chain metrics"""
        metrics = []
        
        # Extract data
        orders_delivered = data.get('orders_delivered', 0)
        orders_on_time = data.get('orders_on_time', 0)
        average_lead_time = data.get('average_lead_time', 0.0)
        daily_demand = data.get('demand', 0)
        fulfilled_orders = data.get('fulfilled_orders', 0)
        supplier_data = data.get('supplier_performance', {})
        
        # Update cumulative values
        self.total_orders += orders_delivered
        self.on_time_deliveries += orders_on_time
        self.total_lead_time += average_lead_time * orders_delivered
        self.total_demand += daily_demand
        self.fulfilled_demand += fulfilled_orders
        
        # Update supplier performance
        for supplier, performance in supplier_data.items():
            self.supplier_performance[supplier].append(performance)
        
        # 1. On-Time Delivery Rate
        on_time_delivery_rate = (self.on_time_deliveries / self.total_orders * 100) if self.total_orders > 0 else 100
        
        metrics.append(self._create_metric_result(
            name='on_time_delivery_rate',
            value=on_time_delivery_rate,
            metric_type=MetricType.PERCENTAGE,
            unit='%',
            description='On-time delivery rate',
            timestamp=timestamp
        ))
        
        # 2. Average Lead Time
        avg_lead_time = (self.total_lead_time / self.total_orders) if self.total_orders > 0 else 0
        
        metrics.append(self._create_metric_result(
            name='average_lead_time',
            value=avg_lead_time,
            metric_type=MetricType.AVERAGE,
            unit='days',
            description='Average order lead time',
            timestamp=timestamp
        ))
        
        # 3. Fill Rate
        fill_rate = (self.fulfilled_demand / self.total_demand * 100) if self.total_demand > 0 else 100
        
        metrics.append(self._create_metric_result(
            name='fill_rate',
            value=fill_rate,
            metric_type=MetricType.PERCENTAGE,
            unit='%',
            description='Order fill rate',
            timestamp=timestamp
        ))
        
        # 4. Supply Chain Responsiveness (Order Cycle Time)
        # Simplified as average lead time for now
        responsiveness = avg_lead_time
        
        metrics.append(self._create_metric_result(
            name='supply_chain_responsiveness',
            value=responsiveness,
            metric_type=MetricType.AVERAGE,
            unit='days',
            description='Supply chain responsiveness (order cycle time)',
            timestamp=timestamp
        ))
        
        # 5. Supplier Performance Index
        if self.supplier_performance:
            supplier_scores = []
            for supplier, performances in self.supplier_performance.items():
                if performances:
                    avg_performance = np.mean(performances)
                    supplier_scores.append(avg_performance)
            
            supplier_performance_index = np.mean(supplier_scores) if supplier_scores else 100
        else:
            supplier_performance_index = 100
        
        metrics.append(self._create_metric_result(
            name='supplier_performance_index',
            value=supplier_performance_index,
            metric_type=MetricType.INDEX,
            unit='score',
            description='Average supplier performance index',
            timestamp=timestamp
        ))
        
        # 6. Perfect Order Rate
        # Simplified calculation: on-time * complete * damage-free * correct
        damage_free_rate = 0.99  # Assume 99% damage-free
        correct_order_rate = 0.98  # Assume 98% correct orders
        complete_order_rate = fill_rate / 100
        
        perfect_order_rate = (on_time_delivery_rate / 100) * complete_order_rate * damage_free_rate * correct_order_rate * 100
        
        metrics.append(self._create_metric_result(
            name='perfect_order_rate',
            value=perfect_order_rate,
            metric_type=MetricType.PERCENTAGE,
            unit='%',
            description='Perfect order fulfillment rate',
            timestamp=timestamp
        ))
        
        return metrics


class MetricsAggregator:
    """
    Aggregates and manages all performance metrics across categories.
    
    Provides centralized metric calculation, benchmarking, and
    comprehensive performance analysis.
    """
    
    def __init__(self):
        self.metric_calculators = {
            MetricCategory.PRODUCTION: ProductionMetrics(),
            MetricCategory.INVENTORY: InventoryMetrics(),
            MetricCategory.QUALITY: QualityMetrics(),
            MetricCategory.FINANCIAL: FinancialMetrics(),
            MetricCategory.SUPPLY_CHAIN: SupplyChainMetrics()
        }
        
        self.all_metrics_history = []
        self.category_summaries = {}
        
        logger.info("Initialized MetricsAggregator with all metric categories")
    
    def calculate_all_metrics(self, strategy_data: Dict[str, Any], timestamp: datetime) -> Dict[MetricCategory, List[MetricResult]]:
        """Calculate metrics for all categories"""
        all_metrics = {}
        
        for category, calculator in self.metric_calculators.items():
            try:
                # Extract relevant data for this category
                category_data = self._extract_category_data(strategy_data, category)
                
                # Calculate metrics
                metrics = calculator.calculate_metrics(category_data, timestamp)
                all_metrics[category] = metrics
                
                # Update category summary
                self.category_summaries[category] = {
                    'timestamp': timestamp,
                    'metric_count': len(metrics),
                    'metrics': {m.name: m.value for m in metrics}
                }
                
            except Exception as e:
                logger.error(f"Failed to calculate {category.value} metrics: {e}")
                all_metrics[category] = []
        
        # Store in history
        self.all_metrics_history.append({
            'timestamp': timestamp,
            'metrics': all_metrics
        })
        
        return all_metrics
    
    def _extract_category_data(self, strategy_data: Dict[str, Any], category: MetricCategory) -> Dict[str, Any]:
        """Extract relevant data for specific metric category"""
        
        # Common data that multiple categories might use
        base_data = {
            'timestamp': strategy_data.get('timestamp'),
            'daily_production': strategy_data.get('daily_production', 0),
            'units_produced': strategy_data.get('units_produced', 0),
            'demand': strategy_data.get('demand', 0)
        }
        
        if category == MetricCategory.PRODUCTION:
            return {
                **base_data,
                'planned_production': strategy_data.get('planned_production', base_data['daily_production']),
                'downtime_hours': strategy_data.get('downtime_hours', 0),
                'operating_time': strategy_data.get('operating_time', 20),
                'defect_rate': strategy_data.get('defect_rate', 0.0),
                'capacity': strategy_data.get('capacity', 1000)
            }
        
        elif category == MetricCategory.INVENTORY:
            return {
                **base_data,
                'total_inventory_value': strategy_data.get('total_inventory_value', 0),
                'carrying_cost': strategy_data.get('carrying_cost', 0),
                'ordering_cost': strategy_data.get('ordering_cost', 0),
                'stockout_events': strategy_data.get('stockout_events', 0),
                'unfilled_orders': strategy_data.get('unfilled_orders', 0),
                'inventory_items': strategy_data.get('inventory_items', {})
            }
        
        elif category == MetricCategory.QUALITY:
            return {
                **base_data,
                'inspected_units': strategy_data.get('inspected_units', 0),
                'defects_found': strategy_data.get('defects_found', 0),
                'rework_cost': strategy_data.get('rework_cost', 0.0),
                'scrap_cost': strategy_data.get('scrap_cost', 0.0),
                'first_pass_units': strategy_data.get('first_pass_units', base_data['daily_production'])
            }
        
        elif category == MetricCategory.FINANCIAL:
            return {
                **base_data,
                'revenue': strategy_data.get('revenue', 0.0),
                'total_costs': strategy_data.get('total_costs', 0.0),
                'investment': strategy_data.get('investment', 0.0),
                'units_sold': strategy_data.get('units_sold', 0),
                'unit_price': strategy_data.get('unit_price', 50.0),
                'production_cost': strategy_data.get('production_cost', 0.0),
                'inventory_cost': strategy_data.get('inventory_cost', 0.0),
                'quality_cost': strategy_data.get('quality_cost', 0.0),
                'maintenance_cost': strategy_data.get('maintenance_cost', 0.0)
            }
        
        elif category == MetricCategory.SUPPLY_CHAIN:
            return {
                **base_data,
                'orders_delivered': strategy_data.get('orders_delivered', 0),
                'orders_on_time': strategy_data.get('orders_on_time', 0),
                'average_lead_time': strategy_data.get('average_lead_time', 0.0),
                'fulfilled_orders': strategy_data.get('fulfilled_orders', 0),
                'supplier_performance': strategy_data.get('supplier_performance', {})
            }
        
        return base_data
    
    def get_metric_summary(self, category: Optional[MetricCategory] = None, 
                          time_period: Optional[Tuple[datetime, datetime]] = None) -> Dict[str, Any]:
        """Get summary of metrics for a category and time period"""
        
        if category is None:
            # Return summary for all categories
            return {cat.value: self.category_summaries.get(cat, {}) 
                   for cat in MetricCategory}
        
        if category in self.category_summaries:
            return self.category_summaries[category]
        
        return {}
    
    def get_performance_dashboard(self) -> Dict[str, Any]:
        """Generate comprehensive performance dashboard data"""
        
        if not self.all_metrics_history:
            return {}
        
        latest_metrics = self.all_metrics_history[-1]['metrics']
        
        dashboard = {
            'timestamp': self.all_metrics_history[-1]['timestamp'],
            'overall_performance': {},
            'category_performance': {},
            'key_metrics': {},
            'alerts': []
        }
        
        # Extract key metrics from each category
        key_metrics = {}
        alerts = []
        
        for category, metrics in latest_metrics.items():
            category_key_metrics = {}
            
            for metric in metrics:
                category_key_metrics[metric.name] = {
                    'value': metric.value,
                    'unit': metric.unit,
                    'vs_benchmark': metric.vs_benchmark,
                    'vs_target': metric.vs_target
                }
                
                # Generate alerts for metrics significantly below targets
                if metric.vs_target is not None and metric.vs_target < -10:
                    alerts.append({
                        'category': category.value,
                        'metric': metric.name,
                        'message': f"{metric.name} is {abs(metric.vs_target):.1f}% below target",
                        'severity': 'high' if metric.vs_target < -20 else 'medium'
                    })
            
            key_metrics[category.value] = category_key_metrics
        
        dashboard['key_metrics'] = key_metrics
        dashboard['alerts'] = alerts
        
        # Calculate overall performance score
        performance_scores = []
        
        for category, metrics in latest_metrics.items():
            category_score = 0
            metric_count = 0
            
            for metric in metrics:
                if metric.vs_benchmark is not None:
                    # Score based on performance vs benchmark
                    if metric.vs_benchmark >= 0:
                        score = min(100, 100 + metric.vs_benchmark)
                    else:
                        score = max(0, 100 + metric.vs_benchmark)
                    
                    category_score += score
                    metric_count += 1
            
            if metric_count > 0:
                avg_category_score = category_score / metric_count
                performance_scores.append(avg_category_score)
                dashboard['category_performance'][category.value] = avg_category_score
        
        overall_score = np.mean(performance_scores) if performance_scores else 50
        dashboard['overall_performance']['score'] = overall_score
        dashboard['overall_performance']['grade'] = self._score_to_grade(overall_score)
        
        return dashboard
    
    def _score_to_grade(self, score: float) -> str:
        """Convert performance score to letter grade"""
        if score >= 90:
            return 'A'
        elif score >= 80:
            return 'B'
        elif score >= 70:
            return 'C'
        elif score >= 60:
            return 'D'
        else:
            return 'F'
    
    def set_benchmarks(self, category: MetricCategory, benchmarks: Dict[str, float]):
        """Set benchmark values for a metric category"""
        if category in self.metric_calculators:
            for metric_name, value in benchmarks.items():
                self.metric_calculators[category].set_benchmark(metric_name, value)
    
    def set_targets(self, category: MetricCategory, targets: Dict[str, float]):
        """Set target values for a metric category"""
        if category in self.metric_calculators:
            for metric_name, value in targets.items():
                self.metric_calculators[category].set_target(metric_name, value)
    
    def export_metrics_data(self, file_path: str, format: str = 'csv'):
        """Export metrics data to file"""
        try:
            # Flatten metrics data for export
            export_data = []
            
            for history_entry in self.all_metrics_history:
                timestamp = history_entry['timestamp']
                
                for category, metrics in history_entry['metrics'].items():
                    for metric in metrics:
                        export_data.append({
                            'timestamp': timestamp,
                            'category': category.value,
                            'metric_name': metric.name,
                            'value': metric.value,
                            'unit': metric.unit,
                            'benchmark': metric.benchmark_value,
                            'target': metric.target_value,
                            'vs_benchmark': metric.vs_benchmark,
                            'vs_target': metric.vs_target
                        })
            
            df = pd.DataFrame(export_data)
            
            if format.lower() == 'csv':
                df.to_csv(file_path, index=False)
            elif format.lower() == 'excel':
                df.to_excel(file_path, index=False)
            else:
                raise ValueError(f"Unsupported format: {format}")
            
            logger.info(f"Metrics data exported to {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to export metrics data: {e}")
            raise