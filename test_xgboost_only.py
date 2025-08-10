#!/usr/bin/env python3
"""
Test XGBoost model only for faster results
"""

import pandas as pd
import numpy as np
from sklearn.metrics import mean_absolute_percentage_error, mean_squared_error

print("="*60)
print("XGBOOST MODEL TRAINING - BEVERLY KNITS")
print("="*60)

# Load data
sales = pd.read_excel('ERP Data/New folder/Sales Activity Report (4).xlsx')
sales['Invoice Date'] = pd.to_datetime(sales['Invoice Date'])

# Aggregate daily sales
daily_sales = sales.groupby('Invoice Date')['Qty Shipped'].sum().reset_index()
daily_sales.columns = ['date', 'quantity']
daily_sales = daily_sales.sort_values('date')

print(f"✅ Loaded {len(daily_sales)} days of sales data")
print(f"   Date range: {daily_sales['date'].min()} to {daily_sales['date'].max()}")
print(f"   Total quantity: {daily_sales['quantity'].sum():,.0f}")
print(f"   Daily average: {daily_sales['quantity'].mean():.0f}")

# Create features
print("\n📊 Creating features...")
X = pd.DataFrame()

# Lag features (previous days)
for i in range(1, 15):
    X[f'lag_{i}'] = daily_sales['quantity'].shift(i)

# Rolling statistics
for window in [7, 14, 30]:
    X[f'mean_{window}d'] = daily_sales['quantity'].rolling(window, min_periods=1).mean()
    X[f'std_{window}d'] = daily_sales['quantity'].rolling(window, min_periods=1).std()

# Date features
X['dayofweek'] = daily_sales['date'].dt.dayofweek
X['day'] = daily_sales['date'].dt.day
X['month'] = daily_sales['date'].dt.month
X['quarter'] = daily_sales['date'].dt.quarter

# Remove NaN rows
X = X.dropna()
y = daily_sales['quantity'].iloc[len(daily_sales) - len(X):]

print(f"✅ Created {X.shape[1]} features")
print(f"   Samples available: {len(X)}")

# Split data 80/20
split_point = int(len(X) * 0.8)
X_train, X_test = X.iloc[:split_point], X.iloc[split_point:]
y_train, y_test = y.iloc[:split_point], y.iloc[split_point:]

print(f"\n📊 Train/Test Split:")
print(f"   Training: {len(X_train)} samples")
print(f"   Testing: {len(X_test)} samples")

# Train XGBoost
print("\n🚀 Training XGBoost model...")

try:
    from xgboost import XGBRegressor
    
    # Create model with optimized parameters
    model = XGBRegressor(
        n_estimators=150,
        max_depth=7,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=3,
        random_state=42
    )
    
    # Train
    model.fit(X_train, y_train)
    
    # Predict
    train_pred = model.predict(X_train)
    test_pred = model.predict(X_test)
    
    # Calculate metrics
    train_mape = mean_absolute_percentage_error(y_train, train_pred) * 100
    test_mape = mean_absolute_percentage_error(y_test, test_pred) * 100
    
    train_rmse = np.sqrt(mean_squared_error(y_train, train_pred))
    test_rmse = np.sqrt(mean_squared_error(y_test, test_pred))
    
    train_accuracy = 100 - train_mape
    test_accuracy = 100 - test_mape
    
    print("\n" + "="*60)
    print("RESULTS")
    print("="*60)
    
    print(f"\n📈 Training Performance:")
    print(f"   Accuracy: {train_accuracy:.2f}%")
    print(f"   MAPE: {train_mape:.2f}%")
    print(f"   RMSE: {train_rmse:.2f}")
    
    print(f"\n📊 Test Performance:")
    print(f"   Accuracy: {test_accuracy:.2f}%")
    print(f"   MAPE: {test_mape:.2f}%")
    print(f"   RMSE: {test_rmse:.2f}")
    
    if test_accuracy > 85:
        print(f"\n🎯 SUCCESS! Achieved {test_accuracy:.2f}% accuracy (>85% target!)")
    else:
        print(f"\n⚠️ Current accuracy: {test_accuracy:.2f}% (Target: >85%)")
    
    # Feature importance
    importance = pd.DataFrame({
        'feature': X.columns,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False).head(10)
    
    print(f"\n🔍 Top 10 Important Features:")
    for _, row in importance.iterrows():
        print(f"   {row['feature']:15s}: {row['importance']:.4f}")
    
    # Sample predictions
    print(f"\n📝 Sample Predictions (last 5 test days):")
    for i in range(-5, 0):
        actual = y_test.iloc[i]
        predicted = test_pred[i]
        error = abs(actual - predicted) / actual * 100
        print(f"   Actual: {actual:8.0f} | Predicted: {predicted:8.0f} | Error: {error:5.1f}%")
    
except ImportError:
    print("❌ XGBoost not installed. Install with: pip install xgboost")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n✅ Complete!")