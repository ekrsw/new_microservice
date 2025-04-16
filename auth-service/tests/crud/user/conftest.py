from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import Optional, Literal
import os

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
    REDIS_TEST_HOST: str = "auth_redis"
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
