#\!/usr/bin/env python3
"""
Six-Phase Planning Engine for Manufacturing ERP
Comprehensive supply chain planning with ML-driven optimization
Refactored for better structure, modularity, and maintainability
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import json
from typing import Dict, List, Tuple, Any, Optional
import logging
from dataclasses import dataclass, asdict, field
from collections import defaultdict
from abc import ABC, abstractmethod
import warnings
warnings.filterwarnings('ignore')

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# ML IMPORTS AND CONFIGURATION
# ============================================================================

try:
    from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
    from sklearn.linear_model import LinearRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import TimeSeriesSplit
    from sklearn.metrics import mean_absolute_percentage_error, mean_squared_error
    from prophet import Prophet
    import xgboost as xgb
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    logger.warning("ML libraries not available. Some features will be limited.")

# ============================================================================
# DATA CLASSES AND CONFIGURATIONS
# ============================================================================

@dataclass
class PlanningConfig:
    """Configuration parameters for planning engine"""
    forecast_horizon: int = 90  # days
    safety_stock_service_level: float = 0.98
    holding_cost_rate: float = 0.25  # 25% annual
    ordering_cost: float = 75.0
    lead_time_buffer: float = 1.2  # 20% buffer
    min_order_quantity: float = 100.0
    forecast_confidence_threshold: float = 0.85
    max_suppliers_per_item: int = 3
    supplier_reliability_weight: float = 0.4
    cost_weight: float = 0.3
    quality_weight: float = 0.3

@dataclass
class PlanningPhaseResult:
    """Result container for each planning phase"""
    phase_number: int
    phase_name: str
    status: str = "pending"
    execution_time: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    output_data: Optional[Any] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return asdict(self)
    
    def add_error(self, error: str):
        """Add error message"""
        self.errors.append(error)
        self.status = "failed"
    
    def add_warning(self, warning: str):
        """Add warning message"""
        self.warnings.append(warning)

@dataclass
class ProcurementRecommendation:
    """Procurement recommendation container"""
    item_code: str
    item_description: str
    supplier: str
    recommended_quantity: float
    eoq: float
    safety_stock: float
    reorder_point: float
    total_cost: float
    savings_potential: float
    priority: str
    rationale: str
    lead_time: int = 7
    min_order_qty: float = 100.0
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for API response"""
        return {
            'item': f"{self.item_code} - {self.item_description[:30]}",
            'supplier': self.supplier,
            'quantity': self.recommended_quantity,
            'cost': self.total_cost,
            'priority': self.priority,
            'savings': self.savings_potential,
            'lead_time': self.lead_time
        }

# ============================================================================
# BASE CLASSES AND INTERFACES
# ============================================================================

class PlanningPhase(ABC):
    """Abstract base class for planning phases"""
    
    def __init__(self, config: PlanningConfig):
        self.config = config
        self.result = None
    
    @abstractmethod
    def execute(self, input_data: Any) -> PlanningPhaseResult:
        """Execute the planning phase"""
        pass
    
    @abstractmethod
    def validate_input(self, input_data: Any) -> bool:
        """Validate input data for the phase"""
        pass
    
    def log_progress(self, message: str, level: str = "info"):
        """Log progress messages"""
        log_func = getattr(logger, level)
        log_func(f"[{self.__class__.__name__}] {message}")

