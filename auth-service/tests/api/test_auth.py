import pytest
from fastapi.testclient import TestClient
import json
from typing import Dict, Any
from app.models.user import AuthUser
from app.core.security import verify_password

class TestAuthEndpoints:
    """認証APIエンドポイントのテスト"""
    
    async def test_login_success(self, client: TestClient, db_test_user, test_user_data, api_test_dependencies):
        """ログイン成功のテスト"""
        data = {
            "username": test_user_data["username"],
            "password": test_user_data["password"]
        }
        
        response = client.post("/api/v1/auth/login", data=data)
        
        assert response.status_code == 200
        assert "access_token" in response.json()
        assert "refresh_token" in response.json()
        assert response.json()["token_type"] == "bearer"
    
    async def test_login_invalid_username(self, client: TestClient, api_test_dependencies):
        """無効なユーザー名でのログイン失敗テスト"""
        data = {
            "username": "nonexistent",
            "password": "anypassword"
        }
        
        response = client.post("/api/v1/auth/login", data=data)
        
        assert response.status_code == 401
        assert "detail" in response.json()
    
    async def test_login_invalid_password(self, client: TestClient, db_test_user, test_user_data, api_test_dependencies):
        """無効なパスワードでのログイン失敗テスト"""
        data = {
            "username": test_user_data["username"],
            "password": "wrongpassword"
        }
        
        response = client.post("/api/v1/auth/login", data=data)
        
        assert response.status_code == 401
        assert "detail" in response.json()
    
    async def test_token_refresh(self, client: TestClient, db_test_user, user_token, user_refresh_token, api_test_dependencies):
        """トークンリフレッシュのテスト"""
        data = {
            "access_token": user_token,
            "refresh_token": user_refresh_token
        }
        
        response = client.post("/api/v1/auth/refresh", json=data)
        
        assert response.status_code == 200
        assert "access_token" in response.json()
        assert "refresh_token" in response.json()
        assert response.json()["token_type"] == "bearer"
        # 新しいトークンは古いトークンと異なる
        assert response.json()["access_token"] != user_token
        assert response.json()["refresh_token"] != user_refresh_token
    
    async def test_token_refresh_invalid(self, client: TestClient, db_test_user, user_token, api_test_dependencies):
        """無効なリフレッシュトークンでのリフレッシュ失敗テスト"""
        data = {
            "access_token": user_token,
            "refresh_token": "invalid_refresh_token"
        }
        
        response = client.post("/api/v1/auth/refresh", json=data)
        
        assert response.status_code == 401
        assert "detail" in response.json()
    
    async def test_logout(self, client: TestClient, db_test_user, user_token, user_refresh_token, api_test_dependencies):
        """ログアウトのテスト"""
        data = {
            "access_token": user_token,
            "refresh_token": user_refresh_token
        }
        
        response = client.post("/api/v1/auth/logout", json=data)
        
        assert response.status_code == 200
        assert "detail" in response.json()

        # ログアウト後は、リフレッシュトークンが無効化されていることを確認
        refresh_data = {
            "access_token": user_token,
            "refresh_token": user_refresh_token
        }
        refresh_response = client.post("/api/v1/auth/refresh", json=refresh_data)
        assert refresh_response.status_code == 401
    
    async def test_update_password(self, client: TestClient, db_test_user, test_user_data, user_auth_headers, api_test_dependencies):
        """パスワード更新のテスト"""
        # テスト用データの準備
        username = test_user_data["username"]
        old_password = test_user_data["password"]
        new_password = "newpassword123"
        
        # パスワード更新リクエスト
        update_data = {
            "current_password": old_password,
            "new_password": new_password
        }
        
        update_response = client.post("/api/v1/auth/update/password", json=update_data, headers=user_auth_headers)
        
        # 更新が成功したことを確認
        assert update_response.status_code == 200
        # APIは更新されたユーザー情報を返す
        assert "id" in update_response.json()
        assert "username" in update_response.json()
        
        # ユーザー情報が返されていることを確認
        response_data = update_response.json()
        assert response_data["username"] == username
    
    async def test_update_password_invalid_current(self, client: TestClient, db_test_user, user_auth_headers, api_test_dependencies):
        """現在のパスワードが無効な場合のパスワード更新失敗テスト"""
        data = {
            "current_password": "wrongpassword",
            "new_password": "newpassword123"
        }
        
        response = client.post("/api/v1/auth/update/password", json=data, headers=user_auth_headers)
        
        assert response.status_code == 401
        assert "detail" in response.json()
    
    async def test_update_password_same(self, client: TestClient, db_test_user, test_user_data, user_auth_headers, api_test_dependencies):
        """新しいパスワードが現在のパスワードと同じ場合のパスワード更新失敗テスト"""
        data = {
            "current_password": test_user_data["password"],
            "new_password": test_user_data["password"]
        }
        
        response = client.post("/api/v1/auth/update/password", json=data, headers=user_auth_headers)
        
        assert response.status_code == 422
        assert "detail" in response.json()
    
    async def test_verify_token_valid(self, client: TestClient, user_token, api_test_dependencies):
        """有効なトークン検証のテスト"""
        data = {
            "token": user_token
        }
        
        response = client.post("/api/v1/auth/verify", json=data)
        
        assert response.status_code == 200
        assert response.json()["valid"] is True
        assert "user_id" in response.json()
        assert "username" in response.json()
    
    async def test_verify_token_invalid(self, client: TestClient, api_test_dependencies):
        """無効なトークン検証のテスト"""
        data = {
            "token": "invalid_token"
        }
        
        response = client.post("/api/v1/auth/verify", json=data)
        
        # APIの実装では無効なトークンでも200を返し、validフラグがFalseになる
        assert response.status_code == 200
        assert response.json()["valid"] is False
    
    async def test_admin_update_password(
        self, client: TestClient, db_test_user, db_test_admin, test_user_data,
        admin_auth_headers, api_test_dependencies
    ):
        """管理者によるパスワード更新のテスト"""
        # テスト用データの準備
        username = test_user_data["username"]
        new_password = "adminset123"
        user_id = db_test_user.id
        
        # 管理者によるパスワード更新リクエスト
        update_data = {
            "user_id": str(user_id),
            "new_password": new_password
        }
        
        update_response = client.post("/api/v1/auth/admin/update/password", json=update_data, headers=admin_auth_headers)
        
        # 更新が成功したことを確認
        assert update_response.status_code == 200
        # APIは更新されたユーザー情報を返す
        assert "id" in update_response.json()
        assert "username" in update_response.json()
        
        # ユーザー情報が返されていることを確認
        response_data = update_response.json()
        assert response_data["username"] == username
    
    async def test_admin_update_password_no_admin_role(
        self, client: TestClient, db_session, db_test_user, db_test_admin, 
        user_auth_headers, api_test_dependencies
    ):
        """管理者権限のないユーザーによるパスワード更新失敗テスト"""
        data = {
            "user_id": str(db_test_admin.id),
            "new_password": "userset123"
        }
        
        response = client.post("/api/v1/auth/admin/update/password", json=data, headers=user_auth_headers)
        
        assert response.status_code == 403
        assert "detail" in response.json()
    
    async def test_admin_update_nonexistent_user(
        self, client: TestClient, db_test_admin, admin_auth_headers, api_test_dependencies
    ):
        """存在しないユーザーのパスワード更新失敗テスト"""
        import uuid
        nonexistent_id = str(uuid.uuid4())
        data = {
            "user_id": nonexistent_id,
            "new_password": "newpassword123"
        }
        
        response = client.post("/api/v1/auth/admin/update/password", json=data, headers=admin_auth_headers)
        
        assert response.status_code == 404
        assert "detail" in response.json()
