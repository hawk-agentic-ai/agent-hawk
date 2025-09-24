# Hedge Fund Management Platform - Technical Documentation

## Project Overview

### Vision Statement
A comprehensive hedge fund operations platform that provides real-time analytics, automated hedge effectiveness monitoring, and AI-powered decision support for financial risk management. The platform integrates traditional hedge fund operations with modern AI capabilities through Dify Cloud integration.

### Current Status
- **Production-Ready**: Fully deployed on AWS with HTTPS
- **Frontend**: Angular 18 application with 49+ components
- **Backend**: Python FastAPI with unified business logic
- **AI Integration**: MCP (Model Context Protocol) server for Dify Cloud
- **Database**: Supabase PostgreSQL with Redis caching
- **Deployment**: AWS EC2 with Nginx reverse proxy

---

## Architecture Overview

### High-Level Architecture
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Angular 18    │    │   FastAPI        │    │   Supabase      │
│   Frontend      │◄──►│   Backend        │◄──►│   PostgreSQL    │
│   (Port 443)    │    │   (Port 8004)    │    │   Database      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         v                       v                       v
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Nginx Proxy   │    │   Redis Cache    │    │   Dify Cloud    │
│   SSL/HTTPS     │    │   Performance    │    │   AI Platform   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                       ▲
                                │                       │
                                v                       │
                       ┌──────────────────┐           │
                       │   MCP Server     │───────────┘
                       │   (Port 8009)    │
                       │   JSON-RPC 2.0   │
                       └──────────────────┘
```

### Service URLs
- **Production Frontend**: `https://3-91-170-95.nip.io`
- **API Backend**: `https://3-91-170-95.nip.io/api`
- **MCP Server**: `https://3-91-170-95.nip.io/mcp`
- **Health Check**: `https://3-91-170-95.nip.io/api/health`

---

## Frontend Architecture (Angular 18)

### Technology Stack
- **Framework**: Angular 18 (Standalone Components)
- **UI Library**: PrimeNG 17.18.0 + PrimeIcons
- **Data Grid**: AG-Grid Community 32.0.0
- **Charts**: Chart.js 4.4.9
- **Styling**: Tailwind CSS + PrimeNG Themes
- **Database Client**: Supabase-js 2.56.0

### Project Structure
```
src/
├── app/
│   ├── core/                     # Core functionality
│   │   ├── components/           # Shared UI components
│   │   │   ├── header/           # Application header
│   │   │   ├── main-sidebar/     # Primary navigation
│   │   │   └── sub-sidebar/      # Secondary navigation
│   │   ├── config/               # Configuration files
│   │   │   ├── app-config.ts     # Application settings
│   │   │   └── supabase.config.ts # Database configuration
│   │   ├── data/                 # Data access layer
│   │   │   └── supabase.client.ts # Database client
│   │   └── services/             # Core services
│   │       └── layout.service.ts # Layout management
│   ├── features/                 # Feature modules
│   │   ├── hedge/                # Core hedge fund operations
│   │   │   └── dashboard/        # Main dashboard
│   │   ├── analytics/            # Financial analytics (7 components)
│   │   ├── configuration/        # System configuration (8 components)
│   │   ├── hawk-agent/           # AI-powered operations (4 components)
│   │   ├── operations/           # Daily operations (7 components)
│   │   └── audit/                # Audit & compliance (4 components)
│   ├── app.component.ts          # Root component
│   └── app.routes.ts             # Application routing
├── assets/                       # Static assets
├── styles.css                    # Global styles
└── main.ts                       # Application bootstrap
```

### Feature Modules

#### 1. Analytics Module (7 Components)
- **Hedge Effectiveness**: ASC 815 compliance monitoring
- **Performance Metrics**: ROI, Sharpe ratio calculations
- **Threshold Monitoring**: Risk limit surveillance
- **Hedging Instruments**: Derivative instrument tracking
- **Exceptions & Alerts**: Automated risk notifications
- **Regulatory Reporting**: IFRS 9, ASC 815 reports
- **SFX Positions**: Foreign exchange position analytics

