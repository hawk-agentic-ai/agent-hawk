# FastAPI to MCP Migration Plan
**Project: HAWK Hedge Fund Backend - FastAPI to Model Context Protocol Migration**

---

## Executive Summary

This document outlines the complete migration strategy from the current FastAPI-based backend to a Model Context Protocol (MCP) server while maintaining full functionality for the Angular frontend and Dify AI integration.

### Current Architecture
- **FastAPI Server**: Port 8004, serving Angular UI via HTTP/REST
- **Supabase Database**: Hedge fund data storage
- **Redis Cache**: Performance optimization (currently disabled)
- **Dify Integration**: HTTP streaming responses
- **Angular Frontend**: Web UI consuming REST APIs
- **Infrastructure**: AWS EC2 (3.91.170.95) with nginx proxy

### Target Architecture
- **Dual Protocol Server**: FastAPI (Angular) + MCP Server (Dify)
- **Shared Business Logic**: Same core processing for both protocols
- **Zero Frontend Impact**: Angular UI unchanged
- **Enhanced Dify Integration**: Native MCP tool discovery and execution

---

## Migration Requirements

### Functional Requirements

#### FR-1: Protocol Support
- **HTTP/REST Protocol**: Maintain existing endpoints for Angular frontend
- **MCP Protocol**: New standardized interface for Dify AI integration
- **Shared Logic**: Both protocols access identical business functions

#### FR-2: Data Operations
- **Supabase Connectivity**: Preserve existing database operations
- **Redis Caching**: Maintain cache infrastructure (enabled/disabled flexibility)
- **Data Extraction**: Keep `SmartDataExtractor` and `PromptIntelligenceEngine`

#### FR-3: Tool Definitions
Create MCP tools that expose existing functionality:
- `process_hedge_prompt`: Universal hedge fund operation processing
- `query_supabase_data`: Direct database access
- `get_system_health`: Health and status monitoring
- `manage_cache`: Cache control operations
- `analyze_prompt`: Prompt intelligence analysis

#### FR-4: Response Formats
- **HTTP Responses**: Keep existing JSON/streaming formats for Angular
- **MCP Responses**: Return structured data objects for Dify consumption
- **Context Building**: Preserve optimized context generation

### Non-Functional Requirements

#### NFR-1: Performance
- **Response Time**: Maintain sub-2 second data preparation target
- **Concurrent Users**: Support 30 hedge fund users
- **Cache Strategy**: Preserve Redis optimization for small user base

#### NFR-2: Reliability
- **Zero Downtime**: Deployment without service interruption
- **Error Handling**: Maintain comprehensive error management
- **Fallback**: HTTP endpoints remain functional during MCP issues

#### NFR-3: Security
- **Authentication**: Preserve existing security model
- **CORS**: Maintain Angular frontend access
- **Data Privacy**: No security regression

#### NFR-4: Maintainability
- **Code Reuse**: Maximize shared business logic
- **Documentation**: Update API documentation
- **Monitoring**: Preserve health check functionality

---

## Implementation Approach

### Phase 1: Preparation and Setup

#### Step 1.1: Dependencies and Environment
```bash
# Add to requirements.txt
mcp>=1.0.0
asyncio>=3.4.3

# Environment variables (add to .env)
MCP_SERVER_PORT=8005
MCP_SERVER_HOST=0.0.0.0
ENABLE_MCP_SERVER=true
```

#### Step 1.2: Project Structure
```
/project-root/
├── unified_smart_backend.py          # Existing FastAPI server
├── mcp_server.py                     # New MCP server entry point
├── shared/                           # Shared business logic
│   ├── __init__.py
│   ├── business_logic.py             # Extracted shared functions
│   ├── supabase_client.py            # Database connection
│   └── cache_manager.py              # Redis operations
├── mcp_tools/                        # MCP tool definitions
│   ├── __init__.py
│   ├── hedge_tools.py                # Hedge operation tools
│   ├── data_tools.py                 # Data access tools
│   └── system_tools.py               # Health and maintenance tools
├── http_endpoints/                   # FastAPI endpoints
│   ├── __init__.py
│   └── api_routes.py                 # Existing HTTP routes
└── requirements.txt                  # Updated dependencies
```

