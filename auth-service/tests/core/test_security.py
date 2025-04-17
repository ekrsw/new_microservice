import pytest
import pytest_asyncio
from datetime import datetime, timedelta, UTC
import uuid
from jose import jwt
from unittest.mock import patch, AsyncMock

from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    verify_token,
    create_refresh_token,
    verify_refresh_token,
    revoke_refresh_token,
    blacklist_token,
    is_token_blacklisted
)
from tests.crud.user.conftest import settings


class TestSecurity:
    def test_password_hashing(self):
        """パスワードハッシュ化と検証のテスト"""
        password = "test_password"
        hashed = get_password_hash(password)
        
        # ハッシュ化されたパスワードは元のパスワードとは異なるはず
        assert hashed != password
        
        # 正しいパスワードでの検証は成功するはず
        assert verify_password(password, hashed) is True
        
        # 間違ったパスワードでの検証は失敗するはず
        assert verify_password("wrong_password", hashed) is False
    
    @pytest.mark.asyncio
    async def test_create_access_token(self):
        """アクセストークン生成のテスト"""
        user_id = str(uuid.uuid4())
        username = "test_user"
        data = {"sub": user_id, "username": username}
        
        # トークン生成
        token = await create_access_token(data)
        
        # トークンが文字列であることを確認
        assert isinstance(token, str)
        
        # トークンの検証
        decoded = jwt.decode(
            token, 
            settings.PUBLIC_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        
        # ペイロードが正しいことを確認
        assert decoded["sub"] == user_id
        assert decoded["username"] == username
        assert "jti" in decoded  # JTI (JWT ID) が含まれていること
        assert "exp" in decoded  # 有効期限が含まれていること
    
    @pytest.mark.asyncio
    async def test_verify_token(self):
        """トークン検証のテスト"""
        user_id = str(uuid.uuid4())
        username = "test_user"
        data = {"sub": user_id, "username": username}
        
        # トークン生成
        token = await create_access_token(data)
        
        # トークン検証
        payload = await verify_token(token)
        
        # ペイロードが正しいことを確認
        assert payload is not None
        assert payload["sub"] == user_id
        assert payload["username"] == username
        
        # 無効なトークンの検証
        invalid_payload = await verify_token("invalid.token.string")
        assert invalid_payload is None
    
    @pytest.mark.asyncio
    async def test_token_blacklist(self):
        """トークンブラックリストのテスト"""
        user_id = str(uuid.uuid4())
        username = "test_user"
        data = {"sub": user_id, "username": username}
        
        # トークン生成
        token = await create_access_token(data)
        
        # トークンをブラックリストに追加
        result = await blacklist_token(token)
        assert result is True
        
        # トークンの検証（ブラックリストに追加されているので失敗するはず）
        payload = await verify_token(token)
        assert payload is None
        
        # 無効なトークンのブラックリスト追加
        invalid_result = await blacklist_token("invalid.token.string")
        assert invalid_result is False
    
    @pytest.mark.asyncio
    async def test_refresh_token_lifecycle(self):
        """リフレッシュトークンのライフサイクルテスト（作成→検証→無効化）"""
        user_id = str(uuid.uuid4())
        
        # リフレッシュトークン生成
        refresh_token = await create_refresh_token(user_id)
        
        # トークンが文字列であることを確認
        assert isinstance(refresh_token, str)
        
        # リフレッシュトークン検証
        verified_user_id = await verify_refresh_token(refresh_token)
        assert verified_user_id == user_id
        
        # リフレッシュトークン無効化
        revoke_result = await revoke_refresh_token(refresh_token)
        assert revoke_result is True
        
        # 無効化後の検証
        post_revoke_user_id = await verify_refresh_token(refresh_token)
        assert post_revoke_user_id is None
        
        # 無効なリフレッシュトークンの無効化
        invalid_revoke_result = await revoke_refresh_token("invalid_token")
        assert invalid_revoke_result is False
    
    @pytest.mark.asyncio
    async def test_token_expiry(self):
        """トークンの有効期限テスト"""
        user_id = str(uuid.uuid4())
        username = "test_user"
        data = {"sub": user_id, "username": username}
        
        # 過去の日時を有効期限として設定
        expires_delta = timedelta(minutes=-5)  # 5分前
        
        # 既に有効期限切れのトークンを生成
        expired_token = await create_access_token(data, expires_delta)
        
        # トークンの検証（有効期限切れなので失敗するはず）
        with pytest.raises(jwt.ExpiredSignatureError):
            decoded = jwt.decode(
                expired_token, 
                settings.PUBLIC_KEY, 
                algorithms=[settings.ALGORITHM]
            )
        
        # 通常の検証関数でも検証に失敗するはず
        payload = await verify_token(expired_token)
        assert payload is None
    
    @pytest.mark.asyncio
    async def test_is_token_blacklisted(self):
        """トークンのブラックリスト確認関数のテスト"""
        # モックのペイロード
        jti = str(uuid.uuid4())
        payload = {"jti": jti, "sub": "user123", "exp": (datetime.now(UTC) + timedelta(minutes=30)).timestamp()}
        
        # Redisモックを使用してブラックリストチェックをテスト
        with patch("redis.asyncio.Redis.from_url") as mock_redis:
            # Redisのget操作をモック
            mock_redis.return_value.get = AsyncMock(return_value=None)
            mock_redis.return_value.aclose = AsyncMock()
            
            # ブラックリストされていない場合
            result = await is_token_blacklisted(payload)
            assert result is False
            
            # Redisのget操作をモック（ブラックリストされている場合）
            mock_redis.return_value.get = AsyncMock(return_value=b"1")
            
            # ブラックリストされている場合
            result = await is_token_blacklisted(payload)
            assert result is True
            
            # jtiがない場合
            result = await is_token_blacklisted({"sub": "user123", "exp": 123456789})
            assert result is False
