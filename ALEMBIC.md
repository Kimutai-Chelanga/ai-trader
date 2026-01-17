# Alembic Database Migrations for AI-Trader

This guide covers using Alembic for database migrations in your AI-Trader project.

## Why Alembic?

Alembic is the industry-standard migration tool that:
- **Auto-generates migrations** from SQLAlchemy models
- **Tracks schema versions** in the database
- **Supports branching** for complex scenarios
- **Integrates with SQLAlchemy** seamlessly
- **Wide community support** and documentation

## Quick Start

### 1. Initial Setup

```bash
# Run the setup script (one-time)
python alembic_setup.py

# Or manually with make
make setup
```

This creates:
- `alembic.ini` - Configuration file
- `models.py` - SQLAlchemy models
- `alembic/` - Migration directory
- `alembic/versions/` - Migration files

### 2. Start Services

```bash
# Start PostgreSQL
docker-compose up -d postgres

# Wait for it to be ready (about 5 seconds)
```

### 3. Create Initial Migration

```bash
# Auto-generate from models
make alembic-revision MESSAGE="initial schema"

# This creates: alembic/versions/YYYYMMDD_HHMM_xxxxx_initial_schema.py
```

### 4. Apply Migration

```bash
# Apply all pending migrations
make alembic-upgrade
```

## Common Workflows

### Adding a New Column

```bash
# 1. Edit models.py
# Add to Position class:
#   notes = Column(String, nullable=True)

# 2. Generate migration
make alembic-revision MESSAGE="add notes to positions"

# 3. Review generated migration in alembic/versions/

# 4. Apply it
make alembic-upgrade
```

### Creating a New Table

```bash
# 1. Add model to models.py
class UserPreference(Base):
    __tablename__ = 'user_preferences'
    id = Column(Integer, primary_key=True)
    user_id = Column(String(100), nullable=False)
    preference_key = Column(String(100), nullable=False)
    preference_value = Column(String(500))

# 2. Generate migration
make alembic-revision MESSAGE="add user preferences table"

# 3. Apply
make alembic-upgrade
```

### Manual Migration (Complex Changes)

Sometimes you need manual control:

```bash
# Create empty migration
make alembic-revision-manual MESSAGE="complex data migration"

# Edit the file and add custom SQL
# Then apply
make alembic-upgrade
```

Example manual migration:
```python
def upgrade() -> None:
    # Custom SQL for complex operations
    op.execute("""
        UPDATE positions 
        SET strategy = 'aggressive' 
        WHERE amount > 1000
    """)

def downgrade() -> None:
    # Reverse the operation
    op.execute("""
        UPDATE positions 
        SET strategy = 'default' 
        WHERE strategy = 'aggressive'
    """)
```

### Rolling Back a Migration

```bash
# Rollback one migration
make alembic-downgrade

# Rollback to a specific version
docker-compose run --rm alembic alembic downgrade <revision_id>

# Rollback everything (DANGEROUS!)
make alembic-downgrade-base
```

## Command Reference

### Migration Commands

```bash
# Check current version
make alembic-current

# Show migration history
make alembic-history

# Apply all pending migrations
make alembic-upgrade

# Apply one migration
make alembic-upgrade-one

# Rollback one migration
make alembic-downgrade

# Create new migration (auto-generate)
make alembic-revision MESSAGE="your message"

# Create empty migration (manual)
make alembic-revision-manual MESSAGE="your message"
```

### Database Commands

```bash
# Connect to database
make db-shell

# Backup database
make db-backup

# Restore from latest backup
make db-restore

# View logs
make db-logs
```

### Development Commands

```bash
# Initial dev setup
make dev-init

# Quick migration workflow
make dev-new-migration MESSAGE="add column"

# Check status
make dev-status
```

## Migration File Structure

Alembic generates files like this:

```python
"""add notes to positions

Revision ID: abc123def456
Revises: xyz789uvw012
Create Date: 2025-01-17 10:30:00.123456

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'abc123def456'
down_revision = 'xyz789uvw012'

def upgrade() -> None:
    # Auto-generated code
    op.add_column('positions', 
        sa.Column('notes', sa.String(), nullable=True))

def downgrade() -> None:
    # Auto-generated code
    op.drop_column('positions', 'notes')
```

