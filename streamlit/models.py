# models.py - SQLAlchemy models for AI-Trader with proper relationships

from sqlalchemy import (
    Column, Integer, String, Numeric, BigInteger, 
    TIMESTAMP, Boolean, Text, ForeignKey, text, Index, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()


# ============================================================
# Core Agent Management
# ============================================================

class Agent(Base):
    """
    Trading agents - each agent represents a unique trading strategy/model
    """
    __tablename__ = 'agents'
    
    id = Column(Integer, primary_key=True)
    signature = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    model_type = Column(String(100))  # e.g., 'gpt-4', 'claude-3', 'qwen'
    base_model = Column(String(100))  # e.g., 'openai', 'anthropic'
    initial_cash = Column(Numeric(20, 2), default=10000.00)
    status = Column(String(50), default='active')  # active, paused, stopped
    created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    updated_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'), onupdate=text('CURRENT_TIMESTAMP'))
    
    # Relationships
    positions = relationship("Position", back_populates="agent", cascade="all, delete-orphan")
    trades = relationship("Trade", back_populates="agent", cascade="all, delete-orphan")
    metrics = relationship("AgentMetric", back_populates="agent", cascade="all, delete-orphan")
    logs = relationship("TradingLog", back_populates="agent", cascade="all, delete-orphan")
    agent_prompts = relationship("AgentPrompt", back_populates="agent", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_agents_status', 'status'),
        Index('idx_agents_model_type', 'model_type'),
    )
    
    def __repr__(self):
        return f"<Agent(signature='{self.signature}', name='{self.name}')>"


# ============================================================
# Prompt Management
# ============================================================

class Prompt(Base):
    """
    Trading prompts/strategies - reusable prompts that can be assigned to multiple agents
    """
    __tablename__ = 'prompts'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    prompt_text = Column(Text, nullable=False)
    prompt_type = Column(String(50), default='trading')  # trading, analysis, risk_management
    version = Column(String(50), default='1.0')
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    updated_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'), onupdate=text('CURRENT_TIMESTAMP'))
    
    # Parameters/config for this prompt (stored as JSON)
    parameters = Column(JSONB, default={})
    
    # Relationships
    agent_prompts = relationship("AgentPrompt", back_populates="prompt", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_prompts_type', 'prompt_type'),
        Index('idx_prompts_active', 'is_active'),
        UniqueConstraint('name', 'version', name='uq_prompt_name_version'),
    )
    
    def __repr__(self):
        return f"<Prompt(name='{self.name}', version='{self.version}')>"


# ============================================================
# Agent-Prompt Association (Many-to-Many)
# ============================================================

class AgentPrompt(Base):
    """
    Association table: Links agents to prompts with additional metadata
    This allows each agent to use multiple prompts and each prompt to be used by multiple agents
    """
    __tablename__ = 'agent_prompts'
    
    id = Column(Integer, primary_key=True)
    agent_id = Column(Integer, ForeignKey('agents.id', ondelete='CASCADE'), nullable=False)
    prompt_id = Column(Integer, ForeignKey('prompts.id', ondelete='CASCADE'), nullable=False)
    
    # When this prompt was assigned to this agent
    assigned_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    
    # Is this prompt currently active for this agent?
    is_active = Column(Boolean, default=True)
    
    # Priority/order if agent uses multiple prompts (lower = higher priority)
    priority = Column(Integer, default=0)
    
    # Agent-specific overrides for prompt parameters
    custom_parameters = Column(JSONB, default={})
    
    # Performance tracking for this specific agent-prompt combination
    total_trades = Column(Integer, default=0)
    successful_trades = Column(Integer, default=0)
    total_profit_loss = Column(Numeric(20, 2), default=0.00)
    
    # Relationships
    agent = relationship("Agent", back_populates="agent_prompts")
    prompt = relationship("Prompt", back_populates="agent_prompts")
    
    __table_args__ = (
        Index('idx_agent_prompts_agent', 'agent_id'),
        Index('idx_agent_prompts_prompt', 'prompt_id'),
        Index('idx_agent_prompts_active', 'is_active'),
        UniqueConstraint('agent_id', 'prompt_id', name='uq_agent_prompt'),
    )
    
    def __repr__(self):
        return f"<AgentPrompt(agent_id={self.agent_id}, prompt_id={self.prompt_id})>"


# ============================================================
# Trading Data
# ============================================================

class Trade(Base):
    """
    Individual trades - each buy/sell action is recorded here
    This is different from positions which track overall holdings
    """
    __tablename__ = 'trades'
    
    id = Column(Integer, primary_key=True)
    trade_uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    
    # Foreign keys
    agent_id = Column(Integer, ForeignKey('agents.id', ondelete='CASCADE'), nullable=False)
    agent_prompt_id = Column(Integer, ForeignKey('agent_prompts.id', ondelete='SET NULL'), nullable=True)
    
    # Trade details
    symbol = Column(String(20), nullable=False, index=True)
    action = Column(String(10), nullable=False)  # 'buy' or 'sell'
    quantity = Column(Numeric(20, 8), nullable=False)
    price = Column(Numeric(20, 8), nullable=False)
    total_value = Column(Numeric(20, 2), nullable=False)  # quantity * price
    
    # Timing
    executed_at = Column(TIMESTAMP, nullable=False, index=True)
    market_date = Column(TIMESTAMP, nullable=False)  # The trading day this belongs to
    
    # Trading context
    cash_before = Column(Numeric(20, 2))
    cash_after = Column(Numeric(20, 2))
    portfolio_value_before = Column(Numeric(20, 2))
    portfolio_value_after = Column(Numeric(20, 2))
    
    # AI decision details
    reasoning = Column(Text)  # Why the AI made this trade
    confidence_score = Column(Numeric(5, 4))  # 0.0 to 1.0
    
    # Fees and costs
    commission = Column(Numeric(20, 2), default=0.00)
    slippage = Column(Numeric(20, 8), default=0.00)
    
    # Trade outcome (filled in later when position is closed)
    profit_loss = Column(Numeric(20, 2))
    profit_loss_percentage = Column(Numeric(10, 4))
    is_profitable = Column(Boolean)
    
    # Status
    status = Column(String(20), default='executed')  # executed, cancelled, failed
    
    # Metadata - FIXED: renamed from 'metadata' to 'trade_metadata'
    trade_metadata = Column(JSONB, default={})
    created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    
    # Relationships
    agent = relationship("Agent", back_populates="trades")
    agent_prompt = relationship("AgentPrompt")
    
    __table_args__ = (
        Index('idx_trades_agent', 'agent_id'),
        Index('idx_trades_symbol', 'symbol'),
        Index('idx_trades_action', 'action'),
        Index('idx_trades_executed_at', 'executed_at'),
        Index('idx_trades_market_date', 'market_date'),
        Index('idx_trades_status', 'status'),
    )
    
    def __repr__(self):
        return f"<Trade(agent_id={self.agent_id}, {self.action} {self.quantity} {self.symbol} @ {self.price})>"


class Position(Base):
    """
    Current and historical positions - snapshot of agent holdings at a point in time
    """
    __tablename__ = 'positions'
    
    id = Column(Integer, primary_key=True)
    agent_id = Column(Integer, ForeignKey('agents.id', ondelete='CASCADE'), nullable=False)
    date = Column(TIMESTAMP, nullable=False, index=True)
    
    # Position details
    symbol = Column(String(20), index=True)
    action = Column(String(50))  # Latest action that affected this position
    amount = Column(Numeric(20, 8))  # Current quantity held
    average_price = Column(Numeric(20, 8))  # Average cost basis
    current_price = Column(Numeric(20, 8))  # Current market price
    
    # Portfolio state
    cash_balance = Column(Numeric(20, 2))
    total_value = Column(Numeric(20, 2))  # cash + all positions value
    
    created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    
    # Relationships
    agent = relationship("Agent", back_populates="positions")
    
    __table_args__ = (
        Index('idx_positions_agent', 'agent_id'),
        Index('idx_positions_date', 'date'),
        Index('idx_positions_symbol', 'symbol'),
        Index('idx_positions_agent_date', 'agent_id', 'date'),
    )
    
    def __repr__(self):
        return f"<Position(agent_id={self.agent_id}, symbol='{self.symbol}', amount={self.amount})>"


# ============================================================
# Market Data
# ============================================================

class StockPrice(Base):
    """
    Historical stock price data
    """
    __tablename__ = 'stock_prices'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), nullable=False, index=True)
    date = Column(TIMESTAMP, nullable=False, index=True)
    
    open_price = Column(Numeric(20, 8))
    high_price = Column(Numeric(20, 8))
    low_price = Column(Numeric(20, 8))
    close_price = Column(Numeric(20, 8))
    volume = Column(BigInteger)
    
    market = Column(String(20), server_default=text("'us'"), index=True)
    created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    
    __table_args__ = (
        Index('idx_stock_prices_symbol_date', 'symbol', 'date'),
        Index('idx_stock_prices_market', 'market'),
        UniqueConstraint('symbol', 'date', 'market', name='uq_stock_price'),
    )
    
    def __repr__(self):
        return f"<StockPrice(symbol='{self.symbol}', date='{self.date}', close={self.close_price})>"


