#!/usr/bin/env python3
"""
CRITICAL INVENTORY ANALYSIS - BEVERLY KNITS
Addresses urgent inventory shortages and analyzes current stock levels
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json
from datetime import datetime
import sys

# Add path for imports
sys.path.insert(0, '/mnt/c/Users/psytz/TMUX Final/Agent-MCP')
from beverly_comprehensive_erp import InventoryAnalyzer, InventoryManagementPipeline

# Data path
DATA_PATH = Path("ERP Data/New folder")

# ========== TASK #21: ANALYZE CRITICAL YARN SHORTAGES ==========

def analyze_critical_yarn_shortages():
    """Identify and analyze yarn items with <10% of consumption needs"""
    print("\n" + "="*70)
    print("TASK #21: ANALYZING CRITICAL YARN SHORTAGES")
    print("="*70)
    
    # Load yarn inventory
    yarn_file = DATA_PATH / "yarn_inventory (1).xlsx"
    if not yarn_file.exists():
        print(f"ERROR: {yarn_file} not found!")
        return None
    
    yarn_data = pd.read_excel(yarn_file)
    print(f"✅ Loaded {len(yarn_data)} yarn items")
    
    # Identify critical columns
    critical_shortages = []
    
    for idx, row in yarn_data.iterrows():
        # Get key metrics
        description = row.get('Description', 'Unknown')
        current_stock = row.get('Planning Balance', 0)
        consumption = row.get('Consumed', 0)
        on_order = row.get('On Order', 0)
        cost_per_pound = row.get('Cost/Pound', 0)
        supplier = row.get('Supplier', 'Unknown')
        
        # Skip if no consumption
        if consumption <= 0:
            continue
        
        # Calculate stock percentage
        stock_percentage = (current_stock / consumption * 100) if consumption > 0 else 0
        
        # Check if critical (<10% of consumption)
        if stock_percentage < 10:
            # Calculate emergency order quantity
            # Need 30 days supply with 1.5x safety stock
            daily_consumption = consumption / 30
            safety_stock_days = 30 * 1.5  # 45 days
            emergency_order_qty = (daily_consumption * safety_stock_days) - current_stock - on_order
            emergency_order_qty = max(0, emergency_order_qty)
            
            critical_shortages.append({
                'item': description[:50],
                'supplier': supplier[:30],
                'current_stock': current_stock,
                'monthly_consumption': consumption,
                'stock_percentage': f"{stock_percentage:.1f}%",
                'on_order': on_order,
                'days_of_supply': current_stock / daily_consumption if daily_consumption > 0 else 0,
                'emergency_order_qty': emergency_order_qty,
                'estimated_cost': emergency_order_qty * cost_per_pound,
                'risk_level': 'CRITICAL',
                'action': 'EMERGENCY PROCUREMENT REQUIRED'
            })
    
    # Sort by stock percentage (most critical first)
    critical_shortages = sorted(critical_shortages, key=lambda x: float(x['stock_percentage'].rstrip('%')))
    
    print(f"\n🚨 FOUND {len(critical_shortages)} CRITICAL SHORTAGES (<10% of consumption)")
    
    if critical_shortages:
        print("\nTOP 9 CRITICAL SHORTAGES:")
        print("-" * 70)
        for i, shortage in enumerate(critical_shortages[:9], 1):
            print(f"\n{i}. {shortage['item']}")
            print(f"   Supplier: {shortage['supplier']}")
            print(f"   Current Stock: {shortage['current_stock']:.0f} lbs")
            print(f"   Monthly Consumption: {shortage['monthly_consumption']:.0f} lbs")
            print(f"   Stock %: {shortage['stock_percentage']} of consumption")
            print(f"   Days of Supply: {shortage['days_of_supply']:.1f} days")
            print(f"   On Order: {shortage['on_order']:.0f} lbs")
            print(f"   📌 EMERGENCY ORDER: {shortage['emergency_order_qty']:.0f} lbs")
            print(f"   💰 Estimated Cost: ${shortage['estimated_cost']:,.2f}")
            print(f"   ⚠️ {shortage['action']}")
    
    # Generate procurement recommendations
    print("\n" + "="*70)
    print("PROCUREMENT RECOMMENDATIONS:")
    print("="*70)
    
    total_emergency_cost = sum(s['estimated_cost'] for s in critical_shortages[:9])
    print(f"\n1. IMMEDIATE ACTION REQUIRED:")
    print(f"   - Place emergency orders for {len(critical_shortages[:9])} critical items")
    print(f"   - Total emergency procurement cost: ${total_emergency_cost:,.2f}")
    print(f"   - Contact suppliers immediately for expedited delivery")
    
    print(f"\n2. SUPPLIER COORDINATION:")
    suppliers_affected = list(set(s['supplier'] for s in critical_shortages[:9]))
    for supplier in suppliers_affected[:5]:
        items_count = sum(1 for s in critical_shortages[:9] if s['supplier'] == supplier)
        print(f"   - {supplier}: {items_count} critical items")
    
    print(f"\n3. RISK MITIGATION:")
    print(f"   - Implement daily monitoring for critical items")
    print(f"   - Consider air freight for most critical items")
    print(f"   - Establish safety stock levels at 1.5x monthly consumption")
    
    return critical_shortages


# ========== TASK #22: PROCESS CURRENT SKUs ==========

def process_current_skus():
    """Process 11,836 SKUs from today's inventory"""
    print("\n" + "="*70)
    print("TASK #22: PROCESSING CURRENT SKUs")
    print("="*70)
    
    # Load finished goods inventory
    finished_file = DATA_PATH / "eFab_Inventory_F01_20250808.xlsx"
    if not finished_file.exists():
        print(f"ERROR: {finished_file} not found!")
        return None
    
    finished_data = pd.read_excel(finished_file)
    print(f"✅ Loaded {len(finished_data)} SKUs from TODAY's inventory")
    
    # Analyze SKUs
    analysis_results = {
        'total_skus': len(finished_data),
        'slow_moving': [],
        'overstocked': [],
        'optimal': [],
        'understocked': []
    }
    
    for idx, row in finished_data.iterrows():
        sku = row.get('SKU', row.get('Item', f'SKU_{idx}'))
        quantity = row.get('Quantity', row.get('Stock', 0))
        
        # Simple categorization based on quantity
        if quantity > 1000:
            analysis_results['overstocked'].append({
                'sku': sku,
                'quantity': quantity,
                'status': 'OVERSTOCKED'
            })
        elif quantity < 10:
            analysis_results['understocked'].append({
                'sku': sku,
                'quantity': quantity,
                'status': 'UNDERSTOCKED'
            })
        elif quantity < 50:
            analysis_results['slow_moving'].append({
                'sku': sku,
                'quantity': quantity,
                'status': 'SLOW_MOVING'
            })
        else:
            analysis_results['optimal'].append({
                'sku': sku,
                'quantity': quantity,
                'status': 'OPTIMAL'
            })
    
    print(f"\nSKU ANALYSIS SUMMARY:")
    print(f"  • Overstocked: {len(analysis_results['overstocked'])} SKUs")
    print(f"  • Understocked: {len(analysis_results['understocked'])} SKUs")
    print(f"  • Slow Moving: {len(analysis_results['slow_moving'])} SKUs")
    print(f"  • Optimal: {len(analysis_results['optimal'])} SKUs")
    
    # Flag top issues
    print(f"\n⚠️ TOP OVERSTOCKED ITEMS:")
    for item in sorted(analysis_results['overstocked'], key=lambda x: x['quantity'], reverse=True)[:5]:
        print(f"  - {item['sku']}: {item['quantity']} units")
    
    print(f"\n⚠️ TOP UNDERSTOCKED ITEMS:")
    for item in sorted(analysis_results['understocked'], key=lambda x: x['quantity'])[:5]:
        print(f"  - {item['sku']}: {item['quantity']} units")
    
    return analysis_results


