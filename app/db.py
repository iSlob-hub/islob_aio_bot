from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models"""
    pass


# Create async engine
engine = create_async_engine(
    str(settings.DATABASE_URL),
    echo=False,
    future=True,
)

# Create async session factory
async_session_factory = async_sessionmaker(
    engine,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting async session"""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Async session context manager
async def get_session() -> AsyncSession:
    """Get async session for use outside of dependency injection"""
    async with async_session_factory() as session:
        return session
