"""
Alembic Environment Configuration

Configured to use SankoSlides database settings.
"""
import os
import sys
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# Add the app directory to the path so we can import our models
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Import our models and database config
from app.core.database import Base, get_sync_database_url
# Make sure template models are registered with Base
import app.core.template_models
import app.core.survey_models

# Alembic Config object
config = context.config

# Set the database URL from our settings
config.set_main_option("sqlalchemy.url", get_sync_database_url())

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for autogenerate support
target_metadata = Base.metadata

# Tables to exclude from autogenerate (managed externally or pre-existing)
EXCLUDE_TABLES = {
    "universities",
    "faculties", 
    "departments",
    "programmes",
}


def include_object(object, name, type_, reflected, compare_to):
    """
    Filter function to exclude certain tables from autogenerate.
    
    Some tables exist in the database but are managed externally
    or were created before we started using Alembic for them.
    """
    if type_ == "table" and name in EXCLUDE_TABLES:
        return False
    if type_ == "index" and object.table.name in EXCLUDE_TABLES:
        return False
    return True


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
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
