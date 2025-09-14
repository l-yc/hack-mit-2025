#!/usr/bin/env bash

set -euo pipefail

# AWS Bare-Metal Deploy Script (EC2 + Nginx + Certbot + Gunicorn)
# - Provisions EC2 (optional) and deploys this repository
# - Installs Python venv, Gunicorn, Nginx, and Let's Encrypt TLS
# - Sets up systemd service and reverse proxy
#
# Requirements on local machine:
#   - aws CLI (configured)
#   - ssh, scp, tar
#
# Examples:
#   ./deploy_aws_baremetal.sh --domain api.example.com --email you@example.com
#   ./deploy_aws_baremetal.sh --domain api.example.com --email you@example.com --region us-east-1 --instance-type t3.small
#   ./deploy_aws_baremetal.sh --host 54.12.34.56 --domain api.example.com --email you@example.com --skip-provision
#
# Notes:
#   - If you pass --skip-provision you must provide --host and a reachable SSH key.
#   - The script uploads this repo, excluding heavy/dev folders (node_modules, .git, uploads, etc.).

########################################
# Defaults
########################################
REGION="us-east-1"
INSTANCE_TYPE="t3.small"
KEY_NAME="hackmit-key-$(date +%s)"
KEY_PATH=""
PROFILE=""
SECURITY_GROUP_NAME="hackmit-backend-sg"
DOMAIN=""
EMAIL=""
HOST=""
UBUNTU_USER="ubuntu"
SKIP_PROVISION="false"
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"  # repo root
APP_DIR_REMOTE="/opt/hack-mit-2025"
SERVICE_NAME="hackmit-backend"

########################################
# Helpers
########################################
log() { echo -e "[deploy] $*"; }
err() { echo -e "[deploy][error] $*" >&2; }

need_bin() {
  if ! command -v "$1" >/dev/null 2>&1; then err "Missing required binary: $1"; exit 1; fi
}

usage() {
  cat <<EOF
Usage: $0 [--domain DOMAIN] [--email EMAIL] [--region REGION] [--instance-type TYPE]
          [--key-name NAME] [--key-path PATH] [--security-group NAME]
          [--profile AWS_PROFILE] [--host IP_OR_DNS] [--skip-provision]

Options:
  --domain DOMAIN           Domain name for HTTPS (recommended)
  --email EMAIL             Email for Let's Encrypt (recommended)
  --region REGION           AWS region (default: ${REGION})
  --instance-type TYPE      EC2 instance type (default: ${INSTANCE_TYPE})
  --key-name NAME           AWS EC2 key pair name (default: generated)
  --key-path PATH           Local .pem path to use/save (default: ./<key-name>.pem)
  --security-group NAME     Security group name (default: ${SECURITY_GROUP_NAME})
  --profile AWS_PROFILE     AWS CLI profile name (optional)
  --host IP_OR_DNS          Use an existing host instead of provisioning
  --skip-provision          Skip EC2 provisioning (requires --host)
  --repo-dir PATH           Local repo directory to upload (default: repo root)

Examples:
  $0 --domain api.example.com --email you@example.com
  $0 --skip-provision --host 54.12.34.56 --domain api.example.com --email you@example.com
EOF
}

########################################
# Parse args
########################################
while [[ $# -gt 0 ]]; do
  case "$1" in
    --domain) DOMAIN="$2"; shift 2;;
    --email) EMAIL="$2"; shift 2;;
    --region) REGION="$2"; shift 2;;
    --instance-type) INSTANCE_TYPE="$2"; shift 2;;
    --key-name) KEY_NAME="$2"; shift 2;;
    --key-path) KEY_PATH="$2"; shift 2;;
    --security-group) SECURITY_GROUP_NAME="$2"; shift 2;;
    --profile) PROFILE="$2"; shift 2;;
    --host) HOST="$2"; shift 2;;
    --skip-provision) SKIP_PROVISION="true"; shift 1;;
    --repo-dir) REPO_DIR="$2"; shift 2;;
    -h|--help) usage; exit 0;;
    *) err "Unknown arg: $1"; usage; exit 1;;
  esac
