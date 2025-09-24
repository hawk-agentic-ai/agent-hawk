#!/usr/bin/env bash
set -euo pipefail

URL=${URL:-http://localhost:8004/hawk-agent/process-prompt}

echo "Testing system status..."
curl -s http://localhost:8004/system/status | sed -e 's/{\|}//g' | head -n 20 || true

echo
echo "Posting streaming request to $URL ..."
curl -N -H "Content-Type: application/json" \
  -d '{
    "user_prompt": "Check HKD hedge capacity",
    "template_category": "hedge_accounting",
    "currency": "HKD",
    "amount": 50000,
    "transaction_date": "2025-09-04",
    "use_cache": true
  }' \
  "$URL"

echo
echo "Done."

