# Environment Configuration Guide

## 🔐 Security First

**CRITICAL**: Never commit the `.env` file to version control. It contains sensitive credentials.

## Quick Setup

### 1. Create Your Environment File

```bash
# Copy the example template
cp .env.example .env
```

### 2. Fill in Your Credentials

Edit the `.env` file with your actual values:

#### Supabase Configuration

1. Go to [Supabase Dashboard](https://app.supabase.com)
2. Select your project
3. Navigate to **Settings > API**
4. Copy the following:
   - **Project URL** → `SUPABASE_URL`
   - **service_role key** → `SUPABASE_SERVICE_ROLE_KEY`
   - **anon key** (optional) → `SUPABASE_ANON_KEY`

```env
SUPABASE_URL=https://ladviaautlfvpxuadqrb.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGc...your-actual-key
```

#### Dify AI Configuration

1. Go to [Dify Console](https://cloud.dify.ai)
2. Select your application
3. Navigate to **API Access**
4. Copy the API key for each agent type

```env
DIFY_API_KEY=app-your-key-here
DIFY_API_KEY_ALLOCATION_AGENT=app-allocation-key
DIFY_API_KEY_BOOKING_AGENT=app-booking-key
```

#### Network Configuration

```env
# For local development
PUBLIC_BASE_URL=http://localhost:8009

# For production deployment
PUBLIC_BASE_URL=https://your-domain.com
```

### 3. Verify Configuration

```bash
# Test Supabase connection
python test_supabase_connection.py

# Test MCP server
python mcp_server_production.py
```

## Environment Variables Reference

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `SUPABASE_URL` | Supabase project URL | `https://xxx.supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | Service role key | `eyJhbGc...` |
| `DIFY_API_KEY` | Default Dify API key | `app-xxx` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CORS_ORIGINS` | Allowed CORS origins | See `.env.example` |
| `PUBLIC_BASE_URL` | Public server URL | `""` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379` |
| `WRITE_TIMEOUT_SECONDS` | Write operation timeout | `30` |
| `QUERY_TIMEOUT_SECONDS` | Query timeout | `10` |

## Security Best Practices

### ✅ DO:
- Keep `.env` file in `.gitignore`
- Use different credentials for dev/staging/production
- Rotate keys regularly
- Use service role keys only on backend
- Store production secrets in a vault (AWS Secrets Manager, Azure Key Vault)

### ❌ DON'T:
- Commit `.env` to version control
- Share `.env` files via email/chat
- Use production credentials in development
- Hardcode credentials in source code
- Log credential values

## Production Deployment

### Option 1: Environment Variables (Recommended)

Set environment variables directly in your deployment platform:

```bash
# AWS/EC2
export SUPABASE_URL="https://xxx.supabase.co"
export SUPABASE_SERVICE_ROLE_KEY="eyJhbGc..."

# Docker
docker run -e SUPABASE_URL="..." -e SUPABASE_SERVICE_ROLE_KEY="..." ...

# Kubernetes
kubectl create secret generic hedge-agent-secrets \
  --from-literal=SUPABASE_URL="..." \
  --from-literal=SUPABASE_SERVICE_ROLE_KEY="..."
```

### Option 2: Secrets Manager

#### AWS Secrets Manager

```python
import boto3
import json

def load_secrets():
    client = boto3.client('secretsmanager', region_name='us-west-2')
    response = client.get_secret_value(SecretId='hedge-agent/production')
    secrets = json.loads(response['SecretString'])

    os.environ['SUPABASE_URL'] = secrets['SUPABASE_URL']
    os.environ['SUPABASE_SERVICE_ROLE_KEY'] = secrets['SUPABASE_SERVICE_ROLE_KEY']
```

#### Azure Key Vault

```python
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

def load_secrets():
    credential = DefaultAzureCredential()
    client = SecretClient(vault_url="https://your-vault.vault.azure.net/", credential=credential)

    os.environ['SUPABASE_URL'] = client.get_secret("SUPABASE-URL").value
    os.environ['SUPABASE_SERVICE_ROLE_KEY'] = client.get_secret("SUPABASE-KEY").value
```

## Troubleshooting

### "SUPABASE_URL not found"

```bash
# Check if .env file exists
ls -la .env

# Verify .env is being loaded
python -c "from dotenv import load_dotenv; load_dotenv(); import os; print(os.getenv('SUPABASE_URL'))"
```

### "Invalid Supabase URL format"

Ensure your URL:
- Starts with `https://`
- Contains `.supabase.co`
- Has no trailing slash

### "Connection refused"

Check:
1. Supabase project is active
2. Network allows HTTPS connections
3. Service role key is correct
4. No firewall blocking requests

## Migration from Hardcoded Credentials

If you previously had hardcoded credentials:

1. **Rotate ALL credentials immediately**
   - Generate new Supabase service role key
   - Generate new Dify API keys

2. **Update `.env` with new credentials**

3. **Verify old credentials are revoked**

4. **Update production deployments**

5. **Verify git history is clean** (credentials never committed)

## Support

For issues:
1. Check [Troubleshooting](#troubleshooting) section
2. Review logs: `pm2 logs mcp_server`
3. Test connection: `python test_supabase_connection.py`
4. Open issue on project repository

---

**Last Updated**: 2025-09-30
**Version**: 1.0.0