done

AWS=(aws)
if [[ -n "$PROFILE" ]]; then AWS+=("--profile" "$PROFILE"); fi
AWS+=("--region" "$REGION")

########################################
# Pre-flight checks
########################################
need_bin aws
need_bin ssh
need_bin scp
need_bin tar

if [[ "$SKIP_PROVISION" == "true" && -z "$HOST" ]]; then
  err "--skip-provision requires --host"
  exit 1
fi

if [[ -z "$KEY_PATH" ]]; then KEY_PATH="./${KEY_NAME}.pem"; fi

########################################
# Provision EC2 (unless skipped)
########################################
if [[ "$SKIP_PROVISION" != "true" ]]; then
  log "Provisioning EC2 in $REGION ..."

  # Create key pair if local pem doesn't exist
  if [[ ! -f "$KEY_PATH" ]]; then
    log "Creating key pair $KEY_NAME and saving to $KEY_PATH"
    "${AWS[@]}" ec2 create-key-pair \
      --key-name "$KEY_NAME" \
      --query 'KeyMaterial' --output text > "$KEY_PATH"
    chmod 400 "$KEY_PATH"
  else
    log "Using existing key file: $KEY_PATH"
  fi

  # Get default VPC
  VPC_ID=$("${AWS[@]}" ec2 describe-vpcs --filters Name=isDefault,Values=true \
    --query 'Vpcs[0].VpcId' --output text)

  # Ensure security group exists
  if ! "${AWS[@]}" ec2 describe-security-groups --group-names "$SECURITY_GROUP_NAME" >/dev/null 2>&1; then
    log "Creating security group: $SECURITY_GROUP_NAME"
    SG_ID=$("${AWS[@]}" ec2 create-security-group \
      --group-name "$SECURITY_GROUP_NAME" \
      --description "HackMIT backend SG" \
      --vpc-id "$VPC_ID" \
      --query 'GroupId' --output text)

    MY_IP=$(curl -s https://checkip.amazonaws.com || echo "0.0.0.0")
    # Allow SSH from my IP only
    "${AWS[@]}" ec2 authorize-security-group-ingress --group-id "$SG_ID" --protocol tcp --port 22 --cidr "${MY_IP}/32" || true
    # HTTP/HTTPS from anywhere
    "${AWS[@]}" ec2 authorize-security-group-ingress --group-id "$SG_ID" --protocol tcp --port 80 --cidr 0.0.0.0/0 || true
    "${AWS[@]}" ec2 authorize-security-group-ingress --group-id "$SG_ID" --protocol tcp --port 443 --cidr 0.0.0.0/0 || true
  else
    SG_ID=$("${AWS[@]}" ec2 describe-security-groups --group-names "$SECURITY_GROUP_NAME" --query 'SecurityGroups[0].GroupId' --output text)
    log "Using security group: $SECURITY_GROUP_NAME ($SG_ID)"
  fi

  # Find default subnet
  SUBNET_ID=$("${AWS[@]}" ec2 describe-subnets --filters Name=vpc-id,Values=$VPC_ID \
    --query 'Subnets[0].SubnetId' --output text)

  # Latest Ubuntu 22.04 AMI via SSM Parameter
  AMI_ID=$("${AWS[@]}" ssm get-parameters \
    --names "/aws/service/canonical/ubuntu/server/22.04/stable/current/amd64/hvm/ebs-gp3/ami-id" \
    --query 'Parameters[0].Value' --output text)

  log "Launching instance: type=$INSTANCE_TYPE ami=$AMI_ID"
  INSTANCE_ID=$("${AWS[@]}" ec2 run-instances \
    --image-id "$AMI_ID" \
    --count 1 \
    --instance-type "$INSTANCE_TYPE" \
    --key-name "$KEY_NAME" \
    --security-group-ids "$SG_ID" \
    --subnet-id "$SUBNET_ID" \
    --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=hackmit-backend}]' \
    --query 'Instances[0].InstanceId' --output text)

  log "Waiting for instance to be running... ($INSTANCE_ID)"
  "${AWS[@]}" ec2 wait instance-running --instance-ids "$INSTANCE_ID"

  # Allocate and associate Elastic IP
  ALLOC_ID=$("${AWS[@]}" ec2 allocate-address --domain vpc --query 'AllocationId' --output text)
  "${AWS[@]}" ec2 associate-address --instance-id "$INSTANCE_ID" --allocation-id "$ALLOC_ID" >/dev/null

  HOST=$("${AWS[@]}" ec2 describe-instances --instance-ids "$INSTANCE_ID" \
    --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)
  log "Instance public IP: $HOST"