class DataLoader:
    """Handles all data loading operations"""
    
    def __init__(self, data_path: Path):
        self.data_path = Path(data_path)
        self._cache = {}
    
    def load_sales_data(self) -> pd.DataFrame:
        """Load sales data with caching"""
        if 'sales' not in self._cache:
            file_path = self.data_path / "Sales Activity Report (4).xlsx"
            if file_path.exists():
                self._cache['sales'] = pd.read_excel(file_path)
                logger.info(f"Loaded {len(self._cache['sales'])} sales records")
            else:
                logger.warning(f"Sales data not found at {file_path}")
                self._cache['sales'] = pd.DataFrame()
        return self._cache['sales']
    
    def load_inventory_data(self) -> pd.DataFrame:
        """Load inventory data with caching"""
        if 'inventory' not in self._cache:
            file_path = self.data_path / "yarn_inventory (1).xlsx"
            if file_path.exists():
                self._cache['inventory'] = pd.read_excel(file_path)
                logger.info(f"Loaded {len(self._cache['inventory'])} inventory items")
            else:
                logger.warning(f"Inventory data not found at {file_path}")
                self._cache['inventory'] = pd.DataFrame()
        return self._cache['inventory']
    
    def load_bom_data(self) -> pd.DataFrame:
        """Load BOM data with caching"""
        if 'bom' not in self._cache:
            file_path = self.data_path / "BOM_2(Sheet1).csv"
            if file_path.exists():
                self._cache['bom'] = pd.read_csv(file_path)
                logger.info(f"Loaded {len(self._cache['bom'])} BOM entries")
            else:
                logger.warning(f"BOM data not found at {file_path}")
                self._cache['bom'] = pd.DataFrame()
        return self._cache['bom']
    
    def clear_cache(self):
        """Clear the data cache"""
        self._cache.clear()

# ============================================================================
# PHASE IMPLEMENTATIONS
# ============================================================================

class Phase1ForecastUnification(PlanningPhase):
    """Phase 1: Unified Forecasting with Multiple Models"""
    
    def execute(self, input_data: Dict) -> PlanningPhaseResult:
        """Execute forecast unification phase"""
        result = PlanningPhaseResult(
            phase_number=1,
            phase_name="Forecast Unification"
        )
        
        start_time = datetime.now()
        
        try:
            sales_data = input_data.get('sales_data')
            if sales_data is None or sales_data.empty:
                result.add_error("No sales data available")
                return result
            
            # Prepare data for forecasting
            forecast_data = self._prepare_forecast_data(sales_data)
            
            # Run multiple forecast models
            forecasts = {}
            if ML_AVAILABLE:
                forecasts['prophet'] = self._prophet_forecast(forecast_data)
                forecasts['xgboost'] = self._xgboost_forecast(forecast_data)
                forecasts['ensemble'] = self._ensemble_forecast(forecasts)
            else:
                forecasts['simple'] = self._simple_forecast(forecast_data)
            
            # Unify forecasts
            unified_forecast = self._unify_forecasts(forecasts)
            
            result.output_data = unified_forecast
            result.details = {
                'models_used': list(forecasts.keys()),
                'forecast_horizon': self.config.forecast_horizon,
                'products_forecasted': len(unified_forecast)
            }
            result.status = "success"
            
        except Exception as e:
            result.add_error(f"Forecasting failed: {str(e)}")
            logger.error(f"Phase 1 error: {e}")
        
        result.execution_time = (datetime.now() - start_time).total_seconds()
        return result
    
    def validate_input(self, input_data: Any) -> bool:
        """Validate input data has required fields"""
        if not isinstance(input_data, dict):
            return False
        return 'sales_data' in input_data
    
    def _prepare_forecast_data(self, sales_data: pd.DataFrame) -> pd.DataFrame:
        """Prepare sales data for forecasting"""
        # Implementation here
        return sales_data
    
    def _prophet_forecast(self, data: pd.DataFrame) -> pd.DataFrame:
        """Prophet forecasting model"""
        # Implementation here
        return pd.DataFrame()
    
    def _xgboost_forecast(self, data: pd.DataFrame) -> pd.DataFrame:
        """XGBoost forecasting model"""
        # Implementation here
        return pd.DataFrame()
    
    def _ensemble_forecast(self, forecasts: Dict) -> pd.DataFrame:
        """Ensemble of multiple forecasts"""
        # Implementation here
        return pd.DataFrame()
    
    def _simple_forecast(self, data: pd.DataFrame) -> pd.DataFrame:
        """Simple moving average forecast"""
        # Implementation here
        return pd.DataFrame()
    
    def _unify_forecasts(self, forecasts: Dict) -> pd.DataFrame:
        """Unify multiple forecasts into single output"""
        # Implementation here
        return pd.DataFrame()

