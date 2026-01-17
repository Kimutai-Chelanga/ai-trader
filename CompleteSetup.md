# Complete Setup Guide: AI-Trader Enhanced Database

## 🎯 What You're Building

A **relational database** that supports:
- ✅ **Multiple AI agents** (GPT-4, Claude, Qwen, etc.)
- ✅ **Reusable prompts** (strategies that can be shared across agents)
- ✅ **Many-to-many relationships** (3 agents × 4 prompts = 12 combinations)
- ✅ **Individual trade tracking** with full audit trail
- ✅ **Performance metrics** per agent AND per prompt
- ✅ **Alembic migrations** for version-controlled schema changes

## 📦 Files You Need

All files have been created in the artifacts above. Here's the complete structure:

```
ai-trader/
├── alembic_setup.py              # One-time setup script
├── models.py                      # SQLAlchemy models (NEW ENHANCED VERSION)
├── db_helpers.py                  # Python helper functions
├── Dockerfile.alembic             # Docker container for migrations
├── docker-compose.yml             # Updated compose file
├── Makefile                       # 30+ migration commands
├── requirements.alembic.txt       # Python dependencies
├── .env                          # Environment variables
└── alembic/                      # Created by setup script
    ├── env.py
    ├── script.py.mako
    └── versions/                 # Migration files go here
        └── 001_initial_schema.py
```

## 🚀 Step-by-Step Setup

### Step 1: Copy Files

```bash
# Copy all the artifact files to your project
# - models.py (enhanced version with agents, prompts, trades)
# - alembic_setup.py
# - db_helpers.py
# - Dockerfile.alembic
# - docker-compose.yml (updated version)
# - Makefile
# - requirements.alembic.txt
```

### Step 2: Initialize Alembic

```bash
# Run the setup script
python alembic_setup.py

# This creates:
# - alembic.ini
# - alembic/ directory
# - alembic/versions/ directory
```

### Step 3: Start PostgreSQL

```bash
# Start only PostgreSQL first
docker-compose up -d postgres

# Wait for it to be ready
sleep 10
```

### Step 4: Create Initial Migration

```bash
# Auto-generate migration from models.py
make alembic-revision MESSAGE="initial schema with agents and prompts"

# This creates: alembic/versions/YYYYMMDD_HHMM_xxxxx_initial_schema.py
```

### Step 5: Edit Migration File

Open the generated migration file and add the seed data and views:

```python
# Copy the content from the "Initial Data and Views Migration" artifact
# This includes:
# - Database views (latest_positions, portfolio_summary, etc.)
# - Default agents (3 agents)
# - Default prompts (4 prompts)
# - Agent-prompt assignments
# - Default watchlist symbols
```

### Step 6: Apply Migration

```bash
# Apply the migration
make alembic-upgrade

# Verify it worked
make db-shell
# Then in PostgreSQL:
\dt              # List tables
SELECT * FROM agents;
SELECT * FROM prompts;
SELECT * FROM agent_prompts;
\q              # Exit
```

### Step 7: Start All Services

```bash
# Start everything
docker-compose up -d

# Check status
docker-compose ps
```

## 📊 Understanding the Schema

### Tables and Relationships

```
┌─────────────┐
│   agents    │ (stores: gpt4-trader-001, claude-conservative-001, etc.)
└──────┬──────┘
       │
       │ 1:N
       │
┌──────▼──────────┐
│ agent_prompts   │ (links agents to prompts)
│ (Many-to-Many)  │ - Tracks which prompt each agent uses
└──────┬──────────┘ - Records performance per combination
       │
       │ N:1
       │
┌──────▼──────┐
│  prompts    │ (stores: Momentum Trading, Value Investing, etc.)
└─────────────┘


┌─────────────┐
│   agents    │
└──────┬──────┘
       │ 1:N
┌──────▼──────┐
│   trades    │ (every buy/sell action)
└──────┬──────┘ - Links to agent_prompts (which strategy?)
       │        - Stores reasoning, confidence
       │        - Tracks profit/loss
       │
┌──────▼──────┐
│ positions   │ (snapshots of holdings)
└─────────────┘
```

### Example: 3 Agents × 4 Prompts

**Agents:**
1. `gpt4-trader-001` - Aggressive trader
2. `claude-conservative-001` - Conservative trader
3. `qwen-balanced-001` - Balanced trader

**Prompts:**
1. Momentum Trading
2. Value Investing
3. Mean Reversion
4. Risk Management

**Assignments (in agent_prompts):**
- GPT-4: Uses Momentum + Risk Management
- Claude: Uses Value Investing + Risk Management
- Qwen: Uses Mean Reversion + Risk Management

Each agent can use multiple prompts with different priorities!

## 🎮 Using the System

### Option 1: Python Helper Functions

```python
from db_helpers import DatabaseHelper

db = DatabaseHelper()

# Create a new agent
agent = db.create_agent(
    signature='my-custom-agent',
    name='My Custom Trading Bot',
    model_type='gpt-4',
    initial_cash=50000.00
)

# Create a new prompt
prompt = db.create_prompt(
    name='Scalping Strategy',
    prompt_text='You are a scalping trader...',
    prompt_type='trading',
    parameters={'max_trade_duration': 5}
)

# Assign prompt to agent
db.assign_prompt_to_agent(
    agent_signature='my-custom-agent',
    prompt_name='Scalping Strategy',
    priority=1
)

# Record a trade
trade = db.record_trade(
    agent_signature='my-custom-agent',
    symbol='NVDA',
    action='buy',
    quantity=10.0,
    price=450.00,
    reasoning='Strong AI chip demand',
    confidence_score=0.92
)

# Get agent summary
summary = db.get_agent_summary('my-custom-agent')
print(f"Win Rate: {summary['performance']['win_rate']:.2f}%")
print(f"Total P&L: ${summary['performance']['total_profit_loss']:.2f}")
```

