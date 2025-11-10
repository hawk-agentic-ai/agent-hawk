# LOCAL TESTING GUIDE - Hedge Agent Integration

Test your Dify agent integration locally before production deployment.

## 🚀 Quick Start Local Testing

### **1. Start the MCP Server Locally**

```bash
cd hedge-agent
python mcp_server_production.py
```

**Expected Output:**
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

### **2. Test Server Health**

Open another terminal and test:

```bash
curl -X POST http://localhost:8000 \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "test-1",
    "method": "initialize",
    "params": {
      "protocolVersion": "2024-11-05",
      "capabilities": {},
      "clientInfo": {"name": "local-test", "version": "1.0.0"}
    }
  }'
```

**Expected Response:**
```json
{
  "jsonrpc": "2.0",
  "id": "test-1",
  "result": {
    "protocolVersion": "2024-11-05",
    "capabilities": {
      "tools": {"listChanged": true}
    },
    "serverInfo": {
      "name": "hedge-fund-mcp",
      "version": "1.0.1"
    }
  }
}
```

### **3. Test Available Tools**

```bash
curl -X POST http://localhost:8000 \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "test-2",
    "method": "tools/list",
    "params": {}
  }'
```

**Should show all bridge tools:**
- `allocation_stage1a_processor`
- `hedge_booking_processor`
- `gl_posting_processor`
- `analytics_processor`
- `config_crud_processor`

### **4. Test Agent Integration**

#### **Test Allocation Agent:**
```bash
curl -X POST http://localhost:8000 \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "test-allocation",
    "method": "tools/call",
    "params": {
      "name": "allocation_stage1a_processor",
      "arguments": {
        "user_prompt": "Check allocation capacity for 1M USD hedge",
        "currency": "USD",
        "entity_id": "ENTITY001",
        "nav_type": "COI",
        "amount": 1000000
      }
    }
  }'
```

#### **Test Booking Agent:**
```bash
curl -X POST http://localhost:8000 \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "test-booking",
    "method": "tools/call",
    "params": {
      "name": "hedge_booking_processor",
      "arguments": {
        "instruction_id": "INST_TEST_LOCAL",
        "currency": "EUR",
        "amount": 500000,
        "execute_booking": false
      }
    }
  }'
```

#### **Test Analytics Agent:**
```bash
curl -X POST http://localhost:8000 \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "test-analytics",
    "method": "tools/call",
    "params": {
      "name": "analytics_processor",
      "arguments": {
        "user_prompt": "Analyze hedge effectiveness for EUR exposures",
        "currency": "EUR",
        "entity_id": "ENTITY001"
      }
    }
  }'
```

#### **Test Config Agent:**
```bash
curl -X POST http://localhost:8000 \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "test-config",
    "method": "tools/call",
    "params": {
      "name": "config_crud_processor",
      "arguments": {
        "table_name": "entity_master",
        "operation": "select",
        "limit": 5
      }
    }
  }'
```

## 🔧 **Advanced Local Testing**

### **Run All Integration Tests:**
```bash
# Run MCP bridge tests
python test_mcp_bridges.py

# Run transaction tests
python test_transaction_atomicity.py

# Run write validation tests
python test_write_validator.py
```

### **Start with Custom Port:**
```python
# In mcp_server_production.py, change the last line:
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)  # Custom port
```

### **Test with Authentication:**
```bash
export DIFY_TOOL_TOKEN="your-test-token"
python mcp_server_production.py

# Then add auth header to requests:
curl -X POST http://localhost:8000 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-test-token" \
  -d '...'
```

## 🎯 **Local Dify Integration Testing**

### **Option 1: Use Local Dify (if you have it)**

1. **Install Dify locally** (docker-compose)
2. **Add your local MCP server** as a tool:
   - URL: `http://host.docker.internal:8000`
   - Or: `http://localhost:8000`

### **Option 2: Simulate Dify Requests**

Create test scripts that mimic what Dify would send:

```python
# test_dify_simulation.py
import requests
import json

def test_allocation_agent():
    """Simulate what Dify Allocation Agent would send"""
    payload = {
        "jsonrpc": "2.0",
        "id": "dify-allocation-001",
        "method": "tools/call",
        "params": {
            "name": "allocation_stage1a_processor",
            "arguments": {
                "user_prompt": "I need to hedge 2M USD exposure for ENTITY001 with COI nav type",
                "currency": "USD",
                "entity_id": "ENTITY001",
                "nav_type": "COI",
                "amount": 2000000
            }
        }
    }

    response = requests.post(
        "http://localhost:8000",
        headers={"Content-Type": "application/json"},
        json=payload
    )

    print("Allocation Agent Response:")
    print(json.dumps(response.json(), indent=2))

if __name__ == "__main__":
    test_allocation_agent()
```

## 📋 **Local Testing Checklist**

### **Before Testing:**
- [ ] Environment variables set (`.env` file)
- [ ] Database connection working (Supabase)
- [ ] Dependencies installed (`pip install -r requirements.txt`)

### **Basic Tests:**
- [ ] Server starts without errors
- [ ] Health check passes
- [ ] Tools list returns all bridge tools
- [ ] Database connection test passes

### **Agent Integration Tests:**
- [ ] Allocation Agent → `allocation_stage1a_processor` works
- [ ] Booking Agent → `hedge_booking_processor` works
- [ ] Booking Agent → `gl_posting_processor` works
- [ ] Analytics Agent → `analytics_processor` works
- [ ] Config Agent → `config_crud_processor` works

### **Error Handling Tests:**
- [ ] Invalid tool names return proper errors
- [ ] Missing parameters return validation errors
- [ ] Database errors are handled gracefully

### **Performance Tests:**
- [ ] Response times under 2 seconds
- [ ] No memory leaks during extended testing
- [ ] Concurrent requests handled properly

## 🚨 **Common Local Testing Issues**

### **1. Port Already in Use**
```bash
# Kill process using port 8000
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Or use different port
python mcp_server_production.py --port 8001
```

### **2. Database Connection Issues**
```bash
# Test connection directly
python test_supabase_connection.py
```

### **3. Environment Variables Not Loading**
```bash
# Check .env file exists and has correct values
cat .env
```

### **4. CORS Issues (if testing from browser)**
```python
# In mcp_server_production.py, add localhost to CORS origins:
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000"
]
```

## ✅ **Success Indicators**

**Your local testing is successful when:**

1. **Server starts** and shows "Application startup complete"
2. **All 8 bridge tools** appear in tools/list
3. **Agent tests return** proper stage_info and success status
4. **No database errors** in the logs
5. **Response times** are under 2 seconds
6. **Transaction tests pass** (if you run them)

## 🚀 **Next Steps After Local Testing**

Once local testing passes:
1. **Test with your actual Dify agents** (point them to localhost:8000)
2. **Verify end-to-end workflows** work as expected
3. **Check logs** for any warnings or issues
4. **Performance test** with realistic data volumes
5. **Ready for production deployment** 🎉

---

**Local testing gives you confidence that everything works before going to production!**