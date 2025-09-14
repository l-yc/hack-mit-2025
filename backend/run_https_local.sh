#!/usr/bin/env bash

set -euo pipefail

# Run Flask backend over HTTPS using self-signed certs
# Usage:
#   ./run_https_local.sh [--hostname HOST] [--port PORT]
# Defaults: HOST=localhost, PORT=6741

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HOSTNAME="localhost"
PORT="6741"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --hostname) HOSTNAME="$2"; shift 2;;
    --port) PORT="$2"; shift 2;;
    -h|--help)
      echo "Usage: $0 [--hostname HOST] [--port PORT]"; exit 0;;
    *) echo "Unknown arg: $1"; exit 1;;
  esac
done

SSL_DIR="$SCRIPT_DIR/ssl"
CERT="$SSL_DIR/server.crt"
KEY="$SSL_DIR/server.key"

mkdir -p "$SSL_DIR"

# Generate self-signed certs if missing
if [[ ! -f "$CERT" || ! -f "$KEY" ]]; then
  echo "[run-https] Generating self-signed certificates for $HOSTNAME ..."
  python3 "$SCRIPT_DIR/generate_ssl_cert.py" --hostname "$HOSTNAME" --output-dir "$SSL_DIR"
fi

export SSL_ENABLED=true
export SSL_CERT_PATH="$CERT"
export SSL_KEY_PATH="$KEY"
export HOST="0.0.0.0"
export PORT="$PORT"
export DEBUG=false

echo "[run-https] Starting Flask on https://$HOSTNAME:$PORT"
exec python3 "$SCRIPT_DIR/backend.py"
