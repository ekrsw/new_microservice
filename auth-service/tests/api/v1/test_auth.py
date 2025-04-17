import pytest
from httpx import AsyncClient
from fastapi import status
from uuid import UUID

from app.core.security import verify_password
from app.schemas.user import UserCreate, AdminUserCreate


class TestAuth:
    @pytest.mark.asyncio
    async def test_login_success(self, async_client: AsyncClient, create_test_user):
        """ログイン成功ケースのテスト"""
        response = await async_client.post(
            "/api/v1/auth/login",
            data={
                "username": "test_user",
                "password": "test_password"
            }
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
    
    @pytest.mark.asyncio
    async def test_login_invalid_username(self, async_client: AsyncClient):
        """存在しないユーザー名でのログイン失敗テスト"""
        response = await async_client.post(
            "/api/v1/auth/login",
            data={
                "username": "nonexistent_user",
                "password": "test_password"
            }
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.asyncio
    async def test_login_invalid_password(self, async_client: AsyncClient, create_test_user):
        """無効なパスワードでのログイン失敗テスト"""
        response = await async_client.post(
            "/api/v1/auth/login",
            data={
                "username": "test_user",
                "password": "wrong_password"
            }
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.asyncio
    async def test_refresh_token_success(self, async_client: AsyncClient, user_tokens):
        """リフレッシュトークンでの更新成功テスト"""
        response = await async_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": user_tokens.refresh_token}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        # 新しいトークンが発行されていることを確認
        assert data["access_token"] != user_tokens.access_token
        assert data["refresh_token"] != user_tokens.refresh_token
    
    @pytest.mark.asyncio
    async def test_refresh_token_invalid(self, async_client: AsyncClient):
        """無効なリフレッシュトークンでの更新失敗テスト"""
        response = await async_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid_token"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.asyncio
    async def test_logout_success(self, async_client: AsyncClient, user_tokens):
        """ログアウト成功テスト"""
        response = await async_client.post(
            "/api/v1/auth/logout",
            json={
                "access_token": user_tokens.access_token,
                "refresh_token": user_tokens.refresh_token
            }
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "detail" in data
    
    @pytest.mark.asyncio
    async def test_update_password_success(
        self, async_client: AsyncClient, token_headers, create_test_user, db_session
    ):
        """パスワード更新成功テスト"""
        response = await async_client.post(
            "/api/v1/auth/update/password",
            json={
                "current_password": "test_password",
                "new_password": "new_test_password"
            },
            headers=token_headers
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(create_test_user.id)
        
        # ユーザーを再取得してパスワードが更新されていることを確認
        updated_user = await db_session.get(type(create_test_user), create_test_user.id)
        assert verify_password("new_test_password", updated_user.hashed_password)
    
    @pytest.mark.asyncio
    async def test_update_password_invalid_current(
        self, async_client: AsyncClient, token_headers
    ):
        """現在のパスワードが無効な場合のパスワード更新失敗テスト"""
        response = await async_client.post(
            "/api/v1/auth/update/password",
            json={
                "current_password": "wrong_password",
                "new_password": "new_test_password"
            },
            headers=token_headers
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.asyncio
    async def test_verify_token_success(self, async_client: AsyncClient, token_headers):
        """トークン検証成功テスト"""
        # ヘッダーからトークンを取得
        token = token_headers["Authorization"].replace("Bearer ", "")
        
        response = await async_client.post(
            "/api/v1/auth/verify",
            json={"token": token}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["valid"] is True
        assert "user_id" in data
        assert "username" in data
    
    @pytest.mark.asyncio
    async def test_verify_token_invalid(self, async_client: AsyncClient):
        """無効なトークンの検証テスト"""
        response = await async_client.post(
            "/api/v1/auth/verify",
            json={"token": "invalid_token"}
        )
        # 無効なトークンでもHTTP 200を返す仕様のため
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["valid"] is False
        assert "error" in data
    
    @pytest.mark.asyncio
    async def test_admin_update_password(
        self, async_client: AsyncClient, admin_token_headers, create_test_user, db_session
    ):
        """管理者によるパスワード更新テスト"""
        response = await async_client.post(
            "/api/v1/auth/admin/update/password",
            json={
                "user_id": str(create_test_user.id),
                "new_password": "admin_changed_password"
            },
            headers=admin_token_headers
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(create_test_user.id)
        
        # ユーザーを再取得してパスワードが更新されていることを確認
        updated_user = await db_session.get(type(create_test_user), create_test_user.id)
        assert verify_password("admin_changed_password", updated_user.hashed_password)
    
    @pytest.mark.asyncio
    async def test_admin_update_password_non_admin(
        self, async_client: AsyncClient, token_headers, create_admin_user
    ):
        """非管理者によるパスワード更新失敗テスト"""
        response = await async_client.post(
            "/api/v1/auth/admin/update/password",
            json={
                "user_id": str(create_admin_user.id),
                "new_password": "changed_by_non_admin"
            },
            headers=token_headers  # 通常ユーザーのトークン
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
