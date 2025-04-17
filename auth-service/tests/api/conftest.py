import pytest
import asyncio
from fastapi.testclient import TestClient
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from typing import Dict, Generator, Any, AsyncGenerator
from unittest.mock import patch, MagicMock
import redis.asyncio as redis

from app.main import app as main_app
from app.db.base import Base
from app.models.user import AuthUser
from app.core.security import get_password_hash, create_access_token, create_refresh_token
from app.db.session import get_db
from app.core.config import settings

# FastAPIのテストクライアント用フィクスチャ
@pytest.fixture(scope="module")
def app() -> FastAPI:
    return main_app

@pytest.fixture(scope="module")
def client(app: FastAPI) -> Generator:
    with TestClient(app) as c:
        yield c

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

# DBセッションを差し替えるフィクスチャ
@pytest.fixture(scope="function")
async def override_get_db(db_session: AsyncSession) -> AsyncGenerator[AsyncSession, None]:
    """DBセッションをオーバーライドするフィクスチャ"""
    # セッションファクトリ関数の作成
    async def _override_get_db():
        try:
            # 既に開始されているトランザクションをロールバック
            await db_session.rollback()
            yield db_session
        finally:
            # テスト後もセッションをロールバック
            await db_session.rollback()
    
    return _override_get_db

@pytest.fixture(scope="function")
async def override_dependency(app: FastAPI, override_get_db):
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()

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
        is_admin=False,
        is_active=True
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
        is_admin=True,
        is_active=True
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin

# ユーザー用アクセストークン
@pytest.fixture(scope="function")
async def user_token(db_test_user, setup_redis_mock) -> str:
    access_token = await create_access_token(
        data={"sub": str(db_test_user.id), "username": db_test_user.username}
    )
    return access_token

# ユーザー用リフレッシュトークン
@pytest.fixture(scope="function")
async def user_refresh_token(db_test_user, setup_redis_mock) -> str:
    # Redisモックが適用された状態でリフレッシュトークンを作成
    refresh_token = await create_refresh_token(user_id=str(db_test_user.id))
    return refresh_token

# 管理者用アクセストークン
@pytest.fixture(scope="function")
async def admin_token(db_test_admin, setup_redis_mock) -> str:
    access_token = await create_access_token(
        data={"sub": str(db_test_admin.id), "username": db_test_admin.username}
    )
    return access_token

# 認証ヘッダー（ユーザー）
@pytest.fixture(scope="function")
def user_auth_headers(user_token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {user_token}"}

# 認証ヘッダー（管理者）
@pytest.fixture(scope="function")
def admin_auth_headers(admin_token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {admin_token}"}

# テスト用のモックRedisクライアント
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

# モックRedisインスタンスを提供するフィクスチャ
@pytest.fixture(scope="function")
def mock_redis_instance():
    return MockRedis()

# Redisモックをセットアップ
@pytest.fixture(scope="function")
async def setup_redis_mock(mock_redis_instance, monkeypatch):
    # redis.from_urlをモック化
    def mock_from_url(*args, **kwargs):
        return mock_redis_instance
    
    # モンキーパッチを適用
    with patch("redis.asyncio.from_url", return_value=mock_redis_instance):
        # トークンブラックリスト機能を有効化
        with patch("app.core.security.settings.TOKEN_BLACKLIST_ENABLED", True):
            yield mock_redis_instance

# テスト実行時に依存関係をオーバーライド
@pytest.fixture(scope="function")
async def api_test_dependencies(override_dependency, setup_redis_mock):
    yield
