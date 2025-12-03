#!/usr/bin/env python3
"""
GreenTech Painting - System Test Script
Tests all components to ensure everything works without VBA.
"""
import sys
import json
import pathlib
from datetime import datetime

def test_imports():
    """Test that all required modules can be imported"""
    print("=" * 70)
    print("TEST 1: Module Imports")
    print("=" * 70)
    
    try:
        from oauth import get_access_token, get_auth_header
        print("✅ oauth.py - OK")
    except Exception as e:
        print(f"❌ oauth.py - FAILED: {e}")
        return False
    
    try:
        from quickbooks_client import get_company_info, QuickBooksAPIError
        print("✅ quickbooks_client.py - OK")
    except Exception as e:
        print(f"❌ quickbooks_client.py - FAILED: {e}")
        return False
    
    try:
        from mapping import validate_quote_data, map_quote_to_qbo_estimate
        print("✅ mapping.py - OK")
    except Exception as e:
        print(f"❌ mapping.py - FAILED: {e}")
        return False
    
    try:
        from cli_push_estimate import process_quote
        print("✅ cli_push_estimate.py - OK")
    except Exception as e:
        print(f"❌ cli_push_estimate.py - FAILED: {e}")
        return False
    
    try:
        from api_server import app
        print("✅ api_server.py - OK")
    except Exception as e:
        print(f"❌ api_server.py - FAILED: {e}")
        return False
    
    print()
    return True

def test_json_validation():
    """Test JSON validation"""
    print("=" * 70)
    print("TEST 2: JSON Validation")
    print("=" * 70)
    
    try:
        from mapping import validate_quote_data
        
        # Test with sample JSON
        sample_path = pathlib.Path("samples/quote_sample.json")
        if not sample_path.exists():
            print(f"❌ Sample JSON not found: {sample_path}")
            return False
        
        with open(sample_path, 'r') as f:
            data = json.load(f)
        
        is_valid, error = validate_quote_data(data)
        
        if is_valid:
            print(f"✅ JSON validation - PASS")
            print(f"   Reference: {data.get('quote', {}).get('reference', 'N/A')}")
            print(f"   Customer: {data.get('customer', {}).get('display_name', 'N/A')}")
            print(f"   Items: {len(data.get('items', []))}")
            return True
        else:
            print(f"❌ JSON validation - FAILED: {error}")
            return False
            
    except Exception as e:
        print(f"❌ JSON validation - ERROR: {e}")
        return False

def test_oauth_config():
    """Test OAuth configuration"""
    print()
    print("=" * 70)
    print("TEST 3: OAuth Configuration")
    print("=" * 70)
    
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    client_id = os.getenv("QBO_CLIENT_ID")
    client_secret = os.getenv("QBO_CLIENT_SECRET")
    refresh_token = os.getenv("QBO_REFRESH_TOKEN")
    realm_id = os.getenv("QBO_REALM_ID")
    mode = os.getenv("QBO_MODE", "sandbox")
    
    if not client_id:
        print("⚠️  QBO_CLIENT_ID not set in .env")
        print("   (This is OK if you haven't set up OAuth yet)")
        return False
    
    if not client_secret:
        print("⚠️  QBO_CLIENT_SECRET not set in .env")
        print("   (This is OK if you haven't set up OAuth yet)")
        return False
    
    print(f"✅ Client ID: {client_id[:20]}...")
    print(f"✅ Client Secret: {'*' * 20}...")
    print(f"✅ Mode: {mode}")
    
    if refresh_token:
        print(f"✅ Refresh Token: {refresh_token[:20]}...")
    else:
        print("⚠️  Refresh Token not set (run initial_oauth_setup.py)")
    
    if realm_id:
        print(f"✅ Realm ID: {realm_id}")
    else:
        print("⚠️  Realm ID not set (run initial_oauth_setup.py)")
    
    print()
    
    if refresh_token and realm_id:
        return True
    else:
        print("ℹ️  OAuth not fully configured - you can still test with --mock flag")
        return False