else
  log "Skipping provisioning. Using host: $HOST"
fi

SSH=(ssh -o StrictHostKeyChecking=no -i "$KEY_PATH" "$UBUNTU_USER@$HOST")
SCP=(scp -o StrictHostKeyChecking=no -i "$KEY_PATH")

########################################
# Remote: base setup
########################################
log "Installing base packages on remote..."
"${SSH[@]}" "sudo apt-get update && sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \ 
  python3-pip python3-venv git nginx certbot python3-certbot-nginx && sudo apt-get upgrade -y"

########################################
# Upload code (exclude heavy/dev content)
########################################
log "Uploading repository to $APP_DIR_REMOTE (excluding heavy folders)..."
TMP_TGZ="/tmp/hackmit_repo.tgz"
EXCLUDES=(
  "--exclude=.git" "--exclude=.github" "--exclude=.DS_Store" \
  "--exclude=**/__pycache__" "--exclude=**/.pytest_cache" \
  "--exclude=frontend/node_modules" "--exclude=node_modules" \
  "--exclude=uploads" "--exclude=**/*.log"
)

tar czf "$TMP_TGZ" -C "$REPO_DIR" "${EXCLUDES[@]}" .
"${SCP[@]}" "$TMP_TGZ" "$UBUNTU_USER@$HOST:/tmp/"
rm -f "$TMP_TGZ"

"${SSH[@]}" "sudo mkdir -p $APP_DIR_REMOTE && sudo chown -R $UBUNTU_USER:$UBUNTU_USER $APP_DIR_REMOTE && \
  tar xzf /tmp/$(basename $TMP_TGZ) -C $APP_DIR_REMOTE && rm -f /tmp/$(basename $TMP_TGZ) && \
  mkdir -p $APP_DIR_REMOTE/uploads $APP_DIR_REMOTE/uploads/cleaned $APP_DIR_REMOTE/uploads/edited"

########################################
# Python venv, deps
########################################
log "Creating venv and installing requirements..."
"${SSH[@]}" "cd $APP_DIR_REMOTE && python3 -m venv .venv && source .venv/bin/activate && \
  pip install --upgrade pip && pip install -r requirements.txt"

########################################
# Env file
########################################
log "Configuring environment file..."
CLAUDE_ENV=""
if [[ -n "${CLAUDE_API_KEY:-}" ]]; then CLAUDE_ENV="CLAUDE_API_KEY=${CLAUDE_API_KEY}"; fi
GEMINI_ENV=""
if [[ -n "${GEMINI_API_KEY:-}" ]]; then GEMINI_ENV="GEMINI_API_KEY=${GEMINI_API_KEY}"; fi

"${SSH[@]}" "cd $APP_DIR_REMOTE && cp backend/env.https.example backend/.env && \
  sed -i 's/^SSL_ENABLED=.*/SSL_ENABLED=false/' backend/.env && \
  sed -i 's#^CORS_ORIGINS=.*#CORS_ORIGINS=https://$DOMAIN,http://$DOMAIN#' backend/.env && \
  (test -n '$CLAUDE_ENV' && grep -q '^CLAUDE_API_KEY=' backend/.env && sed -i 's#^CLAUDE_API_KEY=.*#$CLAUDE_ENV#' backend/.env || true) && \
  (test -n '$GEMINI_ENV' && grep -q '^GEMINI_API_KEY=' backend/.env && sed -i 's#^GEMINI_API_KEY=.*#$GEMINI_ENV#' backend/.env || true)"

