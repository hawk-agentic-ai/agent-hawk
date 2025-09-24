#  Secure Backend API for Hedge Agent

##  Quick Deploy

### Option 1: Vercel (Recommended)
```bash
npm i -g vercel
cd backend-example
vercel
```

### Option 2: Railway
```bash
npm i -g @railway/cli
railway login
railway up
```

### Option 3: Local Development
```bash
npm install
cp .env.example .env
# Edit .env with your credentials
npm run dev
```

##  Project Structure

```
backend-example/
 api/                 # Vercel serverless functions
    dify/
       chat.js     # Dify chat endpoint
       stream.js   # Dify streaming endpoint
    templates/
        index.js    # Supabase templates CRUD
 server.js           # Express server (Railway/Heroku)
 package.json        # Dependencies
 vercel.json         # Vercel configuration
 Dockerfile          # Docker configuration
 .env.example        # Environment template
```

##  Environment Variables

```bash
# Required
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key-not-anon
DIFY_API_KEY=your-dify-api-key

# Optional
JWT_SECRET=your-jwt-secret
ALLOWED_ORIGINS=https://your-domain.com
```

##  Security Features

-  API keys hidden from client
-  Supabase service key (not anon key)  
-  CORS protection
-  Input validation
-  Rate limiting ready
-  Authentication middleware ready

##  API Endpoints

```bash
# Dify AI
POST /api/dify/chat        # Send query to Dify
POST /api/dify/stream      # Stream Dify response

# Templates  
GET  /api/templates        # Get all templates
POST /api/templates        # Create template
PUT  /api/templates/:id    # Update template
DELETE /api/templates/:id  # Delete template

# Other secure endpoints
GET  /api/currencies       # Get currencies
GET  /api/entities         # Get entities
```

##  Test Your Deployment

```bash
# Test templates endpoint
curl https://your-api-url.com/api/templates

# Test Dify endpoint
curl -X POST https://your-api-url.com/api/dify/chat \
  -H "Content-Type: application/json" \
  -d '{"query":"Hello world","msgUid":"test"}'
```

##  Migration Steps

1. **Deploy backend** using any method above
2. **Update frontend** environment config:
   ```typescript
   // src/environments/environment.prod.ts  
   apiUrl: 'https://your-deployed-backend.com/api'
   ```
3. **Replace direct API calls** with `BackendApiService`
4. **Update HTML config**:
   ```html
   window.__env = { API_URL: 'https://your-backend.com/api' };
   ```
5. **Test everything** works
6. **Rotate old credentials** (very important!)

##  Troubleshooting

**CORS Issues:**
- Add your domain to `ALLOWED_ORIGINS`
- Check Vercel headers in `vercel.json`

**Database Connection:**
- Use `SUPABASE_SERVICE_KEY` not `SUPABASE_ANON_KEY`
- Check Supabase project URL is correct

**Dify API Issues:**
- Verify `DIFY_API_KEY` is correct
- Check Dify API endpoint URL

**Build Errors:**
- Check logs in your platform dashboard
- Ensure all dependencies in `package.json`