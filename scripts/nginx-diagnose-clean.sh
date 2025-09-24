#!/usr/bin/env bash
set -euo pipefail

echo "== Paths and binaries =="
command -v nginx || true
nginx -V 2>&1 | sed -n '1,80p' || true
which nginx || true

echo -e "\n== Packages (Debian/Ubuntu) =="
dpkg -l | grep -E 'nginx|openresty' || true

echo -e "\n== Running processes =="
ps aux | grep -E '[n]ginx|[o]penresty' || true

echo -e "\n== Systemd units =="
systemctl list-unit-files | grep -E 'nginx|openresty' || true
systemctl status nginx || true

echo -e "\n== Active config roots =="
for f in /etc/nginx/nginx.conf /usr/local/nginx/conf/nginx.conf; do
  if [ -f "$f" ]; then echo "-- $f"; head -n 40 "$f"; fi
done

echo -e "\n== Sites enabled =="
ls -la /etc/nginx/sites-enabled || true

echo -e "\n== Conf.d =="
ls -la /etc/nginx/conf.d || true

echo -e "\n== Grep for 3-91-170-95.nip.io vhosts =="
grep -RIn "server_name\s*3-91-170-95.nip.io" /etc/nginx 2>/dev/null || true

cat <<'TIP'

Cleanup guidance:
1) Ensure only one Nginx installation:
   - If /usr/sbin/nginx and /usr/local/nginx both exist, remove the source-built one or disable its service.
2) Remove default vhost if not needed:
   sudo rm -f /etc/nginx/sites-enabled/default
3) Keep a single vhost file for 3-91-170-95.nip.io, e.g. /etc/nginx/sites-available/hedge.conf and symlink to sites-enabled.
4) Place your final config into that file and reload:
   sudo nginx -t && sudo systemctl reload nginx
TIP

