#!/usr/bin/env python3
"""
Docker Deployment Script for Vendor Qualification System
Provides easy commands for building, running, and managing Docker containers.
"""

import subprocess
import sys
import time
import argparse
import os
import requests
from typing import Optional

def run_command(command: str, check: bool = True) -> subprocess.CompletedProcess:
    """Run a shell command and return the result"""
    print(f"Running: {command}")
    try:
        result = subprocess.run(command, shell=True, check=check, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        return result
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {e}")
        if e.stderr:
            print(f"Error: {e.stderr}")
        if check:
            sys.exit(1)
        return e

def check_docker():
    """Check if Docker is installed and running"""
    print("Checking Docker installation...")
    
    try:
        result = run_command("docker --version", check=False)
        if result.returncode != 0:
            print("Docker is not installed. Please install Docker first.")
            sys.exit(1)
        
        result = run_command("docker info", check=False)
        if result.returncode != 0:
            print("Docker daemon is not running. Please start Docker.")
            sys.exit(1)
            
        print("Docker is ready!")
        
    except Exception as e:
        print(f"Docker check failed: {e}")
        sys.exit(1)

def check_data_file():
    """Check if the required data file exists"""
    data_file = "data/G2 software - CRM Category Product Overviews.csv"
    if not os.path.exists(data_file):
        print(f"Required data file not found: {data_file}")
        print("Please ensure the CSV file is in the data/ directory.")
        sys.exit(1)
    print("Data file found!")

def build_image(tag: str = "vendor-qualification:latest"):
    """Build the Docker image"""
    print(f"Building Docker image: {tag}")
    run_command(f"docker build -t {tag} .")
    print("Docker image built successfully!")

def run_container(
    tag: str = "vendor-qualification:latest",
    port: int = 5000,
    name: str = "vendor-api",
    detached: bool = True
):
    """Run the Docker container"""
    print(f"Starting container: {name}")
    
    # Stop existing container if running
    run_command(f"docker stop {name}", check=False)
    run_command(f"docker rm {name}", check=False)
    
    # Run new container
    detach_flag = "-d" if detached else ""
    run_command(f"docker run {detach_flag} --name {name} -p {port}:5000 {tag}")
    
    if detached:
        print(f"Container started! API available at http://localhost:{port}")
        print(f"API Documentation: http://localhost:{port}/docs")
    
def run_with_compose(profile: str = ""):
    """Run using docker-compose"""
    print("Starting with Docker Compose...")
    
    profile_flag = f"--profile {profile}" if profile else ""
    run_command(f"docker-compose {profile_flag} up -d --build")
    
    print("Services started with Docker Compose!")
    print("API: http://localhost:5000")

def stop_services():
    """Stop all running services"""
    print("Stopping services...")
    
    # Stop docker-compose services
    run_command("docker-compose down", check=False)
    
    # Stop individual container
    run_command("docker stop vendor-api", check=False)
    run_command("docker rm vendor-api", check=False)
    
    print("All services stopped!")

def check_health(url: str = "http://localhost:5000", max_attempts: int = 30):
    """Check if the API is healthy"""
    print(f"Checking API health at {url}...")
    
    for attempt in range(max_attempts):
        try:
            response = requests.get(f"{url}/health", timeout=5)
            if response.status_code == 200:
                print("API is healthy!")
                return True
        except requests.RequestException:
            pass
        
        print(f"Waiting for API... (attempt {attempt + 1}/{max_attempts})")
        time.sleep(2)
    
    print("API health check failed!")
    return False

def show_logs(container_name: str = "vendor-api", follow: bool = False):
    """Show container logs"""
    follow_flag = "-f" if follow else ""
    run_command(f"docker logs {follow_flag} {container_name}")

def cleanup():
    """Clean up Docker resources"""
    print("Cleaning up Docker resources...")
    
    # Stop and remove containers
    run_command("docker-compose down --remove-orphans", check=False)
    run_command("docker stop vendor-api", check=False)
    run_command("docker rm vendor-api", check=False)
    
    # Remove images
    run_command("docker rmi vendor-qualification:latest", check=False)
    
    # Clean up unused resources
    run_command("docker system prune -f", check=False)
    
    print("Cleanup completed!")

def main():
    parser = argparse.ArgumentParser(description="Docker deployment for Vendor Qualification System")
    parser.add_argument("command", choices=[
        "build", "run", "compose", "stop", "health", "logs", "cleanup", "full-deploy"
    ], help="Command to execute")
    parser.add_argument("--port", type=int, default=5000, help="Port to run on (default: 5000)")
    parser.add_argument("--tag", default="vendor-qualification:latest", help="Docker image tag")
    parser.add_argument("--name", default="vendor-api", help="Container name")
    parser.add_argument("--profile", default="", help="Docker compose profile")
    parser.add_argument("--follow", action="store_true", help="Follow logs")
    
    args = parser.parse_args()
    
    print("VENDOR QUALIFICATION SYSTEM - DOCKER DEPLOYMENT")
    print("=" * 60)
    
    # Always check Docker and data file
    check_docker()
    check_data_file()
    
    if args.command == "build":
        build_image(args.tag)
        
    elif args.command == "run":
        build_image(args.tag)
        run_container(args.tag, args.port, args.name)
        time.sleep(5)
        check_health(f"http://localhost:{args.port}")
        
    elif args.command == "compose":
        run_with_compose(args.profile)
        time.sleep(10)
        check_health()
        
    elif args.command == "stop":
        stop_services()
        
    elif args.command == "health":
        check_health(f"http://localhost:{args.port}")
        
    elif args.command == "logs":
        show_logs(args.name, args.follow)
        
    elif args.command == "cleanup":
        cleanup()
        
    elif args.command == "full-deploy":
        print("Full deployment starting...")
        build_image(args.tag)
        run_container(args.tag, args.port, args.name)
        time.sleep(10)
        if check_health(f"http://localhost:{args.port}"):
            print("\nDEPLOYMENT SUCCESSFUL!")
            print(f"API: http://localhost:{args.port}")
            print(f"Docs: http://localhost:{args.port}/docs")
            print(f"Health: http://localhost:{args.port}/health")
        else:
            print("\nDeployment failed - API not responding")
            show_logs(args.name)

if __name__ == "__main__":
    main() 