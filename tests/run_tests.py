#!/usr/bin/env python3
"""
Test runner for the Vendor Qualification System
Runs all tests in the tests directory
"""

import sys
import os
import subprocess

def run_test_file(test_file):
    """Run a specific test file"""
    print(f"\n{'='*60}")
    print(f"RUNNING: {test_file}")
    print(f"{'='*60}")
    
    try:
        # Change to project root directory (parent of tests)
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        result = subprocess.run([sys.executable, test_file], 
                              capture_output=False, 
                              text=True, 
                              cwd=project_root)
        
        if result.returncode == 0:
            print(f"\n{test_file} - PASSED")
            return True
        else:
            print(f"\n{test_file} - FAILED (exit code: {result.returncode})")
            return False
            
    except Exception as e:
        print(f"\n{test_file} - ERROR: {e}")
        return False

def check_dependencies():
    """Check if required dependencies are installed"""
    print("Checking dependencies...")
    try:
        import pandas
        import sklearn
        import fastapi
        import uvicorn
        import requests
        print("All dependencies are installed.")
        return True
    except ImportError as e:
        print(f"Missing dependency: {e}")
        print("Please run: pip install -r requirements.txt")
        return False

def check_data_file():
    """Check if data file exists"""
    # Get project root directory
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_file = os.path.join(project_root, "data", "G2 software - CRM Category Product Overviews.csv")
    
    if os.path.exists(data_file):
        print(f"Data file found: {data_file}")
        return True
    else:
        print(f"Data file not found: {data_file}")
        print("Please ensure the CSV file is in the data/ directory")
        return False

def main():
    """Main test runner function"""
    print("VENDOR QUALIFICATION SYSTEM - TEST RUNNER")
    print("="*60)
    
    # Pre-flight checks
    if not check_dependencies():
        return 1
    
    if not check_data_file():
        return 1
    
    print("\nStarting test execution...")
    
    # List of test files to run (relative to project root)
    test_files = [
        "tests/test_data_processing.py",
        "tests/test_similarity_system.py", 
        "tests/test_api.py"
    ]
    
    # Track results
    passed = 0
    failed = 0
    
    # Run each test file
    for test_file in test_files:
        # Check if file exists relative to project root
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        full_path = os.path.join(project_root, test_file)
        
        if os.path.exists(full_path):
            if run_test_file(test_file):
                passed += 1
            else:
                failed += 1
        else:
            print(f"Test file not found: {test_file}")
            failed += 1
    
    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Total: {passed + failed}")
    
    if failed == 0:
        print("\nALL TESTS PASSED!")
        print("The Vendor Qualification System is ready for deployment!")
        return 0
    else:
        print(f"\n{failed} TEST(S) FAILED!")
        print("Please fix the failing tests before deployment.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 