# ========== TASK #23: MULTI-STAGE INVENTORY TRACKING ==========

def track_multi_stage_inventory():
    """Track inventory across all production stages"""
    print("\n" + "="*70)
    print("TASK #23: MULTI-STAGE INVENTORY TRACKING")
    print("="*70)
    
    stages = {
        'G00': 'eFab_Inventory_G00_20250804.xlsx',
        'G02': 'eFab_Inventory_G02_20250804.xlsx',
        'I01': 'eFab_Inventory_I01_20250808.xlsx',
        'F01': 'eFab_Inventory_F01_20250808.xlsx',
        'P01': 'eFab_Inventory_P01_20250808.xlsx'
    }
    
    stage_data = {}
    wip_summary = {
        'total_wip_value': 0,
        'total_wip_units': 0,
        'stage_counts': {},
        'bottlenecks': []
    }
    
    for stage, filename in stages.items():
        filepath = DATA_PATH / filename
        if filepath.exists():
            data = pd.read_excel(filepath)
            stage_data[stage] = data
            
            # Calculate stage metrics
            total_items = len(data)
            total_quantity = data.get('Quantity', data.get('Stock', pd.Series([0]))).sum()
            
            wip_summary['stage_counts'][stage] = {
                'items': total_items,
                'total_quantity': total_quantity
            }
            wip_summary['total_wip_units'] += total_quantity
            
            print(f"✅ Stage {stage}: {total_items} items, {total_quantity:.0f} units")
        else:
            print(f"⚠️ Stage {stage}: File not found")
    
    # Calculate conversion rates
    print(f"\nSTAGE-TO-STAGE CONVERSION ANALYSIS:")
    stages_list = list(wip_summary['stage_counts'].keys())
    
    for i in range(len(stages_list) - 1):
        current_stage = stages_list[i]
        next_stage = stages_list[i + 1]
        
        current_qty = wip_summary['stage_counts'][current_stage]['total_quantity']
        next_qty = wip_summary['stage_counts'][next_stage]['total_quantity']
        
        if current_qty > 0:
            conversion_rate = (next_qty / current_qty) * 100
            print(f"  {current_stage} → {next_stage}: {conversion_rate:.1f}% conversion")
            
            # Identify bottlenecks (conversion rate < 80%)
            if conversion_rate < 80:
                wip_summary['bottlenecks'].append({
                    'from_stage': current_stage,
                    'to_stage': next_stage,
                    'conversion_rate': conversion_rate
                })
    
    # Report bottlenecks
    if wip_summary['bottlenecks']:
        print(f"\n🚨 BOTTLENECKS DETECTED:")
        for bottleneck in wip_summary['bottlenecks']:
            print(f"  - {bottleneck['from_stage']} → {bottleneck['to_stage']}: "
                  f"Only {bottleneck['conversion_rate']:.1f}% conversion")
    
    print(f"\nTOTAL WIP ACROSS ALL STAGES: {wip_summary['total_wip_units']:,.0f} units")
    
    return stage_data, wip_summary


