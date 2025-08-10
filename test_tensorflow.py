#!/usr/bin/env python3
"""
Test TensorFlow imports
"""

import sys
import traceback

print("Testing TensorFlow imports...")
print("-" * 60)

# Test 1: Basic TensorFlow import
try:
    import tensorflow as tf
    print(f"✓ TensorFlow {tf.__version__} imported successfully")
except Exception as e:
    print(f"✗ Failed to import tensorflow: {e}")
    traceback.print_exc()

# Test 2: Keras models import
try:
    from tensorflow.keras.models import Sequential
    print("✓ tensorflow.keras.models.Sequential imported successfully")
except Exception as e:
    print(f"✗ Failed to import Sequential: {e}")
    traceback.print_exc()

# Test 3: Keras layers import
try:
    from tensorflow.keras.layers import LSTM, Dense, Dropout
    print("✓ tensorflow.keras.layers (LSTM, Dense, Dropout) imported successfully")
except Exception as e:
    print(f"✗ Failed to import layers: {e}")
    traceback.print_exc()

# Test 4: Alternative import method
try:
    import tensorflow.keras.layers as layers
    print("✓ tensorflow.keras.layers imported as module successfully")
except Exception as e:
    print(f"✗ Failed to import layers module: {e}")
    traceback.print_exc()

# Test 5: Check what's available
print("\n" + "-" * 60)
print("Checking available modules:")
try:
    import tensorflow.keras as keras
    print(f"Available in keras: {dir(keras)[:5]}...")  # Show first 5 items
    print(f"Keras version: {keras.__version__}")
except Exception as e:
    print(f"Error checking keras: {e}")

print("-" * 60)
print("Test complete!")