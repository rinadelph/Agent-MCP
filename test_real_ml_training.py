#!/usr/bin/env python3
"""
Test ML forecasting with real Beverly Knits sales data
"""

import pandas as pd
import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from beverly_comprehensive_erp import ManufacturingSupplyChainAI

def test_ml_forecasting():
    """Test ML forecasting with real sales data"""
    
    # Initialize ERP system with data path
    data_path = 'ERP Data/New folder'
    erp = ManufacturingSupplyChainAI(data_path)
    
    # Load real sales data
    data_path = '/mnt/c/Users/psytz/TMUX Final/Agent-MCP/ERP Data/New folder/Sales Activity Report (4).xlsx'
    
    if os.path.exists(data_path):
        print(f"Loading real sales data from: {data_path}")
        try:
            # Load the Excel file
            sales_data = pd.read_excel(data_path)
            print(f"Loaded {len(sales_data)} sales records")
            
            # Set the data in ERP system
            erp.sales_data = sales_data
            
            # Run ML forecasting
            print("\n" + "="*60)
            print("Running ML Forecasting on Real Data")
            print("="*60)
            
            results = erp.get_ml_forecasting_insights()
            
            print("\nModel Performance Results:")
            print("-"*40)
            for model in results:
                print(f"{model['model']:12s} | Accuracy: {model['accuracy']:6s} | MAPE: {model['mape']:6s}")
                print(f"              | Status: {model['status']}")
                print(f"              | Insights: {model['insights'][:50]}...")
                print()
            
            # Check if we achieved >85% accuracy
            best_model = results[0] if results else None
            if best_model:
                accuracy = float(best_model['accuracy'].replace('%', ''))
                if accuracy > 85:
                    print(f"✅ SUCCESS: Achieved {accuracy:.1f}% accuracy (>85% target)")
                else:
                    print(f"⚠️ Need improvement: {accuracy:.1f}% accuracy (target: >85%)")
            
            # Test additional methods
            print("\n" + "="*60)
            print("Testing Additional ML Methods")
            print("="*60)
            
            # Auto-select best model
            best = erp.auto_select_best_model()
            print(f"\nBest Model Selected: {best['selected_model']}")
            print(f"Performance: {best['performance']}")
            
            # Detect anomalies
            anomalies = erp.detect_demand_anomalies()
            print(f"\nAnomaly Detection: {anomalies.get('summary', 'No summary')}")
            print(f"Total anomalies found: {anomalies.get('total_anomalies', 0)}")
            
            # Generate 90-day forecast
            forecast = erp.generate_90_day_forecast()
            print(f"\n90-Day Forecast Status: {forecast.get('status', 'Unknown')}")
            if 'forecasts' in forecast and forecast['forecasts']:
                print(f"Forecast generated for {len(forecast['forecasts'])} days")
                print(f"First day: {forecast['forecasts'][0].get('date', 'N/A')}")
                print(f"Last day: {forecast['forecasts'][-1].get('date', 'N/A')}")
            
        except Exception as e:
            print(f"Error loading or processing data: {e}")
            import traceback
            traceback.print_exc()
    else:
        print(f"Data file not found: {data_path}")

if __name__ == "__main__":
    test_ml_forecasting()