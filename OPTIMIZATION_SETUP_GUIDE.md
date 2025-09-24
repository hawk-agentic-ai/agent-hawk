# Dify Optimization Setup Guide

This guide walks you through setting up the optimized Dify integration with parallel data fetching, Redis caching, and smart context preparation.

##  Performance Improvements Expected

- **Query Response Time**: 70-80% faster (2-3 seconds  200-500ms)
- **Data Volume Reduction**: 90% less irrelevant data sent to Dify
- **Cache Hit Rate**: 70-80% for repeated queries
- **Context Preparation**: Intelligent filtering based on prompt analysis

##  Prerequisites

### 1. Python Dependencies
```bash
pip install redis fastapi uvicorn httpx asyncio
```

### 2. Redis Server
```bash
# Install Redis (Ubuntu/Debian)
sudo apt-get install redis-server

# Install Redis (macOS with Homebrew)
brew install redis

# Start Redis
redis-server

# Test Redis connection
redis-cli ping
# Should return: PONG
```

### 3. Environment Variables
Create/update your `.env` file:
```bash
DIFY_API_KEY=your-dify-api-key-here
REDIS_URL=redis://localhost:6379/0
```

##  Installation Steps

### Step 1: Deploy Optimized FastAPI Services

1. **Copy the optimization files to your FastAPI project:**
   ```bash
   cp optimized_hedge_data_service.py /path/to/your/fastapi/project/
   cp redis_cache_service.py /path/to/your/fastapi/project/
   cp optimized_dify_endpoint.py /path/to/your/fastapi/project/
   ```

2. **Update your FastAPI app to include the new endpoints:**
   ```python
   # In your main FastAPI app file (e.g., main.py)
   from optimized_dify_endpoint import app as optimized_app
   
   # Mount the optimized endpoints
   app.mount("/api/v2", optimized_app)
   ```

3. **Start the FastAPI server:**
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

### Step 2: Update Angular Frontend

1. **The frontend files are already updated:**
   - `backend-api.service.ts` - Added optimized endpoint methods
   - `optimized-dify.service.ts` - New service for optimized Dify calls
   - `prompt-templates.component.ts` - Updated to use optimization

2. **Update your environment configuration:**
   ```typescript
   // In src/environments/environment.ts
   export const environment = {
     production: false,
     apiUrl: 'http://localhost:8000/api/v2', // Point to optimized endpoints
     enableDifyOptimization: true
   };
   ```

3. **Install Angular dependencies (if not already present):**
   ```bash
   npm install
   ```

### Step 3: Database Setup (if needed)

Ensure your Supabase database has the required tables:
```sql
-- Check if tables exist
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN (
  'entity_master', 'position_nav_master', 'allocation_engine',
  'hedge_instructions', 'hedge_business_events', 'currency_rates',
  'hedging_framework', 'hedge_instruments'
);
```

##  Configuration Options

### Redis Cache Configuration

Edit `redis_cache_service.py` to adjust cache TTL settings:
```python
self.cache_ttl = {
    "static_config": 3600 * 4,      # 4 hours - rarely changes
    "currency_rates": 3600 * 24,     # 24 hours - daily updates
    "entity_positions": 3600 * 2,    # 2 hours - position updates
    "allocations": 1800,              # 30 minutes - frequent updates
    "hedge_events": 3600,             # 1 hour - moderate updates
    "framework_rules": 3600 * 8,     # 8 hours - infrequent changes
    "prompt_context": 900             # 15 minutes - context data
}
```

### Prompt Analysis Tuning

Modify `PromptAnalyzer` in `optimized_hedge_data_service.py`:
```python
# Add custom currency patterns
currency_pattern = r'\\b(YOUR_CUSTOM_CURRENCIES|USD|EUR|GBP)\\b'

# Add custom entity patterns
entity_patterns = [
    r'\\bYOUR_ENTITY_PATTERN\\b',  # Add your patterns
    r'\\b[A-Z]{2,6}\\d{2,4}\\b'    # Existing pattern
]
```

##  Monitoring and Performance

### Check Performance Statistics
```bash
# Get performance stats
curl http://localhost:8000/api/v2/dify/performance-stats

# Response includes:
{
  "service_performance": {
    "total_requests": 150,
    "cache_hits": 105,
    "cache_hit_rate_percent": 70.0,
    "avg_context_prep_time": 250,
    "avg_dify_response_time": 1200
  },
  "cache_health": {
    "total_keys": 45,
    "memory_used_human": "2.5MB",
    "key_distribution": {
      "currency_rates": 15,
      "entity_positions": 12,
      "prompt_context": 18
    }
  }
}
```

### Cache Management
```bash
# Invalidate cache for specific currency
curl -X POST http://localhost:8000/api/v2/cache/invalidate/USD

# Monitor Redis directly
redis-cli
> KEYS hedge:*
> INFO memory
> FLUSHDB  # Clear all cache (use carefully!)
```

### Frontend Console Monitoring

Open browser developer tools and watch for optimization logs:
```
 Sending optimized Dify request: {...}
 Optimized Dify response received: {...}
 Dify Performance Metrics: {
  totalTime: "450ms",
  contextPrepTime: "200ms",
  difyResponseTime: "250ms",
  contextSource: "cache",
  optimization: " Fast context preparation",
  cacheStatus: " Cache Hit"
}
```

##  Troubleshooting

### Common Issues

1. **Redis Connection Failed**
   ```bash
   # Check Redis status
   redis-cli ping
   
   # Check Redis logs
   tail -f /var/log/redis/redis-server.log
   ```

2. **Optimization Not Working**
   ```typescript
   // Check feature flag in prompt-templates.component.ts
   const useOptimized = true; // Should be true
   
   // Check environment configuration
   console.log(environment.apiUrl); // Should point to v2 endpoints
   ```

3. **High Memory Usage**
   ```bash
   # Check Redis memory
   redis-cli INFO memory
   
   # Clear cache if needed
   redis-cli FLUSHDB
   ```

4. **Slow Performance Despite Optimization**
   - Check database query performance
   - Verify parallel execution is working
   - Review cache hit rates
   - Analyze prompt complexity

### Performance Debugging

Enable detailed logging in `optimized_hedge_data_service.py`:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Add timing logs
start_time = datetime.now()
# ... your code ...
logger.debug(f"Operation completed in {(datetime.now() - start_time).total_seconds()}s")
```

##  Feature Flags

Control optimization features via configuration:
```typescript
// In environment.ts
export const environment = {
  // ... other config
  optimizationFeatures: {
    enableParallelQueries: true,
    enableRedisCache: true,
    enablePromptAnalysis: true,
    enableSmartContextFiltering: true,
    maxContextSize: 50000,
    defaultCacheEnabled: true
  }
};
```

##  Production Deployment

### 1. Docker Deployment
```dockerfile
# Dockerfile for optimized FastAPI
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2. Environment Variables for Production
```bash
DIFY_API_KEY=your-production-dify-key
REDIS_URL=redis://your-redis-host:6379/0
DATABASE_URL=your-production-database-url
CACHE_TTL_HOURS=4
MAX_CONTEXT_SIZE=75000
```

### 3. Load Testing
```bash
# Test optimized endpoints
ab -n 100 -c 10 http://your-server/api/v2/dify/performance-stats

# Compare with legacy endpoints  
ab -n 100 -c 10 http://your-server/api/v1/dify/chat
```

##  Success Metrics

After setup, you should see:
-  Response times under 1 second for cached queries
-  70%+ cache hit rate after initial warmup
-  Detailed performance metrics in console
-  Reduced Dify token usage due to focused context
-  Automatic fallback to legacy system if needed

##  Support

If you encounter issues:
1. Check the troubleshooting section above
2. Review the console logs for optimization indicators
3. Verify all dependencies are installed correctly
4. Test Redis connectivity independently

The optimization system is designed to gracefully fallback to the legacy implementation if any component fails, ensuring system reliability.