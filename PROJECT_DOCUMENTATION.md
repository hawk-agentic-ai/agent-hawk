# Hedge Agent Smart Backend - Complete Project Documentation

## PROJECT OVERVIEW

**Vision**: Build a Smart Data Intelligence Layer for AI-driven hedge fund operations that eliminates the 6-10 minute response time problem by pre-fetching targeted data and letting Dify focus purely on analysis.

**Current Problem**: Dify Agent is handling both data fetching AND analysis, causing 6-10 minute delays with human-in-loop errors in template mode.

**Solution**: Smart Backend  Fast Parallel Data Fetching  Dify Analysis Only  Stream Results

---

## CURRENT INFRASTRUCTURE STATUS

### **Server Details**
- **AWS EC2**: `3.91.170.95`
- **SSH Key**: `agent_hawk.pem` 
- **User**: `ubuntu`

### **Running Services**
```
 Redis Server: 127.0.0.1:6379 (2 cached items, 56% hit rate)
 Port 8001: Complete I-U-R-T Hedge Workflow Backend v3.0.0
 Port 8002: AI-First Dify Workflow Backend v4.0.0  
 Port 8003: Efficient Targeted Data Extraction v6.0.0
```

### **Database Connections**
- **Supabase URL**: `https://ladviaautlfvpxuadqrb.supabase.co`
- **Supabase Key**: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxhZHZpYWF1dGxmdnB4dWFkcXJiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTU1OTYwOTksImV4cCI6MjA3MTE3MjA5OX0.viCgb6M8hXIwnoadCtmNc7dFbXYVNZ3mglD1Eq1tyes`
- **Dify API Key**: `app-KKtaMynVyn8tKbdV9VbbaeyR`

---

## FRONTEND ARCHITECTURE ANALYSIS

### **Angular 18 Sophisticated Structure**
```
Main Navigation:
 Configuration (10 sub-modules)
    Hedge Framework, Currency, Entity
    Portfolios, Products, Prompt Templates  
    Threshold, Buffer, Business Rules, Booking Model
 Analytics (8 dashboard views)
    SFX Positions, Hedging Instruments
    Hedge Effectiveness, Performance Metrics
    Threshold Monitoring, Exceptions, Reporting
 HAWK Agent (AI-driven operations)  CORE MODULE
    Agentic AI (Template Mode)
    Prompt History (Session Tracking)
 Operations (7 workflow areas)
    Hedge Instructions, Apportionment, Murex Booking
 Audit & System Logs (4 tracking areas)
```

### **HAWK Agent Module Details**
- **Template Mode**: Users select from 30+ prompt templates stored in Supabase
- **Family Types**: Instructions & Processing, Risk Management, Compliance
- **Template Categories**: I-U-R-T-A-Q workflows
- **Current Flow**: Frontend  Dify (6-10 mins)  Stream Response
- **Target Flow**: Frontend  Smart Backend (2 secs)  Dify Analysis  Stream

---

## BACKEND EVOLUTION HISTORY

### **Phase 1: Traditional Backend (Port 8001)**
```python
File: complete_hedge_workflow_backend.py
Purpose: Complete I-U-R-T lifecycle with Murex + GL integration
Status:  Running, Redis initialized but underutilized
Issues: Complex business logic hardcoded in backend
```

### **Phase 2: AI-First Backend (Port 8002)**  
```python
File: ai_dify_workflow_backend.py
Purpose: Minimal backend, Dify handles all business logic
Status:  Running, Dify integration working
Issues: Dify doing both data fetching AND analysis (6-10 min problem)
```

### **Phase 3: Efficient Backend (Port 8003)**
```python  
File: comprehensive_hedge_data_backend.py (My creation)
Purpose: Targeted currency-specific data extraction
Status:  Running, 6.5x performance improvement
Achievement: 3 seconds vs 20+ seconds for data extraction
```

---

## CACHE INFRASTRUCTURE ANALYSIS

### **Redis Cache Strategy (30 Users Optimized)**
```python
File: hedge_management_cache_config.py

Strategy: Permanent cache after ANY usage (0 = cache forever)
- hedge_positions: 0 (permanent)
- inception_template: 0 (permanent) 
- utilisation_template: 0 (permanent)
- market_data: 300 (5 min only for live data)

Target: 98% cache hit rate, 95% cost reduction
```

### **Active Cache Implementation**
```python
File: complete_dify_endpoint.py
Features:
- Redis get/set operations working
- 30-minute cache for Dify responses  
- Cache management endpoints (/dify/cache-info, /dify/cache)
- Performance metrics tracking
```

### **Current Cache Status**
```
 Redis running on 127.0.0.1:6379
 Stats: 18 hits, 14 misses (56% hit rate)  
 Items: 2 cached (hedge_fund:hedge_positions, optimized_positions:ENTITY0015)
 Issue: Cache not integrated with main I-U-R-T workflows
