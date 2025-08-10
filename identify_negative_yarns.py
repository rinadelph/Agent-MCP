#!/usr/bin/env python3
"""Identify all negative balance yarns"""

import pandas as pd

# Load yarn inventory
df = pd.read_excel('/mnt/c/Users/psytz/TMUX Final/Agent-MCP/ERP Data/New folder/yarn_inventory (1).xlsx')

# Find ALL items with negative Planning Balance
negative_items = df[df['Planning Balance'] < 0].copy()

# Sort by balance (most negative first)
negative_items = negative_items.sort_values('Planning Balance')

print("🚨 ALL NEGATIVE BALANCE YARNS:")
print("="*70)

# Create a list for hardcoding into the method
critical_yarns = []

for idx, row in negative_items.iterrows():
    yarn_id = row['Desc#']
    desc = row['Description']
    balance = row['Planning Balance']
    supplier = row['Supplier']
    
    critical_yarns.append({
        'yarn_id': int(yarn_id),
        'description': str(desc),
        'balance': float(balance),
        'supplier': str(supplier)
    })
    
    print(f"\nYarn {yarn_id}: {desc[:40]}")
    print(f"  Balance: {balance:.1f} units")
    print(f"  Supplier: {supplier}")

print(f"\n\nTOTAL: {len(negative_items)} yarns with negative balance")

# Generate Python code to hardcode these
print("\n" + "="*70)
print("PYTHON CODE TO ADD TO handle_emergency_procurement():")
print("="*70)
print("\n# CRITICAL: Hardcoded negative balance yarns requiring IMMEDIATE procurement")
print("CRITICAL_NEGATIVE_YARNS = [")
for item in critical_yarns[:11]:  # First 11 most critical
    desc_escaped = item['description'].replace("'", "\\'")[:50]
    print(f"    {{'yarn_id': {item['yarn_id']}, 'description': '{desc_escaped}', 'critical_balance': {item['balance']:.1f}, 'supplier': '{item['supplier']}'}},")
print("]")