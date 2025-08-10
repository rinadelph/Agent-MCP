"""
Production Strategies for Textile ERP Backtesting

Implements various strategies for optimizing textile manufacturing operations:
- Inventory Management (JIT, EOQ, Min-Max)
- Production Scheduling (FIFO, Priority-based, Deadline-driven)
- Quality Control Thresholds
- Maintenance Scheduling
- Demand Forecasting
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from abc import ABC, abstractmethod
import math
from collections import deque

from .engine import BaseStrategy, BacktestEvent
from ...core.config import logger


class InventoryPolicy(Enum):
    """Inventory management policies"""
    JIT = "just_in_time"
    EOQ = "economic_order_quantity"
    MIN_MAX = "min_max"
    PERIODIC_REVIEW = "periodic_review"
    CONTINUOUS_REVIEW = "continuous_review"


class SchedulingPolicy(Enum):
    """Production scheduling policies"""
    FIFO = "first_in_first_out"
    LIFO = "last_in_first_out"
    SJF = "shortest_job_first"
    PRIORITY = "priority_based"
    DEADLINE = "earliest_deadline_first"
    CAPACITY = "capacity_based"


@dataclass
class ProductionOrder:
    """Represents a production order in the system"""
    order_id: str
    product_type: str
    quantity: int
    priority: int = 1
    due_date: Optional[datetime] = None
    processing_time: float = 1.0
    materials_required: Dict[str, float] = None
    status: str = "pending"  # pending, in_progress, completed, cancelled
    created_at: datetime = None
    
    def __post_init__(self):
        if self.materials_required is None:
            self.materials_required = {}
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class InventoryItem:
    """Represents an inventory item"""
    item_id: str
    item_type: str
    current_stock: float
    unit_cost: float
    holding_cost_rate: float = 0.2  # 20% annual holding cost
    lead_time: int = 7  # days
    safety_stock: float = 0.0
    reorder_point: float = 0.0
    order_quantity: float = 0.0
    supplier: str = "default"
    
    def holding_cost_per_day(self) -> float:
        """Calculate daily holding cost"""
        return self.current_stock * self.unit_cost * (self.holding_cost_rate / 365)


class InventoryStrategy(BaseStrategy):
    """
    Advanced inventory management strategy with multiple policies.
    
    Supports JIT, EOQ, Min-Max, and other inventory management approaches
    for optimizing textile material inventory.
    """
    
    def __init__(self, name: str, policy: str = "EOQ", **kwargs):
        super().__init__(name, **kwargs)
        
        self.policy = InventoryPolicy(policy.lower()) if isinstance(policy, str) else policy
        self.inventory_items = {}
        self.orders_pending = []
        self.orders_history = []
        
        # Strategy parameters
        self.service_level = kwargs.get('service_level', 0.95)
        self.review_frequency = kwargs.get('review_frequency', 7)  # days
        self.demand_forecast_period = kwargs.get('demand_forecast_period', 30)  # days
        self.safety_stock_factor = kwargs.get('safety_stock_factor', 1.65)  # for 95% service level
        
        # Performance tracking
        self.total_holding_cost = 0.0
        self.total_ordering_cost = 0.0
        self.stockout_events = 0
        self.orders_placed = 0
        
        logger.info(f"Initialized InventoryStrategy with policy: {self.policy.value}")
    
    def initialize(self, historical_data: Dict[str, pd.DataFrame]):
        """Initialize inventory items from historical data"""
        yarn_data = historical_data.get('yarn_data', pd.DataFrame())
        inventory_data = historical_data.get('inventory_data', pd.DataFrame())
        
        # Initialize inventory items from yarn data
        if not yarn_data.empty:
            for _, row in yarn_data.iterrows():
                item_id = f"{row.get('Type', 'Unknown')}_{row.get('Color', 'Unknown')}"
                
                if item_id not in self.inventory_items:
                    self.inventory_items[item_id] = InventoryItem(
                        item_id=item_id,
                        item_type=row.get('Type', 'Unknown'),
                        current_stock=float(row.get('INVEN', 0)),
                        unit_cost=float(str(row.get('Price', '0')).replace('$', '').replace(',', '')),
                        supplier=row.get('Purchased From', 'Unknown')
                    )
        
        # Calculate initial inventory parameters
        self._calculate_inventory_parameters()
        
        logger.info(f"Initialized {len(self.inventory_items)} inventory items")
    
    def execute_step(self, current_time: datetime, data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Execute inventory management for current time step"""
        
        # Update demand forecasts
        demand_forecast = self._forecast_demand(current_time, data)
        
        # Check for stockouts
        stockouts = self._check_stockouts()
        
        # Execute inventory policy
        orders_to_place = []
        
        if self.policy == InventoryPolicy.EOQ:
            orders_to_place = self._execute_eoq_policy(current_time, demand_forecast)
        elif self.policy == InventoryPolicy.JIT:
            orders_to_place = self._execute_jit_policy(current_time, demand_forecast)
        elif self.policy == InventoryPolicy.MIN_MAX:
            orders_to_place = self._execute_min_max_policy(current_time, demand_forecast)
        elif self.policy == InventoryPolicy.PERIODIC_REVIEW:
            if self._is_review_period(current_time):
                orders_to_place = self._execute_periodic_review_policy(current_time, demand_forecast)
        elif self.policy == InventoryPolicy.CONTINUOUS_REVIEW:
            orders_to_place = self._execute_continuous_review_policy(current_time, demand_forecast)
        
        # Place orders
        for order in orders_to_place:
            self._place_order(order, current_time)
        
        # Calculate costs
        daily_holding_cost = sum(item.holding_cost_per_day() for item in self.inventory_items.values())
        self.total_holding_cost += daily_holding_cost
        
        # Update performance metrics
        result = {
            'total_inventory_value': sum(item.current_stock * item.unit_cost for item in self.inventory_items.values()),
            'total_holding_cost': self.total_holding_cost,
            'total_ordering_cost': self.total_ordering_cost,
            'stockout_events': len(stockouts),
            'orders_placed_today': len(orders_to_place),
            'items_below_safety_stock': len([item for item in self.inventory_items.values() 
                                           if item.current_stock < item.safety_stock]),
            'demand_forecast': demand_forecast
        }
        
        self.performance_history.append(result)
        return result
    
    def process_event(self, event: BacktestEvent):
        """Process inventory-related events"""
        if event.event_type == 'yarn_order':
            self._process_yarn_order_event(event)
        elif event.event_type == 'inventory_update':
            self._process_inventory_update_event(event)
    
    def _forecast_demand(self, current_time: datetime, data: Dict[str, pd.DataFrame]) -> Dict[str, float]:
        """Forecast demand for each inventory item"""
        demand_forecast = {}
        
        # Simple exponential smoothing for demand forecasting
        alpha = 0.3  # Smoothing parameter
        
        for item_id, item in self.inventory_items.items():
            # Get recent demand history (simplified)
            recent_demand = self._get_recent_demand(item_id, current_time, data)
            
            if recent_demand:
                # Exponential smoothing
                forecast = recent_demand[0]
                for demand in recent_demand[1:]:
                    forecast = alpha * demand + (1 - alpha) * forecast
                demand_forecast[item_id] = forecast
            else:
                # Default demand if no history
                demand_forecast[item_id] = item.current_stock * 0.1  # 10% of current stock
        
        return demand_forecast
    
    def _get_recent_demand(self, item_id: str, current_time: datetime, data: Dict[str, pd.DataFrame]) -> List[float]:
        """Get recent demand history for an item (simplified)"""
        # This would typically analyze sales/usage data
        # For now, return simulated demand
        return [np.random.exponential(50) for _ in range(7)]  # 7 days of demand
    
    def _check_stockouts(self) -> List[str]:
        """Check for stockout conditions"""
        stockouts = []
        for item_id, item in self.inventory_items.items():
            if item.current_stock <= 0:
                stockouts.append(item_id)
                self.stockout_events += 1
        return stockouts
    
    def _execute_eoq_policy(self, current_time: datetime, demand_forecast: Dict[str, float]) -> List[Dict[str, Any]]:
        """Execute Economic Order Quantity policy"""
        orders = []
        
        for item_id, item in self.inventory_items.items():
            if item.current_stock <= item.reorder_point:
                annual_demand = demand_forecast.get(item_id, 0) * 365
                ordering_cost = 25.0  # Fixed ordering cost per order
                
                if annual_demand > 0:
                    # EOQ formula
                    eoq = math.sqrt((2 * annual_demand * ordering_cost) / 
                                  (item.unit_cost * item.holding_cost_rate))
                    
                    orders.append({
                        'item_id': item_id,
                        'quantity': eoq,
                        'cost': item.unit_cost * eoq,
                        'policy': 'EOQ'
                    })
        
        return orders
    
    def _execute_jit_policy(self, current_time: datetime, demand_forecast: Dict[str, float]) -> List[Dict[str, Any]]:
        """Execute Just-In-Time policy"""
        orders = []
        
        for item_id, item in self.inventory_items.items():
            daily_demand = demand_forecast.get(item_id, 0)
            
            # Order only what's needed for lead time + small buffer
            if item.current_stock < daily_demand * (item.lead_time + 1):
                order_quantity = daily_demand * item.lead_time * 1.1  # 10% buffer
                
                orders.append({
                    'item_id': item_id,
                    'quantity': order_quantity,
                    'cost': item.unit_cost * order_quantity,
                    'policy': 'JIT'
                })
        
        return orders
    
    def _execute_min_max_policy(self, current_time: datetime, demand_forecast: Dict[str, float]) -> List[Dict[str, Any]]:
        """Execute Min-Max inventory policy"""
        orders = []
        
        for item_id, item in self.inventory_items.items():
            daily_demand = demand_forecast.get(item_id, 0)
            
            # Min = safety stock + lead time demand
            min_level = item.safety_stock + (daily_demand * item.lead_time)
            # Max = min + economic order quantity
            max_level = min_level + item.order_quantity
            
            if item.current_stock <= min_level:
                order_quantity = max_level - item.current_stock
                
                orders.append({
                    'item_id': item_id,
                    'quantity': order_quantity,
                    'cost': item.unit_cost * order_quantity,
                    'policy': 'MIN_MAX'
                })
        
        return orders
    
    def _execute_periodic_review_policy(self, current_time: datetime, demand_forecast: Dict[str, float]) -> List[Dict[str, Any]]:
        """Execute Periodic Review policy"""
        orders = []
        
        for item_id, item in self.inventory_items.items():
            daily_demand = demand_forecast.get(item_id, 0)
            review_period_demand = daily_demand * self.review_frequency
            
            # Target stock level
            target_level = item.safety_stock + (daily_demand * (item.lead_time + self.review_frequency))
            
            if item.current_stock < target_level:
                order_quantity = target_level - item.current_stock
                
                orders.append({
                    'item_id': item_id,
                    'quantity': order_quantity,
                    'cost': item.unit_cost * order_quantity,
                    'policy': 'PERIODIC_REVIEW'
                })
        
        return orders
    
    def _execute_continuous_review_policy(self, current_time: datetime, demand_forecast: Dict[str, float]) -> List[Dict[str, Any]]:
        """Execute Continuous Review policy"""
        orders = []
        
        for item_id, item in self.inventory_items.items():
            if item.current_stock <= item.reorder_point:
                order_quantity = item.order_quantity
                
                orders.append({
                    'item_id': item_id,
                    'quantity': order_quantity,
                    'cost': item.unit_cost * order_quantity,
                    'policy': 'CONTINUOUS_REVIEW'
                })
        
        return orders
    
    def _is_review_period(self, current_time: datetime) -> bool:
        """Check if current time is a review period"""
        # Simple check: review every N days
        day_of_year = current_time.timetuple().tm_yday
        return day_of_year % self.review_frequency == 0
    
    def _place_order(self, order: Dict[str, Any], current_time: datetime):
        """Place an inventory order"""
        self.orders_pending.append({
            'order_id': f"ORD_{current_time.strftime('%Y%m%d')}_{len(self.orders_pending)}",
            'item_id': order['item_id'],
            'quantity': order['quantity'],
            'cost': order['cost'],
            'order_date': current_time,
            'expected_delivery': current_time + timedelta(days=self.inventory_items[order['item_id']].lead_time),
            'policy': order['policy']
        })
        
        self.total_ordering_cost += 25.0  # Fixed ordering cost
        self.orders_placed += 1
    
    def _calculate_inventory_parameters(self):
        """Calculate reorder points, safety stock, and order quantities"""
        for item in self.inventory_items.values():
            # Safety stock calculation
            # Assuming normal demand distribution
            lead_time_demand = item.current_stock * 0.1 * item.lead_time  # Simplified
            demand_std = lead_time_demand * 0.3  # Assume 30% CV
            
            item.safety_stock = self.safety_stock_factor * demand_std
            item.reorder_point = lead_time_demand + item.safety_stock
            
            # Economic order quantity (default calculation)
            annual_demand = item.current_stock * 0.1 * 365  # Simplified
            ordering_cost = 25.0
            
            if annual_demand > 0:
                item.order_quantity = math.sqrt((2 * annual_demand * ordering_cost) / 
                                              (item.unit_cost * item.holding_cost_rate))
            else:
                item.order_quantity = 100.0  # Default
    
    def _process_yarn_order_event(self, event: BacktestEvent):
        """Process yarn order events"""
        data = event.data
        item_id = f"{data.get('Type', 'Unknown')}_{data.get('Color', 'Unknown')}"
        
        if item_id in self.inventory_items:
            # Simulate consumption
            consumption = np.random.exponential(10)  # Random consumption
            self.inventory_items[item_id].current_stock = max(0, 
                self.inventory_items[item_id].current_stock - consumption)
    
    def _process_inventory_update_event(self, event: BacktestEvent):
        """Process inventory update events"""
        # Handle received orders
        current_time = event.timestamp
        
        # Check for delivered orders
        delivered_orders = [order for order in self.orders_pending 
                           if order['expected_delivery'] <= current_time]
        
        for order in delivered_orders:
            if order['item_id'] in self.inventory_items:
                self.inventory_items[order['item_id']].current_stock += order['quantity']
                self.orders_history.append(order)
        
        # Remove delivered orders from pending
        self.orders_pending = [order for order in self.orders_pending 
                              if order['expected_delivery'] > current_time]


class ProductionSchedulingStrategy(BaseStrategy):
    """
    Production scheduling strategy with multiple policies.
    
    Supports FIFO, priority-based, deadline-driven, and capacity-based scheduling
    for optimizing textile production workflows.
    """
    
    def __init__(self, name: str, policy: str = "PRIORITY", **kwargs):
        super().__init__(name, **kwargs)
        
        self.policy = SchedulingPolicy(policy.lower()) if isinstance(policy, str) else policy
        self.production_queue = deque()
        self.completed_orders = []
        self.in_progress_orders = {}
        
        # Production capacity parameters
        self.daily_capacity = kwargs.get('daily_capacity', 1000)  # units per day
        self.setup_time = kwargs.get('setup_time', 2)  # hours
        self.efficiency_factor = kwargs.get('efficiency_factor', 0.85)
        
        # Performance tracking
        self.total_production = 0
        self.on_time_deliveries = 0
        self.late_deliveries = 0
        self.capacity_utilization = []
        self.setup_costs = 0.0
        
        logger.info(f"Initialized ProductionSchedulingStrategy with policy: {self.policy.value}")
    
    def initialize(self, historical_data: Dict[str, pd.DataFrame]):
        """Initialize production scheduling with historical sales data"""
        sales_data = historical_data.get('sales_data', pd.DataFrame())
        
        # Generate initial production orders from sales data
        if not sales_data.empty:
            for _, row in sales_data.iterrows():
                # Create production orders based on sales data
                order = self._create_production_order_from_sales(row)
                if order:
                    self.production_queue.append(order)
        
        logger.info(f"Initialized production queue with {len(self.production_queue)} orders")
    
    def execute_step(self, current_time: datetime, data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Execute production scheduling for current time step"""
        
        # Add new orders based on current data
        self._add_new_orders(current_time, data)
        
        # Update in-progress orders
        completed_today = self._update_in_progress_orders(current_time)
        
        # Schedule new orders based on policy
        scheduled_orders = self._schedule_orders(current_time)
        
        # Calculate capacity utilization
        total_scheduled_time = sum(order.processing_time for order in scheduled_orders)
        daily_available_time = 24 * self.efficiency_factor  # hours
        utilization = min(total_scheduled_time / daily_available_time, 1.0)
        self.capacity_utilization.append(utilization)
        
        # Start production on scheduled orders
        for order in scheduled_orders:
            self.in_progress_orders[order.order_id] = {
                'order': order,
                'start_time': current_time,
                'expected_completion': current_time + timedelta(hours=order.processing_time)
            }
            order.status = 'in_progress'
        
        # Calculate performance metrics
        result = {
            'orders_in_queue': len(self.production_queue),
            'orders_in_progress': len(self.in_progress_orders),
            'orders_completed_today': len(completed_today),
            'capacity_utilization': utilization,
            'on_time_delivery_rate': self.on_time_deliveries / max(1, self.on_time_deliveries + self.late_deliveries),
            'total_production': self.total_production,
            'average_queue_length': len(self.production_queue)
        }
        
        self.performance_history.append(result)
        return result
    
    def process_event(self, event: BacktestEvent):
        """Process production-related events"""
        if event.event_type == 'yarn_order':
            # Create production order from yarn order
            order = self._create_production_order_from_yarn_event(event)
            if order:
                self.production_queue.append(order)
    
    def _create_production_order_from_sales(self, sales_row) -> Optional[ProductionOrder]:
        """Create a production order from sales data"""
        try:
            order_id = f"PROD_{sales_row.get('Order_ID', len(self.production_queue))}"
            
            return ProductionOrder(
                order_id=order_id,
                product_type=sales_row.get('Product_Type', 'Fabric'),
                quantity=int(sales_row.get('Quantity', 100)),
                priority=int(sales_row.get('Priority', 1)),
                processing_time=float(sales_row.get('Processing_Hours', 8)),
                materials_required={'yarn': float(sales_row.get('Yarn_Required', 50))}
            )
        except Exception as e:
            logger.warning(f"Failed to create production order from sales data: {e}")
            return None
    
    def _create_production_order_from_yarn_event(self, event: BacktestEvent) -> Optional[ProductionOrder]:
        """Create production order from yarn event"""
        try:
            data = event.data
            order_id = f"PROD_{data.get('PO #', 'UNKNOWN')}"
            
            # Estimate production parameters based on yarn order
            yarn_quantity = float(str(data.get('PO Order Amt', 0)).replace(',', ''))
            fabric_quantity = yarn_quantity * 0.8  # 80% conversion efficiency
            
            return ProductionOrder(
                order_id=order_id,
                product_type='Fabric',
                quantity=int(fabric_quantity),
                priority=np.random.randint(1, 6),  # Random priority 1-5
                processing_time=fabric_quantity / 100,  # hours based on quantity
                materials_required={'yarn': yarn_quantity}
            )
        except Exception as e:
            logger.warning(f"Failed to create production order from yarn event: {e}")
            return None
    
    def _add_new_orders(self, current_time: datetime, data: Dict[str, pd.DataFrame]):
        """Add new orders to production queue based on current data"""
        # This would typically process new sales orders or production requests
        # For simulation, occasionally add random orders
        if np.random.random() < 0.1:  # 10% chance of new order each day
            order = ProductionOrder(
                order_id=f"PROD_{current_time.strftime('%Y%m%d')}_{len(self.production_queue)}",
                product_type=np.random.choice(['Cotton Fabric', 'Polyester Fabric', 'Blend Fabric']),
                quantity=np.random.randint(50, 500),
                priority=np.random.randint(1, 6),
                due_date=current_time + timedelta(days=np.random.randint(1, 30)),
                processing_time=np.random.uniform(4, 24)
            )
            self.production_queue.append(order)
    
    def _update_in_progress_orders(self, current_time: datetime) -> List[ProductionOrder]:
        """Update in-progress orders and move completed ones"""
        completed_orders = []
        
        completed_ids = []
        for order_id, order_info in self.in_progress_orders.items():
            if current_time >= order_info['expected_completion']:
                order = order_info['order']
                order.status = 'completed'
                
                # Check if delivery is on time
                if order.due_date:
                    if current_time <= order.due_date:
                        self.on_time_deliveries += 1
                    else:
                        self.late_deliveries += 1
                
                self.total_production += order.quantity
                completed_orders.append(order)
                self.completed_orders.append(order)
                completed_ids.append(order_id)
        
        # Remove completed orders from in-progress
        for order_id in completed_ids:
            del self.in_progress_orders[order_id]
        
        return completed_orders
    
    def _schedule_orders(self, current_time: datetime) -> List[ProductionOrder]:
        """Schedule orders based on the selected policy"""
        if not self.production_queue:
            return []
        
        # Calculate available capacity
        current_load = sum(1 for order_info in self.in_progress_orders.values() 
                          if order_info['expected_completion'] > current_time)
        
        max_concurrent_orders = max(1, int(self.daily_capacity / 100))  # Simplified capacity model
        available_slots = max(0, max_concurrent_orders - current_load)
        
        if available_slots <= 0:
            return []
        
        # Sort queue based on scheduling policy
        sorted_queue = self._sort_queue_by_policy(list(self.production_queue))
        
        # Select orders to schedule
        scheduled_orders = []
        for order in sorted_queue[:available_slots]:
            scheduled_orders.append(order)
            self.production_queue.remove(order)
        
        return scheduled_orders
    
    def _sort_queue_by_policy(self, orders: List[ProductionOrder]) -> List[ProductionOrder]:
        """Sort production queue based on scheduling policy"""
        
        if self.policy == SchedulingPolicy.FIFO:
            return sorted(orders, key=lambda x: x.created_at or datetime.min)
        
        elif self.policy == SchedulingPolicy.LIFO:
            return sorted(orders, key=lambda x: x.created_at or datetime.min, reverse=True)
        
        elif self.policy == SchedulingPolicy.SJF:
            return sorted(orders, key=lambda x: x.processing_time)
        
        elif self.policy == SchedulingPolicy.PRIORITY:
            return sorted(orders, key=lambda x: (-x.priority, x.created_at or datetime.min))
        
        elif self.policy == SchedulingPolicy.DEADLINE:
            return sorted(orders, key=lambda x: x.due_date or datetime.max)
        
        elif self.policy == SchedulingPolicy.CAPACITY:
            # Balance by processing time and priority
            return sorted(orders, key=lambda x: (x.processing_time / max(1, x.priority)))
        
        else:
            return orders


class QualityControlStrategy(BaseStrategy):
    """
    Quality control strategy for textile production.
    
    Monitors quality metrics and adjusts thresholds to optimize
    the trade-off between quality and production efficiency.
    """
    
    def __init__(self, name: str, **kwargs):
        super().__init__(name, **kwargs)
        
        # Quality thresholds
        self.defect_rate_threshold = kwargs.get('defect_rate_threshold', 0.05)  # 5%
        self.inspection_rate = kwargs.get('inspection_rate', 0.1)  # 10% of production
        self.acceptable_quality_level = kwargs.get('aql', 2.5)  # AQL 2.5
        
        # Quality metrics tracking
        self.total_inspected = 0
        self.total_defects = 0
        self.quality_history = []
        self.rejected_batches = 0
        self.rework_cost = 0.0
        
        # Adaptive parameters
        self.adaptive_thresholds = kwargs.get('adaptive_thresholds', True)
        self.threshold_adjustment_rate = kwargs.get('threshold_adjustment_rate', 0.01)
        
        logger.info("Initialized QualityControlStrategy")
    
    def initialize(self, historical_data: Dict[str, pd.DataFrame]):
        """Initialize quality control with historical data"""
        # This would typically analyze historical quality data
        # For now, set baseline parameters
        self.baseline_defect_rate = 0.03  # 3% baseline defect rate
        logger.info("Quality control initialized with baseline parameters")
    
    def execute_step(self, current_time: datetime, data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Execute quality control for current time step"""
        
        # Simulate daily production and quality inspection
        daily_production = np.random.poisson(500)  # Average 500 units per day
        inspected_units = int(daily_production * self.inspection_rate)
        
        # Simulate defects based on current quality level
        defect_probability = self._calculate_current_defect_rate()
        defects_found = np.random.binomial(inspected_units, defect_probability)
        
        self.total_inspected += inspected_units
        self.total_defects += defects_found
        
        current_defect_rate = defects_found / max(1, inspected_units)
        
        # Quality control decisions
        batch_rejected = current_defect_rate > self.defect_rate_threshold
        if batch_rejected:
            self.rejected_batches += 1
            rework_cost = daily_production * 0.5  # $0.5 per unit rework cost
            self.rework_cost += rework_cost
        
        # Adaptive threshold adjustment
        if self.adaptive_thresholds:
            self._adjust_quality_thresholds(current_defect_rate)
        
        # Calculate quality metrics
        cumulative_defect_rate = self.total_defects / max(1, self.total_inspected)
        first_pass_yield = 1 - cumulative_defect_rate
        
        result = {
            'daily_production': daily_production,
            'inspected_units': inspected_units,
            'defects_found': defects_found,
            'current_defect_rate': current_defect_rate,
            'cumulative_defect_rate': cumulative_defect_rate,
            'first_pass_yield': first_pass_yield,
            'batch_rejected': batch_rejected,
            'total_rework_cost': self.rework_cost,
            'quality_threshold': self.defect_rate_threshold
        }
        
        self.quality_history.append(result)
        self.performance_history.append(result)
        return result
    
    def _calculate_current_defect_rate(self) -> float:
        """Calculate current defect rate with process variations"""
        # Simulate process variations and trends
        base_rate = self.baseline_defect_rate
        
        # Add random variation
        random_variation = np.random.normal(0, base_rate * 0.3)
        
        # Add seasonal trends (simplified)
        seasonal_factor = 1 + 0.1 * np.sin(len(self.quality_history) / 30)  # Monthly cycle
        
        return max(0, base_rate + random_variation) * seasonal_factor
    
    def _adjust_quality_thresholds(self, current_defect_rate: float):
        """Adaptively adjust quality thresholds based on performance"""
        
        # If consistently below threshold, slightly relax it
        if len(self.quality_history) >= 10:
            recent_defect_rates = [h['current_defect_rate'] for h in self.quality_history[-10:]]
            avg_recent_rate = np.mean(recent_defect_rates)
            
            if avg_recent_rate < self.defect_rate_threshold * 0.7:
                # Relax threshold slightly
                self.defect_rate_threshold = min(
                    self.defect_rate_threshold + self.threshold_adjustment_rate,
                    0.1  # Maximum 10% threshold
                )
            elif avg_recent_rate > self.defect_rate_threshold * 1.2:
                # Tighten threshold
                self.defect_rate_threshold = max(
                    self.defect_rate_threshold - self.threshold_adjustment_rate,
                    0.01  # Minimum 1% threshold
                )


class MaintenanceStrategy(BaseStrategy):
    """
    Maintenance scheduling strategy for textile equipment.
    
    Balances preventive maintenance, corrective maintenance, and
    production scheduling to minimize downtime and costs.
    """
    
    def __init__(self, name: str, **kwargs):
        super().__init__(name, **kwargs)
        
        # Maintenance parameters
        self.preventive_interval = kwargs.get('preventive_interval', 30)  # days
        self.breakdown_probability = kwargs.get('breakdown_probability', 0.02)  # 2% daily
        self.maintenance_cost = kwargs.get('maintenance_cost', 500)  # per maintenance
        self.breakdown_cost = kwargs.get('breakdown_cost', 2000)  # per breakdown
        
        # Equipment tracking
        self.equipment_status = {}
        self.maintenance_schedule = []
        self.breakdown_history = []
        self.total_maintenance_cost = 0.0
        self.total_downtime = 0.0
        
        # Initialize equipment
        self._initialize_equipment()
        
        logger.info("Initialized MaintenanceStrategy")
    
    def initialize(self, historical_data: Dict[str, pd.DataFrame]):
        """Initialize maintenance strategy with historical data"""
        # Would typically analyze historical maintenance data
        logger.info("Maintenance strategy initialized")
    
    def execute_step(self, current_time: datetime, data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Execute maintenance scheduling for current time step"""
        
        # Check for scheduled maintenance
        scheduled_maintenance = self._execute_scheduled_maintenance(current_time)
        
        # Check for equipment breakdowns
        breakdowns = self._check_equipment_breakdowns(current_time)
        
        # Update equipment status
        self._update_equipment_status(current_time)
        
        # Schedule future maintenance
        self._schedule_preventive_maintenance(current_time)
        
        # Calculate maintenance metrics
        equipment_availability = len([eq for eq in self.equipment_status.values() 
                                    if eq['status'] == 'operational']) / len(self.equipment_status)
        
        result = {
            'scheduled_maintenance_today': len(scheduled_maintenance),
            'breakdowns_today': len(breakdowns),
            'equipment_availability': equipment_availability,
            'total_maintenance_cost': self.total_maintenance_cost,
            'total_downtime_hours': self.total_downtime,
            'preventive_vs_corrective_ratio': self._calculate_maintenance_ratio()
        }
        
        self.performance_history.append(result)
        return result
    
    def _initialize_equipment(self):
        """Initialize equipment fleet"""
        equipment_types = ['Weaving_Machine', 'Dyeing_Unit', 'Finishing_Machine', 'Quality_Scanner']
        
        for i, eq_type in enumerate(equipment_types):
            for j in range(3):  # 3 of each type
                eq_id = f"{eq_type}_{j+1}"
                self.equipment_status[eq_id] = {
                    'type': eq_type,
                    'status': 'operational',
                    'last_maintenance': datetime.now() - timedelta(days=np.random.randint(0, 30)),
                    'operating_hours': np.random.uniform(100, 1000),
                    'breakdown_probability': self.breakdown_probability
                }
    
    def _execute_scheduled_maintenance(self, current_time: datetime) -> List[str]:
        """Execute scheduled preventive maintenance"""
        maintenance_today = []
        
        for maintenance in self.maintenance_schedule:
            if maintenance['date'] == current_time.date():
                eq_id = maintenance['equipment_id']
                if eq_id in self.equipment_status:
                    # Perform maintenance
                    self.equipment_status[eq_id]['status'] = 'maintenance'
                    self.equipment_status[eq_id]['last_maintenance'] = current_time
                    self.equipment_status[eq_id]['maintenance_end'] = current_time + timedelta(hours=4)
                    
                    self.total_maintenance_cost += self.maintenance_cost
                    self.total_downtime += 4  # 4 hours downtime
                    
                    maintenance_today.append(eq_id)
        
        # Remove completed maintenance from schedule
        self.maintenance_schedule = [m for m in self.maintenance_schedule 
                                   if m['date'] != current_time.date()]
        
        return maintenance_today
    
    def _check_equipment_breakdowns(self, current_time: datetime) -> List[str]:
        """Check for random equipment breakdowns"""
        breakdowns = []
        
        for eq_id, equipment in self.equipment_status.items():
            if equipment['status'] == 'operational':
                # Higher breakdown probability for older equipment
                age_factor = min(equipment['operating_hours'] / 1000, 2.0)
                breakdown_prob = equipment['breakdown_probability'] * age_factor
                
                if np.random.random() < breakdown_prob:
                    # Equipment breakdown
                    equipment['status'] = 'broken'
                    equipment['breakdown_time'] = current_time
                    equipment['repair_end'] = current_time + timedelta(hours=np.random.uniform(8, 24))
                    
                    self.total_maintenance_cost += self.breakdown_cost
                    breakdown_duration = (equipment['repair_end'] - current_time).total_seconds() / 3600
                    self.total_downtime += breakdown_duration
                    
                    self.breakdown_history.append({
                        'equipment_id': eq_id,
                        'breakdown_time': current_time,
                        'repair_duration': breakdown_duration
                    })
                    
                    breakdowns.append(eq_id)
        
        return breakdowns
    
    def _update_equipment_status(self, current_time: datetime):
        """Update equipment status based on time"""
        for eq_id, equipment in self.equipment_status.items():
            # Check if maintenance is complete
            if equipment['status'] == 'maintenance':
                if current_time >= equipment.get('maintenance_end', current_time):
                    equipment['status'] = 'operational'
                    equipment['operating_hours'] = 0  # Reset after maintenance
            
            # Check if repair is complete
            elif equipment['status'] == 'broken':
                if current_time >= equipment.get('repair_end', current_time):
                    equipment['status'] = 'operational'
            
            # Accumulate operating hours
            elif equipment['status'] == 'operational':
                equipment['operating_hours'] += 24  # 24 hours per day
    
    def _schedule_preventive_maintenance(self, current_time: datetime):
        """Schedule future preventive maintenance"""
        for eq_id, equipment in self.equipment_status.items():
            if equipment['status'] == 'operational':
                days_since_maintenance = (current_time - equipment['last_maintenance']).days
                
                if days_since_maintenance >= self.preventive_interval:
                    # Schedule maintenance for next available slot
                    maintenance_date = current_time + timedelta(days=1)
                    
                    # Check if already scheduled
                    already_scheduled = any(m['equipment_id'] == eq_id 
                                          for m in self.maintenance_schedule)
                    
                    if not already_scheduled:
                        self.maintenance_schedule.append({
                            'equipment_id': eq_id,
                            'date': maintenance_date.date(),
                            'type': 'preventive'
                        })
    
    def _calculate_maintenance_ratio(self) -> float:
        """Calculate ratio of preventive to corrective maintenance"""
        preventive_count = len([m for m in self.maintenance_schedule 
                               if m['type'] == 'preventive'])
        corrective_count = len(self.breakdown_history)
        
        if corrective_count == 0:
            return float('inf')
        return preventive_count / corrective_count


class DemandForecastingStrategy(BaseStrategy):
    """
    Demand forecasting strategy for textile production planning.
    
    Uses multiple forecasting methods to predict future demand
    and optimize production planning and inventory management.
    """
    
    def __init__(self, name: str, **kwargs):
        super().__init__(name, **kwargs)
        
        # Forecasting parameters
        self.forecast_horizon = kwargs.get('forecast_horizon', 30)  # days
        self.smoothing_alpha = kwargs.get('smoothing_alpha', 0.3)
        self.seasonal_period = kwargs.get('seasonal_period', 7)  # weekly seasonality
        
        # Historical data storage
        self.demand_history = []
        self.forecast_history = []
        self.forecast_accuracy = []
        
        # Multiple forecasting methods
        self.methods = kwargs.get('methods', ['exponential_smoothing', 'moving_average', 'linear_trend'])
        
        logger.info(f"Initialized DemandForecastingStrategy with methods: {self.methods}")
    
    def initialize(self, historical_data: Dict[str, pd.DataFrame]):
        """Initialize demand forecasting with historical data"""
        # Extract demand patterns from sales data
        sales_data = historical_data.get('sales_data', pd.DataFrame())
        
        if not sales_data.empty:
            # Simplified demand extraction
            for _, row in sales_data.iterrows():
                demand = row.get('Quantity', np.random.poisson(100))
                self.demand_history.append(float(demand))
        
        # Fill with synthetic data if needed
        while len(self.demand_history) < 30:
            self.demand_history.append(np.random.poisson(100))
        
        logger.info(f"Initialized with {len(self.demand_history)} historical demand points")
    
    def execute_step(self, current_time: datetime, data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Execute demand forecasting for current time step"""
        
        # Generate today's actual demand (simulation)
        actual_demand = self._simulate_actual_demand(current_time)
        self.demand_history.append(actual_demand)
        
        # Generate forecasts using different methods
        forecasts = {}
        
        if 'exponential_smoothing' in self.methods:
            forecasts['exponential_smoothing'] = self._exponential_smoothing_forecast()
        
        if 'moving_average' in self.methods:
            forecasts['moving_average'] = self._moving_average_forecast()
        
        if 'linear_trend' in self.methods:
            forecasts['linear_trend'] = self._linear_trend_forecast()
        
        if 'seasonal_naive' in self.methods:
            forecasts['seasonal_naive'] = self._seasonal_naive_forecast()
        
        # Combine forecasts (simple average)
        if forecasts:
            combined_forecast = np.mean(list(forecasts.values()))
        else:
            combined_forecast = self.demand_history[-1]  # Naive forecast
        
        # Calculate forecast accuracy if we have previous forecasts
        forecast_error = 0.0
        if self.forecast_history:
            forecast_error = abs(actual_demand - self.forecast_history[-1])
            self.forecast_accuracy.append(forecast_error)
        
        self.forecast_history.append(combined_forecast)
        
        # Calculate performance metrics
        mape = self._calculate_mape() if len(self.forecast_accuracy) > 0 else 0.0
        
        result = {
            'actual_demand': actual_demand,
            'forecast_demand': combined_forecast,
            'forecast_error': forecast_error,
            'mape': mape,
            'individual_forecasts': forecasts,
            'demand_trend': self._calculate_trend(),
            'demand_volatility': self._calculate_volatility()
        }
        
        # Keep history manageable
        if len(self.demand_history) > 100:
            self.demand_history = self.demand_history[-100:]
        
        if len(self.forecast_history) > 100:
            self.forecast_history = self.forecast_history[-100:]
        
        if len(self.forecast_accuracy) > 100:
            self.forecast_accuracy = self.forecast_accuracy[-100:]
        
        self.performance_history.append(result)
        return result
    
    def _simulate_actual_demand(self, current_time: datetime) -> float:
        """Simulate actual demand with patterns"""
        # Base demand with trend and seasonality
        base_demand = 100
        
        # Add weekly seasonality
        day_of_week = current_time.weekday()
        seasonal_factor = [1.0, 0.8, 0.9, 1.1, 1.2, 0.7, 0.6][day_of_week]
        
        # Add monthly trend
        trend = 0.01 * len(self.demand_history)  # Slight upward trend
        
        # Add random variation
        noise = np.random.normal(0, 10)
        
        return max(0, base_demand + trend * base_demand * seasonal_factor + noise)
    
    def _exponential_smoothing_forecast(self) -> float:
        """Exponential smoothing forecast"""
        if len(self.demand_history) < 2:
            return self.demand_history[-1] if self.demand_history else 100.0
        
        forecast = self.demand_history[0]
        for demand in self.demand_history[1:]:
            forecast = self.smoothing_alpha * demand + (1 - self.smoothing_alpha) * forecast
        
        return forecast
    
    def _moving_average_forecast(self, window: int = 7) -> float:
        """Moving average forecast"""
        if len(self.demand_history) < window:
            return np.mean(self.demand_history)
        
        return np.mean(self.demand_history[-window:])
    
    def _linear_trend_forecast(self) -> float:
        """Linear trend forecast"""
        if len(self.demand_history) < 10:
            return self.demand_history[-1] if self.demand_history else 100.0
        
        # Simple linear regression on recent data
        recent_data = self.demand_history[-20:]  # Use last 20 points
        x = np.arange(len(recent_data))
        y = np.array(recent_data)
        
        # Calculate slope
        if len(recent_data) > 1:
            slope = np.polyfit(x, y, 1)[0]
            intercept = np.polyfit(x, y, 1)[1]
            return slope * len(recent_data) + intercept
        else:
            return recent_data[-1]
    
    def _seasonal_naive_forecast(self) -> float:
        """Seasonal naive forecast (same as last period)"""
        if len(self.demand_history) >= self.seasonal_period:
            return self.demand_history[-self.seasonal_period]
        else:
            return self.demand_history[-1] if self.demand_history else 100.0
    
    def _calculate_mape(self) -> float:
        """Calculate Mean Absolute Percentage Error"""
        if not self.forecast_accuracy or not self.demand_history:
            return 0.0
        
        min_length = min(len(self.forecast_accuracy), len(self.demand_history) - 1)
        if min_length <= 0:
            return 0.0
        
        actual = self.demand_history[-min_length:]
        errors = self.forecast_accuracy[-min_length:]
        
        mape = np.mean([abs(error) / max(abs(actual_val), 1) for error, actual_val in zip(errors, actual)])
        return mape * 100  # Convert to percentage
    
    def _calculate_trend(self) -> float:
        """Calculate demand trend"""
        if len(self.demand_history) < 10:
            return 0.0
        
        recent_data = self.demand_history[-20:]
        x = np.arange(len(recent_data))
        y = np.array(recent_data)
        
        if len(recent_data) > 1:
            slope = np.polyfit(x, y, 1)[0]
            return slope
        else:
            return 0.0
    
    def _calculate_volatility(self) -> float:
        """Calculate demand volatility"""
        if len(self.demand_history) < 2:
            return 0.0
        
        recent_data = self.demand_history[-30:]  # Last 30 points
        return float(np.std(recent_data))