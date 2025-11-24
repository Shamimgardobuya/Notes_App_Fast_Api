from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context
import asyncio
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Import SQLModel and your models
from sqlmodel import SQLModel
from app.models import Notes  # Import all your models here

# this is the Alembic Config object
config = context.config

def get_url():
    """Get and format the database URL for async connections"""
    # Print all environment variables (for debugging)
    print("[DEBUG] Checking for DATABASE_URL in environment...")
    print(f"[DEBUG] DATABASE_URL in os.environ: {'DATABASE_URL' in os.environ}")
    
    url = os.getenv("DATABASE_URL", "").strip()
    
    print(f"[DEBUG] Raw DATABASE_URL length: {len(url)}")
    print(f"[DEBUG] Raw DATABASE_URL exists: {bool(url)}")
    
    if url:
        # Show first 20 chars safely
        prefix = url[:20] if len(url) >= 20 else url
        print(f"[DEBUG] URL starts with: {prefix}...")
        print(f"[DEBUG] URL scheme: {url.split(':')[0] if ':' in url else 'NO COLON FOUND'}")
    else:
        print("[ERROR] DATABASE_URL is empty or not set!")
        print("[ERROR] Available env vars:", list(os.environ.keys())[:10])  # Show first 10 env vars
        sys.exit(1)
    
    if not url:
        raise ValueError("DATABASE_URL environment variable is not set")
    
    # Store original for comparison
    original_url = url
    
    # Convert to async format
    if url.startswith("postgres://") and not url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[11:]
        print("[DEBUG] Converted postgres:// to postgresql+asyncpg://")
    elif url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[13:]
        print("[DEBUG] Converted postgresql:// to postgresql+asyncpg://")
    elif url.startswith("postgresql+asyncpg://"):
        print("[DEBUG] Already in correct format")
    else:
        print(f"[ERROR] Unexpected URL format: {url[:30]}...")
        sys.exit(1)
    
    # Remove any existing SSL parameters
    for param in ["?sslmode=require", "&sslmode=require", "?ssl=require", "&ssl=require"]:
        if param in url:
            url = url.replace(param, "")
            print(f"[DEBUG] Removed parameter: {param}")
    
    # Add ssl=require
    separator = "&" if "?" in url else "?"
    url = f"{url}{separator}ssl=require"
    print(f"[DEBUG] Added SSL with separator: {separator}")
    
    # Parse and show connection details
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        print(f"[DEBUG] Connection details:")
        print(f"  - Scheme: {parsed.scheme}")
        print(f"  - Hostname: {parsed.hostname}")
        print(f"  - Port: {parsed.port}")
        print(f"  - Database: {parsed.path}")
        print(f"  - Username: {parsed.username}")
        print(f"  - Password: {'*' * len(parsed.password) if parsed.password else 'NONE'}")
        print(f"  - Query params: {parsed.query}")
        
        # Verify hostname is resolvable
        if not parsed.hostname:
            print("[ERROR] Hostname is None!")
            sys.exit(1)
            
    except Exception as e:
        print(f"[ERROR] Could not parse URL: {e}")
        sys.exit(1)
    
    print("[DEBUG] URL processing complete")
    return url

# Set the database URL from environment using the get_url function
print("[DEBUG] Starting Alembic env.py...")
config.set_main_option("sqlalchemy.url", get_url())
print("[DEBUG] URL set in config")

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata from SQLModel
target_metadata = SQLModel.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    
    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    
    with context.begin_transaction():
        context.run_migrations()

async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with async engine."""
    print("[DEBUG] Starting async migrations...")
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    
    print("[DEBUG] Engine created, attempting connection...")
    async with connectable.connect() as connection:
        print("[DEBUG] Connected! Running migrations...")
        await connection.run_sync(do_run_migrations)
    
    await connectable.dispose()
    print("[DEBUG] Migrations complete")

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()