########################################
# systemd service (Gunicorn)
########################################
log "Creating systemd service..."
SERVICE_UNIT="/tmp/${SERVICE_NAME}.service"
cat > "$SERVICE_UNIT" <<EOF
[Unit]
Description=HackMIT Backend (Gunicorn)
After=network.target

[Service]
User=${UBUNTU_USER}
WorkingDirectory=${APP_DIR_REMOTE}
Environment=PATH=${APP_DIR_REMOTE}/.venv/bin
EnvironmentFile=${APP_DIR_REMOTE}/backend/.env
ExecStart=${APP_DIR_REMOTE}/.venv/bin/gunicorn -w 4 -k gthread -t 120 -b 127.0.0.1:6741 backend.backend:app
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

"${SCP[@]}" "$SERVICE_UNIT" "$UBUNTU_USER@$HOST:/tmp/"
rm -f "$SERVICE_UNIT"
"${SSH[@]}" "sudo mv /tmp/${SERVICE_NAME}.service /etc/systemd/system/${SERVICE_NAME}.service && \
  sudo systemctl daemon-reload && sudo systemctl enable ${SERVICE_NAME} && \
  sudo systemctl restart ${SERVICE_NAME} && sudo systemctl status ${SERVICE_NAME} --no-pager | cat"

########################################
# Nginx reverse proxy
########################################
SERVER_NAME=${DOMAIN:-_}
log "Configuring Nginx for server_name: ${SERVER_NAME} ..."
NGINX_SITE="/tmp/${SERVICE_NAME}.nginx"
cat > "$NGINX_SITE" <<EOF
server {
    listen 80;
    server_name ${SERVER_NAME} www.${SERVER_NAME};

    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    location / {
        return 301 https://\$host\$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name ${SERVER_NAME} www.${SERVER_NAME};

    # Temporary self-signed (replaced by certbot)
    ssl_certificate /etc/ssl/certs/ssl-cert-snakeoil.pem;
    ssl_certificate_key /etc/ssl/private/ssl-cert-snakeoil.key;

    client_max_body_size 20M;

    location / {
        proxy_pass http://127.0.0.1:6741;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        proxy_http_version 1.1;
        proxy_read_timeout 300s;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
    }
}
EOF

"${SCP[@]}" "$NGINX_SITE" "$UBUNTU_USER@$HOST:/tmp/"
rm -f "$NGINX_SITE"
"${SSH[@]}" "sudo mv /tmp/${SERVICE_NAME}.nginx /etc/nginx/sites-available/${SERVICE_NAME} && \
  sudo ln -sf /etc/nginx/sites-available/${SERVICE_NAME} /etc/nginx/sites-enabled/${SERVICE_NAME} && \
  sudo rm -f /etc/nginx/sites-enabled/default && sudo nginx -t && sudo systemctl reload nginx"

########################################
# TLS via Certbot (if domain + email provided and domain is not an IP)
########################################
if [[ -n "$DOMAIN" && -n "$EMAIL" && ! "$DOMAIN" =~ ^[0-9.]+$ ]]; then
  log "Requesting Let's Encrypt cert for ${DOMAIN} ..."
  set +e
  "${SSH[@]}" "sudo certbot --nginx -n --agree-tos -m '$EMAIL' -d '$DOMAIN' -d 'www.$DOMAIN' --redirect"
  CERTBOT_RC=$?
  set -e
  if [[ $CERTBOT_RC -ne 0 ]]; then
    err "Certbot failed. Keeping temporary TLS (self-signed). You can retry certbot later on the server."
  fi
else
  log "Skipping Certbot (missing --domain/--email or domain is an IP)."
fi

########################################
# Final output
########################################
URL="https://${DOMAIN:-$HOST}"
log "Deployment complete!"
log "URL: $URL"
log "SSH: ssh -i $KEY_PATH $UBUNTU_USER@$HOST"
log "App logs: sudo journalctl -u ${SERVICE_NAME} -f"
log "Nginx logs: sudo tail -f /var/log/nginx/{access,error}.log"
