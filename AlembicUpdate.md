Great question! Let me guide you through what happens next and how to manage your database schema.

## 🎉 Once It Starts Successfully

**1. Verify Everything is Running:**
```bash
# Check container status
docker-compose ps

# You should see all services as "running" or "exited with code 0" (alembic)
```

**2. Access Your Services:**
- **Streamlit Dashboard**: http://localhost:8501
- **Documentation UI**: http://localhost:8888
- **PostgreSQL**: localhost:5432

**3. Verify Database Schema:**
```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U postgres -d trading_db

# Inside psql, run:
\dt                           # List all tables
\d agents                     # Describe agents table
SELECT * FROM agents;         # View seed data
SELECT * FROM prompts;        # View default strategies
\dv                           # List views
\q                            # Exit
```

---

## 🔧 How to Change/Update Schema

### Method 1: Create a New Migration (Recommended)

**Step 1: Modify `models.py`**

Let's say you want to add a new field to the `Agent` model:

```python
# In models.py, add to the Agent class:
class Agent(Base):
    __tablename__ = 'agents'
    
    # ... existing fields ...
    risk_tolerance = Column(String(20), default='medium')  # NEW FIELD
    max_position_size = Column(Numeric(5, 2), default=0.10)  # NEW FIELD
```

**Step 2: Generate Migration**

```bash
# Method A: Using docker-compose
docker-compose run --rm alembic alembic revision --autogenerate -m "add risk fields to agents"

# Method B: If alembic is installed locally
alembic revision --autogenerate -m "add risk fields to agents"
```

This creates a new file in `alembic/versions/` like `002_add_risk_fields_to_agents.py`

**Step 3: Review the Migration**

```bash
# Check what was generated
cat alembic/versions/002_*.py
```

The file will look like:
```python
def upgrade() -> None:
    op.add_column('agents', sa.Column('risk_tolerance', sa.String(length=20), nullable=True))
    op.add_column('agents', sa.Column('max_position_size', sa.Numeric(precision=5, scale=2), nullable=True))

def downgrade() -> None:
    op.drop_column('agents', 'max_position_size')
    op.drop_column('agents', 'risk_tolerance')
```

**Step 4: Apply Migration**

```bash
# Apply the migration
docker-compose run --rm alembic alembic upgrade head

# Or restart the alembic service
docker-compose up alembic
```

**Step 5: Verify**

```bash
docker-compose exec postgres psql -U postgres -d trading_db -c "\d agents"
```

---

### Method 2: Manual Migration

**Create a migration file manually:**

```bash
# Generate empty migration
docker-compose run --rm alembic alembic revision -m "add custom feature"

# This creates: alembic/versions/XXXXXX_add_custom_feature.py
```

**Edit the file:**

```python
"""add custom feature

Revision ID: 002_custom
Revises: 001_initial_schema
Create Date: 2026-01-17

"""
from alembic import op
import sqlalchemy as sa

revision = '002_custom'
down_revision = '001_initial_schema'

def upgrade() -> None:
    # Add a new table
    op.create_table(
        'market_news',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(20), nullable=False),
        sa.Column('headline', sa.Text(), nullable=True),
        sa.Column('sentiment', sa.String(20), nullable=True),
        sa.Column('published_at', sa.TIMESTAMP(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Add an index
    op.create_index('idx_news_symbol', 'market_news', ['symbol'])

def downgrade() -> None:
    op.drop_index('idx_news_symbol')
    op.drop_table('market_news')
```

**Apply it:**
```bash
docker-compose run --rm alembic alembic upgrade head
```

---

## 📋 Common Schema Changes

### 1. Add a Column
```python
def upgrade():
    op.add_column('agents', sa.Column('email', sa.String(255)))

def downgrade():
    op.drop_column('agents', 'email')
```