# ============================================================
# Performance Metrics
# ============================================================

class AgentMetric(Base):
    """
    Daily/periodic performance metrics for each agent
    """
    __tablename__ = 'agent_metrics'
    
    id = Column(Integer, primary_key=True)
    agent_id = Column(Integer, ForeignKey('agents.id', ondelete='CASCADE'), nullable=False)
    date = Column(TIMESTAMP, nullable=False, index=True)
    
    # Portfolio values
    total_value = Column(Numeric(20, 2))
    cash_balance = Column(Numeric(20, 2))
    portfolio_value = Column(Numeric(20, 2))
    
    # Returns
    daily_return = Column(Numeric(10, 4))
    cumulative_return = Column(Numeric(10, 4))
    
    # Risk metrics
    sharpe_ratio = Column(Numeric(10, 4))
    max_drawdown = Column(Numeric(10, 4))
    volatility = Column(Numeric(10, 4))
    
    # Trading activity
    trades_count = Column(Integer, default=0)
    win_rate = Column(Numeric(5, 4))  # Percentage of profitable trades
    
    created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    
    # Relationships
    agent = relationship("Agent", back_populates="metrics")
    
    __table_args__ = (
        Index('idx_agent_metrics_agent', 'agent_id'),
        Index('idx_agent_metrics_date', 'date'),
        Index('idx_agent_metrics_agent_date', 'agent_id', 'date'),
    )
    
    def __repr__(self):
        return f"<AgentMetric(agent_id={self.agent_id}, date='{self.date}', return={self.daily_return})>"


