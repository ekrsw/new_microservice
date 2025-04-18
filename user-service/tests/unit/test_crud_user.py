import pytest
import uuid
from app.crud.user import user as user_crud
from app.schemas.user import UserCreate, AdminUserCreate, UserUpdate
from app.models.user import User
from sqlalchemy.exc import IntegrityError
from unittest.mock import patch, MagicMock

class TestCRUDUser:
    async def test_create_user(self, db_session):
        """一般ユーザー作成のテスト"""
        user_in = UserCreate(username="newuser", fullname="New User")
        user = await user_crud.create(db_session, user_in)
        
        assert user.username == "newuser"
        assert user.fullname == "New User"
        assert user.is_admin is False
        assert user.is_active is True
        
        # DBに保存されていることを確認
        await db_session.commit()
        saved_user = await user_crud.get_by_username(db_session, "newuser")
        assert saved_user is not None
        assert saved_user.id == user.id
    
    async def test_create_admin_user(self, db_session):
        """管理者ユーザー作成のテスト"""
        admin_in = AdminUserCreate(username="newadmin", fullname="New Admin", is_admin=True)
        admin = await user_crud.create(db_session, admin_in)
        
        assert admin.username == "newadmin"
        assert admin.fullname == "New Admin"
        assert admin.is_admin is True
        
        # DBに保存されていることを確認
        await db_session.commit()
        saved_admin = await user_crud.get_by_username(db_session, "newadmin")
        assert saved_admin is not None
        assert saved_admin.is_admin is True
    
    async def test_create_user_without_fullname(self, db_session):
        """fullnameなしでのユーザー作成テスト"""
        user_in = UserCreate(username="nofullname")
        user = await user_crud.create(db_session, user_in)
        
        assert user.username == "nofullname"
        assert user.fullname is None
        
        # DBに保存されていることを確認
        await db_session.commit()
        saved_user = await user_crud.get_by_username(db_session, "nofullname")
        assert saved_user is not None
        assert saved_user.fullname is None
    
    async def test_create_duplicate_username(self, db_session, db_test_user):
        """重複ユーザー名でのユーザー作成テスト（失敗ケース）"""
        # IntegrityErrorが発生するようにモック
        with patch.object(db_session, 'flush', side_effect=IntegrityError("Duplicate username", None, None)):
            user_in = UserCreate(username=db_test_user.username)
            with pytest.raises(IntegrityError):
                await user_crud.create(db_session, user_in)
    
    async def test_get_all_users(self, db_session, db_test_user, db_test_admin):
        """全ユーザー取得のテスト"""
        users = await user_crud.get_all_users(db_session)
        
        # 少なくとも2人のユーザーがいることを確認
        assert len(users) >= 2
        
        # テストユーザーとテスト管理者が含まれていることを確認
        user_ids = [user.id for user in users]
        assert db_test_user.id in user_ids
        assert db_test_admin.id in user_ids
    
    async def test_get_by_id(self, db_session, db_test_user):
        """IDによるユーザー取得テスト"""
        user = await user_crud.get_by_id(db_session, db_test_user.id)
        assert user is not None
        assert user.id == db_test_user.id
        assert user.username == db_test_user.username
        
        # 存在しないIDの場合はNoneを返す
        non_existent_id = uuid.uuid4()
        user = await user_crud.get_by_id(db_session, non_existent_id)
        assert user is None
    
    async def test_get_by_username(self, db_session, db_test_user):
        """ユーザー名によるユーザー取得テスト"""
        user = await user_crud.get_by_username(db_session, db_test_user.username)
        assert user is not None
        assert user.id == db_test_user.id
        
        # 存在しないユーザー名の場合はNoneを返す
        user = await user_crud.get_by_username(db_session, "nonexistent")
        assert user is None
    
    async def test_get_by_user_id(self, db_session, db_test_user):
        """Auth ServiceのユーザーIDによるユーザー取得テスト"""
        # user_idを設定
        db_test_user.user_id = uuid.uuid4()
        await db_session.commit()
        
        user = await user_crud.get_by_user_id(db_session, db_test_user.user_id)
        assert user is not None
        assert user.id == db_test_user.id
        
        # 存在しないユーザーIDの場合はNoneを返す
        non_existent_id = uuid.uuid4()
        user = await user_crud.get_by_user_id(db_session, non_existent_id)
        assert user is None
    
    async def test_update_user(self, db_session, db_test_user):
        """ユーザー情報更新テスト"""
        new_username = "updated_username"
        new_fullname = "Updated User"
        user_update = UserUpdate(username=new_username, fullname=new_fullname)
        updated_user = await user_crud.update(db_session, db_test_user, user_update)
        await db_session.commit()
        
        assert updated_user.username == new_username
        assert updated_user.fullname == new_fullname
        
        # 更新がDBに反映されていることを確認
        db_user = await user_crud.get_by_id(db_session, db_test_user.id)
        assert db_user.username == new_username
        assert db_user.fullname == new_fullname
    
    async def test_update_user_username_only(self, db_session, db_test_user):
        """ユーザー名のみの更新テスト"""
        new_username = "username_only"
        user_update = UserUpdate(username=new_username)
        updated_user = await user_crud.update(db_session, db_test_user, user_update)
        await db_session.commit()
        
        assert updated_user.username == new_username
        assert updated_user.fullname == db_test_user.fullname  # 変更なし
        
        # 更新がDBに反映されていることを確認
        db_user = await user_crud.get_by_id(db_session, db_test_user.id)
        assert db_user.username == new_username
    
    async def test_update_user_fullname_only(self, db_session, db_test_user):
        """フルネームのみの更新テスト"""
        new_fullname = "Fullname Only"
        user_update = UserUpdate(fullname=new_fullname)
        updated_user = await user_crud.update(db_session, db_test_user, user_update)
        await db_session.commit()
        
        assert updated_user.username == db_test_user.username  # 変更なし
        assert updated_user.fullname == new_fullname
        
        # 更新がDBに反映されていることを確認
        db_user = await user_crud.get_by_id(db_session, db_test_user.id)
        assert db_user.fullname == new_fullname
    
    async def test_update_user_status(self, db_session, db_test_user):
        """ユーザーステータス更新テスト"""
        # 非アクティブに更新
        user_update = UserUpdate(is_active=False)
        updated_user = await user_crud.update(db_session, db_test_user, user_update)
        await db_session.commit()
        
        assert updated_user.is_active is False
        
        # DBに反映されていることを確認
        db_user = await user_crud.get_by_id(db_session, db_test_user.id)
        assert db_user.is_active is False
    
    async def test_update_user_admin_status(self, db_session, db_test_user):
        """ユーザー管理者ステータス更新テスト"""
        # 管理者に更新
        user_update = UserUpdate(is_admin=True)
        updated_user = await user_crud.update(db_session, db_test_user, user_update)
        await db_session.commit()
        
        assert updated_user.is_admin is True
        
        # DBに反映されていることを確認
        db_user = await user_crud.get_by_id(db_session, db_test_user.id)
        assert db_user.is_admin is True
    
    async def test_update_user_duplicate_username(self, db_session, db_test_user, db_test_admin):
        """重複ユーザー名での更新テスト（失敗ケース）"""
        # IntegrityErrorが発生するようにモック
        with patch.object(db_session, 'flush', side_effect=IntegrityError("Duplicate username", None, None)):
            user_update = UserUpdate(username=db_test_admin.username)
            with pytest.raises(IntegrityError):
                await user_crud.update(db_session, db_test_user, user_update)
    
    async def test_delete_user(self, db_session, db_test_user):
        """ユーザー削除テスト"""
        await user_crud.delete(db_session, db_test_user)
        await db_session.commit()
        
        # 削除されていることを確認
        deleted_user = await user_crud.get_by_id(db_session, db_test_user.id)
        assert deleted_user is None
    
    async def test_sync_user(self, db_session):
        """ユーザー同期テスト（新規作成）"""
        user_id = uuid.uuid4()
        username = "syncuser"
        fullname = "Sync User"
        is_admin = False
        is_active = True
        
        # 新規ユーザーの同期
        synced_user = await user_crud.sync_user(
            db=db_session,
            user_id=user_id,
            username=username,
            fullname=fullname,
            is_admin=is_admin,
            is_active=is_active
        )
        await db_session.commit()
        
        assert synced_user.user_id == user_id
        assert synced_user.username == username
        assert synced_user.fullname == fullname
        assert synced_user.is_admin is False
        assert synced_user.is_active is True
        
        # DBに保存されていることを確認
        db_user = await user_crud.get_by_user_id(db_session, user_id)
        assert db_user is not None
        assert db_user.username == username
    
    async def test_sync_user_update(self, db_session):
        """ユーザー同期テスト（既存ユーザーの更新）"""
        # 最初にユーザーを作成
        user_id = uuid.uuid4()
        username = "syncuserupdate"
        fullname = "Sync User Update"
        
        synced_user = await user_crud.sync_user(
            db=db_session,
            user_id=user_id,
            username=username,
            fullname=fullname,
            is_admin=False,
            is_active=True
        )
        await db_session.commit()
        
        # 同じuser_idで更新
        new_username = "syncuserupdated"
        new_fullname = "Sync User Updated"
        
        updated_user = await user_crud.sync_user(
            db=db_session,
            user_id=user_id,
            username=new_username,
            fullname=new_fullname,
            is_admin=True,
            is_active=False
        )
        await db_session.commit()
        
        assert updated_user.user_id == user_id
        assert updated_user.username == new_username
        assert updated_user.fullname == new_fullname
        assert updated_user.is_admin is True
        assert updated_user.is_active is False
        
        # DBに反映されていることを確認
        db_user = await user_crud.get_by_user_id(db_session, user_id)
        assert db_user is not None
        assert db_user.username == new_username
        assert db_user.fullname == new_fullname
    
    async def test_sync_user_without_fullname(self, db_session):
        """フルネームなしでのユーザー同期テスト"""
        user_id = uuid.uuid4()
        username = "syncusernofullname"
        
        synced_user = await user_crud.sync_user(
            db=db_session,
            user_id=user_id,
            username=username,
            is_admin=False,
            is_active=True
        )
        await db_session.commit()
        
        assert synced_user.user_id == user_id
        assert synced_user.username == username
        assert synced_user.fullname is None
        
        # DBに保存されていることを確認
        db_user = await user_crud.get_by_user_id(db_session, user_id)
        assert db_user is not None
        assert db_user.username == username
        assert db_user.fullname is None
    
    async def test_search_users(self, db_session, db_test_user, db_test_admin):
        """ユーザー検索テスト"""
        from app.schemas.user import UserSearchParams
        
        # ユーザー名による検索
        params = UserSearchParams(username=db_test_user.username[:4])
        users = await user_crud.search_users(db_session, params)
        assert len(users) >= 1
        assert any(user.username == db_test_user.username for user in users)
        
        # フルネームによる検索
        params = UserSearchParams(fullname=db_test_user.fullname[:4])
        users = await user_crud.search_users(db_session, params)
        assert len(users) >= 1
        assert any(user.fullname == db_test_user.fullname for user in users)
        
        # 管理者フラグによる検索
        params = UserSearchParams(is_admin=True)
        users = await user_crud.search_users(db_session, params)
        assert len(users) >= 1
        assert any(user.username == db_test_admin.username for user in users)
        
        # アクティブフラグによる検索
        params = UserSearchParams(is_active=True)
        users = await user_crud.search_users(db_session, params)
        assert len(users) >= 2
        
        # 複合条件による検索
        params = UserSearchParams(
            username=db_test_admin.username[:4],
            is_admin=True
        )
        users = await user_crud.search_users(db_session, params)
        assert len(users) >= 1
        assert any(user.username == db_test_admin.username for user in users)