### 2. Modify a Column
```python
def upgrade():
    # Change column type
    op.alter_column('agents', 'initial_cash',
                    type_=sa.Numeric(30, 2),  # Increase precision
                    existing_type=sa.Numeric(20, 2))

def downgrade():
    op.alter_column('agents', 'initial_cash',
                    type_=sa.Numeric(20, 2),
                    existing_type=sa.Numeric(30, 2))
```

### 3. Add a New Table
```python
def upgrade():
    op.create_table(
        'alerts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('agent_id', sa.Integer(), sa.ForeignKey('agents.id')),
        sa.Column('alert_type', sa.String(50)),
        sa.Column('message', sa.Text()),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'))
    )

def downgrade():
    op.drop_table('alerts')
```

### 4. Add Data to Existing Table
```python
def upgrade():
    # Add new agents
    op.execute("""
        INSERT INTO agents (signature, name, model_type, initial_cash)
        VALUES ('new-agent-001', 'New Agent', 'gpt-4', 15000.00)
    """)

def downgrade():
    op.execute("DELETE FROM agents WHERE signature = 'new-agent-001'")
```

---

## 🔄 Migration Management Commands

```bash
# Show current migration version
docker-compose run --rm alembic alembic current

# Show migration history
docker-compose run --rm alembic alembic history

# Upgrade to specific version
docker-compose run --rm alembic alembic upgrade <revision_id>

# Downgrade one step
docker-compose run --rm alembic alembic downgrade -1

# Downgrade to base (remove all)
docker-compose run --rm alembic alembic downgrade base

# Show SQL that would be executed (without running it)
docker-compose run --rm alembic alembic upgrade head --sql
```

---

## 🚀 Complete Workflow Example

**Scenario: Add a "Trading Strategy Tags" feature**

**1. Update models.py:**
```python
class Agent(Base):
    __tablename__ = 'agents'
    # ... existing fields ...
    tags = Column(JSONB, default={})  # NEW: store tags like {"style": "aggressive", "focus": "tech"}
```

**2. Create migration:**
```bash
docker-compose run --rm alembic alembic revision --autogenerate -m "add tags to agents"
```

**3. Review generated file:**
```bash
cat alembic/versions/002_*.py
```

**4. Add seed data (optional):**
Edit the migration file to add initial tags:
```python
def upgrade() -> None:
    op.add_column('agents', sa.Column('tags', postgresql.JSONB(), nullable=True))
    
    # Add default tags to existing agents
    op.execute("""
        UPDATE agents 
        SET tags = '{"trading_style": "moderate", "risk": "medium"}'::jsonb
        WHERE tags IS NULL
    """)
```

**5. Apply migration:**
```bash
docker-compose up alembic
```

**6. Verify:**
```bash
docker-compose exec postgres psql -U postgres -d trading_db -c "SELECT signature, tags FROM agents;"
```

**7. Use in your code:**
```python
from db_helpers import DatabaseHelper

db = DatabaseHelper()
agent = db.get_agent('gpt4-trader-001')
print(agent.tags)  # {'trading_style': 'moderate', 'risk': 'medium'}
```

---

## 🛠️ Troubleshooting

**Migration fails?**
```bash
# Check current state
docker-compose run --rm alembic alembic current

# Check alembic logs
docker-compose logs alembic

# Manually fix and stamp
docker-compose run --rm alembic alembic stamp head
```

**Want to start fresh?**
```bash
# WARNING: This deletes all data!
docker-compose down -v
docker-compose up --build
```

**Test migration before applying?**
```bash
# See SQL without running
docker-compose run --rm alembic alembic upgrade head --sql > migration.sql
cat migration.sql
```

---

## ✅ Best Practices

1. **Always review auto-generated migrations** before applying
2. **Test migrations in development first**
3. **Write reversible migrations** (implement both upgrade and downgrade)
4. **Add meaningful migration messages**: `alembic revision -m "descriptive_message"`
5. **One logical change per migration** (don't mix unrelated changes)
6. **Backup production data** before applying migrations
7. **Version control your migrations** (commit to git)

Your system is now fully set up with proper database migrations! 🎉