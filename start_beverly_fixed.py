#!/usr/bin/env python3
"""
Start Beverly Comprehensive ERP with CORS and without debug mode
"""

import os
import sys

# Set environment to production to avoid debug mode
os.environ['FLASK_ENV'] = 'production'
os.environ['FLASK_DEBUG'] = '0'

# Import and run the comprehensive ERP
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the app but modify it before running
from beverly_comprehensive_erp import app, analyzer
from flask_cors import CORS

# Ensure CORS is enabled
CORS(app, origins="*")

print("\n" + "="*60)
print("BEVERLY KNITS COMPREHENSIVE ERP - FIXED VERSION")
print("="*60)
print("✅ CORS enabled for all origins")
print("✅ Debug mode disabled") 
print("✅ Server starting on http://0.0.0.0:5003")
print("✅ Access at: http://localhost:5003")
print("="*60 + "\n")

if __name__ == "__main__":
    # Run without debug mode
    app.run(host='0.0.0.0', port=5003, debug=False)