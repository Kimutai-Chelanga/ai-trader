"""Initial schema with agents, prompts, and views

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-01-17 12:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create agents table
    op.create_table('agents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('signature', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('model_type', sa.String(length=100), nullable=True),
        sa.Column('base_model', sa.String(length=100), nullable=True),
        sa.Column('initial_cash', sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('signature')
    )
    op.create_index('idx_agents_model_type', 'agents', ['model_type'])
    op.create_index('idx_agents_status', 'agents', ['status'])
    op.create_index(op.f('ix_agents_signature'), 'agents', ['signature'])

    # Create prompts table
    op.create_table('prompts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('prompt_text', sa.Text(), nullable=False),
        sa.Column('prompt_type', sa.String(length=50), nullable=True),
        sa.Column('version', sa.String(length=50), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('parameters', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', 'version', name='uq_prompt_name_version')
    )
    op.create_index('idx_prompts_active', 'prompts', ['is_active'])
    op.create_index('idx_prompts_type', 'prompts', ['prompt_type'])

    # Create stock_prices table
    op.create_table('stock_prices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('date', sa.TIMESTAMP(), nullable=False),
        sa.Column('open_price', sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column('high_price', sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column('low_price', sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column('close_price', sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column('volume', sa.BigInteger(), nullable=True),
        sa.Column('market', sa.String(length=20), server_default=sa.text("'us'"), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('symbol', 'date', 'market', name='uq_stock_price')
    )
    op.create_index('idx_stock_prices_market', 'stock_prices', ['market'])
    op.create_index('idx_stock_prices_symbol_date', 'stock_prices', ['symbol', 'date'])
    op.create_index(op.f('ix_stock_prices_date'), 'stock_prices', ['date'])
    op.create_index(op.f('ix_stock_prices_symbol'), 'stock_prices', ['symbol'])

    # Create watchlist table
    op.create_table('watchlist',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(length=100), server_default=sa.text("'default'"), nullable=True),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('added_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('alert_price', sa.Numeric(precision=20, scale=8), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'symbol', name='uq_watchlist_user_symbol')
    )
    op.create_index('idx_watchlist_user', 'watchlist', ['user_id'])

    # Create agent_prompts table (many-to-many relationship)
    op.create_table('agent_prompts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('agent_id', sa.Integer(), nullable=False),
        sa.Column('prompt_id', sa.Integer(), nullable=False),
        sa.Column('assigned_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('priority', sa.Integer(), nullable=True),
        sa.Column('custom_parameters', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('total_trades', sa.Integer(), nullable=True),
        sa.Column('successful_trades', sa.Integer(), nullable=True),
        sa.Column('total_profit_loss', sa.Numeric(precision=20, scale=2), nullable=True),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['prompt_id'], ['prompts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('agent_id', 'prompt_id', name='uq_agent_prompt')
    )
    op.create_index('idx_agent_prompts_active', 'agent_prompts', ['is_active'])
    op.create_index('idx_agent_prompts_agent', 'agent_prompts', ['agent_id'])
    op.create_index('idx_agent_prompts_prompt', 'agent_prompts', ['prompt_id'])

    # Create agent_metrics table
    op.create_table('agent_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('agent_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.TIMESTAMP(), nullable=False),
        sa.Column('total_value', sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column('cash_balance', sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column('portfolio_value', sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column('daily_return', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('cumulative_return', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('sharpe_ratio', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('max_drawdown', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('volatility', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('trades_count', sa.Integer(), nullable=True),
        sa.Column('win_rate', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_agent_metrics_agent', 'agent_metrics', ['agent_id'])
    op.create_index('idx_agent_metrics_agent_date', 'agent_metrics', ['agent_id', 'date'])
    op.create_index('idx_agent_metrics_date', 'agent_metrics', ['date'])

    # Create positions table
    op.create_table('positions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('agent_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.TIMESTAMP(), nullable=False),
        sa.Column('symbol', sa.String(length=20), nullable=True),
        sa.Column('action', sa.String(length=50), nullable=True),
        sa.Column('amount', sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column('average_price', sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column('current_price', sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column('cash_balance', sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column('total_value', sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_positions_agent', 'positions', ['agent_id'])
    op.create_index('idx_positions_agent_date', 'positions', ['agent_id', 'date'])
    op.create_index('idx_positions_date', 'positions', ['date'])
    op.create_index('idx_positions_symbol', 'positions', ['symbol'])

    # Create trading_logs table
    op.create_table('trading_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('agent_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.TIMESTAMP(), nullable=False),
        sa.Column('log_type', sa.String(length=50), nullable=True),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_trading_logs_agent', 'trading_logs', ['agent_id'])
    op.create_index('idx_trading_logs_date', 'trading_logs', ['date'])
    op.create_index('idx_trading_logs_type', 'trading_logs', ['log_type'])

    # Create trades table
    op.create_table('trades',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('trade_uuid', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_id', sa.Integer(), nullable=False),
        sa.Column('agent_prompt_id', sa.Integer(), nullable=True),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('action', sa.String(length=10), nullable=False),
        sa.Column('quantity', sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column('price', sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column('total_value', sa.Numeric(precision=20, scale=2), nullable=False),
        sa.Column('executed_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('market_date', sa.TIMESTAMP(), nullable=False),
        sa.Column('cash_before', sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column('cash_after', sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column('portfolio_value_before', sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column('portfolio_value_after', sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column('reasoning', sa.Text(), nullable=True),
        sa.Column('confidence_score', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('commission', sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column('slippage', sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column('profit_loss', sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column('profit_loss_percentage', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('is_profitable', sa.Boolean(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['agent_prompt_id'], ['agent_prompts.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('trade_uuid')
    )
    op.create_index('idx_trades_action', 'trades', ['action'])
    op.create_index('idx_trades_agent', 'trades', ['agent_id'])
    op.create_index('idx_trades_executed_at', 'trades', ['executed_at'])
    op.create_index('idx_trades_market_date', 'trades', ['market_date'])
    op.create_index('idx_trades_status', 'trades', ['status'])
    op.create_index('idx_trades_symbol', 'trades', ['symbol'])

    # Create database views
    op.execute("""
        CREATE OR REPLACE VIEW latest_positions AS
        SELECT DISTINCT ON (a.signature, p.symbol)
            a.id as agent_id,
            a.signature as agent_signature,
            a.name as agent_name,
            p.symbol,
            p.amount,
            p.current_price as price,
            p.average_price,
            p.cash_balance,
            p.total_value,
            p.date
        FROM positions p
        JOIN agents a ON p.agent_id = a.id
        WHERE p.amount > 0
        ORDER BY a.signature, p.symbol, p.date DESC
    """)
    
    op.execute("""
        CREATE OR REPLACE VIEW portfolio_summary AS
        SELECT 
            a.id as agent_id,
            a.signature as agent_signature,
            a.name as agent_name,
            p.date,
            SUM(p.amount * sp.close_price) as portfolio_value,
            p.cash_balance,
            (SUM(p.amount * sp.close_price) + p.cash_balance) as total_value
        FROM positions p
        JOIN agents a ON p.agent_id = a.id
        LEFT JOIN stock_prices sp ON p.symbol = sp.symbol 
            AND DATE(p.date) = DATE(sp.date)
        WHERE p.amount > 0
        GROUP BY a.id, a.signature, a.name, p.date, p.cash_balance
    """)
    
    op.execute("""
        CREATE OR REPLACE VIEW agent_performance_summary AS
        SELECT 
            a.id,
            a.signature,
            a.name,
            a.status,
            COUNT(DISTINCT t.id) as total_trades,
            COUNT(DISTINCT CASE WHEN t.is_profitable = true THEN t.id END) as winning_trades,
            ROUND(
                COUNT(DISTINCT CASE WHEN t.is_profitable = true THEN t.id END)::numeric / 
                NULLIF(COUNT(DISTINCT t.id), 0) * 100, 
                2
            ) as win_rate_percentage,
            SUM(t.profit_loss) as total_profit_loss,
            MAX(m.total_value) as peak_value,
            MIN(m.max_drawdown) as worst_drawdown,
            AVG(m.sharpe_ratio) as avg_sharpe_ratio,
            COUNT(DISTINCT ap.prompt_id) as prompts_used
        FROM agents a
        LEFT JOIN trades t ON a.id = t.agent_id
        LEFT JOIN agent_metrics m ON a.id = m.agent_id
        LEFT JOIN agent_prompts ap ON a.id = ap.agent_id AND ap.is_active = true
        GROUP BY a.id, a.signature, a.name, a.status
    """)
    
    op.execute("""
        CREATE OR REPLACE VIEW prompt_performance AS
        SELECT 
            p.id as prompt_id,
            p.name as prompt_name,
            p.version,
            COUNT(DISTINCT ap.agent_id) as agents_using,
            SUM(ap.total_trades) as total_trades,
            SUM(ap.successful_trades) as successful_trades,
            ROUND(
                SUM(ap.successful_trades)::numeric / 
                NULLIF(SUM(ap.total_trades), 0) * 100, 
                2
            ) as success_rate_percentage,
            SUM(ap.total_profit_loss) as total_profit_loss,
            AVG(ap.total_profit_loss) as avg_profit_loss_per_agent
        FROM prompts p
        LEFT JOIN agent_prompts ap ON p.id = ap.prompt_id
        WHERE p.is_active = true
        GROUP BY p.id, p.name, p.version
    """)
    
    # Insert seed data - Default agents
    op.execute("""
        INSERT INTO agents (signature, name, description, model_type, base_model, initial_cash, status)
        VALUES 
            ('gpt4-trader-001', 'GPT-4 Aggressive Trader', 'High-frequency trading agent using GPT-4', 'gpt-4', 'openai', 10000.00, 'active'),
            ('claude-conservative-001', 'Claude Conservative', 'Risk-averse long-term strategy', 'claude-3-opus', 'anthropic', 10000.00, 'active'),
            ('qwen-balanced-001', 'Qwen Balanced', 'Balanced risk-reward approach', 'qwen-max', 'qwen', 10000.00, 'active')
    """)
    
    # Insert seed data - Default prompts
    op.execute("""
        INSERT INTO prompts (name, description, prompt_text, prompt_type, version, is_active, parameters)
        VALUES 
            (
                'Momentum Trading',
                'Focus on stocks with strong upward momentum',
                'You are a momentum trader. Analyze price trends and trading volume. Buy stocks showing strong upward momentum with increasing volume. Sell when momentum weakens. Focus on short to medium-term gains.',
                'trading',
                '1.0',
                true,
                '{"max_holding_period": 30, "momentum_threshold": 0.05}'::jsonb
            ),
            (
                'Value Investing',
                'Long-term value-based investment strategy',
                'You are a value investor. Look for undervalued stocks with strong fundamentals. Consider P/E ratios, debt levels, and growth potential. Hold positions for long-term appreciation. Focus on quality over quick gains.',
                'trading',
                '1.0',
                true,
                '{"min_holding_period": 90, "max_pe_ratio": 15}'::jsonb
            ),
            (
                'Mean Reversion',
                'Trade based on mean reversion principles',
                'You are a mean reversion trader. Identify stocks that have deviated significantly from their historical averages. Buy oversold stocks, sell overbought ones. Use statistical indicators to time entries and exits.',
                'trading',
                '1.0',
                true,
                '{"lookback_period": 20, "std_threshold": 2.0}'::jsonb
            ),
            (
                'Risk Management',
                'Conservative risk management overlay',
                'Focus on capital preservation. Implement strict stop-losses at 5% below purchase price. Never allocate more than 10% of portfolio to a single position. Diversify across at least 5 different stocks.',
                'risk_management',
                '1.0',
                true,
                '{"stop_loss_percentage": 0.05, "max_position_size": 0.10, "min_diversification": 5}'::jsonb
            )
    """)
    
    # Assign prompts to agents
    op.execute("""
        WITH agent_ids AS (
            SELECT id, signature FROM agents WHERE signature IN ('gpt4-trader-001', 'claude-conservative-001', 'qwen-balanced-001')
        ),
        prompt_ids AS (
            SELECT id, name FROM prompts WHERE name IN ('Momentum Trading', 'Value Investing', 'Mean Reversion', 'Risk Management')
        )
        INSERT INTO agent_prompts (agent_id, prompt_id, is_active, priority, total_trades, successful_trades, total_profit_loss)
        SELECT 
            a.id, 
            p.id,
            true,
            CASE 
                WHEN a.signature = 'gpt4-trader-001' AND p.name = 'Momentum Trading' THEN 1
                WHEN a.signature = 'gpt4-trader-001' AND p.name = 'Risk Management' THEN 2
                WHEN a.signature = 'claude-conservative-001' AND p.name = 'Value Investing' THEN 1
                WHEN a.signature = 'claude-conservative-001' AND p.name = 'Risk Management' THEN 2
                WHEN a.signature = 'qwen-balanced-001' AND p.name = 'Mean Reversion' THEN 1
                WHEN a.signature = 'qwen-balanced-001' AND p.name = 'Risk Management' THEN 2
                ELSE 99
            END,
            0,
            0,
            0.00
        FROM agent_ids a
        CROSS JOIN prompt_ids p
        WHERE 
            (a.signature = 'gpt4-trader-001' AND p.name IN ('Momentum Trading', 'Risk Management'))
            OR (a.signature = 'claude-conservative-001' AND p.name IN ('Value Investing', 'Risk Management'))
            OR (a.signature = 'qwen-balanced-001' AND p.name IN ('Mean Reversion', 'Risk Management'))
    """)
    
    # Insert default watchlist symbols
    op.execute("""
        INSERT INTO watchlist (user_id, symbol, notes)
        VALUES 
            ('default', 'AAPL', 'Apple Inc.'),
            ('default', 'GOOGL', 'Alphabet Inc.'),
            ('default', 'AMZN', 'Amazon.com Inc.'),
            ('default', 'MSFT', 'Microsoft Corporation'),
            ('default', 'NVDA', 'NVIDIA Corporation'),
            ('default', 'META', 'Meta Platforms Inc.'),
            ('default', 'TSLA', 'Tesla Inc.')
    """)


def downgrade() -> None:
    # Drop views
    op.execute("DROP VIEW IF EXISTS prompt_performance")
    op.execute("DROP VIEW IF EXISTS agent_performance_summary")
    op.execute("DROP VIEW IF EXISTS portfolio_summary")
    op.execute("DROP VIEW IF EXISTS latest_positions")
    
    # Drop tables in reverse order
    op.drop_table('trades')
    op.drop_table('trading_logs')
    op.drop_table('positions')
    op.drop_table('agent_metrics')
    op.drop_table('agent_prompts')
    op.drop_table('watchlist')
    op.drop_table('stock_prices')
    op.drop_table('prompts')
    op.drop_table('agents')