### Option 2: Direct SQL

```sql
-- Create an agent
INSERT INTO agents (signature, name, model_type, base_model, initial_cash)
VALUES ('new-agent', 'New Agent', 'claude-3', 'anthropic', 20000.00);

-- Assign a prompt
INSERT INTO agent_prompts (agent_id, prompt_id, priority)
VALUES (
    (SELECT id FROM agents WHERE signature = 'new-agent'),
    (SELECT id FROM prompts WHERE name = 'Momentum Trading'),
    1
);

-- Record a trade
INSERT INTO trades (agent_id, symbol, action, quantity, price, total_value, executed_at, market_date)
VALUES (
    (SELECT id FROM agents WHERE signature = 'new-agent'),
    'AAPL', 'buy', 50, 150.00, 7500.00, NOW(), CURRENT_DATE
);
```

## 📈 Querying Performance

### Agent Performance
```sql
SELECT * FROM agent_performance_summary
ORDER BY total_profit_loss DESC;
```

### Prompt Performance
```sql
SELECT * FROM prompt_performance
ORDER BY total_profit_loss DESC;
```

### Best Agent-Prompt Combinations
```sql
SELECT 
    a.name as agent,
    p.name as prompt,
    ap.total_trades,
    ROUND(ap.successful_trades::numeric / NULLIF(ap.total_trades, 0) * 100, 2) as win_rate,
    ap.total_profit_loss
FROM agent_prompts ap
JOIN agents a ON ap.agent_id = a.id
JOIN prompts p ON ap.prompt_id = p.id
WHERE ap.total_trades > 10
ORDER BY ap.total_profit_loss DESC;
```

## 🔄 Making Schema Changes

### Adding a New Column

```bash
# 1. Edit models.py
# Add to Agent class:
#   risk_level = Column(String(20), default='medium')

# 2. Generate migration
make alembic-revision MESSAGE="add risk_level to agents"

# 3. Review the auto-generated migration
cat alembic/versions/latest_*.py

# 4. Apply it
make alembic-upgrade
```

### Creating a New Table

```bash
# 1. Add new model to models.py
class BacktestResult(Base):
    __tablename__ = 'backtest_results'
    id = Column(Integer, primary_key=True)
    agent_id = Column(Integer, ForeignKey('agents.id'))
    # ... more fields

# 2. Generate migration
make alembic-revision MESSAGE="add backtest_results table"

# 3. Apply
make alembic-upgrade
```

## ❓ FAQ

### Q: What happened to init-db.sql?
**A:** It's replaced by Alembic migrations. Delete it from docker-compose.yml.

### Q: Can I still use my old data?
**A:** Yes! If you have existing data:
```bash
make db-backup  # Backup first
make alembic-stamp REV=head  # Tell Alembic current state is "head"
# Now use Alembic for future changes
```

### Q: How do I add more agents?
**A:** Use the helper functions:
```python
db.create_agent('new-agent-002', 'New Agent', model_type='gpt-4')
```

### Q: How do prompts work with agents?
**A:** Each agent can use multiple prompts. The `agent_prompts` table:
- Links agents to prompts
- Sets priority (which prompt runs first)
- Tracks performance per combination
- Allows custom parameters per agent

### Q: What if a trade uses multiple prompts?
**A:** Link to the primary prompt via `agent_prompt_id` in the trades table. You can also store multiple prompts in the trade's `metadata` JSONB field.

## 🎯 Next Steps

1. **Test the setup:**
   ```bash
   make dev-status
   ```

2. **Create your first custom agent:**
   ```python
   db.create_agent('my-agent', 'My Agent', model_type='gpt-4')
   ```

3. **Integrate with your trading code:**
   - Import `db_helpers.py`
   - Use `db.record_trade()` after each trade
   - Use `db.update_position()` to track holdings

4. **Monitor performance:**
   ```sql
   SELECT * FROM agent_performance_summary;
   SELECT * FROM prompt_performance;
   ```

5. **Iterate on prompts:**
   - Create new versions
   - A/B test different strategies
   - Track which performs best

## 🆘 Troubleshooting

### Problem: Alembic not detecting model changes
```bash
# Make sure models.py is imported in alembic/env.py
# Line should be: from models import Base
```

### Problem: Foreign key errors
```bash
# Check that referenced records exist
# Example: Agent must exist before creating trade
```

### Problem: Migration conflicts
```bash
# Reset and start fresh
make alembic-downgrade-base
make alembic-upgrade
```

## ✅ Verification Checklist

- [ ] PostgreSQL running (`docker-compose ps`)
- [ ] Alembic initialized (`ls alembic/versions/`)
- [ ] Migration applied (`make alembic-current`)
- [ ] Tables created (`make db-shell` then `\dt`)
- [ ] Seed data loaded (`SELECT COUNT(*) FROM agents;`)
- [ ] Views working (`SELECT * FROM agent_performance_summary;`)
- [ ] Helper functions work (run `python db_helpers.py`)

You're now ready to trade with multiple AI agents using different strategies! 🚀