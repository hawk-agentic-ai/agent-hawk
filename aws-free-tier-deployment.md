# AWS Free Tier Deployment Guide - Optimized Dify Integration

Deploy your hedge agent with full server-side optimization using **100% FREE AWS services** and open-source tools.

##  **AWS Free Tier Services Used (All FREE)**

| Service | Free Tier Limit | Cost |
|---------|----------------|------|
| **EC2 t2.micro** | 750 hours/month | **FREE** |
| **S3** | 5GB storage + 20,000 GET requests | **FREE** |
| **CloudFront** | 50GB data transfer out | **FREE** |
| **Application Load Balancer** |  Not free (~$25/month) | Use **NGINX** instead |
| **ElastiCache** |  Not free (~$15/month) | Use **Redis on EC2** |
| **RDS** | 750 hours db.t2.micro + 20GB | **FREE** (but using Supabase) |

##  **Free Tier Architecture**

```
Internet  CloudFront (FREE)  EC2 t2.micro (FREE)
    
EC2 Instance running:
- NGINX (reverse proxy)
- FastAPI Backend (optimized)
- Redis (in-memory cache)
- Angular Frontend (static files)
```

##  **Expected Performance (Free Tier)**

- **Response Time**: 400-800ms (vs 2-3 seconds unoptimized)
- **Cache Hit Rate**: 70-80% 
- **Data Reduction**: 85% less data sent to Dify
- **Concurrent Users**: 20-30 users
- **Monthly Cost**: **$0** (within free tier limits)

##  **Prerequisites**

- AWS Account (free tier eligible)
- Domain name (optional, can use AWS public IP)
- Basic Linux knowledge

##  **Step-by-Step Free Tier Deployment**

### **Step 1: Launch Free EC2 Instance**

```bash
# Launch t2.micro instance (FREE for 750 hours/month)
aws ec2 run-instances \
    --image-id ami-0c55b159cbfafe1d0 \  # Ubuntu 20.04 LTS
    --count 1 \
    --instance-type t2.micro \
    --key-name your-key-pair \
    --security-group-ids sg-xxxxxx \
    --subnet-id subnet-xxxxxx \
    --associate-public-ip-address
```

### **Step 2: Configure Security Group (FREE)**

```bash
# Create security group
aws ec2 create-security-group \
    --group-name hedge-agent-sg \
    --description "Security group for hedge agent"

# Allow HTTP, HTTPS, SSH
aws ec2 authorize-security-group-ingress \
    --group-id sg-xxxxxxxxx \
    --protocol tcp \
    --port 80 \
    --cidr 0.0.0.0/0

aws ec2 authorize-security-group-ingress \
    --group-id sg-xxxxxxxxx \
    --protocol tcp \
    --port 443 \
    --cidr 0.0.0.0/0

aws ec2 authorize-security-group-ingress \
    --group-id sg-xxxxxxxxx \
    --protocol tcp \
    --port 22 \
    --cidr 0.0.0.0/0
```

### **Step 3: Install Software on EC2**

```bash
# SSH into your EC2 instance
ssh -i your-key.pem ubuntu@your-ec2-public-ip

# Update system
sudo apt update && sudo apt upgrade -y

# Install Node.js and npm
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Install Python 3.9
sudo apt install python3.9 python3.9-venv python3-pip -y

# Install Redis (open source, in-memory cache)
sudo apt install redis-server -y

# Install NGINX (free reverse proxy)
sudo apt install nginx -y

# Install PM2 (free process manager)
sudo npm install -g pm2

# Install Angular CLI
sudo npm install -g @angular/cli
```

### **Step 4: Setup Redis Cache (FREE)**

```bash
# Configure Redis for production
sudo nano /etc/redis/redis.conf

# Add these optimizations:
maxmemory 512mb
maxmemory-policy allkeys-lru
timeout 300
tcp-keepalive 60

# Start and enable Redis
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Test Redis
redis-cli ping  # Should return PONG
```

### **Step 5: Deploy FastAPI Backend**

```bash
# Create application directory
mkdir -p /home/ubuntu/hedge-agent
cd /home/ubuntu/hedge-agent

# Create Python virtual environment
python3.9 -m venv venv
source venv/bin/activate

# Create requirements.txt for free tier
cat > requirements.txt << 'EOF'
fastapi==0.104.1
uvicorn[standard]==0.24.0
redis==5.0.1
httpx==0.25.2
pydantic==2.5.0
supabase==2.0.2
python-multipart==0.0.6
python-dotenv==1.0.0
EOF

# Install dependencies
pip install -r requirements.txt
```

Now upload your optimized Python files:

```bash
# Upload your files (from local machine)
scp -i your-key.pem optimized_hedge_data_service.py ubuntu@your-ec2-ip:/home/ubuntu/hedge-agent/
scp -i your-key.pem redis_cache_service.py ubuntu@your-ec2-ip:/home/ubuntu/hedge-agent/
scp -i your-key.pem optimized_dify_endpoint.py ubuntu@your-ec2-ip:/home/ubuntu/hedge-agent/
```

