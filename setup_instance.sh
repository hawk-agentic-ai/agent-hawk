#!/bin/bash
set -e

echo "🔧 Setting up instance..."

# Update system
sudo apt update && sudo apt upgrade -y

# Install Node.js 18
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Install Python 3.10 and venv
sudo apt install python3.10 python3.10-venv python3-pip -y

# Install Redis (FREE open source cache)
sudo apt install redis-server -y

# Install NGINX (FREE reverse proxy)
sudo apt install nginx -y

# Install PM2 (FREE process manager)
sudo npm install -g pm2

# Configure Redis for production
sudo sed -i 's/# maxmemory <bytes>/maxmemory 400mb/' /etc/redis/redis.conf
sudo sed -i 's/# maxmemory-policy noeviction/maxmemory-policy allkeys-lru/' /etc/redis/redis.conf

# Start services
sudo systemctl start redis-server
sudo systemctl enable redis-server
sudo systemctl start nginx
sudo systemctl enable nginx

# Test Redis
redis-cli ping

echo "✅ Instance setup complete!"
