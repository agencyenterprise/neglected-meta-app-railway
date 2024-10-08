import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import (Column, DateTime, ForeignKey, Integer, MetaData,
                        String, Table, engine_from_config, pool)
from sqlalchemy.sql import func

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Define your tables here
metadata = MetaData()

approaches = Table(
    'approaches', metadata,
    Column('id', Integer, primary_key=True),
    Column('node_id', String),
    Column('created_at', DateTime, server_default=func.now()),
    Column('link', String, nullable=False),
    Column('label', String),
    Column('type', String, nullable=False),
    Column('spotlight_count', Integer, server_default='0'),
    Column('main_article', String)
)

spotlights = Table(
    'spotlights', metadata,
    Column('id', Integer, primary_key=True),
    Column('approach_id', Integer, ForeignKey('approaches.id')),
    Column('email', String),
    Column('comment', String),
    Column('created_at', DateTime, server_default=func.now())
)

# Set target_metadata to the metadata object
target_metadata = metadata

# Override sqlalchemy.url with environment variable
def get_url():
    return os.getenv("DATABASE_URL", "postgresql://postgres:passw0rd@localhost:5432/neglected_meta_analysis")

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

# Modify the run_migrations_online function
def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    configuration = config.get_section(config.config_ini_section)
    configuration['sqlalchemy.url'] = get_url()
    connectable = engine_from_config(
        configuration,
        prefix='sqlalchemy.',
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