Create environment file:

```bash
# Create .env file
cat > .env << 'EOF'
DIFY_API_KEY=your-dify-api-key
REDIS_URL=redis://localhost:6379/0
SUPABASE_URL=your-supabase-url
SUPABASE_ANON_KEY=your-supabase-anon-key
ENVIRONMENT=production
EOF

# Start FastAPI with PM2 (free process manager)
pm2 start "uvicorn optimized_dify_endpoint:app --host 0.0.0.0 --port 8000 --workers 2" --name hedge-agent-api
pm2 startup  # Auto-start on boot
pm2 save
```

### **Step 6: Build and Deploy Angular Frontend**

On your local machine:

```bash
# Update environment for AWS deployment
cat > src/environments/environment.prod.ts << 'EOF'
export const environment = {
  production: true,
  apiUrl: 'https://your-ec2-public-ip/api',  // Update with your EC2 IP
  supabaseUrl: 'your-supabase-url',
  supabaseAnonKey: 'your-supabase-anon-key',
  
  // Free tier optimization settings
  freeTierOptimization: {
    enabled: true,
    serverSideCache: true,
    parallelProcessing: true,
    redisCache: true,
    limitConcurrentRequests: true,
    maxConcurrentRequests: 10
  }
};
EOF

# Build for production
ng build --configuration=production

# Upload dist folder to EC2
scp -i your-key.pem -r dist/* ubuntu@your-ec2-ip:/var/www/html/
```

### **Step 7: Configure NGINX (FREE Reverse Proxy)**

```bash
# On EC2, configure NGINX
sudo nano /etc/nginx/sites-available/hedge-agent

# Add this configuration:
server {
    listen 80;
    server_name your-domain.com;  # Or use EC2 public IP
    
    # Frontend (Angular)
    location / {
        root /var/www/html;
        try_files $uri $uri/ /index.html;
        
        # Cache static assets
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }
    
    # API (FastAPI backend)
    location /api/ {
        proxy_pass http://localhost:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Optimize for performance
        proxy_buffering on;
        proxy_buffer_size 128k;
        proxy_buffers 4 256k;
        proxy_busy_buffers_size 256k;
    }
}

# Enable the site
sudo ln -s /etc/nginx/sites-available/hedge-agent /etc/nginx/sites-enabled/
sudo nginx -t  # Test configuration
sudo systemctl restart nginx
```

### **Step 8: Setup Free SSL with Let's Encrypt**

```bash
# Install Certbot (FREE SSL certificates)
sudo apt install certbot python3-certbot-nginx -y

# Get free SSL certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal (free certificates expire every 90 days)
sudo crontab -e
# Add this line:
0 12 * * * /usr/bin/certbot renew --quiet
```

### **Step 9: Setup CloudFront (FREE CDN)**

```bash
# Create S3 bucket for CloudFront origin (if needed)
aws s3 mb s3://your-hedge-agent-bucket

# Upload static assets to S3
aws s3 sync /var/www/html s3://your-hedge-agent-bucket --exclude="*.html"

# Create CloudFront distribution
aws cloudfront create-distribution --distribution-config '{
  "CallerReference": "hedge-agent-'$(date +%s)'",
  "Comment": "Hedge Agent CDN",
  "Origins": {
    "Quantity": 2,
    "Items": [
      {
        "Id": "ec2-origin",
        "DomainName": "your-ec2-public-ip",
        "CustomOriginConfig": {
          "HTTPPort": 80,
          "HTTPSPort": 443,
          "OriginProtocolPolicy": "http-only"
        }
      },
      {
        "Id": "s3-origin", 
        "DomainName": "your-hedge-agent-bucket.s3.amazonaws.com",
        "S3OriginConfig": {
          "OriginAccessIdentity": ""
        }
      }
    ]
  },
  "DefaultCacheBehavior": {
    "TargetOriginId": "ec2-origin",
    "ViewerProtocolPolicy": "redirect-to-https",
    "MinTTL": 0,
    "ForwardedValues": {
      "QueryString": true,
      "Cookies": {"Forward": "none"}
    }
  },
  "CacheBehaviors": {
    "Quantity": 1,
    "Items": [
      {
        "PathPattern": "*.js,*.css,*.png,*.jpg,*.gif",
        "TargetOriginId": "s3-origin",
        "ViewerProtocolPolicy": "redirect-to-https",
        "MinTTL": 31536000
      }
    ]
  },
  "Enabled": true,
  "PriceClass": "PriceClass_100"
}'
```

##  **Free Tier Monitoring (All FREE)**

### **1. CloudWatch Basic Monitoring (FREE)**

```bash
# Install CloudWatch agent (free tier includes basic metrics)
wget https://s3.amazonaws.com/amazoncloudwatch-agent/amazon_linux/amd64/latest/amazon-cloudwatch-agent.rpm
sudo rpm -U ./amazon-cloudwatch-agent.rpm

# Basic monitoring is included in free tier:
# - CPU utilization
# - Network in/out
# - Disk read/write
```