#### 2. Configuration Module (8 Components)
- **Positions Navigation**: Portfolio position management
- **Hedge Parameters**: Risk parameter configuration
- **Data Sources**: External system connections
- **User Management**: Access control & permissions
- **System Settings**: Application configuration
- **Alert Configuration**: Notification setup
- **Workflow Configuration**: Process automation
- **Integration Settings**: External API management

#### 3. Hawk Agent Module (4 Components)
- **Prompt Templates**: AI conversation templates
- **Prompt History**: Conversation audit trail
- **Manual Mode**: Direct AI interaction
- **Agent Mode**: Automated AI decision support

#### 4. Operations Module (7 Components)
- **Hedge Instructions**: Trade execution commands
- **Apportionment Table**: Cost allocation matrix
- **Murex Booking**: Trade booking system integration
- **Accounting Hub**: Financial transaction processing
- **Externalization Management**: Third-party hedge management
- **Daily Monitoring**: Real-time operation surveillance
- **Hedge Failure Management**: Exception handling workflows

#### 5. Audit Module (4 Components)
- **Audit Logs**: System activity tracking
- **System Logs**: Technical error monitoring
- **Data Lineage**: Data flow documentation
- **Config Change History**: Configuration audit trail

---

## Backend Architecture (Python FastAPI)

### Technology Stack
- **Framework**: FastAPI (Production-grade ASGI)
- **Database**: Supabase PostgreSQL
- **Caching**: Redis (Performance optimization)
- **Authentication**: Bearer token + Supabase Auth
- **Deployment**: Uvicorn ASGI server

### Core Components

#### 1. Unified Smart Backend (`unified_smart_backend.py`)
**Purpose**: Main FastAPI application with unified business logic
**Port**: 8004
**Features**:
- RESTful API endpoints for frontend
- Integrated caching with Redis
- Supabase database operations
- Health monitoring and diagnostics
- Cross-origin resource sharing (CORS)

#### 2. Shared Business Logic (`shared/` module)
**Components**:
- `hedge_processor.py` - Core hedge fund operations processor
- `business_logic.py` - Financial calculation engine
- `data_extractor.py` - Smart data extraction and analysis
- `cache_manager.py` - Redis cache management
- `supabase_client.py` - Database connection management

#### 3. MCP Server (`mcp_dify_compatible.py`)
**Purpose**: Model Context Protocol server for Dify Cloud integration
**Port**: 8009
**Protocol**: JSON-RPC 2.0 over HTTP
**Authentication**: Bearer token (`DIFY_TOOL_TOKEN`)

### API Endpoints

#### Core Backend Endpoints (Port 8004)
```
GET  /health                    # System health check
POST /api/hedge-operations      # Process hedge fund operations
GET  /api/supabase-data        # Database query operations
POST /api/prompt-processing     # AI prompt processing
GET  /api/cache-stats          # Cache performance metrics
```

#### MCP Server Endpoints (Port 8009)
```
POST /                         # JSON-RPC 2.0 endpoint
GET  /                         # Health check (204 No Content)
HEAD /                         # Health check
OPTIONS /                      # CORS preflight
```

---

## MCP Integration Architecture

### Overview
The Model Context Protocol (MCP) integration enables Dify Cloud to interact with hedge fund operations through a standardized JSON-RPC 2.0 interface.

### MCP Server Features

#### Available Tools
1. **process_hedge_prompt**
   - **Purpose**: Process natural language hedge fund operations
   - **Input**: User prompt, template category, currency, entity ID, NAV type, amount
   - **Output**: Structured hedge fund analysis and recommendations

2. **query_supabase_data**
   - **Purpose**: Direct database queries with filtering
   - **Input**: Table name, filters, limit, order_by
   - **Output**: Filtered database results

3. **get_system_health**
   - **Purpose**: System health and performance monitoring
   - **Input**: None
   - **Output**: Component status, cache statistics, performance metrics

4. **manage_cache**
   - **Purpose**: Cache operations and maintenance
   - **Input**: Operation type (stats/info/clear_currency), currency
   - **Output**: Cache management results

#### Authentication
- **Method**: Bearer token authentication
- **Environment Variable**: `DIFY_TOOL_TOKEN`
- **Header**: `Authorization: Bearer <token>`

#### Protocol Compliance
- **Standard**: JSON-RPC 2.0
- **Transport**: HTTP POST
- **Content-Type**: `application/json`
- **Error Handling**: Standard JSON-RPC error codes
- **Notification Support**: 204 No Content responses

### Dify Cloud Configuration
```json
{
  "service_url": "https://3-91-170-95.nip.io/mcp/",
  "name": "Hedge Fund MCP Server",
  "server_identifier": "hedge-fund-mcp",
  "authentication": {
    "type": "bearer_token",
    "token": "${DIFY_TOOL_TOKEN}"
  },
  "timeout": 30000,
  "read_timeout": 30000
}
```

---

## Database Architecture

### Supabase PostgreSQL Schema

#### Core Tables
1. **prompt_templates**
   - Template management for AI conversations
   - Categories: hedge_operations, risk_analysis, compliance

2. **hedge_positions**
   - Portfolio position tracking
   - Real-time mark-to-market valuation

3. **hedge_effectiveness_tests**
   - ASC 815 compliance testing results
   - Effectiveness ratio calculations

4. **risk_parameters**
   - Risk limit configuration
   - Threshold monitoring settings

5. **audit_logs**
   - System activity tracking
   - User action auditing

#### Caching Strategy
- **Primary Cache**: Redis for frequently accessed data
- **Cache Types**: Query results, computation results, session data
- **TTL**: Configurable per data type (5 minutes to 24 hours)
- **Invalidation**: Smart cache clearing based on data dependencies

---

## Deployment Architecture

### AWS Infrastructure
- **Instance Type**: EC2 (Free tier compatible)
- **Operating System**: Ubuntu 22.04 LTS
- **Domain**: `3-91-170-95.nip.io` (nip.io wildcard DNS)
- **SSL**: Let's Encrypt certificates
- **Reverse Proxy**: Nginx

### Service Configuration

#### Nginx Configuration
```nginx
server {
    listen 443 ssl http2;
    server_name 3-91-170-95.nip.io;
    
    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/3-91-170-95.nip.io/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/3-91-170-95.nip.io/privkey.pem;
    
    # Frontend (Angular)
    root /var/www/3-91-170-95.nip.io;
    index index.html;
    
    # API Backend (FastAPI)
    location /api/ {
        proxy_pass http://localhost:8004/;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # MCP Server (Dify Integration)
    location /mcp/ {
        proxy_pass http://localhost:8009/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### Process Management
- **Frontend**: Static files served by Nginx
- **Backend**: `python3 -m uvicorn unified_smart_backend:app --host 0.0.0.0 --port 8004`
- **MCP Server**: `python3 mcp_dify_compatible.py`

### Monitoring
- **Health Checks**: `/health` and `/api/health` endpoints
- **Logs**: Application logs in `~/hedge-agent/backend.log`
- **Performance**: Redis cache statistics
- **Uptime**: Process monitoring via `ps aux`

---

## Current Functionality

### Operational Features
1. **Real-time Position Monitoring**: Live hedge fund position tracking
2. **Risk Analytics**: Automated risk calculation and reporting
3. **Compliance Monitoring**: ASC 815 and IFRS 9 compliance automation
4. **AI-Powered Decision Support**: Natural language hedge fund operations
5. **Automated Reporting**: Regulatory and internal report generation
6. **Cache-Optimized Performance**: Sub-second response times
7. **Audit Trail**: Complete user action and system event logging

### AI Integration Features (via Dify)
1. **Natural Language Operations**: Process hedge instructions in plain English
2. **Intelligent Data Queries**: AI-powered database exploration
3. **Risk Assessment**: Automated risk analysis with explanations
4. **Performance Analytics**: AI-driven performance insights
5. **Compliance Guidance**: Automated compliance checking and recommendations

---

## Technical Requirements

### Development Environment
- **Node.js**: 18+ for Angular development
- **Python**: 3.9+ for backend development
- **Package Managers**: npm/pnpm for frontend, pip for backend
- **Development Tools**: Angular CLI, VS Code/IDE

### Production Environment
- **Server**: Ubuntu 22.04 LTS on AWS EC2
- **Runtime**: Python 3.9+, Node.js 18+
- **Database**: Supabase (PostgreSQL 15+)
- **Cache**: Redis 6+
- **Web Server**: Nginx 1.20+
- **SSL**: Let's Encrypt certificates

### Performance Requirements
- **Response Time**: < 500ms for API calls
- **Cache Hit Rate**: > 95% for frequently accessed data
- **Uptime**: 99.9% availability target
- **Concurrent Users**: Designed for 100+ simultaneous users

### Security Requirements
- **Authentication**: Bearer token + Supabase Row Level Security
- **Encryption**: TLS 1.3 for all communications
- **Data Protection**: Encrypted data at rest in Supabase
- **Audit Logging**: Complete audit trail for all operations
- **Access Control**: Role-based permissions

---

## Development Workflow

### Frontend Development
```bash
# Install dependencies
npm install

