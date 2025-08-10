#!/usr/bin/env python3
"""
Test Beverly Knits data loading from New folder
Verifies all critical yarn and sales files load correctly
"""

import sys
import pandas as pd
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_beverly_knits_data():
    """Test loading all critical Beverly Knits data files"""
    
    data_path = Path("/mnt/c/Users/psytz/TMUX Final/Agent-MCP/ERP Data/New folder")
    
    if not data_path.exists():
        print(f"❌ Data path not found: {data_path}")
        return False
    
    print(f"✅ Data path exists: {data_path}")
    
    # Critical files to test
    critical_files = {
        "yarn_inventory": "yarn_inventory (1).xlsx",
        "yarn_demand_by_style": "Yarn_Demand_By_Style.xlsx",
        "yarn_demand": "Yarn_Demand_2025-08-03_0442.xlsx",
        "sales_activity": "Sales Activity Report (4).xlsx",
        "expected_yarn": "Expected_Yarn_Report.xlsx",
        "inventory_g00": "eFab_Inventory_G00_20250804.xlsx",
        "inventory_g02": "eFab_Inventory_G02_20250804.xlsx",
        "inventory_i01": "eFab_Inventory_I01_20250804.xlsx",
        "inventory_f01": "eFab_Inventory_F01_20250804 (1).xlsx",
        "inventory_p01": "eFab_Inventory_P01_20250808.xlsx",
        "finished_fabric": "QuadS_finishedFabricList_ (2) (1).xlsx",
        "bom": "BOM_2(Sheet1).csv",
        "sales_orders": "eFab_SO_List_202508040846.xlsx"
    }
    
    results = {}
    total_rows = 0
    
    print("\n" + "="*60)
    print("BEVERLY KNITS DATA LOADING TEST")
    print("="*60)
    
    for key, filename in critical_files.items():
        file_path = data_path / filename
        
        if not file_path.exists():
            print(f"❌ {key}: File not found - {filename}")
            results[key] = False
            continue
        
        try:
            # Load Excel or CSV file
            if file_path.suffix.lower() == '.csv':
                df = pd.read_csv(file_path, encoding='utf-8', low_memory=False)
            else:
                df = pd.read_excel(file_path, engine='openpyxl')
            rows = len(df)
            cols = len(df.columns)
            total_rows += rows
            
            print(f"✅ {key}: Loaded {rows:,} rows, {cols} columns from {filename}")
            
            # Show first few columns
            if len(df.columns) > 0:
                print(f"   Columns: {', '.join(df.columns[:5])}")
            
            results[key] = True
            
        except Exception as e:
            print(f"❌ {key}: Failed to load {filename} - {str(e)}")
            results[key] = False
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    success_count = sum(results.values())
    total_count = len(results)
    
    print(f"Files loaded: {success_count}/{total_count}")
    print(f"Total rows: {total_rows:,}")
    
    if success_count == total_count:
        print("🎉 ALL CRITICAL FILES LOADED SUCCESSFULLY!")
        print("\nData Pipeline Status:")
        print("  G00 (Knitting): ✅")
        print("  G02 (Processing): ✅") 
        print("  I01 (Inspection): ✅")
        print("  F01 (Ready): ✅")
        print("  P01 (Packed): ✅")
        print("  Yarn Planning: ✅")
        print("  Sales Data: ✅")
        return True
    else:
        print(f"⚠️ {total_count - success_count} files failed to load")
        return False

def test_data_integration():
    """Test the DataIntegrator class with Beverly Knits data"""
    print("\n" + "="*60)
    print("TESTING DATA INTEGRATOR")
    print("="*60)
    
    try:
        # Add the source directory to path
        sys.path.insert(0, '/mnt/d/32-jkhjk/efab.ai/src')
        
        from data.data_integration import DataIntegrator
        
        # Create integrator with Beverly Knits path
        integrator = DataIntegrator("/mnt/c/Users/psytz/TMUX Final/Agent-MCP/ERP Data/New folder")
        
        print(f"✅ DataIntegrator initialized with path: {integrator.data_path}")
        
        # Load raw data
        raw_data = integrator._load_raw_data()
        
        print(f"✅ Loaded {len(raw_data)} data types:")
        for key, df in raw_data.items():
            print(f"  - {key}: {len(df)} rows")
        
        # Apply fixes
        cleaned_data = integrator._apply_automatic_fixes(raw_data)
        
        print(f"✅ Data cleaned and validated")
        print(f"  Quality issues: {len(integrator.quality_issues)}")
        print(f"  Fixes applied: {len(integrator.fixes_applied)}")
        
        for fix in integrator.fixes_applied[:5]:
            print(f"    - {fix}")
        
        return True
        
    except Exception as e:
        print(f"❌ DataIntegrator test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🧪 BEVERLY KNITS DATA INTEGRATION TEST")
    print("="*60)
    
    # Test 1: Load individual files
    test1_pass = test_beverly_knits_data()
    
    # Test 2: Test DataIntegrator class
    test2_pass = test_data_integration()
    
    print("\n" + "="*60)
    print("FINAL RESULTS")
    print("="*60)
    
    if test1_pass and test2_pass:
        print("✅ ALL TESTS PASSED - System ready for Beverly Knits production!")
        sys.exit(0)
    else:
        print("❌ TESTS FAILED - Fix issues before production")
        sys.exit(1)