from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
from uuid import UUID


# 共通のプロパティを持つUserBaseクラス
class UserBase(BaseModel):
    fullname: Optional[str] = None
    is_active: Optional[bool] = True
    is_admin: Optional[bool] = None


# 新規ユーザー作成時に必要なプロパティ
class UserCreate(BaseModel):
    fullname: str = Field(..., min_length=1, max_length=50)


# 管理者が作成するユーザー
class AdminUserCreate(UserCreate):
    is_admin: bool = False


# ユーザー更新時に使うプロパティ（パスワード更新は含まない）
class UserUpdate(UserBase):
    fullname: Optional[str] = Field(None, max_length=50)


# ユーザープロファイル情報
class UserProfile(BaseModel):
    fullname: str
    is_active: bool
    is_admin: bool

    model_config = {
        "from_attributes": True
    }


# パスワード更新用のスキーマ
class PasswordUpdate(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)


# 管理者用のパスワード更新スキーマ
class AdminPasswordUpdate(BaseModel):
    user_id: UUID
    new_password: str = Field(..., min_length=8)


# トークン
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


# リフレッシュトークン
class RefreshToken(BaseModel):
    refresh_token: str


# レスポンスとして返すユーザー情報
class UserInDBBase(UserBase):
    id: UUID
    fullname: str
    user_id: UUID
    is_active: bool
    is_admin: bool
 
    model_config = {
        "from_attributes": True,
        "arbitrary_types_allowed": True
    }


# APIレスポンスで使用するユーザースキーマ
class User(UserInDBBase):
    pass


# ユーザー検索用のクエリパラメータ
class UserSearchParams(BaseModel):
    fullname: Optional[str] = None
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None
