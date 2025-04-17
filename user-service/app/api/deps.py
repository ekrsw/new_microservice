from uuid import UUID
from typing import Annotated, Union, Optional

from fastapi import Depends, HTTPException, status, Header
from jose import jwt, JWTError
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.crud.user import user
from app.models.user import User


async def validate_token(token: str) -> dict:
    """
    トークンを検証し、ペイロードを返す
    """
    try:
        # JWTの署名検証
        payload = jwt.decode(
            token, 
            settings.JWT_PUBLIC_KEY, 
            algorithms=[settings.ALGORITHM],
            options={"verify_aud": False}
        )
        
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無効なトークンです",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    authorization: Annotated[Union[str, None], Header()] = None, 
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    現在のユーザーを取得する
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="認証されていません",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = authorization.replace("Bearer ", "")
    
    try:
        # トークンの検証
        payload = await validate_token(token)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="無効なトークンです",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except (JWTError, ValidationError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"認証に失敗しました: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # ユーザーの取得
    db_user = await user.get_by_user_id(db, UUID(user_id))
    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ユーザーが見つかりません"
        )
    
    return db_user


async def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """
    現在のユーザーが管理者であることを確認
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="この操作には管理者権限が必要です"
        )
    
    return current_user
