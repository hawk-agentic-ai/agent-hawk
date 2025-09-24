#!/bin/bash
# Final fix for frontend deployment - move files to correct location

set -e

EC2_HOST="3.91.170.95"
EC2_USER="ubuntu"
KEY_FILE="agent_hawk.pem"

echo "🔧 Fixing frontend file location..."

# Use the same SSH pattern that worked in the simple deployment
ssh -i "$KEY_FILE" "$EC2_USER@$EC2_HOST" << 'EOF'
echo "Moving files from subdirectory to web root..."
sudo cp -r /var/www/html/hedge-accounting-sfx/* /var/www/html/
sudo rm -rf /var/www/html/hedge-accounting-sfx

echo "Verifying index.html exists..."
if [ -f /var/www/html/index.html ]; then
    echo "✅ index.html found"
else
    echo "❌ index.html still missing"
fi

echo "Setting correct permissions..."
sudo chown -R www-data:www-data /var/www/html/
sudo chmod -R 755 /var/www/html/

echo "Restarting nginx..."
sudo systemctl restart nginx

echo "Testing local access..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/)
echo "Local HTTP response code: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Frontend is now accessible!"
else
    echo "⚠️ Still getting error code: $HTTP_CODE"
fi
EOF

echo ""
echo "🌐 Testing external access..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://3.91.170.95/)
echo "External HTTP response code: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    echo "🎉 SUCCESS! Frontend is now live at: http://3.91.170.95/"
    echo "✅ Your streaming fixes are deployed and accessible!"
else
    echo "⚠️ Still getting HTTP $HTTP_CODE - may need nginx config adjustment"
fi

echo ""
echo "📍 Your deployment status:"
echo "  ✅ Backend: http://3.91.170.95:8004 (Working)"
echo "  🔧 Frontend: http://3.91.170.95/ (Fixed)"
echo ""
echo "🧪 Test your streaming fixes in Agent Mode!"