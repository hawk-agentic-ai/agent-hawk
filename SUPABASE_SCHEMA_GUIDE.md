# Supabase Schema Guide - Hawk Agent

## 🎯 Overview

The Hawk Agent uses Supabase as its primary PostgreSQL database, providing real-time capabilities, row-level security, and comprehensive hedge fund data management. This guide covers the complete database schema, relationships, and access patterns.

## 🏗️ Database Architecture

### Connection Details
```
Database: PostgreSQL 15.1
Host: ladviaautlfvpxuadqrb.supabase.co
Port: 5432
SSL: Required
Connection Pooling: Enabled (max 60 connections)
```

### Environment Configuration
```bash
SUPABASE_URL=https://ladviaautlfvpxuadqrb.supabase.co
SUPABASE_SERVICE_ROLE_KEY=[secure-service-role-key]
SUPABASE_ANON_KEY=[public-anon-key]
```

## 📊 Core Tables

### 1. hedge_funds
Primary fund management table
```sql
CREATE TABLE hedge_funds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fund_name VARCHAR(255) NOT NULL UNIQUE,
    fund_code VARCHAR(50) NOT NULL UNIQUE,
    total_capacity DECIMAL(15,2) NOT NULL DEFAULT 0,
    utilized_capacity DECIMAL(15,2) NOT NULL DEFAULT 0,
    available_capacity DECIMAL(15,2) GENERATED ALWAYS AS (total_capacity - utilized_capacity) STORED,
    utilization_rate DECIMAL(5,4) GENERATED ALWAYS AS (
        CASE WHEN total_capacity > 0
        THEN utilized_capacity / total_capacity
        ELSE 0 END
    ) STORED,
    management_fee DECIMAL(5,4) DEFAULT 0.02,
    performance_fee DECIMAL(5,4) DEFAULT 0.20,
    high_water_mark DECIMAL(15,2) DEFAULT 0,
    inception_date DATE NOT NULL,
    fund_status VARCHAR(20) DEFAULT 'active' CHECK (fund_status IN ('active', 'closed', 'suspended')),
    base_currency VARCHAR(3) DEFAULT 'USD',
    domicile VARCHAR(100),
    administrator VARCHAR(255),
    custodian VARCHAR(255),
    prime_broker VARCHAR(255),
    investment_strategy TEXT,
    risk_profile VARCHAR(50) DEFAULT 'moderate',
    minimum_investment DECIMAL(15,2) DEFAULT 1000000,
    lock_up_period INTEGER DEFAULT 12,
    redemption_frequency VARCHAR(50) DEFAULT 'monthly',
    notice_period INTEGER DEFAULT 30,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID REFERENCES auth.users(id),
    updated_by UUID REFERENCES auth.users(id)
);
```

### 2. positions
Investment positions tracking
```sql
CREATE TABLE positions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fund_id UUID NOT NULL REFERENCES hedge_funds(id) ON DELETE CASCADE,
    position_code VARCHAR(50) NOT NULL,
    instrument_type VARCHAR(50) NOT NULL CHECK (instrument_type IN (
        'equity', 'bond', 'derivative', 'commodity', 'currency', 'alternative'
    )),
    symbol VARCHAR(50) NOT NULL,
    instrument_name VARCHAR(255),
    isin VARCHAR(12),
    cusip VARCHAR(9),
    bloomberg_ticker VARCHAR(50),
    exchange VARCHAR(100),
    sector VARCHAR(100),
    industry VARCHAR(100),
    country VARCHAR(3),
    currency VARCHAR(3) DEFAULT 'USD',
    position_type VARCHAR(10) NOT NULL CHECK (position_type IN ('long', 'short')),
    quantity DECIMAL(15,6) NOT NULL,
    entry_price DECIMAL(15,6) NOT NULL,
    current_price DECIMAL(15,6),
    market_value DECIMAL(15,2) GENERATED ALWAYS AS (quantity * current_price) STORED,
    cost_basis DECIMAL(15,2) GENERATED ALWAYS AS (quantity * entry_price) STORED,
    unrealized_pnl DECIMAL(15,2) GENERATED ALWAYS AS (market_value - cost_basis) STORED,
    realized_pnl DECIMAL(15,2) DEFAULT 0,
    total_pnl DECIMAL(15,2) GENERATED ALWAYS AS (unrealized_pnl + realized_pnl) STORED,
    allocation_percentage DECIMAL(5,4),
    weight_in_portfolio DECIMAL(5,4),
    entry_date DATE NOT NULL,
    last_price_update TIMESTAMPTZ,
    maturity_date DATE,
    option_type VARCHAR(10) CHECK (option_type IN ('call', 'put')),
    strike_price DECIMAL(15,6),
    expiration_date DATE,
    delta DECIMAL(10,6),
    gamma DECIMAL(10,6),
    theta DECIMAL(10,6),
    vega DECIMAL(10,6),
    implied_volatility DECIMAL(10,6),
    position_status VARCHAR(20) DEFAULT 'active' CHECK (position_status IN (
        'active', 'closed', 'pending', 'expired', 'assigned'
    )),
    risk_rating VARCHAR(10) DEFAULT 'medium' CHECK (risk_rating IN ('low', 'medium', 'high', 'extreme')),
    stop_loss DECIMAL(15,6),
    take_profit DECIMAL(15,6),
    position_comments TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID REFERENCES auth.users(id),
    updated_by UUID REFERENCES auth.users(id),

    UNIQUE(fund_id, position_code),
    CONSTRAINT valid_prices CHECK (entry_price > 0 AND (current_price IS NULL OR current_price > 0))
);
```

### 3. transactions
Trade execution records
```sql
CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fund_id UUID NOT NULL REFERENCES hedge_funds(id),
    position_id UUID REFERENCES positions(id),
    transaction_type VARCHAR(20) NOT NULL CHECK (transaction_type IN (
        'buy', 'sell', 'dividend', 'interest', 'fee', 'transfer'
    )),
    transaction_date DATE NOT NULL,
    settlement_date DATE,
    symbol VARCHAR(50) NOT NULL,
    quantity DECIMAL(15,6),
    price DECIMAL(15,6),
    gross_amount DECIMAL(15,2),
    commission DECIMAL(15,2) DEFAULT 0,
    fees DECIMAL(15,2) DEFAULT 0,
    taxes DECIMAL(15,2) DEFAULT 0,
    net_amount DECIMAL(15,2) GENERATED ALWAYS AS (
        gross_amount - COALESCE(commission, 0) - COALESCE(fees, 0) - COALESCE(taxes, 0)
    ) STORED,
    currency VARCHAR(3) DEFAULT 'USD',
    exchange_rate DECIMAL(10,6) DEFAULT 1.0,
    broker VARCHAR(255),
    execution_venue VARCHAR(255),
    order_id VARCHAR(50),
    trade_id VARCHAR(50),
    counterparty VARCHAR(255),
    transaction_status VARCHAR(20) DEFAULT 'settled' CHECK (transaction_status IN (
        'pending', 'executed', 'settled', 'failed', 'cancelled'
    )),
    transaction_comments TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID REFERENCES auth.users(id)
);
```

### 4. allocations
Fund allocation management
```sql
CREATE TABLE allocations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fund_id UUID NOT NULL REFERENCES hedge_funds(id),
    allocation_type VARCHAR(50) NOT NULL CHECK (allocation_type IN (
        'asset_class', 'sector', 'geography', 'strategy', 'risk_bucket'
    )),
    allocation_name VARCHAR(255) NOT NULL,
    target_percentage DECIMAL(5,4) NOT NULL,
    current_percentage DECIMAL(5,4) DEFAULT 0,
    deviation DECIMAL(5,4) GENERATED ALWAYS AS (current_percentage - target_percentage) STORED,
    min_allocation DECIMAL(5,4) DEFAULT 0,
    max_allocation DECIMAL(5,4) DEFAULT 1.0,
    rebalance_threshold DECIMAL(5,4) DEFAULT 0.05,
    allocation_priority INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE,
    effective_date DATE NOT NULL,
    expiry_date DATE,
    allocation_comments TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID REFERENCES auth.users(id),

    CONSTRAINT valid_allocation_range CHECK (
        target_percentage >= 0 AND target_percentage <= 1 AND
        min_allocation >= 0 AND max_allocation <= 1 AND
        min_allocation <= target_percentage AND target_percentage <= max_allocation
    )
);
```

### 5. risk_metrics
Risk measurement and monitoring
```sql
CREATE TABLE risk_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fund_id UUID NOT NULL REFERENCES hedge_funds(id),
    position_id UUID REFERENCES positions(id),
    metric_date DATE NOT NULL,
    var_1_day DECIMAL(15,2),
    var_10_day DECIMAL(15,2),
    cvar_1_day DECIMAL(15,2),
    cvar_10_day DECIMAL(15,2),
    volatility_annualized DECIMAL(10,6),
    beta DECIMAL(10,6),
    correlation DECIMAL(10,6),
    sharpe_ratio DECIMAL(10,6),
    sortino_ratio DECIMAL(10,6),
    calmar_ratio DECIMAL(10,6),
    max_drawdown DECIMAL(10,6),
    tracking_error DECIMAL(10,6),
    information_ratio DECIMAL(10,6),
    exposure_gross DECIMAL(15,2),
    exposure_net DECIMAL(15,2),
    leverage_ratio DECIMAL(10,6),
    concentration_risk DECIMAL(10,6),
    liquidity_score DECIMAL(3,2),
    stress_test_results JSONB,
    risk_attribution JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(fund_id, COALESCE(position_id, '00000000-0000-0000-0000-000000000000'::UUID), metric_date)
);
```

### 6. performance_metrics
Performance tracking and analytics
```sql
CREATE TABLE performance_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fund_id UUID NOT NULL REFERENCES hedge_funds(id),
    metric_date DATE NOT NULL,
    nav_per_share DECIMAL(15,6) NOT NULL,
    total_nav DECIMAL(15,2) NOT NULL,
    daily_return DECIMAL(10,6),
    cumulative_return DECIMAL(10,6),
    ytd_return DECIMAL(10,6),
    inception_return DECIMAL(10,6),
    benchmark_return DECIMAL(10,6),
    excess_return DECIMAL(10,6) GENERATED ALWAYS AS (daily_return - benchmark_return) STORED,
    alpha DECIMAL(10,6),
    beta DECIMAL(10,6),
    r_squared DECIMAL(10,6),
    sharpe_ratio DECIMAL(10,6),
    volatility DECIMAL(10,6),
    max_drawdown DECIMAL(10,6),
    high_water_mark DECIMAL(15,6),
    management_fee_accrued DECIMAL(15,2) DEFAULT 0,
    performance_fee_accrued DECIMAL(15,2) DEFAULT 0,
    total_fees DECIMAL(15,2) GENERATED ALWAYS AS (
        COALESCE(management_fee_accrued, 0) + COALESCE(performance_fee_accrued, 0)
    ) STORED,
    aum_beginning DECIMAL(15,2),
    subscriptions DECIMAL(15,2) DEFAULT 0,
    redemptions DECIMAL(15,2) DEFAULT 0,
    aum_ending DECIMAL(15,2),
    share_outstanding DECIMAL(15,6),
    benchmark_used VARCHAR(100),
    performance_comments TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(fund_id, metric_date)
);
```