# ============================================================
# Logging and Audit
# ============================================================

class TradingLog(Base):
    """
    Detailed logs of agent actions and system events
    """
    __tablename__ = 'trading_logs'
    
    id = Column(Integer, primary_key=True)
    agent_id = Column(Integer, ForeignKey('agents.id', ondelete='CASCADE'), nullable=False)
    date = Column(TIMESTAMP, nullable=False, index=True)
    
    log_type = Column(String(50), index=True)  # info, warning, error, trade, decision
    message = Column(Text)
    log_metadata = Column(JSONB, default={})  # FIXED: renamed from 'metadata' to 'log_metadata'
    
    created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    
    # Relationships
    agent = relationship("Agent", back_populates="logs")
    
    __table_args__ = (
        Index('idx_trading_logs_agent', 'agent_id'),
        Index('idx_trading_logs_date', 'date'),
        Index('idx_trading_logs_type', 'log_type'),
    )
    
    def __repr__(self):
        return f"<TradingLog(agent_id={self.agent_id}, type='{self.log_type}')>"


# ============================================================
# User Features
# ============================================================

class Watchlist(Base):
    """
    User watchlists for monitoring specific stocks
    """
    __tablename__ = 'watchlist'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(100), server_default=text("'default'"), index=True)
    symbol = Column(String(20), nullable=False)
    added_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    
    # Additional metadata
    notes = Column(Text)
    alert_price = Column(Numeric(20, 8))  # Alert when price reaches this level
    
    __table_args__ = (
        Index('idx_watchlist_user', 'user_id'),
        UniqueConstraint('user_id', 'symbol', name='uq_watchlist_user_symbol'),
    )
    
    def __repr__(self):
        return f"<Watchlist(user_id='{self.user_id}', symbol='{self.symbol}')>"