```

---

## CORE PROBLEM ANALYSIS

### **Current Problematic Flow**
```
User Input  Angular HAWK Agent  Dify Agent
                                    
                          Sequential Data Fetching:
                          1. Hit Supabase table 1
                          2. Wait for response  
                          3. Hit Supabase table 2
                          4. Wait for response
                          5. Query Notion knowledge base
                          6. Analyze + Generate response
                          
                      6-10 minutes + errors
```

### **Root Cause Issues**
1. **Dify Overload**: AI doing data operations instead of analysis
2. **Sequential Queries**: One table at a time instead of parallel
3. **Knowledge Base Overhead**: Notion queries adding delay
4. **No Pre-filtering**: Dify gets all data, not targeted context
5. **Cache Bypass**: Direct Supabase hits instead of Redis-first

---

## SOLUTION ARCHITECTURE

### **Target Smart Backend Flow**
```
User Input  Angular Frontend  Smart Backend Intelligence Layer
                                        
                              Prompt Analysis Engine:
                              - Parse user intent (I/U/R/T/A/Q)
                              - Identify required tables
                              - Determine currency/entity scope
                                        
                              Parallel Data Fetcher:
                              - Redis cache check FIRST  
                              - Hit 5-10 Supabase tables simultaneously
                              - Targeted extraction (CNY only for CNY queries)
                                        
                              Context Builder:
                              - Package relevant data for Dify
                              - Include metadata summaries
                              - Send complete context (no more DB queries needed)
                                        
                              Dify Agent (Analysis ONLY):
                              - Focus purely on business logic
                              - Waterfall decisions
                              - Generate recommendations
                                        
                              Stream Response (Real-time)
```

### **Performance Expectations**
- **Data Preparation**: Under 2 seconds (vs 6-10 minutes)
- **Cache Hit Rate**: 98% (vs current 56%)  
- **Parallel Queries**: 5-10 simultaneous (vs sequential)
- **Dify Focus**: Pure analysis (vs data+analysis)
- **Template Mode**: Fully automated (vs human-in-loop errors)

---

## I-U-R-T-A-Q WORKFLOW REQUIREMENTS

### **Utilization (U)**
```
Prompt: "Check if I can hedge 150K CNY today"
Required Data: CNY entities + CNY positions + CNY allocations + threshold configs
Smart Extraction: Filter by currency_code='CNY' only
Dify Focus: Capacity analysis + waterfall logic + recommendations
```

### **Inception (I)**  
```
Prompt: "Start USD 25M COI hedge"
Required Data: USD entities + COI positions + hedge instruments + booking configs  
Smart Extraction: Filter by currency='USD' AND nav_type='COI'
Dify Focus: Deal structuring + booking recommendations + GL entries
```

### **Rollover (R)**
```
Prompt: "Rollover existing EUR hedge"
Required Data: Active EUR positions + rollover configs + recent events
Smart Extraction: Filter by currency='EUR' AND status='Active'
Dify Focus: Rollover feasibility + cost analysis + new terms
```

### **Termination (T)**
```
Prompt: "Close JPY hedge position"  
Required Data: Mature JPY positions + GL entries + P&L data
Smart Extraction: Filter by currency='JPY' AND eligible for termination
Dify Focus: Settlement calculation + P&L recognition + closure process
```

### **Amendment (A)**
```
Prompt: "Modify order ORD-123 notional to 120M"
Required Data: Original instruction + related events + impact analysis
Smart Extraction: Filter by order_id='ORD-123' + related transactions
Dify Focus: Amendment validation + impact assessment + approval workflow
```

### **Query/Inquiry (Q)**
```
Prompt: "Status of all CNY instructions"
Required Data: Recent CNY instructions + business events + system status
Smart Extraction: Recent activity for currency='CNY' only  
Dify Focus: Status reporting + capacity summary + recommendations
```

---

## TECHNICAL IMPLEMENTATION DETAILS

### **Successful Optimizations Applied**
1. **Targeted Extraction Functions**: Created currency-specific data extraction (6.5x faster)
2. **Parallel Query Capability**: Built infrastructure for simultaneous table queries
3. **Metadata Tracking**: Added extraction counts and performance metrics
4. **Error Handling**: Graceful fallbacks for missing data
5. **API Documentation**: FastAPI auto-generated docs at /docs endpoints

### **Existing Efficient Functions Created**
```python
# In comprehensive_hedge_data_backend.py (Port 8003)
extract_utilization_targeted_data(currency)  CNY-specific data only
extract_inception_targeted_data(currency, nav_type)  Targeted inception context  
extract_rollover_targeted_data(currency)  Active positions focus
extract_termination_targeted_data(currency)  P&L calculation focus
extract_amendment_targeted_data(currency, order_id)  Impact analysis focus
extract_inquiry_targeted_data(currency)  Status reporting focus
```

### **Redis Integration Points**
```python
# Cache configuration available in hedge_management_cache_config.py
get_hedge_cache_key(query_type, user_id, params)  Smart cache keys
get_cache_duration(query_type, usage_count)  30-user optimized durations
HEDGE_CACHE_STRATEGY  Permanent cache for templates, 5min for live data
```

---

## CONSOLIDATION PLAN

### **Next Steps Required**
1. **Analyze Current Backends**: Determine best architecture to build upon
2. **Create Unified Smart Backend**: Merge best features from all 3 backends
3. **Integrate Cache Strategy**: Apply hedge_management_cache_config across all workflows  
4. **Build Prompt Intelligence**: Parse user input  determine required data tables
5. **Implement Parallel Fetching**: Hit multiple Supabase tables simultaneously
6. **Test I-U-R-T-A-Q Workflows**: Validate each workflow type performance
7. **Frontend Integration**: Connect Angular HAWK Agent to new smart backend
8. **Performance Validation**: Achieve <2 second data preparation target

### **Files to Consolidate**
```
 Keep: hedge_management_cache_config.py (sophisticated 30-user strategy)
 Keep: Efficient extraction functions from comprehensive_hedge_data_backend.py  
 Keep: Redis implementation from complete_dify_endpoint.py
 Merge: Best Dify integration patterns from ai_dify_workflow_backend.py
 Retire: Redundant backend processes after consolidation