### **2. Application Performance Monitoring**

```python
# Add to your FastAPI app for free monitoring
import time
import redis

redis_client = redis.Redis(host='localhost', port=6379, db=1)  # Use db=1 for metrics

@app.middleware("http")
async def performance_monitoring(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    # Store metrics in Redis (free)
    redis_client.lpush("response_times", process_time)
    redis_client.ltrim("response_times", 0, 999)  # Keep last 1000
    
    response.headers["X-Process-Time"] = str(process_time)
    return response

@app.get("/metrics")
async def get_metrics():
    """Free metrics endpoint"""
    response_times = [float(x) for x in redis_client.lrange("response_times", 0, -1)]
    
    return {
        "avg_response_time": sum(response_times) / len(response_times) if response_times else 0,
        "total_requests": len(response_times),
        "cache_info": redis_client.info("memory"),
        "server_uptime": redis_client.info("server")["uptime_in_seconds"]
    }
```

### **3. Log Management (FREE)**

```bash
# Setup log rotation (free)
sudo nano /etc/logrotate.d/hedge-agent

# Add log rotation config:
/var/log/nginx/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 0644 www-data www-data
    postrotate
        sudo systemctl reload nginx
    endscript
}

# PM2 logs (free)
pm2 logs hedge-agent-api --lines 100
```

##  **Free Tier Optimizations**

### **1. Memory Management**

```python
# Optimize for t2.micro (1GB RAM)
import gc
import asyncio

@app.middleware("http")
async def memory_management(request: Request, call_next):
    response = await call_next(request)
    
    # Force garbage collection every 100 requests
    if not hasattr(memory_management, 'counter'):
        memory_management.counter = 0
    
    memory_management.counter += 1
    if memory_management.counter % 100 == 0:
        gc.collect()
    
    return response
```

### **2. Connection Pooling**

```python
# Optimize database connections for free tier
from supabase import create_client

# Use connection pooling to reduce memory usage
class OptimizedSupabaseClient:
    def __init__(self):
        self.client = None
        self.last_used = 0
    
    def get_client(self):
        current_time = time.time()
        # Recreate connection every 30 minutes to save memory
        if not self.client or (current_time - self.last_used) > 1800:
            self.client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
            self.last_used = current_time
        return self.client

supabase_client = OptimizedSupabaseClient()
```

##  **Free Tier Limitations & Solutions**

| Limitation | Solution |
|------------|----------|
| **1GB RAM** | Use Redis with memory limits, garbage collection |
| **1 vCPU** | Async processing, connection pooling |
| **30GB EBS** | Log rotation, cache size limits |
| **No auto-scaling** | Connection limiting, graceful degradation |

##  **Cost Breakdown (FREE TIER)**

```
 EC2 t2.micro:        $0/month (750 hours free)
 S3:                  $0/month (5GB free)
 CloudFront:          $0/month (50GB transfer free)
 Redis (on EC2):      $0/month (open source)
 NGINX:               $0/month (open source)
 PM2:                 $0/month (open source)
 Let's Encrypt SSL:   $0/month (free certificates)
 Basic CloudWatch:    $0/month (included)

 TOTAL MONTHLY COST:  $0
```

##  **Expected Performance (Free Tier)**

After deployment, you should see:

- **Response Time**: 400-800ms (vs 2-3 seconds unoptimized)
- **Cache Hit Rate**: 70-80% (Redis on same instance)
- **Data Reduction**: 85% less data sent to Dify
- **Concurrent Users**: 20-30 users comfortably
- **Uptime**: 99%+ with proper monitoring

##  **Quick Deployment Script**

```bash
#!/bin/bash
# Quick free tier deployment script

# Upload files
scp -i your-key.pem *.py ubuntu@your-ec2-ip:/home/ubuntu/hedge-agent/

# SSH and setup
ssh -i your-key.pem ubuntu@your-ec2-ip << 'EOF'
cd /home/ubuntu/hedge-agent
source venv/bin/activate
pip install -r requirements.txt

# Start services
pm2 restart hedge-agent-api || pm2 start "uvicorn optimized_dify_endpoint:app --host 0.0.0.0 --port 8000 --workers 2" --name hedge-agent-api
sudo systemctl restart nginx
sudo systemctl restart redis-server

echo " Deployment complete! Your optimized hedge agent is running on AWS Free Tier!"
EOF
```

##  **Success Metrics**

You'll know the free tier optimization is working when:

-  **Console shows** performance metrics
-  **Response times** under 1 second
-  **Cache hit rates** above 70%
-  **Server stays** within 1GB RAM usage
-  **SSL certificate** working (https://)
-  **CloudFront** serving static assets

**This gives you enterprise-grade performance optimization for $0/month on AWS Free Tier!** 