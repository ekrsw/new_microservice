import uuid
from typing import Any, List, Optional
from datetime import timedelta
from uuid import UUID
from jose import JWTError, jwt
from pydantic import ValidationError

from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.crud.user import user
from app.db.session import get_db
from app.schemas.user import PasswordUpdate, AdminPasswordUpdate, User as UserResponse, Token, RefreshToken
from app.core.config import settings
from app.api.deps import validate_refresh_token, get_current_user, get_current_admin_user
from app.core.logging import get_request_logger, app_logger
from app.models.user import User

router = APIRouter()


@router.post("/login", response_model=Token)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
    ) -> Any:
    """
    ユーザーログインとトークン発行のエンドポイント
    """
    logger = get_request_logger(request)
    logger.info(f"ログインリクエスト: ユーザー名={form_data.username}")
    
    # ユーザー認証
    db_user = await user.get_by_username(db, username=form_data.username)
    if not db_user:
        logger.warning(f"ログイン失敗: ユーザー名 '{form_data.username}' が存在しません")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ユーザー名またはパスワードが正しくありません",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # パスワード検証
    if not verify_password(form_data.password, db_user.hashed_password):
        logger.warning(f"ログイン失敗: ユーザー '{form_data.username}' のパスワードが不正です")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ユーザー名またはパスワードが正しくありません",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # アクセストークン生成
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = await create_access_token(
        data={"sub": str(db_user.id)},
        expires_delta=access_token_expires
    )
    
    # リフレッシュトークン生成
    refresh_token = await create_refresh_token(user_id=str(db_user.id))
    
    logger.info(f"ログイン成功: ユーザーID={db_user.id}, ユーザー名={db_user.username}")
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/refresh", response_model=Token)
async def refresh_token(
    request: Request,
    token_data: RefreshToken,
    db: AsyncSession = Depends(get_db)
    ) -> Any:
    """
    リフレッシュトークンを使用して新しいアクセストークンを発行するエンドポイント
    """
    logger = get_request_logger(request)
    logger.info("トークン更新リクエスト")
    
    try:
        # リフレッシュトークンの検証
        user_id = await validate_refresh_token(token_data.refresh_token)
        
        # ユーザーの存在確認
        db_user = await user.get_by_id(db, id=UUID(user_id))
        if not db_user:
            logger.warning(f"トークン更新失敗: ユーザーID '{user_id}' が存在しません")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="無効なユーザーです",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # 古いリフレッシュトークンを無効化
        await revoke_refresh_token(token_data.refresh_token)
        
        # 新しいアクセストークンの生成
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = await create_access_token(
            data={"sub": str(db_user.id)},
            expires_delta=access_token_expires
        )
        
        # 新しいリフレッシュトークンの生成
        refresh_token = await create_refresh_token(user_id=str(db_user.id))
        
        logger.info(f"トークン更新成功: ユーザーID={db_user.id}")
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
    except Exception as e:
        logger.error(f"トークン更新中にエラーが発生しました: {str(e)}", exc_info=True)
        raise


@router.post("/logout")
async def logout(
    request: Request,
    token_data: RefreshToken
    ) -> Any:
    """
    ログアウトしてリフレッシュトークンを無効化するエンドポイント
    """
    logger = get_request_logger(request)
    logger.info("ログアウトリクエスト")
    
    try:
        # リフレッシュトークンを無効化
        result = await revoke_refresh_token(token_data.refresh_token)
        
        if not result:
            logger.warning("ログアウト失敗: 無効なトークン")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="無効なトークンです",
            )
        
        logger.info("ログアウト成功: トークンを無効化しました")
        return {"detail": "ログアウトしました"}
    except Exception as e:
        logger.error(f"ログアウト処理中にエラーが発生しました: {str(e)}", exc_info=True)
        raise


@router.post("/update/password", response_model=UserResponse)
async def update_password(
    request: Request,
    password_update: PasswordUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    ユーザーのパスワードを更新するエンドポイント
    - 現在のパスワード確認が必要
    - 自分自身のパスワードのみ更新可能
    """
    logger = get_request_logger(request)
    logger.info(f"パスワード更新リクエスト: ユーザーID={current_user.id}")
    
    # 現在のパスワード確認
    if not verify_password(password_update.current_password, current_user.hashed_password):
        logger.warning(f"パスワード更新失敗: ユーザーID={current_user.id} - 現在のパスワードが不正")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="現在のパスワードが正しくありません"
        )
    
    # パスワード更新
    try:
        updated_user = await user.update_password(db, current_user, password_update.new_password)
        logger.info(f"パスワード更新成功: ユーザーID={updated_user.id}")
        return updated_user
    except Exception as e:
        logger.error(f"パスワード更新失敗: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="パスワード更新中にエラーが発生しました"
        )


@router.post("/admin/update/password", response_model=UserResponse)
async def admin_update_password(
    request: Request,
    password_update: AdminPasswordUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    管理者によるユーザーのパスワード更新エンドポイント
    - 管理者認証が必要
    - 現在のパスワード確認は不要
    - 任意のユーザーのパスワードを更新可能
    """
    logger = get_request_logger(request)
    logger.info(f"管理者によるパスワード更新リクエスト: 対象ユーザーID={password_update.user_id}, 要求元={current_user.username}")
    
    # 更新対象ユーザーの取得
    db_user = await user.get_by_id(db, id=password_update.user_id)
    if not db_user:
        logger.warning(f"パスワード更新失敗: ユーザーID '{password_update.user_id}' が存在しません")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="指定されたユーザーが見つかりません"
        )
    
    # パスワード更新
    try:
        updated_user = await user.update_password(db, db_user, password_update.new_password)
        logger.info(f"パスワード更新成功: ユーザーID={updated_user.id}, 管理者={current_user.username}")
        return updated_user
    except Exception as e:
        logger.error(f"パスワード更新失敗: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="パスワード更新中にエラーが発生しました"
        )
