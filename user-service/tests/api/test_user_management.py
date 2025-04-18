import pytest
from fastapi.testclient import TestClient
from fastapi import status
import uuid

class TestUserManagement:
    @pytest.mark.asyncio
    async def test_get_all_users(self, client: TestClient, api_test_dependencies, db_test_user, db_test_admin):
        """全ユーザー一覧取得テスト"""
        response = client.get("/api/v1/users")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2
        
        # テストユーザーとテスト管理者が含まれていることを確認
        user_ids = [user["id"] for user in data]
        assert str(db_test_user.id) in user_ids
        assert str(db_test_admin.id) in user_ids
    
    @pytest.mark.asyncio
    async def test_get_user_by_id(self, client: TestClient, api_test_dependencies, db_test_user):
        """特定ユーザーの詳細情報取得テスト"""
        response = client.get(f"/api/v1/users/{db_test_user.id}")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["id"] == str(db_test_user.id)
        assert data["username"] == db_test_user.username
        assert data["fullname"] == db_test_user.fullname
        assert data["is_active"] == db_test_user.is_active
        assert data["is_admin"] == db_test_user.is_admin
    
    @pytest.mark.asyncio
    async def test_get_user_nonexistent(self, client: TestClient, api_test_dependencies):
        """存在しないユーザーの詳細情報取得テスト"""
        non_existent_id = uuid.uuid4()
        response = client.get(f"/api/v1/users/{non_existent_id}")
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    @pytest.mark.asyncio
    async def test_create_user(self, client: TestClient, api_test_dependencies):
        """新規ユーザー作成テスト"""
        user_data = {
            "username": "newuser",
            "fullname": "New User",
            "is_admin": False
        }
        
        response = client.post("/api/v1/users/create", json=user_data)
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["username"] == user_data["username"]
        assert data["fullname"] == user_data["fullname"]
        assert data["is_admin"] == user_data["is_admin"]
        assert data["is_active"] is True
        assert "id" in data
        assert "user_id" in data
    
    @pytest.mark.asyncio
    async def test_create_admin_user(self, client: TestClient, api_test_dependencies):
        """新規管理者ユーザー作成テスト"""
        user_data = {
            "username": "newadmin",
            "fullname": "New Admin",
            "is_admin": True
        }
        
        response = client.post("/api/v1/users/create", json=user_data)
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["username"] == user_data["username"]
        assert data["fullname"] == user_data["fullname"]
        assert data["is_admin"] == user_data["is_admin"]
        assert data["is_active"] is True
    
    @pytest.mark.asyncio
    async def test_create_user_without_fullname(self, client: TestClient, api_test_dependencies):
        """フルネームなしでの新規ユーザー作成テスト"""
        user_data = {
            "username": "nofullname",
            "is_admin": False
        }
        
        response = client.post("/api/v1/users/create", json=user_data)
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["username"] == user_data["username"]
        assert data["fullname"] is None
        assert data["is_admin"] == user_data["is_admin"]
    
    @pytest.mark.asyncio
    async def test_create_user_duplicate_username(self, client: TestClient, api_test_dependencies, db_test_user):
        """重複ユーザー名での新規ユーザー作成テスト（失敗ケース）"""
        user_data = {
            "username": db_test_user.username,
            "fullname": "Duplicate User"
        }
        
        response = client.post("/api/v1/users/create", json=user_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    @pytest.mark.asyncio
    async def test_update_user(self, client: TestClient, api_test_dependencies, db_test_user):
        """ユーザー情報更新テスト"""
        update_data = {
            "username": "adminupdated",
            "fullname": "Admin Updated",
            "is_admin": True,
            "is_active": False
        }
        
        response = client.put(f"/api/v1/users/update/{db_test_user.id}", json=update_data)
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["username"] == update_data["username"]
        assert data["fullname"] == update_data["fullname"]
        assert data["is_admin"] == update_data["is_admin"]
        assert data["is_active"] == update_data["is_active"]
    
    @pytest.mark.asyncio
    async def test_update_user_partial(self, client: TestClient, api_test_dependencies, db_test_user):
        """部分的なユーザー情報更新テスト"""
        update_data = {
            "username": "partialupdate"
        }
        
        response = client.put(f"/api/v1/users/update/{db_test_user.id}", json=update_data)
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["username"] == update_data["username"]
        assert data["fullname"] == db_test_user.fullname
        assert data["is_admin"] == db_test_user.is_admin
        assert data["is_active"] == db_test_user.is_active
    
    @pytest.mark.asyncio
    async def test_update_user_nonexistent(self, client: TestClient, api_test_dependencies):
        """存在しないユーザーの情報更新テスト"""
        non_existent_id = uuid.uuid4()
        update_data = {
            "username": "nonexistentupdate"
        }
        
        response = client.put(f"/api/v1/users/update/{non_existent_id}", json=update_data)
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    @pytest.mark.asyncio
    async def test_update_user_duplicate_username(self, client: TestClient, api_test_dependencies, db_test_user, db_test_admin):
        """重複ユーザー名でのユーザー情報更新テスト（失敗ケース）"""
        update_data = {
            "username": db_test_admin.username
        }
        
        response = client.put(f"/api/v1/users/update/{db_test_user.id}", json=update_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    @pytest.mark.asyncio
    async def test_delete_user(self, client: TestClient, api_test_dependencies, db_session):
        """ユーザー削除テスト"""
        # 削除用のテストユーザーを作成
        from app.models.user import User
        delete_user = User(
            username="deleteuser",
            fullname="Delete User",
            is_admin=False,
            is_active=True,
            user_id=uuid.uuid4()
        )
        db_session.add(delete_user)
        await db_session.commit()
        await db_session.refresh(delete_user)
        
        response = client.delete(f"/api/v1/users/delete/{delete_user.id}")
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # 削除されたことを確認
        response = client.get(f"/api/v1/users/{delete_user.id}")
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_user(self, client: TestClient, api_test_dependencies):
        """存在しないユーザーの削除テスト"""
        non_existent_id = uuid.uuid4()
        response = client.delete(f"/api/v1/users/delete/{non_existent_id}")
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    @pytest.mark.asyncio
    async def test_delete_self(self, client: TestClient, api_test_dependencies, db_test_admin):
        """自分自身の削除テスト（失敗ケース）"""
        response = client.delete(f"/api/v1/users/delete/{db_test_admin.id}")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
