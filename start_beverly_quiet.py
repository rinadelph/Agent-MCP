#!/usr/bin/env python3
"""
Start Beverly Comprehensive ERP - Quiet Version (No TensorFlow warnings)
"""

import os
import sys
import warnings

# Suppress TensorFlow warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # Suppress TensorFlow messages
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'  # Disable oneDNN custom operations
warnings.filterwarnings('ignore')

# Set environment to production
os.environ['FLASK_ENV'] = 'production'
os.environ['FLASK_DEBUG'] = '0'

# Import and run
if __name__ == "__main__":
    # Import with suppressed warnings
    import logging
    logging.getLogger('tensorflow').setLevel(logging.ERROR)
    
    from beverly_comprehensive_erp import app, analyzer
    from flask_cors import CORS
    
    # Ensure CORS is enabled
    CORS(app, origins="*")
    
    print("\n" + "="*60)
    print("BEVERLY KNITS COMPREHENSIVE ERP - PRODUCTION MODE")
    print("="*60)
    print("✅ Server starting on http://0.0.0.0:5003")
    print("✅ CORS enabled for all origins")
    print("✅ TensorFlow warnings suppressed")
    print("✅ Debug mode disabled")
    print("="*60)
    print("\nData loaded:")
    if hasattr(analyzer, 'sales_data') and analyzer.sales_data is not None:
        print(f"  ✓ Sales: {len(analyzer.sales_data)} records")
    if hasattr(analyzer, 'raw_materials_data') and analyzer.raw_materials_data is not None:
        print(f"  ✓ Materials: {len(analyzer.raw_materials_data)} records")
    if hasattr(analyzer, 'bom_data') and analyzer.bom_data is not None:
        print(f"  ✓ BOM: {len(analyzer.bom_data)} records")
    print("="*60 + "\n")
    
    app.run(host='0.0.0.0', port=5003, debug=False)