### Phase 2: Core Implementation

#### Step 2.1: Extract Shared Business Logic
Move core functionality to shared modules:
- `PromptIntelligenceEngine` operations
- `SmartDataExtractor` methods
- `build_optimized_context()` function
- Supabase query builders
- Redis cache operations

#### Step 2.2: Create MCP Server Foundation
```python
# mcp_server.py structure
from mcp.server import Server
from mcp.server.stdio import stdio_server
from shared.business_logic import HedgeFundProcessor
from mcp_tools.hedge_tools import register_hedge_tools

async def main():
    server = Server("hedge-fund-mcp-server")
    
    # Initialize shared components
    processor = HedgeFundProcessor()
    
    # Register MCP tools
    register_hedge_tools(server, processor)
    
    # Start server
    async with stdio_server() as streams:
        await server.run(streams[0], streams[1])
```

#### Step 2.3: Define MCP Tools
Create tool definitions that mirror existing functionality:

```python
# mcp_tools/hedge_tools.py
@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="process_hedge_prompt",
            description="Process hedge fund operations from natural language prompts",
            input_schema={
                "type": "object",
                "properties": {
                    "user_prompt": {"type": "string"},
                    "template_category": {"type": "string"},
                    "currency": {"type": "string"},
                    "entity_id": {"type": "string"},
                    # ... other parameters
                }
            }
        )
    ]
```

### Phase 3: Integration and Testing

#### Step 3.1: Dual Server Configuration
- **FastAPI Server**: Continue serving port 8004 for Angular
- **MCP Server**: New process on port 8005 or stdio for Dify
- **Shared Resources**: Common Supabase and Redis connections
- **Process Management**: Supervisor or systemd configuration

#### Step 3.2: Dify Integration Update
- Remove HTTP endpoint configuration from Dify
- Add MCP server configuration
- Update workflow nodes to use MCP tools
- Test tool discovery and execution

#### Step 3.3: Testing Strategy
1. **Unit Testing**: Individual MCP tools
2. **Integration Testing**: MCP server with Dify
3. **Regression Testing**: Angular frontend functionality
4. **Performance Testing**: Response time validation
5. **Load Testing**: 30 concurrent users simulation

### Phase 4: Deployment and Cutover

#### Step 4.1: Parallel Deployment
- Deploy MCP server alongside existing FastAPI
- Configure nginx for dual service routing
- Enable monitoring for both services
- Validate all endpoints and tools

#### Step 4.2: Dify Migration
- Switch Dify configuration to MCP protocol
- Validate all workflows and agent operations
- Monitor for any integration issues
- Rollback plan to HTTP if needed

#### Step 4.3: Production Validation
- Monitor system health and performance
- Validate Angular frontend operations
- Confirm Dify AI responses
- Check cache performance metrics

---

## Technical Specifications

### MCP Tool Definitions

#### Tool: process_hedge_prompt
**Purpose**: Universal hedge fund operation processing
**Input**: FlexiblePromptRequest equivalent
**Output**: Structured analysis and data
**Business Logic**: Existing prompt intelligence + data extraction

#### Tool: query_supabase_data
**Purpose**: Direct database access for specific queries
**Input**: Table name, filters, parameters
**Output**: Raw query results
**Business Logic**: Existing SmartDataExtractor methods

#### Tool: get_system_health
**Purpose**: System monitoring and diagnostics
**Input**: Component specification (optional)
**Output**: Health status and metrics
**Business Logic**: Existing health check logic

#### Tool: manage_cache
**Purpose**: Cache operations and optimization
**Input**: Operation type, parameters
**Output**: Cache status and statistics
**Business Logic**: Existing Redis cache management

### Data Flow Diagrams

#### Current State
```
Angular UI ──HTTP──→ FastAPI ──SQL──→ Supabase
    ↑                    ↓
    └──────JSON──────────┘

Dify ──HTTP──→ FastAPI ──Context──→ Dify AI
```

#### Target State
```
Angular UI ──HTTP──→ FastAPI ──SQL──→ Supabase
    ↑                    ↓         ↗
    └──────JSON──────────┘    Shared
                              Logic
Dify ──MCP──→ MCP Server ──────┘
```

### Error Handling Strategy

