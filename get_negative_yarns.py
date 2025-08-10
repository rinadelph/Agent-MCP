#!/usr/bin/env python3
"""Get exact negative balance yarns for emergency procurement"""

import pandas as pd

# Load yarn inventory
df = pd.read_excel('ERP Data/New folder/yarn_inventory (1).xlsx')

# Find items with negative Planning Balance
negative_items = df[df['Planning Balance'] < 0].copy()
negative_items = negative_items.sort_values('Planning Balance')

print("ALL NEGATIVE BALANCE YARNS FOR handle_emergency_procurement():")
print("="*70)

# Generate the exact code to add
print("\n# CRITICAL: 11 negative balance yarns (ALREADY OVERSOLD!)")
print("CRITICAL_NEGATIVE_YARNS = [")

for idx, row in negative_items.head(11).iterrows():
    yarn_id = int(row['Desc#'])
    balance = float(row['Planning Balance'])
    desc = str(row['Description'])[:50].replace("'", "\\'")
    supplier = str(row['Supplier'])
    
    # Check for specific yarns mentioned
    if yarn_id == 19004:
        print(f"    # PRIORITY: Yarn 19004 specifically requested")
    elif yarn_id == 18868:
        print(f"    # PRIORITY: Yarn 18868 specifically requested")
    elif yarn_id == 18851:
        print(f"    # PRIORITY: Yarn 18851 specifically requested")
    
    print(f"    {{'yarn_id': {yarn_id}, 'balance': {balance:.1f}, 'description': '{desc}', 'supplier': '{supplier}'}},")

print("]")

# Check if specific yarns are in the data
print("\n\nVERIFICATION OF REQUESTED YARNS:")
print("-"*40)
# Check for yarns 19004, 18868, 18851
for check_id in [19004, 18868, 18851, 18892, 14270]:
    check_yarn = df[df['Desc#'] == check_id]
    if not check_yarn.empty:
        row = check_yarn.iloc[0]
        balance = row['Planning Balance']
        if balance < 0:
            print(f"✓ Yarn {check_id}: {balance:.1f} units - FOUND IN NEGATIVE")
        else:
            print(f"  Yarn {check_id}: {balance:.1f} units - POSITIVE balance")
    else:
        print(f"✗ Yarn {check_id}: NOT FOUND in data")