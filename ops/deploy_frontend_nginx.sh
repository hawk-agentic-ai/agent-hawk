#!/usr/bin/env bash
set -euo pipefail

# Simple deploy script to publish Angular dist and enable nginx site
# Usage: sudo ./deploy_frontend_nginx.sh [domain] [web_root]

DOMAIN="${1:-3-91-170-95.nip.io}"
WEB_ROOT="${2:-/var/www/${DOMAIN}}"
SITE_NAME="hedge-agent"
CONF_SRC_DIR="$(cd "$(dirname "$0")"/.. && pwd)"
CONF_FILE_SRC="${CONF_SRC_DIR}/nginx_complete.conf"
CONF_DST="/etc/nginx/sites-available/${SITE_NAME}.conf"
ENABLED_LINK="/etc/nginx/sites-enabled/${SITE_NAME}.conf"

echo "==> Deploying frontend to ${WEB_ROOT} for domain ${DOMAIN}"

if [[ $EUID -ne 0 ]]; then
  echo "[ERROR] Please run as root: sudo $0"; exit 1;
fi

command -v nginx >/dev/null 2>&1 || { echo "[ERROR] nginx not installed"; exit 1; }

# 1) Publish Angular dist
if [[ ! -d "${CONF_SRC_DIR}/dist/hedge-accounting-sfx" ]]; then
  echo "[ERROR] Angular dist not found at ${CONF_SRC_DIR}/dist/hedge-accounting-sfx"
  echo "        Build it via: npm run build (Angular)"
  exit 1
fi

mkdir -p "${WEB_ROOT}"
rsync -ah --delete "${CONF_SRC_DIR}/dist/hedge-accounting-sfx/" "${WEB_ROOT}/"
echo "[OK] Synced Angular dist to ${WEB_ROOT}"

# 2) Install nginx site config
if [[ ! -f "${CONF_FILE_SRC}" ]]; then
  echo "[ERROR] Config not found: ${CONF_FILE_SRC}"; exit 1
fi

# Replace hardcoded domain occurrences if present
TMP_CONF="/tmp/${SITE_NAME}.conf"
sed "s/3-91-170-95.nip.io/${DOMAIN}/g" "${CONF_FILE_SRC}" > "${TMP_CONF}"
install -m 0644 "${TMP_CONF}" "${CONF_DST}"
ln -sf "${CONF_DST}" "${ENABLED_LINK}"

# Disable default site if present
if [[ -e /etc/nginx/sites-enabled/default ]]; then
  rm -f /etc/nginx/sites-enabled/default
  echo "[OK] Disabled default nginx site"
fi

# 3) Test and reload nginx
nginx -t
systemctl reload nginx || service nginx reload
echo "[OK] Nginx reloaded"

echo "==> Done. Frontend should be live at: https://${DOMAIN}/"