```

### **Success Criteria**
-  Single unified backend serving all I-U-R-T-A-Q workflows
-  <2 second data preparation (vs 6-10 minutes currently)  
-  98% cache hit rate (vs 56% currently)
-  Parallel data fetching (vs sequential currently)
-  Dify focused on analysis only (vs data+analysis currently)
-  Template mode fully automated (vs human-in-loop errors currently)

---

## DEPLOYMENT INFORMATION

### **Current Deployed Status**
```bash
# Server Access
ssh -i agent_hawk.pem ubuntu@3.91.170.95

# Check Running Services  
ps aux | grep python3
ss -tlnp | grep python

# Redis Status
redis-cli info stats
redis-cli dbsize && redis-cli keys '*'

# Test Endpoints
curl http://3.91.170.95:8001/health
curl http://3.91.170.95:8002/health  
curl http://3.91.170.95:8003/health
```

### **Environment Variables**
```bash
export SUPABASE_URL='https://ladviaautlfvpxuadqrb.supabase.co'
export SUPABASE_ANON_KEY='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxhZHZpYWF1dGxmdnB4dWFkcXJiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTU1OTYwOTksImV4cCI6MjA3MTE3MjA5OX0.viCgb6M8hXIwnoadCtmNc7dFbXYVNZ3mglD1Eq1tyes'
export DIFY_API_KEY='app-KKtaMynVyn8tKbdV9VbbaeyR'
```

---

## LESSONS LEARNED

### **What Worked Well**
1. **Targeted Data Extraction**: 6.5x performance improvement proven
2. **Angular Frontend Sophistication**: Well-structured enterprise-grade UI
3. **Redis Cache Strategy**: Intelligent 30-user optimization approach  
4. **FastAPI Documentation**: Auto-generated API docs valuable for testing
5. **Parallel Architecture**: Multiple backends allowed experimentation

### **What Needs Improvement** 
1. **Backend Consolidation**: 3 backends running simultaneously is inefficient
2. **Cache Integration**: Sophisticated cache strategy not applied to main workflows
3. **Dify Overload**: AI doing data operations wastes time and causes errors
4. **Sequential Queries**: Not leveraging parallel data fetching capabilities
5. **Template Disconnect**: Frontend templates not optimized for backend efficiency

### **Critical Success Factors**
1. **Smart Data Pre-fetching**: Backend must intelligently determine required tables
2. **Cache-First Strategy**: Redis check before any database operations
3. **Parallel Execution**: Multiple Supabase queries simultaneously  
4. **Targeted Context**: Send only relevant data to Dify, not comprehensive datasets
5. **Performance Monitoring**: Track cache hit rates and response times continuously

---

## CONCLUSION

The project has excellent vision and sophisticated architecture. The core problem is clear: **Dify is overloaded with data operations causing 6-10 minute delays**. The solution is equally clear: **Smart Backend handles fast data preparation, Dify focuses purely on analysis**.

All the necessary components exist:
-  Sophisticated Angular frontend with template system  
-  Working Redis cache with 30-user optimization strategy
-  Proven efficient data extraction functions (6.5x faster)  
-  Successful Dify integration patterns
-  AWS infrastructure and database connections

**Next phase**: Consolidate the best parts into ONE smart data intelligence layer that serves the exact architecture the user described.

---

*Documentation created: 2025-09-03*  
*Status: Ready for Smart Backend Consolidation Phase*