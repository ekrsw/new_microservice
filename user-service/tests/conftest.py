import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.db.base import Base
from app.models.user import User
from uuid import UUID
import uuid

# テスト用のインメモリSQLiteデータベース
@pytest.fixture(scope="function")
async def db_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest.fixture(scope="function")
async def db_session(db_engine):
    async_session = sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session

# テストユーザーデータ
@pytest.fixture(scope="function")
def test_user_data():
    return {
        "username": "testuser",
        "fullname": "Test User"
    }

# テスト管理者データ
@pytest.fixture(scope="function")
def test_admin_data():
    return {
        "username": "admin",
        "fullname": "Admin User",
        "is_admin": True
    }

# DBに登録済みのテストユーザー
@pytest.fixture(scope="function")
async def db_test_user(db_session, test_user_data):
    user = User(
        username=test_user_data["username"],
        fullname=test_user_data["fullname"],
        is_admin=False
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user

# DBに登録済みのテスト管理者
@pytest.fixture(scope="function")
async def db_test_admin(db_session, test_admin_data):
    admin = User(
        username=test_admin_data["username"],
        fullname=test_admin_data["fullname"],
        is_admin=True
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin
