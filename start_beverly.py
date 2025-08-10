#!/usr/bin/env python3
"""
Simple launcher for Beverly Comprehensive ERP
Ensures proper startup without debug mode issues
"""

import os
os.environ['FLASK_ENV'] = 'production'
os.environ['FLASK_DEBUG'] = '0'

from beverly_comprehensive_erp import app

if __name__ == "__main__":
    print("\n" + "="*60)
    print("Starting Beverly Knits Comprehensive ERP")
    print("="*60)
    print("✅ CORS enabled with Flask-CORS")
    print("✅ Server binding to 0.0.0.0:5003 (all interfaces)")
    print("✅ Access at: http://localhost:5003 or http://YOUR_IP:5003")
    print("="*60 + "\n")
    
    # Run without debug to avoid restart issues
    app.run(host='0.0.0.0', port=5003, debug=False)