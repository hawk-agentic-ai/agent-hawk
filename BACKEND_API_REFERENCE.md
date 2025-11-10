# Backend API Reference - Hawk Agent

## 🎯 Overview

The Hawk Agent backend provides a comprehensive REST API and WebSocket interface for managing hedge fund operations. This reference covers all endpoints, request/response formats, and integration patterns.

## 🏗️ Service Architecture

### Service Endpoints
```
Unified Smart Backend (Port 8004)
├── /api/health          # Health checks
├── /api/hawk/           # HAWK agent operations
├── /api/positions/      # Position management
├── /api/funds/          # Fund operations
└── /api/analytics/      # Performance analytics

MCP Server Production (Port 8009)
├── /                    # JSON-RPC 2.0 endpoint
├── /tools/list          # Tool discovery
└── /tools/call          # Tool execution

MCP Allocation Server (Port 8010)
├── /                    # Allocation JSON-RPC
├── /allocations/        # Fund allocations
└── /capacity/           # Capacity checks
```

## 📡 REST API Endpoints

### Health Check
```http
GET /api/health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "5.0.0",
  "services": {
    "supabase": "connected",
    "redis": "connected",
    "cache_stats": {
      "hits": 1245,
      "misses": 32,
      "hit_rate": "97.5%"
    }
  },
  "uptime": 86400,
  "timestamp": "2025-09-24T12:00:00Z"
}
```

### HAWK Agent Operations
```http
POST /api/hawk/process
```

**Request:**
```json
{
  "instruction_type": "inception",
  "user_prompt": "Create new hedge position for AAPL with $1M allocation",
  "stage": "stage_1a",
  "context": {
    "user_id": "user_123",
    "session_id": "session_456"
  }
}
```

**Response:**
```json
{
  "success": true,
  "operation_id": "op_789",
  "result": {
    "type": "inception",
    "status": "processed",
    "data": {
      "position_id": "pos_101",
      "allocation": 1000000,
      "risk_score": 0.72,
      "compliance_check": "passed"
    }
  },
  "execution_time": 1.23,
  "cached": false
}
```

### Position Management
```http
GET /api/positions
POST /api/positions
PUT /api/positions/{id}
DELETE /api/positions/{id}
```

**GET /api/positions:**
```json
{
  "positions": [
    {
      "id": "pos_101",
      "symbol": "AAPL",
      "allocation": 1000000,
      "current_value": 1050000,
      "profit_loss": 50000,
      "status": "active",
      "created_at": "2025-09-24T10:00:00Z",
      "updated_at": "2025-09-24T12:00:00Z"
    }
  ],
  "total_count": 1,
  "page": 1,
  "page_size": 50
}
```

**POST /api/positions:**
```json
{
  "symbol": "TSLA",
  "allocation": 500000,
  "strategy": "long",
  "risk_limit": 0.05,
  "stop_loss": 0.1,
  "take_profit": 0.2
}
```

### Fund Operations
```http
GET /api/funds/capacity
GET /api/funds/utilization
POST /api/funds/allocate
```

**GET /api/funds/capacity:**
```json
{
  "total_capacity": 100000000,
  "available_capacity": 45000000,
  "utilized_capacity": 55000000,
  "utilization_rate": 0.55,
  "funds": [
    {
      "fund_id": "fund_001",
      "name": "Alpha Fund",
      "capacity": 50000000,
      "utilized": 35000000,
      "available": 15000000
    }
  ]
}
```

### Analytics
```http
GET /api/analytics/performance
GET /api/analytics/risk
GET /api/analytics/portfolio
```

**GET /api/analytics/performance:**
```json
{
  "period": "30d",
  "total_return": 0.087,
  "sharpe_ratio": 1.45,
  "max_drawdown": -0.032,
  "volatility": 0.15,
  "benchmark_return": 0.065,
  "alpha": 0.022,
  "beta": 1.12,
  "daily_returns": [
    {"date": "2025-09-01", "return": 0.002},
    {"date": "2025-09-02", "return": -0.001}
  ]
}
```

## 🔧 JSON-RPC 2.0 API (MCP)

