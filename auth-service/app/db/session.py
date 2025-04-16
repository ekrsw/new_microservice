from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_scoped_session
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
import asyncio

from app.core.config import settings


# 非同期エンジンの作成
async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.SQLALCHEMY_ECHO,
    future=True
)

# 非同期セッションファクトリーの作成
AsyncSessionLocal = sessionmaker(
    async_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

# 非同期DBセッションを取得するための依存関係
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.commit()
            await session.close()

# テスト用の非同期エンジンとセッションファクトリーの作成
test_async_engine = create_async_engine(
    settings.TEST_DATABASE_URL,
    echo=True,
    future=True,
    poolclass=NullPool,  # コネクションプールを無効化
)
TestAsyncSessionLocal = sessionmaker(
    test_async_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

# テスト用DBセッションを取得するための依存関係
async def get_test_db() -> AsyncSession:
    async with TestAsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
