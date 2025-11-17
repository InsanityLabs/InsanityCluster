"""
Database connection management with asyncpg connection pooling
"""
import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

import asyncpg
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from insanity_cluster.common.config import settings


class DatabaseManager:
    """Manages database connections with connection pooling"""

    def __init__(self):
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[async_sessionmaker] = None
        self._asyncpg_pool: Optional[asyncpg.Pool] = None

    async def initialize(self):
        """Initialize database engine and connection pool"""
        if self._engine is not None:
            return

        # Create SQLAlchemy async engine
        database_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")

        self._engine = create_async_engine(
            database_url,
            echo=settings.debug,
            pool_size=20,
            max_overflow=10,
            pool_pre_ping=True,
            pool_recycle=3600,
        )

        # Create session factory
        self._session_factory = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        # Create asyncpg connection pool for raw queries
        self._asyncpg_pool = await asyncpg.create_pool(
            host=settings.postgres_host,
            port=settings.postgres_port,
            database=settings.postgres_db,
            user=settings.postgres_user,
            password=settings.postgres_password,
            min_size=10,
            max_size=20,
            command_timeout=60,
        )

    async def close(self):
        """Close database connections"""
        if self._asyncpg_pool:
            await self._asyncpg_pool.close()
            self._asyncpg_pool = None

        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get a database session"""
        if self._session_factory is None:
            await self.initialize()

        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    @asynccontextmanager
    async def connection(self) -> AsyncGenerator[asyncpg.Connection, None]:
        """Get a raw asyncpg connection from the pool"""
        if self._asyncpg_pool is None:
            await self.initialize()

        async with self._asyncpg_pool.acquire() as conn:
            yield conn

    async def execute_raw(self, query: str, *args) -> list:
        """Execute a raw SQL query and return results"""
        async with self.connection() as conn:
            return await conn.fetch(query, *args)

    async def execute_raw_one(self, query: str, *args) -> Optional[asyncpg.Record]:
        """Execute a raw SQL query and return a single result"""
        async with self.connection() as conn:
            return await conn.fetchrow(query, *args)

    async def health_check(self) -> bool:
        """Check if database connection is healthy"""
        try:
            async with self.connection() as conn:
                await conn.fetchval("SELECT 1")
            return True
        except Exception:
            return False


# Global database manager instance
db_manager = DatabaseManager()


# Convenience functions
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for FastAPI to get database session"""
    async with db_manager.session() as session:
        yield session


async def init_db():
    """Initialize database connection pool"""
    await db_manager.initialize()


async def close_db():
    """Close database connections"""
    await db_manager.close()


# Synchronous database dependency for FastAPI
def get_db():
    """
    Synchronous database session dependency for FastAPI.
    
    Note: This uses the synchronous context manager from DatabaseManager.
    For async endpoints, use get_session() instead.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker, Session
    
    # Create synchronous engine
    database_url = settings.database_url
    engine = create_engine(
        database_url,
        pool_size=20,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=3600,
    )
    
    # Create session factory
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
