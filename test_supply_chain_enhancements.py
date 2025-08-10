#!/usr/bin/env python3
"""
Test script for the new Supply Chain Optimization enhancements
"""

import sys
import os
from pathlib import Path

# Add the current directory to the path so we can import the module
sys.path.insert(0, str(Path(__file__).parent))

try:
    from beverly_comprehensive_erp import ComprehensiveSupplyChainAI
    print("✅ Successfully imported ComprehensiveSupplyChainAI")
except ImportError as e:
    print(f"❌ Failed to import: {e}")
    sys.exit(1)

def test_supply_chain_enhancements():
    """Test all the new supply chain optimization methods"""
    
    # Initialize the analyzer
    data_path = Path("ERP Data/New folder")
    print(f"📁 Initializing analyzer with data path: {data_path}")
    
    try:
        analyzer = ComprehensiveSupplyChainAI(data_path)
        print("✅ Analyzer initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize analyzer: {e}")
        return False
    
    # Test 1: Dynamic EOQ Calculation
    print("\n🔧 Testing calculate_dynamic_eoq()...")
    try:
        dynamic_eoq_results = analyzer.calculate_dynamic_eoq()
        print(f"✅ Dynamic EOQ calculation completed. Found {len(dynamic_eoq_results)} items")
        
        if len(dynamic_eoq_results) > 0:
            sample_item = dynamic_eoq_results[0]
            print(f"   Sample result: {sample_item['item']} - Dynamic EOQ: {sample_item['dynamic_eoq']}")
            print(f"   Seasonality factor: {sample_item['seasonality_factor']}")
        else:
            print("   No items returned (may be expected if no data files)")
            
    except Exception as e:
        print(f"❌ Dynamic EOQ calculation failed: {e}")
        return False
    
    # Test 2: Supplier Risk Scoring
    print("\n🏢 Testing calculate_supplier_risk_score()...")
    try:
        supplier_risks = analyzer.calculate_supplier_risk_score()
        print(f"✅ Supplier risk scoring completed. Found {len(supplier_risks)} suppliers")
        
        if len(supplier_risks) > 0:
            sample_supplier = supplier_risks[0]
            print(f"   Sample result: {sample_supplier['supplier']} - Risk Score: {sample_supplier['risk_score']} ({sample_supplier['risk_level']})")
            print(f"   Mitigation Strategy: {sample_supplier['mitigation_strategy']}")
        else:
            print("   No suppliers returned (may be expected if no data files)")
            
    except Exception as e:
        print(f"❌ Supplier risk scoring failed: {e}")
        return False
    
    # Test 3: Emergency Procurement Handler
    print("\n🚨 Testing handle_emergency_procurement()...")
    try:
        emergency_items = analyzer.handle_emergency_procurement()
        print(f"✅ Emergency procurement analysis completed. Found {len(emergency_items)} critical items")
        
        if len(emergency_items) > 0:
            sample_emergency = emergency_items[0]
            print(f"   Sample result: {sample_emergency['item']} - Days of supply: {sample_emergency['days_of_supply']}")
            print(f"   Urgency: {sample_emergency['urgency']}, Recommended action: {sample_emergency['recommendation']}")
        else:
            print("   No emergency items found (good news!)")
            
    except Exception as e:
        print(f"❌ Emergency procurement analysis failed: {e}")
        return False
    
    # Test 4: Enhanced get_advanced_inventory_optimization()
    print("\n⚡ Testing enhanced get_advanced_inventory_optimization()...")
    try:
        optimization_results = analyzer.get_advanced_inventory_optimization()
        print(f"✅ Advanced inventory optimization completed. Found {len(optimization_results)} recommendations")
        
        if len(optimization_results) > 0:
            sample_opt = optimization_results[0]
            print(f"   Sample result: {sample_opt['item']} - EOQ: {sample_opt['eoq']}")
            print(f"   Total savings: {sample_opt['total_savings']}, Lead time risk: {sample_opt['lead_time_risk']}")
            print(f"   Recommendations: {sample_opt['recommendations'][0] if sample_opt['recommendations'] else 'None'}")
        else:
            print("   No optimization recommendations (may be expected if no data files)")
            
    except Exception as e:
        print(f"❌ Advanced inventory optimization failed: {e}")
        return False
    
    print("\n🎉 All tests completed successfully!")
    return True

def test_api_availability():
    """Test that the new API endpoints would work"""
    
    print("\n🌐 Testing API endpoint availability...")
    
    # Import Flask app components
    try:
        from beverly_comprehensive_erp import app
        print("✅ Flask app imported successfully")
        
        # Check if our new routes are registered
        routes = [rule.rule for rule in app.url_map.iter_rules()]
        
        expected_routes = [
            '/api/dynamic-eoq',
            '/api/supplier-risk-scoring', 
            '/api/emergency-procurement'
        ]
        
        for route in expected_routes:
            if route in routes:
                print(f"✅ Route {route} is registered")
            else:
                print(f"❌ Route {route} is missing")
                return False
                
    except Exception as e:
        print(f"❌ API testing failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("🧪 Testing Beverly Knits Supply Chain Enhancements")
    print("=" * 60)
    
    # Run functionality tests
    functionality_success = test_supply_chain_enhancements()
    
    # Run API tests
    api_success = test_api_availability()
    
    print("\n" + "=" * 60)
    if functionality_success and api_success:
        print("🎉 All tests PASSED! The supply chain enhancements are ready.")
        sys.exit(0)
    else:
        print("❌ Some tests FAILED. Please review the errors above.")
        sys.exit(1)