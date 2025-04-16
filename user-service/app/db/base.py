from datetime import datetime
from typing import Any
from sqlalchemy import DateTime
from sqlalchemy.orm import as_declarative, declared_attr, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid


@as_declarative()
class Base:
    __name__: str

    # 共通フィールド
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # テーブル名を自動的にクラス名から生成（スネークケース）
    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower()