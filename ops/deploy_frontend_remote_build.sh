#!/usr/bin/env bash
set -euo pipefail

# Build Angular on the server and deploy to nginx web root
# Usage: ./ops/deploy_frontend_remote_build.sh

EC2_HOST="3.91.170.95"
EC2_USER="ubuntu"
KEY_FILE="agent_hawk.pem"
REMOTE_DIR="/home/${EC2_USER}/hedge-frontend-src"
WEB_ROOT="/var/www/3-91-170-95.nip.io"

echo "==> Preparing remote build on ${EC2_HOST}"

if [[ ! -f "$KEY_FILE" ]]; then
  echo "[ERROR] SSH key not found: ${KEY_FILE}"; exit 1
fi

echo "==> Creating source folder on server"
ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no "${EC2_USER}@${EC2_HOST}" \
  "mkdir -p ${REMOTE_DIR} && rm -rf ${REMOTE_DIR}/* && mkdir -p ${WEB_ROOT}"

echo "==> Uploading project sources (no node_modules)"
rsync -ah --delete \
  -e "ssh -i ${KEY_FILE} -o StrictHostKeyChecking=no" \
  --exclude node_modules --exclude dist --exclude .angular --exclude .git \
  angular.json package.json package-lock.json tsconfig*.json \
  src public proxy.conf.json \
  "${EC2_USER}@${EC2_HOST}:${REMOTE_DIR}/"

echo "==> Ensuring Node.js 18 on server"
ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no "${EC2_USER}@${EC2_HOST}" bash -lc '
  set -e
  if ! command -v node >/dev/null 2>&1; then
    curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
    sudo apt-get install -y nodejs
  fi
  node -v && npm -v
'

echo "==> Installing deps and building on server"
ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no "${EC2_USER}@${EC2_HOST}" bash -lc "
  set -e
  cd ${REMOTE_DIR}
  npm ci
  npm run build:prod
"

echo "==> Publishing build to nginx root"
ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no "${EC2_USER}@${EC2_HOST}" bash -lc "
  set -e
  sudo rsync -ah --delete ${REMOTE_DIR}/dist/hedge-accounting-sfx/ ${WEB_ROOT}/
  sudo chown -R www-data:www-data ${WEB_ROOT}
  sudo find ${WEB_ROOT} -type d -exec chmod 755 {} \;
  sudo find ${WEB_ROOT} -type f -exec chmod 644 {} \;
  sudo nginx -t && sudo systemctl reload nginx
"

echo "==> Frontend deployed to https://${EC2_HOST}/"

