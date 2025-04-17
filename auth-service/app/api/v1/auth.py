import uuid
from typing import Any, List, Optional
from datetime import timedelta
from uuid import UUID
from jose import JWTError, jwt
from pydantic import ValidationError

from fastapi import APIRouter, Depends, Header, HTTPException, status, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.crud.user import user
from app.db.session import get_db
from app.schemas.user import PasswordUpdate, AdminPasswordUpdate, User as UserResponse, Token, RefreshToken, RefreshTokenRequest, LogoutRequest, TokenVerifyRequest, TokenVerifyResponse
from app.core.security import (
    verify_password, 
    create_access_token, 
    create_refresh_token, 
    verify_refresh_token,
    revoke_refresh_token,
    verify_token,
    blacklist_token
)
from app.core.config import settings
from app.api.deps import validate_refresh_token, get_current_user, get_current_admin_user
from app.core.logging import get_request_logger, app_logger
from app.models.user import AuthUser

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
        data={"sub": str(db_user.id),
              "username": db_user.username},
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
    token_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
    ) -> Any:
    """
    リフレッシュトークンを使用して新しいアクセストークンを発行するエンドポイント
    - アクセストークンとリフレッシュトークンの両方が必要
    - 古いトークンは無効化される
    """
    logger = get_request_logger(request)
    logger.info("トークン更新リクエスト")
    
    # トランザクション開始
    async with db.begin():
        try:
            # リフレッシュトークンの検証
            try:
                user_id = await validate_refresh_token(token_data.refresh_token)
            except jwt.JWTError as e:
                logger.warning(f"リフレッシュトークン検証失敗: JWT形式エラー: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="無効なリフレッシュトークンです",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            except Exception as e:
                logger.warning(f"リフレッシュトークン検証失敗: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="リフレッシュトークンの検証に失敗しました",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
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
            refresh_result = await revoke_refresh_token(token_data.refresh_token)
            if not refresh_result:
                logger.warning(f"リフレッシュトークン無効化失敗: {token_data.refresh_token}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="リフレッシュトークンの無効化に失敗しました",
                )

            # 古いアクセストークンをブラックリストに追加（必須）
            blacklist_result = await blacklist_token(token_data.access_token)
            logger.info(f"アクセストークンのブラックリスト登録: {blacklist_result}")
            if not blacklist_result:
                logger.warning(f"アクセストークンのブラックリスト登録失敗: {token_data.access_token}")
                # 登録に失敗しても処理を続行するが、ログには残す

            # 新しいアクセストークンの生成
            access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token = await create_access_token(
                data={"sub": str(db_user.id),
                      "username": db_user.username},
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
        except HTTPException:
            # 既に適切なHTTPExceptionが発生している場合はそのまま再送出
            raise
        except JWTError as e:
            # JWT形式エラーは400 Bad Requestとして扱う
            logger.error(f"JWTエラー: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"トークンの形式が不正です: {str(e)}"
            )
        except Exception as e:
            # その他の予期しないエラーは500 Internal Server Errorとして扱う
            logger.error(f"トークン更新中にエラーが発生しました: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"トークン更新中にエラーが発生しました: {str(e)}"
            )


@router.post("/logout")
async def logout(
    request: Request,
    token_data: LogoutRequest,
    db: AsyncSession = Depends(get_db)
    ) -> Any:
    """
    ログアウトしてリフレッシュトークンとアクセストークンを無効化するエンドポイント
    - アクセストークンとリフレッシュトークンの両方が必要
    - 両方のトークンを無効化する
    """
    logger = get_request_logger(request)
    logger.info("ログアウトリクエスト")
    
    # トランザクション開始
    async with db.begin():
        try:
            # リフレッシュトークンを無効化
            refresh_result = await revoke_refresh_token(token_data.refresh_token)
            if not refresh_result:
                logger.warning(f"リフレッシュトークン無効化失敗: {token_data.refresh_token}")
                # 失敗をログに残すが、アクセストークンの処理は続行

            # アクセストークンをブラックリストに追加（必須）
            blacklist_result = await blacklist_token(token_data.access_token)
            logger.info(f"アクセストークンのブラックリスト登録: {blacklist_result}")
            if not blacklist_result:
                logger.warning(f"アクセストークンのブラックリスト登録失敗: {token_data.access_token}")
                # 失敗をログに残す
            
            # 両方のトークン処理が失敗した場合はエラーを返す
            if not refresh_result and not blacklist_result:
                logger.warning("ログアウト失敗: 両方のトークンが無効")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="無効なトークンです。ログアウト処理に失敗しました。",
                )
            
            # 少なくとも一方が成功した場合
            success_message = "ログアウトしました"
            if not refresh_result:
                success_message += "（リフレッシュトークンの無効化に失敗しました）"
            if not blacklist_result:
                success_message += "（アクセストークンのブラックリスト登録に失敗しました）"
            
            logger.info(f"ログアウト処理完了: {success_message}")
            return {"detail": success_message}
        except HTTPException:
            # 既に適切なHTTPExceptionが発生している場合はそのまま再送出
            raise
        except JWTError as e:
            # JWT形式エラーは400 Bad Requestとして扱う
            logger.error(f"JWTエラー: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"トークンの形式が不正です: {str(e)}"
            )
        except Exception as e:
            # その他の予期しないエラーは500 Internal Server Errorとして扱う
            logger.error(f"ログアウト処理中にエラーが発生しました: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"ログアウト処理中にエラーが発生しました: {str(e)}"
            )


@router.post("/update/password", response_model=UserResponse)
async def update_password(
    request: Request,
    password_update: PasswordUpdate,
    current_user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    authorization: str = Header(None)
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
        
        # 現在のアクセストークンをブラックリストに追加
        if authorization and authorization.startswith("Bearer "):
            access_token = authorization.replace("Bearer ", "")
            await blacklist_token(access_token)
            logger.info(f"パスワード変更に伴いアクセストークンをブラックリストに追加: ユーザーID={updated_user.id}")
            
        logger.info(f"パスワード更新成功: ユーザーID={updated_user.id}")
        return updated_user
    except Exception as e:
        logger.error(f"パスワード更新失敗: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="パスワード更新中にエラーが発生しました"
        )


@router.post("/verify", response_model=TokenVerifyResponse)
async def verify_token_endpoint(
    request: Request,
    token_data: TokenVerifyRequest
) -> Any:
    """
    トークンを検証するエンドポイント
    """
    logger = get_request_logger(request)
    logger.info("トークン検証リクエスト")
    
    try:
        # トークンの検証（ブラックリストチェックを含む）
        payload = await verify_token(token_data.token)
        
        # ペイロードが取得できない場合（無効なトークン、ブラックリスト登録済み）
        if not payload:
            logger.warning("トークン検証失敗: 無効なトークンまたはブラックリスト登録済み")
            # 401エラーではなく、正常なレスポンスとして検証結果を返す
            return {
                "valid": False,
                "error": "無効なトークンまたはブラックリスト登録済み"
            }

        logger.info(f"トークン検証成功: ユーザーID={payload.get('sub')}")
        
        # 有効なトークンの場合の正常レスポンス
        return {
            "valid": True,
            "user_id": payload.get("sub"),
            "username": payload.get("username"),
            "roles": payload.get("roles", [])
        }
    except JWTError as e:
        # JWT形式エラーは400 Bad Requestとして扱う
        logger.error(f"JWTエラー: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"トークンの形式が不正です: {str(e)}"
        )
    except Exception as e:
        # その他の予期しないエラーは500 Internal Server Errorとして扱う
        logger.error(f"トークン検証中にエラーが発生しました: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"トークン検証中にエラーが発生しました: {str(e)}"
        )


@router.post("/admin/update/password", response_model=UserResponse)
async def admin_update_password(
    request: Request,
    password_update: AdminPasswordUpdate,
    current_user: AuthUser = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
    authorization: str = Header(None)
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
        
        # ユーザーの全トークンをブラックリストに追加する機能はここでは実装しません
        # ただし管理者のアクセストークンはブラックリスト登録不要です
        
        logger.info(f"パスワード更新成功: ユーザーID={updated_user.id}, 管理者={current_user.username}")
        return updated_user
    except Exception as e:
        logger.error(f"パスワード更新失敗: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="パスワード更新中にエラーが発生しました"
        )
