import pytest
from fastapi.testclient import TestClient
from fastapi import status
import uuid

class TestUserSearch:
    @pytest.mark.asyncio
    async def test_search_users_by_username(self, client: TestClient, api_test_dependencies, db_test_user):
        """ユーザー名によるユーザー検索テスト"""
        response = client.get(f"/api/v1/users/search?username={db_test_user.username[:4]}")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(user["username"] == db_test_user.username for user in data)
    
    @pytest.mark.asyncio
    async def test_search_users_by_fullname(self, client: TestClient, api_test_dependencies, db_test_user):
        """フルネームによるユーザー検索テスト"""
        response = client.get(f"/api/v1/users/search?fullname={db_test_user.fullname[:4]}")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(user["fullname"] == db_test_user.fullname for user in data)
    
    @pytest.mark.asyncio
    async def test_search_users_by_admin_flag(self, client: TestClient, api_test_dependencies, db_test_admin):
        """管理者フラグによるユーザー検索テスト"""
        response = client.get("/api/v1/users/search?is_admin=true")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(user["username"] == db_test_admin.username for user in data)
    
    @pytest.mark.asyncio
    async def test_search_users_by_active_flag(self, client: TestClient, api_test_dependencies, db_test_user, db_session):
        """アクティブフラグによるユーザー検索テスト"""
        # ユーザーを非アクティブに設定
        db_test_user.is_active = False
        await db_session.commit()
        
        response = client.get("/api/v1/users/search?is_active=false")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(user["username"] == db_test_user.username for user in data)
    
    @pytest.mark.asyncio
    async def test_search_users_combined(self, client: TestClient, api_test_dependencies, db_test_admin):
        """複合条件によるユーザー検索テスト"""
        response = client.get(f"/api/v1/users/search?username={db_test_admin.username[:4]}&is_admin=true")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(user["username"] == db_test_admin.username for user in data)
    
    @pytest.mark.asyncio
    async def test_search_users_no_results(self, client: TestClient, api_test_dependencies):
        """検索結果なしのテスト"""
        response = client.get("/api/v1/users/search?username=nonexistentuser")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0


class TestUserSync:
    @pytest.mark.asyncio
    async def test_sync_user_create(self, client: TestClient, api_test_dependencies):
        """ユーザー同期（新規作成）テスト"""
        user_id = str(uuid.uuid4())
        sync_data = {
            "user_id": user_id,
            "username": "syncuser",
            "fullname": "Sync User",
            "is_admin": False,
            "is_active": True
        }
        
        response = client.post("/api/v1/sync/user", json=sync_data)
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["username"] == sync_data["username"]
        assert data["fullname"] == sync_data["fullname"]
        assert data["is_admin"] == sync_data["is_admin"]
        assert data["is_active"] == sync_data["is_active"]
        assert str(data["user_id"]) == user_id
    
    @pytest.mark.asyncio
    async def test_sync_user_update(self, client: TestClient, api_test_dependencies, db_session):
        """ユーザー同期（更新）テスト"""
        # 最初にユーザーを作成
        user_id = uuid.uuid4()
        from app.models.user import User
        sync_user = User(
            username="syncuserupdate",
            fullname="Sync User Update",
            is_admin=False,
            is_active=True,
            user_id=user_id
        )
        db_session.add(sync_user)
        await db_session.commit()
        await db_session.refresh(sync_user)
        
        # 同期APIで更新
        sync_data = {
            "user_id": str(user_id),
            "username": "syncuserupdated",
            "fullname": "Sync User Updated",
            "is_admin": True,
            "is_active": False
        }
        
        response = client.post("/api/v1/sync/user", json=sync_data)
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["username"] == sync_data["username"]
        assert data["fullname"] == sync_data["fullname"]
        assert data["is_admin"] == sync_data["is_admin"]
        assert data["is_active"] == sync_data["is_active"]
        assert str(data["user_id"]) == str(user_id)
    
    @pytest.mark.asyncio
    async def test_sync_user_without_fullname(self, client: TestClient, api_test_dependencies):
        """フルネームなしでのユーザー同期テスト"""
        user_id = str(uuid.uuid4())
        sync_data = {
            "user_id": user_id,
            "username": "syncusernofullname",
            "is_admin": False,
            "is_active": True
        }
        
        response = client.post("/api/v1/sync/user", json=sync_data)
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["username"] == sync_data["username"]
        assert data["fullname"] is None
        assert data["is_admin"] == sync_data["is_admin"]
        assert data["is_active"] == sync_data["is_active"]
        assert str(data["user_id"]) == user_id
