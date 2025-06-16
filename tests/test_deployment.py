#!/usr/bin/env python3
import requests
import json
import time
import sys

def test_endpoint(base_url, endpoint, method='GET', data=None, expected_status=200):
    """Test a specific endpoint"""
    url = f"{base_url}{endpoint}"
    
    try:
        if method == 'GET':
            response = requests.get(url, timeout=30)
        elif method == 'POST':
            response = requests.post(url, json=data, timeout=30)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        if response.status_code == expected_status:
            print(f"PASS {method} {endpoint} - Status: {response.status_code}")
            return True, response.json()
        else:
            print(f"FAIL {method} {endpoint} - Expected: {expected_status}, Got: {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
            return False, None
            
    except requests.exceptions.RequestException as e:
        print(f"FAIL {method} {endpoint} - Connection Error: {e}")
        return False, None
    except json.JSONDecodeError as e:
        print(f"FAIL {method} {endpoint} - JSON Decode Error: {e}")
        return False, None

def wait_for_server(base_url, max_attempts=30, delay=2):
    """Wait for server to be ready"""
    print(f"Waiting for server at {base_url} to be ready...")
    
    for attempt in range(max_attempts):
        try:
            response = requests.get(f"{base_url}/health", timeout=5)
            if response.status_code == 200:
                print(f"Server is ready after {attempt + 1} attempts")
                return True
        except requests.exceptions.RequestException:
            pass
        
        if attempt < max_attempts - 1:
            time.sleep(delay)
    
    print(f"Server not ready after {max_attempts} attempts")
    return False

def run_deployment_tests(base_url):
    """Run comprehensive deployment tests"""
    print("VENDOR QUALIFICATION SYSTEM - DEPLOYMENT TESTS")
    print("=" * 60)
    print(f"Testing API at: {base_url}")
    print("-" * 60)
    
    # Wait for server to be ready
    if not wait_for_server(base_url):
        return False
    
    tests_passed = 0
    tests_total = 0
    
    # Test 1: Health Check
    print("\nTest 1: Health Check")
    tests_total += 1
    success, data = test_endpoint(base_url, "/health")
    if success:
        tests_passed += 1
        print(f"   Data loader status: {data.get('data_loader_status')}")
        print(f"   Total products: {data.get('total_products')}")
        print(f"   Total features: {data.get('total_features')}")
    
    # Test 2: Root Endpoint
    print("\nTest 2: Root Endpoint")
    tests_total += 1
    success, data = test_endpoint(base_url, "/")
    if success:
        tests_passed += 1
        print(f"   API Version: {data.get('version')}")
        print(f"   Description: {data.get('description')}")
    
    # Test 3: Categories
    print("\nTest 3: Categories Endpoint")
    tests_total += 1
    success, data = test_endpoint(base_url, "/categories")
    if success:
        tests_passed += 1
        print(f"   Total categories: {data.get('total_categories')}")
        print(f"   Total products: {data.get('total_products')}")
    
    # Test 4: Features
    print("\nTest 4: Features Endpoint")
    tests_total += 1
    success, data = test_endpoint(base_url, "/features?limit=5")
    if success:
        tests_passed += 1
        print(f"   Total unique features: {data.get('total_unique_features')}")
        if data.get('common_features'):
            top_features = list(data['common_features'].keys())[:3]
            print(f"   Top features: {top_features}")
    
    # Test 5: Vendors
    print("\nTest 5: Vendors Endpoint")
    tests_total += 1
    success, data = test_endpoint(base_url, "/vendors?category=CRM")
    if success:
        tests_passed += 1
        print(f"   Total vendors: {data.get('total_vendors')}")
        print(f"   Category filter: {data.get('category_filter')}")
    
    # Test 6: Main Vendor Qualification (Low Threshold)
    print("\nTest 6: Vendor Qualification (threshold=0.4)")
    tests_total += 1
    query_data = {
        "software_category": "CRM Software",
        "capabilities": ["Lead Management", "Email Marketing"],
        "similarity_threshold": 0.5,
        "top_n": 5,
        "include_explanations": False
    }
    success, data = test_endpoint(base_url, "/vendor_qualification", method='POST', data=query_data)
    if success:
        tests_passed += 1
        results = data.get('results', {})
        print(f"   Qualified vendors: {results.get('total_qualified_vendors')}")
        print(f"   Returned vendors: {results.get('returned_vendors')}")
        
        if results.get('ranked_vendors'):
            top_vendor = results['ranked_vendors'][0]
            print(f"   Top vendor: {top_vendor.get('product_name')} (score: {top_vendor.get('rank_score', 0):.3f})")
    
    # Test 7: Vendor Qualification with Explanations
    print("\nTest 7: Vendor Qualification with Explanations")
    tests_total += 1
    query_data = {
        "software_category": "CRM Software",
        "capabilities": ["Contact Management"],
        "similarity_threshold": 0.5,
        "top_n": 3,
        "include_explanations": True
    }
    success, data = test_endpoint(base_url, "/vendor_qualification", method='POST', data=query_data)
    if success:
        tests_passed += 1
        print(f"   Response includes explanations: {'ranking_explanation' in str(data)}")
        print(f"   Response includes methodology: {'methodology' in data}")
    
    # Test 8: Edge Case - High Threshold
    print("\nTest 8: Edge Case - High Threshold (0.9)")
    tests_total += 1
    query_data = {
        "software_category": "CRM Software",
        "capabilities": ["Lead Management"],
        "similarity_threshold": 0.9,
        "top_n": 10
    }
    success, data = test_endpoint(base_url, "/vendor_qualification", method='POST', data=query_data)
    if success:
        tests_passed += 1
        results = data.get('results', {})
        print(f"   High threshold handled: {results.get('total_qualified_vendors', 0)} vendors found")
        if 'analysis' in data:
            print("   Includes helpful suggestions for no matches")
    
    # Summary
    print("\n" + "=" * 60)
    print("DEPLOYMENT TEST SUMMARY")
    print("=" * 60)
    print(f"Passed: {tests_passed}/{tests_total}")
    print(f"Failed: {tests_total - tests_passed}/{tests_total}")
    
    if tests_passed == tests_total:
        print("\nALL DEPLOYMENT TESTS PASSED!")
        print("API is ready for production use!")
        return True
    else:
        print(f"\n{tests_total - tests_passed} TEST(S) FAILED!")
        print("Please check the API deployment and fix issues.")
        return False

def main():
    """Main test execution"""
    print("VENDOR QUALIFICATION SYSTEM - DEPLOYMENT TESTS")
    print("=" * 60)
    
    base_url = 'http://localhost:5000'
    
    print(f"Testing API deployment at: {base_url}")
    print("Make sure the API server is running with: python deployment_script.py")
    print("-" * 60)
    
    success = run_deployment_tests(base_url)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 