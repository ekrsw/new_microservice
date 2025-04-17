import pytest
from jose import jwt, JWTError
from datetime import datetime, timedelta, UTC
from unittest.mock import patch, MagicMock
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    blacklist_token,
    is_token_blacklisted,
    verify_token,
    create_refresh_token,
    verify_refresh_token,
    revoke_refresh_token
)
from app.core.config import settings

class TestPasswordFunctions:
    def test_password_hashing(self):
        """パスワードハッシュ化と検証のテスト"""
        password = "test_password"
        hashed = get_password_hash(password)
        
        # ハッシュ化されたパスワードが元のパスワードと異なることを確認
        assert hashed != password
        
        # 正しいパスワードで検証できることを確認
        assert verify_password(password, hashed) is True
        
        # 誤ったパスワードで検証できないことを確認
        assert verify_password("wrong_password", hashed) is False

class TestTokenFunctions:
    @patch("app.core.security.settings.TOKEN_BLACKLIST_ENABLED", True)
    @patch("app.core.security.jwt.encode")
    async def test_create_access_token(self, mock_jwt_encode):
        """アクセストークン生成のテスト"""
        mock_jwt_encode.return_value = "mocked_token"
        
        test_data = {"sub": "user_id", "username": "testuser"}
        token = await create_access_token(data=test_data)
        
        assert token == "mocked_token"
        mock_jwt_encode.assert_called_once()
    
    @patch("app.core.security.settings.TOKEN_BLACKLIST_ENABLED", True)
    @patch("app.core.security.redis.from_url")
    async def test_blacklist_token_successful(self, mock_redis_from_url, mock_redis):
        """トークンのブラックリスト登録テスト（成功）"""
        # Redisモックの設定
        mock_redis_instance = mock_redis
        mock_redis_from_url.return_value = mock_redis_instance
        
        # JWT.decodeをモック化
        with patch("app.core.security.jwt.decode") as mock_jwt_decode:
            # 有効なJWTペイロードを設定
            exp_time = (datetime.now(UTC) + timedelta(minutes=15)).timestamp()
            mock_jwt_decode.return_value = {"jti": "test_jti", "exp": exp_time}
            
            # トークン
            token = "dummy_token"
            
            # ブラックリスト登録
            result = await blacklist_token(token)
            
            # 検証
            assert result is True
            assert f"blacklist_token:test_jti" in mock_redis_instance.data
    
    @patch("app.core.security.settings.TOKEN_BLACKLIST_ENABLED", True)
    @patch("app.core.security.redis.from_url")
    async def test_is_token_blacklisted(self, mock_redis_from_url, mock_redis):
        """ブラックリストチェックのテスト"""
        # Redisモックの設定
        mock_redis_instance = mock_redis
        mock_redis_from_url.return_value = mock_redis_instance
        
        # テストデータをRedisにセット
        await mock_redis_instance.setex("blacklist_token:test_jti", 3600, "1")
        
        # ブラックリスト済みのトークンをチェック
        result = await is_token_blacklisted({"jti": "test_jti"})
        assert result is True
        
        # ブラックリストされていないトークンをチェック
        result = await is_token_blacklisted({"jti": "non_blacklisted_jti"})
        assert result is False
    
    @patch("app.core.security.settings.TOKEN_BLACKLIST_ENABLED", True)
    @patch("app.core.security.jwt.decode")
    @patch("app.core.security.is_token_blacklisted")
    async def test_verify_token_valid(self, mock_is_blacklisted, mock_jwt_decode):
        """有効なトークン検証のテスト"""
        # モックの設定
        mock_payload = {"sub": "user_id", "username": "testuser", "jti": "test_jti"}
        mock_jwt_decode.return_value = mock_payload
        mock_is_blacklisted.return_value = False
        
        # トークン検証
        result = await verify_token("valid_token")
        
        # 検証
        assert result == mock_payload
        mock_jwt_decode.assert_called_once()
        mock_is_blacklisted.assert_called_once_with(mock_payload)
    
    @patch("app.core.security.settings.TOKEN_BLACKLIST_ENABLED", True)
    @patch("app.core.security.jwt.decode")
    @patch("app.core.security.is_token_blacklisted")
    async def test_verify_token_blacklisted(self, mock_is_blacklisted, mock_jwt_decode):
        """ブラックリスト登録済みトークンの検証テスト"""
        # モックの設定
        mock_payload = {"sub": "user_id", "username": "testuser", "jti": "test_jti"}
        mock_jwt_decode.return_value = mock_payload
        mock_is_blacklisted.return_value = True
        
        # トークン検証
        result = await verify_token("blacklisted_token")
        
        # 検証
        assert result is None
        mock_jwt_decode.assert_called_once()
        mock_is_blacklisted.assert_called_once_with(mock_payload)
    
    @patch("app.core.security.settings.TOKEN_BLACKLIST_ENABLED", True)
    @patch("app.core.security.jwt.decode")
    async def test_verify_token_invalid(self, mock_jwt_decode):
        """無効なトークンの検証テスト"""
        # JWTエラーを発生させる
        mock_jwt_decode.side_effect = JWTError("Invalid token")
        
        # トークン検証
        result = await verify_token("invalid_token")
        
        # 検証
        assert result is None
        mock_jwt_decode.assert_called_once()
    
    @patch("app.core.security.settings.TOKEN_BLACKLIST_ENABLED", True)
    @patch("app.core.security.redis.from_url")
    async def test_create_refresh_token(self, mock_redis_from_url, mock_redis):
        """リフレッシュトークン生成のテスト"""
        # Redisモックの設定
        mock_redis_instance = mock_redis
        mock_redis_from_url.return_value = mock_redis_instance
        
        # リフレッシュトークン作成
        user_id = "test_user_id"
        token = await create_refresh_token(user_id)
        
        # 検証
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Redisにトークンが保存されていることを確認
        key = f"refresh_token:{token}"
        assert key in mock_redis_instance.data
        assert mock_redis_instance.data[key] == user_id
    
    @patch("app.core.security.settings.TOKEN_BLACKLIST_ENABLED", True)
    @patch("app.core.security.redis.from_url")
    async def test_verify_refresh_token_valid(self, mock_redis_from_url, mock_redis):
        """有効なリフレッシュトークン検証のテスト"""
        # Redisモックの設定
        mock_redis_instance = mock_redis
        mock_redis_from_url.return_value = mock_redis_instance
        
        # テストデータをRedisにセット
        token = "valid_refresh_token"
        user_id = "test_user_id"
        await mock_redis_instance.setex(f"refresh_token:{token}", 3600, user_id)
        
        # リフレッシュトークン検証
        result = await verify_refresh_token(token)
        
        # 検証
        assert result == user_id
    
    @patch("app.core.security.settings.TOKEN_BLACKLIST_ENABLED", True)
    @patch("app.core.security.redis.from_url")
    async def test_verify_refresh_token_invalid(self, mock_redis_from_url, mock_redis):
        """無効なリフレッシュトークン検証のテスト"""
        # Redisモックの設定
        mock_redis_instance = mock_redis
        mock_redis_from_url.return_value = mock_redis_instance
        
        # 存在しないトークンの検証
        result = await verify_refresh_token("invalid_token")
        
        # 検証
        assert result is None
    
    @patch("app.core.security.settings.TOKEN_BLACKLIST_ENABLED", True)
    @patch("app.core.security.redis.from_url")
    async def test_revoke_refresh_token(self, mock_redis_from_url, mock_redis):
        """リフレッシュトークン無効化のテスト"""
        # Redisモックの設定
        mock_redis_instance = mock_redis
        mock_redis_from_url.return_value = mock_redis_instance
        
        # テストデータをRedisにセット
        token = "refresh_token_to_revoke"
        user_id = "test_user_id"
        await mock_redis_instance.setex(f"refresh_token:{token}", 3600, user_id)
        
        # リフレッシュトークン無効化
        result = await revoke_refresh_token(token)
        
        # 検証
        assert result is True
        assert f"refresh_token:{token}" not in mock_redis_instance.data
