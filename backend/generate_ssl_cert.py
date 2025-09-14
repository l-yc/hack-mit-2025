#!/usr/bin/env python3
"""
SSL Certificate Generation Script for HTTPS Backend

This script generates self-signed SSL certificates for development and testing.
For production, use certificates from a trusted Certificate Authority (CA).

Usage:
    python generate_ssl_cert.py [--hostname HOSTNAME] [--output-dir DIR]

Options:
    --hostname HOSTNAME    The hostname for the certificate (default: localhost)
    --output-dir DIR       Directory to save certificates (default: ./ssl)
    --days DAYS           Certificate validity in days (default: 365)
    --key-size SIZE       RSA key size in bits (default: 2048)
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path
from datetime import datetime, timedelta


def run_command(cmd, check=True):
    """Run a command and return the result"""
    try:
        result = subprocess.run(cmd, shell=True, check=check, 
                              capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        return False, e.stdout, e.stderr


def check_openssl():
    """Check if OpenSSL is available"""
    success, _, _ = run_command("openssl version", check=False)
    return success


def generate_private_key(key_path, key_size=2048):
    """Generate a private key"""
    cmd = f"openssl genrsa -out {key_path} {key_size}"
    success, stdout, stderr = run_command(cmd)
    if not success:
        print(f"Error generating private key: {stderr}")
        return False
    print(f"Generated private key: {key_path}")
    return True


def generate_certificate_signing_request(csr_path, key_path, hostname):
    """Generate a certificate signing request"""
    # Create a temporary config file for the CSR
    config_content = f"""[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no

[req_distinguished_name]
C = US
ST = State
L = City
O = Organization
OU = Organizational Unit
CN = {hostname}

[v3_req]
keyUsage = keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = {hostname}
DNS.2 = localhost
IP.1 = 127.0.0.1
IP.2 = ::1
"""
    
    config_path = csr_path.with_suffix('.conf')
    with open(config_path, 'w') as f:
        f.write(config_content)
    
    cmd = f"openssl req -new -key {key_path} -out {csr_path} -config {config_path}"
    success, stdout, stderr = run_command(cmd)
    
    # Clean up config file
    config_path.unlink()
    
    if not success:
        print(f"Error generating CSR: {stderr}")
        return False
    print(f"Generated CSR: {csr_path}")
    return True


def generate_self_signed_certificate(cert_path, key_path, hostname, days=365):
    """Generate a self-signed certificate"""
    # Create a temporary config file for the certificate
    config_content = f"""[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no

[req_distinguished_name]
C = US
ST = State
L = City
O = Organization
OU = Organizational Unit
CN = {hostname}

[v3_req]
keyUsage = keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = {hostname}
DNS.2 = localhost
IP.1 = 127.0.0.1
IP.2 = ::1
"""
    
    config_path = cert_path.with_suffix('.conf')
    with open(config_path, 'w') as f:
        f.write(config_content)
    
    cmd = f"openssl req -x509 -new -nodes -key {key_path} -sha256 -days {days} -out {cert_path} -config {config_path}"
    success, stdout, stderr = run_command(cmd)
    
    # Clean up config file
    config_path.unlink()
    
    if not success:
        print(f"Error generating certificate: {stderr}")
        return False
    print(f"Generated certificate: {cert_path}")
    return True


def set_permissions(key_path):
    """Set appropriate permissions for the private key"""
    try:
        os.chmod(key_path, 0o600)
        print(f"Set secure permissions for private key: {key_path}")
        return True
    except Exception as e:
        print(f"Warning: Could not set permissions for {key_path}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Generate SSL certificates for HTTPS backend')
    parser.add_argument('--hostname', default='localhost', 
                       help='Hostname for the certificate (default: localhost)')
    parser.add_argument('--output-dir', default='./ssl', 
                       help='Directory to save certificates (default: ./ssl)')
    parser.add_argument('--days', type=int, default=365, 
                       help='Certificate validity in days (default: 365)')
    parser.add_argument('--key-size', type=int, default=2048, 
                       help='RSA key size in bits (default: 2048)')
    
    args = parser.parse_args()
    
    # Check if OpenSSL is available
    if not check_openssl():
        print("Error: OpenSSL is not installed or not in PATH")
        print("Please install OpenSSL and try again")
        sys.exit(1)
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    # Define file paths
    key_path = output_dir / 'server.key'
    cert_path = output_dir / 'server.crt'
    
    print(f"Generating SSL certificates for hostname: {args.hostname}")
    print(f"Output directory: {output_dir.absolute()}")
    print(f"Certificate validity: {args.days} days")
    print(f"Key size: {args.key_size} bits")
    print()
    
    # Generate private key
    if not generate_private_key(key_path, args.key_size):
        sys.exit(1)
    
    # Generate self-signed certificate
    if not generate_self_signed_certificate(cert_path, key_path, args.hostname, args.days):
        sys.exit(1)
    
    # Set secure permissions for private key
    set_permissions(key_path)
    
    print()
    print("SSL certificates generated successfully!")
    print(f"Private key: {key_path.absolute()}")
    print(f"Certificate: {cert_path.absolute()}")
    print()
    print("To use these certificates with your Flask backend:")
    print(f"  SSL_CERT_PATH={cert_path.absolute()}")
    print(f"  SSL_KEY_PATH={key_path.absolute()}")
    print()
    print("Note: These are self-signed certificates for development only.")
    print("For production, use certificates from a trusted CA.")


if __name__ == '__main__':
    main()