class Phase2BOMExplosion(PlanningPhase):
    """Phase 2: Multi-level BOM Explosion"""
    
    def execute(self, input_data: Dict) -> PlanningPhaseResult:
        """Execute BOM explosion phase"""
        result = PlanningPhaseResult(
            phase_number=2,
            phase_name="BOM Explosion"
        )
        
        start_time = datetime.now()
        
        try:
            forecast = input_data.get('forecast')
            bom_data = input_data.get('bom_data')
            
            if forecast is None or bom_data is None:
                result.add_error("Missing forecast or BOM data")
                return result
            
            # Perform multi-level BOM explosion
            exploded_bom = self._explode_bom(forecast, bom_data)
            
            result.output_data = exploded_bom
            result.details = {
                'products_exploded': len(forecast),
                'materials_required': len(exploded_bom),
                'total_quantity': exploded_bom['required_quantity'].sum()
            }
            result.status = "success"
            
        except Exception as e:
            result.add_error(f"BOM explosion failed: {str(e)}")
            logger.error(f"Phase 2 error: {e}")
        
        result.execution_time = (datetime.now() - start_time).total_seconds()
        return result
    
    def validate_input(self, input_data: Any) -> bool:
        """Validate input data"""
        if not isinstance(input_data, dict):
            return False
        return 'forecast' in input_data and 'bom_data' in input_data
    
    def _explode_bom(self, forecast: pd.DataFrame, bom: pd.DataFrame) -> pd.DataFrame:
        """Perform multi-level BOM explosion"""
        # Implementation here
        return pd.DataFrame()

class Phase3InventoryNetting(PlanningPhase):
    """Phase 3: Inventory Netting and Requirements Calculation"""
    
    def execute(self, input_data: Dict) -> PlanningPhaseResult:
        """Execute inventory netting phase"""
        result = PlanningPhaseResult(
            phase_number=3,
            phase_name="Inventory Netting"
        )
        
        start_time = datetime.now()
        
        try:
            exploded_bom = input_data.get('exploded_bom')
            inventory = input_data.get('inventory_data')
            
            if exploded_bom is None or inventory is None:
                result.add_error("Missing BOM or inventory data")
                return result
            
            # Calculate net requirements
            net_requirements = self._calculate_net_requirements(
                exploded_bom, 
                inventory
            )
            
            result.output_data = net_requirements
            result.details = {
                'items_analyzed': len(net_requirements),
                'items_to_order': len(net_requirements[net_requirements['order_needed'] > 0]),
                'total_shortage': net_requirements['shortage'].sum()
            }
            result.status = "success"
            
        except Exception as e:
            result.add_error(f"Inventory netting failed: {str(e)}")
            logger.error(f"Phase 3 error: {e}")
        
        result.execution_time = (datetime.now() - start_time).total_seconds()
        return result
    
    def validate_input(self, input_data: Any) -> bool:
        """Validate input data"""
        if not isinstance(input_data, dict):
            return False
        return 'exploded_bom' in input_data and 'inventory_data' in input_data
    
    def _calculate_net_requirements(
        self, 
        bom: pd.DataFrame, 
        inventory: pd.DataFrame
    ) -> pd.DataFrame:
        """Calculate net requirements after inventory netting"""
        # Implementation here
        return pd.DataFrame()

# ============================================================================
# MAIN ENGINE CLASS
# ============================================================================

