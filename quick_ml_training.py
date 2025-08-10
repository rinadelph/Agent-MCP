#!/usr/bin/env python3
"""
Quick ML training on Beverly Knits sales data
"""

import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.metrics import mean_absolute_percentage_error
import warnings
warnings.filterwarnings('ignore')

print("="*60)
print("QUICK ML TRAINING - BEVERLY KNITS")
print("="*60)

# Load and prepare data
sales = pd.read_excel('ERP Data/New folder/Sales Activity Report (4).xlsx')
sales['Invoice Date'] = pd.to_datetime(sales['Invoice Date'])
daily_sales = sales.groupby('Invoice Date')['Qty Shipped'].sum().reset_index()
daily_sales.columns = ['ds', 'y']

print(f"✅ Data loaded: {len(daily_sales)} days of sales data")
print(f"   Total quantity: {daily_sales['y'].sum():,.0f} units")

# Split data
train_size = int(len(daily_sales) * 0.8)
train_data = daily_sales.iloc[:train_size]
test_data = daily_sales.iloc[train_size:]

print(f"\n📊 Train/Test Split:")
print(f"   Training: {len(train_data)} days")
print(f"   Testing: {len(test_data)} days")

# Quick Prophet Model
print("\n" + "="*40)
print("PROPHET MODEL")
print("="*40)

try:
    from prophet import Prophet
    
    # Train with optimized parameters
    model = Prophet(
        changepoint_prior_scale=0.1,
        seasonality_mode='multiplicative',
        yearly_seasonality=False,  # Faster without yearly
        weekly_seasonality=True,
        interval_width=0.95
    )
    
    model.fit(train_data)
    
    # Predict
    future = model.make_future_dataframe(periods=len(test_data))
    forecast = model.predict(future)
    test_pred = forecast.iloc[-len(test_data):]
    
    # Calculate accuracy
    mape = mean_absolute_percentage_error(test_data['y'], test_pred['yhat']) * 100
    accuracy = 100 - mape
    
    print(f"✅ Prophet Results:")
    print(f"   Accuracy: {accuracy:.2f}%")
    print(f"   MAPE: {mape:.2f}%")
    
    if accuracy > 85:
        print(f"   🎯 TARGET ACHIEVED! >85% accuracy!")
    
    # Show sample predictions
    print(f"\n   Sample Predictions (last 5 days):")
    for i in range(-5, 0):
        actual = test_data.iloc[i]['y']
        predicted = test_pred.iloc[i]['yhat']
        error_pct = abs(actual - predicted) / actual * 100
        print(f"     {test_data.iloc[i]['ds'].strftime('%Y-%m-%d')}: Actual={actual:,.0f}, Predicted={predicted:,.0f}, Error={error_pct:.1f}%")
    
except Exception as e:
    print(f"❌ Prophet failed: {e}")

# Quick XGBoost Model
print("\n" + "="*40)
print("XGBOOST MODEL")
print("="*40)

try:
    from xgboost import XGBRegressor
    
    # Simple features
    X = pd.DataFrame()
    for i in range(1, 8):
        X[f'lag_{i}'] = daily_sales['y'].shift(i)
    
    X['rolling_mean_7'] = daily_sales['y'].rolling(7, min_periods=1).mean()
    X['dayofweek'] = pd.to_datetime(daily_sales['ds']).dt.dayofweek
    X['month'] = pd.to_datetime(daily_sales['ds']).dt.month
    
    X = X.dropna()
    y = daily_sales['y'].iloc[len(daily_sales) - len(X):]
    
    # Split
    X_train = X.iloc[:train_size]
    X_test = X.iloc[train_size:]
    y_train = y.iloc[:train_size]
    y_test = y.iloc[train_size:]
    
    # Train
    model = XGBRegressor(n_estimators=100, max_depth=5, learning_rate=0.1, random_state=42)
    model.fit(X_train, y_train)
    
    # Predict
    predictions = model.predict(X_test)
    
    # Calculate accuracy
    mape = mean_absolute_percentage_error(y_test, predictions) * 100
    accuracy = 100 - mape
    
    print(f"✅ XGBoost Results:")
    print(f"   Accuracy: {accuracy:.2f}%")
    print(f"   MAPE: {mape:.2f}%")
    
    if accuracy > 85:
        print(f"   🎯 TARGET ACHIEVED! >85% accuracy!")
    
except Exception as e:
    print(f"❌ XGBoost failed: {e}")

print("\n✅ Quick training complete!")