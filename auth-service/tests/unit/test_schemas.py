import pytest
from pydantic import ValidationError
from app.schemas.user import (
    UserCreate,
    AdminUserCreate,
    PasswordUpdate,
    AdminPasswordUpdate,
    UserUpdate,
    Token,
    RefreshTokenRequest,
    LogoutRequest,
    TokenVerifyRequest,
    TokenVerifyResponse
)
import uuid

class TestUserSchemas:
    def test_user_create_valid(self):
        """有効なUserCreateスキーマのテスト"""
        user_data = {"username": "testuser", "password": "password123"}
        user = UserCreate(**user_data)
        assert user.username == "testuser"
        assert user.password == "password123"
    
    def test_user_create_invalid_short_username(self):
        """無効なUserCreateスキーマ（短すぎるユーザー名）のテスト"""
        user_data = {"username": "", "password": "password123"}
        with pytest.raises(ValidationError):
            UserCreate(**user_data)
    
    def test_user_create_invalid_long_username(self):
        """無効なUserCreateスキーマ（長すぎるユーザー名）のテスト"""
        user_data = {"username": "a" * 51, "password": "password123"}
        with pytest.raises(ValidationError):
            UserCreate(**user_data)
    
    def test_user_create_invalid_short_password(self):
        """無効なUserCreateスキーマ（短すぎるパスワード）のテスト"""
        user_data = {"username": "testuser", "password": ""}
        with pytest.raises(ValidationError):
            UserCreate(**user_data)
    
    def test_user_create_invalid_long_password(self):
        """無効なUserCreateスキーマ（長すぎるパスワード）のテスト"""
        user_data = {"username": "testuser", "password": "a" * 17}
        with pytest.raises(ValidationError):
            UserCreate(**user_data)
    
    def test_admin_user_create_valid(self):
        """有効なAdminUserCreateスキーマのテスト"""
        admin_data = {"username": "admin", "password": "adminpass", "is_admin": True}
        admin = AdminUserCreate(**admin_data)
        assert admin.username == "admin"
        assert admin.password == "adminpass"
        assert admin.is_admin is True
    
    def test_admin_user_create_default_is_admin(self):
        """is_adminが指定されていない場合のAdminUserCreateスキーマのテスト"""
        admin_data = {"username": "admin", "password": "adminpass"}
        admin = AdminUserCreate(**admin_data)
        assert admin.is_admin is False  # デフォルト値はFalse
    
    def test_password_update_valid(self):
        """有効なパスワード更新スキーマのテスト"""
        data = {"current_password": "oldpass", "new_password": "newpass"}
        pwd_update = PasswordUpdate(**data)
        assert pwd_update.current_password == "oldpass"
        assert pwd_update.new_password == "newpass"
    
    def test_password_update_invalid_same_password(self):
        """無効なパスワード更新スキーマ（同じパスワード）のテスト"""
        data = {"current_password": "samepass", "new_password": "samepass"}
        with pytest.raises(ValidationError):
            PasswordUpdate(**data)
    
    def test_password_update_invalid_long_password(self):
        """無効なパスワード更新スキーマ（長すぎるパスワード）のテスト"""
        data = {"current_password": "validpass", "new_password": "a" * 17}
        with pytest.raises(ValidationError):
            PasswordUpdate(**data)
    
    def test_admin_password_update_valid(self):
        """有効な管理者パスワード更新スキーマのテスト"""
        user_id = uuid.uuid4()
        data = {"user_id": user_id, "new_password": "newadminpass"}
        admin_pwd_update = AdminPasswordUpdate(**data)
        assert admin_pwd_update.user_id == user_id
        assert admin_pwd_update.new_password == "newadminpass"
    
    def test_admin_password_update_invalid_long_password(self):
        """無効な管理者パスワード更新スキーマ（長すぎるパスワード）のテスト"""
        user_id = uuid.uuid4()
        data = {"user_id": user_id, "new_password": "a" * 17}
        with pytest.raises(ValidationError):
            AdminPasswordUpdate(**data)
    
    def test_user_update_valid(self):
        """有効なユーザー更新スキーマのテスト"""
        data = {"username": "updateduser", "is_active": False, "is_admin": True}
        user_update = UserUpdate(**data)
        assert user_update.username == "updateduser"
        assert user_update.is_active is False
        assert user_update.is_admin is True
    
    def test_user_update_partial(self):
        """部分的なユーザー更新スキーマのテスト"""
        # usernameのみ更新
        data1 = {"username": "updateduser"}
        user_update1 = UserUpdate(**data1)
        assert user_update1.username == "updateduser"
        assert user_update1.is_active is None
        assert user_update1.is_admin is False  # is_adminのデフォルト値はFalse
        
        # is_activeのみ更新
        data2 = {"is_active": False}
        user_update2 = UserUpdate(**data2)
        assert user_update2.username is None
        assert user_update2.is_active is False
        assert user_update2.is_admin is False  # is_adminのデフォルト値はFalse
        
        # is_adminのみ更新
        data3 = {"is_admin": True}
        user_update3 = UserUpdate(**data3)
        assert user_update3.username is None
        assert user_update3.is_active is None
        assert user_update3.is_admin is True
    
    def test_user_update_invalid_long_username(self):
        """無効なユーザー更新スキーマ（長すぎるユーザー名）のテスト"""
        data = {"username": "a" * 51}
        with pytest.raises(ValidationError):
            UserUpdate(**data)


class TestTokenSchemas:
    def test_token_valid(self):
        """有効なTokenスキーマのテスト"""
        data = {
            "access_token": "access_token_value",
            "refresh_token": "refresh_token_value",
            "token_type": "bearer"
        }
        token = Token(**data)
        assert token.access_token == "access_token_value"
        assert token.refresh_token == "refresh_token_value"
        assert token.token_type == "bearer"
    
    def test_token_default_token_type(self):
        """デフォルトのトークンタイプを持つTokenスキーマのテスト"""
        data = {
            "access_token": "access_token_value",
            "refresh_token": "refresh_token_value"
        }
        token = Token(**data)
        assert token.token_type == "bearer"
    
    def test_refresh_token_request_valid(self):
        """有効なRefreshTokenRequestスキーマのテスト"""
        data = {
            "refresh_token": "refresh_token_value",
            "access_token": "access_token_value"
        }
        request = RefreshTokenRequest(**data)
        assert request.refresh_token == "refresh_token_value"
        assert request.access_token == "access_token_value"
    
    def test_logout_request_valid(self):
        """有効なLogoutRequestスキーマのテスト"""
        data = {
            "refresh_token": "refresh_token_value",
            "access_token": "access_token_value"
        }
        request = LogoutRequest(**data)
        assert request.refresh_token == "refresh_token_value"
        assert request.access_token == "access_token_value"
    
    def test_token_verify_request_valid(self):
        """有効なTokenVerifyRequestスキーマのテスト"""
        data = {"token": "token_value"}
        request = TokenVerifyRequest(**data)
        assert request.token == "token_value"
    
    def test_token_verify_response_valid(self):
        """有効なTokenVerifyResponseスキーマのテスト"""
        data = {
            "valid": True,
            "user_id": "user123",
            "username": "testuser",
            "roles": ["user", "admin"]
        }
        response = TokenVerifyResponse(**data)
        assert response.valid is True
        assert response.user_id == "user123"
        assert response.username == "testuser"
        assert response.roles == ["user", "admin"]
        assert response.error is None
    
    def test_token_verify_response_invalid(self):
        """無効なTokenVerifyResponseスキーマのテスト"""
        data = {
            "valid": False,
            "error": "Invalid token"
        }
        response = TokenVerifyResponse(**data)
        assert response.valid is False
        assert response.user_id is None
        assert response.username is None
        assert response.roles == []
        assert response.error == "Invalid token"
