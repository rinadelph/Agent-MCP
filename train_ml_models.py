#!/usr/bin/env python3
"""
Train ML models on real Beverly Knits sales data
Goal: Achieve >85% forecast accuracy
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

print("="*60)
print("ML MODEL TRAINING - BEVERLY KNITS")
print("="*60)

# Load real sales data
data_path = Path('ERP Data/New folder')
sales_file = data_path / 'Sales Activity Report (4).xlsx'

print(f"Loading data from: {sales_file}")
sales = pd.read_excel(sales_file)
print(f"✅ Loaded {len(sales)} sales records")

# Explore data structure
print("\n📊 Data Structure:")
print("-"*40)
print(f"Columns: {list(sales.columns)}")
print(f"\nFirst few rows:")
print(sales.head())

print(f"\nData types:")
print(sales.dtypes)

print(f"\nBasic statistics:")
print(sales.describe())

# Check for date columns
date_columns = [col for col in sales.columns if 'date' in col.lower() or 'Date' in col]
print(f"\n📅 Date columns found: {date_columns}")

# Check for quantity columns
qty_columns = [col for col in sales.columns if 'qty' in col.lower() or 'quantity' in col.lower() or 'Qty' in col]
print(f"📦 Quantity columns found: {qty_columns}")

# Check for product/item columns
item_columns = [col for col in sales.columns if 'item' in col.lower() or 'product' in col.lower() or 'Item' in col]
print(f"🏷️ Item columns found: {item_columns}")

# Check for null values
print(f"\n🔍 Null values per column:")
null_counts = sales.isnull().sum()
for col, count in null_counts.items():
    if count > 0:
        print(f"  {col}: {count} nulls ({count/len(sales)*100:.1f}%)")

print("\n" + "="*60)
print("DATA PREPARATION")
print("="*60)

# Identify the main columns
if date_columns:
    date_col = date_columns[0]
    print(f"Using date column: {date_col}")
    
    # Convert to datetime
    sales[date_col] = pd.to_datetime(sales[date_col], errors='coerce')
    
    # Check date range
    date_min = sales[date_col].min()
    date_max = sales[date_col].max()
    print(f"Date range: {date_min.strftime('%Y-%m-%d')} to {date_max.strftime('%Y-%m-%d')}")
    print(f"Total days: {(date_max - date_min).days}")
    print(f"Total months: {(date_max - date_min).days / 30:.1f}")

if qty_columns:
    qty_col = qty_columns[0]
    print(f"\nUsing quantity column: {qty_col}")
    
    # Basic stats on quantity
    print(f"Total quantity: {sales[qty_col].sum():,.0f}")
    print(f"Average per record: {sales[qty_col].mean():.1f}")
    print(f"Median: {sales[qty_col].median():.1f}")
    print(f"Std dev: {sales[qty_col].std():.1f}")

if item_columns:
    item_col = item_columns[0]
    print(f"\nUsing item column: {item_col}")
    
    # Count unique items
    unique_items = sales[item_col].nunique()
    print(f"Unique items: {unique_items}")
    
    # Top 10 items by quantity
    if qty_columns:
        top_items = sales.groupby(item_col)[qty_col].sum().nlargest(10)
        print(f"\nTop 10 items by quantity:")
        for item, qty in top_items.items():
            print(f"  {item}: {qty:,.0f}")

print("\n✅ Data exploration complete!")
print("Ready to train ML models...")