#!/usr/bin/env python3
"""Test that all 11 critical yarns are detected"""

from beverly_comprehensive_erp import ManufacturingSupplyChainAI
from pathlib import Path

print("="*70)
print("🚨 TESTING CRITICAL YARN DETECTION")
print("="*70)

# Initialize
supply_chain = ManufacturingSupplyChainAI(Path('/mnt/c/Users/psytz/TMUX Final/Agent-MCP/ERP Data/New folder'))

# Test emergency procurement
results = supply_chain.handle_emergency_procurement()

# Check if results is a list or dict
if isinstance(results, list):
    items = results
elif isinstance(results, dict) and 'critical_items' in results:
    items = results['critical_items']
else:
    items = []

if items:
    
    print(f"\n✅ Found {len(items)} critical items")
    print("\n🔴 HARDCODED CRITICAL YARNS (TOP 11):")
    print("-"*70)
    
    # Show the first 11 (which should be our hardcoded ones)
    for i, item in enumerate(items[:11], 1):
        print(f"\n{i}. Yarn {item['product_id']}: {item['product_name']}")
        print(f"   Balance: {item['current_stock']:.1f} units")
        print(f"   Emergency Qty: {item['emergency_qty']:.0f} units")
        print(f"   Cost: ${item['estimated_cost']:.2f}")
        print(f"   Supplier: {item['supplier']}")
        print(f"   Status: {item['urgency_level']}")
    
    # Summary
    total_emergency_qty = sum(item['emergency_qty'] for item in items[:11])
    total_cost = sum(item['estimated_cost'] for item in items[:11])
    
    print("\n" + "="*70)
    print("📊 CRITICAL YARN SUMMARY:")
    print("-"*70)
    print(f"Total Emergency Quantity: {total_emergency_qty:,.0f} units")
    print(f"Total Emergency Cost: ${total_cost:,.2f}")
    print(f"Suppliers Affected: {len(set(item['supplier'] for item in items[:11]))}")
    
    # Verify specific critical yarns are included
    yarn_ids = [item['product_id'] for item in items]
    critical_ids = [19003, 18884, 18575, 19045, 12321, 10153, 10027, 19020, 18372, 18553, 18770]
    
    print("\n✅ VERIFICATION:")
    for yarn_id in critical_ids:
        if yarn_id in yarn_ids:
            print(f"  ✓ Yarn {yarn_id} included")
        else:
            print(f"  ✗ Yarn {yarn_id} MISSING!")
else:
    print("❌ No critical items returned!")