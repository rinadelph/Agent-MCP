#!/usr/bin/env python3
"""Test emergency procurement with live data"""

from beverly_comprehensive_erp import ManufacturingSupplyChainAI
from pathlib import Path

# Initialize with live data
supply_chain = ManufacturingSupplyChainAI(Path('/mnt/c/Users/psytz/TMUX Final/Agent-MCP/ERP Data/New folder'))

# Load live data
print("Loading live ERP data...")
supply_chain.load_live_erp_data()

# Run emergency procurement detection
print('\n' + '='*70)
print('🚨 EMERGENCY PROCUREMENT ANALYSIS')
print('='*70)

results = supply_chain.handle_emergency_procurement()

if results and 'summary' in results:
    summary = results['summary']
    print(f"\n📊 SUMMARY:")
    print(f"  Total emergency items: {summary.get('total_emergency_items', 0)}")
    print(f"  Items with NEGATIVE balance: {summary.get('negative_balance_count', 0)}")
    print(f"  Items with <7 days supply: {summary.get('critical_shortage_count', 0)}")
    print(f"  Total emergency quantity needed: {summary.get('total_emergency_qty', 0):,.0f} units")
    print(f"  Total emergency cost: ${summary.get('total_emergency_cost', 0):,.2f}")
    print(f"  Suppliers affected: {summary.get('suppliers_affected', 0)}")
    
    if 'critical_items' in results and results['critical_items']:
        print(f"\n🔴 TOP CRITICAL ITEMS:")
        for i, item in enumerate(results['critical_items'][:15], 1):  # Show top 15
            if item['negative_balance']:
                print(f"\n{i}. [NEGATIVE BALANCE] {item['product_name']}")
            else:
                print(f"\n{i}. {item['product_name']}")
            print(f"   Stock: {item['current_stock']:.0f} | Days supply: {item['days_of_supply']}")
            print(f"   Emergency order: {item['emergency_qty']:.0f} units | Cost: ${item['estimated_cost']:.2f}")
            print(f"   Supplier: {item['supplier']}")

print("\n" + "="*70)
print("✅ Analysis complete!")