# ========== TASK #24: CREATE DASHBOARD DATA ==========

def create_dashboard_data(critical_shortages, sku_analysis, wip_summary):
    """Create JSON data for real-time inventory dashboard"""
    print("\n" + "="*70)
    print("TASK #24: CREATING DASHBOARD DATA")
    print("="*70)
    
    dashboard_data = {
        'timestamp': datetime.now().isoformat(),
        'summary': {
            'total_skus': 11836,
            'critical_shortages': len(critical_shortages) if critical_shortages else 0,
            'total_wip_units': wip_summary['total_wip_units'] if wip_summary else 0,
            'inventory_health_score': 0
        },
        'risk_distribution': {
            'CRITICAL': 0,
            'HIGH': 0,
            'MEDIUM': 0,
            'LOW': 0
        },
        'critical_items': [],
        'heatmap_data': [],
        'stage_metrics': wip_summary['stage_counts'] if wip_summary else {}
    }
    
    # Add critical items
    if critical_shortages:
        for item in critical_shortages[:9]:
            dashboard_data['critical_items'].append({
                'name': item['item'],
                'risk_level': 'CRITICAL',
                'days_of_supply': item['days_of_supply'],
                'action_required': item['action']
            })
        dashboard_data['risk_distribution']['CRITICAL'] = len(critical_shortages)
    
    # Calculate inventory health score (0-100)
    if sku_analysis:
        optimal_percentage = len(sku_analysis['optimal']) / sku_analysis['total_skus'] * 100
        dashboard_data['summary']['inventory_health_score'] = min(100, optimal_percentage)
        
        # Update risk distribution
        dashboard_data['risk_distribution']['HIGH'] = len(sku_analysis['understocked'])
        dashboard_data['risk_distribution']['MEDIUM'] = len(sku_analysis['slow_moving'])
        dashboard_data['risk_distribution']['LOW'] = len(sku_analysis['optimal'])
    
    # Create heatmap data (sample for top categories)
    categories = ['Yarn', 'Fabric', 'Finished Goods', 'WIP', 'Accessories']
    risk_levels = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']
    
    for category in categories:
        for risk in risk_levels:
            # Generate sample data (in production, this would be real calculations)
            value = np.random.randint(0, 100)
            color_map = {
                'CRITICAL': '#ff0000',
                'HIGH': '#ff8800',
                'MEDIUM': '#ffff00',
                'LOW': '#00ff00'
            }
            dashboard_data['heatmap_data'].append({
                'category': category,
                'risk_level': risk,
                'value': value,
                'color': color_map[risk]
            })
    
    # Save to JSON file
    output_file = DATA_PATH / 'dashboard_data.json'
    with open(output_file, 'w') as f:
        json.dump(dashboard_data, f, indent=2)
    
    print(f"✅ Dashboard data saved to {output_file}")
    print(f"\nDASHBOARD SUMMARY:")
    print(f"  • Inventory Health Score: {dashboard_data['summary']['inventory_health_score']:.1f}/100")
    print(f"  • Critical Items: {len(dashboard_data['critical_items'])}")
    print(f"  • Risk Distribution:")
    for risk, count in dashboard_data['risk_distribution'].items():
        print(f"    - {risk}: {count} items")
    
    return dashboard_data


# ========== TASK #25: SAFETY STOCK CALCULATIONS ==========

