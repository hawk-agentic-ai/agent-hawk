# Dify MCP Integration Guide
**Hedge Fund AI Assistant - Model Context Protocol Integration**

---

## Overview

This guide provides step-by-step instructions for integrating the Hedge Fund MCP server with Dify AI platform. The MCP server exposes 4 specialized tools for hedge fund operations via the standardized Model Context Protocol.

## Architecture

```
Dify AI Platform
    ↓ (MCP stdio protocol)
MCP Server (hedge-fund-mcp-server)
    ↓ (shared business logic)  
HedgeFundProcessor
    ↓ (database & cache)
Supabase + Redis
```

## MCP Server Details

- **Server Name**: `hedge-fund-mcp-server`
- **Protocol**: stdio (standard input/output)
- **Location**: `/home/ubuntu/hedge-agent/mcp_server.py`
- **Dependencies**: Python 3.10+, mcp>=1.0.0

## Available Tools

### 1. process_hedge_prompt
**Primary tool for hedge fund operations**

```json
{
  "name": "process_hedge_prompt",
  "description": "Process hedge fund operations from natural language prompts using AI analysis",
  "parameters": {
    "user_prompt": "string (required) - Natural language description of hedge operation",
    "template_category": "string (optional) - inception|utilization|rollover|termination|risk_analysis|compliance|performance|monitoring|general",
    "currency": "string (optional) - Currency code (USD, EUR, GBP, etc.)",
    "entity_id": "string (optional) - Specific entity ID",
    "nav_type": "string (optional) - Official|Unofficial|Both",
    "amount": "number (optional) - Financial amount for calculations",
    "use_cache": "boolean (optional, default: true) - Enable Redis caching"
  }
}
```

**Example Usage:**
- "Create inception hedge instruction for USD 1M position"
- "Show hedge effectiveness for EUR positions"
- "Generate risk analysis for entity ABC123"

### 2. query_supabase_data
**Direct database access for specific queries**

```json
{
  "name": "query_supabase_data",
  "description": "Direct access to Supabase database tables with filtering",
  "parameters": {
    "table_name": "string (required) - entity_master|position_nav_master|hedge_instructions|hedge_business_events|allocation_engine|currency_configuration|etc.",
    "filters": "object (optional) - Key-value pairs for filtering",
    "limit": "integer (optional, default: 100) - Max records (1-1000)",
    "order_by": "string (optional) - Column to sort by (prefix with '-' for DESC)",
    "use_cache": "boolean (optional, default: true) - Use caching"
  }
}
```

**Example Usage:**
- Get USD entities: `{"table_name": "entity_master", "filters": {"currency_code": "USD"}}`
- Recent hedge instructions: `{"table_name": "hedge_instructions", "limit": 50, "order_by": "-created_date"}`

### 3. get_system_health
**System monitoring and diagnostics**

```json
{
  "name": "get_system_health", 
  "description": "Get comprehensive system health and performance metrics",
  "parameters": {}
}
```

**Returns:**
- Database connectivity status
- Cache performance metrics
- Component initialization status
- Processing performance statistics

### 4. manage_cache
**Redis cache management**

```json
{
  "name": "manage_cache",
  "description": "Manage Redis cache operations for performance optimization",
  "parameters": {
    "operation": "string (required) - stats|clear_currency|info",
    "currency": "string (optional) - Currency code for clear_currency operation"
  }
}
```

**Operations:**
- `stats` - Get cache hit rates and statistics
- `clear_currency` - Clear cached data for specific currency
- `info` - Get Redis server memory usage

---

## Dify Configuration Steps

### Step 1: Configure MCP Connection

1. **In Dify Settings → Integrations → Model Context Protocol:**
   - **Connection Type**: `stdio`
   - **Command**: `python3`
   - **Arguments**: `["/home/ubuntu/hedge-agent/mcp_server.py"]`
   - **Working Directory**: `/home/ubuntu/hedge-agent`
   - **Environment Variables**:
     ```
     SUPABASE_URL=https://ladviaautlfvpxuadqrb.supabase.co
     ALLOWED_ORIGINS=https://3-91-170-95.nip.io
     ```

2. **Test Connection:**
   - Click "Test Connection" 
   - Should show: "Connected to hedge-fund-mcp-server"
   - Tools discovered: 4 tools

### Step 2: Verify Tool Discovery

**Expected tool list in Dify:**
- ✅ process_hedge_prompt
- ✅ query_supabase_data  
- ✅ get_system_health
- ✅ manage_cache

### Step 3: Create Hedge Fund Agent

1. **Create New Agent in Dify:**
   - **Name**: "HAWK - Hedge Fund Assistant"
   - **Description**: "AI assistant for hedge fund operations with MCP integration"

2. **Agent Configuration:**
   ```
   Role: You are HAWK, an AI assistant specializing in hedge fund operations.
   You have access to specialized tools via MCP for:
   - Processing hedge instructions (inception, utilization, rollover, termination)
   - Analyzing risk metrics and hedge effectiveness  
   - Querying hedge fund database directly
   - Managing system performance and cache

   Always use the process_hedge_prompt tool for hedge fund operations.
   Use query_supabase_data for specific database queries.
   Check system health regularly with get_system_health.
   ```

3. **Enable MCP Tools:**
   - Check all 4 hedge fund tools
   - Set permissions to "Allow All"

### Step 4: Test Integration

**Test Prompts:**
1. **System Health**: "Check system health"
2. **Simple Query**: "Show me USD entities"  
3. **Hedge Operation**: "Create inception instruction for EUR 500K position"
4. **Risk Analysis**: "Analyze hedge effectiveness for all positions"

---

## Expected Responses

### System Health Response
```json
{
  "status": "healthy",
  "version": "5.0.0-mcp", 
  "components": {
    "supabase": "connected",
    "redis": "connected",
    "prompt_engine": "initialized",
    "data_extractor": "initialized"
  },
  "cache_stats": {
    "cache_hit_rate": "98%",
    "redis_available": true
  }
}
```

### Hedge Operation Response
```json
{
  "status": "success",
  "prompt_analysis": {
    "intent": "hedge_inception",
    "confidence": 95,
    "instruction_type": "I",
    "parameters": {
      "currency": "EUR", 
      "amount": 500000
    }
  },
  "extracted_data": {
    "entity_master": [...],
    "position_nav_master": [...],
    "currency_configuration": [...]
  },
  "optimized_context": "# USER REQUEST ANALYSIS\nIntent: hedge_inception...",
  "processing_metadata": {
    "processing_time_ms": 1247,
    "cache_hit_rate": "94.2%"
  }
}
```

---

## Troubleshooting

### Common Issues

1. **"Connection Failed"**
   - Verify MCP server is accessible: `python3 /home/ubuntu/hedge-agent/mcp_server.py`
   - Check Python path and dependencies
   - Ensure proper permissions on files

2. **"Tools Not Discovered"**  
   - Test tool discovery: Run test scripts in `/home/ubuntu/hedge-agent/`
   - Check MCP server logs for errors
   - Verify MCP protocol version compatibility

3. **"Database Connection Error"**
   - Verify Supabase URL and credentials
   - Check network connectivity to database
   - Test with: `get_system_health` tool

4. **"Performance Issues"**
   - Check Redis cache status with `manage_cache` tool
   - Monitor processing times in tool responses
   - Verify cache hit rates are >90%

### Debug Commands

```bash
# Test MCP server locally
cd /home/ubuntu/hedge-agent
python3 test_simple_mcp.py

# Check dependencies
python3 -c "import mcp; print('MCP OK')"
python3 -c "from shared.hedge_processor import hedge_processor; print('Processor OK')"

# View server logs
tail -f mcp.log

# Test database connection
python3 -c "from shared.supabase_client import DatabaseManager; import asyncio; asyncio.run(DatabaseManager().initialize_connections())"
```

---

## Performance Optimization

### Cache Strategy
- **98% target cache hit rate** for 30-user hedge fund
- **Permanent caching** for strategic data (positions, compliance)
- **5-minute cache** for real-time data (market data, P&L)

### Expected Performance
- **Process hedge prompt**: < 2 seconds (with cache)  
- **Direct queries**: < 500ms
- **System health**: < 100ms
- **Cache operations**: < 50ms

### Monitoring
- Use `get_system_health` regularly to monitor performance
- Check `cache_hit_rate` in all tool responses
- Monitor `processing_time_ms` for performance issues

---

## Migration Benefits

### Before (HTTP Integration)
- ❌ Custom API endpoints needed for each operation
- ❌ Manual context building and streaming
- ❌ Complex error handling and retry logic
- ❌ Tight coupling between Dify and FastAPI

### After (MCP Integration)  
- ✅ **Standardized tool discovery** - Dify automatically finds tools
- ✅ **Rich input schemas** - Built-in validation and documentation
- ✅ **Structured responses** - No manual parsing needed
- ✅ **Error handling** - Standardized MCP error responses
- ✅ **Decoupled architecture** - FastAPI serves Angular, MCP serves Dify
- ✅ **Enhanced debugging** - Clear tool call logs and responses

---

## Next Steps

1. **Configure Dify MCP connection** using above settings
2. **Test all 4 tools** with sample prompts
3. **Create hedge fund workflows** using MCP tools
4. **Monitor performance** via system health tool
5. **Optimize caching** based on usage patterns

**Support**: Check `/home/ubuntu/hedge-agent/` for test scripts and logs.