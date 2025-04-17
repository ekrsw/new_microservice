import pytest
from fastapi import HTTPException
from unittest.mock import patch, AsyncMock, MagicMock
import uuid
from uuid import UUID

from app.api.deps import (
    get_current_user,
    get_current_admin_user,
    validate_refresh_token
)
from app.models.user import AuthUser


class TestDeps:
    @pytest.mark.asyncio
    async def test_get_current_user_success(self, db_session):
        """get_current_userが正常動作するケースのテスト"""
        # テスト用のユーザーID
        user_id = uuid.uuid4()
        
        # モックユーザーの作成
        mock_user = AuthUser(
            id=user_id,
            username="test_user",
            hashed_password="hashed_password",
            is_admin=False
        )
        
        # verify_tokenとuser_crud.get_by_idの戻り値をモック
        with patch("app.api.deps.verify_token") as mock_verify_token, \
             patch("app.crud.user.user.get_by_id") as mock_get_by_id:
            
            # トークン検証結果のモック
            mock_verify_token.return_value = {"sub": str(user_id), "username": "test_user"}
            
            # ユーザー取得結果のモック
            mock_get_by_id.return_value = mock_user
            
            # 関数を実行
            result = await get_current_user("valid_token", db_session)
            
            # 検証
            assert result == mock_user
            mock_verify_token.assert_called_once_with("valid_token")
            mock_get_by_id.assert_called_once_with(db_session, id=user_id)
    
    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self, db_session):
        """無効なトークンでget_current_userが例外を発生させるケースのテスト"""
        # verify_tokenの戻り値をモック（無効なトークン）
        with patch("app.api.deps.verify_token") as mock_verify_token:
            mock_verify_token.return_value = None
            
            # 例外が発生することを検証
            with pytest.raises(HTTPException) as excinfo:
                await get_current_user("invalid_token", db_session)
            
            # 例外の内容を検証
            assert excinfo.value.status_code == 401
            assert "認証情報が無効です" in excinfo.value.detail
    
    @pytest.mark.asyncio
    async def test_get_current_user_user_not_found(self, db_session):
        """ユーザーが見つからない場合のget_current_userのテスト"""
        # テスト用のユーザーID
        user_id = uuid.uuid4()
        
        # verify_tokenとuser_crud.get_by_idの戻り値をモック
        with patch("app.api.deps.verify_token") as mock_verify_token, \
             patch("app.crud.user.user.get_by_id") as mock_get_by_id:
            
            # トークン検証結果のモック
            mock_verify_token.return_value = {"sub": str(user_id), "username": "test_user"}
            
            # ユーザー取得結果のモック（ユーザーなし）
            mock_get_by_id.return_value = None
            
            # 例外が発生することを検証
            with pytest.raises(HTTPException) as excinfo:
                await get_current_user("valid_token", db_session)
            
            # 例外の内容を検証
            assert excinfo.value.status_code == 401
            assert "認証情報が無効です" in excinfo.value.detail
    
    @pytest.mark.asyncio
    async def test_get_current_admin_user_success(self):
        """管理者ユーザーでget_current_admin_userが正常動作するケースのテスト"""
        # 管理者ユーザーのモック
        admin_user = AuthUser(
            id=uuid.uuid4(),
            username="admin_user",
            hashed_password="hashed_password",
            is_admin=True
        )
        
        # 関数を実行
        result = await get_current_admin_user(admin_user)
        
        # 検証
        assert result == admin_user
    
    @pytest.mark.asyncio
    async def test_get_current_admin_user_not_admin(self):
        """一般ユーザーでget_current_admin_userが例外を発生させるケースのテスト"""
        # 一般ユーザーのモック
        normal_user = AuthUser(
            id=uuid.uuid4(),
            username="normal_user",
            hashed_password="hashed_password",
            is_admin=False
        )
        
        # 例外が発生することを検証
        with pytest.raises(HTTPException) as excinfo:
            await get_current_admin_user(normal_user)
        
        # 例外の内容を検証
        assert excinfo.value.status_code == 403
        assert "この操作には管理者権限が必要です" in excinfo.value.detail
    
    @pytest.mark.asyncio
    async def test_validate_refresh_token_success(self):
        """リフレッシュトークン検証が成功するケースのテスト"""
        # テスト用のユーザーID
        user_id = str(uuid.uuid4())
        
        # verify_refresh_tokenの戻り値をモック
        with patch("app.api.deps.verify_refresh_token") as mock_verify_refresh_token:
            mock_verify_refresh_token.return_value = user_id
            
            # 関数を実行
            result = await validate_refresh_token("valid_refresh_token")
            
            # 検証
            assert result == user_id
            mock_verify_refresh_token.assert_called_once_with("valid_refresh_token")
    
    @pytest.mark.asyncio
    async def test_validate_refresh_token_invalid(self):
        """無効なリフレッシュトークンで例外が発生するケースのテスト"""
        # verify_refresh_tokenの戻り値をモック（無効なトークン）
        with patch("app.api.deps.verify_refresh_token") as mock_verify_refresh_token:
            mock_verify_refresh_token.return_value = None
            
            # 例外が発生することを検証
            with pytest.raises(HTTPException) as excinfo:
                await validate_refresh_token("invalid_refresh_token")
            
            # 例外の内容を検証
            assert excinfo.value.status_code == 401
            assert "リフレッシュトークンが無効です" in excinfo.value.detail
