#!/usr/bin/env python3
"""
Quick integration test for Beverly Knits ERP system
Tests data loading, planning engine, and API endpoints
"""

import sys
import os
sys.path.append('/mnt/d/32-jkhjk/efab.ai/src')

from pathlib import Path
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_data_integration():
    """Test the data integration module"""
    print("=" * 60)
    print("TESTING DATA INTEGRATION")
    print("=" * 60)
    
    try:
        from data.data_integration import DataIntegrator
        
        # Test with Beverly Knits data path
        integrator = DataIntegrator("/mnt/c/Users/psytz/TMUX Final/Agent-MCP/ERP Data/4")
        
        # Load raw data
        raw_data = integrator._load_raw_data()
        
        print(f"✅ Loaded {len(raw_data)} data types:")
        for key, df in raw_data.items():
            print(f"  - {key}: {len(df)} rows")
        
        return True
    except Exception as e:
        print(f"❌ Data integration failed: {e}")
        return False

def test_planning_engine():
    """Test the planning engine"""
    print("\n" + "=" * 60)
    print("TESTING PLANNING ENGINE")
    print("=" * 60)
    
    try:
        from engine.planning_engine import PlanningEngine
        
        engine = PlanningEngine()
        
        # Test Beverly Knits planning cycle
        print("Testing execute_beverly_knits_planning_cycle()...")
        
        # Use the actual data path
        recommendations = engine.execute_beverly_knits_planning_cycle(
            data_path="/mnt/c/Users/psytz/TMUX Final/Agent-MCP/ERP Data/4"
        )
        
        print(f"✅ Generated {len(recommendations)} procurement recommendations")
        
        if recommendations:
            total_cost = sum(rec.total_cost.amount for rec in recommendations)
            print(f"  Total procurement cost: ${total_cost:,.2f}")
        
        return True
    except Exception as e:
        print(f"❌ Planning engine failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_csv_files():
    """Test that CSV files are accessible"""
    print("\n" + "=" * 60)
    print("TESTING CSV FILE ACCESS")
    print("=" * 60)
    
    data_path = Path("/mnt/c/Users/psytz/TMUX Final/Agent-MCP/ERP Data/4")
    
    if not data_path.exists():
        print(f"❌ Data path not found: {data_path}")
        return False
    
    csv_files = list(data_path.glob("*.csv"))
    print(f"✅ Found {len(csv_files)} CSV files")
    
    # Check for key Beverly Knits files
    expected_patterns = [
        "eFab_Inventory_F01",
        "eFab_Inventory_G00", 
        "eFab_Inventory_G02",
        "eFab_Inventory_I01",
        "Yarn_Demand",
        "eFab_SO_List"
    ]
    
    for pattern in expected_patterns:
        matching = [f for f in csv_files if pattern in f.name]
        if matching:
            print(f"  ✅ {pattern}: {matching[0].name}")
        else:
            print(f"  ❌ {pattern}: NOT FOUND")
    
    return len(csv_files) > 0

def test_api_endpoints():
    """Test API endpoints"""
    print("\n" + "=" * 60)
    print("TESTING API ENDPOINTS")
    print("=" * 60)
    
    import requests
    
    endpoints = [
        ("http://localhost:8501", "Streamlit Dashboard"),
        ("http://localhost:8082/api/health", "API Health"),
        ("http://localhost:8080/api/status", "MCP Status")
    ]
    
    results = []
    for url, name in endpoints:
        try:
            resp = requests.get(url, timeout=2)
            if resp.status_code < 500:
                print(f"  ✅ {name}: {resp.status_code}")
                results.append(True)
            else:
                print(f"  ❌ {name}: {resp.status_code}")
                results.append(False)
        except Exception as e:
            print(f"  ❌ {name}: Connection failed")
            results.append(False)
    
    return any(results)

def main():
    """Run all tests"""
    print("\n🧪 BEVERLY KNITS ERP INTEGRATION TEST SUITE")
    print("=" * 60)
    
    results = {
        "CSV Files": test_csv_files(),
        "Data Integration": test_data_integration(),
        "Planning Engine": test_planning_engine(),
        "API Endpoints": test_api_endpoints()
    }
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    total_passed = sum(results.values())
    total_tests = len(results)
    
    print(f"\nOverall: {total_passed}/{total_tests} tests passed")
    
    if total_passed == total_tests:
        print("🎉 ALL TESTS PASSED! System is ready.")
    else:
        print("⚠️ Some tests failed. Please fix the issues.")
    
    return total_passed == total_tests

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)