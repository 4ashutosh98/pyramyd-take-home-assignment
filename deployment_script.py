#!/usr/bin/env python3
"""
Deployment script for the Vendor Qualification System API
Starts the FastAPI server with proper configuration
"""

import uvicorn
import sys
import os
import time

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def check_dependencies():
    """Check if all required dependencies are installed"""
    print("Checking dependencies...")
    try:
        import pandas
        import sklearn
        import fastapi
        import uvicorn
        print("All dependencies are installed.")
        return True
    except ImportError as e:
        print(f"Missing dependency: {e}")
        print("Please run: pip install -r requirements.txt")
        return False

def check_data_file():
    """Check if the data file exists"""
    data_file = "data/G2 software - CRM Category Product Overviews.csv"
    if os.path.exists(data_file):
        print(f"Data file found: {data_file}")
        return True
    else:
        print(f"Data file not found: {data_file}")
        print("Please ensure the CSV file is in the data/ directory")
        return False

def main():
    """Main deployment function"""
    print("VENDOR QUALIFICATION SYSTEM - DEPLOYMENT")
    print("=" * 60)
    
    # Pre-flight checks
    if not check_dependencies():
        sys.exit(1)
    
    if not check_data_file():
        sys.exit(1)
    
    print("\nStarting Vendor Qualification System API...")
    print("Server will be available at: http://localhost:5000")
    print("API Documentation: http://localhost:5000/docs")
    print("Interactive API: http://localhost:5000/redoc")
    print("-" * 60)
    print("Press Ctrl+C to stop the server")
    print("-" * 60)
    
    try:
        # Start the FastAPI server
        uvicorn.run(
            "src.api.app:app",
            host="127.0.0.1",
            port=5000,
            reload=True,
            log_level="info",
            access_log=True
        )
    except KeyboardInterrupt:
        print("\nServer stopped by user")
    except Exception as e:
        print(f"Server error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 