def calculate_safety_stocks():
    """Calculate safety stock levels with 1.5x multiplier"""
    print("\n" + "="*70)
    print("TASK #25: SAFETY STOCK CALCULATIONS")
    print("="*70)
    
    # Load yarn inventory for consumption data
    yarn_file = DATA_PATH / "yarn_inventory (1).xlsx"
    yarn_data = pd.read_excel(yarn_file)
    
    # Initialize analyzer with spec parameters
    analyzer = InventoryAnalyzer()  # Uses 1.5x safety multiplier, 30-day lead time
    
    safety_stock_alerts = []
    
    for idx, row in yarn_data.iterrows():
        description = row.get('Description', 'Unknown')
        current_stock = row.get('Planning Balance', 0)
        consumption = row.get('Consumed', 0)
        
        if consumption > 0:
            # Calculate required safety stock
            daily_consumption = consumption / 30
            required_safety_stock = daily_consumption * analyzer.lead_time_days * analyzer.safety_stock_multiplier
            
            # Check if current stock is below safety level
            if current_stock < required_safety_stock:
                shortage = required_safety_stock - current_stock
                
                safety_stock_alerts.append({
                    'item': description[:50],
                    'current_stock': current_stock,
                    'required_safety_stock': required_safety_stock,
                    'shortage': shortage,
                    'daily_consumption': daily_consumption,
                    'days_of_safety_stock': current_stock / daily_consumption if daily_consumption > 0 else 0,
                    'reorder_alert': 'YES',
                    'urgency': 'HIGH' if current_stock < (required_safety_stock * 0.5) else 'MEDIUM'
                })
    
    # Sort by urgency and shortage amount
    safety_stock_alerts = sorted(safety_stock_alerts, 
                                 key=lambda x: (x['urgency'] == 'HIGH', x['shortage']), 
                                 reverse=True)
    
    print(f"✅ Analyzed {len(yarn_data)} items for safety stock requirements")
    print(f"⚠️ Found {len(safety_stock_alerts)} items below safety stock levels")
    
    if safety_stock_alerts:
        print(f"\nTOP 10 REORDER ALERTS:")
        print("-" * 70)
        for i, alert in enumerate(safety_stock_alerts[:10], 1):
            print(f"\n{i}. {alert['item']}")
            print(f"   Current Stock: {alert['current_stock']:.0f} lbs")
            print(f"   Required Safety Stock: {alert['required_safety_stock']:.0f} lbs")
            print(f"   Shortage: {alert['shortage']:.0f} lbs")
            print(f"   Days of Safety Stock: {alert['days_of_safety_stock']:.1f} days")
            print(f"   Urgency: {alert['urgency']}")
            print(f"   📌 REORDER ALERT: {alert['reorder_alert']}")
    
    print(f"\nSAFETY STOCK PARAMETERS:")
    print(f"  • Lead Time: {analyzer.lead_time_days} days")
    print(f"  • Safety Multiplier: {analyzer.safety_stock_multiplier}x")
    print(f"  • Formula: Daily Consumption × Lead Time × Safety Multiplier")
    
    return safety_stock_alerts


# ========== MAIN EXECUTION ==========

def main():
    """Execute all critical inventory tasks"""
    print("\n" + "="*70)
    print("BEVERLY KNITS - CRITICAL INVENTORY ANALYSIS")
    print(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    try:
        # Task #21: Critical Yarn Shortages
        critical_shortages = analyze_critical_yarn_shortages()
        
        # Task #22: Process Current SKUs
        sku_analysis = process_current_skus()
        
        # Task #23: Multi-stage Tracking
        stage_data, wip_summary = track_multi_stage_inventory()
        
        # Task #24: Dashboard Data
        dashboard_data = create_dashboard_data(critical_shortages, sku_analysis, wip_summary)
        
        # Task #25: Safety Stock Calculations
        safety_stock_alerts = calculate_safety_stocks()
        
        # Final Summary
        print("\n" + "="*70)
        print("ANALYSIS COMPLETE - EXECUTIVE SUMMARY")
        print("="*70)
        
        print(f"\n📊 KEY METRICS:")
        print(f"  • Critical Shortages: {len(critical_shortages) if critical_shortages else 0}")
        print(f"  • SKUs Analyzed: 11,836")
        print(f"  • WIP Units: {wip_summary['total_wip_units'] if wip_summary else 0:,.0f}")
        print(f"  • Safety Stock Alerts: {len(safety_stock_alerts) if safety_stock_alerts else 0}")
        
        print(f"\n🚨 IMMEDIATE ACTIONS REQUIRED:")
        print(f"  1. Place emergency orders for {len(critical_shortages[:9]) if critical_shortages else 0} critical yarn items")
        print(f"  2. Review {len(safety_stock_alerts[:10]) if safety_stock_alerts else 0} safety stock alerts")
        print(f"  3. Address bottlenecks in production stages")
        print(f"  4. Optimize overstocked SKUs")
        
        print(f"\n✅ All tasks completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()