class SixPhasePlanningEngine:
    """
    Refactored 6-phase planning engine for supply chain optimization
    """
    
    def __init__(self, data_path: Path, config: Optional[PlanningConfig] = None):
        self.data_path = Path(data_path)
        self.config = config or PlanningConfig()
        self.data_loader = DataLoader(data_path)
        
        # Initialize phases
        self.phases = {
            1: Phase1ForecastUnification(self.config),
            2: Phase2BOMExplosion(self.config),
            3: Phase3InventoryNetting(self.config),
            # Add remaining phases here
        }
        
        # Storage for results
        self.phase_results = []
        self.final_output = None
        
        logger.info(f"Planning Engine initialized with data path: {data_path}")
    
    def execute_full_cycle(self) -> Dict[str, Any]:
        """Execute all 6 phases of the planning cycle"""
        logger.info("Starting 6-Phase Planning Cycle")
        
        start_time = datetime.now()
        
        # Load all required data
        input_data = self._load_all_data()
        
        # Execute phases in sequence
        for phase_num in range(1, 7):
            if phase_num in self.phases:
                phase = self.phases[phase_num]
                
                # Prepare phase input
                phase_input = self._prepare_phase_input(phase_num, input_data)
                
                # Execute phase
                result = phase.execute(phase_input)
                self.phase_results.append(result)
                
                # Update input data with phase output
                if result.status == "success" and result.output_data is not None:
                    input_data[f'phase{phase_num}_output'] = result.output_data
                
                logger.info(f"Phase {phase_num} completed: {result.status}")
        
        # Generate final output
        self.final_output = self._generate_final_output()
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        return {
            'status': 'completed',
            'execution_time': execution_time,
            'phase_results': [r.to_dict() for r in self.phase_results],
            'final_output': self.final_output
        }
    
    def _load_all_data(self) -> Dict[str, Any]:
        """Load all required data for planning"""
        return {
            'sales_data': self.data_loader.load_sales_data(),
            'inventory_data': self.data_loader.load_inventory_data(),
            'bom_data': self.data_loader.load_bom_data()
        }
    
    def _prepare_phase_input(self, phase_num: int, data: Dict) -> Dict:
        """Prepare input data for specific phase"""
        phase_input = {}
        
        if phase_num == 1:
            phase_input['sales_data'] = data.get('sales_data')
        elif phase_num == 2:
            phase_input['forecast'] = data.get('phase1_output')
            phase_input['bom_data'] = data.get('bom_data')
        elif phase_num == 3:
            phase_input['exploded_bom'] = data.get('phase2_output')
            phase_input['inventory_data'] = data.get('inventory_data')
        # Add remaining phases
        
        return phase_input
    
    def _generate_final_output(self) -> Dict:
        """Generate final consolidated output"""
        return {
            'timestamp': datetime.now().isoformat(),
            'phases_completed': len(self.phase_results),
            'success_rate': sum(1 for r in self.phase_results if r.status == "success") / len(self.phase_results),
            'recommendations': self._extract_recommendations()
        }
    
    def _extract_recommendations(self) -> List[Dict]:
        """Extract key recommendations from phase results"""
        recommendations = []
        
        for result in self.phase_results:
            if result.status == "success" and result.output_data is not None:
                # Extract recommendations based on phase
                pass
        
        return recommendations
    
    def get_phase_status(self) -> Dict[int, str]:
        """Get status of all phases"""
        return {r.phase_number: r.status for r in self.phase_results}
    
    def export_results(self, output_path: Path):
        """Export results to file"""
        output_data = {
            'execution_date': datetime.now().isoformat(),
            'config': asdict(self.config),
            'phase_results': [r.to_dict() for r in self.phase_results],
            'final_output': self.final_output
        }
        
        with open(output_path, 'w') as f:
            json.dump(output_data, f, indent=2, default=str)
        
        logger.info(f"Results exported to {output_path}")

# ============================================================================
# INTEGRATION FUNCTION
# ============================================================================

def integrate_with_beverly_erp(data_path: str) -> SixPhasePlanningEngine:
    """
    Integration point for Beverly Knits ERP system
    """
    engine = SixPhasePlanningEngine(Path(data_path))
    logger.info("6-Phase Planning Engine integrated with Beverly ERP")
    return engine

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    # Example usage
    data_path = Path("ERP Data/New folder")
    
    # Initialize engine with custom config
    config = PlanningConfig(
        forecast_horizon=90,
        safety_stock_service_level=0.98,
        holding_cost_rate=0.25
    )
    
    engine = SixPhasePlanningEngine(data_path, config)
    
    # Execute full planning cycle
    results = engine.execute_full_cycle()
    
    # Export results
    engine.export_results(Path("planning_results.json"))
    
    print(f"Planning cycle completed in {results['execution_time']:.2f} seconds")
    print(f"Success rate: {results['final_output']['success_rate']*100:.1f}%")
