#!/bin/bash

# =============================================================================
# Quick Internal HTTPS Setup - No Domain Required
# =============================================================================

print_status() { echo -e "\033[0;34m[INFO]\033[0m $1"; }
print_success() { echo -e "\033[0;32m[SUCCESS]\033[0m $1"; }

print_status "🔒 Setting up HTTPS for Internal Testing (No Domain Required)"

# Make the internal setup script executable and run it
chmod +x setup_internal_https.sh
./setup_internal_https.sh

print_success "✅ Internal HTTPS setup complete!"
print_status "Access your app at: https://3.91.170.95 (accept browser warning)"