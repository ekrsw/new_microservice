from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import Optional, Literal, AsyncGenerator
import os
import pytest
import pytest_asyncio
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

# テスト用のモデルをインポート
from app.models.user import AuthUser
from app.db.base import Base
from app.crud.user import CRUDUser, user
from app.schemas.user import UserCreate, AdminUserCreate


class Settings(BaseSettings):
    # 環境設定
    ENVIRONMENT: Literal["development", "testing", "production"] = "testing"
    
    # ロギング設定
    LOG_LEVEL: str = "INFO"
    LOG_TO_FILE: bool = False
    LOG_FILE_PATH: str = "logs/auth_test_service.log"
    
    # 初期管理者ユーザー設定
    INITIAL_ADMIN_USERNAME: str = "admin"
    INITIAL_ADMIN_PASSWORD: str = "changeme"  # 本番環境では強力なパスワードに変更

    # データベース設定
    AUTH_TEST_DB_USER: str
    AUTH_TEST_DB_PASSWORD: str
    AUTH_TEST_DB_HOST: str
    AUTH_TEST_DB_PORT: str
    AUTH_TEST_DB: str
    
    # Redis設定
    REDIS_TEST_HOST: str = "auth_test_redis"
    REDIS_TEST_PORT: int = 6379
    
    # トークン設定
    ALGORITHM: str = "RS256"  # HS256からRS256に変更
    PRIVATE_KEY_PATH: str = "keys/private.pem"  # 秘密鍵のパス
    PUBLIC_KEY_PATH: str = "keys/public.pem"   # 公開鍵のパス
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # トークンブラックリスト関連の設定
    TOKEN_BLACKLIST_ENABLED: bool = True
    
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.AUTH_TEST_DB_USER}:{self.AUTH_TEST_DB_PASSWORD}@{self.AUTH_TEST_DB_HOST}:{self.AUTH_TEST_DB_PORT}/{self.AUTH_TEST_DB}"

    SQLALCHEMY_ECHO: bool = False  # SQLAlchemyのログ出力設定を追加
    
    @property
    def REDIS_URL(self) -> str:
        return f"redis://{self.REDIS_TEST_HOST}:{self.REDIS_TEST_PORT}/0"
    
    @property
    def PRIVATE_KEY(self) -> str:
        """秘密鍵の内容を読み込む"""
        try:
            with open(self.PRIVATE_KEY_PATH, "r") as f:
                return f.read()
        except FileNotFoundError:
            # 開発環境では環境変数から直接読み込む選択肢も
            return os.environ.get("PRIVATE_KEY", "")

    @property
    def PUBLIC_KEY(self) -> str:
        """公開鍵の内容を読み込む"""
        try:
            with open(self.PUBLIC_KEY_PATH, "r") as f:
                return f.read()
        except FileNotFoundError:
            return os.environ.get("PUBLIC_KEY", "")

    model_config = ConfigDict(
        env_file=".env.test",
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix="",
    )


settings = Settings()

# テスト用の非同期エンジンを作成
test_async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.SQLALCHEMY_ECHO,
    future=True
)

# テスト用の非同期セッションファクトリを作成
TestAsyncSessionLocal = sessionmaker(
    test_async_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


@pytest_asyncio.fixture
async def setup_database():
    """テスト用データベースをセットアップし、テスト後にクリーンアップする"""
    # テーブルを作成
    async with test_async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    # テスト終了後にテーブルを削除
    async with test_async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session(setup_database) -> AsyncGenerator[AsyncSession, None]:
    """テスト用の非同期データベースセッションを提供する"""
    async with TestAsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()


@pytest_asyncio.fixture
async def create_test_user(db_session: AsyncSession) -> AsyncGenerator[AuthUser, None]:
    """テスト用のユーザーを作成する"""
    test_user = UserCreate(
        username="test_user",
        password="test_password"
    )
    
    db_user = await user.create(db_session, test_user)
    await db_session.commit()
    
    yield db_user


@pytest_asyncio.fixture
async def create_admin_user(db_session: AsyncSession) -> AsyncGenerator[AuthUser, None]:
    """テスト用の管理者ユーザーを作成する"""
    admin_user = AdminUserCreate(
        username="admin_user",
        password="admin_password",
        is_admin=True
    )
    
    db_admin = await user.create(db_session, admin_user)
    await db_session.commit()
    
    yield db_admin
