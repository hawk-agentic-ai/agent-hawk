-- Complete database schema for hedge agent optimization
-- Run this in your Supabase SQL editor

-- Portfolio positions table
CREATE TABLE IF NOT EXISTS portfolio_positions (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    quantity DECIMAL(15, 4) NOT NULL,
    entry_price DECIMAL(15, 4) NOT NULL,
    current_price DECIMAL(15, 4),
    market_value DECIMAL(15, 2),
    unrealized_pnl DECIMAL(15, 2),
    sector VARCHAR(50),
    asset_type VARCHAR(30),
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Trade history table  
CREATE TABLE IF NOT EXISTS trade_history (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL, -- 'buy' or 'sell'
    quantity DECIMAL(15, 4) NOT NULL,
    price DECIMAL(15, 4) NOT NULL,
    total_value DECIMAL(15, 2),
    pnl DECIMAL(15, 2),
    commission DECIMAL(10, 2),
    trade_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    strategy VARCHAR(50),
    notes TEXT
);

-- Risk metrics table
CREATE TABLE IF NOT EXISTS risk_metrics (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    portfolio_value DECIMAL(15, 2),
    var_95 DECIMAL(15, 2), -- Value at Risk 95%
    var_99 DECIMAL(15, 2), -- Value at Risk 99%
    beta DECIMAL(8, 4),
    sharpe_ratio DECIMAL(8, 4),
    max_drawdown DECIMAL(8, 4),
    volatility DECIMAL(8, 4),
    correlation_spy DECIMAL(8, 4),
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Market data table
CREATE TABLE IF NOT EXISTS market_data (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    price DECIMAL(15, 4),
    change_pct DECIMAL(8, 4),
    volume BIGINT,
    market_cap BIGINT,
    pe_ratio DECIMAL(8, 2),
    sector VARCHAR(50),
    industry VARCHAR(100),
    active BOOLEAN DEFAULT true,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Prompt templates table (enhanced)
CREATE TABLE IF NOT EXISTS prompt_templates (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    category VARCHAR(50),
    template TEXT NOT NULL,
    variables JSONB,
    use_hedge_context BOOLEAN DEFAULT false,
    performance_rating INTEGER DEFAULT 0,
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Performance analytics table
CREATE TABLE IF NOT EXISTS performance_analytics (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    query_text TEXT,
    response_time_ms INTEGER,
    cache_hit BOOLEAN DEFAULT false,
    parallel_queries INTEGER DEFAULT 0,
    context_used BOOLEAN DEFAULT false,
    satisfaction_score INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_portfolio_positions_user_id ON portfolio_positions(user_id);
CREATE INDEX IF NOT EXISTS idx_portfolio_positions_status ON portfolio_positions(status);
CREATE INDEX IF NOT EXISTS idx_trade_history_user_id ON trade_history(user_id);
CREATE INDEX IF NOT EXISTS idx_trade_history_date ON trade_history(trade_date);
CREATE INDEX IF NOT EXISTS idx_risk_metrics_user_id ON risk_metrics(user_id);
CREATE INDEX IF NOT EXISTS idx_market_data_symbol ON market_data(symbol);
CREATE INDEX IF NOT EXISTS idx_market_data_active ON market_data(active);

-- Insert sample data for testing
INSERT INTO prompt_templates (name, category, template, variables, use_hedge_context) VALUES
('Portfolio Analysis', 'analysis', 'Analyze my current portfolio performance and provide insights on {metric}', '{"metric": "risk"}', true),
('Risk Assessment', 'risk', 'What is my current risk exposure in {sector}?', '{"sector": "technology"}', true),
('Trading Strategy', 'strategy', 'Suggest hedging strategies for my {asset_type} positions', '{"asset_type": "equity"}', true),
('Market Outlook', 'market', 'What is the market outlook for {timeframe}?', '{"timeframe": "next quarter"}', false),
('Performance Review', 'analysis', 'Review my trading performance over {period}', '{"period": "last month"}', true);

-- Insert sample portfolio data
INSERT INTO portfolio_positions (user_id, symbol, quantity, entry_price, current_price, market_value, sector, asset_type) VALUES
('default', 'AAPL', 100, 150.00, 175.50, 17550.00, 'Technology', 'equity'),
('default', 'MSFT', 50, 300.00, 330.00, 16500.00, 'Technology', 'equity'),
('default', 'TSLA', 25, 800.00, 750.00, 18750.00, 'Automotive', 'equity'),
('default', 'SPY', -10, 400.00, 420.00, -4200.00, 'Index', 'etf'),
('default', 'QQQ', -5, 350.00, 380.00, -1900.00, 'Technology', 'etf');

-- Insert sample trade history
INSERT INTO trade_history (user_id, symbol, side, quantity, price, total_value, pnl) VALUES
('default', 'AAPL', 'buy', 100, 150.00, 15000.00, 2550.00),
('default', 'MSFT', 'buy', 50, 300.00, 15000.00, 1500.00),
('default', 'TSLA', 'sell', 25, 800.00, 20000.00, -1250.00),
('default', 'SPY', 'sell', 10, 400.00, 4000.00, 200.00);

-- Insert sample market data
INSERT INTO market_data (symbol, price, change_pct, volume, sector) VALUES
('AAPL', 175.50, 2.3, 50000000, 'Technology'),
('MSFT', 330.00, 1.8, 35000000, 'Technology'),
('TSLA', 750.00, -1.2, 45000000, 'Automotive'),
('SPY', 420.00, 0.8, 80000000, 'Index'),
('QQQ', 380.00, 1.5, 60000000, 'Technology');

-- Grant permissions (adjust as needed for your setup)
-- ALTER TABLE portfolio_positions ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE trade_history ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE risk_metrics ENABLE ROW LEVEL SECURITY;