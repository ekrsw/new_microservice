import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.db.base import Base
from app.models.user import AuthUser
from app.core.security import get_password_hash
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

# テスト用のモックRedisクライアント
@pytest.fixture(scope="function")
def mock_redis():
    class MockRedis:
        def __init__(self):
            self.data = {}
            self.expirations = {}
        
        async def setex(self, key, ttl, value):
            self.data[key] = value
            self.expirations[key] = ttl
            return True
            
        async def get(self, key):
            value = self.data.get(key)
            if value:
                # 実際のRedisのようにバイト列を返す
                return value.encode('utf-8') if isinstance(value, str) else value
            return None
            
        async def delete(self, key):
            if key in self.data:
                del self.data[key]
                return 1
            return 0
            
        async def aclose(self):
            pass
    
    return MockRedis()

# テストユーザーデータ
@pytest.fixture(scope="function")
def test_user_data():
    return {
        "username": "testuser",
        "password": "password123"
    }

# テスト管理者データ
@pytest.fixture(scope="function")
def test_admin_data():
    return {
        "username": "admin",
        "password": "adminpass",
        "is_admin": True
    }

# DBに登録済みのテストユーザー
@pytest.fixture(scope="function")
async def db_test_user(db_session, test_user_data):
    user = AuthUser(
        username=test_user_data["username"],
        hashed_password=get_password_hash(test_user_data["password"]),
        is_admin=False
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user

# DBに登録済みのテスト管理者
@pytest.fixture(scope="function")
async def db_test_admin(db_session, test_admin_data):
    admin = AuthUser(
        username=test_admin_data["username"],
        hashed_password=get_password_hash(test_admin_data["password"]),
        is_admin=True
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin
