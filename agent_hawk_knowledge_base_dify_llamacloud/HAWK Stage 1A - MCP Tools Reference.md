# HAWK Stage 1A - MCP Tools Reference

## Overview

This document provides the complete reference for the dedicated Stage 1A Allocation Agent MCP server and its tools. This server is optimized specifically for hedge allocation operations with intelligent intent detection and view-first performance.

**Server Details:**
- **Name**: hawk-allocation-mcp-server
- **Port**: 8010 (dedicated port, separate from unified server)
- **Protocol**: JSON-RPC 2.0 over HTTP
- **Specialization**: Stage 1A operations only

---

## Available Tools

### 1. `allocation_stage1a_processor`
**Primary intelligent tool for Stage 1A operations**

#### Purpose
Handles both analysis queries and hedge instructions with automatic intent detection. Provides optimized routing to views for queries and complete Stage 1A pipeline for instructions.

#### Parameters
```json
{
  "user_prompt": {
    "type": "string",
    "required": true,
    "description": "Natural language request in any format"
  },
  "force_write": {
    "type": "boolean",
    "required": false,
    "default": false,
    "description": "Force instruction recording even for query-type prompts"
  }
}
```

#### Automatic Intent Detection

**QUERY Patterns (→ Fast view-based response):**
- `"Show [CURRENCY] capacity"`
- `"What's available for [CURRENCY]"`
- `"[CURRENCY] headroom status"`
- `"USD PB threshold check"`
- `"Entity breakdown by type"`
- `"Available amounts summary"`

**INSTRUCTION Patterns (→ Full pipeline + DB write):**
- `"Can I hedge [AMOUNT] [CURRENCY]?"`
- `"Would like to check if I can hedge [AMOUNT]"`
- `"Process utilization check for [AMOUNT] [CURRENCY]"`
- `"Check feasibility for placing [AMOUNT] hedge"`
- `"Can we put on another hedge for [AMOUNT]"`

#### Response Format
**For Queries:**
```json
{
  "intent": "CAPACITY_QUERY",
  "data_source": "v_entity_capacity_complete",
  "results": [...],
  "processing_time_ms": 245,
  "cache_hit": true
}
```

**For Instructions:**
```json
{
  "intent": "UTILIZATION_INSTRUCTION",
  "feasibility_result": "Pass|Partial|Fail",
  "allocated_amount": 150000,
  "instruction_id": "INS_20241217_001",
  "db_verification": "✅ CONFIRMED",
  "processing_time_ms": 1247
}
```

---

### 2. `query_allocation_view`
**Direct optimized view access for specific analysis**

#### Purpose
Fast access to specific optimized views when you know exactly which data source is needed. Bypasses intent detection for maximum performance.

#### Parameters
```json
{
  "view_name": {
    "type": "string",
    "required": true,
    "enum": [
      "v_entity_capacity_complete",
      "v_available_amounts_fast",
      "v_usd_pb_capacity_check",
      "v_allocation_waterfall_summary"
    ]
  },
  "filters": {
    "type": "object",
    "required": false,
    "description": "Dynamic filters applied to the view"
  }
}
```

#### Available Views

**v_entity_capacity_complete**
- Complete entity capacity analysis with buffer calculations
- Filters: `currency_code`, `entity_type`, `active_flag`

**v_available_amounts_fast**
- Rapid available capacity calculations
- Filters: `currency_code`, `entity_id`, `nav_type`

**v_usd_pb_capacity_check**
- USD Prime Brokerage threshold monitoring
- Filters: `currency_code`, `threshold_status`

**v_allocation_waterfall_summary**
- Waterfall allocation priority and sequencing
- Filters: `currency_code`, `car_exemption_flag`

#### Example Usage
```json
{
  "view_name": "v_entity_capacity_complete",
  "filters": {
    "currency_code": "AUD",
    "entity_type": "Branch"
  }
}
```

---

### 3. `get_allocation_health`
**System health and performance monitoring**

#### Purpose
Returns comprehensive health status of the Stage 1A allocation system including database connectivity, cache performance, and processing metrics.

#### Parameters
None required.

#### Response Format
```json
{
  "status": "healthy",
  "database": {
    "supabase_connected": true,
    "response_time_ms": 23,
    "last_query": "2024-12-17T10:30:15Z"
  },
  "cache": {
    "redis_available": true,
    "hit_rate": "94.2%",
    "entries_count": 1247
  },
  "views": {
    "v_entity_capacity_complete": "available",
    "v_available_amounts_fast": "available",
    "v_usd_pb_capacity_check": "available"
  },
  "performance": {
    "avg_query_time_ms": 156,
    "avg_instruction_time_ms": 1247,
    "total_requests": 342
  }
}
```

---

## Integration Patterns

### Dify Agent Configuration

**Tool Selection Strategy:**
1. **Primary Tool**: Use `allocation_stage1a_processor` for 95% of user interactions
2. **Fast Queries**: Use `query_allocation_view` when you need specific view data quickly
3. **Monitoring**: Use `get_allocation_health` for system status checks

**Prompt Engineering:**
```markdown
You have access to intelligent Stage 1A tools that automatically detect user intent:

- For any capacity/threshold questions: Just pass the natural language prompt
- For hedge feasibility checks: Pass the prompt as-is, the tool handles extraction
- For system monitoring: Use get_allocation_health

Never manually extract parameters - let the tools handle intent detection.
```

### Natural Language Examples

**Capacity Queries:**
- `"Show me AUD capacity across all entities"`
- `"What's the available headroom for EUR?"`
- `"USD PB threshold status today"`

**Utilization Instructions:**
- `"Can I hedge 150K HKD today?"`
- `"Process utilization check for 2.5M EUR"`
- `"Would like to check if we can put on another 500K AUD hedge"`

**Multi-Entity Analysis:**
- `"Show entity breakdown for SGD capacity"`
- `"Available amounts summary by entity type"`

---

## Performance Characteristics

### Query Performance (Views)
- **Target Response Time**: <200ms
- **Cache Hit Rate**: >95%
- **Data Freshness**: Real-time from views

### Instruction Performance (Full Pipeline)
- **Target Response Time**: <1.5s
- **Database Write**: Always performed for instructions
- **Verification**: Automatic confirmation of persistence

### Error Handling
- **Graceful Fallbacks**: Views → Raw tables → Error
- **Partial Results**: Return available data with warnings
- **Context Preservation**: Maintain Stage 1A scope boundaries

---

## Deployment Configuration

### Environment Variables
```bash
PORT=8010
SUPABASE_URL=https://ladviaautlfvpxuadqrb.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<key>
CORS_ORIGINS=https://dify.ai,http://localhost:4200
CACHE_STRATEGY=view_first
MAX_RESPONSE_SIZE_KB=64
```

### Health Endpoints
- `GET /` - Basic server status
- `GET /health` - Detailed health check
- `GET /health/views` - View availability check

### MCP Endpoint
- `POST /` - JSON-RPC 2.0 MCP protocol

---

## Migration from Universal Server

When ready to migrate Dify agents:

1. **Update MCP Connection**: Change port from 8009 → 8010
2. **Update Tool Names**:
   - `process_hedge_prompt` → `allocation_stage1a_processor`
   - `query_supabase_data` → `query_allocation_view`
   - `get_system_health` → `get_allocation_health`
3. **Simplify Prompts**: Remove manual parameter extraction
4. **Test Natural Language**: Verify intent detection works with your prompt patterns

---

**Note**: This dedicated server provides 3-5x performance improvement for Stage 1A operations while maintaining full compatibility with HAWK business logic and compliance requirements.