### Initialize Connection
```http
POST http://3.238.163.106:8009/
Content-Type: application/json
```

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "method": "initialize",
  "params": {
    "protocolVersion": "2024-11-05",
    "capabilities": {
      "roots": {"listChanged": true},
      "sampling": {}
    },
    "clientInfo": {
      "name": "hawk-agent",
      "version": "1.0.0"
    }
  }
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "result": {
    "protocolVersion": "2024-11-05",
    "capabilities": {
      "tools": {"listChanged": true},
      "logging": {}
    },
    "serverInfo": {
      "name": "mcp-server-production",
      "version": "1.0.0"
    }
  }
}
```

### List Available Tools
```json
{
  "jsonrpc": "2.0",
  "id": "2",
  "method": "tools/list"
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": "2",
  "result": {
    "tools": [
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
  }
}
```

### Execute Tool
```json
{
  "jsonrpc": "2.0",
  "id": "3",
  "method": "tools/call",
  "params": {
    "name": "process_hedge_prompt",
    "arguments": {
      "instruction_type": "query",
      "user_prompt": "Show me all active positions",
      "stage": "stage_1a"
    }
  }
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": "3",
  "result": {
    "content": [
      {
        "type": "text",
        "text": "Found 5 active positions with total allocation of $12.5M"
      }
    ],
    "isError": false
  }
}
```

## 📊 Data Models

### Position Model
```typescript
interface Position {
  id: string;
  symbol: string;
  allocation: number;
  current_value: number;
  profit_loss: number;
  strategy: 'long' | 'short' | 'neutral';
  status: 'active' | 'closed' | 'pending';
  risk_score: number;
  stop_loss?: number;
  take_profit?: number;
  created_at: string;
  updated_at: string;
}
```

### Fund Model
```typescript
interface Fund {
  id: string;
  name: string;
  total_capacity: number;
  utilized_capacity: number;
  available_capacity: number;
  utilization_rate: number;
  performance_metrics: {
    total_return: number;
    sharpe_ratio: number;
    max_drawdown: number;
    volatility: number;
  };
  created_at: string;
  updated_at: string;
}
```

### Operation Model
```typescript
interface Operation {
  id: string;
  type: 'inception' | 'utilization' | 'rollover' | 'termination' | 'amendment' | 'query';
  status: 'pending' | 'processing' | 'completed' | 'failed';
  user_prompt: string;
  stage: 'stage_1a' | 'stage_1b' | 'stage_2';
  result: any;
  execution_time: number;
  cached: boolean;
  created_at: string;
  completed_at?: string;
}
```

## 🔐 Authentication

### API Key Authentication
```http
POST /api/hawk/process
Authorization: Bearer your_api_key_here
Content-Type: application/json
```

### Token Validation
```json
{
  "token": "your_secure_token",
  "user_id": "user_123",
  "permissions": ["read", "write", "execute"]
}
```

## ⚡ Real-time Features

### WebSocket Connection
```javascript
const ws = new WebSocket('wss://3-238-163-106.nip.io/ws');

// Subscribe to position updates
ws.send(JSON.stringify({
  action: 'subscribe',
  channels: ['positions', 'analytics']
}));

// Receive real-time updates
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Real-time update:', data);
};
```

### Streaming Responses
```http
POST /api/hawk/process
Accept: text/event-stream
```

**Response Stream:**
```
data: {"status": "processing", "progress": 25}

data: {"status": "extracting_data", "progress": 50}

data: {"status": "calculating", "progress": 75}

data: {"status": "completed", "progress": 100, "result": {...}}
```

## 🚨 Error Handling

### Standard Error Response
```json
{
  "success": false,
  "error": {
    "code": "INVALID_ALLOCATION",
    "message": "Allocation exceeds available capacity",
    "details": {
      "requested": 5000000,
      "available": 3000000,
      "fund_id": "fund_001"
    }
  },
  "request_id": "req_789",
  "timestamp": "2025-09-24T12:00:00Z"
}
```

### Common Error Codes
```
INVALID_REQUEST        400  Malformed request
UNAUTHORIZED          401  Invalid authentication
FORBIDDEN             403  Insufficient permissions
NOT_FOUND             404  Resource not found
INVALID_ALLOCATION    422  Allocation validation failed
RISK_LIMIT_EXCEEDED   422  Risk parameters violated
CAPACITY_EXCEEDED     422  Fund capacity exceeded
INTERNAL_ERROR        500  Server error
SERVICE_UNAVAILABLE   503  Temporary service issue
```

### JSON-RPC Error Codes
```
-32700  Parse error       Invalid JSON
-32600  Invalid request   Invalid JSON-RPC
-32601  Method not found  Unknown method
-32602  Invalid params    Bad parameters
-32603  Internal error    Server error
```

## 📈 Rate Limiting

### Limits by Endpoint
```
/api/hawk/process     10 requests/minute
/api/positions        60 requests/minute
/api/funds           100 requests/minute
/api/analytics        30 requests/minute
MCP endpoints         20 requests/minute
```

### Rate Limit Headers
```http
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 7
X-RateLimit-Reset: 1695638400
```

## 🔧 Development Tools

### API Testing
```bash
# Test health endpoint
curl https://3-238-163-106.nip.io/api/health

# Test MCP initialization
curl -X POST https://3-238-163-106.nip.io:8009/ \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":"1","method":"initialize","params":{}}'

# Test position creation
curl -X POST https://3-238-163-106.nip.io/api/positions \
  -H "Authorization: Bearer your_token" \
  -H "Content-Type: application/json" \
  -d '{"symbol":"AAPL","allocation":1000000}'
```

### SDK Examples

#### Python SDK
```python
import requests

class HawkClient:
    def __init__(self, base_url, token):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {token}"}

    def create_position(self, symbol, allocation):
        response = requests.post(
            f"{self.base_url}/api/positions",
            headers=self.headers,
            json={"symbol": symbol, "allocation": allocation}
        )
        return response.json()

# Usage
client = HawkClient("https://3-238-163-106.nip.io", "your_token")
position = client.create_position("TSLA", 500000)
```

#### JavaScript SDK
```javascript
class HawkAPI {
  constructor(baseUrl, token) {
    this.baseUrl = baseUrl;
    this.token = token;
  }

  async processOperation(operation) {
    const response = await fetch(`${this.baseUrl}/api/hawk/process`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(operation)
    });
    return response.json();
  }
}

// Usage
const api = new HawkAPI('https://3-238-163-106.nip.io', 'your_token');
const result = await api.processOperation({
  instruction_type: 'inception',
  user_prompt: 'Create new position',
  stage: 'stage_1a'
});
```

## 🔍 Monitoring

### Health Check Endpoints
```bash
# Service health
curl https://3-238-163-106.nip.io/api/health

# MCP server health
curl https://3-238-163-106.nip.io:8009/

# Allocation server health
curl https://3-238-163-106.nip.io:8010/
```

### Performance Metrics
```json
{
  "response_times": {
    "avg": 1.23,
    "p95": 2.45,
    "p99": 4.67
  },
  "cache_performance": {
    "hit_rate": 0.975,
    "hits": 1245,
    "misses": 32
  },
  "error_rates": {
    "success_rate": 0.999,
    "error_rate": 0.001
  }
}
```

---

*Last Updated: September 24, 2025*
*Version: 1.0.0*
*API Version: v1*