def test_quickbooks_connection():
    """Test QuickBooks connection (if configured)"""
    print("=" * 70)
    print("TEST 4: QuickBooks Connection")
    print("=" * 70)
    
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    refresh_token = os.getenv("QBO_REFRESH_TOKEN")
    realm_id = os.getenv("QBO_REALM_ID")
    
    if not refresh_token or not realm_id:
        print("⚠️  Skipping - OAuth not configured")
        print("   Run: python initial_oauth_setup.py")
        return None
    
    try:
        from quickbooks_client import get_company_info
        
        print("🔄 Testing connection...")
        company = get_company_info()
        
        print(f"✅ Connected to: {company.get('CompanyName', 'Unknown')}")
        print(f"   Company ID: {company.get('Id', 'Unknown')}")
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("   Make sure your tokens are valid")
        return False

def test_mock_estimate():
    """Test creating a mock estimate"""
    print()
    print("=" * 70)
    print("TEST 5: Mock Estimate Creation")
    print("=" * 70)
    
    try:
        from cli_push_estimate import process_quote
        
        sample_path = pathlib.Path("samples/quote_sample.json")
        if not sample_path.exists():
            print(f"❌ Sample JSON not found: {sample_path}")
            return False
        
        print("🔄 Creating mock estimate...")
        result = process_quote(sample_path, use_mock=True)
        
        if result.get("ok"):
            print(f"✅ Mock estimate created successfully!")
            print(f"   Reference: {result.get('reference')}")
            print(f"   Customer: {result.get('customer_name')}")
            print(f"   PDF: {result.get('pdf_path')}")
            return True
        else:
            print(f"❌ Mock estimate failed: {result.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ Mock estimate - ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_api_server_imports():
    """Test that API server can be imported and basic routes exist"""
    print()
    print("=" * 70)
    print("TEST 6: API Server")
    print("=" * 70)
    
    try:
        from api_server import app
        
        # Check that routes exist
        routes = [str(rule) for rule in app.url_map.iter_rules()]
        
        required_routes = ['/health', '/api/v1/status', '/api/v1/estimate']
        found_routes = []
        
        for route in required_routes:
            if any(route in r for r in routes):
                found_routes.append(route)
                print(f"✅ Route found: {route}")
            else:
                print(f"⚠️  Route missing: {route}")
        
        if len(found_routes) == len(required_routes):
            print("✅ API server routes - OK")
            return True
        else:
            print("⚠️  Some routes missing")
            return False
            
    except Exception as e:
        print(f"❌ API server - ERROR: {e}")
        return False

def main():
    """Run all tests"""
    print()
    print("=" * 70)
    print("GreenTech Painting - System Test")
    print("=" * 70)
    print(f"Test started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    results = {}
    
    # Test 1: Imports
    results['imports'] = test_imports()
    
    # Test 2: JSON Validation
    results['json'] = test_json_validation()
    
    # Test 3: OAuth Config
    results['oauth'] = test_oauth_config()
    
    # Test 4: QuickBooks Connection (if configured)
    results['connection'] = test_quickbooks_connection()
    
    # Test 5: Mock Estimate
    results['mock'] = test_mock_estimate()
    
    # Test 6: API Server
    results['api'] = test_api_server_imports()
    
    # Summary
    print()
    print("=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    for test_name, result in results.items():
        if result is True:
            status = "✅ PASS"
        elif result is False:
            status = "❌ FAIL"
        else:
            status = "⚠️  SKIP"
        print(f"{test_name.upper():15} {status}")
    
    print()
    
    # Overall status
    critical_tests = ['imports', 'json', 'mock', 'api']
    passed = sum(1 for t in critical_tests if results.get(t) is True)
    
    if passed == len(critical_tests):
        print("✅ ALL CRITICAL TESTS PASSED")
        print()
        print("Your system is ready to use!")
        print()
        print("Next steps:")
        print("1. If OAuth not configured: python initial_oauth_setup.py")
        print("2. Test with mock: python cli_push_estimate.py --json samples/quote_sample.json --mock")
        print("3. Create real estimate: python cli_push_estimate.py --json samples/quote_sample.json")
        print("4. Start API server: python start_server.py")
        return 0
    else:
        print("⚠️  SOME TESTS FAILED")
        print("Please fix the issues above before proceeding")
        return 1

if __name__ == "__main__":
    sys.exit(main())

