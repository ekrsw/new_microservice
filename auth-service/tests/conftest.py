import asyncio
import pytest
import pytest_asyncio
from typing import AsyncGenerator, Generator
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

# アプリケーションのインポート
from app.main import app
from app.api.deps import get_db
from app.core.security import create_access_token, create_refresh_token
from app.schemas.user import Token

# テスト用のセッション設定をインポート
from tests.crud.user.conftest import (
    db_session,
    setup_database,
    create_test_user,
    create_admin_user,
    settings
)


@pytest.fixture(scope="session")
def event_loop():
    """非同期テスト用のイベントループを提供"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def test_app() -> Generator[FastAPI, None, None]:
    """テスト用のFastAPIアプリケーションを提供"""
    yield app


@pytest.fixture(scope="function")
def client(test_app: FastAPI) -> Generator[TestClient, None, None]:
    """テスト用のクライアントを提供"""
    with TestClient(test_app) as c:
        yield c


@pytest.fixture(scope="function")
def async_client(test_app: FastAPI) -> Generator[TestClient, None, None]:
    """
    テスト用のクライアントを提供
    注: 実際にはAsyncClientではなくTestClientを返しますが、
    既存のテストコードと互換性を保つため命名を維持しています
    """
    with TestClient(test_app) as client:
        yield client


@pytest_asyncio.fixture(scope="function")
async def token_headers(create_test_user) -> AsyncGenerator[dict, None]:
    """通常ユーザー用の認証ヘッダーを提供"""
    # アクセストークンの生成
    access_token = await create_access_token(
        data={"sub": str(create_test_user.id), "username": create_test_user.username}
    )
    headers = {"Authorization": f"Bearer {access_token}"}
    yield headers


@pytest_asyncio.fixture(scope="function")
async def admin_token_headers(create_admin_user) -> AsyncGenerator[dict, None]:
    """管理者ユーザー用の認証ヘッダーを提供"""
    # アクセストークンの生成
    access_token = await create_access_token(
        data={"sub": str(create_admin_user.id), "username": create_admin_user.username}
    )
    headers = {"Authorization": f"Bearer {access_token}"}
    yield headers


@pytest_asyncio.fixture(scope="function")
async def user_tokens(create_test_user) -> AsyncGenerator[Token, None]:
    """通常ユーザー用のアクセストークンとリフレッシュトークンを提供"""
    # アクセストークンの生成
    access_token = await create_access_token(
        data={"sub": str(create_test_user.id), "username": create_test_user.username}
    )
    # リフレッシュトークンの生成
    refresh_token = await create_refresh_token(user_id=str(create_test_user.id))
    
    yield Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )


@pytest_asyncio.fixture(scope="function")
async def admin_tokens(create_admin_user) -> AsyncGenerator[Token, None]:
    """管理者ユーザー用のアクセストークンとリフレッシュトークンを提供"""
    # アクセストークンの生成
    access_token = await create_access_token(
        data={"sub": str(create_admin_user.id), "username": create_admin_user.username}
    )
    # リフレッシュトークンの生成
    refresh_token = await create_refresh_token(user_id=str(create_admin_user.id))
    
    yield Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )
