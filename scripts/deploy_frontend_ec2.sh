#!/usr/bin/env bash
set -euo pipefail

# Deploy Angular build output to EC2 static host
# Requirements: Node 18+, npm, rsync, ssh, (optional) aws cli

# Inputs via env vars:
#   EC2_HOST           (required)    e.g. 54.12.34.56 or myapp.example.com
#   SSH_KEY            (required)    path to SSH private key, e.g. ~/.ssh/my-key.pem
#   EC2_USER           (optional)    default: ubuntu
#   REMOTE_PATH        (optional)    default: /var/www/html
#   CF_DIST_ID         (optional)    if set, triggers CloudFront invalidation
#   NGINX_RELOAD       (optional)    if set to 1, tries: sudo systemctl reload nginx

EC2_USER=${EC2_USER:-ubuntu}
REMOTE_PATH=${REMOTE_PATH:-/var/www/html}

if [[ -z "${EC2_HOST:-}" || -z "${SSH_KEY:-}" ]]; then
  echo "EC2_HOST and SSH_KEY are required env vars" >&2
  exit 1
fi

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
APP_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)
cd "$APP_ROOT"

echo "[1/4] Installing deps and building (production)..."
npm ci
npm run build:prod

BUILD_DIR="dist/hedge-accounting-sfx"
if [[ ! -d "$BUILD_DIR" ]]; then
  echo "Build directory $BUILD_DIR not found. Build failed?" >&2
  exit 1
fi

echo "[2/4] Creating remote path if missing..."
ssh -i "$SSH_KEY" "$EC2_USER@$EC2_HOST" "mkdir -p '$REMOTE_PATH'"

echo "[3/4] Syncing files to EC2: $EC2_USER@$EC2_HOST:$REMOTE_PATH/"
rsync -avz --delete -e "ssh -i $SSH_KEY" "$BUILD_DIR/" "$EC2_USER@$EC2_HOST:$REMOTE_PATH/"

if [[ "${NGINX_RELOAD:-0}" == "1" ]]; then
  echo "[3b] Reloading NGINX on remote..."
  ssh -i "$SSH_KEY" "$EC2_USER@$EC2_HOST" "sudo systemctl reload nginx || true"
fi

if [[ -n "${CF_DIST_ID:-}" ]]; then
  echo "[4/4] Creating CloudFront invalidation for distribution $CF_DIST_ID ..."
  aws cloudfront create-invalidation --distribution-id "$CF_DIST_ID" --paths "/*"
else
  echo "[4/4] Skipping CloudFront invalidation (CF_DIST_ID not set)"
fi

echo "Done. Deployed build to $EC2_HOST:$REMOTE_PATH"

