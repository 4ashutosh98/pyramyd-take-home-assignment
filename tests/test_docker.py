#!/usr/bin/env python3
"""
Docker Deployment Tests for Vendor Qualification System
Tests Docker build, container startup, and API functionality.
"""

import subprocess
import time
import requests
import json
import sys
import os

def run_command(command: str, check: bool = True) -> subprocess.CompletedProcess:
    """Run a shell command and return the result"""
    print(f"Running: {command}")
    try:
        result = subprocess.run(command, shell=True, check=check, capture_output=True, text=True)
        return result
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {e}")
        if check:
            raise
        return e

def test_docker_build():
    """Test Docker image build"""
    print("\nTesting Docker Build")
    print("-" * 40)
    
    try:
        result = run_command("docker build -t vendor-qualification-test .")
        if result.returncode == 0:
            print("Docker build successful")
            return True
        else:
            print(f"Docker build failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"Docker build error: {e}")
        return False

def test_container_startup():
    """Test container startup"""
    print("\nTesting Container Startup")
    print("-" * 40)
    
    try:
        # Stop any existing container
        run_command("docker stop vendor-qualification-test-container", check=False)
        run_command("docker rm vendor-qualification-test-container", check=False)
        
        # Start new container
        result = run_command(
            "docker run -d --name vendor-qualification-test-container -p 5001:5000 vendor-qualification-test"
        )
        
        if result.returncode == 0:
            print("Container started successfully")
            time.sleep(10)  # Wait for startup
            return True
        else:
            print(f"Container startup failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"Container startup error: {e}")
        return False

def test_api_health():
    """Test API health endpoint"""
    print("\nTesting API Health")
    print("-" * 40)
    
    max_attempts = 30
    for attempt in range(max_attempts):
        try:
            response = requests.get("http://localhost:5001/health", timeout=5)
            if response.status_code == 200:
                print("API health check passed")
                print(f"Response: {response.json()}")
                return True
        except requests.RequestException as e:
            print(f"Attempt {attempt + 1}/{max_attempts}: {e}")
            time.sleep(2)
    
    print("API health check failed")
    return False

def test_api_endpoints():
    """Test main API endpoints"""
    print("\nTesting API Endpoints")
    print("-" * 40)
    
    base_url = "http://localhost:5001"
    
    # Test root endpoint
    try:
        response = requests.get(f"{base_url}/")
        if response.status_code == 200:
            print("Root endpoint working")
        else:
            print(f"Root endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"Root endpoint error: {e}")
        return False
    
    # Test categories endpoint
    try:
        response = requests.get(f"{base_url}/categories")
        if response.status_code == 200:
            print("Categories endpoint working")
        else:
            print(f"Categories endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"Categories endpoint error: {e}")
        return False
    
    # Test main vendor qualification endpoint
    try:
        test_data = {
            "software_category": "CRM Software",
            "capabilities": ["Lead Management"],
            "similarity_threshold": 0.4,
            "top_n": 3,
            "include_explanations": True
        }
        
        response = requests.post(
            f"{base_url}/vendor_qualification",
            json=test_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print("Vendor qualification endpoint working")
            print(f"Found {result['results']['total_qualified_vendors']} qualified vendors")
            return True
        else:
            print(f"Vendor qualification failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"Vendor qualification error: {e}")
        return False

def test_container_logs():
    """Check container logs for errors"""
    print("\nChecking Container Logs")
    print("-" * 40)
    
    try:
        result = run_command("docker logs vendor-qualification-test-container", check=False)
        if "ERROR" in result.stdout or "CRITICAL" in result.stdout:
            print("Errors found in logs:")
            print(result.stdout)
            return False
        else:
            print("No critical errors in logs")
            return True
    except Exception as e:
        print(f"Log check error: {e}")
        return False

def cleanup_test_resources():
    """Clean up test containers and images"""
    print("\nCleaning Up Test Resources")
    print("-" * 40)
    
    try:
        run_command("docker stop vendor-qualification-test-container", check=False)
        run_command("docker rm vendor-qualification-test-container", check=False)
        run_command("docker rmi vendor-qualification-test", check=False)
        print("Test resources cleaned up")
    except Exception as e:
        print(f"Cleanup warning: {e}")

def test_docker_compose():
    """Test docker-compose deployment"""
    print("\nTesting Docker Compose")
    print("-" * 40)
    
    try:
        # Stop any existing services
        run_command("docker-compose down", check=False)
        
        # Start with compose
        result = run_command("docker-compose up -d --build")
        if result.returncode != 0:
            print(f"Docker compose failed: {result.stderr}")
            return False
        
        print("Docker compose started")
        time.sleep(15)  # Wait for services to start
        
        # Test health
        try:
            response = requests.get("http://localhost:5000/health", timeout=10)
            if response.status_code == 200:
                print("Docker compose API healthy")
                return True
            else:
                print(f"Docker compose API unhealthy: {response.status_code}")
                return False
        except Exception as e:
            print(f"Docker compose health check failed: {e}")
            return False
            
    except Exception as e:
        print(f"Docker compose test error: {e}")
        return False
    finally:
        # Cleanup
        run_command("docker-compose down", check=False)

def main():
    """Run all Docker tests"""
    print("VENDOR QUALIFICATION SYSTEM - DOCKER TESTS")
    print("=" * 60)
    
    # Check if Docker is available
    try:
        run_command("docker --version")
        run_command("docker info")
    except Exception:
        print("Docker is not available. Please install and start Docker.")
        sys.exit(1)
    
    # Check if data file exists
    if not os.path.exists("data/G2 software - CRM Category Product Overviews.csv"):
        print("Required data file not found. Please ensure the CSV file is in the data/ directory.")
        sys.exit(1)
    
    tests = [
        ("Docker Build", test_docker_build),
        ("Container Startup", test_container_startup),
        ("API Health", test_api_health),
        ("API Endpoints", test_api_endpoints),
        ("Container Logs", test_container_logs),
        ("Docker Compose", test_docker_compose)
    ]
    
    results = {}
    
    try:
        for test_name, test_func in tests:
            print(f"\n{'='*60}")
            print(f"Running: {test_name}")
            print(f"{'='*60}")
            
            try:
                results[test_name] = test_func()
            except Exception as e:
                print(f"{test_name} failed with exception: {e}")
                results[test_name] = False
    
    finally:
        # Always cleanup
        cleanup_test_resources()
    
    # Print summary
    print(f"\n{'='*60}")
    print("DOCKER TEST SUMMARY")
    print(f"{'='*60}")
    
    passed = 0
    total = len(tests)
    
    for test_name, result in results.items():
        status = "PASS" if result else "FAIL"
        print(f"{test_name:<25} {status}")
        if result:
            passed += 1
    
    print(f"\nResults: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\nALL DOCKER TESTS PASSED!")
        print("Docker deployment is working correctly!")
    else:
        print(f"\n{total-passed} tests failed. Please check the issues above.")
        sys.exit(1)

if __name__ == "__main__":
    main() 