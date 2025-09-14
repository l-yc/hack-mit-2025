#!/usr/bin/env python3
"""
HTTPS Backend Startup Script

This script provides a production-ready way to start the backend with HTTPS support.
It includes proper SSL configuration, environment validation, and error handling.

Usage:
    python start_https.py [--config CONFIG_FILE] [--generate-certs]

Options:
    --config CONFIG_FILE    Path to environment configuration file (default: .env)
    --generate-certs        Generate SSL certificates if they don't exist
    --check-only           Only validate configuration without starting server
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path


def load_environment(config_file=".env"):
    """Load environment variables from configuration file"""
    if not os.path.exists(config_file):
        print(f"Configuration file not found: {config_file}")
        print(f"Copy env.https.example to {config_file} and configure it")
        return False
    
    try:
        with open(config_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
        print(f"Loaded configuration from: {config_file}")
        return True
    except Exception as e:
        print(f"Error loading configuration: {e}")
        return False


def check_ssl_certificates():
    """Check if SSL certificates exist and are valid"""
    cert_path = os.environ.get("SSL_CERT_PATH", "")
    key_path = os.environ.get("SSL_KEY_PATH", "")
    
    if not cert_path or not key_path:
        print("SSL certificate paths not configured")
        return False
    
    if not os.path.exists(cert_path):
        print(f"SSL certificate not found: {cert_path}")
        return False
    
    if not os.path.exists(key_path):
        print(f"SSL private key not found: {key_path}")
        return False
    
    # Check certificate validity
    try:
        import ssl
        context = ssl.create_default_context()
        with open(cert_path, 'rb') as f:
            cert = ssl.PEM_cert_to_DER_cert(f.read())
        print("SSL certificates are valid")
        return True
    except Exception as e:
        print(f"SSL certificate validation failed: {e}")
        return False


def generate_ssl_certificates():
    """Generate SSL certificates using the certificate generation script"""
    script_path = Path(__file__).parent / "generate_ssl_cert.py"
    
    if not script_path.exists():
        print(f"Certificate generation script not found: {script_path}")
        return False
    
    try:
        # Get SSL paths from environment
        ssl_dir = os.path.dirname(os.environ.get("SSL_CERT_PATH", "./ssl"))
        hostname = os.environ.get("SSL_HOSTNAME", "localhost")
        
        # Create SSL directory
        os.makedirs(ssl_dir, exist_ok=True)
        
        # Run certificate generation
        cmd = [
            sys.executable, str(script_path),
            "--hostname", hostname,
            "--output-dir", ssl_dir,
            "--days", "365"
        ]
        
        print(f"Generating SSL certificates...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("SSL certificates generated successfully")
            return True
        else:
            print(f"Error generating certificates: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"Error running certificate generation: {e}")
        return False


def validate_configuration():
    """Validate the complete configuration"""
    print("Validating configuration...")
    
    # Check required environment variables
    required_vars = ["SSL_ENABLED"]
    missing_vars = []
    
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"Missing required environment variables: {', '.join(missing_vars)}")
        return False
    
    # Check SSL configuration if enabled
    if os.environ.get("SSL_ENABLED", "false").lower() in ("true", "1", "yes"):
        if not check_ssl_certificates():
            print("SSL certificate validation failed")
            return False
    
    print("Configuration validation passed")
    return True


def start_server():
    """Start the Flask server"""
    try:
        # Import and run the backend
        from backend import app, SSL_ENABLED, SSL_CONTEXT
        
        host = os.environ.get("HOST", "0.0.0.0")
        port = int(os.environ.get("PORT", 6741))
        debug = os.environ.get("DEBUG", "false").lower() in ("true", "1", "yes")
        
        protocol = "HTTPS" if SSL_ENABLED and SSL_CONTEXT else "HTTP"
        
        print(f"\n{'='*50}")
        print(f"Starting Flask Backend Server")
        print(f"{'='*50}")
        print(f"Protocol: {protocol}")
        print(f"Host: {host}")
        print(f"Port: {port}")
        print(f"Debug: {debug}")
        
        if SSL_ENABLED and SSL_CONTEXT:
            print(f"SSL Certificate: {os.environ.get('SSL_CERT_PATH')}")
            print(f"SSL Private Key: {os.environ.get('SSL_KEY_PATH')}")
            print(f"Server URL: https://{host}:{port}")
        else:
            print(f"Server URL: http://{host}:{port}")
        
        print(f"{'='*50}\n")
        
        # Start the server
        if SSL_ENABLED and SSL_CONTEXT:
            app.run(host=host, port=port, debug=debug, ssl_context=SSL_CONTEXT)
        else:
            app.run(host=host, port=port, debug=debug)
            
    except KeyboardInterrupt:
        print("\nServer stopped by user")
    except Exception as e:
        print(f"Error starting server: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description='Start HTTPS backend server')
    parser.add_argument('--config', default='.env', 
                       help='Configuration file path (default: .env)')
    parser.add_argument('--generate-certs', action='store_true',
                       help='Generate SSL certificates if they don\'t exist')
    parser.add_argument('--check-only', action='store_true',
                       help='Only validate configuration without starting server')
    
    args = parser.parse_args()
    
    # Load environment configuration
    if not load_environment(args.config):
        sys.exit(1)
    
    # Generate certificates if requested
    if args.generate_certs:
        if not generate_ssl_certificates():
            sys.exit(1)
    
    # Validate configuration
    if not validate_configuration():
        print("\nConfiguration validation failed.")
        print("Please check your configuration and try again.")
        sys.exit(1)
    
    # Check if only validation was requested
    if args.check_only:
        print("Configuration validation completed successfully")
        return
    
    # Start the server
    start_server()


if __name__ == '__main__':
    main()
