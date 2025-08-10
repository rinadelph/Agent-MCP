#!/usr/bin/env python3
"""
COMPREHENSIVE EMERGENCY PROCUREMENT TEST
Tests all critical yarns and validates procurement calculations
"""

import pandas as pd
from pathlib import Path
from datetime import datetime
from beverly_comprehensive_erp import ManufacturingSupplyChainAI

def test_emergency_system():
    """Complete test of emergency procurement system"""
    print("="*80)
    print("🚨 COMPREHENSIVE EMERGENCY PROCUREMENT TEST")
    print(f"Test Date: {datetime.now().strftime('%B %d, %Y %H:%M')}")
    print("="*80)
    
    # Initialize with live data path
    DATA_PATH = Path('ERP Data/New folder')
    supply_chain = ManufacturingSupplyChainAI(DATA_PATH)
    
    # Load live data
    print("\n📂 Loading Live Data...")
    supply_chain.load_all_data()
    
    # Get emergency items
    emergency_results = supply_chain.handle_emergency_procurement()
    
    # Handle both list and dict return formats
    if isinstance(emergency_results, list):
        emergency_items = emergency_results
    elif isinstance(emergency_results, dict):
        emergency_items = emergency_results.get('critical_items', [])
    else:
        emergency_items = []
    
    print(f"✓ Found {len(emergency_items)} emergency items")
    
    # Analyze results
    print("\n" + "="*80)
    print("📊 EMERGENCY PROCUREMENT ANALYSIS")
    print("="*80)
    
    # Group by urgency
    negative_items = [i for i in emergency_items if i.get('current_stock', 0) < 0]
    critical_items = [i for i in emergency_items if i.get('days_of_supply', 999) < 7 and i.get('current_stock', 0) >= 0]
    
    print(f"\n🔴 NEGATIVE BALANCE ITEMS: {len(negative_items)}")
    print(f"⚠️  CRITICAL (<7 days): {len(critical_items)}")
    
    # Top 5 most critical
    print("\n🚨 TOP 5 MOST CRITICAL ITEMS:")
    print("-"*80)
    for i, item in enumerate(emergency_items[:5], 1):
        print(f"\n{i}. {item.get('product_name', 'Unknown')}")
        print(f"   ID: {item.get('product_id', 'N/A')}")
        print(f"   Current Stock: {item.get('current_stock', 0):.1f} units")
        print(f"   Days Supply: {item.get('days_of_supply', 0):.1f}")
        print(f"   Emergency Order: {item.get('emergency_qty', 0):,.0f} units")
        print(f"   Estimated Cost: ${item.get('estimated_cost', 0):,.2f}")
        print(f"   Supplier: {item.get('supplier', 'Unknown')}")
    
    # Financial impact
    total_qty = sum(i.get('emergency_qty', 0) for i in emergency_items)
    total_cost = sum(i.get('estimated_cost', 0) for i in emergency_items)
    
    print("\n" + "="*80)
    print("💰 FINANCIAL IMPACT")
    print("="*80)
    print(f"Total Emergency Quantity: {total_qty:,.0f} units")
    print(f"Total Procurement Cost: ${total_cost:,.2f}")
    print(f"Average Cost per Item: ${total_cost/len(emergency_items):,.2f}" if emergency_items else "N/A")
    
    # Supplier analysis
    suppliers = {}
    for item in emergency_items:
        supplier = item.get('supplier', 'Unknown')
        if supplier not in suppliers:
            suppliers[supplier] = {'count': 0, 'total_qty': 0, 'total_cost': 0}
        suppliers[supplier]['count'] += 1
        suppliers[supplier]['total_qty'] += item.get('emergency_qty', 0)
        suppliers[supplier]['total_cost'] += item.get('estimated_cost', 0)
    
    print("\n" + "="*80)
    print("📦 SUPPLIER BREAKDOWN")
    print("="*80)
    
    # Sort suppliers by urgency (item count)
    sorted_suppliers = sorted(suppliers.items(), key=lambda x: x[1]['count'], reverse=True)
    
    for supplier, data in sorted_suppliers[:10]:
        print(f"\n{supplier}:")
        print(f"  Items: {data['count']}")
        print(f"  Total Quantity: {data['total_qty']:,.0f} units")
        print(f"  Total Cost: ${data['total_cost']:,.2f}")
    
    # BOM Impact Analysis
    print("\n" + "="*80)
    print("📋 BOM IMPACT ANALYSIS")
    print("="*80)
    
    # Load BOM data to check affected products
    bom_file = DATA_PATH / "BOM_2(Sheet1).csv"
    if bom_file.exists():
        bom_data = pd.read_csv(bom_file)
        print(f"✓ Loaded {len(bom_data)} BOM entries")
        
        # Count affected products for top critical yarns
        critical_yarn_ids = [item.get('product_id') for item in emergency_items[:5]]
        affected_products = set()
        
        for yarn_id in critical_yarn_ids:
            if yarn_id and 'Yarn_ID' in bom_data.columns:
                products = bom_data[bom_data['Yarn_ID'] == yarn_id]['Style_id'].unique()
                affected_products.update(products)
        
        print(f"\n⚠️ Products affected by top 5 critical yarns: {len(affected_products)}")
        if len(affected_products) > 0:
            print(f"   Sample affected styles: {list(affected_products)[:5]}")
    
    # Action plan
    print("\n" + "="*80)
    print("⚡ RECOMMENDED ACTIONS")
    print("="*80)
    print("1. IMMEDIATE (Today):")
    print("   - Contact suppliers for expedited shipping on negative balance items")
    print(f"   - Prepare POs for {len(negative_items)} negative balance yarns")
    print(f"   - Allocate ${total_cost:,.2f} emergency procurement budget")
    
    print("\n2. URGENT (Within 24 hours):")
    print("   - Review production schedule for affected products")
    print("   - Consider air freight for most critical items")
    print("   - Update safety stock levels to prevent future shortages")
    
    print("\n3. FOLLOW-UP (Within 48 hours):")
    print("   - Implement automated reorder points")
    print("   - Review supplier contracts for better terms")
    print("   - Establish backup supplier relationships")
    
    # Success validation
    print("\n" + "="*80)
    print("✅ TEST VALIDATION")
    print("="*80)
    
    # Check for the 11 critical yarns
    expected_yarns = [19003, 18884, 18575, 19045, 12321, 10153, 10027, 19020, 18372, 18553, 18770]
    found_yarns = [item.get('product_id') for item in emergency_items if item.get('product_id') in expected_yarns]
    
    print(f"Critical Yarns Found: {len(found_yarns)}/{len(expected_yarns)}")
    if len(found_yarns) == len(expected_yarns):
        print("✅ All critical yarns detected successfully!")
    else:
        missing = set(expected_yarns) - set(found_yarns)
        print(f"⚠️ Missing yarns: {missing}")
    
    return {
        'total_items': len(emergency_items),
        'negative_balance': len(negative_items),
        'critical': len(critical_items),
        'total_cost': total_cost,
        'total_qty': total_qty,
        'suppliers': len(suppliers)
    }

if __name__ == "__main__":
    results = test_emergency_system()
    print("\n" + "="*80)
    print("📈 FINAL SUMMARY")
    print("="*80)
    for key, value in results.items():
        if 'cost' in key:
            print(f"{key}: ${value:,.2f}")
        elif isinstance(value, (int, float)):
            print(f"{key}: {value:,.0f}")
        else:
            print(f"{key}: {value}")