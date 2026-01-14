-- Initialize database schema for AI-Trader and Streamlit Dashboard

-- Create tables for trading positions
CREATE TABLE IF NOT EXISTS positions (
    id SERIAL PRIMARY KEY,
    date TIMESTAMP NOT NULL,
    agent_signature VARCHAR(255) NOT NULL,
    action VARCHAR(50),
    symbol VARCHAR(20),
    amount DECIMAL(20, 8),
    price DECIMAL(20, 8),
    cash_balance DECIMAL(20, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index for faster queries
CREATE INDEX idx_positions_date ON positions(date);
CREATE INDEX idx_positions_agent ON positions(agent_signature);
CREATE INDEX idx_positions_symbol ON positions(symbol);

-- Create table for stock prices
CREATE TABLE IF NOT EXISTS stock_prices (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    date TIMESTAMP NOT NULL,
    open_price DECIMAL(20, 8),
    high_price DECIMAL(20, 8),
    low_price DECIMAL(20, 8),
    close_price DECIMAL(20, 8),
    volume BIGINT,
    market VARCHAR(20) DEFAULT 'us',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, date, market)
);

CREATE INDEX idx_stock_prices_symbol_date ON stock_prices(symbol, date);
CREATE INDEX idx_stock_prices_market ON stock_prices(market);

-- Create table for agent performance metrics
CREATE TABLE IF NOT EXISTS agent_metrics (
    id SERIAL PRIMARY KEY,
    agent_signature VARCHAR(255) NOT NULL,
    date TIMESTAMP NOT NULL,
    total_value DECIMAL(20, 2),
    cash_balance DECIMAL(20, 2),
    portfolio_value DECIMAL(20, 2),
    daily_return DECIMAL(10, 4),
    cumulative_return DECIMAL(10, 4),
    sharpe_ratio DECIMAL(10, 4),
    max_drawdown DECIMAL(10, 4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_agent_metrics_signature_date ON agent_metrics(agent_signature, date);

-- Create table for trading logs
CREATE TABLE IF NOT EXISTS trading_logs (
    id SERIAL PRIMARY KEY,
    agent_signature VARCHAR(255) NOT NULL,
    date TIMESTAMP NOT NULL,
    log_type VARCHAR(50),
    message TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_trading_logs_signature ON trading_logs(agent_signature);
CREATE INDEX idx_trading_logs_date ON trading_logs(date);

-- Create table for watchlist (for Streamlit dashboard)
CREATE TABLE IF NOT EXISTS watchlist (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) DEFAULT 'default',
    symbol VARCHAR(20) NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, symbol)
);

CREATE INDEX idx_watchlist_user ON watchlist(user_id);

-- Create view for latest positions by agent
CREATE OR REPLACE VIEW latest_positions AS
SELECT DISTINCT ON (agent_signature, symbol)
    agent_signature,
    symbol,
    amount,
    price,
    cash_balance,
    date
FROM positions
ORDER BY agent_signature, symbol, date DESC;

-- Create view for portfolio summary
CREATE OR REPLACE VIEW portfolio_summary AS
SELECT 
    p.agent_signature,
    p.date,
    SUM(p.amount * sp.close_price) as portfolio_value,
    p.cash_balance,
    (SUM(p.amount * sp.close_price) + p.cash_balance) as total_value
FROM positions p
LEFT JOIN stock_prices sp ON p.symbol = sp.symbol 
    AND DATE(p.date) = DATE(sp.date)
WHERE p.amount > 0
GROUP BY p.agent_signature, p.date, p.cash_balance;

-- Insert default watchlist symbols
INSERT INTO watchlist (symbol) VALUES 
    ('AAPL'),
    ('GOOGL'),
    ('AMZN'),
    ('MSFT')
ON CONFLICT (user_id, symbol) DO NOTHING;

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO aitrader;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO aitrader;