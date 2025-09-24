#!/bin/bash

# =============================================================================
# Simple HTTPS Deployment Script
# Quick setup for production HTTPS deployment
# =============================================================================

set -e

print_status() { echo -e "\033[0;34m[INFO]\033[0m $1"; }
print_success() { echo -e "\033[0;32m[SUCCESS]\033[0m $1"; }
print_error() { echo -e "\033[0;31m[ERROR]\033[0m $1"; }

print_status "🔒 Simple HTTPS Deployment for Hedge Agent"

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   print_error "This script should not be run as root for security reasons"
   exit 1
fi

# Get domain name
read -p "Enter your domain name: " DOMAIN_NAME
if [ -z "$DOMAIN_NAME" ]; then
    print_error "Domain name required"
    exit 1
fi

print_status "Domain: $DOMAIN_NAME"

# Update environment files with user's domain
print_status "Updating environment files..."

sed -i "s|https://your-domain.com|https://$DOMAIN_NAME|g" src/environments/environment.ts
sed -i "s|https://your-domain.com|https://$DOMAIN_NAME|g" src/environments/environment.prod.ts

print_success "Environment files updated"

# Make the main setup script executable and run it
chmod +x setup_https_production.sh

print_status "Running comprehensive HTTPS setup..."
./setup_https_production.sh

print_success "🎉 HTTPS deployment complete!"
print_status "Your secure application is ready at: https://$DOMAIN_NAME"