#### MCP Tool Errors
- **Database Errors**: Return empty results with error metadata
- **Cache Errors**: Fallback to direct database access
- **Validation Errors**: Return structured error responses
- **System Errors**: Log and return generic error message

#### Fallback Mechanisms
- **MCP Unavailable**: Dify can fallback to HTTP endpoints temporarily
- **Database Unavailable**: Return cached data with staleness warning
- **Redis Unavailable**: Continue without cache (performance impact only)

---

## Risk Assessment and Mitigation

### High Risk Items

#### Risk: Dify Integration Failure
**Impact**: AI functionality completely broken
**Probability**: Medium
**Mitigation**: 
- Parallel HTTP endpoint maintenance
- Comprehensive integration testing
- Rollback procedure documented

#### Risk: Performance Degradation
**Impact**: User experience degraded
**Probability**: Low
**Mitigation**:
- Performance benchmarking before/after
- Cache optimization validation
- Load testing with 30 users

#### Risk: Data Inconsistency
**Impact**: Incorrect hedge fund calculations
**Probability**: Low
**Mitigation**:
- Shared business logic validation
- Comprehensive regression testing
- Side-by-side result comparison

### Medium Risk Items

#### Risk: Deployment Complexity
**Impact**: Extended downtime during deployment
**Probability**: Medium
**Mitigation**:
- Parallel deployment strategy
- Automated rollback procedures
- Staging environment validation

#### Risk: Infrastructure Changes
**Impact**: Nginx/networking issues
**Probability**: Low
**Mitigation**:
- Minimal infrastructure changes
- Port-based separation
- Configuration backup and restore

---

## Success Criteria

### Functional Success
- [ ] All existing Angular UI functionality preserved
- [ ] All MCP tools discoverable by Dify
- [ ] Hedge fund calculations produce identical results
- [ ] Cache performance maintained or improved
- [ ] Error handling comprehensive and appropriate

### Performance Success
- [ ] Sub-2 second response time maintained
- [ ] 30 concurrent user support verified
- [ ] Memory usage within acceptable limits
- [ ] Database connection pooling optimized

### Integration Success
- [ ] Dify workflows execute without modification
- [ ] MCP tool discovery automatic
- [ ] Context building produces equivalent results
- [ ] Streaming vs structured response validated

---

## Implementation Timeline

### Week 1: Foundation
- **Day 1-2**: Extract shared business logic
- **Day 3-4**: Create MCP server structure
- **Day 5**: Basic tool implementation and testing

### Week 2: Integration
- **Day 1-2**: Complete MCP tool development
- **Day 3-4**: Dify integration and testing
- **Day 5**: Performance optimization and validation

### Week 3: Deployment
- **Day 1-2**: Staging environment deployment
- **Day 3**: Production parallel deployment
- **Day 4**: Dify cutover and validation
- **Day 5**: Monitoring and optimization

---

## Monitoring and Maintenance

### Key Metrics
- **Response Time**: Track MCP tool execution time
- **Error Rate**: Monitor tool failures and exceptions
- **Cache Hit Rate**: Validate Redis performance
- **User Experience**: Angular frontend responsiveness
- **Resource Usage**: Memory, CPU, database connections

### Alerting Thresholds
- **Response Time**: > 5 seconds for any tool
- **Error Rate**: > 5% for any 15-minute period
- **Cache Hit Rate**: < 85% (current target 98%)
- **System Health**: Any component unavailable > 30 seconds

### Maintenance Procedures
- **Daily**: Monitor system health dashboard
- **Weekly**: Review performance metrics and optimization opportunities
- **Monthly**: Validate Dify integration and tool usage analytics
- **Quarterly**: Assess migration success and future enhancements

---

## Conclusion

This migration plan provides a comprehensive approach to transitioning from FastAPI to MCP while maintaining system reliability and user experience. The dual-protocol strategy ensures zero disruption to existing functionality while enabling enhanced AI integration capabilities.

The phased implementation approach minimizes risk and allows for thorough testing at each stage. Success depends on careful extraction of shared business logic and comprehensive integration testing with both Angular frontend and Dify AI platform.

**Next Steps**: Review this plan with development team, validate technical approach, and begin Phase 1 implementation.