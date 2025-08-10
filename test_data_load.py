#!/usr/bin/env python3
"""
Simple test to load Beverly Knits data
"""
import pandas as pd
from pathlib import Path

# Test data loading
data_path = Path("ERP Data/New folder")
print(f"Data path: {data_path}")
print(f"Exists: {data_path.exists()}")

if data_path.exists():
    files = list(data_path.glob("*.*"))
    print(f"Found {len(files)} files:")
    for f in files:
        print(f"  - {f.name}")
    
    # Test yarn inventory
    yarn_file = data_path / "yarn_inventory (1).xlsx"
    print(f"\nYarn file exists: {yarn_file.exists()}")
    if yarn_file.exists():
        try:
            df = pd.read_excel(yarn_file)
            print(f"Yarn data shape: {df.shape}")
            print("Columns:", list(df.columns))
            print("\nFirst 3 rows:")
            print(df.head(3))
        except Exception as e:
            print(f"Error loading yarn: {e}")
    
    # Test sales data
    sales_file = data_path / "Sales Activity Report (4).xlsx"
    print(f"\nSales file exists: {sales_file.exists()}")
    if sales_file.exists():
        try:
            df = pd.read_excel(sales_file)
            print(f"Sales data shape: {df.shape}")
            print("Columns:", list(df.columns))
            print("\nFirst 3 rows:")
            print(df.head(3))
        except Exception as e:
            print(f"Error loading sales: {e}")