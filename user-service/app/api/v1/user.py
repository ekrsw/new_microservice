import uuid
from typing import Any, List, Optional
from datetime import timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Request, Response, Body, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.crud.user import user
from app.db.session import get_db
from app.schemas.user import (
    User as UserResponse,
    UserCreate,
    UserUpdate,
    UserProfile,
    UserSearchParams,
    AdminUserCreate
)
from app.core.config import settings
from app.api.deps import get_current_user, get_current_admin_user
from app.core.logging import get_request_logger, app_logger
from app.models.user import User

router = APIRouter()

# ユーザープロファイル関連エンドポイント
@router.get("/profile/me", response_model=UserProfile)
async def get_profile_me(
    request: Request,
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    自分自身のプロファイル情報を取得するエンドポイント
    """
    logger = get_request_logger(request)
    logger.info(f"プロファイル情報取得リクエスト: ユーザーID={current_user.id}")
    
    return current_user


@router.get("/profile/{user_id}", response_model=UserProfile)
async def get_profile(
    user_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    特定ユーザーのプロファイル情報を取得するエンドポイント
    - 誰でも取得可能（公開情報として扱う）
    """
    logger = get_request_logger(request)
    logger.info(f"ユーザープロファイル取得リクエスト: ユーザーID={user_id}")
    
    db_user = await user.get_by_id(db, id=user_id)
    if not db_user:
        logger.warning(f"ユーザープロファイル取得失敗: ユーザーID '{user_id}' が存在しません")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="指定されたユーザーが見つかりません"
        )
    
    # 非アクティブユーザーのプロファイルは取得不可
    if not db_user.is_active:
        logger.warning(f"ユーザープロファイル取得失敗: ユーザーID '{user_id}' は非アクティブです")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="指定されたユーザーが見つかりません"
        )
    
    logger.info(f"ユーザープロファイル取得成功: ID={db_user.id}")
    return db_user


@router.put("/profile/update", response_model=UserProfile)
async def update_profile(
    user_update: UserUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    自分自身のプロファイル情報を更新するエンドポイント
    - is_adminフラグは変更不可
    """
    logger = get_request_logger(request)
    logger.info(f"プロファイル更新リクエスト: ユーザーID={current_user.id}")
    
    # 管理者フラグは変更不可
    if user_update.is_admin is not None:
        user_update.is_admin = current_user.is_admin
        logger.warning(f"プロファイル更新: 管理者フラグの変更は無視されました: ユーザーID={current_user.id}")
    
    try:
        updated_user = await user.update(db, current_user, user_update)
        await db.commit()
        logger.info(f"プロファイル更新成功: ユーザーID={updated_user.id}")
        return updated_user
    except IntegrityError:
        await db.rollback()
        logger.error(f"プロファイル更新失敗: データベースエラー", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="プロファイル更新に失敗しました。入力内容を確認してください。"
        )
    except Exception as e:
        await db.rollback()
        logger.error(f"プロファイル更新失敗: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="プロファイル更新中にエラーが発生しました"
        )


# 管理者向けユーザー管理エンドポイント
@router.get("/users", response_model=List[UserResponse])
async def get_all_users(
    request: Request,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    全ユーザー一覧を取得するエンドポイント（管理者のみ）
    """
    logger = get_request_logger(request)
    logger.info(f"全ユーザー取得リクエスト: 要求元={current_user.id}")
    
    users = await user.get_all_users(db)
    return users


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    特定ユーザーの詳細情報を取得するエンドポイント（管理者のみ）
    """
    logger = get_request_logger(request)
    logger.info(f"ユーザー詳細取得リクエスト: 対象ID={user_id}, 要求元={current_user.id}")
    
    db_user = await user.get_by_id(db, id=user_id)
    if not db_user:
        logger.warning(f"ユーザー詳細取得失敗: ユーザーID '{user_id}' が存在しません")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="指定されたユーザーが見つかりません"
        )
    
    logger.info(f"ユーザー詳細取得成功: ID={db_user.id}")
    return db_user


@router.post("/users/create", response_model=UserResponse)
async def create_user(
    user_in: AdminUserCreate,
    request: Request,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    新規ユーザーを作成するエンドポイント（管理者のみ）
    """
    logger = get_request_logger(request)
    logger.info(f"ユーザー作成リクエスト: フルネーム={user_in.fullname}, 要求元={current_user.id}")
    
    # ユーザー名の重複チェック
    existing_user = await user.get_by_fullname(db, fullname=user_in.fullname)
    if existing_user:
        logger.warning(f"ユーザー作成失敗: フルネーム '{user_in.fullname}' は既に使用されています")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="このフルネームは既に登録されています"
        )
    
    try:
        # ユーザー作成
        new_user = await user.create(db, user_in)
        await db.commit()
        logger.info(f"ユーザー作成成功: ID={new_user.id}, フルネーム={new_user.fullname}, 管理者={new_user.is_admin}")
        return new_user
    except IntegrityError:
        await db.rollback()
        logger.error(f"ユーザー作成失敗: データベースエラー", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ユーザー作成に失敗しました。入力内容を確認してください。"
        )
    except Exception as e:
        await db.rollback()
        logger.error(f"ユーザー作成失敗: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ユーザー作成中にエラーが発生しました"
        )


