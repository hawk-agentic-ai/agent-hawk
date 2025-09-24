# 🔒 HTTPS Production Setup Guide

Complete guide to secure your Hedge Agent application with SSL certificates and eliminate the "Not Secure" browser warning.

## 🚨 Problem Solved

**Before**: `http://3.91.170.95:8004` shows ⚠️ "Not Secure" warning  
**After**: `https://your-domain.com` shows 🔒 "Secure" with valid SSL certificate

## 🎯 Quick Setup (Recommended)

### Option 1: One-Command Setup
```bash
chmod +x deploy_https_simple.sh && ./deploy_https_simple.sh
```

### Option 2: Manual Setup
```bash
chmod +x setup_https_production.sh && ./setup_https_production.sh
```

## 📋 Prerequisites

1. **Domain Name**: You need a domain pointing to your server IP `3.91.170.95`
2. **DNS Setup**: Ensure A records point to your server:
   ```
   your-domain.com     A    3.91.170.95
   www.your-domain.com A    3.91.170.95
   ```
3. **Server Access**: SSH access to your AWS instance

## 🔧 What Gets Fixed

### ✅ SSL Certificate
- **Let's Encrypt** free SSL certificate
- **Auto-renewal** configured
- **A+ security rating** with proper headers

### ✅ Nginx Reverse Proxy  
- **Frontend** served at `https://your-domain.com`
- **API** available at `https://your-domain.com/api`
- **Health Check** at `https://your-domain.com/health`

### ✅ Application Updates
- **Angular environments** updated to HTTPS URLs
- **Backend CORS** configured for HTTPS origins
- **Security headers** added for protection

### ✅ Automatic Deployment
- **Frontend build** and deployment
- **Backend startup** script with HTTPS support
- **Firewall** configuration

## 📁 Files Created/Modified

### New Files
- `setup_https_production.sh` - Comprehensive setup script
- `deploy_https_simple.sh` - Quick deployment script  
- `start_https_backend.sh` - HTTPS backend startup
- `HTTPS_SETUP_GUIDE.md` - This guide

### Modified Files
- `src/environments/environment.ts` - HTTPS URLs
- `src/environments/environment.prod.ts` - HTTPS URLs
- `unified_smart_backend.py` - HTTPS CORS support

## 🚀 Step-by-Step Manual Process

If you prefer manual setup:

### 1. Point Your Domain
```bash
# Check DNS propagation
nslookup your-domain.com
# Should return: 3.91.170.95
```

### 2. Run Setup Script
```bash
ssh -i agent_hawk.pem ubuntu@3.91.170.95
cd /path/to/hedge-agent
chmod +x setup_https_production.sh
./setup_https_production.sh
```

### 3. Start HTTPS Backend
```bash
./start_https_backend.sh
```

### 4. Verify Installation
```bash
# Test SSL certificate
curl https://your-domain.com/health

# Test API endpoint  
curl https://your-domain.com/api/system/status

# Check browser - should show 🔒 Secure
```

## 🔍 Troubleshooting

### Issue: Certificate Generation Fails
```bash
# Check domain DNS
dig your-domain.com +short
# Should return: 3.91.170.95

# Check firewall
sudo ufw status
# Should allow: 80, 443, SSH
```

### Issue: Backend Not Accessible
```bash
# Check backend is running
ps aux | grep python
sudo netstat -tlnp | grep :8004

# Check logs
sudo tail -f /var/log/nginx/error.log
```

### Issue: CORS Errors
Update the allowed origins:
```bash
export ALLOWED_ORIGINS='https://your-domain.com,https://www.your-domain.com'
./start_https_backend.sh
```

## 📊 Security Features

### 🛡️ Security Headers
- `Strict-Transport-Security` - Force HTTPS
- `X-Frame-Options` - Prevent clickjacking  
- `X-XSS-Protection` - XSS protection
- `X-Content-Type-Options` - MIME sniffing protection
- `Content-Security-Policy` - Content restrictions

### 🔐 SSL Configuration
- **TLS 1.2/1.3** only
- **Strong cipher suites**
- **HTTP/2** support
- **OCSP stapling**

## 🔄 Automatic Renewal

SSL certificates auto-renew via systemd timer:
```bash
# Check renewal status
sudo systemctl status certbot.timer

# Test renewal
sudo certbot renew --dry-run
```

## 📈 Performance Optimizations

### Nginx Optimizations
- **Gzip compression** enabled
- **Static file caching** configured  
- **HTTP/2** for faster loading
- **CDN-ready** headers

### Backend Optimizations
- **Reverse proxy** for better performance
- **Load balancing ready**
- **Connection pooling** supported

## 🎉 Expected Results

After successful setup:

### ✅ Browser Security
- 🔒 **Green padlock** in address bar
- ✅ **"Secure"** indicator  
- ❌ **No warning messages**

### ✅ URLs Updated
- `https://your-domain.com` - Frontend
- `https://your-domain.com/api/*` - Backend API
- `https://your-domain.com/health` - Health check

### ✅ Performance
- **A+ SSL rating** on SSL Labs
- **Fast loading** with HTTP/2
- **Mobile optimized** serving

## 🔗 Verification Commands

```bash
# Test complete HTTPS setup
curl -I https://your-domain.com
curl https://your-domain.com/health
curl https://your-domain.com/api/system/status

# Check SSL certificate
openssl s_client -connect your-domain.com:443 -servername your-domain.com

# Verify security rating
# Visit: https://www.ssllabs.com/ssltest/
```

## 🆘 Support

If you encounter issues:

1. **Check logs**: `sudo tail -f /var/log/nginx/error.log`
2. **Verify DNS**: `nslookup your-domain.com`
3. **Test connectivity**: `curl -I https://your-domain.com`
4. **Check certificates**: `sudo certbot certificates`

---

**🎯 Result**: Your application will be fully secure with HTTPS, eliminating all browser security warnings and providing enterprise-grade security for your hedge fund operations platform.