## Best Practices

### ✅ DO:

1. **Review auto-generated migrations**
   ```bash
   # After creating, always review
   cat alembic/versions/latest_*.py
   ```

2. **Test migrations locally first**
   ```bash
   make test-migration
   ```

3. **Backup before production migrations**
   ```bash
   make db-backup
   make alembic-upgrade
   ```

4. **Keep models.py in sync with database**
   - Update models.py first
   - Then generate migration

5. **Use meaningful messages**
   - Good: "add risk_score column to positions"
   - Bad: "update schema"

### ❌ DON'T:

1. **Don't edit applied migrations**
   - Create a new migration instead

2. **Don't delete migration files**
   - Keep entire history

3. **Don't skip testing rollback**
   ```bash
   make alembic-upgrade
   make alembic-downgrade
   make alembic-upgrade
   ```

4. **Don't commit without testing**
   ```bash
   # Test locally first
   make alembic-upgrade
   # Then commit
   git add alembic/versions/*.py models.py
   git commit -m "Add migration"
   ```

## Advanced Usage

### Viewing SQL Without Applying

```bash
# See SQL that would be executed
docker-compose run --rm alembic alembic upgrade head --sql
```

### Branching and Merging

```bash
# If you have multiple branches
docker-compose run --rm alembic alembic merge heads -m "merge branches"
```

### Stamping Database

If you're migrating from an existing schema:

```bash
# Mark database as being at a specific version
make alembic-stamp REV=head
```

### Custom Migration Templates

Edit `alembic/script.py.mako` to customize generated files.

## Comparison: Alembic vs Custom Script

| Feature | Alembic | Custom Script |
|---------|---------|---------------|
| Auto-generation | ✅ Yes | ❌ No |
| SQLAlchemy integration | ✅ Native | ⚠️ Manual |
| Branching/merging | ✅ Yes | ❌ No |
| Type detection | ✅ Automatic | ⚠️ Manual |
| Community support | ✅ Large | ⚠️ Limited |
| Learning curve | ⚠️ Moderate | ✅ Simple |
| Customization | ⚠️ Complex | ✅ Easy |

## Troubleshooting

### Problem: Migration out of sync

```bash
# Check current state
make alembic-current
make alembic-history

# If needed, stamp to specific version
make alembic-stamp REV=<revision_id>
```

### Problem: Autogenerate not detecting changes

```bash
# Make sure you're importing models correctly in alembic/env.py
# Check that target_metadata is set to Base.metadata
```

### Problem: Migration fails

```bash
# View error details
make db-logs

# Rollback
make alembic-downgrade

# Fix the migration file
# Re-apply
make alembic-upgrade
```

### Problem: Can't connect to database

```bash
# Check database is running
docker-compose ps

# Check connection string in alembic.ini
# Or set DATABASE_URL environment variable
export DATABASE_URL=postgresql://user:pass@host:5432/db
```

## Production Deployment

### Pre-deployment Checklist

```bash
# 1. Run checks
make prod-check

# 2. Review SQL output carefully

# 3. Ensure backup is recent
make db-backup

# 4. Deploy during maintenance window
make prod-deploy
```

### Automated Deployment

In your CI/CD pipeline:

```yaml
# Example GitHub Actions
- name: Run database migrations
  run: |
    docker-compose up -d postgres
    sleep 10
    docker-compose run --rm alembic alembic upgrade head
```

## Integration with Your Workflow

### With Git

```bash
# Create feature branch
git checkout -b feature/add-column

# Make changes to models.py
# Generate migration
make alembic-revision MESSAGE="add column"

# Test it
make alembic-upgrade
make test-migration

# Commit both files
git add models.py alembic/versions/*.py
git commit -m "Add column to positions table"

# Push and create PR
git push origin feature/add-column
```

### With Docker Compose

Your services automatically wait for migrations:

```yaml
ai-trader-agent:
  depends_on:
    alembic:
      condition: service_completed_successfully
```

## Resources

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

## Getting Help

```bash
# Show all commands
make help

# Check migration status
make dev-status

# View Alembic help
docker-compose run --rm alembic alembic --help
```