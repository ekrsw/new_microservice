from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import Optional, Literal
import os

class Settings(BaseSettings):
    # 環境設定
    ENVIRONMENT: Literal["development", "testing", "production"] = "development"
    
    # ロギング設定
    LOG_LEVEL: str = "INFO"
    LOG_TO_FILE: bool = False
    LOG_FILE_PATH: str = "logs/user_service.log"
    
    # RabbitMQ設定
    RABBITMQ_HOST: str = "rabbitmq"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "guest"
    RABBITMQ_PASSWORD: str = "guest"
    RABBITMQ_VHOST: str = "/"
    USER_SYNC_EXCHANGE: str = "user_events"
    USER_SYNC_ROUTING_KEY: str = "user.sync"
    USER_SYNC_QUEUE: str = "user_service_sync"
    
    # データベース設定
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_PORT: str
    POSTGRES_DB: str

    # auth-service設定
    AUTH_SERVICE_INTERNAL_PORT: int = 8080
    
    # トークン設定
    ALGORITHM: str = "RS256"
    PUBLIC_KEY_PATH: str = "keys/public.pem"   # 公開鍵のパス
    
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    SQLALCHEMY_ECHO: bool = False  # SQLAlchemyのログ出力設定を追加

    @property
    def AUTH_SERVICE_URL(self) -> str:
        """認証サービスのURL"""
        return f"http://localhost:{self.AUTH_SERVICE_INTERNAL_PORT}/api/v1/auth/login"

    @property
    def PUBLIC_KEY(self) -> str:
        """公開鍵の内容を読み込む"""
        try:
            with open(self.PUBLIC_KEY_PATH, "r") as f:
                return f.read()
        except FileNotFoundError:
            return os.environ.get("PUBLIC_KEY", "")

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix="",
    )


settings = Settings()
