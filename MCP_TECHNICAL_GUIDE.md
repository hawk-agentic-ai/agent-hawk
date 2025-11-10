# MCP Technical Guide - Model Context Protocol

## 🎯 Overview

The Model Context Protocol (MCP) serves as the intelligent middleware between the Hawk Agent frontend and AI processing systems, specifically designed for financial hedge fund operations.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    MCP ARCHITECTURE                         │
├─────────────────────────────────────────────────────────────┤
│  Frontend Request   │   MCP Processing   │   AI Response    │
│  ┌─────────────────┐ │ ┌─────────────────┐ │ ┌──────────────┐ │
│  │ Angular UI      │─┤►│ MCP Server      │─┤►│ Dify.ai      │ │
│  │ HAWK Component  │ │ │ (Port 8009)     │ │ │ Workflows    │ │
│  └─────────────────┘ │ └─────────────────┘ │ └──────────────┘ │
│                     │                     │                  │
│  ┌─────────────────┐ │ ┌─────────────────┐ │ ┌──────────────┐ │
│  │ Operations UI   │─┤►│ Allocation Srv  │─┤►│ Business     │ │
│  │ Management      │ │ │ (Port 8010)     │ │ │ Logic Engine │ │
│  └─────────────────┘ │ └─────────────────┘ │ └──────────────┘ │
├─────────────────────────────────────────────────────────────┤
│                   SHARED MODULES                            │
│  hedge_processor.py  │  data_extractor.py │  business_logic.py │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 MCP Services

### 1. MCP Server Production (Port 8009)
**File**: `mcp_server_production.py` (565 lines)
**Purpose**: Primary MCP-over-HTTP JSON-RPC 2.0 server

#### Key Features:
```python
# Core Capabilities
- JSON-RPC 2.0 Protocol: Standard communication
- Tool Registry: Dynamic function discovery
- Request Routing: Intelligent method dispatch
- Error Handling: Comprehensive error responses
- CORS Support: Cross-origin requests
- Authentication: Token-based security
```

#### Supported Methods:
```json
{
  "initialize": "Setup MCP connection and capabilities",
  "initialized": "Notification of successful initialization",
  "tools/list": "Retrieve available tool definitions",
  "tools/call": "Execute specific hedge fund operations"
}
```

### 2. MCP Allocation Server (Port 8010)
**File**: `mcp_allocation_server.py` (1,175 lines)
**Purpose**: Specialized allocation and fund management

#### Key Features:
```python
# Allocation Capabilities
- Fund Capacity Analysis: Real-time utilization checks
- Position Management: I-U-R-T-A-Q operations
- Risk Assessment: Automated risk calculations
- Compliance Checking: Regulatory validation
- Portfolio Optimization: AI-driven suggestions
```

## 🛠️ Technical Implementation

### JSON-RPC 2.0 Protocol
```json
// Request Format
{
  "jsonrpc": "2.0",
  "id": "unique-request-id",
  "method": "tools/call",
  "params": {
    "name": "process_hedge_prompt",
    "arguments": {
      "instruction_type": "inception",
      "user_prompt": "Create new hedge position",
      "stage": "stage_1a"
    }
  }
}

// Response Format
{
  "jsonrpc": "2.0",
  "id": "unique-request-id",
  "result": {
    "content": [
      {
        "type": "text",
        "text": "Successfully processed hedge operation"
      }
    ],
    "isError": false
  }
}
```

### Tool Registry
```python
# Available Tools
AVAILABLE_TOOLS = [
    {
        "name": "process_hedge_prompt",
        "description": "Process hedge fund operations (I-U-R-T-A-Q)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "instruction_type": {
                    "type": "string",
                    "enum": ["inception", "utilization", "rollover", "termination", "amendment", "query"]
                },
                "user_prompt": {"type": "string"},
                "stage": {"type": "string", "enum": ["stage_1a", "stage_1b", "stage_2"]}
            },
            "required": ["instruction_type", "user_prompt"]
        }
    }
]
```

### Error Handling
```python
# Error Response Structure
{
    "jsonrpc": "2.0",
    "id": request_id,
    "error": {
        "code": -32603,
        "message": "Internal error",
        "data": "Detailed error description"
    }
}

# Common Error Codes
-32700: Parse error
-32600: Invalid request
-32601: Method not found
-32602: Invalid params
-32603: Internal error
```

## 🔄 Request Flow

### 1. Initialization Sequence
```
Client → initialize → MCP Server
      ← capabilities ←
Client → initialized → MCP Server
      ← 204 No Content ←
```

### 2. Tool Discovery
```
Client → tools/list → MCP Server
      ← tool_registry ←
```

### 3. Operation Execution
```
Client → tools/call → MCP Server → Business Logic → Supabase
      ← streaming_response ←         ← data_extraction ←
```

## 🎛️ Configuration

### Environment Variables
```bash
# MCP Server Configuration
MCP_HOST=0.0.0.0
MCP_PORT=8009
DIFY_TOOL_TOKEN=your_secure_token_here

# Allocation Server Configuration
ALLOCATION_HOST=0.0.0.0
ALLOCATION_PORT=8010

# Security Settings
CORS_ORIGINS=https://cloud.dify.ai,https://3-238-163-106.nip.io
AUTH_REQUIRED=true
```

### CORS Configuration
```python
# Secure CORS setup
ALLOWED_ORIGINS = [
    "https://cloud.dify.ai",
    "https://3-238-163-106.nip.io",
    "http://localhost:4200"  # Development
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"]
)
```

## 🧠 Business Logic Integration

### Shared Modules
```python
# Core Processing Engine
from shared.hedge_processor import hedge_processor

# Key Components:
├── hedge_processor.py (85,308 lines)
│   ├── HedgeFundProcessor class
│   ├── I-U-R-T-A-Q operation handlers
│   ├── AI decision engine integration
│   └── Performance optimization
│
├── data_extractor.py (21,404 lines)
│   ├── Supabase query optimization
│   ├── Real-time data processing
│   ├── Cache management
│   └── Response formatting
│
└── business_logic.py (28,187 lines)
    ├── Financial calculations
    ├── Risk assessment algorithms
    ├── Compliance validation
    └── Portfolio optimization
```

### Performance Features
```python
# Caching Strategy
- Redis Integration: 98% hit rate target
- Query Optimization: <2s response time
- Parallel Processing: 5-10 simultaneous operations
- Memory Management: Efficient resource usage

# Error Recovery
- Graceful Degradation: Fallback mechanisms
- Retry Logic: Automatic error recovery
- Circuit Breaker: Prevents cascade failures
- Health Monitoring: Real-time status checks
```

## 🔧 Development & Testing

### Local Development
```bash
# Start MCP Server locally
cd hedge-agent
python mcp_server_production.py

# Start Allocation Server
python mcp_allocation_server.py

# Test endpoints
curl -X POST http://localhost:8009/ \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":"1","method":"tools/list"}'
```

### Health Checks
```bash
# MCP Server Health
curl https://3-238-163-106.nip.io/mcp/

# Allocation Server Health
curl https://3-238-163-106.nip.io/dify/
```

### Debugging
```python
# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Monitor requests
logger.info(f"Request: {json.dumps(body)}")
logger.info(f"Response: {json.dumps(response)}")

# Performance monitoring
start_time = time.time()
# ... processing ...
execution_time = time.time() - start_time
logger.info(f"Execution time: {execution_time:.2f}s")
```

## 🚀 Deployment

### Production Deployment
```bash
# Deploy via SSH
ssh -i agent_tmp.pem ubuntu@3.238.163.106

# Navigate to production directory
cd /home/ubuntu/hedge-agent/production/backend/

# Start services with PM2
pm2 start mcp_server_production.py --name mcp_server
pm2 start mcp_allocation_server.py --name allocation_server

# Monitor services
pm2 status
pm2 logs mcp_server
```

### Service Management
```bash
# Restart services
pm2 restart mcp_server
pm2 restart allocation_server

# Stop services
pm2 stop mcp_server

# View logs
pm2 logs --lines 100
```

## 📊 Monitoring & Analytics

### Performance Metrics
```bash
# Response Time Monitoring
Average Response Time: <2s
95th Percentile: <3s
99th Percentile: <5s

# Cache Performance
Cache Hit Rate: 98% (target)
Cache Miss Rate: 2%
Memory Usage: <100MB

# Error Rates
Success Rate: 99.9%
Error Rate: <0.1%
Timeout Rate: <0.01%
```

### Logging
```python
# Structured logging
{
    "timestamp": "2025-09-24T12:00:00Z",
    "level": "INFO",
    "service": "mcp_server",
    "method": "tools/call",
    "execution_time": 1.23,
    "cache_hit": true,
    "user_id": "user_123"
}
```

## 🔐 Security

### Authentication
```python
# Token-based authentication
AUTH_TOKEN = os.getenv("DIFY_TOOL_TOKEN")

def authenticate_request(token: str) -> bool:
    return token == AUTH_TOKEN
```

### Input Validation
```python
# Parameter validation
def validate_tool_parameters(tool_name: str, arguments: dict) -> Optional[callable]:
    if tool_name == "process_hedge_prompt":
        required = ["instruction_type", "user_prompt"]
        if not all(key in arguments for key in required):
            return lambda req_id: _jsonrpc_error(req_id, -32602, "Missing required parameters")
    return None
```

### Rate Limiting
```python
# Request throttling (future implementation)
@rate_limit(requests_per_minute=60)
async def handle_request(request: Request):
    # Process request
    pass
```

## 🎯 Future Enhancements

### Phase 1: Advanced Features
- [ ] WebSocket support for real-time streaming
- [ ] Enhanced error recovery mechanisms
- [ ] Advanced caching strategies
- [ ] Performance optimization

### Phase 2: Scale & Security
- [ ] Load balancing across multiple MCP instances
- [ ] Enhanced security measures
- [ ] Comprehensive audit logging
- [ ] Rate limiting and DDoS protection

### Phase 3: AI Enhancement
- [ ] Advanced AI model routing
- [ ] Predictive caching
- [ ] Automated optimization
- [ ] Machine learning insights

---

*Last Updated: September 24, 2025*
*Version: 1.0.0*
*MCP Protocol: 2024-11-05*