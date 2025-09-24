#!/bin/bash
echo "🚀 Deploying Angular Frontend to Production Server..."

# Build the application first
echo "📦 Building Angular application..."
npm run build:prod

# Check if build was successful
if [ ! -d "dist/hedge-accounting-sfx" ]; then
    echo "❌ Build failed - dist directory not found"
    exit 1
fi

echo "✅ Build successful"

# Create deployment package
echo "📋 Creating deployment package..."
cd dist/hedge-accounting-sfx
tar -czf ../../frontend-deployment.tar.gz *
cd ../..

echo "✅ Deployment package created: frontend-deployment.tar.gz"

# Upload and deploy to server
echo "📤 Uploading to server..."
scp -i agent_hawk.pem -o StrictHostKeyChecking=no frontend-deployment.tar.gz ubuntu@13.222.100.183:/tmp/

echo "🔧 Deploying on server..."
ssh -i agent_hawk.pem ubuntu@13.222.100.183 -o StrictHostKeyChecking=no << 'EOF'
    # Extract files to HTTPS web directory
    cd /tmp
    sudo rm -rf /var/www/13-222-100-183.nip.io/*
    sudo tar -xzf frontend-deployment.tar.gz -C /var/www/13-222-100-183.nip.io/
    
    # Set correct permissions
    sudo chown -R www-data:www-data /var/www/13-222-100-183.nip.io/
    sudo chmod -R 644 /var/www/13-222-100-183.nip.io/*
    sudo chmod 755 /var/www/13-222-100-183.nip.io/
    # Fix directory permissions for assets to be accessible
    sudo find /var/www/13-222-100-183.nip.io/ -type d -exec chmod 755 {} \;
    
    # Test nginx configuration
    sudo nginx -t
    
    # Reload nginx
    sudo systemctl reload nginx
    
    echo "✅ Frontend deployed successfully"
    
    # Clean up
    rm /tmp/frontend-deployment.tar.gz
EOF

echo "🌐 Testing deployment..."
curl -I https://13-222-100-183.nip.io

echo "🎉 Deployment complete!"
echo "🔗 Access your application at: https://13-222-100-183.nip.io"