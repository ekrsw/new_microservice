import pytest
from fastapi.testclient import TestClient
import json
from typing import Dict, Any
from uuid import UUID
import uuid
from app.models.user import AuthUser

class TestUserInfoEndpoints:
    """ユーザー情報取得APIエンドポイントのテスト"""
    
    async def test_get_all_users_admin(self, client: TestClient, db_test_user, db_test_admin, admin_auth_headers, api_test_dependencies):
        """管理者による全ユーザー取得成功テスト"""
        response = client.get("/api/v1/auth/users", headers=admin_auth_headers)
        
        assert response.status_code == 200
        users = response.json()
        assert isinstance(users, list)
        assert len(users) >= 2  # 少なくともテストユーザーと管理者の2つが存在する
        
        # ユーザー情報の構造を検証
        for user in users:
            assert "id" in user
            assert "username" in user
            assert "is_admin" in user
    
    async def test_get_all_users_non_admin(self, client: TestClient, user_auth_headers, api_test_dependencies):
        """権限のないユーザーによる全ユーザー取得試行テスト"""
        response = client.get("/api/v1/auth/users", headers=user_auth_headers)
        
        assert response.status_code == 403
        assert "detail" in response.json()
    
    async def test_get_user_me(self, client: TestClient, test_user_data, user_auth_headers, api_test_dependencies):
        """自分自身のユーザー情報取得テスト"""
        response = client.get("/api/v1/auth/user/me", headers=user_auth_headers)
        
        assert response.status_code == 200
        assert "id" in response.json()
        assert "username" in response.json()
        assert response.json()["username"] == test_user_data["username"]
        assert "is_admin" in response.json()
        assert response.json()["is_admin"] is False
    
    async def test_get_user_by_id_self(self, client: TestClient, db_test_user, test_user_data, user_auth_headers, api_test_dependencies):
        """ユーザーが自分自身のIDで情報取得するテスト"""
        user_id = db_test_user.id
        
        response = client.get(f"/api/v1/auth/user/{user_id}", headers=user_auth_headers)
        
        assert response.status_code == 200
        assert "id" in response.json()
        assert response.json()["id"] == str(user_id)
        assert "username" in response.json()
        assert response.json()["username"] == test_user_data["username"]
    
    async def test_get_user_by_id_admin(self, client: TestClient, db_test_user, test_user_data, admin_auth_headers, api_test_dependencies):
        """管理者が他のユーザーIDで情報取得するテスト"""
        user_id = db_test_user.id
        
        response = client.get(f"/api/v1/auth/user/{user_id}", headers=admin_auth_headers)
        
        assert response.status_code == 200
        assert "id" in response.json()
        assert response.json()["id"] == str(user_id)
        assert "username" in response.json()
        assert response.json()["username"] == test_user_data["username"]
    
    async def test_get_user_by_id_other_user(self, client: TestClient, db_test_admin, user_auth_headers, api_test_dependencies):
        """一般ユーザーが他のユーザーIDで情報取得しようとするテスト"""
        admin_id = db_test_admin.id  # 管理者のID
        
        response = client.get(f"/api/v1/auth/user/{admin_id}", headers=user_auth_headers)
        
        assert response.status_code == 403
        assert "detail" in response.json()
    
    async def test_get_nonexistent_user(self, client: TestClient, admin_auth_headers, api_test_dependencies):
        """存在しないユーザーIDでの情報取得テスト"""
        nonexistent_id = str(uuid.uuid4())
        
        response = client.get(f"/api/v1/auth/user/{nonexistent_id}", headers=admin_auth_headers)
        
        assert response.status_code == 404
        assert "detail" in response.json()


class TestUserUpdateEndpoints:
    """ユーザー情報更新APIエンドポイントのテスト"""
    
    async def test_update_user_self(self, client: TestClient, db_test_user, user_auth_headers, api_test_dependencies):
        """ユーザーが自分の情報を更新するテスト"""
        user_id = db_test_user.id
        update_data = {
            "username": "updatedusername"
        }
        
        response = client.put(f"/api/v1/auth/update/user/{user_id}", json=update_data, headers=user_auth_headers)
        
        assert response.status_code == 200
        assert "id" in response.json()
        assert response.json()["id"] == str(user_id)
        assert "username" in response.json()
        assert response.json()["username"] == update_data["username"]
        assert "is_admin" in response.json()
        assert response.json()["is_admin"] is False
    
    async def test_update_user_admin(self, client: TestClient, db_test_user, admin_auth_headers, api_test_dependencies):
        """管理者が他のユーザー情報を更新するテスト"""
        user_id = db_test_user.id
        update_data = {
            "username": "adminupdatedname"
        }
        
        response = client.put(f"/api/v1/auth/update/user/{user_id}", json=update_data, headers=admin_auth_headers)
        
        assert response.status_code == 200
        assert "id" in response.json()
        assert response.json()["id"] == str(user_id)
        assert "username" in response.json()
        assert response.json()["username"] == update_data["username"]
    
    async def test_update_admin_status_by_admin(self, client: TestClient, db_test_user, admin_auth_headers, api_test_dependencies):
        """管理者がユーザーの管理者権限を変更するテスト"""
        user_id = db_test_user.id
        update_data = {
            "is_admin": True
        }
        
        response = client.put(f"/api/v1/auth/update/user/{user_id}", json=update_data, headers=admin_auth_headers)
        
        assert response.status_code == 200
        assert "id" in response.json()
        assert response.json()["id"] == str(user_id)
        assert "is_admin" in response.json()
        assert response.json()["is_admin"] is True
    
    async def test_update_other_user(self, client: TestClient, db_test_admin, user_auth_headers, api_test_dependencies):
        """一般ユーザーが他のユーザー情報を更新しようとするテスト"""
        admin_id = db_test_admin.id
        update_data = {
            "username": "attemptchange"
        }
        
        response = client.put(f"/api/v1/auth/update/user/{admin_id}", json=update_data, headers=user_auth_headers)
        
        assert response.status_code == 403
        assert "detail" in response.json()
    
    async def test_update_self_admin_status(self, client: TestClient, db_test_user, user_auth_headers, api_test_dependencies):
        """一般ユーザーが自分の管理者権限を変更しようとするテスト"""
        user_id = db_test_user.id
        update_data = {
            "is_admin": True
        }
        
        response = client.put(f"/api/v1/auth/update/user/{user_id}", json=update_data, headers=user_auth_headers)
        
        assert response.status_code == 403
        assert "detail" in response.json()
    
    async def test_update_nonexistent_user(self, client: TestClient, admin_auth_headers, api_test_dependencies):
        """存在しないユーザーの更新試行テスト"""
        nonexistent_id = str(uuid.uuid4())
        update_data = {
            "username": "nonexistentupdate"
        }
        
        response = client.put(f"/api/v1/auth/update/user/{nonexistent_id}", json=update_data, headers=admin_auth_headers)
        
        assert response.status_code == 404
        assert "detail" in response.json()
