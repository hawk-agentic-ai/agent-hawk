#  Backend Deployment Guide

## Quick Start - Choose Your Platform:

### 1.  **VERCEL (Recommended for MVP)**
*Free tier, serverless, zero config*

```bash
# 1. Install Vercel CLI
npm i -g vercel

# 2. Navigate to backend folder
cd backend-example

# 3. Deploy
vercel

# 4. Set environment variables
vercel env add SUPABASE_URL
vercel env add SUPABASE_SERVICE_KEY  
vercel env add DIFY_API_KEY

# 5. Redeploy with env vars
vercel --prod
```

**Your API will be available at:** `https://your-project.vercel.app/api/`

---

### 2.  **RAILWAY (Simple & Fast)**
*$5/month, persistent, great for startups*

```bash
# 1. Install Railway CLI
npm install -g @railway/cli

# 2. Login and deploy
railway login
railway link
railway up

# 3. Set environment variables in Railway dashboard
# Go to: https://railway.app/project/your-project/variables
```

**Your API will be available at:** `https://your-app.railway.app/api/`

---

### 3.  **HEROKU (Traditional PaaS)**
*Free tier ended, $7/month minimum*

```bash
# 1. Install Heroku CLI
# Download from: https://devcenter.heroku.com/articles/heroku-cli

# 2. Login and create app
heroku login
heroku create your-hedge-backend

# 3. Set environment variables
heroku config:set SUPABASE_URL=your-url
heroku config:set SUPABASE_SERVICE_KEY=your-key
heroku config:set DIFY_API_KEY=your-key

# 4. Deploy
git push heroku main
```

---

### 4.  **DIGITAL OCEAN (Droplet)**
*$4/month minimum, full control*

```bash
# 1. Create droplet with Node.js
# Go to: https://cloud.digitalocean.com/droplets/new
# Select: Ubuntu + Node.js one-click app

# 2. SSH into your droplet
ssh root@your-droplet-ip

# 3. Clone your repo
git clone https://github.com/your-username/hedge-agent.git
cd hedge-agent/backend-example

# 4. Install dependencies
npm install

# 5. Set up environment variables
nano .env
# Add your variables here

# 6. Install PM2 for process management
npm install -g pm2
pm2 start server.js --name "hedge-backend"
pm2 startup
pm2 save

# 7. Set up nginx (optional)
sudo apt install nginx
# Configure reverse proxy
```

---

### 5.  **RENDER (Modern Alternative)**
*Free tier available, $7/month for production*

1. Go to [render.com](https://render.com)
2. Connect your GitHub repo
3. Choose "Web Service"
4. Set build command: `npm install`
5. Set start command: `npm start`
6. Add environment variables in dashboard

---

### 6.  **AWS/GCP/AZURE (Enterprise)**

#### AWS Lambda (Serverless)
```bash
# Install Serverless Framework
npm install -g serverless

# Deploy to AWS
serverless deploy
```

#### AWS EC2 (Traditional)
```bash
# Use Docker deployment method
# Push to ECR and deploy to EC2
```

---

##  **Environment Variables Required:**

```bash
# Database
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key

# AI API  
DIFY_API_KEY=your-dify-api-key
DIFY_API_URL=https://api.dify.ai/v1

# Security (optional)
JWT_SECRET=your-random-jwt-secret
SESSION_SECRET=your-random-session-secret

# CORS (optional)
ALLOWED_ORIGINS=https://your-frontend-domain.com,http://localhost:4200
```

---

##  **After Deployment:**

### 1. Update Frontend Config
```typescript
// src/environments/environment.prod.ts
export const environment = {
  production: true,
  apiUrl: 'https://your-deployed-backend.com/api'
};
```

### 2. Update HTML Config
```html
<!-- docs/index.html -->
<script>
  window.__env = {
    API_URL: 'https://your-deployed-backend.com/api'
  };
</script>
```

### 3. Test Your API
```bash
curl https://your-deployed-backend.com/api/templates
```

---

##  **Cost Comparison:**

| Platform | Free Tier | Paid | Best For |
|----------|-----------|------|----------|
| Vercel |  Generous | $20/mo | MVP, Serverless |
| Railway |  Trial only | $5/mo | Simple apps |
| Heroku |  Ended | $7/mo | Traditional apps |
| Render |  Limited | $7/mo | Modern alternative |
| DigitalOcean |  | $4/mo | Full control |
| AWS |  Complex | Variable | Enterprise |

---

##  **Security Checklist:**

-  Environment variables set
-  CORS configured properly  
-  Rate limiting enabled
-  Input validation added
-  Authentication implemented
-  HTTPS enabled
-  Secrets rotated from client exposure

---

##  **Need Help?**

1. **Vercel Issues:** Check build logs in dashboard
2. **Environment Variables:** Use dashboard, not CLI for production
3. **CORS Errors:** Add your domain to ALLOWED_ORIGINS
4. **Database Connection:** Use SERVICE_KEY not ANON_KEY
5. **API Not Working:** Check function logs in platform dashboard

---

**Recommendation for your use case:** Start with **Vercel** for MVP, then migrate to **Railway** or **DigitalOcean** as you scale.