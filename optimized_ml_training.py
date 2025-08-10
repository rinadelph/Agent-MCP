#!/usr/bin/env python3
"""
Optimized ML training with weekly aggregation for better accuracy
"""

import pandas as pd
import numpy as np
from sklearn.metrics import mean_absolute_percentage_error, mean_squared_error
from sklearn.ensemble import RandomForestRegressor
import warnings
warnings.filterwarnings('ignore')

print("="*60)
print("OPTIMIZED ML TRAINING - BEVERLY KNITS")
print("="*60)

# Load data
sales = pd.read_excel('ERP Data/New folder/Sales Activity Report (4).xlsx')
sales['Invoice Date'] = pd.to_datetime(sales['Invoice Date'])

# Aggregate to WEEKLY sales for smoother predictions
sales['week'] = sales['Invoice Date'].dt.to_period('W')
weekly_sales = sales.groupby('week')['Qty Shipped'].sum().reset_index()
weekly_sales['week'] = weekly_sales['week'].dt.to_timestamp()
weekly_sales.columns = ['date', 'quantity']
weekly_sales = weekly_sales.sort_values('date')

print(f"✅ Aggregated to weekly sales: {len(weekly_sales)} weeks")
print(f"   Date range: {weekly_sales['date'].min()} to {weekly_sales['date'].max()}")
print(f"   Total quantity: {weekly_sales['quantity'].sum():,.0f}")
print(f"   Weekly average: {weekly_sales['quantity'].mean():.0f}")
print(f"   Standard deviation: {weekly_sales['quantity'].std():.0f}")

# Create comprehensive features
print("\n📊 Feature Engineering...")
X = pd.DataFrame()

# Lag features (previous weeks)
for i in range(1, 9):  # 8 weeks of lag
    X[f'lag_{i}w'] = weekly_sales['quantity'].shift(i)

# Rolling statistics
for window in [4, 8, 12]:  # 4, 8, 12 weeks
    X[f'mean_{window}w'] = weekly_sales['quantity'].rolling(window, min_periods=1).mean()
    X[f'std_{window}w'] = weekly_sales['quantity'].rolling(window, min_periods=1).std()
    X[f'min_{window}w'] = weekly_sales['quantity'].rolling(window, min_periods=1).min()
    X[f'max_{window}w'] = weekly_sales['quantity'].rolling(window, min_periods=1).max()

# Trend features
X['trend'] = np.arange(len(weekly_sales))
X['trend_squared'] = X['trend'] ** 2

# Date features
X['month'] = weekly_sales['date'].dt.month
X['quarter'] = weekly_sales['date'].dt.quarter
X['week_of_month'] = (weekly_sales['date'].dt.day - 1) // 7 + 1

# Remove NaN rows
X = X.dropna()
y = weekly_sales['quantity'].iloc[len(weekly_sales) - len(X):]
dates = weekly_sales['date'].iloc[len(weekly_sales) - len(X):]

print(f"✅ Created {X.shape[1]} features")
print(f"   Samples available: {len(X)}")

# Time series split (respecting temporal order)
split_point = int(len(X) * 0.8)
X_train, X_test = X.iloc[:split_point], X.iloc[split_point:]
y_train, y_test = y.iloc[:split_point], y.iloc[split_point:]
dates_test = dates.iloc[split_point:]

print(f"\n📊 Train/Test Split:")
print(f"   Training: {len(X_train)} weeks")
print(f"   Testing: {len(X_test)} weeks")

results = {}

# 1. RANDOM FOREST (often better than XGBoost for time series)
print("\n" + "="*60)
print("1. RANDOM FOREST MODEL")
print("="*60)

rf_model = RandomForestRegressor(
    n_estimators=200,
    max_depth=10,
    min_samples_split=5,
    min_samples_leaf=2,
    random_state=42
)

rf_model.fit(X_train, y_train)
rf_pred = rf_model.predict(X_test)

rf_mape = mean_absolute_percentage_error(y_test, rf_pred) * 100
rf_accuracy = 100 - rf_mape
rf_rmse = np.sqrt(mean_squared_error(y_test, rf_pred))

results['RandomForest'] = {'accuracy': rf_accuracy, 'mape': rf_mape, 'rmse': rf_rmse}

print(f"✅ Random Forest Results:")
print(f"   Accuracy: {rf_accuracy:.2f}%")
print(f"   MAPE: {rf_mape:.2f}%")
print(f"   RMSE: {rf_rmse:.2f}")

if rf_accuracy > 85:
    print(f"   🎯 TARGET ACHIEVED! >85% accuracy!")

