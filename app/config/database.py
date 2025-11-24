import os
from dotenv import load_dotenv
load_dotenv()
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from typing import Annotated
from fastapi import Depends
import redis.asyncio as redis
from logging.handlers import RotatingFileHandler

redis_client = redis.from_url(os.getenv('REDIS_URL'), encoding='utf-8', decode_responses = True)
DATABASE_URL = os.getenv("DATABASE_URL")
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    # Convert postgres:// to postgresql+asyncpg://
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
    elif DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    # Remove any incorrect sslmode parameter
    DATABASE_URL = DATABASE_URL.replace("sslmode=require", "")
    DATABASE_URL = DATABASE_URL.replace("?sslmode=require", "")
    DATABASE_URL = DATABASE_URL.replace("&sslmode=require", "")
    
    # Clean up any double question marks or ampersands
    DATABASE_URL = DATABASE_URL.replace("??", "?").replace("?&", "?")
    
    # Add ssl=require if not present
    if "ssl=" not in DATABASE_URL.lower():
        separator = "&" if "?" in DATABASE_URL else "?"
        DATABASE_URL += f"{separator}ssl=require"
    
    # Strip any whitespace
    DATABASE_URL = DATABASE_URL.strip()

print(f"Final DATABASE_URL: {DATABASE_URL}")

engine = create_async_engine(DATABASE_URL, echo=True)

AsyncSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_async_session() -> AsyncSession:
    """Provides a managed asynchronous database session to endpoints."""
    async with AsyncSessionLocal() as session:
        yield session

SessionDep = Annotated[AsyncSession, Depends(get_async_session)]
