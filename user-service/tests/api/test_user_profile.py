import pytest
from fastapi.testclient import TestClient
from fastapi import status
import uuid

class TestUserProfile:
    @pytest.mark.asyncio
    async def test_get_profile_me(self, client: TestClient, api_test_dependencies, db_test_user):
        """自分自身のプロファイル情報取得テスト"""
        response = client.get("/api/v1/profile/me")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["username"] == db_test_user.username
        assert data["fullname"] == db_test_user.fullname
        assert data["is_active"] == db_test_user.is_active
        assert data["is_admin"] == db_test_user.is_admin
    
    @pytest.mark.asyncio
    async def test_get_profile_by_id(self, client: TestClient, api_test_dependencies, db_test_user):
        """特定ユーザーのプロファイル情報取得テスト"""
        response = client.get(f"/api/v1/profile/{db_test_user.id}")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["username"] == db_test_user.username
        assert data["fullname"] == db_test_user.fullname
        assert data["is_active"] == db_test_user.is_active
        assert data["is_admin"] == db_test_user.is_admin
    
    @pytest.mark.asyncio
    async def test_get_profile_nonexistent_user(self, client: TestClient, api_test_dependencies):
        """存在しないユーザーのプロファイル情報取得テスト"""
        non_existent_id = uuid.uuid4()
        response = client.get(f"/api/v1/profile/{non_existent_id}")
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    @pytest.mark.asyncio
    async def test_get_profile_inactive_user(self, client: TestClient, api_test_dependencies, db_session, db_test_user):
        """非アクティブユーザーのプロファイル情報取得テスト"""
        # ユーザーを非アクティブに設定
        db_test_user.is_active = False
        await db_session.commit()
        
        response = client.get(f"/api/v1/profile/{db_test_user.id}")
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    @pytest.mark.asyncio
    async def test_update_profile(self, client: TestClient, api_test_dependencies, db_test_user):
        """プロファイル情報更新テスト"""
        update_data = {
            "username": "updateduser",
            "fullname": "Updated User"
        }
        
        response = client.put("/api/v1/profile/update", json=update_data)
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["username"] == update_data["username"]
        assert data["fullname"] == update_data["fullname"]
        assert data["is_active"] == db_test_user.is_active
        assert data["is_admin"] == db_test_user.is_admin
    
    @pytest.mark.asyncio
    async def test_update_profile_username_only(self, client: TestClient, api_test_dependencies, db_test_user):
        """ユーザー名のみの更新テスト"""
        update_data = {
            "username": "usernameonly"
        }
        
        response = client.put("/api/v1/profile/update", json=update_data)
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["username"] == update_data["username"]
        assert data["fullname"] == db_test_user.fullname
    
    @pytest.mark.asyncio
    async def test_update_profile_fullname_only(self, client: TestClient, api_test_dependencies, db_test_user):
        """フルネームのみの更新テスト"""
        update_data = {
            "fullname": "Fullname Only"
        }
        
        response = client.put("/api/v1/profile/update", json=update_data)
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["username"] == db_test_user.username
        assert data["fullname"] == update_data["fullname"]
    
    @pytest.mark.asyncio
    async def test_update_profile_admin_flag_ignored(self, client: TestClient, api_test_dependencies, db_test_user):
        """管理者フラグの更新が無視されるテスト"""
        update_data = {
            "username": "updateduser",
            "is_admin": True  # 一般ユーザーは管理者フラグを変更できない
        }
        
        response = client.put("/api/v1/profile/update", json=update_data)
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["username"] == update_data["username"]
        assert data["is_admin"] == db_test_user.is_admin  # 変更されていないことを確認
    
    @pytest.mark.asyncio
    async def test_update_profile_duplicate_username(self, client: TestClient, api_test_dependencies, db_test_user, db_test_admin):
        """重複ユーザー名での更新テスト（失敗ケース）"""
        update_data = {
            "username": db_test_admin.username  # 既に存在するユーザー名
        }
        
        response = client.put("/api/v1/profile/update", json=update_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
