from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from typing import Optional
from pydantic import ValidationError
from uuid import UUID

from app.core.config import settings
from app.core.security import verify_refresh_token, verify_token
from app.models.user import AuthUser
from app.crud.user import user as user_crud
from app.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

async def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: AsyncSession = Depends(get_db)
        ) -> AuthUser:
    """
    アクセストークンからユーザーを取得する依存関数
    
    Args:
        token: JWTアクセストークン
        db: データベースセッション
        
    Returns:
        AuthUser: 認証されたユーザー
        
    Raises:
        HTTPException: トークンが無効な場合
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="認証情報が無効です",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # 移行期間中は両方の方式をサポート
        payload = await verify_token(token)
        if payload is None:
            raise credentials_exception
            
        user_id: str = payload.get("sub")
        
        if user_id is None:
            raise credentials_exception
            
    except (JWTError, ValidationError):
        raise credentials_exception
        
    # ユーザーをデータベースから取得
    user = await user_crud.get_by_id(db, id=UUID(user_id))
    
    if user is None:
        raise credentials_exception
        
    return user

async def get_current_admin_user(
        current_user: AuthUser = Depends(get_current_user)
        ) -> AuthUser:
    """
    現在のユーザーが管理者であることを確認する依存関数
    
    Args:
        current_user: 認証されたユーザー
        
    Returns:
        AuthUser: 管理者権限を持つユーザー
        
    Raises:
        HTTPException: ユーザーが管理者でない場合
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="この操作には管理者権限が必要です",
        )
    return current_user

async def validate_refresh_token(refresh_token: str) -> Optional[str]:
    """
    リフレッシュトークンを検証する関数
    
    Args:
        refresh_token: 検証するリフレッシュトークン
        
    Returns:
        Optional[str]: トークンが有効な場合はユーザーID、無効な場合はNone
        
    Raises:
        HTTPException: トークンが無効な場合
    """
    user_id = await verify_refresh_token(refresh_token)
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="リフレッシュトークンが無効です",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    return user_id
