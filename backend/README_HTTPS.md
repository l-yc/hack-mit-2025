# HTTPS Backend Setup

This guide explains how to set up and run the backend with HTTPS support.

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Generate SSL certificates:**
   ```bash
   python generate_ssl_cert.py
   ```

3. **Configure environment:**
   ```bash
   cp env.https.example .env
   # Edit .env with your configuration
   ```

4. **Start the HTTPS server:**
   ```bash
   python start_https.py
   ```

## Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `SSL_ENABLED` | Enable HTTPS support | `false` | Yes |
| `SSL_CERT_PATH` | Path to SSL certificate | `./ssl/server.crt` | If SSL enabled |
| `SSL_KEY_PATH` | Path to SSL private key | `./ssl/server.key` | If SSL enabled |
| `HOST` | Server host | `0.0.0.0` | No |
| `PORT` | Server port | `6741` | No |
| `DEBUG` | Enable debug mode | `false` | No |
| `CORS_ORIGINS` | Additional CORS origins | - | No |

### SSL Certificate Generation

The `generate_ssl_cert.py` script creates self-signed certificates for development:

```bash
# Basic usage
python generate_ssl_cert.py

# Custom hostname and output directory
python generate_ssl_cert.py --hostname mydomain.com --output-dir ./certs

# Custom validity period
python generate_ssl_cert.py --days 730
```

**Options:**
- `--hostname`: Certificate hostname (default: localhost)
- `--output-dir`: Output directory (default: ./ssl)
- `--days`: Certificate validity in days (default: 365)
- `--key-size`: RSA key size in bits (default: 2048)

### Production Certificates

For production, use certificates from a trusted Certificate Authority (CA):

1. **Let's Encrypt (Free):**
   ```bash
   # Install certbot
   sudo apt-get install certbot
   
   # Generate certificate
   sudo certbot certonly --standalone -d yourdomain.com
   
   # Update .env
   SSL_CERT_PATH=/etc/letsencrypt/live/yourdomain.com/fullchain.pem
   SSL_KEY_PATH=/etc/letsencrypt/live/yourdomain.com/privkey.pem
   ```

2. **Commercial CA:**
   - Purchase certificate from trusted CA
   - Update `SSL_CERT_PATH` and `SSL_KEY_PATH` in `.env`

## Running the Server

### Development Mode

```bash
# Start with auto-generated certificates
python start_https.py --generate-certs

# Start with existing configuration
python start_https.py

# Validate configuration only
python start_https.py --check-only
```

### Production Mode

```bash
# Set production environment
export DEBUG=false
export SSL_ENABLED=true
export SSL_CERT_PATH=/path/to/production/cert.pem
export SSL_KEY_PATH=/path/to/production/key.pem

# Start server
python start_https.py
```

### Using Gunicorn (Production)

For production deployments, use Gunicorn with SSL:

```bash
# Install gunicorn
pip install gunicorn

# Start with SSL
gunicorn --bind 0.0.0.0:6741 \
         --certfile=./ssl/server.crt \
         --keyfile=./ssl/server.key \
         --workers 4 \
         backend:app
```

## Security Features

The HTTPS implementation includes several security features:

### SSL/TLS Configuration
- **Minimum TLS Version:** TLS 1.2
- **Disabled Protocols:** SSLv2, SSLv3, TLS 1.0, TLS 1.1
- **Strong Ciphers:** ECDHE+AESGCM, ECDHE+CHACHA20, DHE+AESGCM, DHE+CHACHA20
- **Disabled Weak Ciphers:** NULL, MD5, DSS

### CORS Configuration
- **HTTPS Origins:** Supports both HTTP and HTTPS origins
- **Credential Support:** `supports_credentials=True`
- **Custom Headers:** Content-Type, Authorization, X-Requested-With
- **Methods:** GET, POST, PUT, DELETE, OPTIONS

### File Security
- **Private Key Permissions:** 600 (owner read/write only)
- **Certificate Validation:** Automatic validation on startup
- **Error Handling:** Graceful fallback to HTTP if SSL fails

## Troubleshooting

### Common Issues

1. **"SSL certificate file not found"**
   - Generate certificates: `python generate_ssl_cert.py`
   - Check file paths in `.env`

2. **"SSL context creation failed"**
   - Verify certificate and key files are valid
   - Check file permissions (key should be 600)

3. **"CORS error with HTTPS"**
   - Add your domain to `CORS_ORIGINS` in `.env`
   - Ensure frontend uses HTTPS URLs

4. **"Certificate validation failed"**
   - Regenerate certificates with correct hostname
   - For production, ensure CA-signed certificates

### Debug Mode

Enable debug mode for detailed logging:

```bash
export DEBUG=true
python start_https.py
```

### Testing HTTPS

Test your HTTPS setup:

```bash
# Test with curl
curl -k https://localhost:6741/

# Test with openssl
openssl s_client -connect localhost:6741 -servername localhost

# Test certificate
openssl x509 -in ssl/server.crt -text -noout
```

## API Endpoints

All existing API endpoints work with HTTPS:

- `GET /` - Health check
- `POST /upload` - Upload single photo
- `POST /upload/multiple` - Upload multiple photos
- `GET /photos` - List photos
- `GET /photos/<filename>` - Get photo
- `DELETE /photos/<filename>` - Delete photo
- `POST /images/cleanup` - Clean up image
- `POST /images/edit` - Edit image
- `POST /select` - Select top photos
- `GET /agents` - List AI agents

## Monitoring

### Health Check

The health check endpoint works with both HTTP and HTTPS:

```bash
# HTTP
curl http://localhost:6741/

# HTTPS
curl -k https://localhost:6741/
```

### Logs

Monitor server logs for SSL-related messages:

```bash
# Start with verbose logging
python start_https.py 2>&1 | tee backend.log
```

## Migration from HTTP

To migrate from HTTP to HTTPS:

1. **Update frontend URLs:**
   ```javascript
   // Change from
   const API_BASE = 'http://localhost:6741';
   
   // To
   const API_BASE = 'https://localhost:6741';
   ```

2. **Update CORS origins:**
   ```bash
   # Add HTTPS origins to .env
   CORS_ORIGINS=https://yourdomain.com,https://api.yourdomain.com
   ```

3. **Test all endpoints:**
   - Verify all API calls work with HTTPS
   - Check file uploads and downloads
   - Test image processing endpoints

## Security Best Practices

1. **Use Strong Certificates:**
   - 2048-bit RSA minimum (4096-bit recommended)
   - SHA-256 or better signature algorithm

2. **Regular Certificate Renewal:**
   - Set up automatic renewal for Let's Encrypt
   - Monitor certificate expiration dates

3. **Secure Private Keys:**
   - Store private keys securely
   - Use proper file permissions (600)
   - Consider hardware security modules for production

4. **Network Security:**
   - Use firewall rules to restrict access
   - Consider VPN for internal services
   - Monitor for unusual traffic patterns

5. **Regular Updates:**
   - Keep Python and dependencies updated
   - Monitor security advisories
   - Apply security patches promptly
