import pytest
import asyncio
from fastapi.testclient import TestClient
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from typing import Dict, Generator, Any, AsyncGenerator
from unittest.mock import patch, MagicMock
import uuid
from sqlalchemy.ext.asyncio import async_scoped_session
from sqlalchemy import event
import greenlet

from app.main import app as main_app
from app.db.base import Base
from app.models.user import User
from app.db.session import get_db
from app.core.config import settings
from app.api.deps import get_current_user, get_current_admin_user

# テスト用のモックデータベースセッション
class MockDBSession:
    def __init__(self, users=None):
        self.users = users or []
        self.committed = False
        self.rolled_back = False
        self.closed = False
        self.flushed = False
    
    async def commit(self):
        self.committed = True
    
    async def rollback(self):
        self.rolled_back = True
    
    async def close(self):
        self.closed = True
    
    async def flush(self):
        self.flushed = True
    
    def add(self, obj):
        if isinstance(obj, User):
            self.users.append(obj)
    
    async def refresh(self, obj):
        pass
    
    async def delete(self, obj):
        if isinstance(obj, User) and obj in self.users:
            self.users.remove(obj)
        # MagicMockオブジェクトの場合は何もしない
    
    async def execute(self, query):
        # SQLAlchemyのselectクエリをシミュレート
        from sqlalchemy import select
        from sqlalchemy.engine.result import Result
        
        # 簡易的なResultオブジェクトのモック
        class MockResult:
            def __init__(self, items):
                self.items = items
            
            def scalars(self):
                return self
            
            def first(self):
                return self.items[0] if self.items else None
            
            def all(self):
                return self.items
            
            def fetchall(self):
                return [(item,) for item in self.items]
            
            def scalar_one_or_none(self):
                return self.items[0] if self.items else None
        
        # クエリの種類に応じた処理
        if hasattr(query, 'whereclause') and query.whereclause is not None:
            # フィルタリング条件がある場合
            filtered_users = []
            for user in self.users:
                # 簡易的なフィルタリング（実際のSQLAlchemyの動作とは異なる）
                if hasattr(query.whereclause, 'right') and hasattr(query.whereclause, 'left'):
                    if str(query.whereclause.right.value) == str(user.id):
                        filtered_users.append(user)
            return MockResult(filtered_users)
        else:
            # フィルタリング条件がない場合は全ユーザーを返す
            return MockResult(self.users)

# テスト用のモックユーザー
class MockUser:
    def __init__(self, id=None, username="testuser", fullname="Test User", is_admin=False, is_active=True, user_id=None):
        self.id = id or uuid.uuid4()
        self.username = username
        self.fullname = fullname
        self.is_admin = is_admin
        self.is_active = is_active
        self.user_id = user_id or uuid.uuid4()

# FastAPIのテストクライアント用フィクスチャ
@pytest.fixture(scope="module")
def app() -> FastAPI:
    # 依存関係をモックに置き換え
    app = main_app
    
    # モックユーザーを作成
    test_user = MockUser(username="testuser", fullname="Test User", is_admin=False)
    test_admin = MockUser(username="admin", fullname="Admin User", is_admin=True)
    
    # 依存関係をオーバーライド
    async def mock_get_current_user():
        return test_user
    
    async def mock_get_current_admin_user():
        return test_admin
    
    async def mock_get_db():
        mock_session = MockDBSession(users=[test_user, test_admin])
        yield mock_session
    
    app.dependency_overrides[get_db] = mock_get_db
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_current_admin_user] = mock_get_current_admin_user
    
    return app

@pytest.fixture(scope="module")
def client(app: FastAPI) -> Generator:
    with TestClient(app) as c:
        yield c

# テスト用のモックデータベースセッション
@pytest.fixture(scope="function")
def db_session():
    return MockDBSession()

# テスト用のモックユーザー
@pytest.fixture(scope="function")
def db_test_user():
    return MockUser(username="testuser", fullname="Test User", is_admin=False)

# テスト用のモック管理者
@pytest.fixture(scope="function")
def db_test_admin():
    return MockUser(username="admin", fullname="Admin User", is_admin=True)

# テスト用の依存関係をオーバーライドするフィクスチャ
@pytest.fixture(scope="function")
def api_test_dependencies():
    # 既にappフィクスチャで依存関係をオーバーライドしているので、
    # ここでは何もしない
    yield
