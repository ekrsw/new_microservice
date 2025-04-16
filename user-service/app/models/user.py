from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base
import uuid


class User(Base):
    __tablename__ = "users"
    fullname: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    user_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)