import pytest
import asyncio
from fastapi.testclient import TestClient
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from typing import Dict, Generator, Any, AsyncGenerator
from unittest.mock import patch, MagicMock
import uuid

from app.main import app as main_app
from app.db.base import Base
from app.models.user import User
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
        is_admin=False,
        is_active=True,
        user_id=uuid.uuid4()
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
        is_admin=True,
        is_active=True,
        user_id=uuid.uuid4()
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin

# 認証をモックするためのフィクスチャ
@pytest.fixture(scope="function")
def mock_current_user(db_test_user):
    """現在のユーザーをモックするフィクスチャ"""
    from app.api.deps import get_current_user
    
    async def override_get_current_user():
        return db_test_user
    
    return override_get_current_user

@pytest.fixture(scope="function")
def mock_current_admin_user(db_test_admin):
    """現在の管理者ユーザーをモックするフィクスチャ"""
    from app.api.deps import get_current_admin_user
    
    async def override_get_current_admin_user():
        return db_test_admin
    
    return override_get_current_admin_user

# 認証依存関係をオーバーライドするフィクスチャ
@pytest.fixture(scope="function")
def override_auth_dependency(app: FastAPI, mock_current_user, mock_current_admin_user):
    from app.api.deps import get_current_user, get_current_admin_user
    
    app.dependency_overrides[get_current_user] = mock_current_user
    app.dependency_overrides[get_current_admin_user] = mock_current_admin_user
    
    yield
    
    app.dependency_overrides.clear()

# テスト実行時に依存関係をオーバーライド
@pytest.fixture(scope="function")
async def api_test_dependencies(override_dependency, override_auth_dependency):
    yield
