#!/bin/bash
echo "🔒 HAWK Agent - SSL Setup Script"
echo "================================"

SERVER_IP="3.238.163.106"
SSH_KEY="agent_tmp.pem"
DOMAIN="3-238-163-106.nip.io"

# Check if key exists
if [ ! -f "$SSH_KEY" ]; then
    echo "⚠️  SSH Key not found in current directory!"
    echo "   Please place $SSH_KEY in this folder or update the script."
    exit 1
fi

echo "📋 connecting to $SERVER_IP..."

ssh -i $SSH_KEY -o StrictHostKeyChecking=no ubuntu@$SERVER_IP << 'EOF'
    echo "  → Updating package lists..."
    sudo apt-get update -q

    echo "  → Installing Certbot..."
    sudo apt-get install -y certbot python3-certbot-nginx

    echo "  → Obtaining SSL Certificate for 3-238-163-106.nip.io..."
    # --nginx: Use Nginx plugin
    # --non-interactive: No prompts
    # --agree-tos: Agree to terms
    # --register-unsafely-without-email: Skip email requirement
    # --redirect: Force HTTPS redirect
    sudo certbot --nginx -d 3-238-163-106.nip.io --non-interactive --agree-tos --register-unsafely-without-email --redirect

    echo "  → Reloading Nginx..."
    sudo systemctl reload nginx

    echo "  ✅ SSL Setup Complete!"
EOF

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 HTTPS Enabled Successfully!"
    echo "👉 Test it here: https://$DOMAIN"
else
    echo "❌ SSL Setup Failed."
fi
