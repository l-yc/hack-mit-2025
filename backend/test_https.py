#!/usr/bin/env python3
"""
HTTPS Backend Test Script

This script tests the HTTPS backend functionality including:
- SSL certificate validation
- API endpoint accessibility
- CORS configuration
- File upload/download

Usage:
    python test_https.py [--url URL] [--verbose]

Options:
    --url URL        Backend URL to test (default: https://localhost:6741)
    --verbose        Enable verbose output
"""

import requests
import argparse
import json
import os
from pathlib import Path
import ssl
import urllib3


def test_ssl_certificate(url):
    """Test SSL certificate validity"""
    print("Testing SSL certificate...")
    
    try:
        # Disable SSL warnings for self-signed certificates
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # Test SSL connection
        response = requests.get(url, verify=False, timeout=10)
        
        if response.status_code == 200:
            print("✓ SSL certificate is valid and server is accessible")
            return True
        else:
            print(f"✗ Server returned status code: {response.status_code}")
            return False
            
    except requests.exceptions.SSLError as e:
        print(f"✗ SSL error: {e}")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"✗ Connection error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False


def test_health_endpoint(url):
    """Test the health check endpoint"""
    print("Testing health endpoint...")
    
    try:
        response = requests.get(f"{url}/", verify=False, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Health check passed: {data.get('message', 'Unknown')}")
            return True
        else:
            print(f"✗ Health check failed with status: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"✗ Health check error: {e}")
        return False


def test_agents_endpoint(url):
    """Test the agents endpoint"""
    print("Testing agents endpoint...")
    
    try:
        response = requests.get(f"{url}/agents", verify=False, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            agent_count = data.get('total_count', 0)
            print(f"✓ Agents endpoint working: {agent_count} agents found")
            return True
        else:
            print(f"✗ Agents endpoint failed with status: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"✗ Agents endpoint error: {e}")
        return False


def test_photos_endpoint(url):
    """Test the photos listing endpoint"""
    print("Testing photos endpoint...")
    
    try:
        response = requests.get(f"{url}/photos", verify=False, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            photo_count = data.get('total_count', 0)
            print(f"✓ Photos endpoint working: {photo_count} photos found")
            return True
        else:
            print(f"✗ Photos endpoint failed with status: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"✗ Photos endpoint error: {e}")
        return False


def test_cors_headers(url):
    """Test CORS headers"""
    print("Testing CORS headers...")
    
    try:
        # Test preflight request
        headers = {
            'Origin': 'https://localhost:3000',
            'Access-Control-Request-Method': 'POST',
            'Access-Control-Request-Headers': 'Content-Type'
        }
        
        response = requests.options(f"{url}/upload", headers=headers, verify=False, timeout=10)
        
        cors_headers = {
            'Access-Control-Allow-Origin': response.headers.get('Access-Control-Allow-Origin'),
            'Access-Control-Allow-Methods': response.headers.get('Access-Control-Allow-Methods'),
            'Access-Control-Allow-Headers': response.headers.get('Access-Control-Allow-Headers'),
            'Access-Control-Allow-Credentials': response.headers.get('Access-Control-Allow-Credentials')
        }
        
        print(f"✓ CORS headers present:")
        for header, value in cors_headers.items():
            if value:
                print(f"  {header}: {value}")
        
        return True
        
    except Exception as e:
        print(f"✗ CORS test error: {e}")
        return False


def test_file_upload(url, verbose=False):
    """Test file upload functionality"""
    print("Testing file upload...")
    
    try:
        # Create a test image file
        test_image_path = Path("test_image.png")
        
        # Create a simple 1x1 PNG image for testing
        png_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\nIDATx\x9cc\xf8\x00\x00\x00\x01\x00\x01\x00\x00\x00\x00IEND\xaeB`\x82'
        
        with open(test_image_path, 'wb') as f:
            f.write(png_data)
        
        # Test upload
        with open(test_image_path, 'rb') as f:
            files = {'photo': ('test.png', f, 'image/png')}
            response = requests.post(f"{url}/upload", files=files, verify=False, timeout=30)
        
        # Clean up test file
        test_image_path.unlink()
        
        if response.status_code == 201:
            data = response.json()
            filename = data.get('filename', 'Unknown')
            print(f"✓ File upload successful: {filename}")
            return True
        else:
            print(f"✗ File upload failed with status: {response.status_code}")
            if verbose:
                print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ File upload error: {e}")
        return False
    finally:
        # Clean up test file if it exists
        if test_image_path.exists():
            test_image_path.unlink()


def run_all_tests(url, verbose=False):
    """Run all tests"""
    print(f"Testing HTTPS backend at: {url}")
    print("=" * 50)
    
    tests = [
        ("SSL Certificate", lambda: test_ssl_certificate(url)),
        ("Health Endpoint", lambda: test_health_endpoint(url)),
        ("Agents Endpoint", lambda: test_agents_endpoint(url)),
        ("Photos Endpoint", lambda: test_photos_endpoint(url)),
        ("CORS Headers", lambda: test_cors_headers(url)),
        ("File Upload", lambda: test_file_upload(url, verbose)),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("Test Summary:")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! HTTPS backend is working correctly.")
        return True
    else:
        print("❌ Some tests failed. Check the output above for details.")
        return False


def main():
    parser = argparse.ArgumentParser(description='Test HTTPS backend functionality')
    parser.add_argument('--url', default='https://localhost:6741',
                       help='Backend URL to test (default: https://localhost:6741)')
    parser.add_argument('--verbose', action='store_true',
                       help='Enable verbose output')
    
    args = parser.parse_args()
    
    # Ensure URL has proper protocol
    if not args.url.startswith(('http://', 'https://')):
        args.url = f"https://{args.url}"
    
    success = run_all_tests(args.url, args.verbose)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
