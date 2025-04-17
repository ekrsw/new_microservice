import pytest
import uuid
from app.crud.user import user as user_crud
from app.schemas.user import UserCreate, AdminUserCreate, UserUpdate
from app.models.user import AuthUser
from app.core.security import verify_password
from sqlalchemy.exc import IntegrityError
from unittest.mock import patch, MagicMock

class TestCRUDUser:
    async def test_create_user(self, db_session):
        """一般ユーザー作成のテスト"""
        user_in = UserCreate(username="newuser", password="newpassword")
        user = await user_crud.create(db_session, user_in)
        
        assert user.username == "newuser"
        assert user.is_admin is False
        assert user.is_active is True
        assert user.hashed_password != "newpassword"  # パスワードはハッシュ化される
        
        # DBに保存されていることを確認
        await db_session.commit()
        saved_user = await user_crud.get_by_username(db_session, "newuser")
        assert saved_user is not None
        assert saved_user.id == user.id
    
    async def test_create_admin_user(self, db_session):
        """管理者ユーザー作成のテスト"""
        admin_in = AdminUserCreate(username="newadmin", password="adminpass", is_admin=True)
        admin = await user_crud.create(db_session, admin_in)
        
        assert admin.username == "newadmin"
        assert admin.is_admin is True
        
        # DBに保存されていることを確認
        await db_session.commit()
        saved_admin = await user_crud.get_by_username(db_session, "newadmin")
        assert saved_admin is not None
        assert saved_admin.is_admin is True
    
    async def test_create_duplicate_username(self, db_session, db_test_user):
        """重複ユーザー名でのユーザー作成テスト（失敗ケース）"""
        # IntegrityErrorが発生するようにモック
        with patch.object(db_session, 'flush', side_effect=IntegrityError("Duplicate username", None, None)):
            user_in = UserCreate(username=db_test_user.username, password="somepassword")
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
    
    async def test_update_user(self, db_session, db_test_user):
        """ユーザー情報更新テスト"""
        new_username = "updated_username"
        user_update = UserUpdate(username=new_username)
        updated_user = await user_crud.update(db_session, db_test_user, user_update)
        await db_session.commit()
        
        assert updated_user.username == new_username
        
        # 更新がDBに反映されていることを確認
        db_user = await user_crud.get_by_id(db_session, db_test_user.id)
        assert db_user.username == new_username
    
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
    
    async def test_update_password(self, db_session, db_test_user, test_user_data):
        """パスワード更新テスト"""
        new_password = "new_password123"
        updated_user = await user_crud.update_password(db_session, db_test_user, new_password)
        await db_session.commit()
        
        # パスワードが更新されていることを確認
        assert verify_password(new_password, updated_user.hashed_password) is True
        assert verify_password(test_user_data["password"], updated_user.hashed_password) is False
        
        # DBに反映されていることを確認
        db_user = await user_crud.get_by_id(db_session, db_test_user.id)
        assert verify_password(new_password, db_user.hashed_password) is True
    
    async def test_delete_user(self, db_session, db_test_user):
        """ユーザー削除テスト"""
        await user_crud.delete(db_session, db_test_user)
        await db_session.commit()
        
        # 削除されていることを確認
        deleted_user = await user_crud.get_by_id(db_session, db_test_user.id)
        assert deleted_user is None
    
    async def test_delete_nonexistent_user(self, db_session):
        """存在しないユーザーの削除テスト"""
        non_existent_user = AuthUser(id=uuid.uuid4(), username="nonexistent")
        with pytest.raises(ValueError, match="User not found"):
            await user_crud.delete(db_session, non_existent_user)