### 7. operations_log
I-U-R-T-A-Q operations tracking
```sql
CREATE TABLE operations_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    operation_id VARCHAR(50) NOT NULL UNIQUE,
    fund_id UUID REFERENCES hedge_funds(id),
    operation_type VARCHAR(20) NOT NULL CHECK (operation_type IN (
        'inception', 'utilization', 'rollover', 'termination', 'amendment', 'query'
    )),
    operation_stage VARCHAR(20) DEFAULT 'stage_1a' CHECK (operation_stage IN (
        'stage_1a', 'stage_1b', 'stage_2'
    )),
    user_prompt TEXT NOT NULL,
    ai_response TEXT,
    operation_status VARCHAR(20) DEFAULT 'pending' CHECK (operation_status IN (
        'pending', 'processing', 'completed', 'failed', 'cancelled'
    )),
    execution_time DECIMAL(8,3),
    cached_response BOOLEAN DEFAULT FALSE,
    cache_hit_ratio DECIMAL(5,4),
    error_message TEXT,
    error_code VARCHAR(50),
    request_metadata JSONB,
    response_metadata JSONB,
    user_id UUID REFERENCES auth.users(id),
    session_id VARCHAR(100),
    ip_address INET,
    user_agent TEXT,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 8. audit_trail
Comprehensive audit logging
```sql
CREATE TABLE audit_trail (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    table_name VARCHAR(100) NOT NULL,
    record_id UUID NOT NULL,
    action VARCHAR(20) NOT NULL CHECK (action IN ('INSERT', 'UPDATE', 'DELETE')),
    old_values JSONB,
    new_values JSONB,
    changed_fields TEXT[],
    user_id UUID REFERENCES auth.users(id),
    session_id VARCHAR(100),
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

## 🔗 Table Relationships

```mermaid
erDiagram
    HEDGE_FUNDS ||--o{ POSITIONS : contains
    HEDGE_FUNDS ||--o{ TRANSACTIONS : records
    HEDGE_FUNDS ||--o{ ALLOCATIONS : defines
    HEDGE_FUNDS ||--o{ RISK_METRICS : measures
    HEDGE_FUNDS ||--o{ PERFORMANCE_METRICS : tracks
    HEDGE_FUNDS ||--o{ OPERATIONS_LOG : logs

    POSITIONS ||--o{ TRANSACTIONS : generates
    POSITIONS ||--o{ RISK_METRICS : analyzes

    USERS ||--o{ HEDGE_FUNDS : manages
    USERS ||--o{ POSITIONS : creates
    USERS ||--o{ TRANSACTIONS : executes
    USERS ||--o{ OPERATIONS_LOG : initiates
    USERS ||--o{ AUDIT_TRAIL : tracked_by
```

## 🔐 Row Level Security (RLS)

### RLS Policies

#### hedge_funds Policy
```sql
CREATE POLICY "Users can view funds they have access to" ON hedge_funds
    FOR SELECT USING (
        auth.uid() IN (
            SELECT user_id FROM fund_permissions
            WHERE fund_id = hedge_funds.id
        ) OR
        auth.uid() = created_by
    );

CREATE POLICY "Fund managers can update funds" ON hedge_funds
    FOR UPDATE USING (
        auth.uid() IN (
            SELECT user_id FROM fund_permissions
            WHERE fund_id = hedge_funds.id
            AND permission_type IN ('admin', 'manager')
        )
    );
```

#### positions Policy
```sql
CREATE POLICY "Users can view positions in accessible funds" ON positions
    FOR SELECT USING (
        fund_id IN (
            SELECT fund_id FROM fund_permissions
            WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Portfolio managers can modify positions" ON positions
    FOR ALL USING (
        fund_id IN (
            SELECT fund_id FROM fund_permissions
            WHERE user_id = auth.uid()
            AND permission_type IN ('admin', 'portfolio_manager')
        )
    );
```

### Permission System
```sql
CREATE TABLE fund_permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fund_id UUID NOT NULL REFERENCES hedge_funds(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    permission_type VARCHAR(50) NOT NULL CHECK (permission_type IN (
        'admin', 'manager', 'portfolio_manager', 'analyst', 'viewer'
    )),
    granted_by UUID REFERENCES auth.users(id),
    granted_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE,

    UNIQUE(fund_id, user_id)
);
```

## 📊 Views and Functions

### Comprehensive Fund Overview
```sql
CREATE VIEW fund_overview AS
SELECT
    hf.id,
    hf.fund_name,
    hf.fund_code,
    hf.total_capacity,
    hf.utilized_capacity,
    hf.available_capacity,
    hf.utilization_rate,
    COUNT(p.id) as total_positions,
    COUNT(CASE WHEN p.position_status = 'active' THEN 1 END) as active_positions,
    SUM(p.market_value) as total_market_value,
    SUM(p.unrealized_pnl) as total_unrealized_pnl,
    pm.nav_per_share as current_nav,
    pm.ytd_return,
    rm.var_1_day,
    rm.sharpe_ratio
FROM hedge_funds hf
LEFT JOIN positions p ON hf.id = p.fund_id
LEFT JOIN performance_metrics pm ON hf.id = pm.fund_id
    AND pm.metric_date = (
        SELECT MAX(metric_date)
        FROM performance_metrics pm2
        WHERE pm2.fund_id = hf.id
    )
LEFT JOIN risk_metrics rm ON hf.id = rm.fund_id
    AND rm.position_id IS NULL
    AND rm.metric_date = (
        SELECT MAX(metric_date)
        FROM risk_metrics rm2
        WHERE rm2.fund_id = hf.id AND rm2.position_id IS NULL
    )
GROUP BY hf.id, hf.fund_name, hf.fund_code, hf.total_capacity,
         hf.utilized_capacity, hf.available_capacity, hf.utilization_rate,
         pm.nav_per_share, pm.ytd_return, rm.var_1_day, rm.sharpe_ratio;
```

### Position Performance Analysis
```sql
CREATE VIEW position_performance AS
SELECT
    p.id,
    p.fund_id,
    p.position_code,
    p.symbol,
    p.instrument_name,
    p.position_type,
    p.quantity,
    p.entry_price,
    p.current_price,
    p.market_value,
    p.cost_basis,
    p.unrealized_pnl,
    p.realized_pnl,
    p.total_pnl,
    (p.unrealized_pnl / NULLIF(p.cost_basis, 0)) * 100 as unrealized_return_pct,
    (p.total_pnl / NULLIF(p.cost_basis, 0)) * 100 as total_return_pct,
    p.allocation_percentage,
    p.weight_in_portfolio,
    p.entry_date,
    CURRENT_DATE - p.entry_date as days_held,
    rm.var_1_day as position_var,
    rm.volatility_annualized as position_volatility,
    rm.beta as position_beta,
    p.risk_rating,
    p.position_status
FROM positions p
LEFT JOIN risk_metrics rm ON p.id = rm.position_id
    AND rm.metric_date = (
        SELECT MAX(metric_date)
        FROM risk_metrics rm2
        WHERE rm2.position_id = p.id
    )
WHERE p.position_status = 'active';
```

### Fund Allocation Analysis
```sql
CREATE OR REPLACE FUNCTION get_allocation_analysis(fund_id_param UUID)
RETURNS TABLE (
    allocation_type VARCHAR,
    allocation_name VARCHAR,
    target_percentage DECIMAL,
    current_percentage DECIMAL,
    deviation DECIMAL,
    current_value DECIMAL,
    status VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        a.allocation_type,
        a.allocation_name,
        a.target_percentage,
        a.current_percentage,
        a.deviation,
        (a.current_percentage * hf.total_capacity) as current_value,
        CASE
            WHEN ABS(a.deviation) <= a.rebalance_threshold THEN 'In Range'
            WHEN a.deviation > a.rebalance_threshold THEN 'Over Allocated'
            ELSE 'Under Allocated'
        END as status
    FROM allocations a
    JOIN hedge_funds hf ON a.fund_id = hf.id
    WHERE a.fund_id = fund_id_param
    AND a.is_active = TRUE
    ORDER BY a.allocation_type, a.allocation_priority;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

## 🔄 Real-time Features

### Real-time Subscriptions
```sql
-- Enable realtime for key tables
ALTER PUBLICATION supabase_realtime ADD TABLE hedge_funds;
ALTER PUBLICATION supabase_realtime ADD TABLE positions;
ALTER PUBLICATION supabase_realtime ADD TABLE transactions;
ALTER PUBLICATION supabase_realtime ADD TABLE performance_metrics;
ALTER PUBLICATION supabase_realtime ADD TABLE operations_log;
```

### Triggers for Real-time Updates
```sql
-- Auto-update timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_hedge_funds_updated_at
    BEFORE UPDATE ON hedge_funds
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_positions_updated_at
    BEFORE UPDATE ON positions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

### Audit Trail Trigger
```sql
CREATE OR REPLACE FUNCTION audit_trigger_function()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        INSERT INTO audit_trail (table_name, record_id, action, old_values, user_id)
        VALUES (TG_TABLE_NAME, OLD.id, TG_OP, to_jsonb(OLD), auth.uid());
        RETURN OLD;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO audit_trail (table_name, record_id, action, old_values, new_values, user_id)
        VALUES (TG_TABLE_NAME, NEW.id, TG_OP, to_jsonb(OLD), to_jsonb(NEW), auth.uid());
        RETURN NEW;
    ELSIF TG_OP = 'INSERT' THEN
        INSERT INTO audit_trail (table_name, record_id, action, new_values, user_id)
        VALUES (TG_TABLE_NAME, NEW.id, TG_OP, to_jsonb(NEW), auth.uid());
        RETURN NEW;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Apply audit triggers
CREATE TRIGGER audit_hedge_funds
    AFTER INSERT OR UPDATE OR DELETE ON hedge_funds
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();

CREATE TRIGGER audit_positions
    AFTER INSERT OR UPDATE OR DELETE ON positions
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();
```

## 📈 Performance Optimization

### Indexes
```sql
-- Performance-critical indexes
CREATE INDEX idx_positions_fund_id ON positions(fund_id);
CREATE INDEX idx_positions_symbol ON positions(symbol);
CREATE INDEX idx_positions_status ON positions(position_status);
CREATE INDEX idx_positions_entry_date ON positions(entry_date);

CREATE INDEX idx_transactions_fund_id ON transactions(fund_id);
CREATE INDEX idx_transactions_date ON transactions(transaction_date);
CREATE INDEX idx_transactions_symbol ON transactions(symbol);

CREATE INDEX idx_performance_metrics_fund_date ON performance_metrics(fund_id, metric_date);
CREATE INDEX idx_risk_metrics_fund_date ON risk_metrics(fund_id, metric_date);

CREATE INDEX idx_operations_log_type_status ON operations_log(operation_type, operation_status);
CREATE INDEX idx_operations_log_created_at ON operations_log(created_at);

-- Partial indexes for active records
CREATE INDEX idx_positions_active ON positions(fund_id, symbol)
    WHERE position_status = 'active';

CREATE INDEX idx_allocations_active ON allocations(fund_id, allocation_type)
    WHERE is_active = TRUE;
```

### Database Connection Pooling
```python
# Python connection pooling example
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    "postgresql://user:password@host:port/database",
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=300
)
```

## 🔧 Data Access Patterns

### Common Queries

#### Get Fund Summary
```sql
SELECT
    fund_name,
    total_capacity,
    utilized_capacity,
    utilization_rate,
    (SELECT COUNT(*) FROM positions WHERE fund_id = hf.id AND position_status = 'active') as active_positions,
    (SELECT nav_per_share FROM performance_metrics
     WHERE fund_id = hf.id
     ORDER BY metric_date DESC LIMIT 1) as current_nav
FROM hedge_funds hf
WHERE id = $1;
```

#### Get Position Details with Performance
```sql
SELECT
    p.*,
    (p.unrealized_pnl / NULLIF(p.cost_basis, 0)) * 100 as return_percentage,
    rm.var_1_day,
    rm.beta,
    rm.volatility_annualized
FROM positions p
LEFT JOIN risk_metrics rm ON p.id = rm.position_id
    AND rm.metric_date = (SELECT MAX(metric_date) FROM risk_metrics WHERE position_id = p.id)
WHERE p.fund_id = $1
    AND p.position_status = 'active'
ORDER BY p.market_value DESC;
```

#### Recent Operations Log
```sql
SELECT
    operation_id,
    operation_type,
    operation_status,
    execution_time,
    cached_response,
    started_at,
    completed_at
FROM operations_log
WHERE fund_id = $1
ORDER BY started_at DESC
LIMIT 50;
```

### Bulk Operations

#### Batch Position Updates
```sql
CREATE OR REPLACE FUNCTION update_position_prices(
    position_updates JSONB
)
RETURNS INTEGER AS $$
DECLARE
    update_count INTEGER := 0;
    position_update JSONB;
BEGIN
    FOR position_update IN SELECT * FROM jsonb_array_elements(position_updates)
    LOOP
        UPDATE positions
        SET
            current_price = (position_update->>'current_price')::DECIMAL,
            last_price_update = NOW(),
            updated_at = NOW()
        WHERE symbol = position_update->>'symbol'
            AND position_status = 'active';

        update_count := update_count + 1;
    END LOOP;

    RETURN update_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

## 🚀 Migration Scripts

### Initial Setup
```sql
-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create custom types
CREATE TYPE operation_type AS ENUM (
    'inception', 'utilization', 'rollover',
    'termination', 'amendment', 'query'
);

CREATE TYPE position_status AS ENUM (
    'active', 'closed', 'pending', 'expired', 'assigned'
);
```

### Sample Data
```sql
-- Insert sample hedge fund
INSERT INTO hedge_funds (
    fund_name, fund_code, total_capacity, inception_date,
    investment_strategy, risk_profile
) VALUES (
    'Alpha Growth Fund', 'AGF001', 100000000.00, '2024-01-01',
    'Long/Short equity strategy focusing on growth companies',
    'moderate'
);

-- Insert sample positions
INSERT INTO positions (
    fund_id, position_code, instrument_type, symbol,
    position_type, quantity, entry_price, current_price, entry_date
) VALUES (
    (SELECT id FROM hedge_funds WHERE fund_code = 'AGF001'),
    'AAPL_001', 'equity', 'AAPL', 'long',
    1000, 150.00, 155.25, CURRENT_DATE
);
```

---

*Last Updated: September 24, 2025*
*Version: 1.0.0*
*Database Version: PostgreSQL 15.1*