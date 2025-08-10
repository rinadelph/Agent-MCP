#!/usr/bin/env python3
"""
Simple test of ML forecasting with real data
"""

import pandas as pd
import numpy as np
from datetime import datetime

# Check if we can load the real data
data_path = 'ERP Data/New folder/Sales Activity Report (4).xlsx'
print(f"Loading data from: {data_path}")

# Load the Excel file
sales_data = pd.read_excel(data_path)
print(f"✅ Loaded {len(sales_data)} sales records")

# Check date range
if 'Date' in sales_data.columns:
    sales_data['Date'] = pd.to_datetime(sales_data['Date'], errors='coerce')
    date_range = sales_data['Date'].max() - sales_data['Date'].min()
    print(f"✅ Date range: {sales_data['Date'].min().strftime('%Y-%m-%d')} to {sales_data['Date'].max().strftime('%Y-%m-%d')}")
    print(f"✅ Total period: {date_range.days} days ({date_range.days/30:.1f} months)")

# Check unique products
if 'Item' in sales_data.columns:
    unique_products = sales_data['Item'].nunique()
    print(f"✅ Unique products: {unique_products}")

# Check quantity shipped
if 'Qty Shipped' in sales_data.columns:
    total_qty = sales_data['Qty Shipped'].sum()
    avg_daily = sales_data.groupby('Date')['Qty Shipped'].sum().mean()
    print(f"✅ Total quantity shipped: {total_qty:,.0f}")
    print(f"✅ Average daily quantity: {avg_daily:,.0f}")

# Now test with SalesForecastingEngine
print("\n" + "="*60)
print("Testing SalesForecastingEngine with Real Data")
print("="*60)

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from beverly_comprehensive_erp import SalesForecastingEngine

# Initialize the engine
engine = SalesForecastingEngine()
print("✅ SalesForecastingEngine initialized")

# Generate forecast
try:
    forecast_output = engine.generate_forecast_output(sales_data)
    
    if 'model_performance' in forecast_output:
        print("\n📊 Model Performance Results:")
        print("-"*40)
        for model_name, perf in forecast_output['model_performance'].items():
            accuracy = perf.get('accuracy', 0)
            mape = perf.get('mape', 100)
            print(f"{model_name:12s} | Accuracy: {accuracy:6.2f}% | MAPE: {mape:6.2f}%")
            
            # Check if we achieved >85% accuracy
            if model_name == 'ensemble' and accuracy > 85:
                print(f"\n🎯 SUCCESS: Ensemble model achieved {accuracy:.1f}% accuracy (>85% target!)")
    
    if 'forecast_90_days' in forecast_output:
        forecast_data = forecast_output['forecast_90_days']
        if isinstance(forecast_data, pd.DataFrame) and not forecast_data.empty:
            print(f"\n📅 90-Day Forecast Generated:")
            print(f"  - Start date: {forecast_data.iloc[0]['date']}")
            print(f"  - End date: {forecast_data.iloc[-1]['date']}")
            print(f"  - Average daily forecast: {forecast_data['forecast'].mean():,.0f} units")
            print(f"  - Total 90-day forecast: {forecast_data['forecast'].sum():,.0f} units")
            
except Exception as e:
    print(f"Error during forecasting: {e}")
    import traceback
    traceback.print_exc()

print("\n✅ Test completed!")