@router.put("/users/update/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    user_in: UserUpdate,
    request: Request,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    ユーザー情報を更新するエンドポイント（管理者のみ）
    - 全てのフィールドが更新可能
    """
    logger = get_request_logger(request)
    logger.info(f"ユーザー更新リクエスト: 対象ID={user_id}, 要求元={current_user.id}")
    
    # 更新対象ユーザーの取得
    db_user = await user.get_by_id(db, id=user_id)
    if not db_user:
        logger.warning(f"ユーザー更新失敗: ユーザーID '{user_id}' が存在しません")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="指定されたユーザーが見つかりません"
        )
    
    try:
        # ユーザー更新
        updated_user = await user.update(db, db_user, user_in)
        await db.commit()
        logger.info(f"ユーザー更新成功: ID={updated_user.id}, フルネーム={updated_user.fullname}")
        return updated_user
    except IntegrityError:
        await db.rollback()
        logger.error(f"ユーザー更新失敗: データベースエラー", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ユーザー更新に失敗しました。入力内容を確認してください。"
        )
    except Exception as e:
        await db.rollback()
        logger.error(f"ユーザー更新失敗: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ユーザー更新中にエラーが発生しました"
        )


@router.delete("/users/delete/{user_id}")
async def delete_user(
    user_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    ユーザーを削除するエンドポイント（管理者のみ）
    """
    logger = get_request_logger(request)
    logger.info(f"ユーザー削除リクエスト: 対象ID={user_id}, 要求元={current_user.id}")
    
    # 削除対象ユーザーの取得
    db_user = await user.get_by_id(db, id=user_id)
    if not db_user:
        logger.warning(f"ユーザー削除失敗: ユーザーID '{user_id}' が存在しません")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="指定されたユーザーが見つかりません"
        )
    
    # 自分自身を削除しようとしていないか確認
    if str(current_user.id) == str(user_id):
        logger.warning(f"ユーザー削除失敗: ユーザーID '{current_user.id}' が自分自身を削除しようとしています")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="自分自身を削除することはできません"
        )
    
    try:
        # ユーザー削除
        await user.delete(db, db_user)
        await db.commit()
        logger.info(f"ユーザー削除成功: ID={user_id}, フルネーム={db_user.fullname}")
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as e:
        await db.rollback()
        logger.error(f"ユーザー削除失敗: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ユーザー削除中にエラーが発生しました"
        )


# ユーザー検索エンドポイント
@router.get("/users/search", response_model=List[UserResponse])
async def search_users(
    request: Request,
    fullname: Optional[str] = None,
    is_active: Optional[bool] = None,
    is_admin: Optional[bool] = None,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    条件に基づいてユーザーを検索するエンドポイント（管理者のみ）
    """
    logger = get_request_logger(request)
    logger.info(f"ユーザー検索リクエスト: 条件=[fullname={fullname}, is_active={is_active}, is_admin={is_admin}], 要求元={current_user.id}")
    
    # 検索条件の構築
    search_params = UserSearchParams(
        fullname=fullname,
        is_active=is_active,
        is_admin=is_admin
    )
    
    # ユーザー検索
    users = await user.search_users(db, search_params)
    logger.info(f"ユーザー検索結果: {len(users)}件")
    return users


# RabbitMQメッセージングエンドポイント
@router.post("/sync/user", response_model=UserResponse)
async def sync_user(
    request: Request,
    user_id: UUID = Body(...),
    fullname: str = Body(...),
    is_admin: bool = Body(...),
    is_active: bool = Body(...),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    auth-serviceからのユーザー同期イベントを受け取るエンドポイント
    - 内部APIとして使用（APIキーなどでの保護が必要）
    """
    logger = get_request_logger(request)
    logger.info(f"ユーザー同期リクエスト: ユーザーID={user_id}, フルネーム={fullname}")
    
    # TODO: API認証の実装（X-API-Keyなど）
    
    try:
        # ユーザー同期
        synced_user = await user.sync_user(
            db=db,
            user_id=user_id,
            fullname=fullname,
            is_admin=is_admin,
            is_active=is_active
        )
        await db.commit()
        
        action = "更新" if await user.get_by_user_id(db, user_id) else "作成"
        logger.info(f"ユーザー同期成功: ID={synced_user.id}, フルネーム={synced_user.fullname}, アクション={action}")
        return synced_user
    except IntegrityError:
        await db.rollback()
        logger.error(f"ユーザー同期失敗: データベースエラー", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ユーザー同期に失敗しました。データの整合性エラー。"
        )
    except Exception as e:
        await db.rollback()
        logger.error(f"ユーザー同期失敗: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ユーザー同期中にエラーが発生しました"
        )
