"""
Backtesting Framework for Textile ERP System

This module provides comprehensive backtesting capabilities for analyzing
historical data and simulating production scenarios in textile manufacturing.

Components:
- Engine: Core backtesting execution framework
- Strategies: Production optimization strategies (inventory, scheduling, quality)
- Metrics: Performance measurement and KPI calculation
- Simulator: Synthetic data generation for realistic testing
- Reports: Comprehensive analysis and visualization
"""

from .engine import BacktestEngine, BacktestConfig
from .strategies import (
    InventoryStrategy,
    ProductionSchedulingStrategy,
    QualityControlStrategy,
    MaintenanceStrategy,
    DemandForecastingStrategy
)
from .metrics import (
    ProductionMetrics,
    InventoryMetrics,
    QualityMetrics,
    FinancialMetrics,
    SupplyChainMetrics
)
from .simulator import TextileDataSimulator
from .reports import BacktestReporter

__all__ = [
    'BacktestEngine',
    'BacktestConfig',
    'InventoryStrategy',
    'ProductionSchedulingStrategy',
    'QualityControlStrategy',
    'MaintenanceStrategy',
    'DemandForecastingStrategy',
    'ProductionMetrics',
    'InventoryMetrics',
    'QualityMetrics',
    'FinancialMetrics',
    'SupplyChainMetrics',
    'TextileDataSimulator',
    'BacktestReporter'
]