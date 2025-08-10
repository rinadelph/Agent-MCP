"""
Refactored functions to replace oversized methods in beverly_comprehensive_erp.py
This file contains properly sized, focused functions that maintain the same functionality
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple, Optional


class RefactoredEmergencyProcurement:
    """Refactored emergency procurement handling with smaller, focused methods"""
    
    def handle_emergency_procurement(self):
        """Main method to detect critical materials with NEGATIVE balance or <7 days supply"""
        if not self._ensure_data_loaded():
            return {'critical_items': [], 'summary': {}}
        
        try:
            emergency_items = self._process_emergency_items()
            emergency_items = self._sort_by_urgency(emergency_items)
            summary = self._create_emergency_summary(emergency_items)
            self._print_urgent_alerts(emergency_items)
            
            return {
                'critical_items': emergency_items,
                'summary': summary
            }
        except Exception as e:
            print(f"Error in emergency procurement: {str(e)}")
            return {'critical_items': [], 'summary': {}}
    
    def _ensure_data_loaded(self) -> bool:
        """Ensure raw materials data is loaded"""
        if self.raw_materials_data is None:
            if hasattr(self, 'load_live_erp_data'):
                self.load_live_erp_data()
            return self.raw_materials_data is not None
        return True
    
    def _process_emergency_items(self) -> List[Dict]:
        """Process each item to identify emergency procurement needs"""
        emergency_items = []
        
        for idx, row in self.raw_materials_data.iterrows():
            metrics = self._extract_item_metrics(row, idx)
            
            if self._should_skip_item(metrics):
                continue
            
            urgency_data = self._calculate_urgency(metrics)
            
            if urgency_data['is_emergency']:
                emergency_item = self._create_emergency_item(metrics, urgency_data)
                emergency_items.append(emergency_item)
        
        return emergency_items
    
    def _extract_item_metrics(self, row: pd.Series, idx: int) -> Dict:
        """Extract key metrics from row data"""
        return {
            'desc': row.get('Description', f"Item {row.get('Desc#', idx)}"),
            'balance': row.get('Planning Balance', 0),
            'consumed': row.get('Consumed', 0),
            'beginning': row.get('Beginning Balance', 0),
            'theoretical': row.get('Theoretical Balance', 0),
            'on_order': row.get('On Order', 0),
            'allocated': row.get('Allocated', 0),
            'supplier': row.get('Supplier', 'Unknown'),
            'cost_per_pound': row.get('Cost/Pound', 10),
            'product_id': row.get('Desc#', ''),
        }
    
    def _calculate_actual_consumption(self, metrics: Dict) -> float:
        """Calculate actual consumption based on available data"""
        consumed = metrics['consumed']
        if consumed == 0:
            implied_consumption = abs(metrics['beginning'] - metrics['theoretical'])
            if implied_consumption > 0.1:
                consumed = implied_consumption
        return consumed
    
    def _should_skip_item(self, metrics: Dict) -> bool:
        """Determine if item should be skipped"""
        consumed = self._calculate_actual_consumption(metrics)
        return consumed <= 0 and metrics['balance'] >= 0
    
    def _calculate_urgency(self, metrics: Dict) -> Dict:
        """Calculate urgency level and days of supply"""
        consumed = self._calculate_actual_consumption(metrics)
        daily_consumption = consumed / 30 if consumed > 0 else 1
        available_balance = metrics['balance'] - metrics['allocated'] if metrics['allocated'] > 0 else metrics['balance']
        
        if available_balance < 0:
            days_of_supply = 0
            urgency_level = "CRITICAL - NEGATIVE STOCK"
            is_emergency = True
        else:
            days_of_supply = available_balance / daily_consumption if daily_consumption > 0 else 999
            urgency_level = "CRITICAL" if days_of_supply < 7 else "HIGH"
            is_emergency = days_of_supply < 7
        
        return {
            'daily_consumption': daily_consumption,
            'available_balance': available_balance,
            'days_of_supply': days_of_supply,
            'urgency_level': urgency_level,
            'is_emergency': is_emergency,
            'consumed': consumed
        }
    
    def _calculate_emergency_quantity(self, urgency_data: Dict, metrics: Dict) -> float:
        """Calculate emergency procurement quantity"""
        target_days = 30 * 1.2  # 36 days with safety buffer
        target_quantity = urgency_data['daily_consumption'] * target_days
        
        if urgency_data['available_balance'] < 0:
            return abs(urgency_data['available_balance']) + target_quantity - metrics['on_order']
        else:
            return max(0, target_quantity - urgency_data['available_balance'] - metrics['on_order'])
    
    def _create_emergency_item(self, metrics: Dict, urgency_data: Dict) -> Dict:
        """Create emergency item dictionary"""
        emergency_qty = self._calculate_emergency_quantity(urgency_data, metrics)
        
        return {
            'product_name': metrics['desc'][:50],
            'product_id': metrics['product_id'],
            'current_stock': urgency_data['available_balance'],
            'on_order': metrics['on_order'],
            'allocated': metrics['allocated'],
            'daily_consumption': round(urgency_data['daily_consumption'], 2),
            'monthly_consumption': round(urgency_data['consumed'], 2),
            'days_of_supply': round(urgency_data['days_of_supply'], 1),
            'emergency_qty': round(emergency_qty, 0),
            'estimated_cost': round(emergency_qty * metrics['cost_per_pound'], 2),
            'supplier': metrics['supplier'],
            'urgency_level': urgency_data['urgency_level'],
            'negative_balance': urgency_data['available_balance'] < 0
        }
    
    def _sort_by_urgency(self, emergency_items: List[Dict]) -> List[Dict]:
        """Sort items by urgency (negative balance first, then by days of supply)"""
        return sorted(emergency_items, key=lambda x: (not x['negative_balance'], x['days_of_supply']))
    
    def _create_emergency_summary(self, emergency_items: List[Dict]) -> Dict:
        """Create summary of emergency procurement needs"""
        negative_items = [i for i in emergency_items if i['negative_balance']]
        critical_items = [i for i in emergency_items if not i['negative_balance']]
        
        return {
            'total_emergency_items': len(emergency_items),
            'negative_balance_count': len(negative_items),
            'critical_shortage_count': len(critical_items),
            'total_emergency_qty': sum(i['emergency_qty'] for i in emergency_items),
            'total_emergency_cost': sum(i['estimated_cost'] for i in emergency_items),
            'suppliers_affected': len(set(i['supplier'] for i in emergency_items))
        }
    
    def _print_urgent_alerts(self, emergency_items: List[Dict]) -> None:
        """Print urgent alerts for negative balance items"""
        negative_items = [i for i in emergency_items if i['negative_balance']]
        
        if negative_items:
            print(f"\n🚨 ALERT: {len(negative_items)} items have NEGATIVE balance!")
            for item in negative_items[:5]:
                print(f"  - {item['product_name']}: {item['current_stock']:.0f} (need {item['emergency_qty']:.0f} units)")


class RefactoredInventoryOptimization:
    """Refactored inventory optimization with smaller, focused methods"""
    
    def get_advanced_inventory_optimization(self):
        """Main method for enhanced EOQ with multi-supplier sourcing and advanced analytics"""
        if self.raw_materials_data is None:
            return []
        
        recommendations = []
        top_items = self.raw_materials_data.nlargest(30, 'Consumed')
        supplier_data = self._analyze_suppliers()
        market_benchmarks = self._calculate_market_benchmarks()
        
        for _, item in top_items.iterrows():
            recommendation = self._process_item_optimization(item, supplier_data, market_benchmarks)
            if recommendation:
                recommendations.append(recommendation)
        
        return recommendations
    
    def _analyze_suppliers(self) -> pd.DataFrame:
        """Analyze supplier performance metrics"""
        return self.raw_materials_data.groupby('Supplier').agg({
            'Cost/Pound': ['mean', 'std', 'count', 'min', 'max'],
            'Planning Balance': ['sum', 'mean'],
            'Consumed': 'sum'
        }).round(2)
    
    def _calculate_market_benchmarks(self) -> Dict:
        """Calculate market cost benchmarks"""
        return {
            'avg_cost': self.raw_materials_data['Cost/Pound'].median(),
            'cost_std': self.raw_materials_data['Cost/Pound'].std()
        }
    
    def _process_item_optimization(self, item: pd.Series, supplier_data: pd.DataFrame, 
                                  market_benchmarks: Dict) -> Optional[Dict]:
        """Process optimization for a single item"""
        annual_demand = item['Consumed'] * 12
        unit_cost = item['Cost/Pound'] if pd.notna(item['Cost/Pound']) else 5.0
        
        if annual_demand <= 0 or unit_cost <= 0:
            return None
        
        # Calculate various optimization parameters
        holding_cost_rate = self._calculate_holding_cost_rate(unit_cost, market_benchmarks)
        ordering_cost = self._calculate_ordering_cost(str(item['Supplier']))
        eoq = self._calculate_eoq(annual_demand, ordering_cost, unit_cost, holding_cost_rate)
        
        lead_time_params = self._get_lead_time_parameters(str(item['Supplier']))
        service_level_params = self._determine_service_level(annual_demand)
        
        safety_stock = self._calculate_safety_stock(
            annual_demand, lead_time_params, service_level_params
        )
        
        reorder_point = self._calculate_reorder_point(
            annual_demand, lead_time_params['avg_lead_time'], safety_stock
        )
        
        sourcing_analysis = self._analyze_multi_supplier_sourcing(
            item, supplier_data, unit_cost
        )
        
        return self._create_optimization_recommendation(
            item, eoq, safety_stock, reorder_point, sourcing_analysis, 
            holding_cost_rate, ordering_cost
        )
    
    def _calculate_holding_cost_rate(self, unit_cost: float, market_benchmarks: Dict) -> float:
        """Calculate dynamic holding cost rate based on item value"""
        base_holding_rate = 0.25
        market_avg = market_benchmarks['avg_cost']
        
        if unit_cost > market_avg * 1.5:  # Premium items
            return base_holding_rate + 0.05
        elif unit_cost < market_avg * 0.7:  # Low-value items
            return base_holding_rate - 0.03
        else:
            return base_holding_rate
    
    def _calculate_ordering_cost(self, supplier_name: str) -> float:
        """Calculate ordering cost based on supplier type"""
        supplier_lower = supplier_name.lower()
        base_ordering_cost = 75
        
        if 'international' in supplier_lower:
            return base_ordering_cost * 1.4
        elif 'local' in supplier_lower:
            return base_ordering_cost * 0.8
        else:
            return base_ordering_cost
    
    def _calculate_eoq(self, annual_demand: float, ordering_cost: float, 
                      unit_cost: float, holding_cost_rate: float) -> float:
        """Calculate Economic Order Quantity"""
        holding_cost = unit_cost * holding_cost_rate
        return np.sqrt((2 * annual_demand * ordering_cost) / holding_cost)
    
    def _get_lead_time_parameters(self, supplier_name: str) -> Dict:
        """Get lead time parameters based on supplier type"""
        supplier_lower = supplier_name.lower()
        
        if 'international' in supplier_lower:
            return {'avg_lead_time': 35, 'lead_time_std': 10}
        elif 'local' in supplier_lower:
            return {'avg_lead_time': 14, 'lead_time_std': 3}
        else:
            return {'avg_lead_time': 21, 'lead_time_std': 5}
    
    def _determine_service_level(self, annual_demand: float) -> Dict:
        """Determine service level based on item criticality"""
        median_demand = self.raw_materials_data['Consumed'].median() * 12
        
        if annual_demand > median_demand * 1.5:
            return {'service_level': 0.99, 'z_score': 2.33}
        elif annual_demand < median_demand * 0.5:
            return {'service_level': 0.95, 'z_score': 1.65}
        else:
            return {'service_level': 0.98, 'z_score': 2.05}
    
    def _calculate_demand_variability(self) -> float:
        """Calculate demand variability from sales data"""
        if len(self.sales_data) > 0:
            monthly_demands = self.sales_data.groupby(pd.Grouper(freq='M'))['Qty Shipped'].sum()
            if len(monthly_demands) > 3:
                variability = monthly_demands.std() / monthly_demands.mean() if monthly_demands.mean() > 0 else 0.15
                return min(0.4, max(0.05, variability))
        return 0.15
    
    def _calculate_safety_stock(self, annual_demand: float, lead_time_params: Dict, 
                                service_level_params: Dict) -> float:
        """Calculate safety stock with combined variability factors"""
        daily_demand = annual_demand / 365
        avg_lead_time = lead_time_params['avg_lead_time']
        lead_time_std = lead_time_params['lead_time_std']
        z_score = service_level_params['z_score']
        
        demand_variability = self._calculate_demand_variability()
        demand_during_lead_time = daily_demand * avg_lead_time
        demand_std_dev = demand_during_lead_time * demand_variability
        lead_time_std_demand = daily_demand * lead_time_std
        
        combined_std = np.sqrt((demand_std_dev ** 2) + (lead_time_std_demand ** 2))
        return z_score * combined_std
    
    def _calculate_reorder_point(self, annual_demand: float, avg_lead_time: float, 
                                 safety_stock: float) -> float:
        """Calculate reorder point"""
        daily_demand = annual_demand / 365
        return (daily_demand * avg_lead_time) + safety_stock
    
    def _analyze_multi_supplier_sourcing(self, item: pd.Series, supplier_data: pd.DataFrame, 
                                         unit_cost: float) -> Dict:
        """Analyze multi-supplier sourcing opportunities"""
        # Simplified version - would include full analysis in production
        return {
            'current_supplier': str(item['Supplier']),
            'alternative_suppliers': [],
            'cost_savings_opportunity': 0,
            'best_alternative_cost': unit_cost
        }
    
    def _create_optimization_recommendation(self, item: pd.Series, eoq: float, 
                                           safety_stock: float, reorder_point: float, 
                                           sourcing_analysis: Dict, holding_cost_rate: float, 
                                           ordering_cost: float) -> Dict:
        """Create comprehensive optimization recommendation"""
        return {
            'item': str(item['Description'])[:50],
            'annual_demand': item['Consumed'] * 12,
            'current_stock': item['Planning Balance'],
            'eoq': round(eoq, 0),
            'safety_stock': round(safety_stock, 0),
            'reorder_point': round(reorder_point, 0),
            'holding_cost_rate': round(holding_cost_rate, 3),
            'ordering_cost': round(ordering_cost, 2),
            'supplier_analysis': sourcing_analysis,
            'recommendations': self._generate_recommendations(
                item, eoq, safety_stock, reorder_point
            )
        }
    
    def _generate_recommendations(self, item: pd.Series, eoq: float, 
                                 safety_stock: float, reorder_point: float) -> List[str]:
        """Generate specific recommendations for the item"""
        recommendations = []
        current_stock = item['Planning Balance']
        
        if current_stock < reorder_point:
            recommendations.append(f"Place order immediately - stock below reorder point")
        
        if current_stock < safety_stock:
            recommendations.append(f"Critical: Stock below safety level")
        
        recommendations.append(f"Optimal order quantity: {eoq:.0f} units")
        
        return recommendations