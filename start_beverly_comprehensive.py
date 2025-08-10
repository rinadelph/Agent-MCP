#!/usr/bin/env python3
"""
Start Beverly Comprehensive ERP - Fixed Version
"""

import os
import sys

# Set environment to production to avoid debug mode issues
os.environ['FLASK_ENV'] = 'production'
os.environ['FLASK_DEBUG'] = '0'

# Import and run
if __name__ == "__main__":
    from beverly_comprehensive_erp import app
    from flask_cors import CORS
    
    # Ensure CORS is enabled
    CORS(app, origins="*")
    
    print("\n" + "="*60)
    print("BEVERLY KNITS COMPREHENSIVE ERP")
    print("="*60)
    print("✅ CORS enabled for all origins")
    print("✅ Debug mode disabled") 
    print("✅ Server starting on http://0.0.0.0:5003")
    print("="*60 + "\n")
    
    app.run(host='0.0.0.0', port=5003, debug=False)