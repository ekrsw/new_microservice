from typing import Optional, List
from uuid import UUID
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.exc import IntegrityError
from app.models.user import User
from app.schemas.user import UserCreate, AdminUserCreate, UserUpdate, UserSearchParams

class CRUDUser:
    async def create(self, db: AsyncSession, obj_in: UserCreate | AdminUserCreate) -> User:
        # 管理者フラグの設定
        is_admin = getattr(obj_in, 'is_admin', False)
        
        # ユーザーオブジェクトの作成
        db_obj = User(
            username=obj_in.username,
            fullname=obj_in.fullname,
            is_admin=is_admin
        )
        db.add(db_obj)
        # コミットは呼び出し元に任せる
        await db.flush() # flush() でセッションに変更を反映
        await db.refresh(db_obj)
        return db_obj
    
    async def get_all_users(self, db: AsyncSession) -> list[User]:
        """全ユーザーを取得"""
        result = await db.execute(select(User))
        return result.scalars().all()
    
    async def get_by_id(self, db: AsyncSession, id: UUID) -> Optional[User]:
        """IDによるユーザー取得"""
        result = await db.execute(select(User).filter(User.id == id))
        return result.scalar_one_or_none()

    async def get_by_user_id(self, db: AsyncSession, user_id: UUID) -> Optional[User]:
        """Auth ServiceのユーザーIDでユーザーを取得"""
        result = await db.execute(select(User).filter(User.user_id == user_id))
        return result.scalar_one_or_none()

    async def get_by_username(self, db: AsyncSession, username: str) -> Optional[User]:
        """ユーザー名でユーザーを取得"""
        result = await db.execute(select(User).filter(User.username == username))
        return result.scalar_one_or_none()
        
    async def get_by_fullname(self, db: AsyncSession, fullname: str) -> Optional[User]:
        """フルネームでユーザーを取得"""
        result = await db.execute(select(User).filter(User.fullname == fullname))
        return result.scalar_one_or_none()

    async def search_users(self, db: AsyncSession, params: UserSearchParams) -> List[User]:
        """条件によるユーザー検索"""
        query = select(User)
        
        if params.username:
            query = query.filter(User.username.ilike(f"%{params.username}%"))
        if params.fullname:
            query = query.filter(User.fullname.ilike(f"%{params.fullname}%"))
        if params.is_active is not None:
            query = query.filter(User.is_active == params.is_active)
        if params.is_admin is not None:
            query = query.filter(User.is_admin == params.is_admin)
            
        result = await db.execute(query)
        return result.scalars().all()

    async def update(self, db: AsyncSession, db_obj: User, obj_in: UserUpdate) -> User:
        """ユーザー情報の更新"""
        try:
            if obj_in.username is not None:
                db_obj.username = obj_in.username
            if obj_in.fullname is not None:
                db_obj.fullname = obj_in.fullname
            if obj_in.is_active is not None:
                db_obj.is_active = obj_in.is_active
            if obj_in.is_admin is not None:
                db_obj.is_admin = obj_in.is_admin
                
            await db.flush()
            await db.refresh(db_obj)
            return db_obj
        except IntegrityError:
            raise

    async def delete(self, db: AsyncSession, db_obj: User) -> None:
        """ユーザーの削除"""
        await db.delete(db_obj)
        await db.flush()

    async def sync_user(self, db: AsyncSession, user_id: UUID, username: str, fullname: Optional[str] = None, is_admin: bool = False, is_active: bool = True) -> User:
        """
        Auth Serviceからのユーザー同期
        - user_idが存在すれば更新、なければ作成
        """
        # ユーザーの検索
        db_user = await self.get_by_user_id(db, user_id)
        
        if db_user:
            # 既存ユーザーの更新
            db_user.username = username
            if fullname is not None:
                db_user.fullname = fullname
            db_user.is_admin = is_admin
            db_user.is_active = is_active
            await db.flush()
            await db.refresh(db_user)
            return db_user
        else:
            # 新規ユーザーの作成
            db_obj = User(
                user_id=user_id,
                username=username,
                fullname=fullname,
                is_admin=is_admin,
                is_active=is_active
            )
            db.add(db_obj)
            await db.flush()
            await db.refresh(db_obj)
            return db_obj

user = CRUDUser()
