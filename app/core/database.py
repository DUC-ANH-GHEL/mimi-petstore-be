from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool
from app.core.config import settings

# Create declarative base
Base = declarative_base()

# Create async engine with NullPool to prevent connection pooling issues
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True,  # Enable SQL query logging
    future=True,
    poolclass=NullPool,  # Disable connection pooling
    pool_pre_ping=True
)

# Create async session factory with expire_on_commit=False
async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

async def get_db() -> AsyncSession:
    """Get database session"""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close() 