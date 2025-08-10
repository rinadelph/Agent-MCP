#\!/usr/bin/env python3
"""
CRITICAL YARN SHORTAGE ANALYSIS & EMERGENCY PROCUREMENT
Analyzes all 9 critical yarn shortages and generates emergency procurement plan
Date: August 8, 2025
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import json

# Live data path
DATA_PATH = Path("/mnt/c/Users/psytz/TMUX Final/Agent-MCP/ERP Data/New folder")

class CriticalYarnAnalyzer:
    """Analyze critical yarn shortages and generate emergency procurement plans"""
    
    def __init__(self):
        self.yarn_inventory = None
        self.bom_data = None
        self.sales_data = None
        self.finished_goods = None
        self.critical_items = []
        self.load_data()
    
    def load_data(self):
        """Load all necessary data files"""
        print("="*70)
        print("🔴 CRITICAL YARN SHORTAGE ANALYSIS")
        print(f"Analysis Date: {datetime.now().strftime('%B %d, %Y %H:%M')}")
        print("="*70)
        
        # Load yarn inventory
        yarn_file = DATA_PATH / "yarn_inventory (1).xlsx"
        if yarn_file.exists():
            self.yarn_inventory = pd.read_excel(yarn_file)
            print(f"✓ Loaded {len(self.yarn_inventory)} yarn items")
        
        # Load BOM data
        bom_file = DATA_PATH / "BOM_2(Sheet1).csv"
        if bom_file.exists():
            self.bom_data = pd.read_csv(bom_file)
            print(f"✓ Loaded {len(self.bom_data)} BOM entries for {self.bom_data['Style_id'].nunique()} products")
        
        # Load sales data
        sales_file = DATA_PATH / "Sales Activity Report (4).xlsx"
        if sales_file.exists():
            self.sales_data = pd.read_excel(sales_file)
            print(f"✓ Loaded {len(self.sales_data)} sales transactions")
        
        # Load finished goods
        fg_file = DATA_PATH / "eFab_Inventory_F01_20250808.xlsx"
        if fg_file.exists():
            self.finished_goods = pd.read_excel(fg_file)
            print(f"✓ Loaded {len(self.finished_goods)} current SKUs")
    
    def identify_critical_shortages(self):
        """Identify ALL yarns with <7 days supply"""
        if self.yarn_inventory is None:
            return []
        
        print("\n" + "="*70)
        print("🔍 IDENTIFYING CRITICAL SHORTAGES (<7 days supply)")
        print("="*70)
        
        critical_count = 0
        
        for idx, row in self.yarn_inventory.iterrows():
            # Get key metrics
            desc = row.get('Description', '')
            balance = row.get('Planning Balance', 0)
            consumed = row.get('Consumed', 0)
            beginning = row.get('Beginning Balance', 0)
            theoretical = row.get('Theoretical Balance', 0)
            on_order = row.get('On Order', 0)
            allocated = row.get('Allocated', 0)
            supplier = row.get('Supplier', 'Unknown')
            cost_per_pound = row.get('Cost/Pound', 0)
            
            # Calculate actual consumption
            if consumed == 0:
                # Use balance changes as proxy
                implied_consumption = abs(beginning - theoretical)
                if implied_consumption > 0.1:
                    consumed = implied_consumption
            
            # Skip if no consumption
            if consumed <= 0:
                continue
            
            # Calculate days of supply
            daily_consumption = consumed / 30  # Monthly to daily
            
            # Account for allocated quantities (reduce available balance)
            available_balance = balance - allocated if allocated > 0 else balance
            
            days_of_supply = available_balance / daily_consumption if daily_consumption > 0 else 999
            
            # Future supply including on-order
            future_balance = available_balance + on_order
            future_days_supply = future_balance / daily_consumption if daily_consumption > 0 else 999
            
            # Check if critical (<7 days)
            if days_of_supply < 7:
                critical_count += 1
                
                # Calculate emergency procurement needs
                # Target: 30 days supply + 20% safety buffer
                target_days = 30 * 1.2  # 36 days
                target_quantity = daily_consumption * target_days
                emergency_qty = max(0, target_quantity - future_balance)
                
                # Estimate lead time based on supplier
                if 'LOCAL' in supplier.upper() or 'DOMESTIC' in supplier.upper():
                    lead_time_days = 3
                elif 'CHINA' in supplier.upper() or 'ASIA' in supplier.upper():
                    lead_time_days = 14
                else:
                    lead_time_days = 7  # Default
                
                # Calculate urgency score (0-100)
                urgency_score = min(100, (7 - days_of_supply) * 20) if days_of_supply < 7 else 0
                
                self.critical_items.append({
                    'yarn_id': row.get('Desc#', ''),
                    'description': desc[:50],
                    'supplier': supplier,
                    'current_stock': available_balance,
                    'on_order': on_order,
                    'allocated': allocated,
                    'daily_consumption': round(daily_consumption, 2),
                    'monthly_consumption': round(consumed, 2),
                    'days_of_supply': round(days_of_supply, 1),
                    'future_days_supply': round(future_days_supply, 1),
                    'emergency_qty': round(emergency_qty, 0),
                    'target_qty': round(target_quantity, 0),
                    'cost_per_pound': cost_per_pound,
                    'estimated_cost': round(emergency_qty * cost_per_pound, 2),
                    'lead_time_days': lead_time_days,
                    'urgency_score': round(urgency_score, 1),
                    'order_by_date': (datetime.now() + timedelta(days=max(0, days_of_supply - lead_time_days))).strftime('%Y-%m-%d')
                })
        
        # Sort by urgency
        self.critical_items.sort(key=lambda x: x['urgency_score'], reverse=True)
        
        print(f"\n🔴 Found {len(self.critical_items)} CRITICAL yarn shortages!")
        return self.critical_items

def main():
    """Run critical yarn analysis"""
    analyzer = CriticalYarnAnalyzer()
    
    # Identify critical shortages
    critical_items = analyzer.identify_critical_shortages()
    
    if critical_items:
        # Show all critical items
        print("\n🔴 ALL CRITICAL YARNS (< 7 days supply):")
        print("-" * 70)
        for i, item in enumerate(critical_items, 1):
            print(f"\n{i}. {item['description']}")
            print(f"   Current supply: {item['days_of_supply']:.1f} days")
            print(f"   Daily consumption: {item['daily_consumption']:.1f} lbs/day")
            print(f"   Emergency order: {item['emergency_qty']:,.0f} lbs")
            print(f"   Cost: ${item['estimated_cost']:,.2f}")
            print(f"   ORDER BY: {item['order_by_date']}")
            print(f"   Supplier: {item['supplier']}")
    
    return analyzer

if __name__ == "__main__":
    analyzer = main()
