# alembic_setup.py - Initialize Alembic for your project

"""
Setup script to initialize Alembic migrations for AI-Trader

Run this once to set up Alembic:
    python alembic_setup.py
"""

import os
from pathlib import Path

def create_alembic_ini():
    """Create alembic.ini configuration file"""
    content = """# A generic, single database configuration.

[alembic]
# Path to migration scripts
script_location = alembic

# Template used to generate migration files
file_template = %%(year)d%%(month).2d%%(day).2d_%%(hour).2d%%(minute).2d_%%(rev)s_%%(slug)s

# sys.path path, will be prepended to sys.path if present.
prepend_sys_path = .

# Timezone to use when rendering the date within the migration file
# as well as the filename.
# If specified, requires the python-dateutil library that can be
# installed by adding `alembic[tz]` to the pip requirements
# string value is passed to dateutil.tz.gettz()
# leave blank for localtime
# timezone =

# max length of characters to apply to the
# "slug" field
# truncate_slug_length = 40

# set to 'true' to run the environment during
# the 'revision' command, regardless of autogenerate
# revision_environment = false

# set to 'true' to allow .pyc and .pyo files without
# a source .py file to be detected as revisions in the
# versions/ directory
# sourceless = false

# version location specification; This defaults
# to alembic/versions.  When using multiple version
# directories, initial revisions must be specified with --version-path.
# The path separator used here should be the separator specified by "version_path_separator" below.
# version_locations = %(here)s/bar:%(here)s/bat:alembic/versions

# version path separator; As mentioned above, this is the character used to split
# version_locations. The default within new alembic.ini files is "os", which uses os.pathsep.
# If this key is omitted entirely, it falls back to the legacy behavior of splitting on spaces and/or commas.
# Valid values for version_path_separator are:
#
# version_path_separator = :
# version_path_separator = ;
# version_path_separator = space
version_path_separator = os  # Use os.pathsep. Default configuration used for new projects.

# set to 'true' to search source files recursively
# in each "version_locations" directory
# new in Alembic version 1.10
# recursive_version_locations = false

# the output encoding used when revision files
# are written from script.py.mako
# output_encoding = utf-8

sqlalchemy.url = postgresql://aitrader:aitrader_password@localhost:5432/trading_db


[post_write_hooks]
# post_write_hooks defines scripts or Python functions that are run
# on newly generated revision scripts.  See the documentation for further
# detail and examples

# format using "black" - use the console_scripts runner, against the "black" entrypoint
# hooks = black
# black.type = console_scripts
# black.entrypoint = black
# black.options = -l 79 REVISION_SCRIPT_FILENAME

# lint with attempts to fix using "ruff" - use the exec runner, execute a binary
# hooks = ruff
# ruff.type = exec
# ruff.executable = %(here)s/.venv/bin/ruff
# ruff.options = --fix REVISION_SCRIPT_FILENAME

# Logging configuration
[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
"""
    
    with open('alembic.ini', 'w') as f:
        f.write(content)
    print("✅ Created alembic.ini")


