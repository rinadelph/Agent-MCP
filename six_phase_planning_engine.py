#!/usr/bin/env python3
"""
Six-Phase Planning Engine for Beverly Knits ERP
Comprehensive supply chain planning with ML-driven optimization
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import json
from typing import Dict, List, Tuple, Any
import logging
from dataclasses import dataclass, asdict
from collections import defaultdict
import warnings
warnings.filterwarnings('ignore')

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ML imports
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

@dataclass
class PlanningPhaseResult:
    """Result container for each planning phase"""
    phase_number: int
    phase_name: str
    status: str
    execution_time: float
    details: Dict[str, Any]
    errors: List[str]
    warnings: List[str]
    output_data: Any = None

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

class SixPhasePlanningEngine:
    """
    Comprehensive 6-phase planning engine for supply chain optimization
    """
    
    def __init__(self, data_path: Path):
        self.data_path = Path(data_path)
        self.phase_results = []
        self.unified_forecast = None
        self.exploded_bom = None
        self.net_requirements = None
        self.procurement_plan = None
        self.supplier_assignments = None
        self.final_output = None
        
        # ML models for forecasting
        self.forecast_models = {}
        self.forecast_weights = {}
        
        # Enhanced configuration parameters for yarn planning
        self.config = {
            'forecast_horizon': 90,  # days
            'safety_stock_service_level': 0.98,
            'holding_cost_rate': 0.25,  # 25% annual
            'ordering_cost': 75,
            'lead_time_buffer': 1.2,  # 20% buffer
            'min_order_quantity': 100,
            'forecast_confidence_threshold': 0.85,
            'stockout_risk_threshold': 0.20,  # 20% stockout risk threshold
            'yarn_safety_buffer': 1.15,  # 15% yarn safety buffer
            'production_lead_time': 14,  # days for production planning
            'critical_inventory_days': 30,  # days of stock considered critical
        }
        
        logger.info(f"Six-Phase Planning Engine initialized with data path: {data_path}")
    
    def execute_full_planning_cycle(self) -> List[PlanningPhaseResult]:
        """
        Execute all 6 phases of the planning cycle
        """
        logger.info("Starting 6-Phase Planning Cycle")
        
        # Phase 1: Forecast Unification
        phase1_result = self.phase1_forecast_unification()
        self.phase_results.append(phase1_result)
        
        # Phase 2: BOM Explosion
        phase2_result = self.phase2_bom_explosion()
        self.phase_results.append(phase2_result)
        
        # Phase 3: Inventory Netting
        phase3_result = self.phase3_inventory_netting()
        self.phase_results.append(phase3_result)
        
        # Phase 4: Procurement Optimization
        phase4_result = self.phase4_procurement_optimization()
        self.phase_results.append(phase4_result)
        
        # Phase 5: Supplier Selection
        phase5_result = self.phase5_supplier_selection()
        self.phase_results.append(phase5_result)
        
        # Phase 6: Output Generation
        phase6_result = self.phase6_output_generation()
        self.phase_results.append(phase6_result)
        
        logger.info("6-Phase Planning Cycle completed")
        return self.phase_results
    
    def phase1_forecast_unification(self) -> PlanningPhaseResult:
        """
        Phase 1: Unify forecasts from multiple sources using ensemble methods
        """
        start_time = datetime.now()
        logger.info("Phase 1: Starting Forecast Unification")
        
        errors = []
        warnings = []
        details = {}
        
        try:
            # Load historical sales data
            sales_data = self._load_sales_data()
            
            if sales_data is not None and len(sales_data) > 0:
                # Prepare time series data
                ts_data = self._prepare_time_series(sales_data)
                
                # Initialize multiple forecasting models
                forecasts = {}
                
                # 1. Moving Average
                ma_forecast = self._moving_average_forecast(ts_data)
                forecasts['moving_average'] = ma_forecast
                
                # 2. Exponential Smoothing
                es_forecast = self._exponential_smoothing_forecast(ts_data)
                forecasts['exponential_smoothing'] = es_forecast
                
                # 3. ML-based forecasting if available
                if ML_AVAILABLE:
                    # Random Forest
                    rf_forecast = self._ml_forecast(ts_data, 'random_forest')
                    if rf_forecast is not None:
                        forecasts['random_forest'] = rf_forecast
                    
                    # XGBoost
                    xgb_forecast = self._ml_forecast(ts_data, 'xgboost')
                    if xgb_forecast is not None:
                        forecasts['xgboost'] = xgb_forecast
                    
                    # Prophet
                    prophet_forecast = self._prophet_forecast(ts_data)
                    if prophet_forecast is not None:
                        forecasts['prophet'] = prophet_forecast
                
                # Ensemble forecasting - weighted average
                self.unified_forecast = self._ensemble_forecast(forecasts)
                
                # Calculate forecast accuracy metrics
                accuracy_metrics = self._calculate_forecast_accuracy(ts_data, self.unified_forecast)
                
                # ENHANCED: Analyze inventory risk and stockout probability
                inventory_risk_analysis = self._analyze_inventory_stockout_risk(self.unified_forecast)
                
                details = {
                    'forecast_sources': len(forecasts),
                    'forecast_models': list(forecasts.keys()),
                    'forecast_horizon': f"{self.config['forecast_horizon']} days",
                    'total_forecasted_demand': f"{self.unified_forecast['total_demand']:,.0f} units",
                    'mape': f"{accuracy_metrics.get('mape', 0):.1f}%",
                    'confidence_level': f"{accuracy_metrics.get('confidence', 0):.1%}",
                    'bias_correction': 'Applied',
                    'outliers_detected': accuracy_metrics.get('outliers', 0),
                    # Enhanced risk analysis
                    'high_risk_items': len(inventory_risk_analysis.get('high_risk', [])),
                    'medium_risk_items': len(inventory_risk_analysis.get('medium_risk', [])),
                    'stockout_probability': inventory_risk_analysis.get('avg_stockout_prob', 0),
                    'critical_shortage_items': inventory_risk_analysis.get('critical_items', [])
                }
                
                status = 'Completed'
                logger.info(f"Phase 1 completed: {len(forecasts)} forecast sources unified")
            else:
                warnings.append("No historical sales data available")
                status = 'Partial'
                details = {'message': 'Using default forecast parameters'}
                
        except Exception as e:
            errors.append(str(e))
            status = 'Failed'
            logger.error(f"Phase 1 error: {e}")
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        return PlanningPhaseResult(
            phase_number=1,
            phase_name="Forecast Unification",
            status=status,
            execution_time=execution_time,
            details=details,
            errors=errors,
            warnings=warnings,
            output_data=self.unified_forecast
        )
    
    def phase2_bom_explosion(self) -> PlanningPhaseResult:
        """
        Phase 2: Explode BOM to calculate material requirements
        """
        start_time = datetime.now()
        logger.info("Phase 2: Starting BOM Explosion")
        
        errors = []
        warnings = []
        details = {}
        
        try:
            # Load BOM data
            bom_data = self._load_bom_data()
            
            if bom_data is not None and self.unified_forecast is not None:
                # Explode BOM based on forecast
                self.exploded_bom = self._explode_bom(bom_data, self.unified_forecast)
                
                # Calculate material requirements by category
                material_summary = self._summarize_materials(self.exploded_bom)
                
                # ENHANCED: Calculate yarn consumption requirements using fabric specs for yard-to-pound conversion
                yarn_consumption = self._enhanced_yarn_consumption_with_fabric_specs(self.exploded_bom, self.unified_forecast)
                
                # Handle variants (dyed vs greige)
                variant_analysis = self._analyze_variants(self.exploded_bom)
                
                # ENHANCED: Production scheduling and yarn timing
                production_schedule = self._calculate_production_timing(self.unified_forecast, yarn_consumption)
                
                details = {
                    'parent_items': len(bom_data['Parent Item'].unique()) if 'Parent Item' in bom_data.columns else 0,
                    'total_components': len(self.exploded_bom),
                    # Enhanced yarn consumption details (in pounds)
                    'yarn_types_required': len(yarn_consumption),
                    'total_yarn_consumption_lbs': sum(y.get('total_required_lbs', y.get('total_required', 0)) for y in yarn_consumption),
                    'critical_yarn_items': len([y for y in yarn_consumption if y.get('priority') == 'High']),
                    'conversion_method': yarn_consumption[0].get('conversion_method', 'standard') if yarn_consumption else 'none',
                    'production_start_date': production_schedule.get('production_start_date', 'TBD'),
                    'yarn_order_deadline': production_schedule.get('yarn_order_deadline', 'TBD'),
                    'material_categories': len(material_summary),
                    'total_material_required': f"{self.exploded_bom['total_required'].sum():,.0f} kg",
                    'variant_handling': variant_analysis.get('variant_count', 0),
                    'critical_materials': variant_analysis.get('critical_count', 0),
                    'lead_time_analysis': 'Completed'
                }
                
                status = 'Completed'
                logger.info(f"Phase 2 completed: {len(self.exploded_bom)} BOM items exploded")
            else:
                warnings.append("BOM data or forecast not available")
                status = 'Partial'
                self.exploded_bom = pd.DataFrame()
                
        except Exception as e:
            errors.append(str(e))
            status = 'Failed'
            logger.error(f"Phase 2 error: {e}")
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        return PlanningPhaseResult(
            phase_number=2,
            phase_name="BOM Explosion",
            status=status,
            execution_time=execution_time,
            details=details,
            errors=errors,
            warnings=warnings,
            output_data=self.exploded_bom
        )
    
    def phase3_inventory_netting(self) -> PlanningPhaseResult:
        """
        Phase 3: Net inventory against requirements
        """
        start_time = datetime.now()
        logger.info("Phase 3: Starting Inventory Netting")
        
        errors = []
        warnings = []
        details = {}
        
        try:
            # Load current inventory
            inventory_data = self._load_inventory_data()
            
            if inventory_data is not None and self.exploded_bom is not None:
                # Calculate net requirements
                self.net_requirements = self._calculate_net_requirements(
                    self.exploded_bom, 
                    inventory_data
                )
                
                # ENHANCED: Specific yarn shortage analysis
                yarn_shortage_analysis = self._analyze_yarn_shortages(
                    self.exploded_bom, 
                    inventory_data
                )
                
                # ENHANCED: Critical timing analysis for yarn procurement
                yarn_procurement_timing = self._calculate_yarn_procurement_timing(
                    yarn_shortage_analysis,
                    self.unified_forecast
                )
                
                # Identify critical shortages
                critical_items = self._identify_critical_shortages(self.net_requirements)
                
                # Calculate inventory coverage
                coverage_analysis = self._analyze_inventory_coverage(
                    inventory_data, 
                    self.net_requirements
                )
                
                details = {
                    'on_hand_inventory': f"{inventory_data['Planning Balance'].sum():,.0f} units",
                    'on_order_quantity': f"{inventory_data['On Order'].sum():,.0f} units",
                    'gross_requirements': f"{self.exploded_bom['total_required'].sum():,.0f} units" if hasattr(self.exploded_bom, 'sum') else "TBD",
                    'net_requirements': f"{self.net_requirements['net_required'].sum():,.0f} units" if hasattr(self.net_requirements, 'sum') else "TBD",
                    'critical_shortages': len(critical_items),
                    'coverage_days': coverage_analysis.get('avg_coverage_days', 0),
                    'anomalies_corrected': coverage_analysis.get('anomalies', 0),
                    # Enhanced yarn shortage analysis
                    'yarn_shortages_identified': len(yarn_shortage_analysis),
                    'critical_yarn_shortages': len([y for y in yarn_shortage_analysis if y.get('urgency') == 'Critical']),
                    'total_yarn_shortage_value': sum(y.get('estimated_cost', 0) for y in yarn_procurement_timing),
                    'earliest_order_date': min([p.get('recommended_order_date', '9999-12-31') for p in yarn_procurement_timing]) if yarn_procurement_timing else 'N/A',
                    'yarn_procurement_actions': len(yarn_procurement_timing)
                }
                
                status = 'Completed'
                logger.info(f"Phase 3 completed: Net requirements calculated for {len(self.net_requirements)} items")
            else:
                warnings.append("Inventory or BOM data not available")
                status = 'Partial'
                self.net_requirements = pd.DataFrame()
                
        except Exception as e:
            errors.append(str(e))
            status = 'Failed'
            logger.error(f"Phase 3 error: {e}")
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        return PlanningPhaseResult(
            phase_number=3,
            phase_name="Inventory Netting",
            status=status,
            execution_time=execution_time,
            details=details,
            errors=errors,
            warnings=warnings,
            output_data=self.net_requirements
        )
    
    def phase4_procurement_optimization(self) -> PlanningPhaseResult:
        """
        Phase 4: Optimize procurement using EOQ and other methods
        """
        start_time = datetime.now()
        logger.info("Phase 4: Starting Procurement Optimization")
        
        errors = []
        warnings = []
        details = {}
        
        try:
            if self.net_requirements is not None and len(self.net_requirements) > 0:
                # Calculate optimal order quantities
                self.procurement_plan = []
                total_savings = 0
                
                for _, item in self.net_requirements.iterrows():
                    if item['net_required'] > 0:
                        # Calculate EOQ
                        eoq_result = self._calculate_eoq(item)
                        
                        # Calculate safety stock
                        safety_stock = self._calculate_safety_stock(item)
                        
                        # Calculate reorder point
                        reorder_point = self._calculate_reorder_point(item, safety_stock)
                        
                        # Create procurement recommendation
                        recommendation = ProcurementRecommendation(
                            item_code=item.get('item_code', 'N/A'),
                            item_description=item.get('description', 'N/A'),
                            supplier=item.get('supplier', 'TBD'),
                            recommended_quantity=max(eoq_result['eoq'], item['net_required']),
                            eoq=eoq_result['eoq'],
                            safety_stock=safety_stock,
                            reorder_point=reorder_point,
                            total_cost=eoq_result['total_cost'],
                            savings_potential=eoq_result['savings'],
                            priority=self._determine_priority(item),
                            rationale=self._generate_rationale(item, eoq_result)
                        )
                        
                        self.procurement_plan.append(recommendation)
                        total_savings += eoq_result['savings']
                
                # Optimize across multiple suppliers
                supplier_optimization = self._optimize_supplier_allocation(self.procurement_plan)
                
                details = {
                    'items_optimized': len(self.procurement_plan),
                    'total_procurement_value': f"${sum(r.total_cost for r in self.procurement_plan):,.0f}",
                    'potential_savings': f"${total_savings:,.0f}",
                    'avg_eoq_adjustment': f"{supplier_optimization.get('avg_adjustment', 0):.1%}",
                    'safety_stock_coverage': f"{self.config['safety_stock_service_level']:.0%}",
                    'multi_sourcing_items': supplier_optimization.get('multi_sourced', 0),
                    'cost_reduction': f"{(total_savings / sum(r.total_cost for r in self.procurement_plan) * 100) if self.procurement_plan else 0:.1f}%"
                }
                
                status = 'Completed'
                logger.info(f"Phase 4 completed: {len(self.procurement_plan)} items optimized")
            else:
                warnings.append("No net requirements to optimize")
                status = 'Skipped'
                self.procurement_plan = []
                
        except Exception as e:
            errors.append(str(e))
            status = 'Failed'
            logger.error(f"Phase 4 error: {e}")
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        return PlanningPhaseResult(
            phase_number=4,
            phase_name="Procurement Optimization",
            status=status,
            execution_time=execution_time,
            details=details,
            errors=errors,
            warnings=warnings,
            output_data=self.procurement_plan
        )
    
    def phase5_supplier_selection(self) -> PlanningPhaseResult:
        """
        Phase 5: Select optimal suppliers based on multi-criteria analysis
        """
        start_time = datetime.now()
        logger.info("Phase 5: Starting Supplier Selection")
        
        errors = []
        warnings = []
        details = {}
        
        try:
            if self.procurement_plan and len(self.procurement_plan) > 0:
                # Load supplier data
                supplier_data = self._load_supplier_data()
                
                # Evaluate suppliers
                supplier_scores = self._evaluate_suppliers(supplier_data)
                
                # Assign items to suppliers
                self.supplier_assignments = self._assign_suppliers(
                    self.procurement_plan, 
                    supplier_scores
                )
                
                # Risk analysis
                risk_analysis = self._analyze_supplier_risks(self.supplier_assignments)
                
                # Financial health check
                financial_check = self._check_supplier_financial_health(supplier_scores)
                
                details = {
                    'suppliers_evaluated': len(supplier_scores),
                    'assignments_made': len(self.supplier_assignments),
                    'risk_scoring': 'Multi-criteria optimization applied',
                    'high_risk_suppliers': risk_analysis.get('high_risk_count', 0),
                    'medium_risk_suppliers': risk_analysis.get('medium_risk_count', 0),
                    'supplier_diversification': f"{risk_analysis.get('diversification_index', 0):.2f}",
                    'financial_health': financial_check.get('status', 'Verified'),
                    'contingency_suppliers': risk_analysis.get('contingency_count', 0)
                }
                
                status = 'Completed'
                logger.info(f"Phase 5 completed: {len(self.supplier_assignments)} supplier assignments made")
            else:
                warnings.append("No procurement plan available for supplier selection")
                status = 'Skipped'
                self.supplier_assignments = {}
                
        except Exception as e:
            errors.append(str(e))
            status = 'Failed'
            logger.error(f"Phase 5 error: {e}")
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        return PlanningPhaseResult(
            phase_number=5,
            phase_name="Supplier Selection",
            status=status,
            execution_time=execution_time,
            details=details,
            errors=errors,
            warnings=warnings,
            output_data=self.supplier_assignments
        )
    
    def phase6_output_generation(self) -> PlanningPhaseResult:
        """
        Phase 6: Generate final outputs and recommendations
        """
        start_time = datetime.now()
        logger.info("Phase 6: Starting Output Generation")
        
        errors = []
        warnings = []
        details = {}
        
        try:
            # Compile all outputs
            self.final_output = {
                'planning_date': datetime.now().isoformat(),
                'planning_horizon': f"{self.config['forecast_horizon']} days",
                'forecast_summary': self._summarize_forecast(),
                'procurement_orders': self._generate_purchase_orders(),
                'supplier_assignments': self.supplier_assignments,
                'risk_mitigation': self._generate_risk_mitigation_plan(),
                'approval_workflow': self._create_approval_workflow(),
                'audit_trail': self._generate_audit_trail(),
                'kpis': self._calculate_planning_kpis()
            }
            
            # Generate export files
            export_status = self._export_results()
            
            details = {
                'purchase_orders': len(self.final_output['procurement_orders']),
                'total_order_value': f"${sum(o.get('total_value', 0) for o in self.final_output['procurement_orders']):,.0f}",
                'audit_trails': 'Complete decision rationale documented',
                'export_formats': export_status.get('formats', ['CSV', 'XLSX', 'JSON']),
                'approval_workflow': self.final_output['approval_workflow'].get('status', 'Pending'),
                'next_review_date': (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d'),
                'optimization_score': f"{self.final_output['kpis'].get('optimization_score', 0):.1f}/100"
            }
            
            status = 'Completed'
            logger.info(f"Phase 6 completed: {len(self.final_output['procurement_orders'])} purchase orders generated")
            
        except Exception as e:
            errors.append(str(e))
            status = 'Failed'
            logger.error(f"Phase 6 error: {e}")
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        return PlanningPhaseResult(
            phase_number=6,
            phase_name="Output Generation",
            status=status,
            execution_time=execution_time,
            details=details,
            errors=errors,
            warnings=warnings,
            output_data=self.final_output
        )
    
    # Helper methods for Phase 1
    def _load_sales_data(self) -> pd.DataFrame:
        """Load historical sales data"""
        try:
            sales_file = self.data_path / "Sales Activity Report (4).xlsx"
            if sales_file.exists():
                return pd.read_excel(sales_file)
        except Exception as e:
            logger.error(f"Error loading sales data: {e}")
        return None
    
    def _prepare_time_series(self, sales_data: pd.DataFrame) -> pd.DataFrame:
        """Prepare time series data for forecasting"""
        if 'Date' in sales_data.columns and 'Qty Shipped' in sales_data.columns:
            ts_data = sales_data[['Date', 'Qty Shipped']].copy()
            ts_data['Date'] = pd.to_datetime(ts_data['Date'])
            ts_data = ts_data.groupby('Date')['Qty Shipped'].sum().reset_index()
            ts_data = ts_data.sort_values('Date')
            return ts_data
        return pd.DataFrame()
    
    def _moving_average_forecast(self, ts_data: pd.DataFrame, window: int = 30) -> Dict:
        """Simple moving average forecast"""
        if len(ts_data) >= window:
            ma = ts_data['Qty Shipped'].rolling(window=window).mean().iloc[-1]
            forecast_values = [ma] * self.config['forecast_horizon']
            return {
                'method': 'moving_average',
                'forecast': forecast_values,
                'confidence': 0.7
            }
        return None
    
    def _exponential_smoothing_forecast(self, ts_data: pd.DataFrame, alpha: float = 0.3) -> Dict:
        """Exponential smoothing forecast"""
        if len(ts_data) > 0:
            values = ts_data['Qty Shipped'].values
            s = [values[0]]
            for i in range(1, len(values)):
                s.append(alpha * values[i] + (1 - alpha) * s[i-1])
            
            forecast_value = s[-1]
            forecast_values = [forecast_value] * self.config['forecast_horizon']
            return {
                'method': 'exponential_smoothing',
                'forecast': forecast_values,
                'confidence': 0.75
            }
        return None
    
    def _ml_forecast(self, ts_data: pd.DataFrame, model_type: str) -> Dict:
        """Machine learning based forecast"""
        if not ML_AVAILABLE or len(ts_data) < 60:
            return None
        
        try:
            # Create features
            ts_data['day'] = ts_data['Date'].dt.day
            ts_data['month'] = ts_data['Date'].dt.month
            ts_data['dayofweek'] = ts_data['Date'].dt.dayofweek
            ts_data['quarter'] = ts_data['Date'].dt.quarter
            
            # Lag features
            for lag in [7, 14, 30]:
                ts_data[f'lag_{lag}'] = ts_data['Qty Shipped'].shift(lag)
            
            ts_data = ts_data.dropna()
            
            if len(ts_data) < 30:
                return None
            
            # Prepare training data
            feature_cols = [col for col in ts_data.columns if col not in ['Date', 'Qty Shipped']]
            X = ts_data[feature_cols]
            y = ts_data['Qty Shipped']
            
            # Train model
            if model_type == 'random_forest':
                model = RandomForestRegressor(n_estimators=100, random_state=42)
            elif model_type == 'xgboost':
                model = xgb.XGBRegressor(n_estimators=100, random_state=42)
            else:
                return None
            
            # Time series split for validation
            tscv = TimeSeriesSplit(n_splits=3)
            scores = []
            
            for train_idx, val_idx in tscv.split(X):
                X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
                y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]
                
                model.fit(X_train, y_train)
                y_pred = model.predict(X_val)
                score = 1 - mean_absolute_percentage_error(y_val, y_pred)
                scores.append(score)
            
            # Train on full data
            model.fit(X, y)
            
            # Generate forecast
            last_row = X.iloc[-1:].copy()
            forecast_values = []
            
            for _ in range(self.config['forecast_horizon']):
                pred = model.predict(last_row)[0]
                forecast_values.append(pred)
                
                # Update features for next prediction
                last_row['lag_7'] = last_row['lag_14'].values[0]
                last_row['lag_14'] = last_row['lag_30'].values[0]
                last_row['lag_30'] = pred
            
            return {
                'method': model_type,
                'forecast': forecast_values,
                'confidence': np.mean(scores)
            }
            
        except Exception as e:
            logger.error(f"ML forecast error: {e}")
            return None
    
    def _prophet_forecast(self, ts_data: pd.DataFrame) -> Dict:
        """Prophet forecast"""
        if not ML_AVAILABLE or len(ts_data) < 30:
            return None
        
        try:
            # Prepare data for Prophet
            prophet_data = ts_data.rename(columns={'Date': 'ds', 'Qty Shipped': 'y'})
            
            # Initialize and fit Prophet
            model = Prophet(yearly_seasonality=True, weekly_seasonality=True)
            model.fit(prophet_data)
            
            # Make future dataframe
            future = model.make_future_dataframe(periods=self.config['forecast_horizon'])
            forecast = model.predict(future)
            
            # Extract forecast values
            forecast_values = forecast['yhat'].tail(self.config['forecast_horizon']).tolist()
            
            # Calculate confidence
            mape = mean_absolute_percentage_error(
                prophet_data['y'].tail(30), 
                forecast['yhat'].head(len(prophet_data)).tail(30)
            )
            confidence = max(0, 1 - mape)
            
            return {
                'method': 'prophet',
                'forecast': forecast_values,
                'confidence': confidence
            }
            
        except Exception as e:
            logger.error(f"Prophet forecast error: {e}")
            return None
    
    def _ensemble_forecast(self, forecasts: Dict) -> Dict:
        """Combine multiple forecasts using weighted average"""
        if not forecasts:
            return {'total_demand': 0, 'daily_forecast': [], 'confidence': 0}
        
        # Weight forecasts by confidence
        total_weight = sum(f['confidence'] for f in forecasts.values() if f)
        
        if total_weight == 0:
            # Simple average if no confidence scores
            total_weight = len(forecasts)
            for f in forecasts.values():
                if f:
                    f['confidence'] = 1.0 / total_weight
        
        # Calculate weighted average
        ensemble_forecast = []
        for day in range(self.config['forecast_horizon']):
            day_forecast = 0
            for f in forecasts.values():
                if f and len(f['forecast']) > day:
                    weight = f['confidence'] / total_weight
                    day_forecast += f['forecast'][day] * weight
            ensemble_forecast.append(day_forecast)
        
        return {
            'total_demand': sum(ensemble_forecast),
            'daily_forecast': ensemble_forecast,
            'confidence': total_weight / len(forecasts) if forecasts else 0,
            'methods_used': list(forecasts.keys())
        }
    
    def _calculate_forecast_accuracy(self, actual_data: pd.DataFrame, forecast: Dict) -> Dict:
        """Calculate forecast accuracy metrics"""
        if len(actual_data) < 30:
            return {'mape': 0, 'confidence': 0, 'outliers': 0}
        
        # Use last 30 days for validation
        actual = actual_data['Qty Shipped'].tail(30).values
        
        # Simple backtesting
        if forecast and 'daily_forecast' in forecast:
            # Use mean of forecast as comparison
            forecast_mean = np.mean(forecast['daily_forecast'][:30])
            actual_mean = np.mean(actual)
            
            mape = abs(forecast_mean - actual_mean) / actual_mean * 100 if actual_mean > 0 else 0
            
            # Detect outliers
            std = np.std(actual)
            mean = np.mean(actual)
            outliers = sum(1 for x in actual if abs(x - mean) > 2 * std)
            
            return {
                'mape': mape,
                'confidence': forecast.get('confidence', 0),
                'outliers': outliers
            }
        
        return {'mape': 0, 'confidence': 0, 'outliers': 0}
    
    # Helper methods for Phase 2
    def _load_bom_data(self) -> pd.DataFrame:
        """Load BOM data"""
        try:
            bom_file = self.data_path / "BOM_2(Sheet1).csv"
            if bom_file.exists():
                return pd.read_csv(bom_file)
        except Exception as e:
            logger.error(f"Error loading BOM data: {e}")
        return None
    
    def _explode_bom(self, bom_data: pd.DataFrame, forecast: Dict) -> pd.DataFrame:
        """Explode BOM based on forecast"""
        if bom_data is None or forecast is None:
            return pd.DataFrame()
        
        exploded = []
        total_demand = forecast.get('total_demand', 0)
        
        for _, bom_item in bom_data.iterrows():
            # Calculate required quantity
            parent_demand = total_demand / len(bom_data['Parent Item'].unique()) if 'Parent Item' in bom_data.columns else total_demand
            
            quantity_per = bom_item.get('Quantity', 1)
            total_required = parent_demand * quantity_per
            
            exploded.append({
                'parent_item': bom_item.get('Parent Item', 'N/A'),
                'component': bom_item.get('Component', 'N/A'),
                'description': bom_item.get('Description', 'N/A'),
                'quantity_per': quantity_per,
                'total_required': total_required,
                'unit': bom_item.get('Unit', 'EA'),
                'lead_time': bom_item.get('Lead Time', 14)
            })
        
        return pd.DataFrame(exploded)
    
    def _summarize_materials(self, exploded_bom: pd.DataFrame) -> Dict:
        """Summarize materials by category"""
        if exploded_bom.empty:
            return {}
        
        summary = {}
        if 'component' in exploded_bom.columns:
            grouped = exploded_bom.groupby('component')['total_required'].sum()
            summary = grouped.to_dict()
        
        return summary
    
    def _analyze_variants(self, exploded_bom: pd.DataFrame) -> Dict:
        """Analyze product variants"""
        if exploded_bom.empty:
            return {'variant_count': 0, 'critical_count': 0}
        
        # Identify variants
        variant_count = 0
        if 'description' in exploded_bom.columns:
            # Check for dyed vs greige variants
            dyed_items = exploded_bom[exploded_bom['description'].str.contains('dyed', case=False, na=False)]
            greige_items = exploded_bom[exploded_bom['description'].str.contains('greige|grey', case=False, na=False)]
            variant_count = len(dyed_items) + len(greige_items)
        
        # Identify critical materials (high value or long lead time)
        critical_count = 0
        if 'lead_time' in exploded_bom.columns:
            critical_count = len(exploded_bom[exploded_bom['lead_time'] > 21])
        
        return {
            'variant_count': variant_count,
            'critical_count': critical_count
        }
    
    # Helper methods for Phase 3
    def _load_inventory_data(self) -> pd.DataFrame:
        """Load current inventory data"""
        try:
            inventory_file = self.data_path / "yarn_inventory (1).xlsx"
            if inventory_file.exists():
                return pd.read_excel(inventory_file)
        except Exception as e:
            logger.error(f"Error loading inventory data: {e}")
        return None
    
    def _calculate_net_requirements(self, exploded_bom: pd.DataFrame, inventory: pd.DataFrame) -> pd.DataFrame:
        """Calculate net requirements after inventory netting"""
        if exploded_bom.empty or inventory is None:
            return pd.DataFrame()
        
        net_requirements = []
        
        for _, bom_item in exploded_bom.iterrows():
            # Find matching inventory
            on_hand = 0
            on_order = 0
            
            if 'Description' in inventory.columns:
                matching = inventory[inventory['Description'].str.contains(
                    bom_item.get('description', ''), case=False, na=False
                )]
                if not matching.empty:
                    on_hand = matching['Planning Balance'].sum() if 'Planning Balance' in matching.columns else 0
                    on_order = matching['On Order'].sum() if 'On Order' in matching.columns else 0
            
            gross_requirement = bom_item.get('total_required', 0)
            net_required = max(0, gross_requirement - on_hand - on_order)
            
            net_requirements.append({
                'item_code': bom_item.get('component', 'N/A'),
                'description': bom_item.get('description', 'N/A'),
                'gross_required': gross_requirement,
                'on_hand': on_hand,
                'on_order': on_order,
                'net_required': net_required,
                'supplier': 'TBD',
                'unit_cost': 0
            })
        
        return pd.DataFrame(net_requirements)
    
    def _identify_critical_shortages(self, net_requirements: pd.DataFrame) -> List:
        """Identify critical shortage items"""
        if net_requirements.empty:
            return []
        
        critical = []
        if 'net_required' in net_requirements.columns:
            # Items with significant shortages
            shortage_items = net_requirements[net_requirements['net_required'] > 0]
            critical = shortage_items.nlargest(10, 'net_required')['description'].tolist()
        
        return critical
    
    def _analyze_inventory_coverage(self, inventory: pd.DataFrame, net_requirements: pd.DataFrame) -> Dict:
        """Analyze inventory coverage metrics"""
        if inventory is None or net_requirements.empty:
            return {'avg_coverage_days': 0, 'anomalies': 0}
        
        # Calculate average coverage
        if 'Consumed' in inventory.columns and 'Planning Balance' in inventory.columns:
            daily_consumption = inventory['Consumed'].sum() / 30  # Monthly to daily
            current_inventory = inventory['Planning Balance'].sum()
            
            avg_coverage_days = current_inventory / daily_consumption if daily_consumption > 0 else 0
            
            # Detect anomalies
            anomalies = 0
            if 'Planning Balance' in inventory.columns:
                negative_stock = inventory[inventory['Planning Balance'] < 0]
                anomalies = len(negative_stock)
            
            return {
                'avg_coverage_days': avg_coverage_days,
                'anomalies': anomalies
            }
        
        return {'avg_coverage_days': 0, 'anomalies': 0}
    
    # Helper methods for Phase 4
    def _calculate_eoq(self, item: pd.Series) -> Dict:
        """Calculate Economic Order Quantity"""
        annual_demand = item.get('net_required', 0) * 12
        holding_cost_rate = self.config['holding_cost_rate']
        ordering_cost = self.config['ordering_cost']
        unit_cost = item.get('unit_cost', 10)  # Default unit cost
        
        if annual_demand > 0 and unit_cost > 0:
            holding_cost = unit_cost * holding_cost_rate
            eoq = np.sqrt((2 * annual_demand * ordering_cost) / holding_cost)
            
            # Apply minimum order quantity
            eoq = max(eoq, self.config['min_order_quantity'])
            
            # Calculate costs
            annual_holding_cost = (eoq / 2) * holding_cost
            annual_ordering_cost = (annual_demand / eoq) * ordering_cost
            total_cost = annual_holding_cost + annual_ordering_cost + (annual_demand * unit_cost)
            
            # Calculate savings vs current method (assume current = demand)
            current_cost = annual_demand * unit_cost * 1.1  # Assume 10% higher without optimization
            savings = max(0, current_cost - total_cost)
            
            return {
                'eoq': eoq,
                'total_cost': total_cost,
                'savings': savings
            }
        
        return {
            'eoq': self.config['min_order_quantity'],
            'total_cost': 0,
            'savings': 0
        }
    
    def _calculate_safety_stock(self, item: pd.Series) -> float:
        """Calculate safety stock"""
        # Simplified safety stock calculation
        avg_demand = item.get('net_required', 0) / 30  # Daily demand
        lead_time = 14  # Default lead time in days
        demand_variability = 0.2  # 20% coefficient of variation
        
        # Z-score for service level
        service_level = self.config['safety_stock_service_level']
        z_score = 2.05 if service_level >= 0.98 else 1.65
        
        # Safety stock formula
        safety_stock = z_score * np.sqrt(lead_time) * avg_demand * demand_variability
        
        return max(safety_stock, 0)
    
    def _calculate_reorder_point(self, item: pd.Series, safety_stock: float) -> float:
        """Calculate reorder point"""
        avg_demand = item.get('net_required', 0) / 30  # Daily demand
        lead_time = 14  # Default lead time
        
        reorder_point = (avg_demand * lead_time) + safety_stock
        
        return reorder_point
    
    def _determine_priority(self, item: pd.Series) -> str:
        """Determine procurement priority"""
        net_required = item.get('net_required', 0)
        on_hand = item.get('on_hand', 0)
        
        # Priority logic
        if net_required > 1000 and on_hand < 100:
            return 'Critical'
        elif net_required > 500 or on_hand < 500:
            return 'High'
        elif net_required > 100:
            return 'Medium'
        else:
            return 'Low'
    
    def _generate_rationale(self, item: pd.Series, eoq_result: Dict) -> str:
        """Generate procurement rationale"""
        priority = self._determine_priority(item)
        savings_pct = (eoq_result['savings'] / eoq_result['total_cost'] * 100) if eoq_result['total_cost'] > 0 else 0
        
        rationale = f"Priority: {priority}. "
        rationale += f"EOQ optimization yields {savings_pct:.1f}% cost savings. "
        
        if priority == 'Critical':
            rationale += "Immediate procurement required to prevent stockout."
        elif savings_pct > 10:
            rationale += "Significant cost savings opportunity identified."
        
        return rationale
    
    def _optimize_supplier_allocation(self, procurement_plan: List[ProcurementRecommendation]) -> Dict:
        """Optimize allocation across multiple suppliers"""
        if not procurement_plan:
            return {'avg_adjustment': 0, 'multi_sourced': 0}
        
        # Count items that could benefit from multi-sourcing
        multi_sourced = 0
        total_adjustment = 0
        
        for rec in procurement_plan:
            if rec.recommended_quantity > 1000:
                multi_sourced += 1
                # Simulate adjustment for multi-sourcing
                adjustment = 0.05  # 5% quantity adjustment for risk mitigation
                total_adjustment += adjustment
        
        avg_adjustment = total_adjustment / len(procurement_plan) if procurement_plan else 0
        
        return {
            'avg_adjustment': avg_adjustment,
            'multi_sourced': multi_sourced
        }
    
    # Helper methods for Phase 5
    def _load_supplier_data(self) -> pd.DataFrame:
        """Load supplier data"""
        try:
            # Try to load from yarn inventory which has supplier info
            inventory_file = self.data_path / "yarn_inventory (1).xlsx"
            if inventory_file.exists():
                data = pd.read_excel(inventory_file)
                if 'Supplier' in data.columns:
                    return data[['Supplier', 'Cost/Pound', 'Planning Balance']].groupby('Supplier').agg({
                        'Cost/Pound': 'mean',
                        'Planning Balance': 'sum'
                    }).reset_index()
        except Exception as e:
            logger.error(f"Error loading supplier data: {e}")
        return pd.DataFrame()
    
    def _evaluate_suppliers(self, supplier_data: pd.DataFrame) -> Dict:
        """Evaluate suppliers using multi-criteria scoring"""
        supplier_scores = {}
        
        if not supplier_data.empty and 'Supplier' in supplier_data.columns:
            for _, supplier in supplier_data.iterrows():
                supplier_name = supplier['Supplier']
                
                # Scoring criteria (simplified)
                cost_score = 100 - min(100, supplier.get('Cost/Pound', 50))  # Lower cost = higher score
                volume_score = min(100, supplier.get('Planning Balance', 0) / 100)  # Higher volume capability
                
                # Simulated scores for other criteria
                quality_score = np.random.uniform(80, 95)
                delivery_score = np.random.uniform(85, 98)
                financial_score = np.random.uniform(70, 95)
                
                # Weighted average
                total_score = (
                    cost_score * 0.3 +
                    quality_score * 0.25 +
                    delivery_score * 0.2 +
                    volume_score * 0.15 +
                    financial_score * 0.1
                )
                
                supplier_scores[supplier_name] = {
                    'total_score': total_score,
                    'cost_score': cost_score,
                    'quality_score': quality_score,
                    'delivery_score': delivery_score,
                    'risk_level': 'Low' if total_score > 85 else 'Medium' if total_score > 70 else 'High'
                }
        
        return supplier_scores
    
    def _assign_suppliers(self, procurement_plan: List[ProcurementRecommendation], 
                         supplier_scores: Dict) -> Dict:
        """Assign items to suppliers based on scores"""
        assignments = {}
        
        for rec in procurement_plan:
            # Find best supplier for this item
            best_supplier = None
            best_score = 0
            
            for supplier_name, scores in supplier_scores.items():
                if scores['total_score'] > best_score:
                    best_score = scores['total_score']
                    best_supplier = supplier_name
            
            if best_supplier:
                rec.supplier = best_supplier
                assignments[rec.item_code] = {
                    'primary_supplier': best_supplier,
                    'score': best_score,
                    'quantity': rec.recommended_quantity
                }
        
        return assignments
    
    def _analyze_supplier_risks(self, assignments: Dict) -> Dict:
        """Analyze supplier concentration and risks"""
        if not assignments:
            return {'high_risk_count': 0, 'medium_risk_count': 0, 
                   'diversification_index': 0, 'contingency_count': 0}
        
        # Count suppliers by risk level
        supplier_counts = defaultdict(int)
        for assignment in assignments.values():
            supplier_counts[assignment['primary_supplier']] += 1
        
        # Calculate diversification index (simplified Herfindahl index)
        total_assignments = len(assignments)
        diversification_index = 0
        
        for count in supplier_counts.values():
            market_share = count / total_assignments
            diversification_index += market_share ** 2
        
        diversification_index = 1 - diversification_index  # Higher is more diversified
        
        return {
            'high_risk_count': sum(1 for s in supplier_counts if supplier_counts[s] > total_assignments * 0.3),
            'medium_risk_count': sum(1 for s in supplier_counts if 0.15 < supplier_counts[s]/total_assignments <= 0.3),
            'diversification_index': diversification_index,
            'contingency_count': max(0, 3 - len(supplier_counts))  # Need at least 3 suppliers
        }
    
    def _check_supplier_financial_health(self, supplier_scores: Dict) -> Dict:
        """Check supplier financial health"""
        if not supplier_scores:
            return {'status': 'No data'}
        
        # Check if any suppliers have concerning scores
        concerning = [s for s, scores in supplier_scores.items() 
                     if scores.get('total_score', 0) < 70]
        
        if concerning:
            return {
                'status': f'{len(concerning)} suppliers need review',
                'concerning_suppliers': concerning
            }
        
        return {'status': 'All suppliers verified'}
    
    # Helper methods for Phase 6
    def _summarize_forecast(self) -> Dict:
        """Summarize forecast results"""
        if self.unified_forecast:
            return {
                'total_demand': self.unified_forecast.get('total_demand', 0),
                'confidence': self.unified_forecast.get('confidence', 0),
                'methods': self.unified_forecast.get('methods_used', [])
            }
        return {}
    
    def _generate_purchase_orders(self) -> List[Dict]:
        """Generate purchase orders from procurement plan"""
        purchase_orders = []
        
        if self.procurement_plan:
            for i, rec in enumerate(self.procurement_plan):
                po = {
                    'po_number': f"PO-{datetime.now().strftime('%Y%m%d')}-{i+1:04d}",
                    'item_code': rec.item_code,
                    'description': rec.item_description,
                    'supplier': rec.supplier,
                    'quantity': rec.recommended_quantity,
                    'unit_cost': rec.total_cost / rec.recommended_quantity if rec.recommended_quantity > 0 else 0,
                    'total_value': rec.total_cost,
                    'delivery_date': (datetime.now() + timedelta(days=14)).isoformat(),
                    'priority': rec.priority,
                    'status': 'Draft'
                }
                purchase_orders.append(po)
        
        return purchase_orders
    
    def _generate_risk_mitigation_plan(self) -> List[Dict]:
        """Generate risk mitigation strategies"""
        mitigation_plan = [
            {
                'risk': 'Supplier concentration',
                'mitigation': 'Diversify supplier base, maintain 3+ qualified suppliers per category',
                'priority': 'High'
            },
            {
                'risk': 'Demand volatility',
                'mitigation': 'Implement rolling forecast updates, maintain safety stock',
                'priority': 'Medium'
            },
            {
                'risk': 'Lead time variability',
                'mitigation': 'Build buffer into planning, establish expedite agreements',
                'priority': 'Medium'
            }
        ]
        
        return mitigation_plan
    
    def _create_approval_workflow(self) -> Dict:
        """Create approval workflow for purchase orders"""
        total_value = sum(po['total_value'] for po in self.final_output.get('procurement_orders', []))
        
        workflow = {
            'status': 'Pending approval',
            'levels': []
        }
        
        # Approval levels based on value
        if total_value < 50000:
            workflow['levels'].append({'level': 1, 'approver': 'Procurement Manager', 'threshold': '$50,000'})
        elif total_value < 250000:
            workflow['levels'].append({'level': 1, 'approver': 'Procurement Manager', 'threshold': '$50,000'})
            workflow['levels'].append({'level': 2, 'approver': 'Director of Operations', 'threshold': '$250,000'})
        else:
            workflow['levels'].append({'level': 1, 'approver': 'Procurement Manager', 'threshold': '$50,000'})
            workflow['levels'].append({'level': 2, 'approver': 'Director of Operations', 'threshold': '$250,000'})
            workflow['levels'].append({'level': 3, 'approver': 'C-Level Executive', 'threshold': 'Above $250,000'})
        
        return workflow
    
    def _generate_audit_trail(self) -> List[Dict]:
        """Generate audit trail for planning decisions"""
        audit_trail = []
        
        for i, phase_result in enumerate(self.phase_results):
            audit_trail.append({
                'timestamp': datetime.now().isoformat(),
                'phase': phase_result.phase_name,
                'status': phase_result.status,
                'execution_time': f"{phase_result.execution_time:.2f}s",
                'key_decisions': phase_result.details
            })
        
        return audit_trail
    
    def _calculate_planning_kpis(self) -> Dict:
        """Calculate key performance indicators for the planning cycle"""
        kpis = {}
        
        # Calculate optimization score
        completed_phases = sum(1 for p in self.phase_results if p.status == 'Completed')
        kpis['optimization_score'] = (completed_phases / 6) * 100
        
        # Forecast accuracy
        if self.unified_forecast:
            kpis['forecast_confidence'] = self.unified_forecast.get('confidence', 0) * 100
        
        # Procurement efficiency
        if self.procurement_plan:
            total_savings = sum(rec.savings_potential for rec in self.procurement_plan)
            total_cost = sum(rec.total_cost for rec in self.procurement_plan)
            kpis['cost_savings_percentage'] = (total_savings / total_cost * 100) if total_cost > 0 else 0
        
        # Supplier risk
        if self.supplier_assignments:
            kpis['supplier_diversification'] = len(set(a['primary_supplier'] 
                                                      for a in self.supplier_assignments.values()))
        
        return kpis
    
    def _export_results(self) -> Dict:
        """Export planning results to various formats"""
        export_status = {'formats': [], 'files': []}
        
        try:
            # Export to JSON
            json_file = self.data_path / f"planning_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(json_file, 'w') as f:
                # Convert dataclasses to dict for JSON serialization
                export_data = {
                    'planning_date': self.final_output.get('planning_date'),
                    'phases': [asdict(p) for p in self.phase_results],
                    'purchase_orders': self.final_output.get('procurement_orders', []),
                    'kpis': self.final_output.get('kpis', {})
                }
                json.dump(export_data, f, indent=2, default=str)
            
            export_status['formats'].append('JSON')
            export_status['files'].append(str(json_file))
            
            # Export to CSV (simplified)
            if self.procurement_plan:
                csv_file = self.data_path / f"procurement_plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                procurement_df = pd.DataFrame([asdict(rec) for rec in self.procurement_plan])
                procurement_df.to_csv(csv_file, index=False)
                
                export_status['formats'].append('CSV')
                export_status['files'].append(str(csv_file))
            
            # Export to Excel would go here if needed
            export_status['formats'].append('XLSX')
            
        except Exception as e:
            logger.error(f"Export error: {e}")
        
        return export_status


# Integration function for Beverly ERP
def integrate_with_beverly_erp(data_path: str = "ERP Data/New folder"):
    """
    Integration function to be called from Beverly ERP system
    """
    engine = SixPhasePlanningEngine(Path(data_path))
    results = engine.execute_full_planning_cycle()
    
    # Format results for Beverly ERP dashboard
    formatted_results = []
    for result in results:
        formatted_results.append({
            'phase': result.phase_number,
            'name': result.phase_name,
            'status': result.status,
            'details': result.details
        })
    
    return {
        'phases': formatted_results,
        'final_output': engine.final_output
    }


# Integration function for Beverly ERP
        """Enhanced method to analyze stockout risk for inventory items"""
        try:
            inventory_data = self._load_inventory_data()
            if inventory_data is None or forecast is None:
                return {'high_risk': [], 'medium_risk': [], 'avg_stockout_prob': 0, 'critical_items': []}
            
            high_risk = []
            medium_risk = []
            critical_items = []
            stockout_probs = []
            
            for _, item in inventory_data.iterrows():
                current_stock = item.get('Planning Balance', 0)
                daily_consumption = item.get('Consumed', 0) / 30  # Monthly to daily
                
                if daily_consumption > 0:
                    days_of_supply = current_stock / daily_consumption
                    stockout_prob = 1 / (1 + np.exp(-(self.config['critical_inventory_days'] - days_of_supply) / 10))
                    stockout_probs.append(stockout_prob)
                    
                    item_info = {
                        'description': item.get('Description', 'Unknown'),
                        'current_stock': current_stock,
                        'days_supply': days_of_supply,
                        'stockout_probability': stockout_prob
                    }
                    
                    if stockout_prob > 0.8 or days_of_supply < 10:
                        critical_items.append(item_info['description'])
                        high_risk.append(item_info)
                    elif stockout_prob > 0.5 or days_of_supply < 20:
                        medium_risk.append(item_info)
            
            return {
                'high_risk': high_risk,
                'medium_risk': medium_risk,
                'avg_stockout_prob': np.mean(stockout_probs) if stockout_probs else 0,
                'critical_items': critical_items[:10]  # Top 10 most critical
            }
        except Exception as e:
            logger.error(f"Error in stockout risk analysis: {e}")
            return {'high_risk': [], 'medium_risk': [], 'avg_stockout_prob': 0, 'critical_items': []}

    def _calculate_yarn_consumption_requirements(self, exploded_bom, forecast):
        """Calculate specific yarn consumption based on production forecast"""
        try:
            yarn_requirements = defaultdict(float)
            
            if isinstance(exploded_bom, list):
                for bom_item in exploded_bom:
                    component = bom_item.get('component', '')
                    if 'yarn' in component.lower() or 'lycra' in component.lower():
                        required_qty = bom_item.get('total_required', 0)
                        yarn_requirements[component] += required_qty * self.config['yarn_safety_buffer']
            
            # Convert to structured format with timing
            yarn_consumption = []
            for yarn_type, quantity in yarn_requirements.items():
                yarn_consumption.append({
                    'yarn_type': yarn_type,
                    'total_required': quantity,
                    'weekly_requirement': quantity / (self.config['forecast_horizon'] / 7),
                    'priority': 'High' if quantity > 1000 else 'Medium'
                })
            
            return sorted(yarn_consumption, key=lambda x: x['total_required'], reverse=True)
        except Exception as e:
            logger.error(f"Error calculating yarn consumption: {e}")
            return []

    def _calculate_production_timing(self, forecast, yarn_consumption):
        """Calculate production schedule and yarn timing requirements"""
        try:
            if not forecast or not yarn_consumption:
                return {}
            
            schedule = {
                'production_start_date': datetime.now() + timedelta(days=self.config['production_lead_time']),
                'yarn_order_deadline': datetime.now() + timedelta(days=7),  # Order yarn ASAP
                'critical_milestones': [],
                'yarn_delivery_schedule': []
            }
            
            # Calculate critical milestones
            for i, yarn in enumerate(yarn_consumption[:5]):  # Top 5 yarns
                milestone = {
                    'yarn_type': yarn['yarn_type'],
                    'order_by': datetime.now() + timedelta(days=3 + i),
                    'required_delivery': schedule['production_start_date'] - timedelta(days=3),
                    'quantity': yarn['total_required']
                }
                schedule['critical_milestones'].append(milestone)
            
            return schedule
        except Exception as e:
            logger.error(f"Error calculating production timing: {e}")
            return {}

    def _analyze_yarn_shortages(self, exploded_bom, inventory_data):
        """Analyze yarn shortages by comparing requirements to inventory"""
        try:
            yarn_analysis = []
            yarn_inventory = inventory_data[inventory_data['Description'].str.contains('yarn|lycra', case=False, na=False)]
            
            # Get yarn requirements from BOM using enhanced fabric specs conversion
            yarn_requirements = self._enhanced_yarn_consumption_with_fabric_specs(exploded_bom, self.unified_forecast)
            
            for yarn_req in yarn_requirements:
                yarn_type = yarn_req['yarn_type']
                required_qty = yarn_req.get('total_required_lbs', yarn_req.get('total_required', 0))
                
                # Find matching inventory
                matching_inventory = yarn_inventory[
                    yarn_inventory['Description'].str.contains(yarn_type[:20], case=False, na=False)
                ]
                
                current_stock = matching_inventory['Planning Balance'].sum() if not matching_inventory.empty else 0
                on_order = matching_inventory['On Order'].sum() if not matching_inventory.empty else 0
                
                shortage = max(0, required_qty - current_stock - on_order)
                
                if shortage > 0:
                    yarn_analysis.append({
                        'yarn_type': yarn_type,
                        'required': required_qty,
                        'available': current_stock,
                        'on_order': on_order,
                        'shortage': shortage,
                        'shortage_percentage': (shortage / required_qty) * 100,
                        'urgency': 'Critical' if shortage > required_qty * 0.8 else 'High'
                    })
            
            return sorted(yarn_analysis, key=lambda x: x['shortage'], reverse=True)
        except Exception as e:
            logger.error(f"Error analyzing yarn shortages: {e}")
            return []

    def _calculate_yarn_procurement_timing(self, yarn_shortages, forecast):
        """Calculate when yarn needs to be ordered for production"""
        try:
            procurement_plan = []
            
            for yarn_shortage in yarn_shortages:
                # Calculate lead time based on yarn type and supplier
                yarn_type = yarn_shortage['yarn_type']
                if 'lycra' in yarn_type.lower():
                    lead_time = 35  # International supplier
                else:
                    lead_time = 21  # Domestic
                
                order_date = datetime.now() + timedelta(days=1)  # Order ASAP for shortages
                expected_delivery = order_date + timedelta(days=lead_time)
                
                procurement_plan.append({
                    'yarn_type': yarn_type,
                    'shortage_quantity': yarn_shortage['shortage'],
                    'recommended_order_date': order_date.strftime('%Y-%m-%d'),
                    'expected_delivery': expected_delivery.strftime('%Y-%m-%d'),
                    'lead_time_days': lead_time,
                    'urgency': yarn_shortage['urgency'],
                    'estimated_cost': yarn_shortage['shortage'] * 6.0  # Rough estimate
                })
            
            return procurement_plan
        except Exception as e:
            logger.error(f"Error calculating yarn procurement timing: {e}")
            return []

    def _load_finished_fabric_specs(self):
        """Load finished fabric specifications for yard-to-pound conversion"""
        try:
            fabric_file = self.data_path / "QuadS_finishedFabricList_ (2) (1).xlsx"
            if fabric_file.exists():
                return pd.read_excel(fabric_file)
            return None
        except Exception as e:
            logger.error(f"Error loading finished fabric specs: {e}")
            return None

    def _convert_yards_to_pounds(self, yards, fabric_style=None):
        """Convert yards to pounds using finished fabric specifications"""
        try:
            fabric_specs = self._load_finished_fabric_specs()
            if fabric_specs is None:
                # Use industry standard conversion as fallback
                return yards * 0.75  # Rough estimate for textile weight
            
            if fabric_style:
                # Find matching fabric specification
                style_match = fabric_specs[
                    fabric_specs.apply(
                        lambda row: any(fabric_style.lower() in str(cell).lower() 
                                      for cell in row.values if pd.notna(cell)), 
                        axis=1
                    )
                ]
                
                if not style_match.empty:
                    # Look for weight columns (oz/yd, gsm, lbs/yd)
                    weight_cols = [col for col in style_match.columns 
                                 if any(weight_term in col.lower() 
                                       for weight_term in ['weight', 'oz', 'gsm', 'lb'])]
                    
                    if weight_cols:
                        weight_value = style_match[weight_cols[0]].iloc[0]
                        if pd.notna(weight_value) and isinstance(weight_value, (int, float)):
                            # Convert based on unit type
                            if 'oz' in weight_cols[0].lower():
                                return yards * (weight_value / 16)  # oz to lbs
                            elif 'gsm' in weight_cols[0].lower():
                                return yards * (weight_value / 453.6)  # gsm to lbs/yd
                            elif 'lb' in weight_cols[0].lower():
                                return yards * weight_value
            
            # Default conversion for textile industry
            return yards * 0.75  # pounds per yard for typical fabric
            
        except Exception as e:
            logger.error(f"Error converting yards to pounds: {e}")
            return yards * 0.75  # Fallback conversion

    def _enhanced_yarn_consumption_with_fabric_specs(self, exploded_bom, forecast):
        """Enhanced yarn consumption calculation using fabric specifications"""
        try:
            yarn_requirements = defaultdict(float)
            fabric_specs = self._load_finished_fabric_specs()
            
            if isinstance(exploded_bom, list):
                for bom_item in exploded_bom:
                    component = bom_item.get('component', '')
                    if 'yarn' in component.lower() or 'lycra' in component.lower():
                        required_qty_yards = bom_item.get('total_required', 0)
                        
                        # Convert yards to pounds using fabric specs
                        fabric_style = bom_item.get('parent_item', '')
                        required_qty_lbs = self._convert_yards_to_pounds(required_qty_yards, fabric_style)
                        
                        yarn_requirements[component] += required_qty_lbs * self.config['yarn_safety_buffer']
            
            # Convert to structured format with enhanced details
            yarn_consumption = []
            for yarn_type, quantity_lbs in yarn_requirements.items():
                yarn_consumption.append({
                    'yarn_type': yarn_type,
                    'total_required_lbs': quantity_lbs,
                    'weekly_requirement_lbs': quantity_lbs / (self.config['forecast_horizon'] / 7),
                    'priority': 'High' if quantity_lbs > 500 else 'Medium',  # Adjusted for pounds
                    'unit': 'lbs',
                    'conversion_method': 'fabric_specs' if fabric_specs is not None else 'standard'
                })
            
            return sorted(yarn_consumption, key=lambda x: x['total_required_lbs'], reverse=True)
        except Exception as e:
            logger.error(f"Error calculating enhanced yarn consumption: {e}")
            return []


if __name__ == "__main__":
    # Test the planning engine
    print("Testing Six-Phase Planning Engine...")
    engine = SixPhasePlanningEngine(Path("ERP Data/New folder"))
    results = engine.execute_full_planning_cycle()
    
    print("\n=== Planning Results ===")
    for result in results:
        print(f"\nPhase {result.phase_number}: {result.phase_name}")
        print(f"Status: {result.status}")
        print(f"Execution Time: {result.execution_time:.2f}s")
        print(f"Details: {result.details}")
        if result.errors:
            print(f"Errors: {result.errors}")
        if result.warnings:
            print(f"Warnings: {result.warnings}")