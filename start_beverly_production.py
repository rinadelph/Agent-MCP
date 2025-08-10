#!/usr/bin/env python3
"""
Beverly Knits Comprehensive ERP - Production Launcher
Handles all TensorFlow import issues gracefully
"""

import os
import sys
import warnings

# Suppress all warnings and TensorFlow messages
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['FLASK_ENV'] = 'production'
os.environ['FLASK_DEBUG'] = '0'
warnings.filterwarnings('ignore')

# Suppress TensorFlow logging
import logging
logging.getLogger('tensorflow').setLevel(logging.ERROR)
logging.getLogger('tensorflow').disabled = True

def main():
    """Main entry point for production server"""
    try:
        # Import with all warnings suppressed
        from beverly_comprehensive_erp import app, analyzer
        from flask_cors import CORS
        
        # Enable CORS for all origins
        CORS(app, origins="*")
        
        print("\n" + "="*70)
        print(" BEVERLY KNITS COMPREHENSIVE ERP - PRODUCTION SERVER")
        print("="*70)
        print()
        print(" Status: ✅ READY")
        print(" Port:   5003")
        print(" URL:    http://localhost:5003")
        print(" CORS:   Enabled for all origins")
        print()
        
        # Show data statistics
        data_loaded = False
        if hasattr(analyzer, 'sales_data') and analyzer.sales_data is not None:
            print(f" Sales Data:      {len(analyzer.sales_data):,} records")
            data_loaded = True
        if hasattr(analyzer, 'raw_materials_data') and analyzer.raw_materials_data is not None:
            print(f" Materials Data:  {len(analyzer.raw_materials_data):,} records")
            data_loaded = True
        if hasattr(analyzer, 'bom_data') and analyzer.bom_data is not None:
            print(f" BOM Data:        {len(analyzer.bom_data):,} records")
            data_loaded = True
        
        if not data_loaded:
            print(" ⚠️  Warning: No data loaded")
        
        print()
        print("="*70)
        print(" Available Endpoints:")
        print("="*70)
        print("  /                          - Main dashboard")
        print("  /api/comprehensive-kpis    - Key performance indicators")
        print("  /api/planning-phases       - 6-phase planning data")
        print("  /api/ml-forecasting        - ML forecasting results")
        print("  /api/advanced-optimization - Optimization recommendations")
        print("  /api/yarn                  - Yarn inventory data")
        print("  /api/sales                 - Sales data")
        print("  /api/emergency-procurement - Emergency procurement analysis")
        print("="*70)
        print("\n Press Ctrl+C to stop the server\n")
        
        # Start the server
        app.run(host='0.0.0.0', port=5003, debug=False, use_reloader=False)
        
    except ImportError as e:
        print(f"\n❌ Import Error: {e}")
        print("\nPlease install required packages:")
        print("  pip install flask flask-cors pandas numpy")
        print("  pip install tensorflow scikit-learn prophet")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()