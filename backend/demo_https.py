#!/usr/bin/env python3
"""
HTTPS Backend Demo Script

This script demonstrates how to use the HTTPS backend by:
1. Generating SSL certificates
2. Starting the HTTPS server
3. Running basic tests
4. Cleaning up

Usage:
    python demo_https.py [--port PORT] [--host HOST]

Options:
    --port PORT    Port to run the server on (default: 6741)
    --host HOST    Host to bind the server to (default: localhost)
"""

import os
import sys
import subprocess
import time
import signal
import argparse
from pathlib import Path


def run_command(cmd, check=True, capture_output=True):
    """Run a command and return the result"""
    try:
        result = subprocess.run(cmd, shell=True, check=check, 
                              capture_output=capture_output, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        return False, e.stdout, e.stderr


def generate_ssl_certificates(hostname="localhost", ssl_dir="./ssl"):
    """Generate SSL certificates for the demo"""
    print("🔐 Generating SSL certificates...")
    
    # Create SSL directory
    os.makedirs(ssl_dir, exist_ok=True)
    
    # Run certificate generation script
    script_path = Path(__file__).parent / "generate_ssl_cert.py"
    cmd = f"python {script_path} --hostname {hostname} --output-dir {ssl_dir}"
    
    success, stdout, stderr = run_command(cmd)
    
    if success:
        print("✅ SSL certificates generated successfully")
        return True
    else:
        print(f"❌ Failed to generate SSL certificates: {stderr}")
        return False


def setup_environment(host, port, ssl_dir):
    """Set up environment variables for HTTPS"""
    print("⚙️  Setting up environment...")
    
    env_vars = {
        "SSL_ENABLED": "true",
        "SSL_CERT_PATH": f"{ssl_dir}/server.crt",
        "SSL_KEY_PATH": f"{ssl_dir}/server.key",
        "HOST": host,
        "PORT": str(port),
        "DEBUG": "false"
    }
    
    for key, value in env_vars.items():
        os.environ[key] = value
        print(f"  {key}={value}")
    
    print("✅ Environment configured")


def start_backend_server():
    """Start the backend server in the background"""
    print("🚀 Starting HTTPS backend server...")
    
    # Start the server
    script_path = Path(__file__).parent / "backend.py"
    process = subprocess.Popen([sys.executable, str(script_path)], 
                             stdout=subprocess.PIPE, 
                             stderr=subprocess.PIPE)
    
    # Wait a moment for the server to start
    time.sleep(3)
    
    # Check if the process is still running
    if process.poll() is None:
        print("✅ Backend server started successfully")
        return process
    else:
        stdout, stderr = process.communicate()
        print(f"❌ Failed to start backend server: {stderr.decode()}")
        return None


def test_backend(host, port):
    """Test the backend server"""
    print("🧪 Testing backend server...")
    
    # Run the test script
    test_script = Path(__file__).parent / "test_https.py"
    url = f"https://{host}:{port}"
    cmd = f"python {test_script} --url {url}"
    
    success, stdout, stderr = run_command(cmd, capture_output=False)
    
    if success:
        print("✅ Backend tests passed")
        return True
    else:
        print(f"❌ Backend tests failed: {stderr}")
        return False


def cleanup(process, ssl_dir):
    """Clean up resources"""
    print("🧹 Cleaning up...")
    
    # Stop the server
    if process and process.poll() is None:
        print("  Stopping backend server...")
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
    
    # Remove SSL certificates (optional)
    if os.path.exists(ssl_dir):
        print(f"  Removing SSL directory: {ssl_dir}")
        import shutil
        shutil.rmtree(ssl_dir)
    
    print("✅ Cleanup completed")


def main():
    parser = argparse.ArgumentParser(description='Demo HTTPS backend functionality')
    parser.add_argument('--port', type=int, default=6741,
                       help='Port to run the server on (default: 6741)')
    parser.add_argument('--host', default='localhost',
                       help='Host to bind the server to (default: localhost)')
    
    args = parser.parse_args()
    
    ssl_dir = "./ssl"
    process = None
    
    try:
        print("🎯 HTTPS Backend Demo")
        print("=" * 50)
        
        # Step 1: Generate SSL certificates
        if not generate_ssl_certificates(args.host, ssl_dir):
            sys.exit(1)
        
        # Step 2: Set up environment
        setup_environment(args.host, args.port, ssl_dir)
        
        # Step 3: Start backend server
        process = start_backend_server()
        if not process:
            sys.exit(1)
        
        # Step 4: Test the backend
        if not test_backend(args.host, args.port):
            print("⚠️  Some tests failed, but server is running")
        
        # Step 5: Show server info
        print("\n" + "=" * 50)
        print("🎉 HTTPS Backend Demo Complete!")
        print("=" * 50)
        print(f"Server URL: https://{args.host}:{args.port}")
        print(f"Health Check: https://{args.host}:{args.port}/")
        print(f"API Docs: https://{args.host}:{args.port}/agents")
        print("\nPress Ctrl+C to stop the server and clean up...")
        
        # Keep the server running until interrupted
        try:
            while process.poll() is None:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Interrupted by user")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        sys.exit(1)
    
    finally:
        # Clean up
        cleanup(process, ssl_dir)


if __name__ == '__main__':
    main()