# 2. XGBOOST with better parameters
print("\n" + "="*60)
print("2. XGBOOST MODEL (Optimized)")
print("="*60)

try:
    from xgboost import XGBRegressor
    
    xgb_model = XGBRegressor(
        n_estimators=300,
        max_depth=5,  # Reduced to prevent overfitting
        learning_rate=0.01,  # Lower learning rate
        subsample=0.7,
        colsample_bytree=0.7,
        min_child_weight=5,
        reg_alpha=0.1,  # L1 regularization
        reg_lambda=1.0,  # L2 regularization
        random_state=42
    )
    
    xgb_model.fit(X_train, y_train)
    xgb_pred = xgb_model.predict(X_test)
    
    xgb_mape = mean_absolute_percentage_error(y_test, xgb_pred) * 100
    xgb_accuracy = 100 - xgb_mape
    xgb_rmse = np.sqrt(mean_squared_error(y_test, xgb_pred))
    
    results['XGBoost'] = {'accuracy': xgb_accuracy, 'mape': xgb_mape, 'rmse': xgb_rmse}
    
    print(f"✅ XGBoost Results:")
    print(f"   Accuracy: {xgb_accuracy:.2f}%")
    print(f"   MAPE: {xgb_mape:.2f}%")
    print(f"   RMSE: {xgb_rmse:.2f}")
    
    if xgb_accuracy > 85:
        print(f"   🎯 TARGET ACHIEVED! >85% accuracy!")
    
except ImportError:
    print("❌ XGBoost not available")
    results['XGBoost'] = {'accuracy': 0, 'mape': 100, 'rmse': float('inf')}

# 3. ENSEMBLE (Average of models)
print("\n" + "="*60)
print("3. ENSEMBLE MODEL")
print("="*60)

if 'XGBoost' in results and results['XGBoost']['accuracy'] > 0:
    ensemble_pred = (rf_pred + xgb_pred) / 2
else:
    ensemble_pred = rf_pred

ensemble_mape = mean_absolute_percentage_error(y_test, ensemble_pred) * 100
ensemble_accuracy = 100 - ensemble_mape
ensemble_rmse = np.sqrt(mean_squared_error(y_test, ensemble_pred))

results['Ensemble'] = {'accuracy': ensemble_accuracy, 'mape': ensemble_mape, 'rmse': ensemble_rmse}

print(f"✅ Ensemble Results:")
print(f"   Accuracy: {ensemble_accuracy:.2f}%")
print(f"   MAPE: {ensemble_mape:.2f}%")
print(f"   RMSE: {ensemble_rmse:.2f}")

if ensemble_accuracy > 85:
    print(f"   🎯 TARGET ACHIEVED! >85% accuracy!")

# FINAL RESULTS
print("\n" + "="*60)
print("FINAL RESULTS SUMMARY")
print("="*60)

print(f"\n📊 Model Comparison:")
print(f"{'Model':<15} {'Accuracy':<12} {'MAPE':<12} {'RMSE':<12}")
print("-" * 51)

for model_name, metrics in results.items():
    status = "✅" if metrics['accuracy'] > 85 else "  "
    print(f"{status} {model_name:<13} {metrics['accuracy']:>9.2f}% {metrics['mape']:>10.2f}% {metrics['rmse']:>10.0f}")

# Best model
best_model = max(results.items(), key=lambda x: x[1]['accuracy'])
print(f"\n🏆 Best Model: {best_model[0]} with {best_model[1]['accuracy']:.2f}% accuracy")

if best_model[1]['accuracy'] > 85:
    print(f"\n🎯 SUCCESS! Achieved {best_model[1]['accuracy']:.2f}% forecast accuracy (>85% target)")
    
    # Show predictions
    print(f"\n📈 Sample Weekly Predictions ({best_model[0]}):")
    if best_model[0] == 'Ensemble':
        predictions = ensemble_pred
    elif best_model[0] == 'RandomForest':
        predictions = rf_pred
    else:
        predictions = xgb_pred
    
    for i in range(min(5, len(y_test))):
        actual = y_test.iloc[i]
        predicted = predictions[i]
        error = abs(actual - predicted) / actual * 100
        date = dates_test.iloc[i].strftime('%Y-%m-%d')
        print(f"   Week {date}: Actual={actual:8.0f}, Predicted={predicted:8.0f}, Error={error:5.1f}%")
else:
    print(f"\n⚠️ Best accuracy: {best_model[1]['accuracy']:.2f}% (Target: >85%)")

print("\n✅ Training complete!")