def create_models_file():
    """Create SQLAlchemy models based on existing schema"""
    content = """# models.py - SQLAlchemy models for AI-Trader

from sqlalchemy import (
    Column, Integer, String, Numeric, BigInteger, 
    TIMESTAMP, Boolean, text, Index, MetaData
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

metadata = MetaData()
Base = declarative_base(metadata=metadata)


class Position(Base):
    __tablename__ = 'positions'
    
    id = Column(Integer, primary_key=True, server_default=text("nextval('positions_id_seq')"))
    date = Column(TIMESTAMP, nullable=False)
    agent_signature = Column(String(255), nullable=False)
    action = Column(String(50))
    symbol = Column(String(20))
    amount = Column(Numeric(20, 8))
    price = Column(Numeric(20, 8))
    cash_balance = Column(Numeric(20, 2))
    created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    
    __table_args__ = (
        Index('idx_positions_date', 'date'),
        Index('idx_positions_agent', 'agent_signature'),
        Index('idx_positions_symbol', 'symbol'),
    )


class StockPrice(Base):
    __tablename__ = 'stock_prices'
    
    id = Column(Integer, primary_key=True, server_default=text("nextval('stock_prices_id_seq')"))
    symbol = Column(String(20), nullable=False)
    date = Column(TIMESTAMP, nullable=False)
    open_price = Column(Numeric(20, 8))
    high_price = Column(Numeric(20, 8))
    low_price = Column(Numeric(20, 8))
    close_price = Column(Numeric(20, 8))
    volume = Column(BigInteger)
    market = Column(String(20), server_default=text("'us'"))
    created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    
    __table_args__ = (
        Index('idx_stock_prices_symbol_date', 'symbol', 'date'),
        Index('idx_stock_prices_market', 'market'),
        Index('stock_prices_symbol_date_market_key', 'symbol', 'date', 'market', unique=True),
    )


class AgentMetric(Base):
    __tablename__ = 'agent_metrics'
    
    id = Column(Integer, primary_key=True, server_default=text("nextval('agent_metrics_id_seq')"))
    agent_signature = Column(String(255), nullable=False)
    date = Column(TIMESTAMP, nullable=False)
    total_value = Column(Numeric(20, 2))
    cash_balance = Column(Numeric(20, 2))
    portfolio_value = Column(Numeric(20, 2))
    daily_return = Column(Numeric(10, 4))
    cumulative_return = Column(Numeric(10, 4))
    sharpe_ratio = Column(Numeric(10, 4))
    max_drawdown = Column(Numeric(10, 4))
    created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    
    __table_args__ = (
        Index('idx_agent_metrics_signature_date', 'agent_signature', 'date'),
    )


class TradingLog(Base):
    __tablename__ = 'trading_logs'
    
    id = Column(Integer, primary_key=True, server_default=text("nextval('trading_logs_id_seq')"))
    agent_signature = Column(String(255), nullable=False)
    date = Column(TIMESTAMP, nullable=False)
    log_type = Column(String(50))
    message = Column(String)
    metadata = Column(JSONB)
    created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    
    __table_args__ = (
        Index('idx_trading_logs_signature', 'agent_signature'),
        Index('idx_trading_logs_date', 'date'),
    )


class Watchlist(Base):
    __tablename__ = 'watchlist'
    
    id = Column(Integer, primary_key=True, server_default=text("nextval('watchlist_id_seq')"))
    user_id = Column(String(100), server_default=text("'default'"))
    symbol = Column(String(20), nullable=False)
    added_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    
    __table_args__ = (
        Index('idx_watchlist_user', 'user_id'),
        Index('watchlist_user_id_symbol_key', 'user_id', 'symbol', unique=True),
    )
"""
    
    with open('models.py', 'w') as f:
        f.write(content)
    print("✅ Created models.py")


def create_env_py():
    """Create Alembic environment configuration"""
    alembic_dir = Path('alembic')
    alembic_dir.mkdir(exist_ok=True)
    
    content = """from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
import os
import sys

# Add parent directory to path to import models
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Import your models
from models import Base

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata for autogenerate support
target_metadata = Base.metadata

# Override sqlalchemy.url from environment variable if available
database_url = os.getenv('DATABASE_URL')
if database_url:
    config.set_main_option('sqlalchemy.url', database_url)


def run_migrations_offline() -> None:
    \"\"\"Run migrations in 'offline' mode.\"\"\"
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    \"\"\"Run migrations in 'online' mode.\"\"\"
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata,
            compare_type=True,  # Detect column type changes
            compare_server_default=True,  # Detect default value changes
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
"""
    
    env_file = alembic_dir / 'env.py'
    with open(env_file, 'w') as f:
        f.write(content)
    print("✅ Created alembic/env.py")


def create_script_mako():
    """Create migration template"""
    alembic_dir = Path('alembic')
    
    content = '''"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
'''
    
    script_file = alembic_dir / 'script.py.mako'
    with open(script_file, 'w') as f:
        f.write(content)
    print("✅ Created alembic/script.py.mako")


def create_versions_dir():
    """Create versions directory"""
    versions_dir = Path('alembic/versions')
    versions_dir.mkdir(parents=True, exist_ok=True)
    
    # Create __init__.py
    init_file = versions_dir / '__init__.py'
    init_file.touch()
    print("✅ Created alembic/versions/")


def main():
    """Main setup function"""
    print("🚀 Setting up Alembic for AI-Trader")
    print("=" * 50)
    
    create_alembic_ini()
    create_models_file()
    create_env_py()
    create_script_mako()
    create_versions_dir()
    
    print("\n" + "=" * 50)
    print("✅ Alembic setup complete!")
    print("\nNext steps:")
    print("1. Review and adjust alembic.ini if needed")
    print("2. Create initial migration:")
    print("   alembic revision --autogenerate -m 'Initial schema'")
    print("3. Apply migrations:")
    print("   alembic upgrade head")
    print("\nFor Docker:")
    print("   make alembic-revision MESSAGE='your message'")
    print("   make alembic-upgrade")


if __name__ == '__main__':
    main()