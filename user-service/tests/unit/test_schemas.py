import pytest
from pydantic import ValidationError
from app.schemas.user import (
    UserCreate,
    AdminUserCreate,
    UserUpdate,
    UserProfile,
    UserSearchParams
)
import uuid

class TestUserSchemas:
    def test_user_create_valid(self):
        """有効なUserCreateスキーマのテスト"""
        user_data = {"username": "testuser", "fullname": "Test User"}
        user = UserCreate(**user_data)
        assert user.username == "testuser"
        assert user.fullname == "Test User"
    
    def test_user_create_without_fullname(self):
        """フルネームなしでのUserCreateスキーマのテスト"""
        user_data = {"username": "testuser"}
        user = UserCreate(**user_data)
        assert user.username == "testuser"
        assert user.fullname is None
    
    def test_user_create_invalid_short_username(self):
        """無効なUserCreateスキーマ（短すぎるユーザー名）のテスト"""
        user_data = {"username": "", "fullname": "Test User"}
        with pytest.raises(ValidationError):
            UserCreate(**user_data)
    
    def test_user_create_invalid_long_username(self):
        """無効なUserCreateスキーマ（長すぎるユーザー名）のテスト"""
        user_data = {"username": "a" * 51, "fullname": "Test User"}
        with pytest.raises(ValidationError):
            UserCreate(**user_data)
    
    def test_user_create_invalid_long_fullname(self):
        """無効なUserCreateスキーマ（長すぎるフルネーム）のテスト"""
        user_data = {"username": "testuser", "fullname": "a" * 51}
        with pytest.raises(ValidationError):
            UserCreate(**user_data)
    
    def test_admin_user_create_valid(self):
        """有効なAdminUserCreateスキーマのテスト"""
        admin_data = {"username": "admin", "fullname": "Admin User", "is_admin": True}
        admin = AdminUserCreate(**admin_data)
        assert admin.username == "admin"
        assert admin.fullname == "Admin User"
        assert admin.is_admin is True
    
    def test_admin_user_create_default_is_admin(self):
        """is_adminが指定されていない場合のAdminUserCreateスキーマのテスト"""
        admin_data = {"username": "admin", "fullname": "Admin User"}
        admin = AdminUserCreate(**admin_data)
        assert admin.is_admin is False  # デフォルト値はFalse
    
    def test_user_update_valid(self):
        """有効なユーザー更新スキーマのテスト"""
        data = {"username": "updateduser", "fullname": "Updated User", "is_active": False, "is_admin": True}
        user_update = UserUpdate(**data)
        assert user_update.username == "updateduser"
        assert user_update.fullname == "Updated User"
        assert user_update.is_active is False
        assert user_update.is_admin is True
    
    def test_user_update_partial(self):
        """部分的なユーザー更新スキーマのテスト"""
        # usernameのみ更新
        data1 = {"username": "updateduser"}
        user_update1 = UserUpdate(**data1)
        assert user_update1.username == "updateduser"
        assert user_update1.fullname is None
        assert user_update1.is_active is None
        assert user_update1.is_admin is None
        
        # fullnameのみ更新
        data2 = {"fullname": "Updated User"}
        user_update2 = UserUpdate(**data2)
        assert user_update2.username is None
        assert user_update2.fullname == "Updated User"
        assert user_update2.is_active is None
        assert user_update2.is_admin is None
        
        # is_activeのみ更新
        data3 = {"is_active": False}
        user_update3 = UserUpdate(**data3)
        assert user_update3.username is None
        assert user_update3.fullname is None
        assert user_update3.is_active is False
        assert user_update3.is_admin is None
        
        # is_adminのみ更新
        data4 = {"is_admin": True}
        user_update4 = UserUpdate(**data4)
        assert user_update4.username is None
        assert user_update4.fullname is None
        assert user_update4.is_active is None
        assert user_update4.is_admin is True
    
    def test_user_update_invalid_long_username(self):
        """無効なユーザー更新スキーマ（長すぎるユーザー名）のテスト"""
        data = {"username": "a" * 51}
        with pytest.raises(ValidationError):
            UserUpdate(**data)
    
    def test_user_update_invalid_long_fullname(self):
        """無効なユーザー更新スキーマ（長すぎるフルネーム）のテスト"""
        data = {"fullname": "a" * 51}
        with pytest.raises(ValidationError):
            UserUpdate(**data)
    
    def test_user_profile_valid(self):
        """有効なUserProfileスキーマのテスト"""
        data = {
            "username": "testuser",
            "fullname": "Test User",
            "is_active": True,
            "is_admin": False
        }
        profile = UserProfile(**data)
        assert profile.username == "testuser"
        assert profile.fullname == "Test User"
        assert profile.is_active is True
        assert profile.is_admin is False
    
    def test_user_profile_without_fullname(self):
        """フルネームなしでのUserProfileスキーマのテスト"""
        data = {
            "username": "testuser",
            "is_active": True,
            "is_admin": False
        }
        profile = UserProfile(**data)
        assert profile.username == "testuser"
        assert profile.fullname is None
        assert profile.is_active is True
        assert profile.is_admin is False
    
    def test_user_search_params_valid(self):
        """有効なUserSearchParamsスキーマのテスト"""
        data = {
            "username": "test",
            "fullname": "user",
            "is_active": True,
            "is_admin": False
        }
        params = UserSearchParams(**data)
        assert params.username == "test"
        assert params.fullname == "user"
        assert params.is_active is True
        assert params.is_admin is False
    
    def test_user_search_params_partial(self):
        """部分的なUserSearchParamsスキーマのテスト"""
        # usernameのみ
        data1 = {"username": "test"}
        params1 = UserSearchParams(**data1)
        assert params1.username == "test"
        assert params1.fullname is None
        assert params1.is_active is None
        assert params1.is_admin is None
        
        # fullnameのみ
        data2 = {"fullname": "user"}
        params2 = UserSearchParams(**data2)
        assert params2.username is None
        assert params2.fullname == "user"
        assert params2.is_active is None
        assert params2.is_admin is None
        
        # is_activeのみ
        data3 = {"is_active": True}
        params3 = UserSearchParams(**data3)
        assert params3.username is None
        assert params3.fullname is None
        assert params3.is_active is True
        assert params3.is_admin is None
        
        # is_adminのみ
        data4 = {"is_admin": True}
        params4 = UserSearchParams(**data4)
        assert params4.username is None
        assert params4.fullname is None
        assert params4.is_active is None
        assert params4.is_admin is True
    
    def test_user_search_params_empty(self):
        """空のUserSearchParamsスキーマのテスト"""
        params = UserSearchParams()
        assert params.username is None
        assert params.fullname is None
        assert params.is_active is None
        assert params.is_admin is None