# Development server
npm run dev

# Production build
npm run build:prod

# Serve production build
npm run serve
```

### Backend Development
```bash
# Install dependencies
pip install -r requirements.txt

# Development server
python -m uvicorn unified_smart_backend:app --reload --port 8004

# MCP server
python mcp_dify_compatible.py
```

### Deployment
```bash
# Frontend deployment
npm run build:prod
scp -r dist/* ubuntu@server:/var/www/site/

# Backend deployment
scp unified_smart_backend.py ubuntu@server:~/hedge-agent/
ssh ubuntu@server "cd hedge-agent && pkill -f uvicorn && python3 -m uvicorn unified_smart_backend:app --host 0.0.0.0 --port 8004 &"
```

---

## Project Roadmap

### Phase 1: Current Status ✅
- [x] Complete Angular 18 frontend with 49 components
- [x] Unified FastAPI backend with shared business logic
- [x] MCP server integration with Dify Cloud
- [x] Production deployment on AWS with HTTPS
- [x] Redis caching for performance optimization

### Phase 2: Enhanced AI Capabilities (Next 1-2 weeks)
- [ ] Expand MCP tool library with specialized hedge fund operations
- [ ] Implement advanced caching strategies for high-frequency requests
- [ ] Add real-time market data integration
- [ ] Portfolio risk analysis and VaR calculations

### Phase 3: Production Hardening (Next 2-4 weeks)
- [ ] Comprehensive monitoring and alerting system
- [ ] Role-based access control implementation
- [ ] Rate limiting and DDoS protection
- [ ] Automated backup and disaster recovery

### Phase 4: Advanced Analytics (Next 1-2 months)
- [ ] Machine learning models for predictive analytics
- [ ] Automated anomaly detection in transactions
- [ ] Performance benchmarking against market indices
- [ ] Advanced reporting and visualization capabilities

---

## Support and Maintenance

### Key Files for Claude Context
- **Frontend Entry**: `src/app/app.component.ts`, `src/app/app.routes.ts`
- **Backend Entry**: `unified_smart_backend.py`
- **MCP Server**: `mcp_dify_compatible.py`
- **Shared Logic**: `shared/hedge_processor.py`, `shared/business_logic.py`
- **Configuration**: `angular.json`, `package.json`, `requirements.txt`
- **Deployment**: `nginx_config_updated.conf`

### Common Operations
- **Health Check**: `curl https://3-91-170-95.nip.io/api/health`
- **MCP Test**: `curl -X POST https://3-91-170-95.nip.io/mcp/`
- **Frontend Access**: `https://3-91-170-95.nip.io`
- **Backend Logs**: `tail -f ~/hedge-agent/backend.log`

